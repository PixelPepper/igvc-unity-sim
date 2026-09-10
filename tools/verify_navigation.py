#!/usr/bin/env python3
"""Bounded, motion-producing integration checks for the already-running ideal course robot."""
import json
import math
from pathlib import Path
import time
import sys

import rclpy
from rclpy.action import ActionClient
from rclpy.signals import SignalHandlerOptions
from rclpy.time import Time
from geometry_msgs.msg import Twist, PoseStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
from std_srvs.srv import SetBool, Trigger
from action_msgs.srv import CancelGoal
from nav2_msgs.action import NavigateToPose, ComputePathToPose
from nav2_msgs.srv import ClearEntireCostmap
from tf2_ros import Buffer, TransformListener

REPORT = Path(__file__).resolve().parents[1] / 'artifacts/checks/navigation-live.json'
# Source scene barrel (-3.03, .3, -17.051), source spawn (-2.61,-.001,-20.57).
BARREL = (-.420, 3.519)
HEADING = math.atan2(BARREL[1], BARREL[0])
GOAL = (6 * math.cos(HEADING), 6 * math.sin(HEADING))


def yaw(q):
    return math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))


def pose(x, y, heading=0):
    p = PoseStamped(); p.header.frame_id = 'odom'
    p.pose.position.x = float(x); p.pose.position.y = float(y)
    p.pose.orientation.z = math.sin(heading/2); p.pose.orientation.w = math.cos(heading/2)
    return p


