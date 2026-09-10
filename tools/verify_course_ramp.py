#!/usr/bin/env python3
"""Bounded manual course-ramp consistency test; no resets or autonomous commands."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import re
import time

import rclpy
from rclpy.signals import SignalHandlerOptions
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, LaserScan
from std_msgs.msg import String, Bool
from verify_caster_suspension import Verifier as SuspensionVerifier
from verify_terrain_body import height, stamp, angles


class Verifier(SuspensionVerifier):
    def __init__(self, speed):
        super().__init__(speed)
        self.maximum['axle_height_m']=0.
        self.sensor_counts=Counter();self.sensor_wall={};self.status_wall=None
        self.status_text=None;self.run_id=None;self.course=None;self.support_ready=False
        self.autonomy=None;self.autonomy_wall=None
        self.create_subscription(String,'/sim/status',self.status,10)
        self.create_subscription(Bool,'/sim/autonomy_enabled',self.autonomy_status,10)
        for key,kind,topic in [('scan',LaserScan,'/scan'),('rgb',Image,'/camera/color/image_raw'),
                               ('depth',Image,'/camera/depth/image_raw')]:
            self.create_subscription(kind,topic,lambda m,k=key:self.sensor(k,m),qos_profile_sensor_data)

    def autonomy_status(self,msg):
        self.autonomy=msg.data;self.autonomy_wall=time.monotonic()
        if msg.data:self.errors['autonomy_must_be_disabled']+=1

    def sensor(self,key,msg):
        expected='lidar_link' if key=='scan' else 'camera_color_optical_frame'
        if stamp(msg)<=0 or msg.header.frame_id!=expected:
            self.errors[key+'_frame_or_stamp']+=1;return
        if key=='scan':
            if not msg.ranges:self.errors['empty_scan']+=1;return
        elif not msg.data or (msg.encoding!=('rgb8' if key=='rgb' else '32FC1')):
            self.errors[key+'_encoding_or_empty']+=1;return
        self.sensor_counts[key]+=1;self.sensor_wall[key]=time.monotonic()

    def status(self,msg):
        self.status_text=msg.data;self.status_wall=time.monotonic()
        fields=dict(re.findall(r'(\w+)=([^\s]+)',msg.data))
        try:
            run=int(fields['run']);course=fields['course']
            self.support_ready=fields.get('terrain_support','').lower() in ('true','active','on','caster','sprung')
            if not course.startswith('seed-') or not self.support_ready:raise ValueError('variant_terrain_support_required')
            if fields.get('paused','').lower()!='false' or fields.get('estop','').lower()!='false':
                raise ValueError('paused_or_stopped')
            if int(fields.get('line_blocks','-1'))!=0:raise ValueError('lane_guard_blocked_or_missing')
            if self.run_id is not None and (run!=self.run_id or course!=self.course):raise ValueError('run_or_course_changed')
            self.run_id=run;self.course=course
        except (ValueError,KeyError) as exc:self.errors[str(exc)]+=1

    def streams_ready(self):
        now=time.monotonic()
        return (self.ready and self.last_wall is not None and now-self.last_wall<=.5
                and self.support_ready and self.status_wall is not None and now-self.status_wall<=1.5
                and all(now-self.sensor_wall.get(k,float('-inf'))<=1. for k in ('scan','rgb','depth'))
                and self.autonomy is False and self.autonomy_wall is not None and now-self.autonomy_wall<=1.)

    def receive(self,key,msg):
        ns=stamp(msg);self.cache[key][ns]=(msg,time.monotonic())
        while len(self.cache[key])>64:self.cache[key].popitem(last=False)
        if not all(ns in c for c in self.cache.values()):return
        matched={k:c.pop(ns) for k,c in self.cache.items()}
        try:
            if ns<=0 or (self.previous and ns<=self.previous[0]):raise ValueError('nonincreasing_stamp')
            if time.monotonic()-min(x[1] for x in matched.values())>.5:raise ValueError('stale_pair')
            od,body,joints,state=[matched[k][0] for k in ('odom','body','joints','state')]
            if (od.header.frame_id,od.child_frame_id)!=('odom','base_footprint'):raise ValueError('odom_frames')
            if (body.header.frame_id,body.child_frame_id)!=('base_footprint','base_link'):raise ValueError('body_frames')
            if list(state.name)!=['rear_body_height','left_compression','right_compression']:raise ValueError('diagnostic_names')
            if len(state.position)!=3 or len(state.velocity)!=3:raise ValueError('diagnostic_dimensions')
            h,left,right=state.position; rate,lr,rr=state.velocity
            pos=od.pose.pose.position; t=body.transform.translation
            roll,pitch,yaw=angles(body.transform.rotation)
            oroll,opitch,oyaw=angles(od.pose.pose.orientation)
            linear=od.twist.twist.linear
            speed=math.sqrt(linear.x**2+linear.y**2+linear.z**2)
            if not all(map(math.isfinite,[h,left,right,rate,lr,rr,pos.x,pos.y,pos.z,t.x,t.y,t.z,speed])):raise ValueError('nonfinite')
            if abs(pos.y)>.05 or abs(pos.z)>.005 or max(abs(oroll),abs(opitch),abs(oyaw),abs(roll),abs(yaw))>.005:raise ValueError('straight_datum')
            if speed>self.speed+.001:raise ValueError('odom_speed')
            axle=(pos.x,pos.y,height(pos.x))
            if self.previous:
                chord=math.dist(axle,self.previous[1])/((ns-self.previous[0])/1e9)
                self.maximum['axle_speed_mps']=max(self.maximum['axle_speed_mps'],chord)
                if chord>self.speed+.002:raise ValueError('axle_3d_speed')
            if self.previous and (ns-self.previous[0])/1e9>.5:raise ValueError('join_gap')
            self.previous=(ns,axle)
            if max(abs(left),abs(right))>.0401:raise ValueError('travel_limit')
            expected_pitch=math.atan(h/.85)
            if abs(pitch-expected_pitch)>.005:raise ValueError('rear_height_pitch')
            expected_x=-.25591*math.cos(pitch)+.30385548*math.sin(pitch)
            expected_z=height(pos.x)+.25591*math.sin(pitch)+.30385548*math.cos(pitch)
            err=max(abs(t.x-expected_x),abs(t.y),abs(t.z-expected_z))
            self.maximum['geometry_error_m']=max(self.maximum['geometry_error_m'],err)
            if err>.01:raise ValueError('body_offset')
            rear_x=pos.x-.85
            required=height(rear_x)-height(pos.x)
            if max(abs(left-(required-h)),abs(right-(required-h)))>.001:
                raise ValueError('support_compression_geometry')
            named=dict(zip(joints.name,joints.position))
            up_y=math.cos(pitch)
            for name,value in [('left_caster_suspension_joint',left),('right_caster_suspension_joint',right)]:
                actual=named[name]
                if not math.isfinite(actual) or abs(actual-value/up_y)>.001:raise ValueError('prismatic_joint_projection')
            for side in ('left','right'):
                tfkey=(ns,side+'_caster_suspension_link')
                self.tf_expected[tfkey]=named[side+'_caster_suspension_joint']
                self.compare_tf(tfkey)
            while len(self.tf_expected)>128:self.tf_expected.popitem(last=False)
            self.maximum['asymmetry_m']=max(self.maximum['asymmetry_m'],abs(left-right))
            self.maximum['compression_m']=max(self.maximum['compression_m'],abs(left),abs(right))
            self.min_pitch=min(self.min_pitch,pitch);self.max_pitch=max(self.max_pitch,pitch)
            self.maximum['axle_height_m']=max(self.maximum['axle_height_m'], t.z-.25591*math.sin(pitch)-.30385548*math.cos(pitch))
            self.count+=1;self.last_wall=time.monotonic()
            self.latest=dict(x=pos.x,stamp_ns=ns,rear_body_height=h,compression=[left,right],velocity=list(state.velocity),pitch=pitch)
            if pos.x>=11 and max(abs(h),abs(left),abs(right))<.002 and max(abs(rate),abs(lr),abs(rr))<.01:
                if self.settled_since is None:self.settled_since=time.monotonic()
            else:self.settled_since=None
            if not self.ready:
                if abs(pos.x)>.05 or speed>.01 or max(abs(h),abs(left),abs(right))>.002:raise ValueError('requires_flat_stationary_origin')
                self.ready=True
        except (ValueError,KeyError,OverflowError) as exc:self.errors[str(exc)]+=1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--speed',type=float,default=.6)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    if not math.isfinite(args.speed) or not .1<=args.speed<=2.2:parser.error('--speed must be 0.1..2.2 m/s')
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node=Verifier(args.speed);started=time.monotonic();finished=False;commanded=False
    try:
        while not node.streams_ready() and not node.errors and time.monotonic()-started<10:
            rclpy.spin_once(node,timeout_sec=.05)
        if not node.streams_ready():node.errors['preflight_not_ready']+=1
        # Publisher graph check is supplemental; exclusive operator ownership remains required.
        others=[p for p in node.get_publishers_info_by_topic('/cmd_vel/teleop') if p.node_name!=node.get_name()]
        if others:node.errors['another_manual_command_publisher']+=1
        if not node.errors:
            began=time.monotonic();next_send=began
            while time.monotonic()-began<min(120.,15.+12./args.speed) and not node.errors:
                now=time.monotonic()
                if not node.streams_ready():node.errors['fresh_stream_or_support_lost']+=1;break
                if node.latest['x']>=11:finished=True;break
                if now>=next_send:
                    node.command(args.speed);commanded=True;next_send=now+.05
                rclpy.spin_once(node,timeout_sec=.01)
    except KeyboardInterrupt:node.errors['interrupted']+=1
    except Exception as exc:node.errors['runtime: '+str(exc)]+=1
    finally:
        # Do not send even a takeover-zero when preflight refused an uncertain session.
        if commanded:
            deadline=time.monotonic()+2;next_send=0.
            while time.monotonic()<deadline:
                if time.monotonic()>=next_send:node.command(0.);next_send=time.monotonic()+.05
                rclpy.spin_once(node,timeout_sec=.01)
        checks=dict(finished=finished,matched_100=node.count>=100,
            dynamic_tf_50=sum(node.tf_counts.values())>=50,
            left_tf_seen=node.tf_counts['left']>0,right_tf_seen=node.tf_counts['right']>0,
            positive_height=node.maximum['axle_height_m']>.35,
            ascended=node.min_pitch<-.08,descended=node.max_pitch>.08,
            final_settled=node.settled_since is not None and time.monotonic()-node.settled_since>=.3,
            sensor_samples=all(node.sensor_counts[k]>0 for k in ('scan','rgb','depth')),
            variant_support=node.support_ready and node.course is not None)
        for key,value in checks.items():
            if not value:node.errors[key]+=1
        result=dict(status='failed' if node.errors else 'passed',requested_speed_mps=args.speed,
            checks=checks,errors=dict(node.errors),course=node.course,run_id=node.run_id,
            matched_pairs=node.count,dynamic_tf_comparisons=dict(node.tf_counts),maximum=node.maximum,
            sensor_counts=dict(node.sensor_counts),last_sim_status=node.status_text,final=node.latest,
            commanded=commanded,duration_wall_s=time.monotonic()-started,
            limitations='Manual straight traversal only; requires exclusive command ownership. '
            'Surveyed x=2..10 ramp is verifier evidence only, never an autonomy input. '
            'Exact-stamp body/suspension/joint and slider TF consistency; no asymmetric bench bump. '
            'Sensor receipt counts do not validate perception accuracy, contact physics or autonomous ramp navigation.')
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2));node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
    return 0 if result['status']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
