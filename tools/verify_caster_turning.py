#!/usr/bin/env python3
"""Bounded manual pivot/arc experiment on the surveyed suspension ramp."""
import argparse
from collections import OrderedDict, Counter
import json
import math
from pathlib import Path
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from verify_terrain_body import height, stamp, angles


def rotate(q, v):
    # Quaternion vector rotation, independent of Unity's coordinate conversion.
    u=(q.x,q.y,q.z)
    cross=lambda a,b:(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
    uv=cross(u,v);uuv=cross(u,uv)
    return tuple(v[i]+2*(q.w*uv[i]+uuv[i]) for i in range(3))


def surface(x,y):
    z=height(x) if abs(y)<=1.5 else 0.
    if .6<=x<=1.4 and abs(y-.24612)<=.08:z=max(z,.025)
    return z


class Turning(Node):
    def __init__(self):
        super().__init__('verify_caster_turning')
        self.cache={k:OrderedDict() for k in ('odom','body','state','joints')}
        self.errors=Counter();self.count=0;self.latest=None;self.last_wall=0.;self.previous=None
        self.ready=False;self.yaw_sum=0.;self.maximum=dict(compression_m=0.,roll_rad=0.,pitch_rad=0.,geometry_error_m=0.,normal_error=0.,axle_speed_mps=0.)
        self.pivot_origin=None;self.maximum['pivot_drift_m']=0.;self.stopped_since=None
        self.previous_swivels=None;self.maximum['swivel_rate_rad_s']=0.;self.maximum['swivel_increment_rate_rad_s']=0.
        self.command=self.create_publisher(Twist,'/cmd_vel/teleop',10)
        for kind,typ,topic in [('odom',Odometry,'/odom'),('body',TransformStamped,'/sim/body_transform'),('state',JointState,'/sim/suspension_state'),('joints',JointState,'/joint_states')]:
            self.create_subscription(typ,topic,lambda m,k=kind:self.receive(k,m),qos_profile_sensor_data)

    def receive(self,kind,msg):
        ns=stamp(msg);self.cache[kind][ns]=(msg,time.monotonic())
        while len(self.cache[kind])>64:self.cache[kind].popitem(last=False)
        if not all(ns in c for c in self.cache.values()):return
        matched={k:c.pop(ns) for k,c in self.cache.items()}
        try:
            od,body,state=[matched[k][0] for k in ('odom','body','state')]
            joints=matched['joints'][0]
            if len(joints.name)!=len(joints.position) or len(joints.name)!=len(joints.velocity):raise ValueError('joint_arrays')
            indices=[joints.name.index(name) for name in ('leftCaster','rightCaster')]
            swivel_angles=[joints.position[i] for i in indices];swivel_rates=[joints.velocity[i] for i in indices]
            if not all(map(math.isfinite,swivel_angles+swivel_rates)):raise ValueError('swivel_nonfinite')
            self.maximum['swivel_rate_rad_s']=max(self.maximum['swivel_rate_rad_s'],*map(abs,swivel_rates))
            if self.previous_swivels and ns>self.previous_swivels[0]:
                dt=(ns-self.previous_swivels[0])/1e9
                rate=max(abs(a-b)/dt for a,b in zip(swivel_angles,self.previous_swivels[1]))
                self.maximum['swivel_increment_rate_rad_s']=max(self.maximum['swivel_increment_rate_rad_s'],rate)
            if max(self.maximum['swivel_rate_rad_s'],self.maximum['swivel_increment_rate_rad_s'])>4.002:raise ValueError('swivel_rate_limit')
            self.previous_swivels=(ns,swivel_angles)
            if time.monotonic()-min(v[1] for v in matched.values())>.5:raise ValueError('stale_join')
            if ns<=0 or self.previous and ns<=self.previous[0]:raise ValueError('nonincreasing_stamp')
            if (od.header.frame_id,od.child_frame_id,body.header.frame_id,body.child_frame_id)!=('odom','base_footprint','base_footprint','base_link'):raise ValueError('frames')
            if list(state.name)!=['rear_body_height','left_compression','right_compression'] or len(state.position)!=3:raise ValueError('diagnostic_schema')
            p=od.pose.pose.position;q=body.transform.rotation;t=body.transform.translation
            oroll,opitch,yaw=angles(od.pose.pose.orientation);roll,pitch,_=angles(q)
            h,left,right=state.position
            v=od.twist.twist.linear.x;w=od.twist.twist.angular.z
            if not all(map(math.isfinite,[p.x,p.y,p.z,t.x,t.y,t.z,h,left,right,v,w])):raise ValueError('nonfinite')
            if abs(p.z)>1e-6 or max(abs(oroll),abs(opitch))>1e-6:raise ValueError('footprint_not_planar')
            def point(dx,dy):return (p.x+dx*math.cos(yaw)-dy*math.sin(yaw),p.y+dx*math.sin(yaw)+dy*math.cos(yaw))
            def sample(dx,dy):return surface(*point(dx,dy))
            fl,fr=sample(0,.405255),sample(0,-.405255)
            z=(fl+fr)/2;slope_left=(fl-fr)/.81051
            expected_left=sample(-.85,.24612)-z-slope_left*.24612-h
            expected_right=sample(-.85,-.24612)-z+slope_left*.24612-h
            # Skip discontinuous strip-edge equations only; always enforce pose/travel bounds.
            def strip_edge(at):
                x,y=at;near_x=min(abs(x-.6),abs(x-1.4))<=.003;near_y=abs(abs(y-.24612)-.08)<=.003
                return near_x and abs(y-.24612)<=.083 or near_y and .597<=x<=1.403
            near_edge=any(strip_edge(point(dx,dy)) for dx,dy in [(0,.405255),(0,-.405255),(-.85,.24612),(-.85,-.24612)])
            if not near_edge:
                if max(abs(left-expected_left),abs(right-expected_right))>.001:raise ValueError('support_geometry')
            up=rotate(q,(0,0,1));normal=(h/.85,-slope_left,1.)
            size=math.sqrt(sum(v*v for v in normal));normal=tuple(v/size for v in normal)
            normal_error=math.dist(up,normal)
            offset=rotate(q,(-.25591,0,.30385548))
            error=math.dist((t.x,t.y,t.z),(offset[0],offset[1],offset[2]+z))
            self.maximum['normal_error']=max(self.maximum['normal_error'],normal_error)
            self.maximum['geometry_error_m']=max(self.maximum['geometry_error_m'],error)
            if error>.001 or normal_error>.001:raise ValueError('body_geometry')
            if up[2]<math.cos(math.radians(15))-.0001 or max(abs(left),abs(right))>.0401:raise ValueError('travel_or_slope_limit')
            axle=(p.x,p.y,z)
            if self.previous:
                dt=(ns-self.previous[0])/1e9
                speed=math.dist(axle,self.previous[1])/dt
                self.yaw_sum+=math.atan2(math.sin(yaw-self.previous[2]),math.cos(yaw-self.previous[2]))
                self.maximum['axle_speed_mps']=max(self.maximum['axle_speed_mps'],speed)
                if speed>2.202:raise ValueError('speed_cap')
            self.previous=(ns,axle,yaw)
            if self.pivot_origin is not None:
                self.maximum['pivot_drift_m']=max(self.maximum['pivot_drift_m'],math.dist(self.pivot_origin,(p.x,p.y)))
            if abs(v)<.01 and abs(w)<.01:
                if self.stopped_since is None:self.stopped_since=ns
            else:self.stopped_since=None
            self.maximum['compression_m']=max(self.maximum['compression_m'],abs(left),abs(right))
            self.maximum['roll_rad']=max(self.maximum['roll_rad'],abs(roll))
            self.maximum['pitch_rad']=max(self.maximum['pitch_rad'],abs(pitch))
            self.latest=dict(x=p.x,y=p.y,yaw=yaw,stamp_ns=ns,roll=roll,pitch=pitch,linear=v,angular=w)
            if not self.ready:
                if math.hypot(p.x,p.y)>.05:raise ValueError('requires_stationary_origin')
                if abs(od.twist.twist.linear.x)>.01 or abs(od.twist.twist.angular.z)>.01:raise ValueError('requires_stationary_origin')
                self.ready=True
            self.count+=1;self.last_wall=time.monotonic()
        except (ValueError,OverflowError) as exc:self.errors[str(exc)]+=1

    def send(self,v=0.,w=0.):
        m=Twist();m.linear.x=float(v);m.angular.z=float(w);self.command.publish(m)

    def phase(self,v,w,duration,until=None):
        start=time.monotonic();next_send=0.
        while time.monotonic()-start<duration and not self.errors:
            now=time.monotonic()
            if now-self.last_wall>.5:self.errors['fresh_join_lost']+=1;break
            if until and until():return True
            if now>=next_send:self.send(v,w);next_send=now+.05
            rclpy.spin_once(self,timeout_sec=.01)
        return not self.errors and until is None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,default=Path(__file__).resolve().parents[1]/'artifacts/checks/caster-turning-live.json')
    args=parser.parse_args();rclpy.init();node=Turning();start=time.monotonic();checks={};phases={}
    def require(name,passed):
        checks[name]=bool(passed)
        if not passed:raise ValueError('required_phase_failed: '+name)
    def arc(name,w,duration,minimum_distance):
        origin=(node.latest['x'],node.latest['y']);begin=node.yaw_sum
        completed=node.phase(.4,w,duration)
        distance=math.dist(origin,(node.latest['x'],node.latest['y']));angle=node.yaw_sum-begin
        phases[name]=dict(distance_m=distance,yaw_change_rad=angle)
        require(name,completed and distance>=minimum_distance and angle*math.copysign(1,w)>=.15)
    try:
        while not node.ready and not node.errors and time.monotonic()-start<10:rclpy.spin_once(node,timeout_sec=.05)
        if not node.ready:node.errors['preflight_timeout']+=1
        if not node.errors:
            require('reached_ramp',node.phase(.6,0,12,lambda:node.latest['x']>=3.4))
            require('stopped_on_ramp',node.phase(0,0,1.5) and node.stopped_since is not None
                and node.latest['stamp_ns']-node.stopped_since>=300_000_000)
            origin=(node.latest['x'],node.latest['y']);begin_yaw=node.yaw_sum
            node.pivot_origin=origin
            require('full_pivot',node.phase(0,.6,16,lambda:node.yaw_sum-begin_yaw>=2*math.pi))
            require('pivot_stopped',node.phase(0,0,1.) and node.stopped_since is not None
                and node.latest['stamp_ns']-node.stopped_since>=300_000_000)
            phases['pivot']=dict(angle_rad=node.yaw_sum-begin_yaw,max_drift_m=node.maximum['pivot_drift_m'])
            require('stationary_pivot_axle',node.maximum['pivot_drift_m']<.01)
            node.pivot_origin=None
            arc('left_arc',.25,1.5,.25)
            arc('right_arc',-.25,3.,.6)
            arc('return_arc',.25,1.5,.25)
    except KeyboardInterrupt:node.errors['interrupted']+=1
    except Exception as exc:node.errors['runtime: '+str(exc)]+=1
    finally:
        deadline=time.monotonic()+2.;next_send=0.
        while time.monotonic()<deadline:
            if time.monotonic()>=next_send:node.send();next_send=time.monotonic()+.05
            rclpy.spin_once(node,timeout_sec=.01)
        checks.update(enough_samples=node.count>=300,roll_exercised=node.maximum['roll_rad']>.08,pitch_exercised=node.maximum['pitch_rad']>.08,
            swivel_exercised=node.maximum['swivel_rate_rad_s']>1.)
        for name,passed in checks.items():
            if not passed:node.errors[name]+=1
        require_stopped=node.stopped_since is not None and node.latest['stamp_ns']-node.stopped_since>=300_000_000
        checks['final_stopped']=require_stopped
        if not require_stopped:node.errors['final_stopped']+=1
        result=dict(status='passed' if not node.errors else 'failed',checks=checks,phases=phases,errors=dict(node.errors),samples=node.count,maximum=node.maximum,final=node.latest,duration_wall_s=time.monotonic()-start,
            limitations='Manual surveyed support geometry and bounded pivot/arcs. Not contact physics, complete autonomy or calibrated suspension.')
        args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
        node.destroy_node();rclpy.shutdown()
    return 0 if result['status']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
