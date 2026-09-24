"""Manual/Nav2 command gate. Ground truth is explicitly the odometry authority."""
import math
import time

import rclpy
from rclpy.node import Node
from rclpy.clock import Clock as RclClock, ClockType
from geometry_msgs.msg import Twist, TwistStamped, TransformStamped
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock
from std_srvs.srv import SetBool
from std_msgs.msg import Bool, String
from rclpy.qos import QoSProfile, DurabilityPolicy
from tf2_ros import TransformBroadcaster, StaticTransformBroadcaster
from .navigation_policy import forward_command_allowed


class ProbeAdapter(Node):
    def __init__(self):
        super().__init__('igvc_probe_adapter')
        self.output = self.create_publisher(Twist, '/cmd_vel', 1)
        self.transport = self.create_publisher(TwistStamped, '/sim/drive_command', 1)
        self.odom = self.create_publisher(Odometry, '/odom', 5)
        self.tf = TransformBroadcaster(self)
        self.static_tf = StaticTransformBroadcaster(self)
        r3a = self.declare_parameter('r3a_mode', False).value
        if r3a:
            self.create_subscription(TransformStamped, '/sim/body_transform', self.body_transform, 10)
        self.create_subscription(Twist, '/cmd_vel/teleop', self.command, 1)
        self.create_subscription(Twist, '/cmd_vel/nav', self.nav_command, 1)
        self.autonomy_enabled = False
        self.require_lanes = self.declare_parameter('require_lanes', False).value
        self.require_depth = self.declare_parameter('require_depth', False).value
        self.last_depth_wall = float('-inf')
        self.create_subscription(Bool, '/perception/depth/healthy', self.depth_health, 1)
        self.lanes_valid = False
        self.last_lane_wall = float('-inf')
        self.unmarked_mode = False
        self.last_camera_wall = float('-inf')
        self.create_subscription(Bool, '/perception/lanes/healthy', self.camera_health, 1)
        self.create_service(SetBool, '/sim/set_unmarked_mode', self.set_unmarked)
        self.create_subscription(Bool, '/perception/lanes/valid', self.lane_status, 1)
        self.mode_output = self.create_publisher(Bool, '/sim/autonomy_enabled',
            QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.stop_reason_output = self.create_publisher(String, '/sim/autonomy_stop_reason',
            QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.stop_reason_output.publish(String(data='Autonomy has not been enabled'))
        self.create_service(SetBool, '/sim/set_autonomy', self.set_autonomy)
        self.create_subscription(Odometry, '/sim/ground_truth/odom', self.pose, 5)
        self.last_command = float('-inf')
        self.last_command_sim_ns = 0
        self.sim_ns = 0
        self.last_clock_wall = float('-inf')
        self.create_subscription(Clock, '/clock', self.clock_received, 1)
        self.latest = Twist()
        # Match monotonic expiry even when host realtime is corrected backward.
        self.steady_clock = RclClock(clock_type=ClockType.STEADY_TIME)
        self.create_timer(0.05, self.tick, clock=self.steady_clock)
        transforms = []
        for parent, child, xyz, quat in [
            ('base_footprint', 'base_link', (-0.25591, 0, 0.30385548) if r3a else (0, 0, 0.35), (0, 0, 0, 1)),
            ('base_link', 'lidar_link', (0, 0, 0.35), (0, 0, 0, 1)),
            ('base_link', 'camera_color_optical_frame', (0.45, 0, 0.7 if r3a else 0.35), (-0.5, 0.5, -0.5, 0.5)),
        ]:
            if r3a and child in ('base_link', 'lidar_link', 'camera_color_optical_frame'):
                continue  # Body is dynamic from Unity; fixed sensors belong to robot_state_publisher.
            msg = TransformStamped()
            msg.header.frame_id, msg.child_frame_id = parent, child
            msg.transform.translation.x, msg.transform.translation.y, msg.transform.translation.z = map(float, xyz)
            (msg.transform.rotation.x, msg.transform.rotation.y,
             msg.transform.rotation.z, msg.transform.rotation.w) = map(float, quat)
            transforms.append(msg)
        self.static_tf.sendTransform(transforms)
        self.get_logger().info(('R3-A KINEMATIC ORACLE' if r3a else 'PROBE') + ': manual default; explicit Nav2 enable, ideal odometry, wall-time watchdog')

    def command(self, msg):
        if not all(math.isfinite(x) for x in (msg.linear.x, msg.angular.z)):
            return
        # Manual takeover latches autonomy off; an old goal cannot silently resume.
        if self.autonomy_enabled:
            self.stop_reason_output.publish(String(data='Manual command took over autonomy'))
        self.autonomy_enabled = False
        self.unmarked_mode = False
        self.accept_command(msg)

    def body_transform(self, msg):
        t,q=msg.transform.translation,msg.transform.rotation
        values=(t.x,t.y,t.z,q.x,q.y,q.z,q.w)
        if (msg.header.frame_id!='base_footprint' or msg.child_frame_id!='base_link'
                or not all(map(math.isfinite,values))
                or abs(q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w-1)>1e-4
                or abs(t.x)>2 or abs(t.y)>2 or not -1<=t.z<=3):
            return
        self.tf.sendTransform(msg)

    def nav_command(self, msg):
        if self.autonomy_enabled:
            self.accept_command(msg if forward_command_allowed(msg.linear.x, msg.angular.z) else Twist())

    def set_autonomy(self, request, response):
        if request.data and not self.perception_fresh():
            self.autonomy_enabled = False
            self.last_command = float('-inf')
            response.success = False
            response.message = 'Fresh lane observations and a confident depth ground estimate required; inspect perception status'
            self.stop_reason_output.publish(String(data=response.message))
            return response
        was_enabled = self.autonomy_enabled
        self.autonomy_enabled = request.data
        self.last_command = float('-inf')
        self.latest = Twist()
        # Cleanup after a latched fault must not overwrite its diagnostic.
        if request.data or was_enabled:
            self.stop_reason_output.publish(String(data='' if request.data else 'Autonomy disabled by service request'))
        response.success = True
        response.message = 'Autonomy enabled; fresh command required' if request.data else 'Manual mode; navigation commands ignored'
        return response

    def lane_status(self, message):
        self.lanes_valid = message.data
        if message.data:
            self.last_lane_wall = time.monotonic()

    def camera_health(self, message):
        if message.data:
            self.last_camera_wall = time.monotonic()

    def perception_fresh(self):
        now=time.monotonic()
        lanes_ok=not self.require_lanes or now-(self.last_camera_wall if self.unmarked_mode else self.last_lane_wall)<.75
        depth_ok=not self.require_depth or now-self.last_depth_wall<.75
        return lanes_ok and depth_ok

    def depth_health(self, message):
        if message.data:
            self.last_depth_wall=time.monotonic()

    def set_unmarked(self, request, response):
        if self.autonomy_enabled and request.data != self.unmarked_mode:
            response.success = False
            response.message = 'Disable autonomy before changing the declared course zone'
            return response
        self.unmarked_mode = request.data
        response.success = True
        response.message = 'Unmarked GPS section: healthy camera still required' if request.data else 'Painted section: lane detections required'
        return response

    def accept_command(self, msg):
        if not all(math.isfinite(x) for x in (msg.linear.x, msg.angular.z)):
            return
        self.latest = Twist()
        # Supplied 2026 rules: 5 mph = 2.2352 m/s; 2027 limit unverified.
        # Leave 0.0352 m/s margin below that reference limit.
        # Saturate the twist uniformly: independent clipping understeers when
        # Nav2 requests a turn faster than the simulated yaw-rate limit.
        scale = min(1.0, (2.2 if msg.linear.x >= 0 else .3) / max(abs(msg.linear.x), 1e-12),
                    1.0 / max(abs(msg.angular.z), 1e-12))
        self.latest.linear.x = msg.linear.x * scale
        self.latest.angular.z = msg.angular.z * scale
        self.last_command = time.monotonic()
        self.last_command_sim_ns = self.sim_ns

    def clock_received(self, msg):
        self.sim_ns = msg.clock.sec * 1_000_000_000 + msg.clock.nanosec
        self.last_clock_wall = time.monotonic()

    def tick(self):
        if self.autonomy_enabled and not self.perception_fresh():
            now = time.monotonic()
            reason = (
                'Autonomy latched off: perception freshness expired '
                f'(require_lanes={self.require_lanes}, require_depth={self.require_depth}, '
                f'unmarked_mode={self.unmarked_mode}, '
                f'camera_age={now-self.last_camera_wall:.3f}s, '
                f'lane_age={now-self.last_lane_wall:.3f}s, '
                f'depth_age={now-self.last_depth_wall:.3f}s, '
                f'clock_age={now-self.last_clock_wall:.3f}s; limit=0.750s). '
                'Explicit autonomy enable is required after healthy observations return.')
            self.get_logger().warning(reason)
            self.stop_reason_output.publish(String(data=reason))
            self.autonomy_enabled = False
            self.last_command = float('-inf')
        self.mode_output.publish(Bool(data=self.autonomy_enabled))
        fresh = time.monotonic() - self.last_command < 0.3 and time.monotonic() - self.last_clock_wall < 0.5
        msg = self.latest if fresh else Twist()
        self.output.publish(msg)
        stamped = TwistStamped()
        # Original simulation acquisition time survives repeats; host UTC clocks may differ.
        ns = self.last_command_sim_ns if fresh else self.sim_ns
        stamped.header.stamp.sec, stamped.header.stamp.nanosec = divmod(ns, 1_000_000_000)
        stamped.header.frame_id = 'base_footprint'
        stamped.twist = msg
        self.transport.publish(stamped)

    def pose(self, msg):
        self.odom.publish(msg)
        transform = TransformStamped()
        transform.header = msg.header
        transform.child_frame_id = msg.child_frame_id
        transform.transform.translation.x = msg.pose.pose.position.x
        transform.transform.translation.y = msg.pose.pose.position.y
        transform.transform.translation.z = msg.pose.pose.position.z
        transform.transform.rotation = msg.pose.pose.orientation
        self.tf.sendTransform(transform)


def main(args=None):
    rclpy.init(args=args)
    node = ProbeAdapter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
