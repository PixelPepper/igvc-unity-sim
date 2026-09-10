"""Read-only live procedural-course sensor evidence; no commands or services."""
import argparse
from collections import Counter, OrderedDict
import json
import math
from pathlib import Path
import struct
import time

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, CameraInfo, JointState, LaserScan, PointCloud2
from nav_msgs.msg import OccupancyGrid
from std_msgs.msg import String


def stamp(m):
    return m.header.stamp.sec*1_000_000_000+m.header.stamp.nanosec


class Check(Node):
    def __init__(self, course, output):
        super().__init__('igvc_variant_sensor_verifier')
        self.output = output
        self.holes = [o for o in course['obstacles'] if o['kind'] == 'pothole']
        self.counts, self.errors = Counter(), Counter()
        self.started = time.monotonic()
        self.last = {}
        self.stamps = {}
        self.cache = {key: OrderedDict() for key in ('rgb', 'info', 'debug', 'status', 'cloud')}
        self.pitch_min, self.pitch_max = math.inf, -math.inf
        self.pitch_count = self.rgb_info_pairs = self.scan_finite = self.scan_inf = 0
        self.paired_stamps = set()
        self.fresh_stamps = set()
        self.max_cloud = self.max_fresh = self.max_matches = 0
        self.matched_holes = set()
        self.latest_points = None
        self.latest_points_wall = -math.inf
        self.costmap_checked = self.costmap_marked = 0
        self.costmap_values = Counter()
        self.best_score = -1
        self.best_images = None
        self.statuses = []
        topics = [('rgb', Image, '/camera/color/image_raw'),
                  ('info', CameraInfo, '/camera/color/camera_info'),
                  ('joint', JointState, '/joint_states'),
                  ('cloud', PointCloud2, '/perception/hazards/points'),
                  ('debug', Image, '/perception/hazards/debug'),
                  ('status', String, '/perception/lanes/status'),
                  ('hazard_status', String, '/perception/hazards/status'),
                  ('scan', LaserScan, '/scan'),
                  ('costmap', OccupancyGrid, '/local_costmap/costmap')]
        for key, kind, topic in topics:
            self.create_subscription(kind, topic, lambda m, k=key: self.receive(k, m), qos_profile_sensor_data)

    def keep(self, key, ns, value):
        self.cache[key][ns] = value
        while len(self.cache[key]) > 40:
            self.cache[key].popitem(last=False)

    def receive(self, key, m):
        self.counts[key] += 1
        self.last[key] = time.monotonic()
        try:
            if key in ('status', 'hazard_status'):
                value = json.loads(m.data)
                self.statuses.append(value)
                self.statuses = self.statuses[-20:]
                if 'stamp_ns' in value:
                    self.keep('status', int(value['stamp_ns']), value)
            elif key == 'joint':
                if 'camera_pitch_joint' in m.name:
                    v = m.position[m.name.index('camera_pitch_joint')]
                    if not math.isfinite(v):
                        raise ValueError('nonfinite_pitch')
                    self.pitch_count += 1
                    self.pitch_min, self.pitch_max = min(self.pitch_min, v), max(self.pitch_max, v)
            elif key == 'scan':
                values = np.asarray(m.ranges)
                self.scan_finite += int(np.isfinite(values).sum())
                self.scan_inf += int(np.isposinf(values).sum())
                if np.isnan(values).any() or np.isneginf(values).any():
                    raise ValueError('invalid_scan_numeric')
            elif key == 'costmap':
                self.inspect_map(m)
            else:
                ns = stamp(m)
                if ns < self.stamps.get(key, ns):
                    self.errors[key+'_backward_stamp'] += 1
                self.stamps[key] = ns
                if key == 'rgb':
                    if m.encoding != 'rgb8' or m.step < m.width*3 or len(m.data) != m.height*m.step:
                        raise ValueError('rgb_format')
                if key == 'debug' and (m.encoding != 'mono8' or m.step < m.width):
                    raise ValueError('debug_format')
                if key == 'cloud':
                    if m.header.frame_id != 'odom':
                        raise ValueError('hazard_cloud_not_odom')
                    fields = {f.name: f for f in m.fields}
                    if any(k not in fields or fields[k].datatype != 7 for k in ('x', 'y', 'z')):
                        raise ValueError('hazard_cloud_fields')
                    endian = '>' if m.is_bigendian else '<'
                    points = np.array([[struct.unpack_from(endian+'f', m.data, row*m.row_step+col*m.point_step+fields[k].offset)[0]
                                        for k in ('x', 'y', 'z')]
                                       for row in range(m.height) for col in range(m.width)], dtype=float).reshape(-1, 3)
                    if not np.isfinite(points).all():
                        raise ValueError('nonfinite_hazard_cloud')
                    self.latest_points, self.latest_points_wall = points, time.monotonic()
                    self.max_cloud = max(self.max_cloud, len(points))
                    self.keep(key, ns, points)
                    matches, ids = self.match(points)
                    self.max_matches = max(self.max_matches, int(matches.sum()))
                    self.matched_holes.update(ids)
                else:
                    self.keep(key, ns, m)
            self.pair_evidence()
        except (ValueError, IndexError, struct.error, KeyError) as exc:
            self.errors[str(exc)] += 1

    def match(self, points):
        matched = np.zeros(len(points), dtype=bool)
        ids = []
        for hole in self.holes:
            radius = float(hole.get('radius', max(hole['length'], hole['width'])/2))
            near = np.linalg.norm(points[:, :2]-[hole['x'], hole['y']], axis=1) <= radius+.5
            if near.any():
                ids.append(hole['id'])
            matched |= near
        return matched, ids

    def pair_evidence(self):
        for ns in self.cache['rgb'].keys() & self.cache['info'].keys():
            if ns in self.paired_stamps:
                continue
            image, info = self.cache['rgb'][ns], self.cache['info'][ns]
            if ((image.width, image.height, image.header.frame_id) != (info.width, info.height, info.header.frame_id)
                    or not all(math.isfinite(v) for v in info.k) or info.k[0] <= 0 or info.k[4] <= 0):
                self.errors['rgb_info_mismatch'] += 1
            else:
                self.rgb_info_pairs += 1
            self.paired_stamps.add(ns)
        for ns in self.cache['cloud'].keys() & self.cache['status'].keys():
            current = int(self.cache['status'][ns].get('hazard_points', 0))
            if current > 0 and len(self.cache['cloud'][ns]) > 0:
                self.fresh_stamps.add(ns)
                self.max_fresh = max(self.max_fresh, current)
            if current > self.best_score and current > 0 and ns in self.cache['rgb'] and ns in self.cache['debug']:
                self.best_score = current
                self.best_images = (ns, self.cache['rgb'][ns], self.cache['debug'][ns])

    def inspect_map(self, m):
        if self.latest_points is None or time.monotonic()-self.latest_points_wall > .75:
            return
        if m.header.frame_id != 'odom' or m.info.resolution <= 0:
            raise ValueError('costmap_frame_or_resolution')
        q = m.info.origin.orientation
        yaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
        matches, _ = self.match(self.latest_points)
        cells = set()
        for x, y, _ in self.latest_points[matches]:
            dx, dy = x-m.info.origin.position.x, y-m.info.origin.position.y
            cx = math.floor((math.cos(yaw)*dx+math.sin(yaw)*dy)/m.info.resolution)
            cy = math.floor((-math.sin(yaw)*dx+math.cos(yaw)*dy)/m.info.resolution)
            if 0 <= cx < m.info.width and 0 <= cy < m.info.height:
                cells.add((cx, cy))
        for cx, cy in cells:
            value = int(m.data[cy*m.info.width+cx])
            self.costmap_values[value] += 1
            self.costmap_checked += 1
            self.costmap_marked += int(value >= 99)

    def report(self, duration):
        saved = []
        if self.best_images:
            ns, rgb, mask = self.best_images
            image = np.frombuffer(rgb.data, np.uint8).reshape(rgb.height, rgb.step)[:, :rgb.width*3].reshape(rgb.height, rgb.width, 3)
            mono = np.frombuffer(mask.data, np.uint8).reshape(mask.height, mask.step)[:, :mask.width]
            for name, pixels in [('hazard-rgb.png', cv2.cvtColor(image, cv2.COLOR_RGB2BGR)), ('hazard-mask.png', mono)]:
                if not cv2.imwrite(str(self.output/name), pixels):
                    raise RuntimeError('PNG save failed: '+name)
                saved.append(name)
        checks = dict(rgb_info_observed=self.rgb_info_pairs > 0,
                      scan_observed=self.scan_finite > 0,
                      pitch_10deg=self.pitch_count > 0 and max(abs(self.pitch_min-math.pi/18), abs(self.pitch_max-math.pi/18)) <= 1e-4,
                      fresh_positive_hazards_observed=bool(self.fresh_stamps),
                      manifest_matches_observed=self.max_matches > 0,
                      matched_costmap_marks_observed=self.costmap_marked > 0,
                      exact_stamp_images_saved=bool(saved), no_numeric_or_format_errors=not self.errors)
        return dict(status='passed' if all(checks.values()) else 'incomplete_or_failed', checks=checks,
                    duration_wall_s=duration, counts=dict(self.counts), rates_hz={k: v/duration for k, v in self.counts.items()},
                    errors=dict(self.errors), pitch_samples=self.pitch_count,
                    pitch_min_rad=self.pitch_min if self.pitch_count else None, pitch_max_rad=self.pitch_max if self.pitch_count else None,
                    rgb_info_exact_pairs=self.rgb_info_pairs, scan_finite_values=self.scan_finite, scan_positive_infinity_values=self.scan_inf,
                    fresh_positive_hazard_frames=len(self.fresh_stamps), max_current_projected_hazard_points=self.max_fresh,
                    max_accumulated_hazard_points=self.max_cloud, max_manifest_matched_points=self.max_matches,
                    observed_pothole_ids=sorted(self.matched_holes), manifest_pothole_count=len(self.holes),
                    matched_costmap_cell_observations=self.costmap_checked, marked_costmap_cell_observations=self.costmap_marked,
                    costmap_value_counts=dict(self.costmap_values), images=saved,
                    image_stamp_ns=self.best_images[0] if self.best_images else None, last_statuses=self.statuses,
                    limitations='Manifest matching is verifier-only, radius + 0.5 m. Clouds contain accumulated observations; '
                    'fresh detection requires same-stamp status with positive current hazard_points. Costmap marks are observed '
                    'on the combined map and do not establish exclusive layer causality. Unseen holes are not passes.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--course', type=Path, required=True)
    parser.add_argument('--duration', type=float, default=120.)
    args = parser.parse_args()
    if not math.isfinite(args.duration) or args.duration <= 0:
        parser.error('duration must be finite and positive')
    course = json.loads(args.course.read_text())
    if course.get('frame') != 'odom':
        raise ValueError('Manifest frame must be odom')
    rclpy.init(args=[])
    node = Check(course, args.course.parent)
    start = time.monotonic()
    try:
        while time.monotonic()-start < args.duration:
            rclpy.spin_once(node, timeout_sec=.1)
        result = node.report(time.monotonic()-start)
        (args.course.parent/'sensors.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps({k: result[k] for k in ('status', 'checks', 'fresh_positive_hazard_frames', 'max_manifest_matched_points', 'marked_costmap_cell_observations')}, indent=2))
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
