#!/usr/bin/env python3
"""Bounded manual caster swivel validation on a fresh flat drive pad; no reset."""
import argparse
from collections import Counter, OrderedDict
import json
import math
from pathlib import Path
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from tf2_msgs.msg import TFMessage
from verify_terrain_body import stamp, angles


def wrap(x):return math.atan2(math.sin(x),math.cos(x))


class Swivel(Node):
    def __init__(self):
        super().__init__('verify_caster_swivel')
        self.pub=self.create_publisher(Twist,'/cmd_vel/teleop',10)
        self.cache={k:OrderedDict() for k in ('odom','joints')}
        self.tfs=OrderedDict();self.expected=OrderedDict();self.tf_counts=Counter()
        self.errors=Counter();self.count=0;self.latest=None;self.previous=None;self.last_wall=0.
        self.ready=False;self.progress=0.;self.yaw_sum=0.;self.distance=0.;self.hold=None;self.hold_samples=0
        self.max_rate=0.;self.max_increment_rate=0.;self.max_hold_error=0.;self.max_tf_error=0.
        self.create_subscription(Odometry,'/odom',lambda m:self.receive('odom',m),qos_profile_sensor_data)
        self.create_subscription(JointState,'/joint_states',lambda m:self.receive('joints',m),qos_profile_sensor_data)
        self.create_subscription(TFMessage,'/tf',self.tf,qos_profile_sensor_data)

    def send(self,v=0.,w=0.):
        msg=Twist();msg.linear.x=v;msg.angular.z=w;self.pub.publish(msg)

    def tf(self,msg):
        for t in msg.transforms:
            if t.child_frame_id in ('left_caster','right_caster'):
                key=(stamp(t),t.child_frame_id);self.tfs[key]=t
                while len(self.tfs)>128:self.tfs.popitem(last=False)
                self.compare(key)

    def compare(self,key):
        if key not in self.tfs or key not in self.expected:return
        t=self.tfs.pop(key);expected=self.expected.pop(key)
        side='left' if key[1]=='left_caster' else 'right'
        try:
            roll,pitch,yaw=angles(t.transform.rotation);p=t.transform.translation
            if not all(map(math.isfinite,[p.x,p.y,p.z])):raise ValueError('nonfinite_tf')
            error=abs(wrap(yaw-expected));self.max_tf_error=max(self.max_tf_error,error)
            if t.header.frame_id!=side+'_caster_suspension_link' or max(abs(p.x),abs(p.y),abs(p.z))>1e-5 or max(abs(roll),abs(pitch),error)>.001:
                raise ValueError('caster_tf_mismatch')
            self.tf_counts[side]+=1
        except ValueError as exc:self.errors[str(exc)]+=1

    def receive(self,kind,msg):
        ns=stamp(msg);self.cache[kind][ns]=(msg,time.monotonic())
        while len(self.cache[kind])>64:self.cache[kind].popitem(last=False)
        if not all(ns in c for c in self.cache.values()):return
        od,oa=self.cache['odom'].pop(ns);js,ja=self.cache['joints'].pop(ns)
        try:
            if ns<=0 or self.previous and ns<=self.previous['stamp']:raise ValueError('nonincreasing_stamp')
            if time.monotonic()-min(oa,ja)>.5:raise ValueError('stale_pair')
            if (od.header.frame_id,od.child_frame_id)!=('odom','base_footprint'):raise ValueError('odom_frames')
            p=od.pose.pose.position;roll,pitch,yaw=angles(od.pose.pose.orientation)
            v=od.twist.twist.linear.x;w=od.twist.twist.angular.z
            if len(js.position)!=len(js.name) or len(js.velocity)!=len(js.name):raise ValueError('joint_arrays')
            indices=[js.name.index(side+'Caster') for side in ('left','right')]
            q=[js.position[i] for i in indices];rates=[js.velocity[i] for i in indices]
            if not all(map(math.isfinite,[p.x,p.y,p.z,v,w]+q+rates)):raise ValueError('nonfinite')
            if max(abs(roll),abs(pitch),abs(p.z))>.005:raise ValueError('not_flat')
            self.max_rate=max(self.max_rate,*map(abs,rates))
            if self.max_rate>4.001:raise ValueError('joint_velocity_limit')
            current=dict(stamp=ns,x=p.x,y=p.y,yaw=yaw,v=v,w=w,q=q)
            if self.previous:
                old=self.previous;dt=(ns-old['stamp'])/1e9
                if dt>.5:raise ValueError('stamp_gap')
                dx=p.x-old['x'];dy=p.y-old['y']
                self.progress+=dx*math.cos(old['yaw'])+dy*math.sin(old['yaw'])
                self.distance+=math.hypot(dx,dy);self.yaw_sum+=wrap(yaw-old['yaw'])
                rate=max(abs(a-b)/dt for a,b in zip(q,old['q']))
                self.max_increment_rate=max(self.max_increment_rate,rate)
                if rate>4.002:raise ValueError('continuous_angle_increment_limit')
            if abs(v)<.005 and abs(w)<.005:
                if self.hold is None:self.hold=(ns,list(q))
                elif ns-self.hold[0]>=300_000_000:
                    error=max(abs(a-b) for a,b in zip(q,self.hold[1]));self.max_hold_error=max(self.max_hold_error,error)
                    if error>.001:raise ValueError('stopped_angles_changed')
                    self.hold_samples+=1
            else:self.hold=None
            for side,angle in zip(('left','right'),q):
                key=(ns,side+'_caster');self.expected[key]=angle;self.compare(key)
            while len(self.expected)>128:self.expected.popitem(last=False)
            if not self.ready:
                if math.hypot(p.x,p.y)>.05 or max(abs(v),abs(w))>.01 or max(map(abs,q))>.01:raise ValueError('requires_fresh_stationary_origin')
                self.ready=True
            self.previous=current;self.latest=current;self.count+=1;self.last_wall=time.monotonic()
        except (ValueError,KeyError,OverflowError) as exc:self.errors[str(exc)]+=1

    def phase(self,v,w,duration):
        began=time.monotonic();next_send=0.;tail=[]
        while time.monotonic()-began<duration:
            if self.errors:raise ValueError('observation_failed')
            if time.monotonic()-self.last_wall>.5:raise ValueError('fresh_join_lost')
            now=time.monotonic()
            if now>=next_send:self.send(v,w);next_send=now+.05
            rclpy.spin_once(self,timeout_sec=.01)
            if now-began>duration-.35 and self.latest:tail.append(self.latest.copy())
        return tail


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,default=Path(__file__).resolve().parents[1]/'artifacts/checks/caster-swivel-live.json')
    args=parser.parse_args();rclpy.init();node=Swivel();started=time.monotonic();checks={};phases={}
    def require(name,value):
        checks[name]=bool(value)
        if not value:raise ValueError('failed: '+name)
    def moving(name,v,w,duration):
        before=(node.progress,node.yaw_sum,node.distance)
        tail=node.phase(v,w,duration)
        progress=node.progress-before[0];yaw=node.yaw_sum-before[1];distance=node.distance-before[2]
        errors=[]
        for row in tail:
            for side,y in enumerate((.24612,-.24612)):
                vx=row['v']-row['w']*y;vy=row['w']*(-.78366)
                if math.hypot(vx,vy)<.005:errors.append(math.inf)
                else:errors.append(abs(wrap(row['q'][side]-math.atan2(vy,vx))))
        phases[name]=dict(signed_progress_m=progress,yaw_change_rad=yaw,distance_m=distance,max_tail_target_error_rad=max(errors,default=None))
        require(name+'_alignment',bool(errors) and max(errors)<.1)
        if name=='forward':require('forward_advancement',progress>.6)
        elif name=='reverse':
            require('reverse_advancement',progress<-.5)
            require('reverse_pi',all(abs(abs(wrap(a))-math.pi)<.1 for a in node.latest['q']))
        elif name=='pivot':
            require('pivot_measured',yaw>1.)
            require('pivot_distinct',abs(wrap(node.latest['q'][0]-node.latest['q'][1]))>.3)
        else:require('arc_measured',distance>.7 and yaw<-.4)
    def stop(name):
        node.phase(0.,0.,1.)
        require(name,node.hold is not None and node.latest['stamp']-node.hold[0]>=300_000_000)
    try:
        while not node.ready and not node.errors and time.monotonic()-started<10:rclpy.spin_once(node,timeout_sec=.05)
        require('preflight',node.ready and not node.errors)
        for name,v,w,duration in [('forward',.6,0.,2.),('reverse',-.3,0.,3.5),('pivot',0.,.6,3.),('arc',.4,-.25,3.)]:
            moving(name,v,w,duration);stop(name+'_stopped')
    except KeyboardInterrupt:node.errors['interrupted']+=1
    except Exception as exc:node.errors[str(exc)]+=1
    finally:
        deadline=time.monotonic()+2.;next_send=0.
        while time.monotonic()<deadline:
            if time.monotonic()>=next_send:node.send();next_send=time.monotonic()+.05
            rclpy.spin_once(node,timeout_sec=.01)
        checks['tf_50_each_side']=all(node.tf_counts[s]>=50 for s in ('left','right'))
        checks['final_stopped']=node.hold is not None and node.latest['stamp']-node.hold[0]>=300_000_000
        checks['hold_observed']=node.hold_samples>=20
        for name,passed in checks.items():
            if not passed:node.errors[name]+=1
        result=dict(status='passed' if not node.errors else 'failed',checks=checks,errors=dict(node.errors),phases=phases,
            matched_pairs=node.count,tf_comparisons=dict(node.tf_counts),max_joint_rate=node.max_rate,
            max_continuous_increment_rate=node.max_increment_rate,max_hold_error_rad=node.max_hold_error,
            max_tf_error_rad=node.max_tf_error,final=node.latest,duration_wall_s=time.monotonic()-started,
            limitations='Flat-pad kinematic swivel consistency, not caster trail/contact forces. No reset behavior is tested.')
        args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2));node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
    return 0 if result['status']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
