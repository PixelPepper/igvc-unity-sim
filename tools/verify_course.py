#!/usr/bin/env python3
"""Read-only, bounded Sooner course ROS stream smoke check. Never commands motion/services."""
import argparse
from collections import Counter, OrderedDict
import json
import math
from pathlib import Path
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rosgraph_msgs.msg import Clock
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image, CameraInfo, LaserScan, JointState


def stamp_ns(stamp):
    return stamp.sec * 1_000_000_000 + stamp.nanosec


class CourseStreams(Node):
    def __init__(self):
        super().__init__('igvc_course_smoke_verifier')
        self.counts = Counter()
        self.errors = Counter()
        self.last_wall = {}
        self.clock_first = None
        self.clock_last = None
        self.images = OrderedDict()
        self.infos = OrderedDict()
        self.matches = 0
        self.matched_stamp_first = None
        self.matched_stamp_last = None
        self.color_count_max = 0
        self.finite_scan_samples = 0
        self.scan_nearest = None
        self.scan_farthest = None
        self.frame_ids = {}
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        for name, kind, topic in [
            ('clock', Clock, '/clock'), ('odom', Odometry, '/odom'),
            ('ground_truth', Odometry, '/sim/ground_truth/odom'),
            ('image', Image, '/camera/color/image_raw'),
            ('info', CameraInfo, '/camera/color/camera_info'),
            ('scan', LaserScan, '/scan'), ('joints', JointState, '/joint_states')]:
            self.create_subscription(kind, topic, lambda m, key=name: self.receive(key, m), qos)

    def receive(self, key, msg):
        self.counts[key] += 1
        self.last_wall[key] = time.monotonic()
        if key == 'clock':
            current = stamp_ns(msg.clock)
            if self.clock_last is not None and current < self.clock_last:
                self.errors['clock_regression'] += 1
            if self.clock_first is None:
                self.clock_first = current
            self.clock_last = current
            return
        expected = {'image': 'camera_color_optical_frame', 'info': 'camera_color_optical_frame',
                    'scan': 'lidar_link', 'joints': 'base_link', 'odom': 'odom', 'ground_truth': 'odom'}[key]
        self.frame_ids[key] = msg.header.frame_id
        if msg.header.frame_id != expected:
            self.errors[key + '_frame'] += 1
        if key in ('image', 'info'):
            stamp = stamp_ns(msg.header.stamp)
            target = self.images if key == 'image' else self.infos
            target[stamp] = (msg.width, msg.height, msg.header.frame_id)
            if key == 'image':
                if (msg.width, msg.height, msg.encoding, msg.step) != (640, 480, 'rgb8', 1920) or len(msg.data) != msg.step * msg.height:
                    self.errors['image_shape_encoding'] += 1
                else:
                    # Spatial colors from bounded samples, without retaining image payloads.
                    colors = {tuple(msg.data[i:i + 3]) for i in range(0, len(msg.data) - 2, 3 * 307)}
                    self.color_count_max = max(self.color_count_max, len(colors))
            elif (msg.width, msg.height) != (640, 480) or not all(math.isfinite(x) for x in (*msg.k, *msg.p)) or msg.k[0] <= 0 or msg.k[4] <= 0:
                self.errors['camera_intrinsics'] += 1
            if stamp in self.images and stamp in self.infos:
                if self.images.pop(stamp) != self.infos.pop(stamp) or stamp <= 0:
                    self.errors['image_info_pair'] += 1
                else:
                    self.matches += 1
                    self.matched_stamp_first = stamp if self.matched_stamp_first is None else min(self.matched_stamp_first, stamp)
                    self.matched_stamp_last = stamp if self.matched_stamp_last is None else max(self.matched_stamp_last, stamp)
            while len(target) > 256:
                target.popitem(last=False)
        elif key == 'scan':
            if not msg.ranges or not math.isfinite(msg.range_min) or not math.isfinite(msg.range_max) or msg.range_max <= msg.range_min:
                self.errors['scan_metadata'] += 1
            finite = [float(r) for r in msg.ranges if math.isfinite(r)]
            valid = [r for r in finite if msg.range_min <= r <= msg.range_max]
            if len(valid) != len(finite):
                self.errors['scan_finite_out_of_range'] += 1
            self.finite_scan_samples += len(valid)
            if valid:
                self.scan_nearest = min(valid) if self.scan_nearest is None else min(self.scan_nearest, min(valid))
                self.scan_farthest = max(valid) if self.scan_farthest is None else max(self.scan_farthest, max(valid))
        elif key == 'joints':
            expected_names = {'leftWheel', 'rightWheel', 'leftCaster', 'rightCaster', 'camera_pitch_joint',
                              'left_caster_suspension_joint', 'right_caster_suspension_joint'}
            if len(msg.name) != 7 or set(msg.name) != expected_names or len(msg.position) != 7 or not all(math.isfinite(p) for p in msg.position):
                self.errors['joint_names_positions'] += 1
            else:
                positions = dict(zip(msg.name, msg.position))
                if abs(positions['left_caster_suspension_joint']) > 1e-8 or abs(positions['right_caster_suspension_joint']) > 1e-8:
                    self.errors['flat_course_caster_rest'] += 1
        else:
            p, q = msg.pose.pose.position, msg.pose.pose.orientation
            if msg.child_frame_id != 'base_footprint':
                self.errors[key + '_child_frame'] += 1
            if not all(math.isfinite(x) for x in (p.x, p.y, p.z, q.x, q.y, q.z, q.w)) or abs(sum(x*x for x in (q.x, q.y, q.z, q.w)) - 1) > 1e-3:
                self.errors[key + '_pose'] += 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration', type=float, default=20)
    parser.add_argument('--report', type=Path, default=Path(__file__).resolve().parents[1] / 'artifacts/checks/sooner-course-live.json')
    args = parser.parse_args()
    if not math.isfinite(args.duration) or not 2 <= args.duration <= 20:
        parser.error('duration must be 2..20 wall-clock seconds')
    rclpy.init(args=[])
    node = CourseStreams()
    start = time.monotonic()
    try:
        while time.monotonic() - start < args.duration:
            rclpy.spin_once(node, timeout_sec=0.05)
        now = time.monotonic()
        needed = ('clock', 'image', 'info', 'scan', 'joints')
        odom = 'odom' if node.counts['odom'] else 'ground_truth'
        needed += (odom,)
        checks = {
            'all_required_streams': all(node.counts[k] > 1 for k in needed),
            'all_required_streams_recent': all(now - node.last_wall.get(k, -math.inf) < 2 for k in needed),
            'clock_advancing': node.clock_first is not None and node.clock_last > node.clock_first,
            'rgb_camera_info_matched_advancing_stamps': node.matches >= 2 and node.matched_stamp_last > node.matched_stamp_first,
            'rgb_spatial_color_variation': node.color_count_max >= 2,
            'scan_detects_finite_obstacles': node.finite_scan_samples > 0,
            'frame_shape_and_data_checks': not node.errors,
        }
        report = {'status': 'passed' if all(checks.values()) else 'failed', 'checks': checks,
                  'mode': 'course_streams_only', 'motion_and_services': 'not invoked',
                  'elapsed_wall_seconds': now-start, 'qos': 'reliable depth10',
                  'counts': dict(node.counts), 'rates_hz': {k:v/(now-start) for k,v in node.counts.items()},
                  'errors': dict(node.errors), 'frame_ids': node.frame_ids, 'odom_topic_selected': '/odom' if odom == 'odom' else '/sim/ground_truth/odom',
                  'matched_image_info_pairs': node.matches,
                  'matched_stamp_ns': [node.matched_stamp_first, node.matched_stamp_last],
                  'maximum_sampled_rgb_colors': node.color_count_max,
                  'finite_scan_samples': node.finite_scan_samples, 'scan_range_extrema_m': [node.scan_nearest,node.scan_farthest],
                  'limitations': 'Proves received streams, not course identity, collision fidelity, navigation, physical calibration or motion safety.'}
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
        print(json.dumps({'status': report['status'], 'checks': checks, 'report': str(args.report)}))
        return 0 if report['status'] == 'passed' else 1
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
