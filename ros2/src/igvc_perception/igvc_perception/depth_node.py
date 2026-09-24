"""Metric depth projection with acquisition-time TF and bounded fresh frames."""
from collections import OrderedDict
import json
import time
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.clock import Clock, ClockType
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import Image, CameraInfo, PointCloud2, PointField
from std_msgs.msg import Header, String, Bool
from std_srvs.srv import Trigger
from tf2_ros import Buffer, TransformListener, TransformException
from .depth import depth_points
from .ground import estimate_ground, terrain_obstacles
from .lanes import rotation_matrix
from .surfaces import classify_surfaces


class DepthNode(Node):
    def __init__(self):
        super().__init__('igvc_depth_processor')
        self.tf=Buffer();self.listener=TransformListener(self.tf,self)
        self.images,self.infos=OrderedDict(),OrderedDict()
        self.last_stamp=0
        self.ground_prior=None
        self.ground_prior_wall=float('-inf')
        self.ground_prior_stamp=0
        self.cloud=self.create_publisher(PointCloud2,'/camera/depth/points',qos_profile_sensor_data)
        self.obstacles=self.create_publisher(PointCloud2,'/perception/depth/obstacles',qos_profile_sensor_data)
        self.surfaces=self.create_publisher(PointCloud2,'/perception/depth/surfaces',qos_profile_sensor_data)
        self.status=self.create_publisher(String,'/perception/depth/status',1)
        self.healthy=self.create_publisher(Bool,'/perception/depth/healthy',1)
        self.create_service(Trigger,'/perception/depth/reset',self.reset)
        self.create_subscription(Image,'/camera/depth/image_raw',lambda m:self.cache(self.images,m),qos_profile_sensor_data)
        self.create_subscription(CameraInfo,'/camera/depth/camera_info',lambda m:self.cache(self.infos,m),qos_profile_sensor_data)
        self.steady_clock=Clock(clock_type=ClockType.STEADY_TIME)
        self.create_timer(.2,self.tick,clock=self.steady_clock)

    @staticmethod
    def stamp(m):return m.header.stamp.sec*1_000_000_000+m.header.stamp.nanosec

    def reset(self, request, response):
        self.images.clear();self.infos.clear();self.last_stamp=0
        self.ground_prior=None
        self.ground_prior_wall=float('-inf');self.ground_prior_stamp=0
        self.healthy.publish(Bool(data=False))
        response.success=True
        response.message='Depth observations and ground prior cleared'
        return response

    def cache(self,store,m):
        stamp=self.stamp(m)
        if store is self.images and stamp<self.last_stamp:
            self.images.clear();self.infos.clear();self.last_stamp=0
            self.ground_prior=None
        store[stamp]=(m,time.monotonic())
        while len(store)>8:store.popitem(last=False)

    @staticmethod
    def message(points,header):
        points=np.asarray(points,dtype='<f4').reshape(-1,3)
        return PointCloud2(header=header,height=1,width=len(points),is_bigendian=False,
            fields=[PointField(name=name,offset=i*4,datatype=PointField.FLOAT32,count=1) for i,name in enumerate(('x','y','z'))],
            point_step=12,row_step=len(points)*12,is_dense=True,data=points.tobytes())

    def tick(self):
        now=time.monotonic()
        if now-self.ground_prior_wall>.75:
            self.ground_prior=None
        common=[s for s in self.images.keys() & self.infos.keys() if s>self.last_stamp and now-max(self.images[s][1],self.infos[s][1])>=.04]
        if not common:
            self.healthy.publish(Bool(data=False))
            self.status.publish(String(data=json.dumps({'valid':False,'reason':'no_new_pair'})))
            return
        # Transport callbacks can deliver a newer image before its exact TF.
        # Use the newest fresh acquisition whose transform is already buffered;
        # never substitute the latest transform for the image's own timestamp.
        ready=[s for s in common if now-min(self.images[s][1],self.infos[s][1])<=.5
               and self.tf.can_transform('odom',self.images[s][0].header.frame_id,
                                         Time.from_msg(self.images[s][0].header.stamp))]
        if not ready:
            self.healthy.publish(Bool(data=False))
            self.status.publish(String(data=json.dumps({'valid':False,'reason':'acquisition_tf_not_ready'})))
            return
        stamp=max(ready);image,arrival=self.images[stamp];info,info_wall=self.infos[stamp]
        try:
            if now-min(arrival,info_wall)>.5:raise ValueError('stale_pair')
            if image.encoding!='32FC1' or image.width!=info.width or image.height!=info.height or image.header.frame_id!=info.header.frame_id:
                raise ValueError('depth_info_format')
            if image.step<image.width*4 or image.step%4 or len(image.data)!=image.height*image.step:raise ValueError('depth_buffer')
            array=np.frombuffer(image.data,dtype='>f4' if image.is_bigendian else '<f4').reshape(image.height,image.step//4)[:,:image.width]
            points=depth_points(array,info.k,stride=4)
            transform=self.tf.lookup_transform('odom',image.header.frame_id,Time.from_msg(image.header.stamp))
            if self.stamp(transform)!=stamp:raise ValueError('tf_acquisition_stamp')
            t,q=transform.transform.translation,transform.transform.rotation
            origin=np.array([t.x,t.y,t.z])
            rotation=rotation_matrix((q.x,q.y,q.z,q.w))
            self.cloud.publish(self.message(points,image.header))
            self.last_stamp=stamp
            # Fit only lower-image returns. No course mesh or fixed world Z is
            # consulted, and an uncertain fit is never replaced by a flat plane.
            candidate_image=array.copy();candidate_image[:160]=np.nan
            candidates=depth_points(candidate_image,info.k,stride=4)@rotation.T+origin
            prior_age=max(now-self.ground_prior_wall,(stamp-self.ground_prior_stamp)/1e9)
            plane=estimate_ground(candidates,origin,self.ground_prior,prior_age)
            observed=classify_surfaces(array,info.k,rotation,origin,plane)
            self.ground_prior=plane
            self.ground_prior_wall=time.monotonic()
            self.ground_prior_stamp=stamp
            obstacles=observed['obstacles']
            valid=observed['valid_mask'];ground=observed['ground_mask']
            surface_points=np.column_stack((observed['grid_world'][valid],ground[valid])).astype('<f4')
            self.surfaces.publish(PointCloud2(header=Header(stamp=image.header.stamp,frame_id='odom'),
                height=1,width=len(surface_points),is_bigendian=False,
                fields=[PointField(name=name,offset=i*4,datatype=PointField.FLOAT32,count=1) for i,name in enumerate(('x','y','z','ground'))],
                point_step=16,row_step=len(surface_points)*16,is_dense=True,data=surface_points.tobytes()))
            self.obstacles.publish(self.message(obstacles,Header(stamp=image.header.stamp,frame_id='odom')))
            self.healthy.publish(Bool(data=True))
            self.status.publish(String(data=json.dumps({'valid':True,'stamp_ns':stamp,'points':len(points),'obstacle_points':len(obstacles),'ground_points':int(ground.sum()),'ground':plane})))
        except (ValueError,TransformException) as exc:
            self.healthy.publish(Bool(data=False))
            self.status.publish(String(data=json.dumps({'valid':False,'reason':str(exc)})))


def main():
    rclpy.init();node=DepthNode()
    try:rclpy.spin(node)
    finally:node.destroy_node();rclpy.shutdown()
