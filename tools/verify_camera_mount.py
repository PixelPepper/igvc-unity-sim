#!/usr/bin/env python3
"""Live camera hinge/TF/calibration checks; run with the R3-a session active."""
import argparse
from collections import OrderedDict
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'ros2/src/igvc_sim_bridge'))
from igvc_sim_bridge.verify_probe import Verify
import rclpy
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import CameraInfo
from std_msgs.msg import Float64
from geometry_msgs.msg import Twist
from tf2_ros import TransformException

PIVOT = (-.34396836, 0, .8)
BODY_OFFSET = (.06290043, 0, .00447802)
OPTICAL_OFFSET = (.01155045, 0, .00476378)
LIMIT = math.pi / 6


def rotated_y(point, angle):
    x, y, z = point
    return (math.cos(angle)*x + math.sin(angle)*z, y,
            -math.sin(angle)*x + math.cos(angle)*z)


def sum_vectors(a, b):
    return tuple(x+y for x, y in zip(a, b))


def translated(transform):
    p = transform.transform.translation
    return (p.x, p.y, p.z)


def rotate_quaternion(rotation, vector):
    q = (rotation.x, rotation.y, rotation.z)
    def cross(a, b):
        return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
    uv = cross(q, vector)
    uuv = cross(q, uv)
    return tuple(v + 2*(rotation.w*a+b) for v, a, b in zip(vector, uv, uuv))


