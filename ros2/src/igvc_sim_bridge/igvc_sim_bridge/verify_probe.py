"""Live ROS/Unity acceptance checks. Run with the probe session already active."""
import argparse
from collections import OrderedDict
import json
import math
from pathlib import Path
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from geometry_msgs.msg import Twist, TwistStamped
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import Image, LaserScan, JointState
from std_srvs.srv import SetBool, Trigger
from tf2_ros import Buffer, TransformListener, TransformException
from ament_index_python.packages import get_package_share_directory


class Verify(Node):
    def __init__(self, mode='probe'):
        super().__init__('igvc_probe_verifier')
        self.counts = dict(clock=0, odom=0, image=0, scan=0, joints=0)
        self.last = {}
        self.clock_regressions = 0
        self.bad_images = 0
        self.history = {'odom': OrderedDict(), 'joints': OrderedDict()}
        self.tf_buffer = Buffer() if mode == 'r3a' else None
        self.tf_listener = TransformListener(self.tf_buffer, self) if self.tf_buffer is not None else None
        self.pub = self.create_publisher(Twist, '/cmd_vel/teleop', 1)
        self.raw_pub = self.create_publisher(TwistStamped, '/sim/drive_command', 1)
        for name, msg, topic in [('clock', Clock, '/clock'), ('odom', Odometry, '/odom'),
                                 ('image', Image, '/camera/color/image_raw'), ('scan', LaserScan, '/scan'),
                                 ('joints', JointState, '/joint_states')]:
            self.create_subscription(msg, topic, lambda value, key=name: self.receive(key, value), qos_profile_sensor_data)
        self.service_clients = {name: self.create_client(kind, '/sim/' + name)
                        for name, kind in [('pause', SetBool), ('estop', SetBool), ('reset', Trigger)]}

    def receive(self, key, msg):
        if key == 'clock' and key in self.last and self.seconds(msg.clock) < self.seconds(self.last[key].clock):
            self.clock_regressions += 1
        if key == 'image' and (msg.width != 640 or msg.height != 480 or msg.encoding != 'rgb8'
                               or len(msg.data) != msg.step * msg.height):
            self.bad_images += 1
        self.counts[key] += 1
        self.last[key] = msg
        if key in self.history:
            history = self.history[key]
            history[self.nanoseconds(msg.header.stamp)] = (msg, time.monotonic())
            while len(history) > 200:
                history.popitem(last=False)

    @staticmethod
    def seconds(stamp):
        return stamp.sec + stamp.nanosec * 1e-9

    @staticmethod
    def nanoseconds(stamp):
        return stamp.sec * 1_000_000_000 + stamp.nanosec

    def synchronized_robot(self):
        """Match joint feedback and TF to one recent odometry acquisition stamp."""
        deadline = time.monotonic() + 3
        last_error = 'No recent matching odometry/joint acquisition stamps'
        while time.monotonic() < deadline:
            common = self.history['odom'].keys() & self.history['joints'].keys()
            if common:
                stamp = max(common)
                odom, odom_wall = self.history['odom'][stamp]
                joints, joints_wall = self.history['joints'][stamp]
                # Wall-age and simulation-age checks reject stale cached transforms/data.
                recent = (stamp > 0 and time.monotonic() - min(odom_wall, joints_wall) < 0.5
                          and 0 <= self.nanoseconds(self.last['odom'].header.stamp) - stamp <= 100_000_000)
                if recent:
                    try:
                        when = Time.from_msg(odom.header.stamp)
                        transforms = {
                            child: self.tf_buffer.lookup_transform(parent, child, when)
                            for parent, child in [('base_footprint', 'base_link'),
                                                  ('base_link', 'wheel_left'), ('base_link', 'wheel_right'),
                                                  ('base_link', 'left_caster'), ('base_link', 'right_caster'),
                                                  ('base_link', 'lidar_link')]
                        }
                        world = self.tf_buffer.lookup_transform('odom', 'base_link', when)
                        if self.nanoseconds(world.header.stamp) != stamp:
                            raise AssertionError('World TF acquisition stamp differs from odometry')
                        return odom, joints, transforms, world
                    except TransformException as exc:
                        last_error = str(exc)
            rclpy.spin_once(self, timeout_sec=0.01)
        raise AssertionError('Fresh synchronized robot TF unavailable: ' + last_error)

    def wait(self, seconds, linear=None, angular=0.0):
        end = time.monotonic() + seconds
        next_send = 0.0
        while time.monotonic() < end:
            if linear is not None and time.monotonic() >= next_send:
                msg = Twist()
                msg.linear.x, msg.angular.z = float(linear), float(angular)
                self.pub.publish(msg)
                next_send = time.monotonic() + 0.05
            rclpy.spin_once(self, timeout_sec=0.01)

    def service(self, name, value=False):
        client = self.service_clients[name]
        if not client.wait_for_service(timeout_sec=15):
            raise AssertionError('Service missing: ' + name)
        req = Trigger.Request() if name == 'reset' else SetBool.Request(data=value)
        future = client.call_async(req)
        end = time.monotonic() + 10
        while not future.done() and time.monotonic() < end:
            rclpy.spin_once(self, timeout_sec=0.05)
        assert future.done() and future.result().success, 'Service failed: ' + name

    def xy(self):
        p = self.last['odom'].pose.pose.position
        return p.x, p.y