class Verify:
    def __init__(self):
        self.node = rclpy.create_node('igvc_navigation_verifier')
        self.odom = None; self.scan = None; self.output = None; self.last_odom = 0
        self.trajectory = []; self.record = False; self.last_sample = 0
        self.radius = None; self.minimum_clearance = math.inf
        self.tf = Buffer(); self.listener = TransformListener(self.tf, self.node)
        self.node.create_subscription(Odometry, '/odom', self.on_odom, 10)
        self.node.create_subscription(LaserScan, '/scan', lambda m: setattr(self, 'scan', m), 10)
        self.node.create_subscription(Twist, '/cmd_vel', lambda m: setattr(self, 'output', m), 10)
        self.nav_pub = self.node.create_publisher(Twist, '/cmd_vel/nav', 1)
        self.teleop = self.node.create_publisher(Twist, '/cmd_vel/teleop', 1)
        self.services = {
            'gate': self.node.create_client(SetBool, '/sim/set_autonomy'),
            'reset': self.node.create_client(Trigger, '/sim/reset'),
            'cancel': self.node.create_client(CancelGoal, '/navigate_to_pose/_action/cancel_goal'),
            'clear_global': self.node.create_client(ClearEntireCostmap, '/global_costmap/clear_entirely_global_costmap'),
            'clear_local': self.node.create_client(ClearEntireCostmap, '/local_costmap/clear_entirely_local_costmap'),
        }
        self.navigate = ActionClient(self.node, NavigateToPose, '/navigate_to_pose')
        self.plan = ActionClient(self.node, ComputePathToPose, '/compute_path_to_pose')
        self.report = {'status':'running', 'checks':{}, 'barrel_center_odom':BARREL, 'candidate_goal_odom':GOAL,
                       'limitations':'Ideal odometry and geometric clearance only; does not prove physical collision avoidance, lane following or hardware safety.'}

    def on_odom(self, m):
        self.odom = m; self.last_odom = time.monotonic()
        if self.record and self.last_odom-self.last_sample > .09:
            x,y = self.xy(); angle = yaw(m.pose.pose.orientation)
            self.trajectory.append([x,y,angle]); self.last_sample = self.last_odom
            if self.radius is not None:
                dx,dy = BARREL[0]-x,BARREL[1]-y
                bx = math.cos(angle)*dx+math.sin(angle)*dy
                by = -math.sin(angle)*dx+math.cos(angle)*dy
                outside = math.hypot(max(-1.1-bx,0,bx-.6),max(abs(by)-.5,0))
                clearance = outside-self.radius
                self.minimum_clearance = min(self.minimum_clearance,clearance)

    def xy(self):
        return (self.odom.pose.pose.position.x,self.odom.pose.pose.position.y)

    def stopped(self):
        return abs(self.odom.twist.twist.linear.x)<.005 and abs(self.odom.twist.twist.angular.z)<.005

    def wait(self, seconds, nav_speed=None):
        end = time.monotonic()+seconds; next_pub = 0
        while time.monotonic()<end:
            if nav_speed is not None and time.monotonic()>=next_pub:
                m=Twist();m.linear.x=nav_speed;self.nav_pub.publish(m);next_pub=time.monotonic()+.05
            rclpy.spin_once(self.node,timeout_sec=.02)

    def future(self, f, seconds):
        end=time.monotonic()+seconds
        while not f.done() and time.monotonic()<end:
            rclpy.spin_once(self.node,timeout_sec=.05)
            if self.record and (time.monotonic()-self.last_odom>1 or self.minimum_clearance < -.02):
                raise RuntimeError('Trajectory monitoring lost odometry or conservative footprint overlapped barrel')
        if not f.done():raise RuntimeError('ROS operation wall timeout')
        return f.result()

    def service(self,name,value=False):
        if not self.services[name].wait_for_service(timeout_sec=5):
            raise RuntimeError(name+' service unavailable')
        request = SetBool.Request(data=value) if name=='gate' else (Trigger.Request() if name=='reset' else CancelGoal.Request() if name=='cancel' else ClearEntireCostmap.Request())
        result=self.future(self.services[name].call_async(request),5)
        if hasattr(result,'success') and not result.success:raise RuntimeError(name+' rejected')
        return result

    def check(self,name,value):
        self.report['checks'][name]=bool(value)
        print(('PASS ' if value else 'FAIL ')+name,flush=True)
        if not value:raise AssertionError(name)

    def reset(self):
        self.record=False
        self.service('gate',False);self.service('cancel');self.wait(.6)
        self.service('reset');self.wait(.7)
        self.service('clear_global');self.service('clear_local');self.wait(2)
        if math.hypot(*self.xy())>.02 or not self.stopped():raise RuntimeError('Reset did not establish stationary origin')

    def run_goal(self,xy,heading,timeout):
        request=NavigateToPose.Goal();request.pose=pose(*xy,heading)
        handle=self.future(self.navigate.send_goal_async(request),5)
        if not handle.accepted:raise RuntimeError('Navigation goal rejected')
        self.service('gate',True)
        result=self.future(handle.get_result_async(),timeout)
        self.service('gate',False)
        return result

    def run(self):
        end=time.monotonic()+20
        while time.monotonic()<end and (self.odom is None or self.scan is None or self.output is None or not all(c.service_is_ready() for c in self.services.values()) or not self.navigate.server_is_ready() or not self.plan.server_is_ready()):
            rclpy.spin_once(self.node,timeout_sec=.1)
        if self.odom is None or self.scan is None or not all(c.service_is_ready() for c in self.services.values()) or not self.navigate.server_is_ready() or not self.plan.server_is_ready():
            raise RuntimeError('Required streams/services/actions unavailable')
        self.wait(1)
        self.reset()
        if '--adaptive' in sys.argv:
            self.adaptive()
            return
        p=self.xy();self.wait(.7,.15)
        self.check('manual_mode_ignores_nav',math.dist(p,self.xy())<.01 and self.stopped())
        self.service('gate',True);self.wait(.2)
        self.check('enable_requires_fresh_command',self.stopped())
        p=self.xy();self.wait(.8,.15)
        self.check('enabled_accepts_fresh_nav',.03<math.dist(p,self.xy())<.2)
        self.teleop.publish(Twist());self.wait(.8,.15)
        self.check('teleop_zero_latches_nav_off',self.stopped())
        p=self.xy();self.wait(.4,.15)
        self.check('continued_nav_cannot_resume',math.dist(p,self.xy())<.01)
        self.service('gate',True);self.wait(.5,.15);self.wait(.7)
        self.check('stale_nav_watchdog_stops',self.stopped())
        self.reset()
        result=self.run_goal((1.,0.),0.,25)
        self.report['nearby_goal']={'status':result.status,'final_xy':self.xy()}
        self.check('nearby_goal_succeeded',result.status==4 and math.dist(self.xy(),(1,0))<.3)
        self.reset()
        transform=self.tf.lookup_transform('odom','lidar_link',Time.from_msg(self.scan.header.stamp))
        t=transform.transform.translation;a=yaw(transform.transform.rotation)
        points=[]
        for i,r in enumerate(self.scan.ranges):
            if not math.isfinite(r):continue
            angle=a+self.scan.angle_min+i*self.scan.angle_increment
            p=(t.x+r*math.cos(angle),t.y+r*math.sin(angle))
            if math.dist(p,BARREL)<.5:points.append(p)
        self.check('known_barrel_matches_lidar',len(points)>=3)
        distances=sorted(math.dist(p,BARREL) for p in points)
        self.radius=distances[len(distances)//2]
        self.check('barrel_radius_plausible',.15<self.radius<.45)
        self.report['barrel_radius_from_scan_m']=self.radius
        request=ComputePathToPose.Goal();request.goal=pose(*GOAL,HEADING);request.planner_id='GridBased';request.use_start=False
        h=self.future(self.plan.send_goal_async(request),5)
        if not h.accepted:raise RuntimeError('ComputePath goal rejected')
        planned=self.future(h.get_result_async(),12)
        self.report['planning_status']=planned.status
        self.check('obstacle_goal_path_computed',planned.status==4 and len(planned.result.path.poses)>2)
        pp=[(p.pose.position.x,p.pose.position.y) for p in planned.result.path.poses]
        length=sum(math.dist(a,b) for a,b in zip(pp,pp[1:]))
        cross=max(abs(p[0]*math.sin(HEADING)-p[1]*math.cos(HEADING)) for p in pp)
        minimum=min(math.dist(p,BARREL) for p in pp)
        self.report['planned_path']={'xy':pp,'length_m':length,'max_offset_from_straight_m':cross,'minimum_center_distance_m':minimum}
        self.check('path_detours_straight_barrel_intersection',length<=8 and cross>self.radius+.4 and minimum>self.radius+.4)
        self.record=True;self.trajectory=[];self.minimum_clearance=math.inf
        result=self.run_goal(GOAL,HEADING,90)
        self.record=False
        self.report['obstacle_goal']={'status':result.status,'final_xy':self.xy(),'goal_error_m':math.dist(self.xy(),GOAL),'trajectory':self.trajectory,'minimum_rectangle_to_barrel_clearance_m':self.minimum_clearance}
        self.check('obstacle_goal_succeeded',result.status==4 and math.dist(self.xy(),GOAL)<.3)
        self.check('conservative_trajectory_clearance',self.minimum_clearance>=0)
        # Test cancellation on a short continuation into the same observed corridor.
        continuation=(GOAL[0]+.6*math.cos(HEADING),GOAL[1]+.6*math.sin(HEADING))
        request=NavigateToPose.Goal();request.pose=pose(*continuation,HEADING)
        h=self.future(self.navigate.send_goal_async(request),5)
        self.check('cancellation_goal_accepted',h.accepted)
        self.service('gate',True);self.wait(.4)
        canceled=self.future(h.cancel_goal_async(),5)
        self.service('gate',False);self.wait(.6)
        self.check('cancellation_stops_within_600ms',bool(canceled.goals_canceling) and self.stopped())
        self.report['status']='passed'

    def adaptive(self):
        # One authorized alternative outside the occluded shadow, testing inflation clearance.
        original=json.loads(REPORT.with_name('navigation-live-first-attempt.json').read_text())
        self.report['previous_attempt']='navigation-live-first-attempt.json'
        self.report['prior_arbitration_and_nearby_checks']={k:v for k,v in original['checks'].items() if k!='obstacle_goal_path_computed'}
        self.radius=original['barrel_radius_from_scan_m']
        goal=(-1.35,5.8);heading=math.atan2(goal[1],goal[0])
        self.report['candidate_goal_odom']=goal
        self.report['adaptive_test']='One lateral goal outside scan shadow. Straight segment intersects inflation/body clearance envelope, not the physical barrel centerline. Unknown policy unchanged.'
        failure=None
        try:
            request=ComputePathToPose.Goal();request.goal=pose(*goal,heading);request.planner_id='GridBased';request.use_start=False
            h=self.future(self.plan.send_goal_async(request),5)
            if not h.accepted:raise RuntimeError('Adaptive ComputePath rejected')
            planned=self.future(h.get_result_async(),12)
            self.report['planning']={'status':planned.status,'error_code':getattr(planned.result,'error_code',None),'error_msg':getattr(planned.result,'error_msg','')}
            self.check('observed_lateral_goal_path_computed',planned.status==4 and len(planned.result.path.poses)>2)
            pp=[(p.pose.position.x,p.pose.position.y) for p in planned.result.path.poses]
            length=sum(math.dist(a,b) for a,b in zip(pp,pp[1:]))
            direct=abs(BARREL[0]*math.sin(heading)-BARREL[1]*math.cos(heading))
            closest=min(math.dist(p,BARREL) for p in pp)
            self.report['planned_path']={'xy':pp,'length_m':length,'straight_segment_barrel_center_distance_m':direct,'path_barrel_center_minimum_m':closest}
            self.check('planner_avoids_straight_footprint_intersection',length<=8 and direct<self.radius+.5 and closest>.7 and closest>direct+.1)
            self.record=True;self.trajectory=[];self.minimum_clearance=math.inf
            result=self.run_goal(goal,heading,90)
            self.record=False
            self.report['obstacle_goal']={'status':result.status,'final_xy':self.xy(),'goal_error_m':math.dist(self.xy(),goal),'trajectory':self.trajectory,'minimum_rectangle_to_barrel_clearance_m':self.minimum_clearance}
            self.check('obstacle_goal_succeeded',result.status==4 and math.dist(self.xy(),goal)<.3)
            self.check('conservative_trajectory_clearance',self.minimum_clearance>=0)
        except Exception as exc:
            self.record=False;failure=str(exc);self.report['obstacle_test_error']=failure
        # Cancellation is independently verified even if obstacle planning/execution failed.
        self.service('gate',False);self.service('cancel');self.wait(.6)
        self.reset()
        request=NavigateToPose.Goal();request.pose=pose(1.5,0,0)
        h=self.future(self.navigate.send_goal_async(request),5)
        self.check('cancellation_goal_accepted',h.accepted)
        self.service('gate',True);self.wait(.6)
        before=self.xy()
        canceled=self.future(h.cancel_goal_async(),5)
        self.service('gate',False);self.wait(.6)
        self.report['cancellation']={'before_xy':before,'after_xy':self.xy(),'goals_canceling':len(canceled.goals_canceling),'stopped':self.stopped()}
        self.check('cancellation_stops_within_600ms',bool(canceled.goals_canceling) and self.stopped())
        if failure:raise RuntimeError(failure)
        self.report['status']='passed'

    def finish(self):
        self.record=False
        failures=[]
        for name in ['gate','cancel']:
            try:
                if self.services[name].service_is_ready():self.service(name,False)
                else:failures.append(name+' unavailable')
            except Exception as e:failures.append(name+': '+str(e))
        try:
            self.wait(.6)
            if failures or not self.stopped():raise RuntimeError('Not safely stopped; reset skipped')
            self.service('reset');self.wait(.7)
            self.service('clear_global');self.service('clear_local')
            self.report['final_reset_xy']=self.xy()
            self.report['final_manual_stopped']=self.stopped() and math.hypot(*self.xy())<.02
        except Exception as e:failures.append(str(e))
        self.report['cleanup_errors']=failures
        if failures:self.report['status']='failed'
        if self.trajectory and 'obstacle_goal' not in self.report:
            self.report['incomplete_obstacle_trajectory']=self.trajectory
            self.report['minimum_rectangle_to_barrel_clearance_m']=self.minimum_clearance if math.isfinite(self.minimum_clearance) else None
        REPORT.parent.mkdir(parents=True,exist_ok=True)
        REPORT.write_text(json.dumps(self.report,indent=2,allow_nan=False)+'\n')


def main():
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    v=Verify()
    try:v.run()
    except BaseException as e:
        v.report['status']='failed';v.report['error']=str(e);print('FAIL '+str(e),flush=True)
    finally:
        v.finish();v.node.destroy_node();rclpy.shutdown()
    print(json.dumps({'status':v.report['status'],'report':str(REPORT),'error':v.report.get('error')}),flush=True)
    return 0 if v.report['status']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
