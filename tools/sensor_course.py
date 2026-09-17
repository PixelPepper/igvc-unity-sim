#!/usr/bin/env python3
"""Experimental sensor-led mission. Reads sparse destinations, never course geometry."""
import argparse
import fcntl
import json
import math
import re
from pathlib import Path
import time

from gps_mission import LocalFrame
from sensor_route_policy import select_local_goal


def destinations(config):
    def finite_number(value):
        return type(value) in (int, float) and math.isfinite(value)

    if (not isinstance(config, dict)
            or set(config) != {'schema_version', 'origin', 'goals', 'max_speed_mps'}
            or type(config['schema_version']) is not int or config['schema_version'] != 1):
        raise ValueError('Only the sanitized autonomy mission schema is accepted')
    origin = config['origin']
    coordinates = {'latitude', 'longitude', 'altitude'}
    metadata = {'world_frame', 'axes', 'model'}
    allowed = coordinates | metadata | {'noise_stddev_m'}
    if (not isinstance(origin, dict) or not coordinates <= set(origin)
            or not set(origin) <= allowed
            or any(not finite_number(origin[key]) for key in coordinates)
            or any(not isinstance(origin[key], str) or not origin[key] for key in metadata & set(origin))
            or ('noise_stddev_m' in origin and
                (not finite_number(origin['noise_stddev_m']) or origin['noise_stddev_m'] < 0))):
        raise ValueError('Origin must contain only scalar GPS coordinates and allowed metadata')
    if not finite_number(config['max_speed_mps']) or not 0 < config['max_speed_mps'] <= 2.2:
        raise ValueError('Invalid mission speed')
    if not isinstance(config['goals'], list) or not 1 <= len(config['goals']) <= 10:
        raise ValueError('Expected one to ten broad destinations')
    frame = LocalFrame(origin)
    result = []
    for goal in config['goals']:
        if not isinstance(goal, dict) or set(goal) != coordinates | {'radius_m'}:
            raise ValueError('Destinations must not contain route geometry or heading')
        if any(not finite_number(value) for value in goal.values()):
            raise ValueError('Destination values must be finite numbers')
        x, y, z = frame.to_enu(goal['latitude'], goal['longitude'], goal['altitude'])
        radius = goal['radius_m']
        if not all(math.isfinite(v) for v in (x, y, z, radius)) or not .4 <= radius <= 5:
            raise ValueError('Invalid destination')
        result.append((x, y, radius))
    return result


