#!/usr/bin/env python3
"""Experimental sensor-led mission. Reads sparse destinations, never course geometry."""
import argparse
from functools import partial
from concurrent.futures import ProcessPoolExecutor
import fcntl
import hashlib
import json
import math
import multiprocessing
import re
import signal
from pathlib import Path
import time

from gps_mission import LocalFrame
from observed_navigation import (plan_observed_navigation, evaluate_observed_navigation,
                                 select_observed_guidance, refine_corridor_guidance)
from lane_heading_memory import GapHeadingMemory
from entrance_memory import ObservedEntranceMemory
from entrance_support import corridor_fresh_support
from navigation_decisions import DecisionRecorder, DecisionOutcomes, compact_event_metadata
from recovery_policy import select_backup_recovery, select_trap_escape
from trap_memory import (TrapMemory, entry_heading, evaluate_with_trap_memory,
                         exclude_trapped_guidance, recent_path)
from recovery_budget import RecoveryBudget
from recovery_intent import RecoveryIntent
from execution_path import controller_path
from path_entry import prepare_controller_plan
from action_cancellation import cancel_action_and_wait
from sensor_telemetry import attach_sensor_telemetry
from mission_health import MissionHealthLedger
from session_paths import session_dir


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


def send_goal_with_startup_retry(send_goal, wait_for_server, pause, retries, *, startup,
                                 still_startup=lambda: True, max_tries=5, budget_s=5.,
                                 clock=time.monotonic):
    """Return the goal handle; the caller still raises on a rejected handle.

    Only before this run's first accepted goal (``startup``) and while the
    robot has not moved (``still_startup``): wait for the server and resend a
    rejected goal up to ``max_tries`` within ``budget_s``, logging each
    rejection into ``retries``. Nav2 restarted between trials can briefly
    reject goals while its BT/controller activate. Otherwise: send once.
    """
    if not startup:
        return send_goal()
    deadline = clock()+budget_s
    if not wait_for_server(timeout_sec=budget_s):
        raise RuntimeError('Navigation action server unavailable at startup')
    for attempt in range(1, max_tries+1):
        handle = send_goal()
        if handle.accepted or attempt == max_tries or clock() >= deadline or not still_startup():
            return handle
        retries.append(dict(attempt=attempt, monotonic_s=clock()))
        pause(min(.5, max(0., deadline-clock())))
    return handle


