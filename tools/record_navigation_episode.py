#!/usr/bin/env python3
"""Bounded read-only sensor evidence recorder; run inside the ROS environment.

Frame bundles preserve acquisition stamps. Nearest depth/mask observations are
explicitly skewed, never described as synchronized. No course geometry is read.
"""
import argparse
from collections import Counter, OrderedDict
from dataclasses import dataclass
import json
import math
from pathlib import Path
import queue
import threading
import time


CACHE_CAPACITY = 8
QUEUE_CAPACITY = 64
MAX_EVENTS = 250000
MAX_IMAGE_BYTES = 4_000_000
MAX_TEXT_BYTES = 262144
MAX_SUSPENSION_JOINTS = 64
MAX_JOINT_NAME_BYTES = 128
MAX_COMMAND_FRAME_BYTES = 512


def acquisition_stamp(message):
    header = getattr(message, 'header', None)
    return (header.stamp.sec*1_000_000_000+header.stamp.nanosec) if header else None


@dataclass(frozen=True)
class Observation:
    stamp_ns: object
    received_monotonic_s: float
    message: object
    frame_id: str = ''


class BoundedCache:
    def __init__(self, capacity=CACHE_CAPACITY):
        if not isinstance(capacity, int) or capacity < 1 or capacity > 32:
            raise ValueError('Cache capacity must be 1..32')
        self.capacity, self.records = capacity, OrderedDict()
        self.evicted = self.regressions = 0
        self.previous_stamp = None
        self.sequence = 0

    def add(self, sample):
        if not math.isfinite(sample.received_monotonic_s):
            raise ValueError('Finite monotonic reception time required')
        if sample.stamp_ns is not None:
            if not isinstance(sample.stamp_ns, int) or sample.stamp_ns < 0:
                raise ValueError('Nonnegative integer acquisition stamp required')
            if self.previous_stamp is not None and sample.stamp_ns < self.previous_stamp:
                self.regressions += 1
            self.previous_stamp = sample.stamp_ns
        self.sequence += 1
        self.records[self.sequence] = sample
        if len(self.records) > self.capacity:
            self.records.popitem(last=False)
            self.evicted += 1

    def values(self):
        return list(self.records.values())


def select_observation(samples, target_stamp, now, *, max_age=.75, max_skew_ns=500_000_000):
    """Exact pair first; otherwise retain explicit bounded skew or absence.

    Matching is based on acquisition stamp, freshness on reception time. Unknown
    acquisition stamps cannot establish a pair, even if received together.
    """
    recent = [p for p in samples if 0 <= now-p.received_monotonic_s <= max_age]
    stamped = [p for p in recent if p.stamp_ns is not None]
    if target_stamp is None:
        chosen = max(recent, key=lambda p: p.received_monotonic_s, default=None)
        return chosen, dict(status='acquisition_stamp_unavailable' if chosen else 'unavailable',
                            synchronized=False, skew_ns=None)
    exact = [p for p in stamped if p.stamp_ns == target_stamp]
    chosen = max(exact, key=lambda p: p.received_monotonic_s, default=None)
    status = 'exact' if chosen else 'unavailable'
    if chosen is None and stamped:
        candidate = min(stamped, key=lambda p: (abs(p.stamp_ns-target_stamp), -p.received_monotonic_s))
        if abs(candidate.stamp_ns-target_stamp) <= max_skew_ns:
            chosen, status = candidate, 'skewed'
    return chosen, dict(status=status, synchronized=status == 'exact',
                        target_stamp_ns=target_stamp,
                        skew_ns=None if chosen is None else chosen.stamp_ns-target_stamp)


def choose_anchor(rgb, masks, now, previous_reception=-math.inf):
    fresh = lambda p: previous_reception < p.received_monotonic_s <= now and now-p.received_monotonic_s <= .75
    candidates = [p for p in masks if fresh(p) and any(
        r.stamp_ns == p.stamp_ns and 0 <= now-r.received_monotonic_s <= .75 for r in rgb)]
    if candidates:
        return max(candidates, key=lambda p: p.received_monotonic_s), 'lane_mask'
    return max((p for p in rgb if fresh(p)), key=lambda p: p.received_monotonic_s, default=None), 'rgb'