class CameraVerify(Verify):
    def __init__(self):
        self.images, self.infos = OrderedDict(), OrderedDict()
        super().__init__('r3a')
        self.pitch = self.create_publisher(Float64, '/sim/camera_pitch_command', 1)
        self.create_subscription(CameraInfo, '/camera/color/camera_info', self.camera_info, qos_profile_sensor_data)

    @staticmethod
    def remember(cache, stamp, value):
        cache[stamp] = (value, time.monotonic())
        while len(cache) > 64:
            cache.popitem(last=False)

    def receive(self, key, msg):
        super().receive(key, msg)
        if key == 'image':
            self.remember(self.images, self.nanoseconds(msg.header.stamp),
                          {'width': msg.width, 'height': msg.height, 'frame': msg.header.frame_id,
                           'encoding': msg.encoding, 'step': msg.step, 'bytes': len(msg.data)})

    def camera_info(self, msg):
        self.remember(self.infos, self.nanoseconds(msg.header.stamp), msg)

    def command_pitch(self, angle, duration=0.8):
        samples = {}
        end = time.monotonic() + duration
        while time.monotonic() < end:
            self.pitch.publish(Float64(data=float(angle)))
            self.wait(.05)
            for stamp, (joint, _) in self.history['joints'].items():
                if 'camera_pitch_joint' in joint.name:
                    samples[stamp] = joint.position[joint.name.index('camera_pitch_joint')]
        return samples

    def snapshot(self, after=0):
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            common = self.history['joints'].keys() & self.history['odom'].keys()
            if common:
                stamp = max(common)
                joints, arrival = self.history['joints'][stamp]
                odom, odom_arrival = self.history['odom'][stamp]
                recent = (stamp > after and time.monotonic()-min(arrival, odom_arrival) < .5
                          and 0 <= self.nanoseconds(self.last['odom'].header.stamp)-stamp <= 100_000_000)
                if recent and 'camera_pitch_joint' in joints.name:
                    index = joints.name.index('camera_pitch_joint')
                    assert len(joints.position) == len(joints.name), 'Joint positions/names length mismatch'
                    pitch = joints.position[index]
                    assert math.isfinite(pitch), 'Pitch is nonfinite'
                    when = Time.from_msg(joints.header.stamp)
                    try:
                        chain = [self.tf_buffer.lookup_transform(a, b, when) for a, b in
                                 [('base_link', 'camera_mount_link'), ('camera_mount_link', 'camera_link'),
                                  ('camera_link', 'camera_color_optical_frame')]]
                        body = self.tf_buffer.lookup_transform('base_link', 'camera_link', when)
                        optical = self.tf_buffer.lookup_transform('base_link', 'camera_color_optical_frame', when)
                        assert self.nanoseconds(optical.header.stamp) == stamp, 'Optical TF stamp mismatch'
                        return {'stamp_ns': stamp, 'pitch': pitch, 'odom': odom,
                                'body': body, 'optical': optical, 'chain': chain}
                    except TransformException:
                        pass
            rclpy.spin_once(self, timeout_sec=.01)
        raise AssertionError('No fresh same-stamp joint/odom/camera TF snapshot')

    def image_info_pair(self, after=0):
        deadline = time.monotonic()+5
        while time.monotonic() < deadline:
            common = self.images.keys() & self.infos.keys()
            if common:
                stamp = max(common)
                image, image_wall = self.images[stamp]
                info, info_wall = self.infos[stamp]
                if stamp > after and time.monotonic()-min(image_wall, info_wall) < .5:
                    return stamp, image, info
            rclpy.spin_once(self, timeout_sec=.01)
        raise AssertionError('No fresh RGB/CameraInfo pair with identical acquisition stamps')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, default=ROOT / 'artifacts/checks/camera-mount-live.json')
    args = parser.parse_args()
    default_pitch = json.loads((ROOT / 'ros2/src/igvc_description/config/camera_mount.json').read_text())['default_simulation_pitch_rad']
    rclpy.init(args=[])
    node = CameraVerify()
    report = {'status': 'failed', 'checks': {}, 'samples': {},
              'expected': {'pivot_m': PIVOT, 'body_offset_m': BODY_OFFSET, 'optical_offset_m': OPTICAL_OFFSET}}

    def check(name, condition):
        report['checks'][name] = bool(condition)
        print(('PASS ' if condition else 'FAIL ') + name, flush=True)
        assert condition, name

    def geometry(label, expected_pitch, after=0):
        snap = node.snapshot(after)
        q = snap['pitch']
        check(label+'_joint_pitch', abs(q-expected_pitch) < .005)
        check(label+'_body_tf', math.dist(translated(snap['body']), sum_vectors(PIVOT, rotated_y(BODY_OFFSET, q))) < .0001)
        expected_position = sum_vectors(PIVOT, rotated_y(sum_vectors(BODY_OFFSET, OPTICAL_OFFSET), q))
        check(label+'_optical_tf', math.dist(translated(snap['optical']), expected_position) < .0001)
        rotation = snap['optical'].transform.rotation
        forward = rotate_quaternion(rotation, (0, 0, 1))
        up = rotate_quaternion(rotation, (0, -1, 0))
        check(label+'_optical_axes', math.dist(forward, rotated_y((1, 0, 0), q)) < .0001
              and math.dist(up, rotated_y((0, 0, 1), q)) < .0001)
        pose = snap['odom'].pose.pose
        check(label+'_robot_stationary', math.hypot(pose.position.x, pose.position.y) < .005
              and abs(pose.orientation.z) < .005)
        report['samples'][label] = {'stamp_ns': snap['stamp_ns'], 'pitch_rad': q,
                                    'optical_xyz_m': translated(snap['optical']), 'optical_forward': forward}
        return snap

    try:
        # Discovery can expose services before Unity finishes topic registration.
        deadline = time.monotonic() + 40
        while not all(node.counts.values()) and time.monotonic() < deadline:
            node.wait(.2)
        check('all_streams_ready_before_control', all(node.counts.values()))
        node.wait(1)
        node.service('estop', False); node.service('pause', False); node.service('reset')
        node.wait(.5, 0)
        geometry('startup_default', default_pitch)
        node.command_pitch(0)
        initial = geometry('neutral', 0)
        motion = node.command_pitch(.2)
        down = geometry('down', .2, initial['stamp_ns'])
        samples = sorted((stamp, q) for stamp, q in motion.items() if stamp >= initial['stamp_ns'])
        rates = [abs(q1-q0)/((t1-t0)*1e-9) for (t0, q0), (t1, q1) in zip(samples, samples[1:]) if t1 > t0]
        check('pitch_slew_limit', len(rates) >= 3 and max(rates) <= 1.05 and any(rate > .1 for rate in rates))
        report['max_observed_pitch_slew_rad_s'] = max(rates)
        check('positive_pitch_looks_down', report['samples']['down']['optical_forward'][2] < -.19)
        node.command_pitch(-.2)
        up = geometry('up', -.2, down['stamp_ns'])
        check('negative_pitch_looks_up', report['samples']['up']['optical_forward'][2] > .19)
        node.command_pitch(10, 1.2)
        upper = geometry('upper_clamp', LIMIT, up['stamp_ns'])
        node.command_pitch(-10, 1.5)
        lower = geometry('lower_clamp', -LIMIT, upper['stamp_ns'])
        node.service('reset'); node.wait(.3)
        reset = geometry('reset', default_pitch, lower['stamp_ns'])
        node.service('pause', True)
        node.command_pitch(.2, .4)
        node.service('pause', False); node.wait(.3)
        resumed = geometry('paused_command_ignored', default_pitch, reset['stamp_ns'])
        node.service('estop', True); node.command_pitch(-.2, .4)
        node.service('estop', False); node.wait(.3)
        geometry('stopped_command_ignored', default_pitch, resumed['stamp_ns'])
        stamp, image, info = node.image_info_pair(reset['stamp_ns'])
        check('rgb_info_exact_stamp_pair', stamp == node.nanoseconds(info.header.stamp))
        check('rgb_info_optical_frame', image['frame'] == info.header.frame_id == 'camera_color_optical_frame')
        check('rgb_info_dimensions', image['width'] == info.width == 640 and image['height'] == info.height == 480
              and image['encoding'] == 'rgb8' and image['step'] == 1920 and image['bytes'] == 640*480*3)
        focal = 480 / (2*math.tan(math.radians(54)/2))
        check('camera_info_intrinsics', len(info.k) == 9 and all(math.isfinite(k) for k in info.k)
              and abs(info.k[0]-focal) < .1 and abs(info.k[4]-focal) < .1
              and abs(info.k[2]-320) <= .51 and abs(info.k[5]-240) <= .51
              and info.k[8] == 1 and all(abs(info.k[i]) < 1e-9 for i in (1, 3, 6, 7)))
        report['camera_info'] = {'stamp_ns': stamp, 'k': list(info.k), 'expected_focal_px': focal}
        report['status'] = 'passed'
    except Exception as exc:
        report['error'] = str(exc)
        raise
    finally:
        try:
            node.pub.publish(Twist())
            node.service('pause', False); node.service('estop', False)
            node.command_pitch(default_pitch, .8)
            restored = node.snapshot()
            report['restored_default_pitch'] = abs(restored['pitch']-default_pitch) < .005
            if not report['restored_default_pitch']:
                report['status'] = 'failed'
        except Exception as exc:
            report['restore_error'] = str(exc)
            report['status'] = 'failed'
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2)+'\n')
        node.destroy_node(); rclpy.shutdown()
    return int(report['status'] != 'passed')


if __name__ == '__main__':
    raise SystemExit(main())
