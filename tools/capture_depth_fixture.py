#!/usr/bin/env python3
"""Capture one fresh, exact-stamp depth/CameraInfo/TF fixture without commands."""
import argparse
from collections import OrderedDict, Counter
import json
import math
from pathlib import Path
import time

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import Image, CameraInfo
from tf2_ros import Buffer, TransformListener, TransformException


def stamp(message):
    return message.header.stamp.sec * 1_000_000_000 + message.header.stamp.nanosec


class Capture(Node):
    def __init__(self):
        super().__init__('capture_depth_fixture')
        self.images = OrderedDict()
        self.infos = OrderedDict()
        self.tf = Buffer()
        self.listener = TransformListener(self.tf, self)
        self.reasons = Counter()
        self.create_subscription(Image, '/camera/depth/image_raw',
                                 lambda m: self.receive(self.images, m), qos_profile_sensor_data)
        self.create_subscription(CameraInfo, '/camera/depth/camera_info',
                                 lambda m: self.receive(self.infos, m), qos_profile_sensor_data)

    def receive(self, cache, message):
        # Volatile subscriptions have no retained-history request. Receipt age is
        # additionally bounded before admitting a pair to the fixture.
        cache[stamp(message)] = (message, time.monotonic())
        while len(cache) > 8:
            cache.popitem(last=False)

    def candidate(self):
        for ns in sorted(self.images.keys() & self.infos.keys(), reverse=True):
            image, image_arrival = self.images[ns]
            info, info_arrival = self.infos[ns]
            if time.monotonic() - min(image_arrival, info_arrival) > .5:
                continue
            try:
                if ns <= 0 or image.header.frame_id != 'camera_color_optical_frame':
                    raise ValueError('invalid_depth_frame_or_stamp')
                if info.header.frame_id != image.header.frame_id:
                    raise ValueError('camera_info_frame_mismatch')
                if image.encoding != '32FC1' or image.width <= 0 or image.height <= 0:
                    raise ValueError('invalid_image_format')
                if (info.width, info.height) != (image.width, image.height):
                    raise ValueError('camera_info_dimensions')
                if image.step < image.width * 4 or len(image.data) != image.height * image.step:
                    raise ValueError('invalid_image_buffer')
                k = np.asarray(info.k, dtype=np.float64).reshape(3, 3)
                if (not np.isfinite(k).all() or k[0, 0] <= 0 or k[1, 1] <= 0
                        or not np.allclose(k[2], [0, 0, 1], atol=1e-9, rtol=0)):
                    raise ValueError('invalid_intrinsics')
                transform = self.tf.lookup_transform('odom', image.header.frame_id,
                                                     Time.from_msg(image.header.stamp))
                if stamp(transform) != ns or transform.header.frame_id != 'odom':
                    raise ValueError('tf_not_exact_acquisition_stamp')
                t, q = transform.transform.translation, transform.transform.rotation
                origin = np.array([t.x, t.y, t.z], dtype=np.float64)
                quaternion = np.array([q.x, q.y, q.z, q.w], dtype=np.float64)
                if (not np.isfinite(origin).all() or not np.isfinite(quaternion).all()
                        or abs(float(quaternion @ quaternion)-1) > 1e-5):
                    raise ValueError('invalid_transform')
                dtype = np.dtype('>f4' if image.is_bigendian else '<f4')
                depth = np.ndarray((image.height, image.width), dtype=dtype,
                                   buffer=image.data, strides=(image.step, 4)).astype(np.float32, copy=True)
                # Preserve NaN and other observed samples for offline diagnosis.
                return dict(depth=depth, k=k, origin=origin, quaternion=quaternion,
                            stamp_ns=np.int64(ns), frame=np.asarray(image.header.frame_id))
            except (ValueError, TransformException, TypeError) as exc:
                self.reasons[str(exc)] += 1
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=float, default=10)
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or not 1 <= args.timeout <= 30:
        parser.error('--timeout must be finite and between 1 and 30 seconds')
    if args.output.suffix.lower() != '.npz':
        parser.error('--output must end in .npz')
    if args.output.exists():
        parser.error('output already exists; refusing to overwrite')
    if not args.output.parent.is_dir():
        parser.error('output parent directory must already exist')
    rclpy.init()
    node = Capture()
    deadline = time.monotonic() + args.timeout
    fixture = None
    try:
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=min(.05, max(0., deadline-time.monotonic())))
            fixture = node.candidate()
            if fixture is not None:
                break
        if fixture is None:
            print(json.dumps(dict(status='timeout', reasons=dict(node.reasons))))
            return 1
        # Exclusive creation protects against another capture racing the precheck.
        with args.output.open('xb') as output:
            np.savez_compressed(output, **fixture)
        print(json.dumps(dict(status='captured', output=str(args.output.resolve()),
                              shape=list(fixture['depth'].shape), stamp_ns=int(fixture['stamp_ns']),
                              frame=str(fixture['frame']), quaternion_order='xyzw')))
        return 0
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