def observation_metadata(sample, now, anchor_stamp):
    if sample is None:
        return dict(available=False)
    return dict(available=True, acquisition_stamp_ns=sample.stamp_ns,
                received_monotonic_s=sample.received_monotonic_s,
                reception_age_s=now-sample.received_monotonic_s, frame_id=sample.frame_id,
                skew_from_anchor_ns=None if sample.stamp_ns is None or anchor_stamp is None else sample.stamp_ns-anchor_stamp)


def decode_image(message):
    import numpy as np
    encodings = {'rgb8': (3, np.dtype('u1')), 'mono8': (1, np.dtype('u1')),
                 '32FC1': (1, np.dtype('>f4' if message.is_bigendian else '<f4'))}
    if message.encoding not in encodings:
        raise ValueError('Unsupported image encoding')
    channels, dtype = encodings[message.encoding]
    if not (0 < message.width <= 1280 and 0 < message.height <= 720):
        raise ValueError('Image dimensions exceed recorder bounds')
    pixel_bytes = channels*dtype.itemsize
    if (message.step < message.width*pixel_bytes or len(message.data) != message.height*message.step
            or len(message.data) > MAX_IMAGE_BYTES):
        raise ValueError('Invalid or oversized image buffer')
    shape = (message.height, message.width, channels) if channels > 1 else (message.height, message.width)
    strides = (message.step, pixel_bytes, dtype.itemsize) if channels > 1 else (message.step, pixel_bytes)
    return np.ndarray(shape, dtype=dtype, buffer=message.data, strides=strides).copy()


def decode_cloud(message, names, max_points):
    import numpy as np
    if (message.height != 1 or not 0 <= message.width <= max_points
            or message.point_step != len(names)*4 or message.row_step != message.width*message.point_step
            or len(message.data) != message.row_step
            or [(f.name, f.offset, f.datatype, f.count) for f in message.fields] !=
                [(name, i*4, 7, 1) for i, name in enumerate(names)]):
        raise ValueError('Unsupported or oversized point cloud layout')
    return np.frombuffer(message.data, dtype='>f4' if message.is_bigendian else '<f4').reshape(-1, len(names)).copy()


def decode_lane_evidence(message):
    import numpy as np
    names = ('x', 'y', 'z', 'age_wall_s', 'observations', 'confirmed', 'stamp_sec', 'stamp_nanosec')
    if (message.height != 1 or not 0 <= message.width <= 8000 or message.point_step != 32
            or message.row_step != message.width*32 or len(message.data) != message.row_step
            or [(f.name, f.offset, f.datatype, f.count) for f in message.fields] !=
                [(name, i*4, 7 if i < 4 else 6, 1) for i, name in enumerate(names)]):
        raise ValueError('Unsupported lane evidence cloud layout')
    endian = '>' if message.is_bigendian else '<'
    dtype = np.dtype([(name, endian+('f4' if i < 4 else 'u4')) for i, name in enumerate(names)])
    return np.frombuffer(message.data, dtype=dtype).copy()


def camera_metadata(image, info):
    if image is None or info is None:
        return dict(valid=False, reason='image_or_exact_camera_info_unavailable')
    if (acquisition_stamp(image) != acquisition_stamp(info)
            or image.header.frame_id != info.header.frame_id
            or (image.width, image.height) != (info.width, info.height)):
        return dict(valid=False, reason='camera_info_stamp_frame_or_dimensions_mismatch')
    k = list(info.k)
    if len(k) != 9 or not all(math.isfinite(v) for v in k) or k[0] <= 0 or k[4] <= 0:
        return dict(valid=False, reason='invalid_camera_intrinsics')
    return dict(valid=True, width=info.width, height=info.height, k=k,
                d=list(info.d), r=list(info.r), p=list(info.p), distortion_model=info.distortion_model)


def json_safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


def vector(value):
    return [value.x, value.y, value.z]


