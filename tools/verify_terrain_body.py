#!/usr/bin/env python3
"""Command a bounded manual bench traversal; never reset or enable autonomy."""
import argparse
from collections import Counter, OrderedDict
import json
import math
from pathlib import Path
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data, QoSProfile, DurabilityPolicy
from geometry_msgs.msg import TransformStamped, Twist
from nav_msgs.msg import Odometry
from tf2_msgs.msg import TFMessage


def height(x):
    if x < 2: return 0.
    if x < 5: return .4*(x-2)/3
    if x < 7: return .4
    if x < 10: return .4*(10-x)/3
    return 0.


def stamp(msg):
    return msg.header.stamp.sec*1_000_000_000+msg.header.stamp.nanosec


def angles(q):
    values = (q.x, q.y, q.z, q.w)
    if not all(map(math.isfinite, values)) or abs(sum(v*v for v in values)-1) > 1e-4:
        raise ValueError('invalid_quaternion')
    # atan2 form remains stable for the small pure pitch expected on this bench.
    pitch = math.atan2(2*(q.w*q.y-q.z*q.x), 1-2*(q.x*q.x+q.y*q.y))
    roll = math.atan2(2*(q.w*q.x+q.y*q.z), 1-2*(q.x*q.x+q.y*q.y))
    yaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
    return roll, pitch, yaw


