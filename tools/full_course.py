#!/usr/bin/env python3
"""Ordered full-loop mission with continuous odometry audit and explicit pause/resume.

No reset or teleport commands. Recovery only backs up 0.5 m through Nav2's
collision-checked BackUp action, once per waypoint. Pauses retain the observer.
"""
import json
import argparse
import fcntl
import math
from pathlib import Path
import re
import time
import rclpy
from rclpy.action import ActionClient
from rclpy.qos import QoSProfile, DurabilityPolicy
from rclpy.signals import SignalHandlerOptions
from nav_msgs.msg import Odometry, Path as RosPath
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import NavSatFix, LaserScan
from std_msgs.msg import Bool, String
from std_srvs.srv import SetBool, Trigger
from nav2_msgs.action import NavigateToPose, NavigateThroughPoses, BackUp
from nav2_msgs.msg import SpeedLimit
from approach_speed import approach_speed
from course_progress import CourseProgress, ProgressError
from gps_mission import LocalFrame

ROOT = Path(__file__).resolve().parents[1]
MISSION = ROOT/'ros2/src/igvc_gps/config/full_loop.json'
REPORT = ROOT/'artifacts/checks/full-course-live.json'


class Mission:
    def __init__(self, resume=False):
        self.config = json.loads(MISSION.read_text())
        self.points = self.config['waypoints']
        self.frame = LocalFrame(self.config['origin'])
        self.audit = CourseProgress.from_mission(self.config, max_lateral=2.2, waypoint_tolerance=.4)
        self.node = rclpy.create_node('igvc_full_course_mission')
        self.nav = ActionClient(self.node, NavigateToPose, '/navigate_to_pose')
        self.through = ActionClient(self.node, NavigateThroughPoses, '/navigate_through_poses')
        self.backup = ActionClient(self.node, BackUp, '/backup')
        self.gate = self.node.create_client(SetBool, '/sim/set_autonomy')
        self.zone = self.node.create_client(SetBool, '/sim/set_unmarked_mode')
        self.node.create_service(Trigger, '/mission/resume', self.resume)
        self.node.create_service(Trigger, '/mission/cancel', self.cancel)
        self.state = {'status':'starting', 'completed_waypoints':0, 'total_waypoints':len(self.points),
                      'events':[], 'trajectory':[], 'mission_file':str(MISSION), 'run_id':None}
        self.saved_audit=None
        if resume:
            self.state=json.loads(REPORT.read_text())
            if self.state.get('audit_error') or not self.state['audit']['valid']:
                raise ValueError('Cannot resume an invalidated route audit')
            if self.state['status']=='completed': raise ValueError('Loop already complete')
            self.saved_audit=self.state['audit']
            self.state['status']='resuming'
            # Prior cleanup resets the adapter to painted mode; reapply the
            # saved position's zone before arming, even if the report says unmarked.
            self.state.pop('zone',None)
        self.origin = None; self.last_gps = 0.; self.last_scan = 0.
        self.course_hash = None
        self.last_fix_stamp = None; self.enabled = False; self.armed = False
        self.resume_requested = False; self.canceled = False; self.handle = None
        self.last_save = 0.; self.last_sample = 0.; self.last_odom = 0.
        self.approach_target = None
        self.speed_limit = self.node.create_publisher(SpeedLimit, '/speed_limit', 10)
        self.audit_error = None; self.run_id = None; self.xy = None; self.start_run = None
        if self.saved_audit is not None:
            self.start_run=self.state['run_id']
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.node.create_subscription(Odometry, '/odom', self.odom, 50)
        self.node.create_subscription(NavSatFix, '/gps/fix', self.gps, 10)
        self.node.create_subscription(LaserScan, '/scan', lambda m: setattr(self,'last_scan',time.monotonic()), 10)
        self.node.create_subscription(String, '/gps/origin', self.gps_origin, qos)
        self.node.create_subscription(Bool, '/sim/autonomy_enabled', lambda m: setattr(self,'enabled',m.data), qos)
        self.node.create_subscription(String, '/sim/status', self.sim_status, 10)
        self.path = self.node.create_publisher(RosPath, '/mission/route', qos)
        self.driven = self.node.create_publisher(RosPath, '/mission/driven', qos)

    def event(self, text):
        self.state['events'].append({'wall':time.time(), 'message':text})
        print(text, flush=True)
        self.save()

    def resume(self, request, response):
        response.success = self.state['status']=='paused' and self.audit_error is None
        self.resume_requested = response.success
        response.message = 'Retry same waypoint requested' if response.success else 'Mission is not resumable'
        return response

    def cancel(self, request, response):
        self.canceled=True; response.success=True; response.message='Mission cancellation requested'
        return response

    def gps_origin(self, m):
        try: self.origin=json.loads(m.data)
        except ValueError: self.origin=None

    def gps(self, m):
        stamp=(m.header.stamp.sec,m.header.stamp.nanosec)
        if m.status.status>=0 and m.header.frame_id=='gps_link' and stamp!=self.last_fix_stamp and all(math.isfinite(v) for v in (m.latitude,m.longitude,m.altitude)):
            self.last_fix_stamp=stamp; self.last_gps=time.monotonic()

    def sim_status(self, m):
        self.state['sim_status']=m.data
        course_match=re.search(r'course_hash=([a-f0-9]{64})',m.data)
        self.course_hash=course_match[1] if course_match else None
        match=re.search(r'run=(\d+)',m.data)
        if match:
            self.run_id=int(match[1])
            if self.start_run is not None and self.run_id!=self.start_run:
                self.audit_error='Simulator reset during full-loop attempt'

    def odom(self, m):
        p=m.pose.pose.position; q=m.pose.pose.orientation
        stamp=m.header.stamp.sec+m.header.stamp.nanosec*1e-9
        self.last_odom=time.monotonic(); self.xy=(p.x,p.y)
        cap = 2.2 if self.approach_target is None else approach_speed(math.dist(self.xy, self.approach_target))
        limit = SpeedLimit(); limit.header = m.header; limit.percentage = False; limit.speed_limit = cap
        self.speed_limit.publish(limit)
        self.state['approach_speed_limit_mps'] = cap
        if self.run_id is None: return
        if self.start_run is None:
            self.start_run=self.run_id; self.state['run_id']=self.run_id
        try:
            if self.saved_audit is not None:
                self.audit.restore(self.saved_audit,(p.x,p.y),stamp,run_id=self.run_id)
                self.saved_audit=None
                self.state['events'].append({'wall':time.time(),'message':'Resumed audit after explicit stationary pause; same run and pose checked within 0.1 m'})
            self.state['audit']=self.audit.update(p.x,p.y,stamp,run_id=self.run_id)
        except ProgressError as exc: self.audit_error=str(exc)
        if stamp-self.last_sample>=.1:
            self.last_sample=stamp
            yaw=math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
            self.state['trajectory'].append([stamp,p.x,p.y,yaw])
        self.state['pose']=[p.x,p.y]
        self.state['velocity']=[m.twist.twist.linear.x,m.twist.twist.angular.z]
        if time.monotonic()-self.last_save>1: self.save()

    def save(self):
        self.last_save=time.monotonic()
        self.state['audit_error']=self.audit_error
        REPORT.parent.mkdir(parents=True,exist_ok=True)
        temp=REPORT.with_suffix('.tmp'); temp.write_text(json.dumps(self.state,indent=2)+'\n');temp.replace(REPORT)
        if hasattr(self,'driven') and self.state['trajectory']:
            path=RosPath();path.header.frame_id='odom'
            for _,x,y,_ in self.state['trajectory'][::5]:
                pose=PoseStamped();pose.header.frame_id='odom'
                pose.pose.position.x=x;pose.pose.position.y=y;pose.pose.orientation.w=1.
                path.poses.append(pose)
            self.driven.publish(path)

    def spin(self, seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            rclpy.spin_once(self.node,timeout_sec=.03)
            if self.canceled: raise RuntimeError('Mission canceled')

    def healthy(self):
        if self.canceled: raise RuntimeError('Mission canceled')
        if self.audit_error: raise ProgressError(self.audit_error)
        if time.monotonic()-self.last_gps>3: raise RuntimeError('GPS stale')
        if time.monotonic()-self.last_scan>1: raise RuntimeError('Lidar stale')
        if time.monotonic()-self.last_odom>1: raise RuntimeError('Odometry stale')
        if self.origin!=self.config['origin']: raise RuntimeError('GPS origin mismatch')
        if self.config.get('course_sha256') and self.course_hash!=self.config['course_sha256']:
            raise RuntimeError('Active Unity course does not match the mission manifest hash')
        if self.armed and not self.enabled: raise RuntimeError('Autonomy disabled by manual takeover or perception watchdog')

    def wait(self, future, timeout=10, monitor=False):
        end=time.monotonic()+timeout
        while not future.done() and time.monotonic()<end:
            self.spin(.03)
            if monitor: self.healthy()
        if not future.done(): raise RuntimeError('ROS operation timeout')
        return future.result()

    def service(self, client, value):
        if not client.wait_for_service(timeout_sec=3): raise RuntimeError('Required service unavailable')
        result=self.wait(client.call_async(SetBool.Request(data=value)))
        if not result.success: raise RuntimeError(result.message)

    def stop(self):
        self.armed=False
        self.approach_target=None
        self.service(self.gate,False)
        if self.handle is not None:
            self.wait(self.handle.cancel_goal_async(),5)
            self.handle=None

    def publish_paths(self):
        planned=RosPath();planned.header.frame_id='odom'
        for p in self.points:
            pose=PoseStamped();pose.header.frame_id='odom'
            pose.pose.position.x,pose.pose.position.y=map(float,p['odom_xy'])
            pose.pose.orientation.w=1.;planned.poses.append(pose)
        self.path.publish(planned)

    def recover(self):
        self.healthy()
        if not self.backup.wait_for_server(timeout_sec=3): raise RuntimeError('BackUp server unavailable')
        self.service(self.gate,True);self.spin(.2);self.armed=True
        self.healthy()
        goal=BackUp.Goal();goal.target.x=-.5;goal.speed=.1;goal.time_allowance.sec=12
        self.handle=self.wait(self.backup.send_goal_async(goal),5,True)
        if not self.handle.accepted: self.handle=None;raise RuntimeError('BackUp rejected')
        result=self.wait(self.handle.get_result_async(),15,True)
        self.handle=None;self.stop()
        if result.status!=4: raise RuntimeError('Collision-checked BackUp could not complete')
        self.event('Recovery backed up 0.5 m; retrying the same waypoint')

    def attempt(self, index):
        point=self.points[index]
        # Extend the unpainted declaration by 6 m before its entrance and 2 m
        # after its exit because the level camera sees paint several metres ahead.
        s=point['route_s_m']
        unmarked_arcs=[p['route_s_m'] for p in self.points if p['mode']=='unmarked']
        unmarked=bool(unmarked_arcs and min(unmarked_arcs)-6<=s<=max(unmarked_arcs)+2)
        if self.armed and self.state.get('zone') != ('unmarked' if unmarked else 'painted'):
            self.stop()
        self.service(self.zone,unmarked)
        self.state['zone']='unmarked' if unmarked else 'painted'
        self.healthy()
        x,y,z=self.frame.to_enu(point['latitude'],point['longitude'],point['altitude'])
        if math.dist((x,y),point['odom_xy'])>.001: raise ValueError('Waypoint geodesy mismatch')
        self.approach_target=(x,y)
        self.spin(.1)  # Publish the braking cap before the controller receives its goal.
        goal=NavigateToPose.Goal();goal.pose.header.frame_id='odom'
        goal.pose.pose.position.x=x;goal.pose.pose.position.y=y
        goal.pose.pose.orientation.z=math.sin(point['yaw']/2);goal.pose.pose.orientation.w=math.cos(point['yaw']/2)
        self.handle=self.wait(self.nav.send_goal_async(goal),10,True)
        if not self.handle.accepted: self.handle=None;raise RuntimeError('Nav2 rejected goal')
        if not self.armed:
            self.service(self.gate,True)
            self.spin(.2)
            if not self.enabled: raise RuntimeError('Autonomy enable not confirmed')
            self.armed=True
        result=self.wait(self.handle.get_result_async(),90,True)
        self.handle=None
        if result.status!=4: raise RuntimeError(f'Nav2 action failed: {result.status}')
        if math.dist(self.xy,(x,y))>.35: raise RuntimeError('Goal success outside waypoint tolerance')

    def run_stop_go(self):
        self.spin(3)
        end=time.monotonic()+20
        while not(self.nav.server_is_ready() and self.gate.service_is_ready() and self.origin is not None and self.xy is not None):
            if time.monotonic()>end: raise RuntimeError('Startup timeout')
            self.spin(.1)
        if self.enabled: raise RuntimeError('Another autonomous task is active')
        self.healthy();self.publish_paths();self.state['status']='running'
        self.event(f'Full loop: {len(self.points)} ordered waypoints; no reset/shortcut permitted')
        for index in range(self.state['completed_waypoints'],len(self.points)):
            point=self.points[index]
            self.state['active_waypoint']=index+1
            recovered=False
            while True:
                try:
                    self.event(f'Waypoint {index+1}/{len(self.points)} {point["name"]} at {point["odom_xy"]}')
                    self.attempt(index)
                    break
                except ProgressError: raise
                except RuntimeError as exc:
                    self.stop()
                    if self.canceled: raise
                    if str(exc).startswith('Nav2 action failed') and not recovered:
                        recovered=True
                        try:
                            self.recover()
                            continue
                        except RuntimeError as recovery_error:
                            self.stop();self.event('Recovery stopped: '+str(recovery_error))
                    self.state['status']='paused';self.resume_requested=False
                    self.event('Paused at same waypoint: '+str(exc))
                    while not self.resume_requested:
                        self.spin(.1)
                        if self.audit_error: raise ProgressError(self.audit_error)
                    self.state['status']='running';self.event('Explicit resume: retrying uncompleted waypoint')
            self.state['completed_waypoints']=index+1;self.save()
        self.stop();self.service(self.zone,False)
        snap=self.audit.snapshot()
        if not snap['complete']: raise ProgressError('Goals finished but full-route audit incomplete')
        self.state['status']='completed';self.event('Full loop completed and stopped at start')

    def course_zone(self, index):
        route=self.config['route'];s=self.points[index]['route_s_m']
        # Keep separate gaps separate: the painted ramp between them must still
        # require lane observations. A 3 m approach/exit buffer accounts for the
        # forward camera losing nearby paint before the axle reaches the gap.
        return any(a-3. <= s <= b+3. for a,b,mode in
                   zip(route['dense_s_m'],route['dense_s_m'][1:],route['dense_modes'])
                   if mode=='unmarked')

    def run(self):
        """Roll ordered through-poses goals without an arrival at each guide point."""
        self.spin(3)
        ready_by=time.monotonic()+20
        while not (self.through.server_is_ready() and self.origin is not None and self.xy is not None
                   and self.run_id is not None and (not self.config.get('course_sha256') or self.course_hash is not None)):
            if time.monotonic()>ready_by:
                raise RuntimeError('NavigateThroughPoses unavailable; rebuild and restart Nav2')
            self.spin(.1)
        self.healthy()
        if self.enabled: raise RuntimeError('Another autonomous task is active')
        self.publish_paths()
        self.state.update(status='running', controller_policy='rolling_three_pose_horizon')
        self.event(f'Continuous full loop: all {len(self.points)} physical checkpoints remain mandatory')
        window=None; result=None; recovered=set(); deadline=time.monotonic()+90
        previous_cursor=self.audit.next_waypoint
        while True:
            try:
                self.spin(.02);self.healthy()
                cursor=self.audit.next_waypoint
                self.state['completed_waypoints']=cursor
                self.state['active_waypoint']=min(cursor+1,len(self.points))
                if cursor!=previous_cursor:
                    self.event(f'Passed waypoint {cursor}/{len(self.points)} without an intermediate stop')
                    previous_cursor=cursor;deadline=time.monotonic()+90
                if cursor==len(self.points):
                    if result is not None and result.done():
                        if result.result().status!=4: raise RuntimeError('Nav2 final arrival failed')
                        if math.dist(self.xy,self.points[-1]['odom_xy'])>.35:
                            raise RuntimeError('Final arrival outside tolerance')
                        break
                else:
                    zone=self.course_zone(cursor)
                    end=min(cursor+3,len(self.points))
                    # The gate requires a stopped transition between painted and
                    # declared unpainted sections, not at ordinary guide points.
                    for i in range(cursor+1,end):
                        if self.course_zone(i)!=zone: end=i;break
                        # Sparse goals must not send the planner beyond currently
                        # observed terrain. Extend the horizon as the robot moves.
                        if math.dist(self.xy,self.points[i]['odom_xy'])>8.5: end=i;break
                    wanted=(cursor,end)
                    if wanted!=window:
                        zone_name='unmarked' if zone else 'painted'
                        if self.state.get('zone')!=zone_name:
                            self.stop();self.service(self.zone,zone)
                            self.state['zone']=zone_name
                        goal=NavigateThroughPoses.Goal()
                        for point in self.points[cursor:end]:
                            x,y,_=self.frame.to_enu(point['latitude'],point['longitude'],point['altitude'])
                            if math.dist((x,y),point['odom_xy'])>.001: raise ValueError('Waypoint geodesy mismatch')
                            pose=PoseStamped();pose.header.frame_id='odom'
                            pose.pose.position.x=x;pose.pose.position.y=y
                            pose.pose.orientation.z=math.sin(point['yaw']/2)
                            pose.pose.orientation.w=math.cos(point['yaw']/2)
                            goal.poses.append(pose)
                        self.approach_target=tuple(self.points[end-1]['odom_xy'])
                        self.spin(.03)
                        # Same action/BT preemption preserves FollowPath. Never
                        # cancel or toggle the command gate at interior points.
                        handle=self.wait(self.through.send_goal_async(goal),5,True)
                        if not handle.accepted: raise RuntimeError('Nav2 rejected rolling horizon')
                        self.handle=handle;result=handle.get_result_async();window=wanted
                        self.state['active_horizon']=[cursor+1,end]
                        if not self.armed:
                            self.service(self.gate,True);self.spin(.1);self.armed=True
                            self.healthy()
                    elif result is not None and result.done():
                        status=result.result().status
                        if status!=4: raise RuntimeError(f'Nav2 action failed: {status}')
                        # A preemption can coincide with the old FollowPath
                        # finishing before its replacement path is installed.
                        # Reissue the still-unvisited goal; the physical audit
                        # and unchanged 90 s deadline remain authoritative.
                        window=None;result=None
                if time.monotonic()>deadline: raise RuntimeError('No ordered checkpoint progress for 90 seconds')
            except ProgressError: raise
            except RuntimeError as exc:
                self.stop();window=None;result=None
                if self.canceled: raise
                cursor=self.audit.next_waypoint
                if str(exc).startswith('Nav2 action failed') and cursor not in recovered:
                    recovered.add(cursor)
                    try:
                        self.recover();deadline=time.monotonic()+90;continue
                    except RuntimeError as recovery_error:
                        self.stop();self.event('Recovery stopped: '+str(recovery_error))
                self.state['status']='paused';self.resume_requested=False
                self.event('Paused at same ordered checkpoint: '+str(exc))
                while not self.resume_requested:
                    self.spin(.1)
                    if self.audit_error: raise ProgressError(self.audit_error)
                self.state['status']='running';deadline=time.monotonic()+90
        self.stop();self.service(self.zone,False)
        if not self.audit.snapshot()['complete']: raise ProgressError('Full-route audit incomplete')
        self.state['status']='completed';self.event('Full loop completed and stopped at start')


def main():
    global MISSION, REPORT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resume',action='store_true',help='Continue saved incomplete run at same stationary pose; never skip failed waypoint')
    parser.add_argument('--mission',type=Path,default=MISSION)
    parser.add_argument('--report',type=Path,default=REPORT)
    args=parser.parse_args()
    MISSION=args.mission.resolve();REPORT=args.report.resolve()
    lock=(ROOT/'artifacts/session/full-course.lock').open('w')
    try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: raise RuntimeError('A full-course mission is already running')
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    m=Mission(resume=args.resume)
    try: m.run()
    except (Exception, KeyboardInterrupt) as exc:
        m.state['status']='failed';m.event(str(exc));raise
    finally:
        m.canceled=False
        try: m.stop();m.service(m.zone,False)
        except Exception as exc: m.event('Cleanup: '+str(exc))
        m.save();m.node.destroy_node();rclpy.shutdown()

if __name__=='__main__': main()
