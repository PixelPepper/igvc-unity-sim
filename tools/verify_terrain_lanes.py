#!/usr/bin/env python3
"""Read-only receipt/stamp consistency checks; no geometry truth or motion commands."""
import argparse
from collections import Counter, OrderedDict, deque
import json
import math
from pathlib import Path
import struct
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import String


def plane(value):
    normal = [float(x) for x in value['normal']]
    offset = float(value['offset'])
    if len(normal) != 3 or not all(math.isfinite(x) for x in normal + [offset]):
        raise ValueError('invalid_plane')
    if abs(sum(x*x for x in normal)-1) > 1e-5:
        raise ValueError('nonunit_plane')
    return normal + [offset]


class Verifier(Node):
    def __init__(self):
        super().__init__('verify_terrain_lanes')
        self.started = time.monotonic()
        self.planes = OrderedDict()
        self.pending = deque()
        self.counts = Counter()
        self.errors = Counter()
        self.reasons = Counter()
        self.max_age = 0.0
        self.max_points = 0
        self.create_subscription(String, '/perception/depth/status', self.depth, 10)
        self.create_subscription(String, '/perception/lanes/status', self.lanes, 10)
        self.create_subscription(PointCloud2, '/perception/lanes/points', self.cloud,
                                 qos_profile_sensor_data)

    def depth(self, msg):
        try:
            data = json.loads(msg.data)
            self.counts['depth_statuses'] += 1
            if not data.get('valid'):
                self.reasons['depth: ' + str(data.get('reason', 'unspecified'))] += 1
                return
            value = plane(data['ground'])
            stamp = int(data['stamp_ns'])
            if stamp <= 0:
                raise ValueError('invalid_depth_stamp')
            self.planes[stamp] = value
            self.planes.move_to_end(stamp)
            while len(self.planes) > 32:
                self.planes.popitem(last=False)
        except (ValueError, KeyError, TypeError, OverflowError) as exc:
            self.errors['depth_status: ' + str(exc)] += 1

    def lanes(self, msg):
        try:
            data = json.loads(msg.data)
            self.counts['lane_statuses'] += 1
            if not data.get('valid'):
                self.reasons['lanes: ' + str(data.get('reason', 'no_paint_or_unspecified'))] += 1
            if 'ground' not in data:
                self.counts['lane_statuses_without_ground'] += 1
                return
            ground = plane(data['ground'])
            rgb_stamp = int(data['stamp_ns'])
            depth_stamp = int(data['ground_stamp_ns'])
            age = float(data['ground_age_s'])
            expected = (rgb_stamp-depth_stamp)/1e9
            if rgb_stamp <= 0 or depth_stamp <= 0:
                raise ValueError('invalid_lane_stamp')
            if not math.isfinite(age) or not 0 <= expected <= .35:
                raise ValueError('ground_age_out_of_bounds')
            if abs(age-expected) > 1e-6:
                raise ValueError('ground_age_disagrees')
            self.max_age = max(self.max_age, expected)
            self.pending.append((time.monotonic(), depth_stamp, ground))
            if len(self.pending) > 32:
                self.errors['pending_overflow'] += 1
                self.pending.popleft()
        except (ValueError, KeyError, TypeError, OverflowError) as exc:
            self.errors['lane_status: ' + str(exc)] += 1

    def match(self, final=False):
        remaining = deque()
        now = time.monotonic()
        for received, stamp, ground in self.pending:
            if stamp in self.planes:
                if any(abs(a-b) > 1e-6 for a, b in zip(ground, self.planes[stamp])):
                    self.errors['ground_does_not_match_depth_fit'] += 1
                else:
                    self.counts['matched_ground_records'] += 1
            elif final or now-received > .5:
                if received-self.started <= 2:
                    self.counts['discovery_prefix_missing_planes'] += 1
                else:
                    self.errors['missing_received_depth_fit'] += 1
            else:
                remaining.append((received, stamp, ground))
        self.pending = remaining

    def cloud(self, msg):
        self.counts['cloud_messages'] += 1
        try:
            if msg.header.frame_id != 'odom':
                raise ValueError('cloud_frame_not_odom')
            if msg.header.stamp.sec*1_000_000_000 + msg.header.stamp.nanosec <= 0:
                raise ValueError('cloud_missing_stamp')
            fields = {f.name: f for f in msg.fields}
            for key in ('x', 'y', 'z'):
                f = fields[key]
                if f.datatype != 7 or f.count != 1 or f.offset+4 > msg.point_step:
                    raise ValueError('invalid_xyz_field')
            if msg.row_step < msg.width*msg.point_step or len(msg.data) != msg.row_step*msg.height:
                raise ValueError('invalid_cloud_buffer')
            fmt = '>f' if msg.is_bigendian else '<f'
            for row in range(msg.height):
                for col in range(msg.width):
                    start = row*msg.row_step + col*msg.point_step
                    if not all(math.isfinite(struct.unpack_from(fmt, msg.data, start+fields[k].offset)[0])
                               for k in ('x', 'y', 'z')):
                        raise ValueError('nonfinite_cloud_point')
            count = msg.width*msg.height
            self.max_points = max(self.max_points, count)
            if count:
                self.counts['finite_nonempty_odom_clouds'] += 1
        except (ValueError, KeyError, struct.error) as exc:
            self.errors['cloud: ' + str(exc)] += 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration', type=float, default=30)
    parser.add_argument('--report', type=Path, default=Path(__file__).resolve().parents[1] /
                        'artifacts/checks/terrain-lanes-live.json')
    args = parser.parse_args()
    if not math.isfinite(args.duration) or not 10 <= args.duration <= 120:
        parser.error('--duration must be between 10 and 120 seconds')
    rclpy.init()
    node = Verifier()
    try:
        while time.monotonic()-node.started < args.duration:
            rclpy.spin_once(node, timeout_sec=.05)
            node.match()
    except KeyboardInterrupt:
        node.errors['interrupted'] += 1
    finally:
        node.match(final=True)
        if node.counts['matched_ground_records'] <= 20:
            node.errors['requires_more_than_20_matched_records'] += 1
        if node.counts['finite_nonempty_odom_clouds'] < 20:
            node.errors['requires_at_least_20_nonempty_clouds'] += 1
        result = dict(status='passed' if not node.errors else 'failed',
                      duration_wall_s=time.monotonic()-node.started,
                      counts=dict(node.counts), errors=dict(node.errors),
                      invalid_reason_counts=dict(node.reasons), max_ground_age_s=node.max_age,
                      maximum_cloud_points=node.max_points,
                      limitations='Received fit/stamp consistency and finite stamped clouds only; '
                      'no terrain geometry truth, lane accuracy or costmap causality claim. '
                      'Depth status cache is bounded to 32; cross-topic delivery may wait 0.5 seconds. '
                      'Only missing fits received in the first 2 seconds are discovery-exempt.')
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result, indent=2))
        node.destroy_node()
        rclpy.shutdown()
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