def run(args):
    import rclpy
    from rclpy.action import ActionClient
    from rclpy.qos import QoSProfile, DurabilityPolicy
    from nav_msgs.msg import Odometry, OccupancyGrid, Path as RosPath
    from geometry_msgs.msg import PoseStamped
    from std_msgs.msg import Bool, String
    from std_srvs.srv import SetBool
    from nav2_msgs.action import NavigateToPose
    from nav2_msgs.msg import SpeedLimit
    from nav2_msgs.srv import ClearEntireCostmap

    config = json.loads(Path(args.mission).read_text())
    goals = destinations(config)
    rclpy.init()
    node = rclpy.create_node('igvc_sensor_course')
    nav = ActionClient(node, NavigateToPose, '/navigate_to_pose')
    gate = node.create_client(SetBool, '/sim/set_autonomy')
    zone = node.create_client(SetBool, '/sim/set_unmarked_mode')
    speed = node.create_publisher(SpeedLimit, '/speed_limit', 10)
    path_pub = node.create_publisher(RosPath, '/mission/observed_path', 1)
    state = {'status': 'starting', 'completed_destinations': 0, 'total_destinations': len(goals),
             'trajectory': [], 'plans': [], 'mode': 'sensor-led', 'sim_status': ''}
    latest = {}
    stamps = {}
    handle = None

    def receive(key, msg):
        if hasattr(msg, 'header'):
            stamp = msg.header.stamp.sec*1000000000+msg.header.stamp.nanosec
            if key in stamps and stamp < stamps[key]:
                latest['reset'] = True
            if stamp <= stamps.get(key, -1):
                return
            stamps[key] = stamp
        latest[key] = (time.monotonic(), msg)

    def odom(msg):
        receive('odom', msg)
        p, q = msg.pose.pose.position, msg.pose.pose.orientation
        yaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
        latest['pose'] = (p.x, p.y, yaw)
        state['trajectory'].append([msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9, p.x, p.y, yaw])

    node.create_subscription(Odometry, '/odom', odom, 10)
    node.create_subscription(OccupancyGrid, '/global_costmap/costmap', lambda m: receive('grid', m), 1)
    node.create_subscription(String, '/sim/status', lambda m: receive('status', m), 1)
    qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    node.create_subscription(Bool, '/sim/autonomy_enabled', lambda m: receive('enabled', m), qos)
    node.create_subscription(String, '/gps/origin', lambda m: receive('origin', m), qos)

    def wait(future, timeout=5):
        end = time.monotonic()+timeout
        while not future.done() and time.monotonic() < end:
            rclpy.spin_once(node, timeout_sec=.05)
        if not future.done():
            raise RuntimeError('ROS request timed out')
        return future.result()

    def set_mode(client, value):
        if not client.wait_for_service(timeout_sec=3):
            raise RuntimeError('Control service unavailable')
        result = wait(client.call_async(SetBool.Request(data=value)))
        if not result.success:
            raise RuntimeError(result.message)

    def pose(x, y, yaw, header):
        msg = PoseStamped(); msg.header = header
        msg.pose.position.x = float(x); msg.pose.position.y = float(y)
        msg.pose.orientation.z = math.sin(yaw/2); msg.pose.orientation.w = math.cos(yaw/2)
        return msg

    try:
        deadline = time.monotonic()+45
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.1)
            if all(k in latest for k in ('grid', 'odom', 'status', 'origin')) and nav.server_is_ready():
                break
        if not all(k in latest for k in ('grid', 'odom', 'status', 'origin')):
            raise RuntimeError('Missing live costmap, odometry, origin or simulator status')
        if json.loads(latest['origin'][1].data) != config['origin']:
            raise RuntimeError('GPS origin mismatch')
        if 'line_guard=scoring' not in latest['status'][1].data:
            raise RuntimeError('Restart Unity with --line-guard scoring; hidden lane enforcement is forbidden')
        initial_run = re.search(r'\brun=(\d+)\b', latest['status'][1].data)
        if initial_run is None:
            raise RuntimeError('Missing simulator run identity')
        set_mode(gate, False)
        for service in ('/global_costmap/clear_entirely_global_costmap', '/local_costmap/clear_entirely_local_costmap'):
            clear = node.create_client(ClearEntireCostmap, service)
            if not clear.wait_for_service(timeout_sec=3):
                raise RuntimeError('Costmap reset service unavailable')
            wait(clear.call_async(ClearEntireCostmap.Request()))
        # A new mission must not inherit observations from an earlier lap.
        latest.pop('grid', None)
        refill_deadline = time.monotonic()+5
        while time.monotonic() < refill_deadline:
            rclpy.spin_once(node, timeout_sec=.1)
        if 'grid' not in latest:
            raise RuntimeError('No fresh costmap after reset')
        # Missing paint is permitted everywhere; camera/depth health and all observed
        # lane costs remain mandatory. No location-dependent map-zone lookup.
        set_mode(zone, True)
        set_mode(gate, True); armed_at = time.monotonic()
        state['status'] = 'running'
        end = time.monotonic()+args.timeout
        target = None; result = None; last_plan = 0.; no_plan_since = None
        while time.monotonic() < end:
            rclpy.spin_once(node, timeout_sec=.05)
            now = time.monotonic()
            if latest.get('reset'):
                raise RuntimeError('Observation clock reset; mission stopped')
            if any(now-latest[k][0] > limit for k, limit in (('grid', 3.), ('odom', 1.), ('status', 3.))):
                raise RuntimeError('Stale observation or simulator stream')
            if now-armed_at > 1 and ('enabled' not in latest or now-latest['enabled'][0] > 1 or not latest['enabled'][1].data):
                raise RuntimeError('Autonomy gate stopped: perception, E-stop or manual takeover')
            state['sim_status'] = latest['status'][1].data
            current_run = re.search(r'\brun=(\d+)\b', state['sim_status'])
            if current_run is None or current_run.group(1) != initial_run.group(1):
                raise RuntimeError('Simulator reset invalidated the mission')
            x, y, yaw = latest['pose']; gx, gy, radius = goals[state['completed_destinations']]
            if math.hypot(gx-x, gy-y) <= radius:
                state['completed_destinations'] += 1
                print(f"Destination {state['completed_destinations']}/{len(goals)}", flush=True)
                if state['completed_destinations'] == len(goals):
                    state['status'] = 'completed'; break
                target = None
            limit = SpeedLimit(); limit.percentage = False
            limit.speed_limit = min(args.speed, config['max_speed_mps'], 2.2)
            speed.publish(limit)
            if now-last_plan < 1.5:
                continue
            grid = latest['grid'][1]
            if grid.header.frame_id != latest['odom'][1].header.frame_id:
                raise RuntimeError('Costmap and odometry frames must match')
            q = grid.info.origin.orientation
            if abs(q.x)+abs(q.y)+abs(q.z) > 1e-6:
                raise RuntimeError('Rotated costmap is unsupported')
            gx, gy, radius = goals[state['completed_destinations']]
            plan = select_local_goal((grid.info.origin.position.x, grid.info.origin.position.y),
                grid.info.resolution, grid.info.width, grid.info.height, grid.data,
                (x, y), yaw, (gx, gy), robot_radius=.5, lookahead=4., max_path_length=14., min_progress=.1,
                forward_only=True)
            last_plan = now
            if plan is None:
                if handle is not None:
                    wait(handle.cancel_goal_async()); handle = None
                target = None
                no_plan_since = no_plan_since or now
                if now-no_plan_since > 10:
                    raise RuntimeError('No safe forward route; stopped without reversing or turning around')
                continue
            no_plan_since = None
            if target is not None and handle is not None and not result.done() and math.hypot(target[0]-plan['local_goal'][0], target[1]-plan['local_goal'][1]) < 1.:
                continue
            target = plan['local_goal']
            request = NavigateToPose.Goal(); request.pose = pose(*target, plan['yaw'], grid.header)
            handle = wait(nav.send_goal_async(request))
            if not handle.accepted:
                raise RuntimeError('Nav2 rejected observed local goal')
            result = handle.get_result_async()
            path = RosPath(); path.header = grid.header
            path.poses = [pose(px, py, 0., grid.header) for px, py in plan['path']]
            path_pub.publish(path)
            state['plans'].append({'destination': state['completed_destinations'], 'goal': target,
                                   'diagnostics': plan['diagnostics']})
        else:
            raise RuntimeError('Bounded sensor mission timed out')
    except (RuntimeError, KeyboardInterrupt) as exc:
        state['status'] = 'stopped'; state['reason'] = str(exc)
        print(state['reason'], flush=True)
    finally:
        try:
            set_mode(gate, False)
            if handle is not None:
                wait(handle.cancel_goal_async())
            set_mode(zone, False)
        except RuntimeError as exc:
            state['cleanup_error'] = str(exc)
        output = Path(args.report); output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(state, indent=2)+'\n')
        node.destroy_node(); rclpy.shutdown()
    return 0 if state['status'] == 'completed' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mission', required=True)
    parser.add_argument('--report', required=True)
    parser.add_argument('--timeout', type=float, default=600.)
    parser.add_argument('--speed', type=float, default=.7)
    args = parser.parse_args()
    if not math.isfinite(args.speed) or not 0 < args.speed <= 2.2 or not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error('Use speed (0, 2.2] m/s and a positive finite timeout')
    lock_path = Path(__file__).resolve().parents[1]/'artifacts/session/full-course.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        raise SystemExit(run(args))
