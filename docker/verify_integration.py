"""Read-only container transport check, valid on both flat and ramp course sections."""
import argparse
from collections import Counter, OrderedDict
import json
import math
from pathlib import Path
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, CameraInfo, LaserScan, JointState
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock
from tf2_ros import Buffer, TransformListener
from rclpy.time import Time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration', type=float, default=20)
    parser.add_argument('--report', type=Path, default=Path('/opt/igvc/artifacts/checks/docker-integration.json'))
    args = parser.parse_args()
    if not 10 <= args.duration <= 120:
        parser.error('duration must be 10..120 seconds')
    rclpy.init()
    node = Node('docker_integration_verifier')
    buffer = Buffer()
    listener = TransformListener(buffer, node)
    counts, errors, pairs = Counter(), Counter(), Counter()
    last, stamps, cache = {}, {}, {k: OrderedDict() for k in ('rgb', 'rgb_info', 'depth', 'depth_info')}

    def receive(key, msg):
        counts[key] += 1
        last[key] = time.monotonic()
        if key == 'clock':
            ns = msg.clock.sec * 10**9 + msg.clock.nanosec
            if ns < stamps.get(key, ns): errors['clock_regression'] += 1
            stamps.setdefault('clock_first', ns)
            stamps[key] = ns
        elif key in cache:
            ns = msg.header.stamp.sec * 10**9 + msg.header.stamp.nanosec
            cache[key][ns] = (msg.width, msg.height, msg.header.frame_id)
            if key in ('rgb', 'depth'):
                expected = ('rgb8', 3) if key == 'rgb' else ('32FC1', 4)
                if msg.encoding != expected[0] or msg.step != msg.width * expected[1] or len(msg.data) != msg.step * msg.height:
                    errors[key + '_encoding'] += 1
            partner = key[:-5] if key.endswith('_info') else key + '_info'
            if ns in cache[partner]:
                if cache[key][ns] != cache[partner][ns]: errors['camera_pair'] += 1
                else: pairs[key.replace('_info', '')] += 1
                del cache[key][ns]
                del cache[partner][ns]
            while len(cache[key]) > 100: cache[key].popitem(last=False)
        elif key == 'scan':
            if msg.header.frame_id != 'lidar_link' or len(msg.ranges) != 360:
                errors['scan_metadata'] += 1
            if any(math.isnan(v) or v < msg.range_min or (math.isfinite(v) and v > msg.range_max) for v in msg.ranges):
                errors['scan_range'] += 1
            counts['finite_scan_returns'] += sum(math.isfinite(v) for v in msg.ranges)
        elif key == 'odom':
            if msg.header.frame_id != 'odom' or msg.child_frame_id != 'base_footprint': errors['odom_frames'] += 1
        elif key == 'joints':
            if len(msg.name) != 7 or len(msg.position) != 7 or not all(math.isfinite(v) for v in msg.position): errors['joint_state'] += 1

    topics = [('clock', Clock, '/clock'), ('odom', Odometry, '/odom'),
              ('rgb', Image, '/camera/color/image_raw'), ('rgb_info', CameraInfo, '/camera/color/camera_info'),
              ('depth', Image, '/camera/depth/image_raw'), ('depth_info', CameraInfo, '/camera/depth/camera_info'),
              ('scan', LaserScan, '/scan'), ('joints', JointState, '/joint_states')]
    subscriptions = [node.create_subscription(kind, topic, lambda m, k=key: receive(k, m), qos_profile_sensor_data) for key, kind, topic in topics]
    start = time.monotonic()
    try:
        while time.monotonic() - start < args.duration: rclpy.spin_once(node, timeout_sec=.05)
        now = time.monotonic()
        rates = {key: counts[key] / (now-start) for key, _, _ in topics}
        checks = {'streams_fresh': all(now-last.get(key, -math.inf) < 1 for key, _, _ in topics),
                  'stream_rates': all(rates[key] >= minimum for key, minimum in [('rgb', 8), ('depth', 5), ('scan', 4), ('odom', 30), ('joints', 15)]),
                  'clock_advancing': stamps.get('clock', 0) > stamps.get('clock_first', 0),
                  'rgb_info_pairs': pairs['rgb'] >= 20, 'depth_info_pairs': pairs['depth'] >= 20,
                  'valid_payloads': not errors,
                  'robot_sensor_tf': all(buffer.can_transform('odom', frame, Time()) for frame in ['base_link', 'lidar_link', 'camera_color_optical_frame', 'left_caster', 'right_caster'])}
        result = dict(passed=all(checks.values()), checks=checks, rates_hz=rates, errors=dict(errors), pairs=dict(pairs), finite_scan_returns=counts['finite_scan_returns'], duration_s=now-start)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result, indent=2))
        return 0 if result['passed'] else 1
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
