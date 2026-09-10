"""Ideal synthetic GPS; this node does not estimate or fuse a robot pose."""
import json
from pathlib import Path
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from ament_index_python.packages import get_package_share_directory
from nav_msgs.msg import Odometry
from sensor_msgs.msg import NavSatFix, NavSatStatus
from std_msgs.msg import String
from geometry_msgs.msg import TransformStamped
from tf2_ros.static_transform_broadcaster import StaticTransformBroadcaster
from .geodesy import LocalFrame


class SyntheticGps(Node):
    def __init__(self):
        super().__init__('synthetic_gps')
        default = str(Path(get_package_share_directory('igvc_gps')) / 'config/origin.json')
        path = self.declare_parameter('origin_file', default).value
        self.origin = json.loads(Path(path).read_text())
        if (self.origin['axes'] != 'x_east_y_north_z_up' or self.origin['world_frame'] != 'odom'
                or self.origin['noise_stddev_m'] != 0
                or self.origin['model'] != 'synthetic_ideal_from_odometry'):
            raise ValueError('This model requires odom ENU axes')
        self.frame = LocalFrame(self.origin)
        self.fix = self.create_publisher(NavSatFix, '/gps/fix', 10)
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.metadata = self.create_publisher(String, '/gps/origin', qos)
        self.metadata.publish(String(data=json.dumps(self.origin, sort_keys=True)))
        self.tf = StaticTransformBroadcaster(self)
        transform = TransformStamped()
        transform.header.frame_id = 'base_footprint'
        transform.child_frame_id = 'gps_link'
        transform.transform.rotation.w = 1.
        self.tf.sendTransform(transform)
        self.last_stamp = None
        self.create_subscription(Odometry, '/odom', self.on_odom, 10)
        self.get_logger().info('Ideal synthetic GPS: arbitrary origin 42/-83 by default, zero noise; no GNSS fusion')

    def on_odom(self, odom):
        if odom.header.frame_id != 'odom' or odom.child_frame_id != 'base_footprint':
            return
        stamp = odom.header.stamp.sec * 1000000000 + odom.header.stamp.nanosec
        if self.last_stamp is not None and 0 <= stamp - self.last_stamp < 100000000:
            return
        self.last_stamp = stamp
        point = odom.pose.pose.position
        fix = NavSatFix()
        fix.header.stamp = odom.header.stamp
        fix.header.frame_id = 'gps_link'
        fix.latitude, fix.longitude, fix.altitude = self.frame.to_geodetic(point.x, point.y, point.z)
        fix.status.status = NavSatStatus.STATUS_FIX
        fix.status.service = NavSatStatus.SERVICE_GPS
        fix.position_covariance = [0.] * 9
        fix.position_covariance_type = NavSatFix.COVARIANCE_TYPE_KNOWN
        self.fix.publish(fix)


def main(args=None):
    rclpy.init(args=args)
    node = SyntheticGps()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