def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--duration', type=float, default=600)
    parser.add_argument('--report', required=True)
    parser.add_argument('--mode', choices=['probe', 'r3a'], default='probe')
    options = parser.parse_args(args)
    rclpy.init(args=[])
    node = Verify(options.mode)
    report = {'checks': {}, 'duration_requested': options.duration, 'mode': options.mode}
    if options.mode == 'r3a':
        report['forward_convention'] = 'drive_wheels_front_casters_rear'
        mount = json.loads((Path(get_package_share_directory('igvc_description')) / 'config/lidar_mount.json').read_text())
        report['lidar_mount_xyz_m'] = mount['scan_xyz_m']
    def check(name, result):
        report['checks'][name] = bool(result)
        print(('PASS ' if result else 'FAIL ') + name, flush=True)
        assert result, name
    try:
        deadline = time.monotonic() + 40
        while not all(node.counts.values()) and time.monotonic() < deadline:
            node.wait(0.2)
        check('all_streams_received', all(node.counts.values()))
        node.service('estop', False); node.service('pause', False); node.service('reset')
        node.wait(0.5)
        if options.mode == 'r3a':
            reset_joints = dict(zip(node.last['joints'].name, node.last['joints'].position))
            check('r3a_reset_caster_swivels', all(abs(reset_joints[name]) < 1e-8 for name in ('leftCaster', 'rightCaster')))
        check('reset_at_origin', math.hypot(*node.xy()) < 0.02)
        scan = node.last['scan']
        wall_range = 4.9 + 0.25591 - mount['scan_xyz_m'][0] if options.mode == 'r3a' else 4.9
        check('known_wall_r3a_offset' if options.mode == 'r3a' else 'known_wall_4_9m',
              abs(scan.ranges[180] - wall_range) < 0.03)
        check('scan_geometry', len(scan.ranges) == 360 and abs(scan.angle_max - (scan.angle_min + 359 * scan.angle_increment)) < 1e-5)
        node.wait(2, 0.4)
        print('FORWARD', node.xy(), 'COUNTS', node.counts, 'SIM', node.seconds(node.last['clock'].clock), flush=True)
        check('terminal_forward_motion', node.xy()[0] > 0.5 and abs(node.xy()[1]) < 0.05)
        if options.mode == 'r3a':
            odom, joints, transforms, world = node.synchronized_robot()
            lidar = transforms['lidar_link'].transform
            check('r3a_lidar_frame_matches_mount', scan.header.frame_id == 'lidar_link'
                  and math.dist((lidar.translation.x, lidar.translation.y, lidar.translation.z), mount['scan_xyz_m']) < 1e-6
                  and abs(lidar.rotation.x) + abs(lidar.rotation.y) + abs(lidar.rotation.z) < 1e-6
                  and abs(abs(lidar.rotation.w) - 1) < 1e-6)
            expected_names = {'leftWheel', 'rightWheel', 'leftCaster', 'rightCaster', 'camera_pitch_joint',
                              'left_caster_suspension_joint', 'right_caster_suspension_joint'}
            check('r3a_canonical_joint_names', len(joints.name) == 7 and set(joints.name) == expected_names
                  and len(joints.position) == 7 and all(math.isfinite(p) for p in joints.position))
            positions = dict(zip(joints.name, joints.position))
            check('r3a_flat_caster_rest', abs(positions['left_caster_suspension_joint']) < 1e-8
                  and abs(positions['right_caster_suspension_joint']) < 1e-8)
            check('r3a_forward_wheel_signs', positions['leftWheel'] > 0 and positions['rightWheel'] < 0)
            left_distance = positions['leftWheel'] * 0.229569608
            right_distance = -positions['rightWheel'] * 0.229569608
            check('r3a_wheel_distance_matches_odom',
                  abs(left_distance - odom.pose.pose.position.x) < 0.03
                  and abs(right_distance - odom.pose.pose.position.x) < 0.03)
            expected_offsets = {'base_link': (-0.25591, 0, 0.30385548),
                                'wheel_left': (0.25591, 0.40526, -0.07445),
                                'wheel_right': (0.25591, -0.40525, -0.07445),
                                'left_caster': (-0.52775, 0.24612, -0.03635),
                                'right_caster': (-0.52775, -0.24612, -0.03635)}
            for frame, expected in expected_offsets.items():
                actual = transforms[frame].transform.translation
                check('r3a_tf_' + frame + '_offset', math.dist((actual.x, actual.y, actual.z), expected) < 1e-5)
            check('r3a_driven_wheels_front_casters_rear',
                  min(transforms[name].transform.translation.x for name in ('wheel_left', 'wheel_right')) > 0
                  and max(transforms[name].transform.translation.x for name in ('left_caster', 'right_caster')) < 0)
            report['r3a_forward'] = {'stamp_ns': node.nanoseconds(odom.header.stamp),
                                     'left_distance_m': left_distance, 'right_distance_m': right_distance,
                                     'odom_x_m': odom.pose.pose.position.x}
        node.wait(0.7)
        check('command_timeout', abs(node.last['odom'].twist.twist.linear.x) < 1e-6)
        node.service('pause', True); node.wait(0.3)
        paused_time = node.seconds(node.last['clock'].clock)
        node.wait(0.4, 0.5)
        check('pause_freezes_clock', node.seconds(node.last['clock'].clock) == paused_time)
        node.service('pause', False); node.wait(0.4)
        check('resume_requires_fresh_command', abs(node.last['odom'].twist.twist.linear.x) < 1e-6)
        node.service('estop', True); before = node.xy(); node.wait(0.6, 0.5)
        check('stop_overrides_teleop', math.dist(before, node.xy()) < 0.01)
        node.service('reset'); node.service('estop', False); node.wait(0.5)
        node.wait(1, 0, 0.5)
        check('positive_yaw', node.last['odom'].pose.pose.orientation.z > 0.1)
        if options.mode == 'r3a':
            odom, _, _, world = node.synchronized_robot()
            position, rotation = odom.pose.pose.position, odom.pose.pose.orientation
            yaw = math.atan2(2 * (rotation.w * rotation.z + rotation.x * rotation.y),
                             1 - 2 * (rotation.y * rotation.y + rotation.z * rotation.z))
            base = world.transform.translation
            check('r3a_pure_yaw_stationary_axle', math.hypot(position.x, position.y) < 0.01)
            check('r3a_base_rotates_about_axle',
                  abs(math.hypot(base.x - position.x, base.y - position.y) - 0.25591) < 1e-5
                  and math.dist((base.x, base.y, base.z),
                                (position.x - 0.25591 * math.cos(yaw),
                                 position.y - 0.25591 * math.sin(yaw), 0.30385548)) < 1e-5)
            report['r3a_pure_yaw'] = {'stamp_ns': node.nanoseconds(odom.header.stamp), 'yaw_rad': yaw,
                                      'axle_xy_m': [position.x, position.y], 'base_xyz_m': [base.x, base.y, base.z]}
        node.wait(0.7); node.service('reset'); node.wait(0.5)
        old = TwistStamped(); old.header.stamp.sec = int(node.seconds(node.last['clock'].clock)) - 10; old.twist.linear.x = 1.0
        node.raw_pub.publish(old); node.wait(0.3)
        check('stale_transport_command_rejected', math.hypot(*node.xy()) < 0.01)
        baseline = dict(node.counts); start = time.monotonic(); sim_start = node.seconds(node.last['clock'].clock)
        node.wait(options.duration)
        elapsed = time.monotonic() - start
        report['rates_hz'] = {key: (node.counts[key] - baseline[key]) / elapsed for key in baseline}
        report['real_time_factor'] = (node.seconds(node.last['clock'].clock) - sim_start) / elapsed
        report['counts'] = node.counts
        check('clock_monotonic', node.clock_regressions == 0)
        check('image_shape_encoding', node.bad_images == 0)
        check('sensor_load_rates', report['rates_hz']['image'] >= 10 and report['rates_hz']['scan'] >= 4.5)
        check('real_time_factor', report['real_time_factor'] >= 0.95)
        report['status'] = 'passed'
    except Exception as exc:
        report['status'] = 'failed'; report['error'] = str(exc)
        raise
    finally:
        node.pub.publish(Twist())
        path = Path(options.report); path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2))
        node.destroy_node(); rclpy.shutdown()
