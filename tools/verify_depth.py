#!/usr/bin/env python3
"""Bounded read-only depth proof. Requires ROS 2, NumPy and Pillow; sends no commands."""
import argparse
from collections import Counter, OrderedDict
import json
import math
from pathlib import Path
import time

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import Image, CameraInfo, PointCloud2
from std_msgs.msg import String
from tf2_ros import Buffer, TransformListener, TransformException

FRAME='camera_color_optical_frame'


def stamp(message):
    return message.header.stamp.sec*1_000_000_000+message.header.stamp.nanosec


def rotation(q):
    # Independent quaternion-vector rotation through the skew matrix.
    vector=np.array([q.x,q.y,q.z],dtype=float)
    skew=np.array([[0,-q.z,q.y],[q.z,0,-q.x],[-q.y,q.x,0]],dtype=float)
    if abs(float(vector@vector)+q.w*q.w-1)>1e-5:raise ValueError('nonunit_tf_rotation')
    return np.eye(3)+2*q.w*skew+2*(skew@skew)


def cloud_array(msg):
    fields={f.name:f for f in msg.fields}
    if any(k not in fields or fields[k].datatype!=7 or fields[k].count!=1 for k in ('x','y','z')):
        raise ValueError('cloud_xyz_fields')
    if msg.row_step<msg.width*msg.point_step or len(msg.data)!=msg.row_step*msg.height:
        raise ValueError('cloud_buffer')
    if any(fields[k].offset+4>msg.point_step for k in ('x','y','z')):raise ValueError('cloud_offsets')
    dtype=np.dtype(dict(names=['x','y','z'],formats=[('>f4' if msg.is_bigendian else '<f4')]*3,
                       offsets=[fields[k].offset for k in ('x','y','z')],itemsize=msg.point_step))
    rows=[np.frombuffer(msg.data,dtype=dtype,count=msg.width,offset=i*msg.row_step) for i in range(msg.height)]
    return np.concatenate([np.column_stack([r[k] for k in ('x','y','z')]) for r in rows]) if rows else np.empty((0,3))