def motion_payload_within_bounds(topic, message):
    """Bound new motion evidence before retaining a ROS message in the queue."""
    if topic not in ('/cmd_vel/nav', '/sim/drive_command', '/sim/suspension_state'):
        return True
    frame = getattr(getattr(message, 'header', None), 'frame_id', '')
    if (not isinstance(frame, str) or len(frame) > MAX_COMMAND_FRAME_BYTES
            or len(frame.encode('utf-8')) > MAX_COMMAND_FRAME_BYTES):
        return False
    if topic == '/sim/suspension_state':
        if any(len(getattr(message, key)) > MAX_SUSPENSION_JOINTS
               for key in ('name', 'position', 'velocity', 'effort')):
            return False
        if any(not isinstance(name, str) or len(name) > MAX_JOINT_NAME_BYTES
               or len(name.encode('utf-8')) > MAX_JOINT_NAME_BYTES for name in message.name):
            return False
    return True


def event_record(topic, sample):
    m = sample.message
    if not motion_payload_within_bounds(topic, m):
        raise ValueError('Oversized motion evidence payload')
    record = dict(topic=topic, acquisition_stamp_ns=sample.stamp_ns,
                  received_monotonic_s=sample.received_monotonic_s, frame_id=sample.frame_id)
    if topic in ('/mission/decision', '/perception/lanes/status', '/perception/depth/status'):
        try:
            record['payload'] = json.loads(m.data)
        except (ValueError, TypeError):
            record['payload'] = dict(invalid_json=True, text=m.data[:MAX_TEXT_BYTES])
    elif topic in ('/cmd_vel', '/cmd_vel/nav'):
        record.update(linear=vector(m.linear), angular=vector(m.angular), headerless=True)
    elif topic == '/sim/drive_command':
        record.update(linear=vector(m.twist.linear), angular=vector(m.twist.angular),
                      headerless=False, stamp_semantics='adapter_command_acceptance_sim_time')
    elif topic == '/sim/suspension_state':
        record.update(name=list(m.name), position=list(m.position),
                      velocity=list(m.velocity), effort=list(m.effort),
                      joint_count=len(m.name),
                      joint_arrays_aligned=all(len(values) in (0, len(m.name))
                          for values in (m.position, m.velocity, m.effort)),
                      nonfinite_values='null')
    elif topic == '/odom':
        p, q = m.pose.pose.position, m.pose.pose.orientation
        record.update(position=vector(p), quaternion_xyzw=[q.x, q.y, q.z, q.w],
                      child_frame_id=m.child_frame_id,
                      linear=vector(m.twist.twist.linear), angular=vector(m.twist.twist.angular))
    elif topic in ('/plan', '/mission/observed_path'):
        record.update(pose_count=len(m.poses), truncated=len(m.poses)>4096,
                      poses=[dict(stamp_ns=acquisition_stamp(p), frame_id=p.header.frame_id,
                                  position=vector(p.pose.position),
                                  quaternion_xyzw=[p.pose.orientation.x, p.pose.orientation.y,
                                                  p.pose.orientation.z, p.pose.orientation.w]) for p in m.poses[:4096]])
    elif topic == '/scan':
        record.update(angle_min=m.angle_min, angle_max=m.angle_max, angle_increment=m.angle_increment,
                      time_increment=m.time_increment, scan_time=m.scan_time,
                      range_min=m.range_min, range_max=m.range_max, ranges=list(m.ranges),
                      intensities=list(m.intensities), nonfinite_values='null')
    return json_safe(record)


