"""Causal depth-supported lidar marking stream; raw /scan remains unchanged."""
from collections import OrderedDict
from copy import deepcopy
import json
import time
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.clock import Clock, ClockType
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import LaserScan, PointCloud2, PointField
from std_msgs.msg import String
from tf2_ros import Buffer, TransformListener, TransformException
from .lanes import rotation_matrix
from .scan_ground import filter_ground_returns


class ScanGroundNode(Node):
    def __init__(self):
        super().__init__('igvc_scan_ground_filter')
        self.tf = Buffer()
        self.listener = TransformListener(self.tf, self)
        self.scans, self.surfaces = OrderedDict(), OrderedDict()
        self.last_stamp = 0
        self.output = self.create_publisher(LaserScan, '/perception/lidar/obstacles_scan', qos_profile_sensor_data)
        self.status = self.create_publisher(String, '/perception/lidar/status', 1)
        self.create_subscription(LaserScan, '/scan', self.scan, qos_profile_sensor_data)
        self.create_subscription(PointCloud2, '/perception/depth/surfaces', self.surface, qos_profile_sensor_data)
        self.steady_clock = Clock(clock_type=ClockType.STEADY_TIME)
        self.create_timer(.2, self.tick, clock=self.steady_clock)

    @staticmethod
    def stamp(message):
        return message.header.stamp.sec*1_000_000_000+message.header.stamp.nanosec

    def scan(self, message):
        stamp = self.stamp(message)
        if stamp < self.last_stamp:
            self.scans.clear(); self.surfaces.clear(); self.last_stamp = 0
        self.scans[stamp] = (message, time.monotonic())
        while len(self.scans) > 8:
            self.scans.popitem(last=False)

    def surface(self, message):
        expected = [(name, index*4, PointField.FLOAT32, 1)
                    for index, name in enumerate(('x', 'y', 'z', 'ground'))]
        try:
            if (message.header.frame_id != 'odom' or message.height != 1 or message.width > 4800
                    or message.point_step != 16 or message.row_step != message.width*16
                    or len(message.data) != message.row_step
                    or [(f.name, f.offset, f.datatype, f.count) for f in message.fields] != expected):
                raise ValueError('Invalid surface layout')
            values = np.frombuffer(message.data, dtype='>f4' if message.is_bigendian else '<f4').reshape(-1, 4).copy()
            if not np.isfinite(values).all() or not np.isin(values[:, 3], [0, 1]).all():
                raise ValueError('Invalid surface values')
            self.surfaces[self.stamp(message)] = (values, time.monotonic())
            while len(self.surfaces) > 8:
                self.surfaces.popitem(last=False)
        except ValueError:
            self.surfaces.clear()

    def tick(self):
        now = time.monotonic()
        ready = [stamp for stamp, (_, arrival) in self.scans.items()
                 if stamp > self.last_stamp and now-arrival >= .04]
        if not ready:
            return
        stamp = max(ready)
        scan, arrival = self.scans[stamp]
        self.last_stamp = stamp
        output = deepcopy(scan)
        diagnostics = dict(stamp_ns=stamp, removed_ground=0, reason='no_fresh_preceding_surface')
        support = [s for s, (_, wall) in self.surfaces.items()
                   if 0 <= stamp-s <= 300_000_000 and 0 <= now-wall <= .75]
        try:
            if now-arrival > .75:
                diagnostics['reason'] = 'scan_stale_passthrough'
            elif support:
                source_stamp = max(support)
                transform = self.tf.lookup_transform('odom', scan.header.frame_id,
                                                     Time.from_msg(scan.header.stamp))
                if self.stamp(transform) != stamp:
                    raise ValueError('TF must match scan acquisition stamp')
                t, q = transform.transform.translation, transform.transform.rotation
                values = self.surfaces[source_stamp][0]
                filtered, result = filter_ground_returns(scan.ranges, scan.angle_min,
                    scan.angle_increment, scan.range_min, scan.range_max,
                    rotation_matrix((q.x, q.y, q.z, q.w)), (t.x, t.y, t.z),
                    values[:, :3], values[:, 3] > 0)
                output.ranges = filtered.astype(np.float32).tolist()
                diagnostics.update(result, support_stamp_ns=source_stamp,
                                   support_age_s=(stamp-source_stamp)/1e9)
        except (ValueError, TransformException, np.linalg.LinAlgError) as exc:
            diagnostics['reason'] = 'passthrough: '+str(exc)
        self.output.publish(output)
        self.status.publish(String(data=json.dumps(diagnostics)))


def main(args=None):
    rclpy.init(args=args)
    node = ScanGroundNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