class DepthVerifier(Node):
    def __init__(self):
        super().__init__('igvc_depth_verifier')
        self.tf=Buffer();self.listener=TransformListener(self.tf,self)
        self.started=time.monotonic();self.counts=Counter();self.errors=Counter();self.times={}
        self.cache={k:OrderedDict() for k in ('image','info','points','obstacles')}
        self.grounds=OrderedDict()
        self.first_pair_stamp=None;self.startup_unmatched=Counter()
        self.done=set();self.ground_pixels=set();self.ground_matches=0;self.ground_tested=0
        self.ground_occluded=0;self.ground_residual=[];self.pairs=0;self.cloud_matches=0
        self.finite_pixels=0;self.nan_pixels=0;self.sky_nan_pixels=0;self.latest=None
        self.positive_obstacle_points=0;self.status_reasons=Counter();self.max_points=0
        for key,typ,topic in [('image',Image,'/camera/depth/image_raw'),
                              ('info',CameraInfo,'/camera/depth/camera_info'),
                              ('points',PointCloud2,'/camera/depth/points'),
                              ('obstacles',PointCloud2,'/perception/depth/obstacles')]:
            self.create_subscription(typ,topic,lambda m,k=key:self.receive(k,m),qos_profile_sensor_data)
        self.create_subscription(String,'/perception/depth/status',self.status,10)
        self.create_timer(.04,self.process)

    def tick(self,key):
        now=time.monotonic();self.counts[key]+=1
        if key not in self.times:self.times[key]=[now,now]
        else:self.times[key][1]=now

    def status(self,msg):
        self.tick('status')
        try:
            value=json.loads(msg.data)
            if value.get('valid') is True:
                self.counts['valid_status']+=1
                if 'ground' in value:
                    self.grounds[value['stamp_ns']]=value['ground']
                    while len(self.grounds)>40:self.grounds.popitem(last=False)
            else:
                reason=value.get('reason','unspecified');self.status_reasons[reason]+=1
                if time.monotonic()-self.started>2 and reason!='no_new_pair':self.errors['processor:'+reason]+=1
        except (ValueError,TypeError):self.errors['invalid_status_json']+=1

    def receive(self,key,msg):
        self.tick(key);s=stamp(msg)
        self.cache[key][s]=(msg,time.monotonic())
        while len(self.cache[key])>40:
            old,_=self.cache[key].popitem(last=False)
            # Independent subscriptions can join on opposite sides of one
            # acquisition. Only the prefix before the first complete pair is
            # outside the observation window; later losses remain errors.
            if self.first_pair_stamp is not None and old<self.first_pair_stamp:
                self.startup_unmatched[key]+=1
                continue
            if key in ('points','obstacles') or old not in self.done:
                self.errors['unmatched_expired_'+key]+=1

    def process(self):
        common=self.cache['image'].keys() & self.cache['info'].keys()
        for s in sorted(common):
            if s in self.done:continue
            if self.first_pair_stamp is not None and s<self.first_pair_stamp:
                self.startup_unmatched['pair_before_first_tf']+=1;self.done.add(s)
                continue
            image,arrival=self.cache['image'][s];info,_=self.cache['info'][s]
            try:
                transform=self.tf.lookup_transform('odom',FRAME,Time.from_msg(image.header.stamp))
            except TransformException:
                if time.monotonic()-arrival>1 and self.first_pair_stamp is not None:
                    self.errors['acquisition_tf_unavailable']+=1;self.done.add(s)
                continue
            try:
                self.check_pair(image,info,transform)
                if self.first_pair_stamp is None:self.first_pair_stamp=s
            except (ValueError,IndexError,TypeError) as exc:self.errors[str(exc)]+=1
            self.done.add(s)
        # Clouds are produced after their source pair; only compare complete acquisitions.
        cloud_common=common & self.cache['points'].keys() & self.cache['obstacles'].keys() & self.grounds.keys()
        for s in sorted(cloud_common):
            if self.first_pair_stamp is not None and s<self.first_pair_stamp:
                self.startup_unmatched['cloud_before_first_tf']+=1
                for key in self.cache:self.cache[key].pop(s,None)
                continue
            image,arrival=self.cache['image'][s]
            try:
                transform=self.tf.lookup_transform('odom',FRAME,Time.from_msg(image.header.stamp))
                self.check_clouds(image,self.cache['info'][s][0],transform,
                                  self.cache['points'][s][0],self.cache['obstacles'][s][0],self.grounds[s])
            except TransformException:
                if time.monotonic()-arrival<1:continue
                self.errors['cloud_acquisition_tf_unavailable']+=1
            except (ValueError,IndexError,TypeError) as exc:self.errors[str(exc)]+=1
            for key in self.cache:self.cache[key].pop(s,None)

    def decode(self,image,info,transform):
        if (image.width,image.height,image.encoding)!=(320,240,'32FC1'):raise ValueError('image_format')
        if image.step<1280 or image.step%4 or len(image.data)!=image.step*240:raise ValueError('image_buffer')
        if image.header.frame_id!=FRAME or info.header.frame_id!=FRAME:raise ValueError('image_info_frame')
        if stamp(image)!=stamp(info) or stamp(transform)!=stamp(image):raise ValueError('acquisition_stamp_mismatch')
        k=np.asarray(info.k).reshape(3,3)
        if (info.width,info.height)!=(320,240) or not np.isfinite(k).all():raise ValueError('info_size_intrinsics')
        if (k[0,0]<=0 or abs(k[0,0]-k[1,1])>1e-6 or not np.allclose(k[2],[0,0,1])
                or abs(k[0,2]-159.5)>1e-6 or abs(k[1,2]-119.5)>1e-6
                or abs(k[0,1])+abs(k[1,0])>1e-9):raise ValueError('depth_intrinsics')
        if not np.allclose(np.asarray(info.r).reshape(3,3),np.eye(3)) or np.any(np.asarray(info.d)!=0):
            raise ValueError('depth_rectification')
        expected_p=np.column_stack((k,np.zeros(3)))
        if not np.allclose(np.asarray(info.p).reshape(3,4),expected_p):raise ValueError('projection_intrinsics')
        array=np.frombuffer(image.data,dtype='>f4' if image.is_bigendian else '<f4').reshape(240,image.step//4)[:,:320]
        r=rotation(transform.transform.rotation);t=transform.transform.translation
        return array,k,r,np.array([t.x,t.y,t.z])

    def check_pair(self,image,info,transform):
        array,k,r,origin=self.decode(image,info,transform)
        finite=np.isfinite(array)
        if np.isinf(array).any() or np.any(finite & ((array<.2)|(array>10))):raise ValueError('depth_range_or_inf')
        self.pairs+=1;self.finite_pixels+=int(finite.sum());self.nan_pixels+=int(np.isnan(array).sum())
        # Sky is independently identified by upward world-space rays in the top band.
        rr,cc=np.mgrid[0:60:4,0:320:4]
        rays=np.stack(((cc-k[0,2])/k[0,0],(rr-k[1,2])/k[1,1],np.ones_like(rr)),axis=-1)
        upward=(rays@r.T)[...,2]>0
        self.sky_nan_pixels+=int(np.count_nonzero(upward & np.isnan(array[rr,cc])))
        # Ground check uses camera TF and pinhole rays only; no scene or labels.
        rows,cols=np.mgrid[160:240:2,100:220:2]
        rays=np.stack(((cols-k[0,2])/k[0,0],(rows-k[1,2])/k[1,1],np.ones_like(rows)),axis=-1)
        direction=(rays@r.T)[...,2]
        expected=np.divide(-origin[2],direction,out=np.full(direction.shape,np.nan),where=direction<-.01)
        measured=array[rows,cols]
        candidate=np.isfinite(measured)&np.isfinite(expected)&(expected>=.2)&(expected<=10)
        residual=origin[2]+direction*measured
        # Closer positive-height hits can be obstacles; record them as excluded, not matches.
        occluded=candidate & (residual>.03)
        matches=candidate & (np.abs(residual)<=.03)
        self.ground_tested+=int(candidate.sum());self.ground_occluded+=int(occluded.sum())
        self.ground_matches+=int(matches.sum())
        self.ground_pixels.update(zip(rows[matches].tolist(),cols[matches].tolist()))
        self.ground_residual.extend(residual[matches].tolist())
        self.latest=array.copy()

    def check_clouds(self,image,info,transform,points,obstacles,plane):
        array,k,r,origin=self.decode(image,info,transform)
        if points.header.frame_id!=FRAME or obstacles.header.frame_id!='odom':raise ValueError('cloud_frame')
        if stamp(points)!=stamp(image) or stamp(obstacles)!=stamp(image):raise ValueError('cloud_stamp')
        rows,cols=np.mgrid[0:240:4,0:320:4];z=array[rows,cols]
        valid=np.isfinite(z)&(z>=.2)&(z<=10)
        expected=np.column_stack(((cols[valid]-k[0,2])*z[valid]/k[0,0],
                                  (rows[valid]-k[1,2])*z[valid]/k[1,1],z[valid])).astype(np.float32)
        actual=cloud_array(points);filtered=cloud_array(obstacles)
        if actual.shape!=expected.shape or not np.allclose(actual,expected,atol=2e-5,rtol=1e-6):
            raise ValueError('optical_cloud_stride4_projection')
        world=expected@r.T+origin
        normal=np.asarray(plane['normal']);offset=float(plane['offset'])
        if not np.isfinite(normal).all() or abs(np.linalg.norm(normal)-1)>1e-5 or normal[2]<np.cos(np.deg2rad(20)):
            raise ValueError('ground_normal')
        if plane['inlier_fraction']<.6 or plane['rms_m']>.035:raise ValueError('ground_confidence')
        # This live verifier is run on the known flat procedural fixture. The
        # reported plane is independently checked before using it for the mask.
        if abs(offset)>.03 or normal[2]<np.cos(np.deg2rad(.5)):raise ValueError('flat_fixture_ground_estimate')
        heights=world@normal+offset
        mask=(np.linalg.norm(expected.astype(float),axis=1)<=10)&(heights>=.12)&(heights<=1.8)
        wanted=world[mask]
        if filtered.shape!=wanted.shape or not np.allclose(filtered,wanted,atol=3e-5,rtol=1e-6):
            raise ValueError('obstacle_cloud_projection_or_filter')
        if not np.isfinite(filtered).all():raise ValueError('nonfinite_obstacle_cloud')
        if len(filtered) and (np.any(filtered@normal+offset<.12-1e-5) or np.any(filtered@normal+offset>1.8+1e-5)
                             or np.any(np.linalg.norm(filtered-origin,axis=1)>10+1e-5)):
            raise ValueError('obstacle_height_or_range')
        self.cloud_matches+=1;self.positive_obstacle_points+=len(filtered);self.max_points=max(self.max_points,len(actual))

    def report(self):
        rates={k:(self.counts[k]-1)/(b-a) if b>a else 0 for k,(a,b) in self.times.items()}
        now=time.monotonic()
        checks=dict(image_rate=rates.get('image',0)>=5,cloud_rate=rates.get('points',0)>=3,
                    obstacle_rate=rates.get('obstacles',0)>=3,matched_image_info_tf=self.pairs>=5,
                    matched_cloud_projection=self.cloud_matches>=3,finite_depth=self.finite_pixels>0,
                    nan_depth=self.nan_pixels>0,nan_sky=self.sky_nan_pixels>0,
                    independent_ground_matches=len(self.ground_pixels)>=100,
                    status_valid=self.counts['valid_status']>0,
                    streams_fresh=all(k in self.times and now-self.times[k][1]<.75 for k in ('image','info','points','obstacles','status')),
                    no_errors=not self.errors)
        return dict(passed=all(checks.values()),checks=checks,wall_duration_s=time.monotonic()-self.started,
                    rates_hz=rates,counts=dict(self.counts),errors=dict(self.errors),status_reasons=dict(self.status_reasons),
                    startup_unmatched=dict(self.startup_unmatched),
                    matched_image_info_tf=self.pairs,matched_clouds=self.cloud_matches,
                    finite_depth_pixels=self.finite_pixels,nan_pixels=self.nan_pixels,upward_ray_nan_pixels=self.sky_nan_pixels,
                    ground_candidate_samples=self.ground_tested,ground_matches=self.ground_matches,
                    unique_ground_match_pixels=len(self.ground_pixels),ground_occlusion_exclusions=self.ground_occluded,
                    ground_match_absolute_height_p95_m=float(np.percentile(np.abs(self.ground_residual),95)) if self.ground_residual else None,
                    max_optical_points=self.max_points,positive_obstacle_points=self.positive_obstacle_points,
                    limitations='Read-only ideal-depth proof. Ground residual tolerance0.03m permits paint; closer positive-height hits are excluded as possible obstacles. '
                    'No obstacle-presence requirement in an empty view; no costmap check performed. NaN sky requires an upward-ray sky view. '
                    'Projection comparisons use exact acquisition TF and independent pinhole/quaternion math, not processor helpers.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration',type=float,default=30)
    parser.add_argument('--report',type=Path,default=Path(__file__).resolve().parents[1]/'artifacts/checks/depth-live.json')
    args=parser.parse_args()
    if not math.isfinite(args.duration) or not 5<=args.duration<=120:parser.error('duration must be5..120 wall seconds')
    rclpy.init();node=DepthVerifier()
    try:
        end=time.monotonic()+args.duration
        while time.monotonic()<end:rclpy.spin_once(node,timeout_sec=.05)
        result=node.report();args.report.parent.mkdir(parents=True,exist_ok=True)
        if node.latest is not None:
            from PIL import Image as PilImage
            valid=np.isfinite(node.latest);scaled=np.nan_to_num(node.latest,nan=0)/10
            rgb=np.stack((255*(1-scaled),255*scaled,100+100*scaled),axis=-1).clip(0,255).astype(np.uint8)
            rgb[~valid]=[255,0,255]
            png=args.report.with_suffix('.png');PilImage.fromarray(rgb).resize((960,720),PilImage.Resampling.NEAREST).save(png)
            result['visualization']=str(png);result['visualization_key']='magenta NaN; red near to green far, optical-Z0.2..10m'
        args.report.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    finally:
        node.destroy_node();rclpy.shutdown()
    if not result['passed']:raise SystemExit(1)


if __name__=='__main__':main()