def write_bundle(directory, bundle):
    import cv2
    import numpy as np
    directory.mkdir()
    metadata = bundle['metadata']
    arrays = {}
    for key, sample in bundle['samples'].items():
        if sample is None or key.endswith('_info') or key.endswith('_status'):
            continue
        try:
            if key in ('rgb', 'mask'):
                pixels = decode_image(sample.message)
                expected = 'rgb8' if key == 'rgb' else 'mono8'
                if sample.message.encoding != expected:
                    raise ValueError('Unexpected '+key+' encoding')
                if key == 'rgb':
                    pixels = cv2.cvtColor(pixels, cv2.COLOR_RGB2BGR)
                if not cv2.imwrite(str(directory/(key+'.png')), pixels):
                    raise OSError('PNG write failed')
            elif key == 'depth':
                if sample.message.encoding != '32FC1':
                    raise ValueError('Expected metric float depth')
                arrays['depth'] = decode_image(sample.message)
            elif key == 'surfaces':
                arrays['surfaces_xy_z_ground'] = decode_cloud(sample.message, ('x', 'y', 'z', 'ground'), 4800)
            elif key == 'lane_points':
                arrays['lane_points_xyz'] = decode_cloud(sample.message, ('x', 'y', 'z'), 8000)
            elif key == 'lane_evidence':
                arrays['lane_evidence'] = decode_lane_evidence(sample.message)
            metadata['observations'][key]['saved'] = True
        except (ValueError, TypeError, AttributeError, OSError) as exc:
            metadata['observations'][key].update(saved=False, error=str(exc))
    if arrays:
        with (directory/'arrays.npz').open('xb') as output:
            np.savez_compressed(output, **arrays)
    for key in ('lane_status', 'depth_status'):
        sample = bundle['samples'].get(key)
        if sample:
            metadata['observations'][key]['payload'] = event_record(
                '/perception/lanes/status' if key == 'lane_status' else '/perception/depth/status', sample)['payload']
    for key in ('rgb', 'depth'):
        image, info = bundle['samples'].get(key), bundle['samples'].get(key+'_info')
        metadata[key+'_camera'] = camera_metadata(image.message if image else None, info.message if info else None)
    with (directory/'metadata.json').open('x') as output:
        json.dump(json_safe(metadata), output, indent=2, allow_nan=False)
        output.write('\n')


