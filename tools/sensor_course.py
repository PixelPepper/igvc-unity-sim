#!/usr/bin/env python3
"""Experimental sensor-led mission. Reads sparse destinations, never course geometry."""
import argparse
from functools import partial
from concurrent.futures import ProcessPoolExecutor
import fcntl
import json
import math
import multiprocessing
import re
from pathlib import Path
import time

from gps_mission import LocalFrame
from observed_navigation import plan_observed_navigation
from lane_heading_memory import GapHeadingMemory
from recovery_policy import select_backup_recovery


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
    from sensor_msgs.msg import PointCloud2
    from sensor_msgs_py import point_cloud2
    from rclpy.qos import qos_profile_sensor_data
    from std_msgs.msg import Bool, String
    from std_srvs.srv import SetBool, Trigger
    from nav2_msgs.action import NavigateToPose, BackUp
    from nav2_msgs.msg import SpeedLimit
    from nav2_msgs.srv import ClearEntireCostmap
    from rcl_interfaces.srv import GetParameters

    config = json.loads(Path(args.mission).read_text())
    goals = destinations(config)
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    node = rclpy.create_node('igvc_sensor_course')
    # Spawn a clean worker: do not fork an initialized ROS/DDS context, and do
    # not make Python collision search compete with callbacks for the GIL.
    planner = ProcessPoolExecutor(max_workers=1, mp_context=multiprocessing.get_context('spawn'))
    nav = ActionClient(node, NavigateToPose, '/navigate_to_pose')
    backup = ActionClient(node, BackUp, '/backup')
    recoveries = {}
    gate = node.create_client(SetBool, '/sim/set_autonomy')
    zone = node.create_client(SetBool, '/sim/set_unmarked_mode')
    speed = node.create_publisher(SpeedLimit, '/speed_limit', 10)
    path_pub = node.create_publisher(RosPath, '/mission/observed_path', 1)
    state = {'status': 'starting', 'completed_destinations': 0, 'total_destinations': len(goals),
             'trajectory': [], 'plans': [], 'mode': 'sensor-led', 'sim_status': ''}
    latest = {}
    heading_memory = GapHeadingMemory()
    stamps = {}
    handle = None

    def receive(key, msg):
        if hasattr(msg, 'header'):
            stamp = msg.header.stamp.sec*1000000000+msg.header.stamp.nanosec
            # Perception can publish a reset/older acquisition while its memory
            # refills. Discard it; only authoritative streams indicate a reset.
            if key != 'lanes' and key in stamps and stamp < stamps[key]:
                latest['reset'] = True
            if stamp <= stamps.get(key, -1):
                return False
            stamps[key] = stamp
        latest[key] = (time.monotonic(), msg)
        return True

    def odom(msg):
        if not receive('odom', msg):
            return
        p, q = msg.pose.pose.position, msg.pose.pose.orientation
        yaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
        latest['pose'] = (p.x, p.y, yaw)
        heading_memory.propose((p.x, p.y), yaw, time.monotonic())
        state['trajectory'].append([msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9, p.x, p.y, yaw])

    node.create_subscription(Odometry, '/odom', odom, 10)
    def lanes(msg):
        if receive('lanes', msg):
            latest['lane_xy'] = [(float(p[0]), float(p[1])) for p in
                point_cloud2.read_points(msg, field_names=('x', 'y'), skip_nans=True)]
    node.create_subscription(PointCloud2, '/perception/lanes/points', lanes, qos_profile_sensor_data)
    node.create_subscription(OccupancyGrid, '/global_costmap/costmap', lambda m: receive('grid', m), 1)
    node.create_subscription(String, '/sim/status', lambda m: receive('status', m), 1)
    qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    node.create_subscription(Bool, '/sim/autonomy_enabled', lambda m: receive('enabled', m), qos)
    node.create_subscription(String, '/gps/origin', lambda m: receive('origin', m), qos)
    node.create_subscription(String, '/sim/autonomy_stop_reason', lambda m: receive('stop_reason', m), qos)

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

    def cancel_action(active):
        terminal = active.get_result_async()
        if terminal.done():
            return
        response = wait(active.cancel_goal_async())
        # A goal may finish between requesting cancellation and its response.
        if response.return_code != 0 and not terminal.done():
            raise RuntimeError('Nav2 cancellation was rejected; recovery withheld')
        wait(terminal)

    def check_live(now, armed_at, initial_run):
        if latest.get('reset'):
            raise RuntimeError('Observation clock reset; mission stopped')
        stale = [f'{k}: age={now-latest[k][0]:.3f}s limit={limit:.3f}s'
                 if k in latest else k+': missing'
                 for k, limit in (('grid', 5.), ('odom', 1.), ('status', 3.), ('lanes', 1.5))
                 if k not in latest or now-latest[k][0] > limit]
        if stale:
            raise RuntimeError('Stale observation or simulator stream ('+'; '.join(stale)+')')
        if now-armed_at > 1 and ('enabled' not in latest or now-latest['enabled'][0] > 1
                                or not latest['enabled'][1].data):
            detail = latest['stop_reason'][1].data if 'stop_reason' in latest else ''
            detail = detail or 'disabled or stale autonomy status; awaiting fault diagnostic'
            raise RuntimeError('Autonomy gate stopped: '+detail)
        state['sim_status'] = latest['status'][1].data
        current_run = re.search(r'\brun=(\d+)\b', state['sim_status'])
        if current_run is None or current_run.group(1) != initial_run.group(1):
            raise RuntimeError('Simulator reset invalidated the mission')

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
        for service in ('/perception/lanes/reset', '/perception/depth/reset'):
            reset_observations = node.create_client(Trigger, service)
            if not reset_observations.wait_for_service(timeout_sec=3):
                raise RuntimeError('Perception observation reset unavailable: '+service)
            if not wait(reset_observations.call_async(Trigger.Request())).success:
                raise RuntimeError('Perception observation reset failed: '+service)
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
        parameters = node.create_client(GetParameters, '/global_costmap/global_costmap/get_parameters')
        if not parameters.wait_for_service(timeout_sec=3):
            raise RuntimeError('Nav2 footprint parameters unavailable')
        values = wait(parameters.call_async(GetParameters.Request(names=['footprint', 'footprint_padding']))).values
        vertices = json.loads(values[0].string_value)
        padding = values[1].double_value
        xs, ys = [p[0] for p in vertices], [p[1] for p in vertices]
        if (len(vertices) != 4 or not all(math.isfinite(v) for v in xs+ys+[padding])
                or padding < 0 or len(set(xs)) != 2 or len(set(ys)) != 2):
            raise RuntimeError('Local goal validation requires the configured rectangular footprint')
        goal_footprint = (min(xs)-padding, max(xs)+padding, min(ys)-padding, max(ys)+padding)
        # Missing paint is permitted everywhere; camera/depth health and all observed
        # lane costs remain mandatory. No location-dependent map-zone lookup.
        set_mode(zone, True)
        set_mode(gate, True); armed_at = time.monotonic()
        state['status'] = 'running'
        end = time.monotonic()+args.timeout
        target = None; result = None; last_plan = 0.; no_plan_since = None
        progress_pose = latest['pose'][:2]; progress_at = time.monotonic()
        last_checkpoint = 0.
        failures = 0
        while time.monotonic() < end:
            rclpy.spin_once(node, timeout_sec=.05)
            now = time.monotonic()
            check_live(now, armed_at, initial_run)
            x, y, yaw = latest['pose']; gx, gy, radius = goals[state['completed_destinations']]
            if math.dist((x, y), progress_pose) >= .15:
                progress_pose = (x, y); progress_at = now
                failures = 0
            if result is not None and result.done():
                outcome = result.result()
                state.setdefault('action_results', []).append({'status': outcome.status,
                    'error_code': getattr(outcome.result, 'error_code', None)})
                failures += int(outcome.status != 4)
                result = None; handle = None; target = None
            if now-last_checkpoint >= 5:
                progress_file = Path(args.report).with_suffix('.progress.json')
                progress_file.write_text(json.dumps({'status': state['status'],
                    'completed_destinations': state['completed_destinations'], 'pose': [x,y,yaw],
                    'stationary_seconds': now-progress_at, 'recoveries': state.get('recoveries', []),
                    'last_guidance': state['plans'][-1]['diagnostics'].get('guidance') if state['plans'] else None})+'\n')
                last_checkpoint = now
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
            if latest['lanes'][1].header.frame_id != grid.header.frame_id:
                raise RuntimeError('Lane observations and costmap frames must match')
            planning = planner.submit(plan_observed_navigation, (grid.info.origin.position.x, grid.info.origin.position.y),
                grid.info.resolution, grid.info.width, grid.info.height, grid.data,
                (x, y), yaw, (gx, gy), latest.get('lane_xy', []),
                heading_hint=heading_memory.propose((x,y), yaw, time.monotonic(), lookahead=7.),
                robot_radius=.5, lookahead=7., max_path_length=14., min_progress=.1,
                forward_only=True, goal_footprint=goal_footprint, minimum_turn_radius=.65,
                max_expansions=50000, max_search_seconds=5.0,
                min_goal_distance=.4, continuation_reserve=1.0)
            planning_deadline = min(end, time.monotonic()+8)
            while not planning.done():
                rclpy.spin_once(node, timeout_sec=.02)
                if time.monotonic() > planning_deadline:
                    raise RuntimeError('Observed route search exceeded its time budget')
                check_live(time.monotonic(), armed_at, initial_run)
            plan = planning.result()
            if plan is not None and 'corridor' in plan['diagnostics']:
                heading_memory.observe(plan['diagnostics']['corridor'], (x,y), time.monotonic())
            check_live(time.monotonic(), armed_at, initial_run)
            last_plan = now
            # A geometrically available goal can still be undrivable. Do not
            # endlessly resubmit it after controller/planner failure or a stall.
            stalled = now-progress_at > 20 or failures >= 2
            if plan is None or stalled:
                if handle is not None:
                    cancel_action(handle); handle = None
                result = None
                target = None
                no_plan_since = no_plan_since or now
                if now-no_plan_since > 10 or stalled:
                    cursor = state['completed_destinations']
                    if recoveries.get(cursor, 0) >= 2 or not backup.wait_for_server(timeout_sec=2):
                        raise RuntimeError('No safe forward route after limited backup recovery')
                    # Stop first, then look for a rear pose with a useful forward
                    # escape. Do not repeatedly back up an arbitrary 0.3 m.
                    recovery_grid = latest['grid'][1]
                    rx, ry, ryaw = latest['pose']
                    guidance = partial(plan_observed_navigation, lane_points=latest.get('lane_xy', []),
                        heading_hint=heading_memory.propose((rx,ry),ryaw,time.monotonic(),lookahead=7.))
                    search = planner.submit(select_backup_recovery,
                        (recovery_grid.info.origin.position.x,recovery_grid.info.origin.position.y),
                        recovery_grid.info.resolution,recovery_grid.info.width,recovery_grid.info.height,
                        recovery_grid.data,(rx,ry),ryaw,(gx,gy),goal_footprint=goal_footprint,
                        forward_planner=guidance, max_search_seconds=5.,
                        forward_options=dict(robot_radius=.5,lookahead=7.,max_path_length=14.,
                            min_progress=.1,forward_only=True,minimum_turn_radius=.65,
                            min_goal_distance=.4,continuation_reserve=1.))
                    search_deadline=min(end,time.monotonic()+8.)
                    while not search.done():
                        rclpy.spin_once(node,timeout_sec=.02)
                        check_live(time.monotonic(),armed_at,initial_run)
                        if time.monotonic()>search_deadline:
                            raise RuntimeError('Backup clearance search exceeded its time budget')
                    escape=search.result()
                    check_live(time.monotonic(),armed_at,initial_run)
                    if escape is None:
                        raise RuntimeError('No observed collision-free backup with useful forward clearance')
                    backup_distance=escape['distance_m']
                    recoveries[cursor] = recoveries.get(cursor, 0)+1
                    request = BackUp.Goal()
                    request.target.x = -backup_distance
                    request.speed = .1
                    request.time_allowance.sec = math.ceil(backup_distance/request.speed)+3
                    handle = wait(backup.send_goal_async(request))
                    if not handle.accepted:
                        raise RuntimeError('Nav2 rejected backup recovery')
                    recovery_future = handle.get_result_async()
                    recovery_deadline = time.monotonic()+request.time_allowance.sec+2
                    while not recovery_future.done():
                        rclpy.spin_once(node, timeout_sec=.05)
                        recovery_now = time.monotonic()
                        check_live(recovery_now,armed_at,initial_run)
                        if recovery_now >= min(end, recovery_deadline):
                            raise RuntimeError('Backup interrupted: timeout')
                    recovery = recovery_future.result()
                    handle = None
                    if recovery.status != 4:
                        raise RuntimeError('Collision-checked backup did not complete')
                    actual_distance=math.dist((rx,ry),latest['pose'][:2])
                    if actual_distance<backup_distance-.08:
                        raise RuntimeError('Backup finished without reaching the planned clearance')
                    state.setdefault('recoveries', []).append({'destination': cursor,
                        'distance_m':backup_distance,'actual_distance_m':actual_distance,
                        'clearance_search':escape['diagnostics']})
                    no_plan_since = None
                    progress_pose = latest['pose'][:2]; progress_at = time.monotonic()
                    failures = 0
                continue
            no_plan_since = None
            if target is not None and handle is not None and not result.done() and math.hypot(target[0]-plan['local_goal'][0], target[1]-plan['local_goal'][1]) < 1.:
                continue
            target = plan['local_goal']
            check_live(time.monotonic(), armed_at, initial_run)
            request = NavigateToPose.Goal(); request.pose = pose(*target, plan['yaw'], grid.header)
            handle = wait(nav.send_goal_async(request))
            if not handle.accepted:
                raise RuntimeError('Nav2 rejected observed local goal')
            result = handle.get_result_async()
            path = RosPath(); path.header = grid.header
            path.poses = [pose(px, py, 0., grid.header) for px, py in plan['path']]
            path_pub.publish(path)
            state['plans'].append({'destination': state['completed_destinations'], 'goal': target,
                                   'goal_yaw': plan['yaw'],
                                   'diagnostics': plan['diagnostics']})
        else:
            raise RuntimeError('Bounded sensor mission timed out')
    except (RuntimeError, OSError, KeyboardInterrupt) as exc:
        state['status'] = 'stopped'; state['reason'] = str(exc)
        print(state['reason'], flush=True)
    finally:
        cleanup = [('disable autonomy', lambda: set_mode(gate, False)),
                   ('cancel action', lambda: cancel_action(handle) if handle is not None else None),
                   ('reset unmarked mode', lambda: set_mode(zone, False))]
        for label, operation in cleanup:
            try:
                operation()
            except RuntimeError as exc:
                state.setdefault('cleanup_errors', []).append(label+': '+str(exc))
                state['status'] = 'stopped'
        try:
            if 'stop_reason' in latest:
                state['stop_reason'] = latest['stop_reason'][1].data
                if state.get('reason', '').startswith('Autonomy gate stopped:') and state['stop_reason']:
                    state['reason'] = 'Autonomy gate stopped: '+state['stop_reason']
            if state['status'] != 'completed' and 'grid' in latest:
                grid = latest['grid'][1]
                snapshot = {'origin': [grid.info.origin.position.x, grid.info.origin.position.y],
                            'resolution': grid.info.resolution, 'width': grid.info.width, 'height': grid.info.height,
                            'costs': list(grid.data), 'pose': latest.get('pose'),
                            'destination': goals[min(state['completed_destinations'],len(goals)-1)],
                            'lane_points': latest.get('lane_xy', [])}
                Path(args.report).with_suffix('.observations.json').write_text(json.dumps(snapshot)+'\n')
            output = Path(args.report)
            output.write_text(json.dumps(state, indent=2)+'\n')
            output.with_suffix('.progress.json').write_text(json.dumps({
                'status': state['status'], 'reason': state.get('reason'),
                'completed_destinations': state['completed_destinations'],
                'pose': latest.get('pose'), 'recoveries': state.get('recoveries', [])})+'\n')
        except OSError as exc:
            state['status'] = 'stopped'
            print('Could not save run evidence: '+str(exc), flush=True)
        finally:
            planner.shutdown(wait=True, cancel_futures=True)
            node.destroy_node(); rclpy.shutdown()
    return 0 if state['status'] == 'completed' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mission', required=True)
    parser.add_argument('--report', required=True)
    parser.add_argument('--timeout', type=float, default=600.)
    parser.add_argument('--speed', type=float, default=2.2,
                        help='Maximum requested speed in m/s; controller slows for observed geometry')
    args = parser.parse_args()
    if not math.isfinite(args.speed) or not 0 < args.speed <= 2.2 or not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error('Use speed (0, 2.2] m/s and a positive finite timeout')
    lock_path = Path(__file__).resolve().parents[1]/'artifacts/session/full-course.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        raise SystemExit(run(args))
