"""Offline sensor-run scorer. Course geometry is evaluation-only, never control input."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

from generate_course_variant import BODY_RADIUS, body_clearance
from gps_mission import LocalFrame
from course_judge import (identity_evidence, paint_evidence, topology_evidence, ramp_body_evidence,
                          world_points)
from finish_crossing import (AUDIT_TOLERANCE, CONTRACT_VERSION, FIXTURE_HALF_SPAN_M, FIXTURE_LINE,
                             LEGACY_CONTRACT, FinishCrossingTracker, select_contract)
from sensor_telemetry import SensorTelemetry


def finish_line_compatibility(run, course, mission):
    """Establish the fixed finish-crossing/1 line independently of runtime claims.

    The line is always FIXTURE_LINE: public origin, +X normal, 3 m half span.
    A claimed line or limit that differs is rejected, never adopted, and an
    incompatible course or mission fails instead of choosing another line.
    """
    reasons = []
    tol = AUDIT_TOLERANCE
    policy = FinishCrossingTracker(FIXTURE_LINE).policy()
    for key, value in run['finish_crossing'].items():
        if key in policy and (isinstance(value, bool) or value != policy[key]):
            reasons.append(f'claimed_{key}_mismatch')
    try:
        origin = mission['origin']
        if origin.get('world_frame') != 'odom' or origin.get('axes') != 'x_east_y_north_z_up':
            reasons.append('mission_frame_not_odom_x_east_y_north_z_up')
        frame = LocalFrame(origin)
        if math.hypot(*frame.to_enu(origin['latitude'], origin['longitude'], origin['altitude'])[:2]) > tol:
            reasons.append('mission_origin_not_enu_zero')
        goals = mission['goals']
        if len(goals) != 6:
            reasons.append('mission_not_six_destinations')
        elif math.hypot(*frame.to_enu(goals[5]['latitude'], goals[5]['longitude'],
                                      goals[5]['altitude'])[:2]) > tol:
            reasons.append('final_destination_not_origin')
        points, widths = world_points(course)
        unit = lambda a, b: tuple((b[k]-a[k])/math.dist(a, b) for k in range(2))
        if max(math.dist(points[0], (0., 0.)), math.dist(points[-1], (0., 0.))) > tol:
            reasons.append('world_loop_not_at_origin')
        for name, direction in (('first', unit(points[0], points[1])), ('last', unit(points[-2], points[-1]))):
            if abs(direction[0]-FIXTURE_LINE.normal[0]) > tol or abs(direction[1]-FIXTURE_LINE.normal[1]) > tol:
                reasons.append(f'world_{name}_segment_not_plus_x')
        if min(widths[0], widths[-1]) < FIXTURE_HALF_SPAN_M-tol:
            reasons.append('world_half_width_below_line_span')
    except (KeyError, TypeError, ValueError, AttributeError, IndexError, ZeroDivisionError):
        reasons.append('invalid_course_or_mission_geometry')
    return dict(passed=not reasons, reasons=reasons, line=FIXTURE_LINE.describe())


def mission_identity_evidence(run, expected_hash):
    observed = run.get('mission_sha256')
    valid = lambda value: isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None
    passed = valid(expected_hash) and valid(observed) and observed == expected_hash
    return dict(passed=passed, expected_mission_sha256=expected_hash,
                observed_mission_sha256=observed,
                status='matched' if passed else 'missing' if expected_hash is None or observed is None
                else 'mismatched' if valid(expected_hash) and valid(observed) else 'invalid')


def sensor_health_evidence(run, samples):
    """Validate latest schema-1 claims without inventing full-interval evidence.

    Schema 1 has bounded recent events and a latest processing summary. Neither
    establishes health throughout the trajectory: first receipts/acquisitions
    and an interval health monitor are absent. Even a latest pass stays open.
    """
    result = dict(latest_processing_status='unknown', latest_processing_passed=False,
                  interval_status='unverified', interval_verified=False,
                  interval_reason='missing_sensor_health', complete=False)
    health = run.get('sensor_health')
    if not isinstance(health, dict):
        return result
    if type(health.get('schema_version')) is not int or health['schema_version'] != 1:
        result['interval_reason'] = 'unsupported_sensor_health_schema'
        return result
    result['interval_reason'] = 'schema_v1_has_no_full_interval_health_proof'
    streams = health.get('streams')
    latest = health.get('latest_status')
    required = ('clock', 'lanes', 'depth_processing', 'lane_health', 'depth_health')
    number = lambda value: type(value) in (int, float) and math.isfinite(value) and value >= 0
    if (not isinstance(streams, dict) or not isinstance(latest, dict)
            or any(not isinstance(streams.get(name), dict)
                   or type(streams[name].get('count')) is not int or streams[name]['count'] <= 0
                   or not number(streams[name].get('age_wall_s')) for name in required)):
        result['latest_processing_reason'] = 'incomplete_or_invalid_telemetry_streams'
        return result
    clock_stamp = streams['clock'].get('last_stamp_ns')
    if type(clock_stamp) is not int or not 0 <= clock_stamp < 2**63:
        result['latest_processing_reason'] = 'missing_or_invalid_clock_acquisition'
        return result
    # Reuse the actual processing contract: lanes.valid=False may describe a
    # legitimate paint gap, while failed health Bools or depth processing fail.
    telemetry = SensorTelemetry(clock=lambda: 0.)
    telemetry.sim_ns = clock_stamp
    telemetry.streams = {name: {'last_wall': -streams[name]['age_wall_s']} for name in required}
    telemetry.last_status = latest
    derived = telemetry.health_summary(now=0.)
    claimed = health.get('processing_health_summary')
    consistent = (isinstance(claimed, dict) and claimed.get('status') == derived['status']
                  and claimed.get('fresh_successful_processing') is derived['fresh_successful_processing'])
    result.update(latest_processing_status=derived['status'] if consistent else 'unknown',
                  latest_processing_passed=consistent and derived['status'] == 'pass',
                  latest_processing_reason='derived_from_recorded_streams_and_status'
                      if consistent else 'missing_or_inconsistent_processing_summary',
                  latest_processing=derived)
    result['telemetry_duration_wall_s'] = health.get('duration_wall_s')
    result['mission_elapsed_wall_s'] = run.get('elapsed_wall_s')
    result['telemetry_clock_end_sim_s'] = clock_stamp/1e9
    if samples:
        result['trajectory_start_sim_s'] = samples[0][0]
        result['trajectory_end_sim_s'] = samples[-1][0]
        if abs(clock_stamp/1e9-samples[-1][0]) > derived['max_acquisition_lag_sim_s']:
            result['interval_reason'] = 'telemetry_clock_does_not_match_trajectory_end'
    duration, elapsed = health.get('duration_wall_s'), run.get('elapsed_wall_s')
    if not number(duration) or not number(elapsed) or duration < elapsed:
        result['interval_reason'] = 'missing_or_inconsistent_wall_interval'
    if (isinstance(run.get('mission_health_interval'), dict)
            and result['interval_reason'] == 'schema_v1_has_no_full_interval_health_proof'):
        interval = mission_interval_evidence(run, samples)
        result.update(interval)
        result['complete'] = result['latest_processing_passed'] and interval['interval_verified']
    return result


def mission_interval_evidence(run, samples):
    """Bind a sampled processing ledger to the actual armed trajectory interval.

    Aggregated counters/maxima cover the entire interval even when recent event
    history is bounded. This does not claim continuous health between samples.
    """
    result = dict(interval_status='unverified', interval_verified=False,
                  interval_reason='invalid_mission_health_ledger')
    value = run['mission_health_interval']
    finite = lambda v: type(v) in (int, float) and math.isfinite(v)
    try:
        if (type(value['schema_version']) is not int or value['schema_version'] != 1
                or value['completed'] is not True or not samples):
            return result
        count, valid = value['sample_count'], value['valid_sample_count']
        totals = value['totals']
        if (type(count) is not int or type(valid) is not int or count < 2 or valid != count
                or set(totals) != {'pass','fail','unknown'}
                or any(type(n) is not int or n < 0 for n in totals.values())
                or sum(totals.values()) != count):
            return result
        result.update(interval_status=value['status'], interval_reason='sampled_processing_health_not_passed',
                      interval_sample_count=count, interval_totals=totals,
                      interval_max_gap_s=value['max_gap_including_bounds_s'])
        if (value['passed'] is not True or value['coverage_complete'] is not True
                or value['status'] != 'pass' or totals['pass'] != count
                or value['latched_fail'] is not False or value['latched_unknown'] is not False
                or value['integrity_errors'] or value['failure_reasons']
                or value['first_fail'] is not None or value['first_unknown'] is not None):
            return result
        bounds = [value[name] for name in ('start','first_sample','last_sample','end')]
        if any(not finite(b['monotonic_s']) or type(b['odom_stamp_ns']) is not int
               or not 0 <= b['odom_stamp_ns'] < 2**63 for b in bounds):
            return result
        wall = [b['monotonic_s'] for b in bounds]
        sim = [b['odom_stamp_ns'] for b in bounds]
        gap_names = ('first_gap_s','max_interior_gap_s','tail_gap_s','max_gap_including_bounds_s')
        gaps = [value[name] for name in gap_names]
        if (any(b < a for a,b in zip(wall,wall[1:])) or wall[0] == wall[-1]
                or any(b < a for a,b in zip(sim,sim[1:])) or sim[0] == sim[-1]
                or not finite(value['max_gap_s']) or not 0 < value['max_gap_s'] <= .25
                or any(not finite(g) or not 0 <= g <= value['max_gap_s']+1e-9 for g in gaps)
                or abs(gaps[0]-(wall[1]-wall[0])) > 1e-8
                or abs(gaps[2]-(wall[3]-wall[2])) > 1e-8
                or abs(gaps[3]-max(gaps[:3])) > 1e-8
                or (wall[2]-wall[1]) > (count-1)*gaps[1]+1e-7
                or not finite(run['elapsed_wall_s'])
                or not finite(value['elapsed_wall_s']) or not finite(value['elapsed_sim_s'])
                or abs(wall[3]-wall[0]-run['elapsed_wall_s']) > 1e-6
                or abs(value['elapsed_wall_s']-run['elapsed_wall_s']) > 1e-6
                or abs(value['elapsed_sim_s']-(sim[3]-sim[0])/1e9) > 1e-6
                or value['health_limits'] != {'max_age_wall_s':1.5,'max_acquisition_lag_sim_s':1.5}):
            result['interval_reason'] = 'inconsistent_or_incomplete_sampling_coverage'
            return result
        first, last = run['health_trajectory_start_index'], run['health_trajectory_end_index']
        if (type(first) is not int or type(last) is not int or not 0 <= first < last < len(samples)
                or abs(samples[first][0]-sim[0]/1e9) > 1e-7
                or abs(samples[last][0]-sim[-1]/1e9) > 1e-7):
            result['interval_reason'] = 'ledger_not_bound_to_trajectory'
            return result
        # Startup/shutdown rows outside the ledger may only record a stationary
        # body. Otherwise a good short interval cannot certify a moving lap.
        for group, anchor in ((samples[:first],samples[first]),(samples[last+1:],samples[last])):
            if any(math.dist(row[1:3],anchor[1:3]) > .001 or
                   abs(math.atan2(math.sin(row[3]-anchor[3]),math.cos(row[3]-anchor[3]))) > .001
                   for row in group):
                result['interval_reason'] = 'unmonitored_trajectory_motion'
                return result
        events = value['recent_events']
        if (type(value['event_limit']) is not int or value['event_limit'] < 2
                or len(events) != min(count,value['event_limit'])
                or any(e['status'] != 'pass' or not finite(e['monotonic_s'])
                       or not wall[0] <= e['monotonic_s'] <= wall[3]
                       or type(e['odom_stamp_ns']) is not int
                       or not sim[0] <= e['odom_stamp_ns'] <= sim[3] for e in events)
                or events[-1]['monotonic_s'] != wall[2]
                or events[-1]['odom_stamp_ns'] != sim[2]
                or (count <= value['event_limit'] and
                    (events[0]['monotonic_s'] != wall[1] or events[0]['odom_stamp_ns'] != sim[1]))
                or any(b['monotonic_s'] <= a['monotonic_s'] or
                       b['odom_stamp_ns'] < a['odom_stamp_ns'] or
                       b['monotonic_s']-a['monotonic_s'] > gaps[1]+1e-9
                       for a,b in zip(events,events[1:]))):
            result['interval_reason'] = 'inconsistent_sample_history'
            return result
        result.update(interval_verified=True, interval_status='pass',
                      interval_reason='sampled_processing_health_covers_armed_motion',
                      interval_scope=value['scope'])
    except (KeyError, TypeError, ValueError, IndexError, OverflowError):
        result['interval_reason'] = 'invalid_mission_health_ledger'
    return result


def ramp_traversal(samples, ramp):
    """Find forward entry-to-exit axle-centre traversal inside ramp side edges.

    Ramp x/y denotes the entry and yaw points along its positive longitudinal
    axis. This checks the driven axle, not the centre of the asymmetric body.
    Segment intersections use the same linear interpolation as the motion audit.
    """
    length = 2 * ramp['rise_length'] + ramp['deck_length']
    half_width = ramp['width'] / 2
    c, s = math.cos(ramp['yaw']), math.sin(ramp['yaw'])
    local = []
    for stamp, x, y, _ in samples:
        dx, dy = x-ramp['x'], y-ramp['y']
        local.append((c*dx+s*dy, -s*dx+c*dy))
    entered = None
    for index, (a, b) in enumerate(zip(local, local[1:])):
        du = b[0]-a[0]
        start_fraction = 0.
        if entered is None:
            if not (a[0] <= 0 < b[0]):
                continue
            start_fraction = -a[0]/du
            entry_lateral = a[1]+start_fraction*(b[1]-a[1])
            if abs(entry_lateral) > half_width:
                continue
            entered = index+start_fraction
        if b[0] < 0:
            entered = None
            continue
        exits = du > 0 and a[0] < length <= b[0]
        end_fraction = (length-a[0])/du if exits else 1.
        start_lateral = a[1]+start_fraction*(b[1]-a[1])
        end_lateral = a[1]+end_fraction*(b[1]-a[1])
        if max(abs(start_lateral), abs(end_lateral)) > half_width:
            entered = None
            continue
        if exits:
            return {'ramp_id': ramp.get('id'), 'passed': True,
                    'entry_trajectory_index': entered,
                    'exit_trajectory_index': index+end_fraction,
                    'longitudinal_span_m': length}
    return {'ramp_id': ramp.get('id'), 'passed': False,
            'longitudinal_span_m': length,
            'reason': 'No ordered positive-longitudinal entry-to-exit axle traversal within ramp width'}


def audit(run, course, mission=None, *, course_sha256=None, mission_sha256=None, open_area_lateral_m=8.):
    """Check sampled motion and conservative sweeps under linear pose interpolation.

    WORLD centerline and paint geometry are scoring-only. Guide routes and guided
    checkpoints are not consumed. Exact manifest-byte identity is required for
    certification; historical reports remain readable but fail closed without it.
    """
    samples = run.get('trajectory', [])
    valid = (len(samples) >= 2 and all(len(p) == 4 and
             all(isinstance(v, (int, float)) and math.isfinite(v) for v in p)
             for p in samples))
    identity = identity_evidence(run, course_sha256)
    mission_identity = mission_identity_evidence(run, mission_sha256)
    health = sensor_health_evidence(run, samples if valid else [])
    # Absence keeps legacy radius grading; anything but finish-crossing/1 fails closed.
    try:
        contract, contract_error = select_contract(run), None
    except ValueError as error:
        contract, contract_error = 'unsupported', str(error)
    crossing_contract = contract != LEGACY_CONTRACT
    checks = {
        'course_identity_matches': identity['passed'],
        'mission_identity_matches': mission_identity['passed'],
        'sensor_health_latest_processing_passes': health['latest_processing_passed'],
        'sensor_health_interval_verified': health['interval_verified'],
        'completed_six_destinations': run.get('status') == 'completed'
            and run.get('completed_destinations') == 6 and run.get('total_destinations') == 6,
        'sensor_led_mode': run.get('mode') == 'sensor-led',
        'scoring_guard': bool(re.search(r'(?:^|\s)line_guard=scoring(?:\s|$)', run.get('sim_status', ''))),
        'zero_line_blocks': bool(re.search(r'(?:^|\s)line_blocks=0(?:\s|$)', run.get('sim_status', ''))),
        'finite_trajectory': valid,
    }
    finish = dict(contract_version=contract, error=contract_error)
    if crossing_contract:
        compatibility = (finish_line_compatibility(run, course, mission) if contract == CONTRACT_VERSION
                         else dict(passed=False, reasons=['unsupported_finish_contract']))
        finish['compatibility'] = compatibility
        checks['finish_contract_supported'] = compatibility['passed']
    report = {'passed': False, 'source_status': run.get('status'),
              'finish_contract': contract, 'finish_crossing': finish,
              'completed_destinations': run.get('completed_destinations'),
              'checks': checks, 'sample_count': len(samples),
              'topology_certified': False, 'full_loop_certified': False,
              'geometric_full_loop_certified': False,
              'paint_crossing_certified': False, 'course_identity': identity,
              'mission_identity': mission_identity, 'sensor_health_evidence': health,
              'certification_status': 'uncertified',
              'limitations': 'Offline ideal geometry evidence, not contact physics. Swept bounds assume '
                  'linear translation and shortest-angle rotation between recorded poses. Gaps fail '
                  'continuity. Topology uses an explicit development lateral tolerance in unpainted '
                  'areas, not a competition rule. Intended direction is WORLD centerline array order; '
                  'initial yaw is not assumed. Course and mission identity require exact file-byte SHA-256. '
                  'Aggregate sensor-led acceptance also requires a trajectory-bound processing ledger '
                  'with sampled coverage gaps at most 0.25 s; this is not continuous physical health. '
                  'Geometric evidence is reported separately.'}
    if not valid:
        return report

    obstacles = course.get('obstacles', [])
    checks['obstacle_geometry_available'] = bool(obstacles)
    minimum = None
    min_bound = math.inf
    collision_samples = uncertain_segments = subdivisions = 0
    travelled = max_speed = 0.
    gaps, nonincreasing, speed_violations = [], [], []

    def clearance(pose, index):
        nonlocal minimum, collision_samples
        result = math.inf
        for obstacle in obstacles:
            value = body_clearance(pose[:2], pose[2], obstacle)
            if value < result:
                result = value
            if minimum is None or value < minimum['clearance_m']:
                minimum = {'clearance_m': value, 'trajectory_index': index,
                           'pose': list(pose), 'obstacle_id': obstacle.get('id')}
        collision_samples += int(result <= 0.)
        return result

    previous_clearance = clearance(samples[0][1:], 0)
    for index, (a, b) in enumerate(zip(samples, samples[1:]), 1):
        dt = b[0] - a[0]
        distance = math.dist(a[1:3], b[1:3])
        travelled += distance
        if dt <= 0:
            nonincreasing.append(index)
        else:
            speed = distance / dt
            max_speed = max(max_speed, speed)
            if speed > 2.2 + 1e-6:
                speed_violations.append(index)
            if dt > .5:
                gaps.append(index)
        angle = math.atan2(math.sin(b[3]-a[3]), math.cos(b[3]-a[3]))
        # Every body point moves at most translation + radius * |rotation|.
        motion_bound = distance + BODY_RADIUS * abs(angle)
        count = max(1, math.ceil(motion_bound / .02))
        # Discontinuous/malicious trajectories should not cause unbounded work.
        if count > 10000:
            uncertain_segments += 1
            previous_clearance = clearance(b[1:], index)
            continue
        step_bound = motion_bound / count
        for step in range(1, count + 1):
            fraction = step / count
            pose = (a[1] + (b[1]-a[1])*fraction,
                    a[2] + (b[2]-a[2])*fraction, a[3] + angle*fraction)
            current = clearance(pose, index-1+fraction)
            # Every interpolated instant is within half a substep of an endpoint.
            bound = min(previous_clearance, current) - step_bound / 2
            min_bound = min(min_bound, bound)
            uncertain_segments += int(bound <= 0.)
            previous_clearance = current
            subdivisions += 1

    checks['trajectory_continuous'] = not gaps and not nonincreasing
    checks['speed_at_most_2_2_mps'] = not speed_violations
    checks['sampled_obstacles_clear'] = bool(obstacles) and collision_samples == 0
    checks['swept_obstacles_clear'] = bool(obstacles) and uncertain_segments == 0
    final_distance = math.hypot(samples[-1][1], samples[-1][2])
    if not crossing_contract:
        checks['returned_within_0_4_m'] = final_distance <= .4
    ramp_evidence = [ramp_traversal(samples, ramp) for ramp in course.get('ramps', [])]
    checks['all_ramps_traversed_entry_to_exit'] = bool(ramp_evidence) and all(
        evidence['passed'] for evidence in ramp_evidence)
    report['ramp_traversals'] = ramp_evidence
    body_ramps = [ramp_body_evidence(samples, ramp) for ramp in course.get('ramps', [])]
    report['ramp_body_containment'] = body_ramps
    checks['all_ramps_body_contained_entry_to_departure'] = bool(body_ramps) and all(
        evidence['passed'] for evidence in body_ramps)
    report['wheel_support_certified'] = False
    report['limitations'] += (' Ramp axle and body-side XY containment are separate evidence. '
                              'The asymmetric rectangle is not a physical wheel-support polygon; '
                              'wheel contact, elevation, suspension and rollover are not certified.')

    visits = []
    if mission is not None:
        frame = LocalFrame(mission['origin'])
        cursor = 0
        # Under the crossing contract only the first five are radius visits.
        for goal in mission.get('goals', [])[:5 if crossing_contract else None]:
            x, y, _ = frame.to_enu(goal['latitude'], goal['longitude'], goal['altitude'])
            while cursor < len(samples) and math.hypot(samples[cursor][1]-x, samples[cursor][2]-y) > goal['radius_m']:
                cursor += 1
            if cursor == len(samples):
                break
            visits.append({'destination_index': len(visits), 'sample_index': cursor,
                           'stamp': samples[cursor][0]})
    six_goals = mission is not None and len(mission.get('goals', [])) == 6
    crossing = None
    if crossing_contract:
        # Independent reconstruction: runtime counts, claimed crossings and
        # indices are never consulted. Eligibility starts after the fifth visit.
        fifth = visits[4]['sample_index'] if six_goals and len(visits) == 5 else None
        if checks['finish_contract_supported']:
            tracker = FinishCrossingTracker(FIXTURE_LINE)
            for index, (stamp, x, y, _) in enumerate(samples):
                tracker.observe(stamp, x, y, eligible=fifth is not None and index > fifth)
            crossing = tracker.crossing
            finish['audit'] = tracker.report()
        finish['fifth_visit_sample_index'] = fifth
        checks['five_destinations_independently_visited_in_order'] = fifth is not None
        checks['finish_line_crossed_after_ordered_visits'] = (
            crossing is not None and fifth is not None and crossing['previous_sample_index'] > fifth)
    else:
        checks['six_destinations_independently_visited_in_order'] = six_goals and len(visits) == 6

    paint = paint_evidence(samples, course)
    topology = topology_evidence(samples, course, open_area_lateral_m=open_area_lateral_m,
                                 finish_crossing=crossing_contract, crossing=crossing)
    report['paint_crossing'] = paint
    report['world_topology'] = topology
    checks['whole_footprint_paint_sweep_clear'] = paint['passed']
    checks['ordered_world_full_loop'] = topology['passed']
    qualified = identity['passed'] and checks['trajectory_continuous'] and checks['speed_at_most_2_2_mps']
    report['topology_certified'] = qualified and topology['passed']
    report['paint_crossing_certified'] = qualified and paint['passed']

    report.update(
        passed=all(checks.values()), observed_destination_visits=visits,
        footprint={'x_min': -1.1, 'x_max': .6, 'y_min': -.5, 'y_max': .5},
        obstacle_count=len(obstacles), minimum=minimum,
        conservative_swept_clearance_lower_bound_m=min_bound if math.isfinite(min_bound) else None,
        collision_pose_count=collision_samples, unproven_sweep_subsegments=uncertain_segments,
        evaluated_sweep_subsegments=subdivisions, observed_distance_m=travelled,
        maximum_interval_speed_mps=max_speed, speed_violation_indices=speed_violations,
        timestamp_gap_indices=gaps, nonincreasing_timestamp_indices=nonincreasing,
        final_distance_to_origin_m=final_distance,
        simulation_span_s=samples[-1][0]-samples[0][0])
    report['full_loop_certified'] = report['passed']
    aggregate_only = {'mission_identity_matches', 'sensor_health_latest_processing_passes',
                      'sensor_health_interval_verified'}
    report['geometric_full_loop_certified'] = all(
        value for key, value in checks.items() if key not in aggregate_only)
    report['certification_status'] = 'passed' if report['passed'] else (
        'failed' if identity['passed'] and mission_identity['passed'] and health['interval_verified']
        else 'uncertified')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', '--live', type=Path, required=True)
    parser.add_argument('--course', type=Path, required=True)
    parser.add_argument('--mission', type=Path, help='Defaults to autonomy.json beside course.json')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--open-area-lateral-m', type=float, default=8.,
                        help='Development scoring corridor allowance in unpainted areas (not a rule limit)')
    args = parser.parse_args()
    raw = args.run.read_bytes()
    mission_path = args.mission or args.course.with_name('autonomy.json')
    mission_raw = mission_path.read_bytes() if mission_path.exists() else None
    mission = json.loads(mission_raw) if mission_raw is not None else None
    course_raw = args.course.read_bytes()
    report = audit(json.loads(raw), json.loads(course_raw), mission,
                   course_sha256=hashlib.sha256(course_raw).hexdigest(),
                   mission_sha256=hashlib.sha256(mission_raw).hexdigest() if mission_raw is not None else None,
                   open_area_lateral_m=args.open_area_lateral_m)
    report['run_sha256'] = hashlib.sha256(raw).hexdigest()
    report['source_run'] = str(args.run)
    report['evaluation_course'] = str(args.course)
    report['evaluation_mission'] = str(mission_path) if mission_raw is not None else None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps({key: report.get(key) for key in (
        'passed', 'checks', 'minimum', 'maximum_interval_speed_mps',
        'final_distance_to_origin_m')}, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