class EpisodeWriter:
    """Nonblocking callback enqueue; only this thread serializes/writes payloads."""
    def __init__(self, output, capacity=QUEUE_CAPACITY, max_events=MAX_EVENTS):
        self.output, self.jobs = Path(output), queue.Queue(maxsize=capacity)
        self.max_events, self.event_count = max_events, 0
        self.counters = Counter()
        (self.output/'frames').mkdir()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def submit(self, kind, payload):
        if kind == 'event' and self.event_count >= self.max_events:
            self.counters['event_limit_drops'] += 1
            return False
        try:
            self.jobs.put_nowait((kind, payload))
        except queue.Full:
            self.counters[kind+'_queue_drops'] += 1
            return False
        if kind == 'event':
            self.event_count += 1
        self.counters[kind+'_queued'] += 1
        self.counters['queue_high_water'] = max(self.counters['queue_high_water'], self.jobs.qsize())
        return True

    def _run(self):
        try:
            with (self.output/'history.jsonl').open('x') as history:
                while True:
                    job = self.jobs.get()
                    try:
                        if job is None:
                            return
                        kind, payload = job
                        if kind == 'event':
                            history.write(json.dumps(event_record(*payload), allow_nan=False)+'\n')
                        else:
                            write_bundle(self.output/'frames'/f"{payload['metadata']['index']:06d}", payload)
                        self.counters[kind+'_written'] += 1
                    except Exception as exc:
                        self.counters['write_errors'] += 1
                        self.counters['last_error'] = str(exc)[:512]
                    finally:
                        self.jobs.task_done()
        except OSError as exc:
            self.counters['fatal_writer_error'] = str(exc)[:512]

    def finish(self):
        # No callbacks run during drain. Bounded backlog, and an explicit timeout
        # if the filesystem stalls; a daemon cannot prevent clean process exit.
        try:
            self.jobs.put(None, timeout=2.)
        except queue.Full:
            self.counters['drain_timeout'] += 1
            return False
        self.thread.join(timeout=15.)
        if self.thread.is_alive():
            self.counters['drain_timeout'] += 1
            return False
        return not self.counters.get('fatal_writer_error')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--duration', type=float, default=420.)
    parser.add_argument('--image-hz', type=float, default=2.)
    args = parser.parse_args()
    if not math.isfinite(args.duration) or not 1 <= args.duration <= 900:
        parser.error('--duration must be 1..900 seconds')
    if not math.isfinite(args.image_hz) or not .1 <= args.image_hz <= 5:
        parser.error('--image-hz must be 0.1..5')
    if args.output.exists() and (not args.output.is_dir() or any(args.output.iterdir())):
        parser.error('output must be a new or empty directory')

    import rclpy
    from rclpy.duration import Duration
    from rclpy.time import Time
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import Image, CameraInfo, PointCloud2, LaserScan, JointState
    from nav_msgs.msg import Odometry, Path as RosPath
    from geometry_msgs.msg import Twist, TwistStamped
    from std_msgs.msg import String
    from tf2_ros import Buffer, TransformListener, TransformException

    args.output.mkdir(parents=True, exist_ok=True)
    writer = EpisodeWriter(args.output)
    rclpy.init()
    node = rclpy.create_node('igvc_navigation_episode_recorder')
    tf = Buffer(cache_time=Duration(seconds=10.))
    listener = TransformListener(tf, node)
    caches, counts, subscriptions = {}, Counter(), []
    topics = [('rgb', '/camera/color/image_raw', Image), ('rgb_info', '/camera/color/camera_info', CameraInfo),
              ('depth', '/camera/depth/image_raw', Image), ('depth_info', '/camera/depth/camera_info', CameraInfo),
              ('mask', '/perception/lanes/debug', Image), ('lane_status', '/perception/lanes/status', String),
              ('lane_points', '/perception/lanes/points', PointCloud2),
              ('lane_evidence', '/perception/lanes/evidence', PointCloud2),
              ('surfaces', '/perception/depth/surfaces', PointCloud2),
              ('depth_status', '/perception/depth/status', String)]

    def receive(key, topic, message, history=False):
        now = time.monotonic()
        counts[key+'_received'] += 1
        if ((hasattr(message, 'data') and len(message.data) > (MAX_TEXT_BYTES if isinstance(message.data, str) else MAX_IMAGE_BYTES))
                or (hasattr(message, 'poses') and len(message.poses) > 8192)
                or (hasattr(message, 'ranges') and len(message.ranges) > 8000)
                or not motion_payload_within_bounds(topic, message)):
            counts[key+'_oversize_drops'] += 1
            return
        stamp = acquisition_stamp(message)
        if isinstance(message, String) and len(message.data) <= MAX_TEXT_BYTES:
            try:
                data = json.loads(message.data)
                embedded = data.get('stamp_ns') if isinstance(data, dict) else None
                if isinstance(embedded, int) and embedded >= 0:
                    stamp = embedded
            except ValueError:
                pass
        sample = Observation(stamp, now, message, getattr(getattr(message, 'header', None), 'frame_id', ''))
        if key in caches:
            caches[key].add(sample)
        if history:
            writer.submit('event', (topic, sample))

    for key, topic, message_type in topics:
        caches[key] = BoundedCache()
        subscriptions.append(node.create_subscription(message_type, topic,
            lambda m, k=key, t=topic: receive(k, t, m, k.endswith('_status')), qos_profile_sensor_data))
    history_topics = [('/odom', Odometry), ('/scan', LaserScan), ('/plan', RosPath),
                      ('/mission/observed_path', RosPath), ('/cmd_vel', Twist),
                      ('/cmd_vel/nav', Twist), ('/sim/drive_command', TwistStamped),
                      ('/sim/suspension_state', JointState), ('/mission/decision', String)]
    for topic, message_type in history_topics:
        subscriptions.append(node.create_subscription(message_type, topic,
            lambda m, t=topic: receive(t, t, m, True), qos_profile_sensor_data))

    def transform(sample):
        if sample is None or sample.stamp_ns is None or not sample.frame_id:
            return dict(available=False, reason='image_acquisition_unavailable')
        try:
            result = tf.lookup_transform('odom', sample.frame_id,
                                         Time(nanoseconds=sample.stamp_ns, clock_type=node.get_clock().clock_type))
            actual = acquisition_stamp(result)
            if actual != sample.stamp_ns:
                return dict(available=False, reason='tf_not_exact_acquisition_stamp', returned_stamp_ns=actual)
            t, q = result.transform.translation, result.transform.rotation
            return dict(available=True, acquisition_stamp_ns=actual, source_frame=sample.frame_id,
                        target_frame='odom', translation=vector(t), quaternion_xyzw=[q.x, q.y, q.z, q.w])
        except (TransformException, ValueError) as exc:
            return dict(available=False, reason=str(exc)[:512])

    started = time.monotonic()
    next_frame, previous_reception, frame_index = started, -math.inf, 0
    interrupted = False
    try:
        while rclpy.ok() and time.monotonic()-started < args.duration:
            rclpy.spin_once(node, timeout_sec=.02)
            now = time.monotonic()
            if now < next_frame:
                continue
            next_frame = now+1/args.image_hz
            anchor, anchor_source = choose_anchor(caches['rgb'].values(), caches['mask'].values(), now, previous_reception)
            stamp = anchor.stamp_ns if anchor else None
            if anchor:
                previous_reception = anchor.received_monotonic_s
            selected, pairings = {}, {}
            for key in caches:
                selected[key], pairings[key] = select_observation(caches[key].values(), stamp, now,
                    max_skew_ns=0 if key in ('rgb_info',) else 500_000_000)
            # The matched lane status identifies the depth acquisition actually
            # used for this RGB projection. Never substitute another surface for
            # this evidence if its exact acquisition was evicted or unavailable.
            status = selected['lane_status']
            ground_stamp = None
            if status is not None and status.stamp_ns == stamp:
                try:
                    payload = json.loads(status.message.data)
                    candidate = payload.get('ground_stamp_ns')
                    if isinstance(candidate, int) and candidate >= 0:
                        ground_stamp = candidate
                except (ValueError, AttributeError):
                    pass
            if ground_stamp is not None:
                selected['depth'], pairings['depth'] = select_observation(
                    caches['depth'].values(), ground_stamp, now, max_skew_ns=0)
            depth = selected['depth']
            for key in ('depth_info', 'surfaces', 'depth_status'):
                target = ground_stamp if ground_stamp is not None else depth.stamp_ns if depth else None
                selected[key], pairings[key] = select_observation(caches[key].values(), target,
                    now, max_skew_ns=0 if ground_stamp is not None or key == 'depth_info' else 500_000_000)
            observations = {k: dict(**observation_metadata(v, now, stamp), pairing=pairings[k]) for k, v in selected.items()}
            writer.submit('frame', dict(samples=selected, metadata=dict(schema_version=1, index=frame_index,
                anchor_source=anchor_source, anchor_acquisition_stamp_ns=stamp,
                projection_ground_stamp_ns=ground_stamp,
                depth_pairing_purpose='projection_source' if ground_stamp is not None else 'nearest_comparison_only',
                recorded_monotonic_s=now, elapsed_s=now-started,
                anchor_available=anchor is not None, observations=observations,
                rgb_transform=transform(selected['rgb']), depth_transform=transform(depth),
                limitations='Exact means stamp equality only, subject to camera frame/dimension validation. '
                    'RGB/depth are independent acquisitions; skewed pairs are not synchronized. '
                    'Lane point cloud history has no perpoint ages; optional lane_evidence preserves published provenance.')))
            frame_index += 1
    except KeyboardInterrupt:
        interrupted = True
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        drained = writer.finish()
        summary = dict(schema_version=1, status='interrupted' if interrupted else 'finished',
                       duration_wall_s=time.monotonic()-started, requested_duration_s=args.duration,
                       image_hz=args.image_hz, frames_attempted=frame_index,
                       cache_capacity=CACHE_CAPACITY, queue_capacity=QUEUE_CAPACITY, max_events=MAX_EVENTS,
                       subscriptions=[t for _, t, _ in topics]+[t for t, _ in history_topics]+['/tf', '/tf_static'],
                       receive_counters=dict(counts), writer_counters=dict(writer.counters), writer_drained=drained,
                       caches={k: dict(evicted=c.evicted, stamp_regressions=c.regressions) for k, c in caches.items()},
                       live_validation='not implied by recorder completion')
        with (args.output/'episode.json').open('x') as output:
            json.dump(json_safe(summary), output, indent=2, allow_nan=False)
            output.write('\n')
        print(json.dumps(summary, allow_nan=False))
    return 0 if drained and not writer.counters.get('write_errors') else 1


if __name__ == '__main__':
    raise SystemExit(main())