def run(args):
    import rclpy
    from rclpy.signals import SignalHandlerOptions
    from rclpy.clock import Clock, ClockType
    from rclpy.action import ActionClient
    from rclpy.qos import QoSProfile, DurabilityPolicy
    from nav_msgs.msg import Odometry, OccupancyGrid, Path as RosPath
    from geometry_msgs.msg import PoseStamped
    from sensor_msgs.msg import PointCloud2
    from sensor_msgs_py import point_cloud2
    from rclpy.qos import qos_profile_sensor_data
    from std_msgs.msg import Bool, String
    from std_srvs.srv import SetBool, Trigger
    from nav2_msgs.action import NavigateToPose, FollowPath, BackUp
    from nav2_msgs.msg import SpeedLimit
    from nav2_msgs.srv import ClearEntireCostmap
    from rcl_interfaces.srv import GetParameters

    mission_bytes = Path(args.mission).read_bytes()
    config = json.loads(mission_bytes)
    goals = destinations(config)
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    # Defer interruption until spin returns from its C binding; retain the ROS context.
    # The sandbox supervisor needs our finally block to cancel actions and save
    # evidence before shutdown; rclpy's default SIGINT handler closes it early.
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = rclpy.create_node('igvc_sensor_course')
    stop_requested = False
    finishing = False

    def request_stop(*_):
        nonlocal stop_requested
        stop_requested = True

    previous_sigint = signal.signal(signal.SIGINT, request_stop)

    def spin(timeout_sec):
        rclpy.spin_once(node, timeout_sec=timeout_sec)
        if stop_requested and not finishing:
            raise RuntimeError('Stopped by operator')

    telemetry = attach_sensor_telemetry(node)
    mission_health = MissionHealthLedger(max_gap_s=.25)
    # Spawn a clean worker: do not fork an initialized ROS/DDS context, and do
    # not make Python collision search compete with callbacks for the GIL.
    planner = ProcessPoolExecutor(max_workers=1, mp_context=multiprocessing.get_context('spawn'))
    direct_path = args.path_execution == 'checked-path'
    nav = ActionClient(node, FollowPath if direct_path else NavigateToPose,
                       '/follow_path' if direct_path else '/navigate_to_pose')
    backup = ActionClient(node, BackUp, '/backup')
    recovery_budget = RecoveryBudget(total_limit=2*len(goals))
    recovery_intent = RecoveryIntent()
    # Experimental A/B: legacy keeps the original straight-backup recovery
    # exactly; retrace adds bounded stall memory and the corridor retrace.
    trap_memory = TrapMemory() if args.escape == 'retrace' else None
    gate = node.create_client(SetBool, '/sim/set_autonomy')
    zone = node.create_client(SetBool, '/sim/set_unmarked_mode')
    speed = node.create_publisher(SpeedLimit, '/speed_limit', 10)
    path_pub = node.create_publisher(RosPath, '/mission/observed_path', 1)
    decision_pub = node.create_publisher(String, '/mission/decision', 20)
    recorder = DecisionRecorder(args.capture_dir) if args.capture_dir else None
    outcomes = DecisionOutcomes(recorder.submit_outcome if recorder else None)
    goal_accepted_once = False
    state = {'status': 'starting', 'completed_destinations': 0, 'total_destinations': len(goals),
             'trajectory': [], 'plans': [], 'mode': 'sensor-led', 'sim_status': '',
             'mission_sha256': hashlib.sha256(mission_bytes).hexdigest(),
             'timeout_wall_s': args.timeout, 'requested_speed_mps': args.speed}
    state['planning_budget_wall_s'] = args.planning_budget
    state['goal_policy'] = args.goal_policy
    state['guidance_memory'] = args.guidance_memory
    state['path_execution'] = args.path_execution
    state['body_clearance_weight'] = args.body_clearance_weight
    state['escape_mode'] = args.escape
    # Loaded once; passed to the planner process at submit time only, never into saved snapshots.
    scorer_options = {}
    for name, (scorer_key, weight_key) in (('route', ('learned_scorer', 'learned_weight')),
                                           ('corridor', ('corridor_scorer', 'corridor_weight'))):
        weight, model = getattr(args, name+'_weight'), getattr(args, name+'_scorer')
        state[name+'_scorer'] = None
        if weight > 0:
            from learning.learned_scorer import load_scorer
            scorer_options.update({scorer_key: load_scorer(model), weight_key: weight})
            state[name+'_scorer'] = dict(path=str(model), weight=weight,
                                         sha256=hashlib.sha256(model.read_bytes()).hexdigest())
    state['source_sha256'] = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
        for name in ('sensor_course.py', 'observed_navigation.py', 'lane_corridor_policy.py',
                     'lane_heading_memory.py', 'sensor_route_policy.py',
                     'entrance_memory.py', 'entrance_support.py', 'recovery_budget.py', 'recovery_policy.py',
                     'execution_path.py', 'path_entry.py', 'swept_footprint.py', 'recovery_intent.py',
                     'action_cancellation.py', 'mission_health.py')
                     + (('trap_memory.py',) if trap_memory is not None else ())}
    latest = {}
    entrance_tracking = args.guidance_memory == 'entrance'
    heading_memory = ObservedEntranceMemory() if entrance_tracking else GapHeadingMemory()
    stamps = {}
    handle = None
    goal_footprint = None
    armed_at = None
    decision_sequence = 0
    active_decision = None
    active_goal_id = None

    def sample_mission_health():
        if mission_health.active:
            sampled_at = time.monotonic()
            mission_health.observe(telemetry.health_summary(now=sampled_at),
                                   sampled_at, stamps.get('odom'))

    # Wall-clock sampling continues while simulation time stalls. Missing
    # callbacks are recorded as coverage gaps, never inferred to be healthy.
    health_timer = node.create_timer(.1, sample_mission_health,
                                    clock=Clock(clock_type=ClockType.STEADY_TIME))

    def decision_event(phase, **fields):
        event = dict(schema_version=1, phase=phase, sequence=decision_sequence,
                     monotonic_s=time.monotonic(), odom_stamp_ns=stamps.get('odom'),
                     pose=list(latest['pose']) if 'pose' in latest else None,
                     destination_index=state['completed_destinations'], **fields)
        state.setdefault('decisions', []).append(event)
        decision_pub.publish(String(data=json.dumps(event, allow_nan=False)))

    def action_finished(future, sequence, goal_id):
        outcome = future.result()
        result_record = dict(action_sequence=sequence, goal_id=goal_id,
                             status=outcome.status,
                             error_code=getattr(outcome.result, 'error_code', None))
        state.setdefault('action_results', []).append(result_record)
        outcomes.result(sequence, outcome.status)
        decision_event('action_result', **result_record)

    def preserved_guidance(pose, now, destination_index):
        was_active = recovery_intent.active
        selection = recovery_intent.propose(pose, now, destination_index)
        if was_active and not recovery_intent.active:
            decision_event('recovery_intent_finished', diagnostics=dict(recovery_intent.diagnostics))
            reason = recovery_intent.diagnostics.get('reason')
            if reason in ('expired', 'invalid_input', 'clock_reset'):
                raise RuntimeError('Preserved recovery intent stopped: '+reason)
        return selection

    def receive(key, msg):
        if hasattr(msg, 'header'):
            stamp = msg.header.stamp.sec*1000000000+msg.header.stamp.nanosec
            # Perception can publish a reset/older acquisition while its memory
            # refills. Discard it; only authoritative streams indicate a reset.
            if key not in ('lanes', 'lane_evidence') and key in stamps and stamp < stamps[key]:
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
    def lane_evidence(msg):
        if msg.header.frame_id == 'odom' and receive('lane_evidence', msg):
            latest['evidence_rows'] = [tuple(float(value) for value in p) for p in
                point_cloud2.read_points(msg, field_names=('x','y','z','age_wall_s',
                    'observations','confirmed','stamp_sec','stamp_nanosec'), skip_nans=True)]
    if entrance_tracking:
        node.create_subscription(PointCloud2, '/perception/lanes/evidence', lane_evidence,
                                 qos_profile_sensor_data)
    node.create_subscription(OccupancyGrid, '/global_costmap/costmap', lambda m: receive('grid', m), 1)
    node.create_subscription(String, '/sim/status', lambda m: receive('status', m), 1)
    qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    node.create_subscription(Bool, '/sim/autonomy_enabled', lambda m: receive('enabled', m), qos)
    node.create_subscription(String, '/gps/origin', lambda m: receive('origin', m), qos)
    node.create_subscription(String, '/sim/autonomy_stop_reason', lambda m: receive('stop_reason', m), qos)

    def wait(future, timeout=5):
        end = time.monotonic()+timeout
        while not future.done() and time.monotonic() < end:
            spin(.05)
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
        return cancel_action_and_wait(
            active, wait, timeout=5.,
            on_diagnostic=lambda details: decision_event(
                'action_cancellation', diagnostics=details))

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
        course_hash = re.search(r'\bcourse_hash=([0-9a-f]{64})\b', state['sim_status'])
        if course_hash and state.get('course_sha256', course_hash.group(1)) != course_hash.group(1):
            raise RuntimeError('Simulator course identity changed during mission')
        if course_hash:
            state['course_sha256'] = course_hash.group(1)
        current_run = re.search(r'\brun=(\d+)\b', state['sim_status'])
        if current_run is None or current_run.group(1) != initial_run.group(1):
            raise RuntimeError('Simulator reset invalidated the mission')

    try:
        deadline = time.monotonic()+45
        while time.monotonic() < deadline:
            spin(.1)
            if all(k in latest for k in ('grid', 'odom', 'status', 'origin')) and nav.server_is_ready():
                break
        if not all(k in latest for k in ('grid', 'odom', 'status', 'origin')):
            missing = [k for k in ('grid', 'odom', 'status', 'origin') if k not in latest]
            raise RuntimeError('Missing live costmap, odometry, origin or simulator status (missing: '
                               +', '.join(missing)+'; nav server ready: '+str(nav.server_is_ready())+')')
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
            spin(.1)
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
        # Keep startup receipts separately: transport warm-up is not an armed
        # lap. Refuse to discard any startup motion rather than hiding it.
        initial_pose = state['trajectory'][-1][1:]
        if any(math.dist(row[1:3],initial_pose[:2]) > .001 or
               abs(math.atan2(math.sin(row[3]-initial_pose[2]),math.cos(row[3]-initial_pose[2]))) > .001
               for row in state['trajectory']):
            raise RuntimeError('Unexpected motion before arming the mission')
        state['startup_trajectory'] = state['trajectory'][:-1]
        state['trajectory'] = state['trajectory'][-1:]
        armed_at = time.monotonic()
        state['health_trajectory_start_index'] = len(state['trajectory'])-1
        mission_health.begin(armed_at, stamps.get('odom'))
        sample_mission_health()
        set_mode(gate, True)
        state['status'] = 'running'
        end = time.monotonic()+args.timeout
        target = None; result = None; last_plan = 0.; no_plan_since = None
        progress_pose = latest['pose'][:2]; progress_at = time.monotonic()
        last_checkpoint = 0.
        failures = 0
        while time.monotonic() < end:
            spin(.05)
            now = time.monotonic()
            check_live(now, armed_at, initial_run)
            x, y, yaw = latest['pose']; gx, gy, radius = goals[state['completed_destinations']]
            preserved_guidance((x,y,yaw), now, state['completed_destinations'])
            if trap_memory is not None:
                for expired in trap_memory.observe((x,y,yaw), now, state['completed_destinations']):
                    decision_event('trap_memory_expired', region=expired)
            if recovery_budget.observe((x, y, yaw)):
                decision_event('recovery_rearmed', budget=recovery_budget.report())
            if math.dist((x, y), progress_pose) >= .15:
                progress_pose = (x, y); progress_at = now
                failures = 0
            if result is not None and result.done():
                outcome = result.result()
                failures += int(outcome.status != 4)
                result = None; handle = None; target = None
                active_goal_id = None
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
                recovery_intent.clear('destination_changed')
                if entrance_tracking:
                    heading_memory.clear()
            limit = SpeedLimit(); limit.percentage = False
            limit.speed_limit = min(args.speed, config['max_speed_mps'], 2.2)
            speed.publish(limit)
            if now-last_plan < 1.5:
                continue
            # Explicit A/B experiment: leave Nav2 pursuing the accepted local
            # goal until it finishes or the existing progress watchdog intervenes.
            if (args.goal_policy == 'hold' and target is not None and handle is not None and result is not None
                    and not result.done() and now-progress_at <= 20 and failures < 2):
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
            planner_options = dict(robot_radius=.5, lookahead=7., max_path_length=14., min_progress=.1,
                forward_only=True, goal_footprint=goal_footprint, minimum_turn_radius=.65,
                max_expansions=50000, max_search_seconds=args.planning_budget,
                min_goal_distance=.4, continuation_reserve=1.0,
                body_clearance_weight=args.body_clearance_weight,
                entrance_tracking=entrance_tracking)
            heading_hint = heading_memory.propose((x,y), yaw, time.monotonic(), lookahead=7.)
            frozen_guidance = preserved_guidance((x,y,yaw), time.monotonic(), state['completed_destinations'])
            # Freeze the same observations sent to the worker. The current action
            # can continue while it plans; completion pose/age are recorded too.
            inputs = dict(origin=[grid.info.origin.position.x, grid.info.origin.position.y],
                          resolution=grid.info.resolution, width=grid.info.width, height=grid.info.height,
                          costs=list(grid.data), robot_xy=[x,y], robot_yaw=yaw,
                          destination=[gx,gy], lane_points=list(latest.get('lane_xy', [])),
                          heading_hint=heading_hint, planner_options=planner_options,
                          frozen_guidance=frozen_guidance)
            decision_sequence += 1
            submitted_at = time.monotonic()
            evidence_rows = latest.get('evidence_rows', [])
            evidence_received_at = latest.get('lane_evidence', (None,))[0]
            metadata = dict(monotonic_s=submitted_at, destination_index=state['completed_destinations'],
                            grid_stamp_ns=stamps.get('grid'), lane_stamp_ns=stamps.get('lanes'),
                            odom_stamp_ns=stamps.get('odom'), frame=grid.header.frame_id,
                            grid_age_wall_s=submitted_at-latest['grid'][0],
                            lane_age_wall_s=submitted_at-latest['lanes'][0],
                            mission_sha256=state['mission_sha256'], source_sha256=state['source_sha256'])
            if entrance_tracking:
                metadata.update(memory=dict(heading_memory.diagnostics),
                                evidence_stamp_ns=stamps.get('lane_evidence'),
                                memory_refresh_input=dict(evidence_rows=evidence_rows,
                                    receipt_age_wall_s=submitted_at-evidence_received_at
                                        if evidence_received_at is not None else None))
            trap_regions = trap_memory.regions() if trap_memory is not None else []
            if trap_regions:
                metadata['trap_memory'] = trap_regions
            capture_file = recorder.submit(decision_sequence, inputs, metadata) if recorder else None
            outcomes.begin(decision_sequence, state['completed_destinations'], (x, y), (gx, gy))
            # Keep large per-point evidence in the compressed snapshot, not in
            # the bounded ROS event stream or every in-memory mission event.
            decision_event('requested', capture_file=capture_file, input_metadata=compact_event_metadata(metadata),
                           input_pose=[x,y,yaw], heading_hint=heading_hint,
                           active_goal=target, active_goal_id=active_goal_id)
            planning = planner.submit(*((evaluate_with_trap_memory, trap_regions) if trap_regions
                                        else (evaluate_observed_navigation,)),
                inputs['origin'], inputs['resolution'], inputs['width'], inputs['height'], inputs['costs'],
                inputs['robot_xy'], inputs['robot_yaw'], inputs['destination'], inputs['lane_points'],
                heading_hint=heading_hint, frozen_guidance=frozen_guidance, **planner_options, **scorer_options)
            planning_deadline = min(end, time.monotonic()+8)
            while not planning.done():
                spin(.02)
                if time.monotonic() > planning_deadline:
                    raise RuntimeError('Bounded sensor mission timed out' if time.monotonic() >= end
                                       else 'Observed route search exceeded its time budget')
                check_live(time.monotonic(), armed_at, initial_run)
            evaluation = planning.result()
            plan = evaluation['plan']
            if entrance_tracking:
                memory_evaluated_at = time.monotonic()
                corridor = evaluation['diagnostics'].get('corridor')
                support = corridor_fresh_support(corridor, evidence_rows,
                    memory_evaluated_at-evidence_received_at if evidence_received_at is not None else float('inf'))
                evaluation['diagnostics']['memory_refresh_support'] = support
                heading_memory.observe(corridor if support['valid'] else None,
                                       latest['pose'][:2], memory_evaluated_at,
                                       support_stamp_ns=support.get('support_stamp_ns'))
                evaluation['diagnostics']['memory'] = dict(heading_memory.diagnostics)
                evaluation['diagnostics']['memory_evaluated_monotonic_s'] = memory_evaluated_at
            decision_event('evaluated', input_pose=[x,y,yaw], input_age_wall_s=time.monotonic()-submitted_at,
                           search_wall_s=evaluation['search_wall_s'],
                           diagnostics=evaluation['diagnostics'], plan=plan)
            outcomes.evaluated(decision_sequence, plan, evaluation['diagnostics'], evaluation['search_wall_s'])
            if not entrance_tracking and plan is not None and 'corridor' in plan['diagnostics']:
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
                    if not recovery_budget.available:
                        # Exhausted recovery is not proof that collision search
                        # found no route: a valid endpoint may still stall Nav2.
                        state['recovery_limit'] = dict(destination=cursor,
                            budget=recovery_budget.report(), forward_plan_available=plan is not None,
                            controller_failures=failures, stationary_seconds=now-progress_at)
                        raise RuntimeError('Backup recovery budget exhausted: '
                            + ('forward plan available but execution stalled' if plan is not None
                               else 'no forward plan available'))
                    if not backup.wait_for_server(timeout_sec=2):
                        raise RuntimeError('Backup recovery action server unavailable')
                    # Stop first, then look for a rear pose with a useful forward
                    # escape. Do not repeatedly back up an arbitrary 0.3 m.
                    recovery_grid = latest['grid'][1]
                    rx, ry, ryaw = latest['pose']
                    # Select once at the actual trap, never independently at
                    # each hypothetical backed-up pose. Preserve an already
                    # active escape intent through a second bounded attempt.
                    selected = preserved_guidance((rx,ry,ryaw), time.monotonic(), cursor)
                    if selected is None:
                        selection_diagnostics = {}
                        selected = select_observed_guidance(latest.get('lane_xy', []),
                            (rx,ry), ryaw, (gx,gy),
                            heading_memory.propose((rx,ry),ryaw,time.monotonic(),lookahead=7.),
                            entrance_tracking=entrance_tracking, lookahead=7.,
                            guidance_diagnostics=selection_diagnostics)
                        selected, gate_selection = refine_corridor_guidance(selected,
                            selection_diagnostics.get('corridor'),
                            (recovery_grid.info.origin.position.x,recovery_grid.info.origin.position.y),
                            recovery_grid.info.resolution,recovery_grid.info.width,recovery_grid.info.height,
                            recovery_grid.data, goal_footprint)
                        decision_event('recovery_gate_selection', diagnostics=gate_selection)
                        if selected is None:
                            raise RuntimeError('No observed clear lane-entry position for recovery')
                    decision_event('recovery_guidance_selected', selection=selected,
                        selection_pose=[rx,ry,ryaw], grid_stamp_ns=stamps.get('grid'))
                    recovery_options = dict(robot_radius=.5,lookahead=7.,max_path_length=14.,
                        min_progress=.1,forward_only=True,minimum_turn_radius=.65,
                        min_goal_distance=.4,continuation_reserve=1.,
                        body_clearance_weight=args.body_clearance_weight)
                    recovery_args = ((recovery_grid.info.origin.position.x,recovery_grid.info.origin.position.y),
                        recovery_grid.info.resolution,recovery_grid.info.width,recovery_grid.info.height,
                        recovery_grid.data,(rx,ry),ryaw,(gx,gy))
                    if trap_memory is None:
                        guidance = partial(plan_observed_navigation, lane_points=[],
                            frozen_guidance=selected, entrance_tracking=entrance_tracking)
                        search = planner.submit(select_backup_recovery, *recovery_args,
                            goal_footprint=goal_footprint, forward_planner=guidance,
                            max_search_seconds=5., forward_options=recovery_options)
                        search_deadline=min(end,time.monotonic()+8.)
                    else:
                        # Remember this stall from the robot's own pose and recent
                        # odometry; never from course data. Bounded and expiring.
                        driven_path = recent_path(state['trajectory'], max_age_s=60., max_length_m=6.)
                        # Never remember a region that would cover the current destination
                        # (2 m GPS goal radius): that stall is the goal approach, not a pocket.
                        region = trap_memory.record((rx,ry,ryaw), time.monotonic(), cursor,
                                                    entry_heading(driven_path), protect_xy=(gx,gy), protect_radius_m=2.)
                        decision_event('trap_memory_recorded' if region else 'trap_memory_skipped_near_destination', region=region,
                                       driven_path_m=sum(math.dist(a,b) for a,b in zip(driven_path,driven_path[1:])))
                        selected, exclusion = exclude_trapped_guidance(selected, (gx,gy),
                            trap_memory.regions(), stall_xy=(rx,ry))
                        if exclusion['excluded']:
                            decision_event('recovery_guidance_excluded', diagnostics=exclusion,
                                           selection=selected)
                        if selected is None:
                            raise RuntimeError('Recovery guidance and destination lie inside remembered trap')
                        guidance = partial(plan_observed_navigation, lane_points=[],
                            frozen_guidance=selected, entrance_tracking=entrance_tracking)
                        search = planner.submit(select_trap_escape, *recovery_args,
                            goal_footprint=goal_footprint, driven_path=driven_path,
                            trap_regions=trap_memory.regions(), forward_planner=guidance,
                            forward_options=recovery_options, straight_seconds=5., retrace_seconds=8.)
                        # Masking/input checks and the cooperative 5+8 s searches.
                        search_deadline=min(end,time.monotonic()+16.)
                    while not search.done():
                        spin(.02)
                        check_live(time.monotonic(),armed_at,initial_run)
                        if time.monotonic()>search_deadline:
                            raise RuntimeError('Backup clearance search exceeded its time budget')
                    escape=search.result()
                    check_live(time.monotonic(),armed_at,initial_run)
                    if escape is None:
                        raise RuntimeError('No observed collision-free backup with useful forward clearance')
                    backup_distance=escape['distance_m']
                    recovery_budget.consume(latest['pose'])
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
                        spin(.05)
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
                        'selected_guidance':selected,
                        'budget':recovery_budget.report(),
                        'clearance_search':escape['diagnostics']})
                    if trap_memory is not None:
                        state['recoveries'][-1].update(escape_type=escape['escape_type'],
                            trap_memory=trap_memory.regions())
                    recovery_intent.install(selected, (rx,ry,ryaw), latest['pose'],
                                            time.monotonic(), cursor)
                    decision_event('recovery_intent_started', diagnostics=dict(recovery_intent.diagnostics))
                    no_plan_since = None
                    progress_pose = latest['pose'][:2]; progress_at = time.monotonic()
                    failures = 0
                continue
            no_plan_since = None
            # A direct path can change sides of an obstacle while keeping the
            # same endpoint. Always deliver its refreshed checked geometry.
            if not direct_path and target is not None and handle is not None and not result.done() and math.hypot(target[0]-plan['local_goal'][0], target[1]-plan['local_goal'][1]) < 1.:
                decision_event('retained_goal', goal=target, proposed_goal=plan['local_goal'],
                               proposed_yaw=plan['yaw'], goal_id=active_goal_id)
                continue
            target = plan['local_goal']
            check_live(time.monotonic(), armed_at, initial_run)
            path = RosPath(); path.header = grid.header
            if direct_path:
                entry_pose = latest['pose']
                entry_grid = latest['grid'][1]
                admitted, admission = prepare_controller_plan(plan, entry_pose,
                    (entry_grid.info.origin.position.x, entry_grid.info.origin.position.y),
                    entry_grid.info.resolution, entry_grid.info.width, entry_grid.info.height,
                    entry_grid.data, goal_footprint)
                decision_event('path_entry', admission=admission, checked_pose=entry_pose,
                    grid_stamp_ns=stamps.get('grid'), input_age_wall_s=time.monotonic()-submitted_at)
                outcomes.update(decision_sequence, admitted=admitted is not None)
                if admitted is None:
                    # The robot may have turned away from the worker's starting
                    # pose. Do not ask the controller to invent a connection.
                    if handle is not None:
                        cancel_action(handle); handle = None
                    result = None; target = None
                    continue
                plan = admitted
                path.poses = [pose(px, py, pyaw, grid.header)
                              for px, py, pyaw in controller_path(plan)]
                request = FollowPath.Goal(); request.path = path
                request.controller_id = 'FollowPath'
                request.goal_checker_id = 'goal_checker'
                request.progress_checker_id = 'progress_checker'
            else:
                request = NavigateToPose.Goal(); request.pose = pose(*target, plan['yaw'], grid.header)
                path.poses = [pose(px, py, pyaw, grid.header) for (px, py), pyaw in
                              zip(plan['path'], plan.get('path_yaws', [0.]*len(plan['path'])))]
            def pause(seconds):
                until = time.monotonic()+seconds
                while time.monotonic() < until:
                    spin(.05)
                check_live(time.monotonic(), armed_at, initial_run)
            sent_from = latest['pose']
            handle = send_goal_with_startup_retry(lambda: wait(nav.send_goal_async(request)),
                nav.wait_for_server, pause, state.setdefault('startup_goal_retries', []),
                startup=not goal_accepted_once,
                still_startup=lambda: math.dist(latest['pose'][:2], sent_from[:2]) <= .05)
            if not handle.accepted:
                outcomes.update(decision_sequence, action='rejected')
                raise RuntimeError('Nav2 rejected observed local goal')
            goal_accepted_once = True
            outcomes.update(decision_sequence, action='accepted')
            previous_goal_id = active_goal_id
            active_decision = decision_sequence
            active_goal_id = bytes(handle.goal_id.uuid).hex()
            decision_event('sent_goal', goal=target, goal_yaw=plan['yaw'],
                           goal_id=active_goal_id, replaced_goal_id=previous_goal_id,
                           input_age_wall_s=time.monotonic()-submitted_at)
            result = handle.get_result_async()
            result.add_done_callback(partial(action_finished, sequence=active_decision,
                                             goal_id=active_goal_id))
            path_pub.publish(path)
            state['plans'].append({'destination': state['completed_destinations'], 'goal': target,
                                   'goal_yaw': plan['yaw'],
                                   'diagnostics': plan['diagnostics']})
        else:
            raise RuntimeError('Bounded sensor mission timed out')
    except (RuntimeError, ValueError, OSError, KeyboardInterrupt) as exc:
        state['status'] = 'stopped'; state['reason'] = str(exc)
        print(state['reason'], flush=True)
    finally:
        finishing = True
        # Capture before cleanup waits obscure the timing around the actual stop.
        state['sensor_health'] = telemetry.report()
        state['recovery_budget'] = recovery_budget.report()
        if trap_memory is not None:
            state['trap_memory'] = trap_memory.report()
        if armed_at is not None:
            state['elapsed_wall_s'] = time.monotonic()-armed_at
        decision_event('mission_end', status=state['status'], reason=state.get('reason'))
        cleanup = [('disable autonomy', lambda: set_mode(gate, False)),
                   ('cancel action', lambda: cancel_action(handle) if handle is not None else None),
                   ('reset unmarked mode', lambda: set_mode(zone, False))]
        for label, operation in cleanup:
            try:
                operation()
            except RuntimeError as exc:
                state.setdefault('cleanup_errors', []).append(label+': '+str(exc))
                state['status'] = 'stopped'
        if mission_health.active:
            sample_mission_health()
            stopped_at = time.monotonic()
            state['mission_health_interval'] = mission_health.end(stopped_at, stamps.get('odom'))
            state['health_trajectory_end_index'] = len(state['trajectory'])-1
            state['elapsed_wall_s'] = stopped_at-armed_at
            state['sensor_health'] = telemetry.report()
        node.destroy_timer(health_timer)
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
                snapshot.update(grid_stamp_ns=grid.header.stamp.sec*1_000_000_000+grid.header.stamp.nanosec,
                                grid_age_wall_s=time.monotonic()-latest['grid'][0],
                                odom_stamp_ns=stamps.get('odom'), lane_stamp_ns=stamps.get('lanes'),
                                course_sha256=state.get('course_sha256'))
                if goal_footprint is not None:
                    snapshot['goal_footprint'] = list(goal_footprint)
                Path(args.report).with_suffix('.observations.json').write_text(json.dumps(snapshot)+'\n')
            output = Path(args.report)
            if recorder:
                outcomes.close(latest['pose'][:2] if 'pose' in latest else None)
                state['decision_capture'] = recorder.close()
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
            signal.signal(signal.SIGINT, previous_sigint)
    return 0 if state['status'] == 'completed' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mission', required=True)
    parser.add_argument('--report', required=True)
    parser.add_argument('--timeout', type=float, default=600.)
    parser.add_argument('--speed', type=float, default=2.2,
                        help='Maximum requested speed in m/s; controller slows for observed geometry')
    parser.add_argument('--capture-dir', type=Path,
                        help='New directory for compressed exact-input decision snapshots')
    parser.add_argument('--planning-budget', type=float, default=5.,
                        help='Forward search wall budget in seconds; lane extraction is additional')
    parser.add_argument('--body-clearance-weight', type=float, default=0.,
                        help='Experimental soft full-body clearance preference (0 disables; maximum 10)')
    parser.add_argument('--goal-policy', choices=('rolling', 'hold'), default='rolling',
                        help='Use hold only for controlled goal-preemption comparisons')
    parser.add_argument('--guidance-memory', choices=('heading', 'entrance'), default='heading',
                        help='Entrance is an experimental fixed observed-target memory')
    parser.add_argument('--escape', choices=('legacy', 'retrace'), default='legacy',
                        help='Experimental retrace adds bounded stall memory and a longer '
                             'corridor-contained straight BackUp when the short one fails')
    # Learned scorers re-rank only already-admissible options; weight 0 (default) is today's policy.
    # Models hold learned weights over observed features only (tools/learning, docs/LEARNING_PLAN.md).
    parser.add_argument('--route-scorer', type=Path, help='Learned route-alternative scorer JSON')
    parser.add_argument('--route-weight', type=float, default=0.)
    parser.add_argument('--corridor-scorer', type=Path, help='Learned lane-corridor scorer JSON')
    parser.add_argument('--corridor-weight', type=float, default=0.)
    parser.add_argument('--path-execution', choices=('nav2-goal', 'checked-path'), default='nav2-goal',
                        help='Experimental checked-path sends the observed swept path to FollowPath')
    args = parser.parse_args()
    if not math.isfinite(args.speed) or not 0 < args.speed <= 2.2 or not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error('Use speed (0, 2.2] m/s and a positive finite timeout')
    if not math.isfinite(args.planning_budget) or not .05 <= args.planning_budget <= 5.:
        parser.error('Use a planning budget between 0.05 and 5 seconds')
    if not math.isfinite(args.body_clearance_weight) or not 0 <= args.body_clearance_weight <= 10:
        parser.error('Use a body clearance weight between 0 and 10')
    for name in ('route', 'corridor'):
        weight, model = getattr(args, name+'_weight'), getattr(args, name+'_scorer')
        if not math.isfinite(weight) or not 0 <= weight <= 10:
            parser.error(f'Use a {name} weight between 0 and 10')
        if weight > 0 and (model is None or not model.is_file()):
            parser.error(f'A positive {name} weight needs an existing --{name}-scorer model')
    # Per instance when IGVC_INSTANCE is set (parallel simulations); otherwise the original path.
    lock_path = session_dir()/'full-course.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        raise SystemExit(run(args))
