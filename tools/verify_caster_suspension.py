#!/usr/bin/env python3
"""Bounded manual suspension bench test; no resets or autonomy commands."""
import argparse
from collections import Counter, OrderedDict
import json
import math
from pathlib import Path
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data, QoSProfile, DurabilityPolicy
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from tf2_msgs.msg import TFMessage
from verify_terrain_body import height, stamp, angles


class Verifier(Node):
    def __init__(self, speed):
        super().__init__('verify_caster_suspension')
        self.speed=speed; self.errors=Counter(); self.count=0
        self.cache={k:OrderedDict() for k in ('odom','body','joints','state')}
        self.tf_cache=OrderedDict(); self.tf_expected=OrderedDict(); self.tf_counts=Counter()
        self.create_subscription(TFMessage,'/tf',self.dynamic,qos_profile_sensor_data)
        self.latest=None; self.last_wall=None; self.previous=None; self.ready=False
        self.maximum=dict(asymmetry_m=0., compression_m=0., axle_speed_mps=0., geometry_error_m=0.)
        self.min_pitch=0.; self.max_pitch=0.; self.settled_since=None
        self.pub=self.create_publisher(Twist,'/cmd_vel/teleop',10)
        for key,typ,topic in [('odom',Odometry,'/odom'),('body',TransformStamped,'/sim/body_transform'),
                              ('joints',JointState,'/joint_states'),('state',JointState,'/sim/suspension_state')]:
            self.create_subscription(typ,topic,lambda m,k=key:self.receive(k,m),qos_profile_sensor_data)
        self.create_subscription(TFMessage,'/tf_static',self.static,
            QoSProfile(depth=100,durability=DurabilityPolicy.TRANSIENT_LOCAL))

    def static(self,msg):
        if any(t.child_frame_id.lstrip('/') in ('base_link','left_caster_suspension_link','right_caster_suspension_link') for t in msg.transforms):
            self.errors['static_base_link']+=1

    def dynamic(self,msg):
        for transform in msg.transforms:
            if transform.child_frame_id in ('left_caster_suspension_link','right_caster_suspension_link'):
                key=(stamp(transform),transform.child_frame_id)
                self.tf_cache[key]=transform
                while len(self.tf_cache)>128:self.tf_cache.popitem(last=False)
                self.compare_tf(key)

    def compare_tf(self,key):
        if key not in self.tf_cache or key not in self.tf_expected:return
        transform=self.tf_cache.pop(key); displacement=self.tf_expected.pop(key)
        side='left' if key[1].startswith('left') else 'right'
        t=transform.transform.translation; q=transform.transform.rotation
        expected=(-.52775,.24612 if side=='left' else -.24612,-.03635+displacement)
        actual=(t.x,t.y,t.z)
        if (transform.header.frame_id!='base_link' or not all(map(math.isfinite,actual+(q.x,q.y,q.z,q.w)))
            or max(abs(a-b) for a,b in zip(actual,expected))>.001
            or max(abs(q.x),abs(q.y),abs(q.z),abs(abs(q.w)-1))>1e-5):
            self.errors['dynamic_slider_tf_mismatch']+=1
        else:self.tf_counts[side]+=1

    def command(self,v):
        m=Twist();m.linear.x=v;self.pub.publish(m)

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
            bump=.025 if .6<=rear_x<=1.4 else 0.
            # Avoid the discontinuous strip edges where float/raycast rounding can choose either surface.
            if min(abs(rear_x-.6),abs(rear_x-1.4))>.002:
                if max(abs(left-(required+bump-h)),abs(right-(required-h)))>.001:
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
    parser.add_argument('--report',type=Path,default=Path(__file__).resolve().parents[1]/'artifacts/checks/caster-suspension-live.json')
    args=parser.parse_args()
    if not math.isfinite(args.speed) or not .1<=args.speed<=2.2:parser.error('--speed must be 0.1..2.2 m/s')
    rclpy.init();node=Verifier(args.speed);started=time.monotonic();finished=False
    try:
        while not node.ready and not node.errors and time.monotonic()-started<10:rclpy.spin_once(node,timeout_sec=.05)
        if not node.ready:node.errors['preflight_timeout']+=1
        if not node.errors:
            began=time.monotonic();next_send=began
            while time.monotonic()-began<55 and not node.errors:
                now=time.monotonic()
                if now-node.last_wall>.5:node.errors['fresh_join_lost']+=1;break
                if node.latest['x']>=11:finished=True;break
                if now>=next_send:node.command(args.speed);next_send=now+.05
                rclpy.spin_once(node,timeout_sec=.01)
    except KeyboardInterrupt:node.errors['interrupted']+=1
    except Exception as exc:node.errors['runtime: '+str(exc)]+=1
    finally:
        deadline=time.monotonic()+2;next_send=0.
        while time.monotonic()<deadline:
            if time.monotonic()>=next_send:node.command(0.);next_send=time.monotonic()+.05
            rclpy.spin_once(node,timeout_sec=.01)
        checks=dict(dynamic_tf_50=sum(node.tf_counts.values())>=50, left_tf_seen=node.tf_counts['left']>0, right_tf_seen=node.tf_counts['right']>0, finished=finished,matched_100=node.count>=100,asymmetric_bump=node.maximum['asymmetry_m']>.005,
            transient_compression=node.maximum['compression_m']>.005,ascended=node.min_pitch<-.08,
            descended=node.max_pitch>.08,final_settled=node.settled_since is not None and time.monotonic()-node.settled_since>=.3)
        for k,v in checks.items():
            if not v:node.errors[k]+=1
        result=dict(status='passed' if not node.errors else 'failed',requested_speed_mps=args.speed,checks=checks,
            errors=dict(node.errors),matched_pairs=node.count,dynamic_tf_comparisons=dict(node.tf_counts),maximum=node.maximum,final=node.latest,
            duration_wall_s=time.monotonic()-started,
            limitations='Analytic bench and diagnostic/joint consistency, not physical spring calibration or contact forces. Slider TF is compared at exact joint stamps with bounded 128-entry caches.')
        args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2));node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
    return 0 if result['status']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
