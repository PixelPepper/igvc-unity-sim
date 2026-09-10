#!/usr/bin/env python3
"""Read-only live lane observation validation; publishes no robot commands."""
import argparse
import json
import math
from pathlib import Path
import time

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import Image, PointCloud2, LaserScan
from nav_msgs.msg import Odometry, OccupancyGrid
from std_msgs.msg import Bool, String
from tf2_ros import Buffer, TransformListener, TransformException


class LaneCheck(Node):
    def __init__(self):
        super().__init__('igvc_lane_readonly_check')
        self.counts = dict(points=0, debug=0, status=0, valid=0, scan=0, odom=0, costmap=0)
        self.latest = {}
        self.statuses = []
        self.valid_true = 0
        self.tf = Buffer()
        self.listener = TransformListener(self.tf, self)
        for key, kind, topic in [('points', PointCloud2, '/perception/lanes/points'),
                                 ('debug', Image, '/perception/lanes/debug'),
                                 ('status', String, '/perception/lanes/status'),
                                 ('valid', Bool, '/perception/lanes/valid'),
                                 ('scan', LaserScan, '/scan'), ('odom', Odometry, '/odom'),
                                 ('costmap', OccupancyGrid, '/global_costmap/costmap')]:
            self.create_subscription(kind, topic, lambda msg, k=key: self.receive(k, msg), qos_profile_sensor_data)

    def receive(self, key, message):
        self.counts[key] += 1
        self.latest[key] = message
        if key == 'status':
            try:
                value = json.loads(message.data)
            except ValueError:
                value = {'raw': message.data}
            self.statuses.append(value)
            self.statuses = self.statuses[-100:]
        if key == 'valid':
            self.valid_true += int(message.data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration', type=float, default=10)
    parser.add_argument('--report', type=Path, default=Path(__file__).resolve().parent.parent/'artifacts/checks/lanes-live.json')
    args = parser.parse_args()
    rclpy.init(args=[])
    node = LaneCheck()
    start = time.monotonic()
    try:
        while time.monotonic()-start < args.duration:
            rclpy.spin_once(node, timeout_sec=.05)
        elapsed = time.monotonic()-start
        report = {'duration_wall_s': elapsed, 'counts': node.counts,
                  'rates_hz': {k: v/elapsed for k, v in node.counts.items()},
                  'valid_true': node.valid_true, 'statuses': node.statuses, 'checks': {}}
        checks = report['checks']
        checks['all_streams_received'] = all(node.counts.values())
        checks['lane_rate_at_least_3hz'] = node.counts['points']/elapsed >= 3
        checks['current_detection_valid'] = node.latest.get('valid', Bool()).data
        if 'debug' in node.latest:
            msg = node.latest['debug']
            checks['debug_mask_format'] = msg.encoding == 'mono8' and msg.width == 640 and msg.height == 480
            mask = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.step)[:, :msg.width]
            png = args.report.with_suffix('.png')
            png.parent.mkdir(parents=True, exist_ok=True)
            checks['debug_saved'] = bool(cv2.imwrite(str(png), mask))
            report['debug_white_pixels'] = int(np.count_nonzero(mask))
        if 'points' in node.latest:
            cloud = node.latest['points']
            checks['cloud_odom_xyz'] = cloud.header.frame_id == 'odom' and cloud.point_step == 12
            xyz = np.frombuffer(cloud.data, dtype='<f4').reshape(-1, 3)
            checks['cloud_finite'] = bool(np.isfinite(xyz).all())
            report['point_count'] = len(xyz)
            if len(xyz):
                report['bounds_m'] = [xyz.min(0).tolist(), xyz.max(0).tolist()]
            # Allow transport/TF callback queues to catch up to this specific stamp.
            deadline = time.monotonic()+1
            transform = None
            while time.monotonic() < deadline:
                try:
                    transform = node.tf.lookup_transform('odom', 'camera_color_optical_frame', Time.from_msg(cloud.header.stamp))
                    break
                except TransformException:
                    rclpy.spin_once(node, timeout_sec=.01)
            checks['camera_tf_at_cloud_acquisition'] = transform is not None
            if transform is not None and len(xyz):
                p = transform.transform.translation
                distance = np.linalg.norm(xyz[:, :2]-[p.x, p.y], axis=1)
                report['point_range_m'] = [float(distance.min()), float(distance.max())]
                report['points_3_to_8m'] = int(((distance >= 3)&(distance <= 8)).sum())
            if 'costmap' in node.latest and len(xyz):
                costmap = node.latest['costmap']
                checks['costmap_frame_matches_cloud'] = costmap.header.frame_id == cloud.header.frame_id
                origin = costmap.info.origin
                checks['costmap_axis_aligned'] = abs(origin.orientation.x)+abs(origin.orientation.y)+abs(origin.orientation.z) < 1e-8
                grid = np.asarray(costmap.data, dtype=np.int16).reshape(costmap.info.height, costmap.info.width)
                cells = np.floor((xyz[:, :2]-[origin.position.x, origin.position.y])/costmap.info.resolution).astype(int)
                inside = (cells[:, 0]>=0)&(cells[:, 0]<costmap.info.width)&(cells[:, 1]>=0)&(cells[:, 1]<costmap.info.height)
                cells = np.unique(cells[inside], axis=0)
                lethal = int((grid[cells[:, 1], cells[:, 0]]==100).sum()) if len(cells) else 0
                report['lane_costmap_cells'] = {'unique_inside': len(cells), 'lethal': lethal,
                                                'lethal_fraction': lethal/len(cells) if len(cells) else 0,
                                                'resolution_m': costmap.info.resolution,
                                                'note': 'Spatial correspondence does not alone distinguish lane marking from overlapping obstacle inflation.'}
                checks['lane_points_in_lethal_cells'] = len(cells)>0 and lethal/len(cells)>=.8
        report['status'] = 'passed' if all(checks.values()) else 'failed'
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps({k: report[k] for k in ('status', 'counts', 'rates_hz', 'checks')}))
        return int(report['status'] != 'passed')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