class Bench(Node):
    def __init__(self, speed):
        super().__init__('verify_terrain_body')
        self.requested_speed = speed
        self.previous_axle = None
        self.command = self.create_publisher(Twist, '/cmd_vel/teleop', 10)
        self.cache = {'odom': OrderedDict(), 'body': OrderedDict()}
        self.errors = Counter()
        self.matches = 0
        self.latest = None
        self.last_pair_wall = None
        self.last_stamp = None
        self.maximum = dict(position_error_m=0., pitch_error_rad=0., speed_mps=0., axle_3d_speed_mps=0.)
        self.min_pitch = float('inf'); self.max_pitch = -float('inf')
        self.max_body_z = -float('inf')
        self.ready = False
        self.create_subscription(Odometry, '/odom', lambda m:self.receive('odom',m), qos_profile_sensor_data)
        self.create_subscription(TransformStamped, '/sim/body_transform', lambda m:self.receive('body',m), 10)
        self.create_subscription(TFMessage, '/tf_static', self.static,
                                 QoSProfile(depth=100, durability=DurabilityPolicy.TRANSIENT_LOCAL))

    def static(self, msg):
        if any(t.child_frame_id.lstrip('/') == 'base_link' for t in msg.transforms):
            self.errors['static_base_link_transform'] += 1

    def receive(self, kind, msg):
        key = stamp(msg)
        cache = self.cache[kind]
        cache[key] = (msg, time.monotonic())
        while len(cache) > 64: cache.popitem(last=False)
        other = 'body' if kind == 'odom' else 'odom'
        if key not in self.cache[other]: return
        odom, arrival = self.cache['odom'].pop(key)
        body, body_arrival = self.cache['body'].pop(key)
        try:
            if key <= 0 or (self.last_stamp is not None and key <= self.last_stamp):
                raise ValueError('nonincreasing_pair_stamp')
            if time.monotonic()-min(arrival, body_arrival) > .5:
                raise ValueError('stale_pair_receipt')
            if odom.header.frame_id != 'odom' or odom.child_frame_id != 'base_footprint':
                raise ValueError('odom_frames')
            if body.header.frame_id != 'base_footprint' or body.child_frame_id != 'base_link':
                raise ValueError('body_frames')
            pos = odom.pose.pose.position
            roll, opitch, yaw = angles(odom.pose.pose.orientation)
            broll, pitch, byaw = angles(body.transform.rotation)
            t = body.transform.translation
            velocity = odom.twist.twist.linear
            speed = math.sqrt(velocity.x**2+velocity.y**2+velocity.z**2)
            if not all(map(math.isfinite, [pos.x,pos.y,pos.z,t.x,t.y,t.z,speed])):
                raise ValueError('nonfinite_state')
            if abs(pos.y) >= .05 or abs(pos.z) > .005 or max(abs(roll),abs(opitch),abs(yaw)) > .005:
                raise ValueError('footprint_off_straight_flat_datum')
            if speed > self.requested_speed+.001: raise ValueError('speed_exceeds_limit')
            axle = (pos.x, pos.y, height(pos.x))
            if self.previous_axle is not None:
                previous_stamp, previous_position = self.previous_axle
                dt = (key-previous_stamp)/1e9
                chord_speed = math.dist(axle, previous_position)/dt
                self.maximum['axle_3d_speed_mps'] = max(self.maximum['axle_3d_speed_mps'], chord_speed)
                if chord_speed > self.requested_speed+.002:
                    raise ValueError('axle_3d_speed_exceeds_limit')
            self.previous_axle = (key, axle)
            expected_pitch = -math.atan((height(pos.x)-height(pos.x-.85))/.85)
            expected_x = -.25591*math.cos(expected_pitch)+.30385548*math.sin(expected_pitch)
            expected_z = height(pos.x)+.25591*math.sin(expected_pitch)+.30385548*math.cos(expected_pitch)
            position_error = max(abs(t.x-expected_x), abs(t.y), abs(t.z-expected_z))
            pitch_error = abs(pitch-expected_pitch)
            self.maximum['position_error_m'] = max(self.maximum['position_error_m'], position_error)
            self.maximum['pitch_error_rad'] = max(self.maximum['pitch_error_rad'], pitch_error)
            self.maximum['speed_mps'] = max(self.maximum['speed_mps'],speed)
            if position_error > .01: raise ValueError('body_translation_mismatch')
            if pitch_error > .005 or abs(broll) > .005 or abs(byaw) > .005:
                raise ValueError('body_rotation_mismatch')
            self.matches += 1
            self.min_pitch = min(self.min_pitch,pitch); self.max_pitch = max(self.max_pitch,pitch)
            self.max_body_z = max(self.max_body_z,t.z)
            self.latest = dict(stamp_ns=key,x=pos.x,y=pos.y,body_z=t.z,pitch=pitch)
            self.last_pair_wall = time.monotonic()
            self.last_stamp = key
            if not self.ready:
                if abs(pos.x) > .05 or speed > .01:
                    raise ValueError('requires_stationary_origin_start')
                self.ready = True
        except (ValueError, OverflowError) as exc:
            self.errors[str(exc)] += 1

    def publish(self, speed):
        msg = Twist(); msg.linear.x = speed
        self.command.publish(msg)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--speed', type=float, default=.3)
    parser.add_argument('--report', type=Path, default=Path(__file__).resolve().parents[1] /
                        'artifacts/checks/terrain-body-live.json')
    args = parser.parse_args()
    if not math.isfinite(args.speed) or not .1 <= args.speed <= 2.2:
        parser.error('--speed must be finite and between 0.1 and 2.2 m/s')
    rclpy.init(); node = Bench(args.speed)
    start = time.monotonic(); drive_start = None; finished = False
    try:
        while not node.ready and not node.errors and time.monotonic()-start < 10:
            rclpy.spin_once(node, timeout_sec=.05)
        if not node.ready:
            node.errors['no_valid_flat_start_pair_within_10s'] += 1
        if not node.errors:
            drive_start = time.monotonic(); next_command = drive_start
            while time.monotonic()-drive_start < 55 and not node.errors:
                now = time.monotonic()
                if now-node.last_pair_wall > .5:
                    node.errors['fresh_pair_lost'] += 1
                    break
                if node.latest['x'] >= 11:
                    finished = True
                    break
                if now >= next_command:
                    node.publish(args.speed)
                    next_command = now+.05
                rclpy.spin_once(node, timeout_sec=max(0., min(.01,next_command-time.monotonic())))
    except KeyboardInterrupt:
        node.errors['interrupted'] += 1
    except Exception as exc:
        node.errors['runtime: '+str(exc)] += 1
    finally:
        # Repeated zero commands are sent even on failed preflight or an exception.
        for _ in range(10):
            node.publish(0.)
            deadline = time.monotonic()+.05
            while time.monotonic() < deadline and rclpy.ok():
                rclpy.spin_once(node, timeout_sec=.01)
        checks = dict(finished_x_at_least_11=finished,
                      at_least_100_matched_pairs=node.matches >= 100,
                      climbing_pitch=node.min_pitch < -.08,
                      descending_pitch=node.max_pitch > .08,
                      deck_body_height=node.max_body_z > .69,
                      finish_flat_height=bool(node.latest and node.latest['x'] >= 11 and
                                              abs(node.latest['body_z']-.30385548) <= .01))
        for key, passed in checks.items():
            if not passed: node.errors[key] += 1
        report = dict(requested_speed_mps=args.speed, status='passed' if not node.errors else 'failed',checks=checks,
                      errors=dict(node.errors),matched_pairs=node.matches,final=node.latest,
                      maximum=node.maximum,
                      minimum_pitch_rad=node.min_pitch if math.isfinite(node.min_pitch) else None,
                      maximum_pitch_rad=node.max_pitch if math.isfinite(node.max_pitch) else None,
                      maximum_body_z=node.max_body_z if math.isfinite(node.max_body_z) else None,
                      duration_wall_s=time.monotonic()-start,
                      limitations='Independent analytic ramp-support transform check, not contact physics. '
                      'No reset, autonomy enable or navigation goals; manual straight command only.')
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
        node.destroy_node()
        if rclpy.ok(): rclpy.shutdown()
    return 0 if report['status']=='passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
