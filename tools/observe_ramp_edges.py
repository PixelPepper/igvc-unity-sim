#!/usr/bin/env python3
"""Read-only surveyed ramp-edge observations; counts are not autonomous pass criteria."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import time
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import String
from nav_msgs.msg import Odometry


def xyz(msg):
    fields={f.name:f for f in msg.fields}
    if msg.header.frame_id!='odom':raise ValueError('frame_not_odom')
    for k in ('x','y','z'):
        f=fields[k]
        if f.datatype!=7 or f.count!=1 or f.offset+4>msg.point_step:raise ValueError('xyz_fields')
    if msg.row_step<msg.width*msg.point_step or len(msg.data)!=msg.row_step*msg.height:raise ValueError('cloud_buffer')
    if not msg.width or not msg.height:return np.empty((0,3))
    dtype=np.dtype(dict(names=['x','y','z'],formats=[('>f4' if msg.is_bigendian else '<f4')]*3,
        offsets=[fields[k].offset for k in ('x','y','z')],itemsize=msg.point_step))
    values=np.ndarray((msg.height,msg.width),dtype=dtype,buffer=msg.data,strides=(msg.row_step,msg.point_step))
    return np.column_stack([values[k].ravel() for k in ('x','y','z')])


def height(x):return .4*np.minimum(1.,np.minimum((x-2)/3,(10-x)/3))


class Observer(Node):
    def __init__(self):
        super().__init__('observe_ramp_edges')
        self.started=time.monotonic();self.streams={};self.counts=Counter();self.reasons=Counter();self.errors=Counter()
        self.hist_xy=np.zeros(10001,dtype=np.int64);self.hist_z=np.zeros(10001,dtype=np.int64)
        self.max_xy=0.;self.max_z=0.;self.odom_first=None;self.odom_last=None
        self.create_subscription(PointCloud2,'/perception/lanes/points',lambda m:self.cloud('lanes',m),qos_profile_sensor_data)
        self.create_subscription(PointCloud2,'/perception/depth/obstacles',lambda m:self.cloud('obstacles',m),qos_profile_sensor_data)
        self.create_subscription(String,'/perception/depth/status',self.status,10)
        self.create_subscription(Odometry,'/odom',self.odom,qos_profile_sensor_data)

    def record(self,key):
        now=time.monotonic();v=self.streams.setdefault(key,dict(count=0,last=None,max_gap_s=0.,first_elapsed_s=now-self.started))
        if v['last'] is not None:v['max_gap_s']=max(v['max_gap_s'],now-v['last'])
        v['last']=now;v['count']+=1

    def odom(self,msg):
        self.record('odom');p=msg.pose.pose.position
        if not all(map(math.isfinite,(p.x,p.y))):self.errors['nonfinite_odom']+=1;return
        self.odom_last=[p.x,p.y]
        if self.odom_first is None:self.odom_first=self.odom_last

    def status(self,msg):
        self.record('depth_status')
        try:
            d=json.loads(msg.data)
            if not isinstance(d,dict):raise ValueError('status_not_object')
            if d.get('valid') is True:self.counts['valid_depth_fits']+=1
            else:
                self.counts['invalid_depth_fits']+=1
                self.reasons[str(d.get('reason','unspecified'))]+=1
        except (ValueError,TypeError) as exc:self.errors[str(exc)]+=1

    def cloud(self,key,msg):
        self.record(key)
        try:
            points=xyz(msg);finite=np.isfinite(points).all(axis=1)
            self.counts[key+'_nonfinite_points']+=int((~finite).sum());points=points[finite]
            self.counts[key+'_finite_points']+=len(points)
            x,y,z=points.T
            if key=='lanes':
                selected=(x>=2.2)&(x<=9.8)&(np.abs(y)>=1.2)&(np.abs(y)<=1.7)
                x,y,z=x[selected],y[selected],z[selected]
                self.counts['left_lane_samples']+=int((y>0).sum())
                self.counts['right_lane_samples']+=int((y<0).sum())
                if len(x):
                    ex=np.abs(np.abs(y)-1.44);ez=np.abs(z-height(x))
                    self.max_xy=max(self.max_xy,float(ex.max()));self.max_z=max(self.max_z,float(ez.max()))
                    # Bounded histograms give conservative p95 upper bins at 1 mm resolution.
                    self.hist_xy+=np.bincount(np.minimum(np.ceil(ex*1000).astype(int),10000),minlength=10001)
                    self.hist_z+=np.bincount(np.minimum(np.ceil(ez*1000).astype(int),10000),minlength=10001)
            else:
                selected=(x>=2.1)&(x<=9.9)&(np.abs(y)<1.4)&(np.abs(x-5)>.06)&(np.abs(x-7)>.06)
                self.counts['surveyed_obstacle_points']+=int(selected.sum())
                self.counts['ground_false_observations']+=int((np.abs(z[selected]-height(x[selected]))<.035).sum())
        except (ValueError,KeyError,TypeError) as exc:self.errors[key+': '+str(exc)]+=1


def percentile(hist):
    total=int(hist.sum())
    return None if not total else float(np.searchsorted(np.cumsum(hist),math.ceil(total*.95)))/1000


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration',type=float,default=30)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    if not math.isfinite(args.duration) or not 1<=args.duration<=120:parser.error('--duration must be 1..120 seconds')
    rclpy.init();node=Observer();interrupted=False
    try:
        while time.monotonic()-node.started<args.duration:rclpy.spin_once(node,timeout_sec=.05)
    except KeyboardInterrupt:interrupted=True
    finally:
        now=time.monotonic()
        for v in node.streams.values():
            v['last_age_s']=now-v.pop('last');v['max_gap_including_tail_s']=max(v['max_gap_s'],v['last_age_s'])
        result=dict(status='observed',interrupted=interrupted,duration_wall_s=now-node.started,
            counts=dict(node.counts),streams=node.streams,invalid_fit_reasons=dict(node.reasons),decode_errors=dict(node.errors),
            missing_streams=[k for k in ('lanes','obstacles','depth_status','odom') if k not in node.streams],
            lane_error_m=dict(xy_max=node.max_xy if node.hist_xy.sum() else None,xy_p95_upper=percentile(node.hist_xy),
                              z_max=node.max_z if node.hist_z.sum() else None,z_p95_upper=percentile(node.hist_z)),
            odom_first=node.odom_first,odom_last=node.odom_last,
            limitations='Known ramp geometry only in this observer, not autonomy. Repeated samples, not distinct points. '
            'Lane metrics include every return inside the stated survey region, without semantic identity assertions. '
            'Paint surface offset is not subtracted. p95 uses 1 mm upper bins, overflow capped at 10 m. '
            'Receipt-time gaps and latest odometry are not acquisition-time causal proof; no pass assertion.')
        args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2));node.destroy_node()
        if rclpy.ok():rclpy.shutdown()


if __name__=='__main__':main()
