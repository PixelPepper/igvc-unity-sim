#!/usr/bin/env python3
"""Read-only known-bench observations, never an autonomy input or pass/fail oracle."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import struct
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import String, Bool
from sensor_msgs.msg import PointCloud2
from nav_msgs.msg import Odometry


def ground(x,y):
    if abs(y)>1.5:return 0.
    if 2<x<5:return .4*(x-2)/3
    if 5<=x<=7:return .4
    if 7<x<10:return .4*(10-x)/3
    return 0.


def phase(x):
    if x is None:return 'unknown'
    if x<2:return 'flat_before'
    if x<5:return 'up'
    if x<7:return 'deck'
    if x<10:return 'down'
    return 'flat_after'


class Observer(Node):
    def __init__(self):
        super().__init__('observe_terrain_perception')
        self.started=time.monotonic();self.streams={};self.reasons=Counter();self.errors=Counter()
        self.phases={};self.examples=[];self.odom=None;self.depth_status=None
        self.plane_range={k:[None,None] for k in ('slope_deg','offset')}
        self.topics={'depth_status':'/perception/depth/status','lane_status':'/perception/lanes/status',
            'depth_healthy':'/perception/depth/healthy','lane_healthy':'/perception/lanes/healthy',
            'obstacles':'/perception/depth/obstacles','odom':'/odom'}
        for key in ('depth_status','lane_status'):
            self.create_subscription(String,self.topics[key],lambda m,k=key:self.status(k,m),10)
        for key in ('depth_healthy','lane_healthy'):
            self.create_subscription(Bool,self.topics[key],lambda m,k=key:self.health(k,m),10)
        self.create_subscription(PointCloud2,self.topics['obstacles'],self.cloud,qos_profile_sensor_data)
        self.create_subscription(Odometry,self.topics['odom'],self.odometry,qos_profile_sensor_data)

    def record(self,key):
        now=time.monotonic();s=self.streams.setdefault(key,dict(count=0,max_gap_s=0.,first_elapsed_s=now-self.started,last_wall=None,true_count=0,false_count=0))
        if s['last_wall'] is not None:s['max_gap_s']=max(s['max_gap_s'],now-s['last_wall'])
        s['last_wall']=now;s['count']+=1
        return s

    def bin(self):
        key=phase(None if self.odom is None else self.odom['x'])
        return self.phases.setdefault(key,Counter())

    def odometry(self,msg):
        self.record('odom');p=msg.pose.pose.position
        if not all(map(math.isfinite,(p.x,p.y))):self.errors['nonfinite_odom']+=1;return
        self.odom=dict(x=p.x,y=p.y,stamp_ns=msg.header.stamp.sec*10**9+msg.header.stamp.nanosec,arrival=time.monotonic())

    def health(self,key,msg):
        self.record(key)['true_count' if msg.data else 'false_count']+=1
        self.bin()[key+('_true' if msg.data else '_false')]+=1

    def status(self,key,msg):
        s=self.record(key)
        try:
            value=json.loads(msg.data)
            if not isinstance(value,dict):raise ValueError('not_object')
            valid=value.get('valid') is True
            s['true_count' if valid else 'false_count']+=1
            self.bin()[key+('_valid' if valid else '_invalid')]+=1
            if not valid:self.reasons[key+': '+str(value.get('reason','unspecified'))]+=1
            if key=='depth_status':
                self.depth_status=dict(valid=valid,stamp_ns=value.get('stamp_ns'),reason=value.get('reason'),ground=value.get('ground'))
                if valid:
                    plane=value['ground']
                    for name in self.plane_range:
                        n=float(plane[name])
                        if not math.isfinite(n):raise ValueError('nonfinite_plane')
                        lo,hi=self.plane_range[name]
                        self.plane_range[name]=[n if lo is None else min(lo,n),n if hi is None else max(hi,n)]
        except (ValueError,TypeError,KeyError) as exc:self.errors[key+': '+str(exc)]+=1

    def cloud(self,msg):
        self.record('obstacles');b=self.bin();b['clouds']+=1
        try:
            if msg.header.frame_id!='odom':raise ValueError('cloud_not_odom')
            fields={f.name:f for f in msg.fields}
            for k in ('x','y','z'):
                f=fields[k]
                if f.datatype!=7 or f.count!=1 or f.offset+4>msg.point_step:raise ValueError('cloud_fields')
            if msg.row_step<msg.width*msg.point_step or len(msg.data)!=msg.row_step*msg.height:raise ValueError('cloud_buffer')
            fmt='>f' if msg.is_bigendian else '<f'
            ns=msg.header.stamp.sec*10**9+msg.header.stamp.nanosec
            for row in range(msg.height):
                for col in range(msg.width):
                    offset=row*msg.row_step+col*msg.point_step
                    x,y,z=[struct.unpack_from(fmt,msg.data,offset+fields[k].offset)[0] for k in ('x','y','z')]
                    b['points']+=1
                    if not all(map(math.isfinite,(x,y,z))):b['nonfinite_points']+=1;continue
                    if not -8<=x<=16 or not -6<=y<=6:b['outside_survey']+=1;continue
                    if abs(abs(y)-1.5)<.06 or min(abs(x-v) for v in (2,5,7,10))<.06:
                        b['transition_excluded']+=1;continue
                    if .54<=x<=1.46 and abs(y-.24612)<=.14:b['bump_excluded']+=1;continue
                    b['surveyed_points']+=1
                    if abs(z-ground(x,y))<.035:
                        b['ground_marked_obstacle']+=1
                        if len(self.examples)<50:
                            self.examples.append(dict(stamp_ns=ns,odom_x=None if self.odom is None else self.odom['x'],
                                odom_age_s=None if self.odom is None else time.monotonic()-self.odom['arrival'],
                                point=[x,y,z],latest_depth_status=self.depth_status))
        except (ValueError,KeyError,struct.error) as exc:self.errors['cloud: '+str(exc)]+=1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration',type=float,default=45)
    parser.add_argument('--report',type=Path,default=Path(__file__).resolve().parents[1]/'artifacts/checks/terrain-perception-baseline.json')
    args=parser.parse_args()
    if not math.isfinite(args.duration) or not 1<=args.duration<=120:parser.error('--duration must be finite, 1..120 seconds')
    rclpy.init();node=Observer();interrupted=False
    try:
        while time.monotonic()-node.started<args.duration:rclpy.spin_once(node,timeout_sec=.05)
    except KeyboardInterrupt:interrupted=True
    finally:
        now=time.monotonic()
        for s in node.streams.values():
            s['last_update_age_s']=now-s.pop('last_wall')
            s['max_gap_including_tail_s']=max(s['max_gap_s'],s['last_update_age_s'])
        result=dict(status='observed',duration_wall_s=now-node.started,interrupted=interrupted,
            missing_topics=[topic for key,topic in node.topics.items() if key not in node.streams],
            streams=node.streams,invalid_reasons=dict(node.reasons),decode_errors=dict(node.errors),
            valid_plane_ranges=node.plane_range,by_odom_phase=node.phases,examples=node.examples,
            limitations='Known bench geometry is used ONLY in this read-only verifier, never autonomy. '
            'Counts are repeated point observations, not distinct obstacles. Latest received odometry assigns phase; '
            'depth status examples are receipt context, not exact-stamp causality. Transition/bump exclusions apply. '
            'No assertions or claim of semantic-ground accuracy; missing topics are reported.')
        args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:v for k,v in result.items() if k!='examples'},indent=2));node.destroy_node()
        if rclpy.ok():rclpy.shutdown()


if __name__=='__main__':main()
