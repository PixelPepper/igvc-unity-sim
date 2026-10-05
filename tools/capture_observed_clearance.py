"""Read-only paired global/local costmap snapshot for a stopped robot."""
import argparse
from collections import deque
import json
import math
import os
from pathlib import Path
import tempfile
import time


def validate_pair(receipts, now, stationary_samples):
    """Reject stale/asynchronous evidence and an unproven stationary interval."""
    if set(receipts) != {'global', 'local', 'odom', 'lanes'}:
        raise RuntimeError('Missing costmap/odom/lane topics')
    if any(not 0 <= now-r['arrival_wall_s'] <= 1.5 for r in receipts.values()):
        raise RuntimeError('Capture topics must all be fresh within 1.5 wall seconds')
    stamps = [r['stamp_ns'] for r in receipts.values()]
    if min(stamps) <= 0 or max(stamps)-min(stamps) > 1_250_000_000:
        raise RuntimeError('Capture acquisition stamps differ by more than 1.25 simulation seconds')
    if len({r['frame'] for r in receipts.values()}) != 1:
        raise RuntimeError('Snapshot frames differ')
    samples = [s for s in stationary_samples if now-s[0] <= 2.]
    if len(samples) < 2 or samples[-1][0]-samples[0][0] < 1. or now-samples[-1][0] > .25:
        raise RuntimeError('Need at least one second of fresh stationary odometry')
    first = samples[0]
    if any(not all(math.isfinite(v) for v in s) or max(abs(v) for v in s[4:]) > .01
           or math.dist(s[1:3], first[1:3]) > .01
           or abs(math.remainder(s[3]-first[3], 2*math.pi)) > .01 for s in samples):
        raise RuntimeError('Robot moved during the comparison window')


def main():
    import rclpy
    from nav_msgs.msg import Odometry, OccupancyGrid
    from sensor_msgs.msg import PointCloud2
    from sensor_msgs_py import point_cloud2
    from rclpy.qos import qos_profile_sensor_data
    from rcl_interfaces.srv import GetParameters
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    rclpy.init()
    node = rclpy.create_node('igvc_clearance_capture')
    latest = {}
    stationary = deque(maxlen=256)
    def receive(name, msg):
        now = time.monotonic()
        latest[name] = (now, msg)
        if name == 'odom':
            p, q, twist = msg.pose.pose.position, msg.pose.pose.orientation, msg.twist.twist
            yaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
            stationary.append((now,p.x,p.y,yaw,twist.linear.x,twist.linear.y,twist.angular.z))
    for key, topic, kind in (('global', '/global_costmap/costmap', OccupancyGrid),
                             ('local', '/local_costmap/costmap', OccupancyGrid),
                             ('odom', '/odom', Odometry),
                             ('lanes', '/perception/lanes/points', PointCloud2)):
        node.create_subscription(kind, topic,
            lambda msg, name=key: receive(name, msg), qos_profile_sensor_data)
    try:
        footprints = {}
        for name in ('global', 'local'):
            service = node.create_client(GetParameters, f'/{name}_costmap/{name}_costmap/get_parameters')
            if not service.wait_for_service(timeout_sec=8):
                raise RuntimeError('Missing footprint parameter service')
            future = service.call_async(GetParameters.Request(names=['footprint', 'footprint_padding']))
            rclpy.spin_until_future_complete(node, future, timeout_sec=3)
            if not future.done():
                raise RuntimeError('Footprint parameter query timed out')
            values = future.result().values
            vertices, padding = json.loads(values[0].string_value), values[1].double_value
            xs, ys = [p[0] for p in vertices], [p[1] for p in vertices]
            if (len(vertices) != 4 or len(set(xs)) != 2 or len(set(ys)) != 2
                    or not all(math.isfinite(v) for v in xs+ys+[padding]) or padding < 0):
                raise RuntimeError('Only finite rectangular footprints are supported')
            footprints[name] = [min(xs)-padding,max(xs)+padding,min(ys)-padding,max(ys)+padding]
        deadline = time.monotonic()+3
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.05)
        # Freeze one shared set only after parameter calls finish. No callback
        # may replace one grid while the other snapshot is serialized.
        frozen, now = dict(latest), time.monotonic()
        receipts = {name: dict(arrival_wall_s=arrival,
            stamp_ns=msg.header.stamp.sec*1_000_000_000+msg.header.stamp.nanosec,
            frame=msg.header.frame_id) for name, (arrival, msg) in frozen.items()}
        validate_pair(receipts, now, list(stationary))
        pair = {'schema_version': 1, 'captured_unix_s': time.time(),
                'receipt_age_limit_s': 1.5, 'stamp_skew_limit_s': 1.25,
                'stamp_skew_s': (max(r['stamp_ns'] for r in receipts.values())-
                                 min(r['stamp_ns'] for r in receipts.values()))/1e9}
        for name in ('global', 'local'):
            grid = frozen[name][1]
            odom = frozen['odom'][1]
            q = odom.pose.pose.orientation
            yaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
            lanes = frozen['lanes'][1]
            q = grid.info.origin.orientation
            if abs(q.x)+abs(q.y)+abs(q.z) > 1e-6:
                raise RuntimeError('Rotated costmap unsupported')
            p = odom.pose.pose.position
            report = dict(origin=[grid.info.origin.position.x, grid.info.origin.position.y],
                resolution=grid.info.resolution, width=grid.info.width, height=grid.info.height,
                costs=list(grid.data), pose=[p.x,p.y,yaw],
                goal_footprint=footprints[name],
                grid_stamp_ns=receipts[name]['stamp_ns'], grid_age_wall_s=now-frozen[name][0],
                odom_stamp_ns=receipts['odom']['stamp_ns'], odom_age_wall_s=now-frozen['odom'][0],
                lane_stamp_ns=receipts['lanes']['stamp_ns'], lane_age_wall_s=now-frozen['lanes'][0],
                lane_points=[[float(row[0]),float(row[1])] for row in point_cloud2.read_points(
                    lanes, field_names=('x','y'),skip_nans=True)],
                source=f'{name}_costmap; stopped-pose capture, asynchronous observations')
            pair[name] = report
        # A single atomic file prevents accidentally combining different captures.
        args.output.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', dir=args.output, delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(pair, stream, allow_nan=False)
                stream.write('\n')
            os.replace(temporary, args.output/'pair.json')
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
        print('Saved validated stopped-robot pair to '+str(args.output/'pair.json'))
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
