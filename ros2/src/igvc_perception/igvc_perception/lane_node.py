import json
import re
from collections import OrderedDict
import time

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.clock import Clock, ClockType
from rclpy.time import Time
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, CameraInfo, PointCloud2, PointField
from std_msgs.msg import Bool, String, Header
from std_srvs.srv import Trigger
from tf2_ros import Buffer, TransformListener, TransformException

from .lanes import lane_pixels, rotation_matrix
from .hazards import hazard_pixels
from .terrain_history import GroundHistory
from .surface_projection import project_observed
from .point_memory import PointMemory


class LaneNode(Node):
    def __init__(self):
        super().__init__('igvc_lane_detector')
        self.ground_history = GroundHistory()
        self.ttl = float(self.declare_parameter('point_ttl', 8.).value)
        self.tf = Buffer()
        self.listener = TransformListener(self.tf, self)
        self.images, self.infos = OrderedDict(), OrderedDict()
        self.surfaces = OrderedDict()
        self.points = PointMemory(self.ttl, 8000)
        self.hazard_points = PointMemory(self.ttl, 4000)
        self.last_stamp = 0
        self.last_success = float('-inf')
        self.last_arrival_stamp = 0
        self.run_id = None
        self.debug = self.create_publisher(Image, '/perception/lanes/debug', qos_profile_sensor_data)
        self.cloud = self.create_publisher(PointCloud2, '/perception/lanes/points', qos_profile_sensor_data)
        self.hazard_cloud = self.create_publisher(PointCloud2, '/perception/hazards/points', qos_profile_sensor_data)
        self.hazard_debug = self.create_publisher(Image, '/perception/hazards/debug', qos_profile_sensor_data)
        self.valid = self.create_publisher(Bool, '/perception/lanes/valid', 1)
        self.healthy = self.create_publisher(Bool, '/perception/lanes/healthy', 1)
        self.status = self.create_publisher(String, '/perception/lanes/status', 1)
        self.create_subscription(Image, '/camera/color/image_raw', self.image, qos_profile_sensor_data)
        self.create_subscription(CameraInfo, '/camera/color/camera_info', self.info, qos_profile_sensor_data)
        self.create_subscription(String, '/sim/status', self.sim_status, 1)
        self.create_subscription(String, '/perception/depth/status', self.ground_status, 1)
        self.create_subscription(PointCloud2, '/perception/depth/surfaces', self.surface_cloud, qos_profile_sensor_data)
        self.create_service(Trigger, '/perception/lanes/reset', self.reset)
        self.steady_clock = Clock(clock_type=ClockType.STEADY_TIME)
        # Expiry must run during simulation pauses and host clock corrections.
        self.create_timer(.2, self.tick, clock=self.steady_clock)

    @staticmethod
    def stamp(message):
        return message.header.stamp.sec*1_000_000_000 + message.header.stamp.nanosec

    @staticmethod
    def cache(store, stamp, message):
        store[stamp] = (message, time.monotonic())
        while len(store) > 8:
            store.popitem(last=False)

    def image(self, message):
        stamp = self.stamp(message)
        if stamp < self.last_arrival_stamp:
            self.clear()
        self.last_arrival_stamp = stamp
        self.cache(self.images, stamp, message)

    def info(self, message):
        self.cache(self.infos, self.stamp(message), message)

    def sim_status(self, message):
        match = re.search(r'\brun=(\d+)', message.data)
        if match:
            run = int(match[1])
            if self.run_id is not None and run != self.run_id:
                self.clear()
                self.valid.publish(Bool(data=False))
            self.run_id = run

    def ground_status(self, message):
        try:
            status=json.loads(message.data)
            if not isinstance(status,dict):raise ValueError('Expected ground status object')
            self.ground_history.update(status,time.monotonic())
        except (ValueError,TypeError):
            self.ground_history.clear()

    def surface_cloud(self,message):
        try:
            if message.header.frame_id!='odom' or message.height!=1 or message.width>4800 or message.point_step!=16 or message.row_step!=message.width*16 or len(message.data)!=message.row_step:
                raise ValueError('surface_format')
            if [(f.name,f.offset,f.datatype,f.count) for f in message.fields]!=[(name,i*4,PointField.FLOAT32,1) for i,name in enumerate(('x','y','z','ground'))]:
                raise ValueError('surface_fields')
            values=np.frombuffer(message.data,dtype='>f4' if message.is_bigendian else '<f4').reshape(-1,4).copy()
            if not np.isfinite(values).all() or not np.isin(values[:,3],[0,1]).all():raise ValueError('surface_values')
            self.cache(self.surfaces,self.stamp(message),values)
        except ValueError:
            self.surfaces.clear();self.ground_history.clear()

    def clear(self):
        self.healthy.publish(Bool(data=False))
        self.points.clear()
        self.hazard_points.clear()
        self.images.clear()
        self.infos.clear()
        self.surfaces.clear()
        self.ground_history.clear()
        self.last_stamp = 0
        self.last_success = float('-inf')

    def reset(self, request, response):
        self.clear()
        self.valid.publish(Bool(data=False))
        self.publish_cloud(Header(frame_id='odom'))
        self.publish_cloud(Header(frame_id='odom'),self.hazard_points,self.hazard_cloud)
        response.success, response.message = True, 'Lane observation cache cleared'
        return response

    def publish_cloud(self, header, points=None, publisher=None):
        values = np.asarray([value[0] for value in (self.points if points is None else points).values()], dtype='<f4').reshape(-1, 3)
        message = PointCloud2(header=header, height=1, width=len(values), is_bigendian=False,
                             point_step=12, row_step=len(values)*12, is_dense=True, data=values.tobytes())
        message.fields = [PointField(name=name, offset=i*4, datatype=PointField.FLOAT32, count=1)
                          for i, name in enumerate(('x', 'y', 'z'))]
        (self.cloud if publisher is None else publisher).publish(message)

    def tick(self):
        now = time.monotonic()
        self.points.expire(now)
        self.hazard_points.expire(now)
        common = {stamp for stamp in self.images.keys() & self.infos.keys()
                  if now-max(self.images[stamp][1], self.infos[stamp][1]) >= .04}
        if not common or max(common) <= self.last_stamp:
            self.healthy.publish(Bool(data=False))
            self.valid.publish(Bool(data=False))
            self.status.publish(String(data=json.dumps({'valid': False, 'reason': 'no_new_exact_stamp_pair',
                                                        'age_wall_s': None if not np.isfinite(self.last_success) else now-self.last_success})))
            return
        # RGB and depth are independent exposures. Select an RGB acquisition
        # with exact TF buffered and a fresh preceding depth plane, not latest TF.
        ready=[]
        available={s for s,(_,wall) in self.surfaces.items() if 0<=now-wall<=.5}
        for candidate in common:
            if candidate<=self.last_stamp:continue
            try:
                ground_stamp,_=self.ground_history.select(candidate,now,available)
            except ValueError:continue
            m=self.images[candidate][0]
            if self.tf.can_transform('odom',m.header.frame_id,Time.from_msg(m.header.stamp)):
                ready.append(candidate)
        if not ready:
            self.healthy.publish(Bool(data=False));self.valid.publish(Bool(data=False))
            self.status.publish(String(data=json.dumps({'valid':False,'reason':'waiting_for_depth_ground_or_rgb_tf'})))
            return
        stamp = max(ready)
        image, arrival = self.images[stamp]
        info, info_arrival = self.infos[stamp]
        try:
            if now-min(arrival, info_arrival) > .5:
                raise ValueError('stale_pair')
            if image.encoding != 'rgb8' or image.width != info.width or image.height != info.height or (image.width,image.height)!=(640,480):
                raise ValueError('image_info_format')
            if image.header.frame_id != info.header.frame_id or not image.header.frame_id:
                raise ValueError('image_info_frame')
            if image.step < image.width*3 or len(image.data) != image.height*image.step:
                raise ValueError('image_buffer')
            transform = self.tf.lookup_transform('odom', image.header.frame_id, Time.from_msg(image.header.stamp))
            if self.stamp(transform) != stamp:
                raise ValueError('tf_acquisition_stamp')
            rgb = np.frombuffer(image.data, dtype=np.uint8).reshape(image.height, image.step)[:, :image.width*3].reshape(image.height, image.width, 3)
            pixels, mask, components = lane_pixels(rgb)
            t, q = transform.transform.translation, transform.transform.rotation
            ground_stamp,ground=self.ground_history.select(stamp,now,available)
            surface=self.surfaces[ground_stamp][0]
            projected = project_observed(pixels, info.k, rotation_matrix((q.x, q.y, q.z, q.w)), (t.x, t.y, t.z), surface[:,:3], eligible_mask=surface[:,3]>0)
            hazard_pixels_xy, hazard_mask, hazard_components = hazard_pixels(rgb)
            hazards = project_observed(hazard_pixels_xy, info.k, rotation_matrix((q.x,q.y,q.z,q.w)), (t.x,t.y,t.z), surface[:,:3])
            self.hazard_points.observe(
                ((tuple(np.floor(point[:2]/.075).astype(int)), point) for point in hazards), stamp, now)
            self.points.observe(
                ((tuple(np.floor(point[:2]/.075).astype(int)), point) for point in projected), stamp, now)
            self.last_stamp = stamp
            self.last_success = now
            self.healthy.publish(Bool(data=True))
            valid = len(projected) >= 12 and components >= 1
            self.valid.publish(Bool(data=valid))
            self.debug.publish(Image(header=image.header, height=image.height, width=image.width,
                                     encoding='mono8', is_bigendian=0, step=image.width, data=mask.tobytes()))
            self.publish_cloud(Header(stamp=image.header.stamp, frame_id='odom'))
            self.publish_cloud(Header(stamp=image.header.stamp, frame_id='odom'),self.hazard_points,self.hazard_cloud)
            self.hazard_debug.publish(Image(header=image.header,height=image.height,width=image.width,encoding='mono8',is_bigendian=0,step=image.width,data=hazard_mask.tobytes()))
            self.status.publish(String(data=json.dumps({'valid': valid, 'stamp_ns': stamp, 'components': components,
                                                        'pixels': len(pixels), 'current_points': len(projected),
                                                        'accumulated_points': len(self.points), 'hazard_components':hazard_components,
                                                        'hazard_points':len(hazards), 'ground':ground,
                                                        'ground_stamp_ns':ground_stamp,
                                                        'ground_age_s':(stamp-ground_stamp)/1e9})))
        except (ValueError, TransformException, np.linalg.LinAlgError) as exc:
            self.healthy.publish(Bool(data=False))
            self.valid.publish(Bool(data=False))
            self.status.publish(String(data=json.dumps({'valid': False, 'reason': str(exc)})))


def main(args=None):
    rclpy.init(args=args)
    node = LaneNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.valid.publish(Bool(data=False))
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
