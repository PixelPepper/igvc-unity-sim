"""Offline sensor-run scorer. Course geometry is evaluation-only, never control input."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

from generate_course_variant import BODY_RADIUS, body_clearance
from gps_mission import LocalFrame


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


def audit(run, course, mission=None):
    """Check sampled motion and conservative sweeps under linear pose interpolation.

    This deliberately does not use guide_route_xy, guided checkpoints, or route
    hashes. Six broad destinations do not establish course topology or a full loop.
    """
    samples = run.get('trajectory', [])
    valid = (len(samples) >= 2 and all(len(p) == 4 and
             all(isinstance(v, (int, float)) and math.isfinite(v) for v in p)
             for p in samples))
    checks = {
        'completed_six_destinations': run.get('status') == 'completed'
            and run.get('completed_destinations') == 6 and run.get('total_destinations') == 6,
        'sensor_led_mode': run.get('mode') == 'sensor-led',
        'scoring_guard': bool(re.search(r'(?:^|\s)line_guard=scoring(?:\s|$)', run.get('sim_status', ''))),
        'zero_line_blocks': bool(re.search(r'(?:^|\s)line_blocks=0(?:\s|$)', run.get('sim_status', ''))),
        'finite_trajectory': valid,
    }
    report = {'passed': False, 'source_status': run.get('status'),
              'completed_destinations': run.get('completed_destinations'),
              'checks': checks, 'sample_count': len(samples),
              'topology_certified': False, 'full_loop_certified': False,
              'limitations': 'Offline ideal geometry evidence, not contact physics. Swept bounds assume '
                  'linear translation and shortest-angle rotation between recorded poses. Gaps fail '
                  'continuity. Paint crossing and full-loop topology are not independently certified; '
                  'line_blocks is only a simulator status assertion. Course/run pairing is caller supplied.'}
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
    checks['returned_within_0_4_m'] = final_distance <= .4
    ramp_evidence = [ramp_traversal(samples, ramp) for ramp in course.get('ramps', [])]
    checks['all_ramps_traversed_entry_to_exit'] = bool(ramp_evidence) and all(
        evidence['passed'] for evidence in ramp_evidence)
    report['ramp_traversals'] = ramp_evidence
    report['limitations'] += (' Ramp evidence follows the driven axle centre inside the side edges '
                              'from local longitudinal 0 to full ramp length; it does not certify '
                              'asymmetric body containment, wheel contact, elevation or suspension.')

    visits = []
    if mission is not None:
        frame = LocalFrame(mission['origin'])
        cursor = 0
        for goal in mission.get('goals', []):
            x, y, _ = frame.to_enu(goal['latitude'], goal['longitude'], goal['altitude'])
            while cursor < len(samples) and math.hypot(samples[cursor][1]-x, samples[cursor][2]-y) > goal['radius_m']:
                cursor += 1
            if cursor == len(samples):
                break
            visits.append({'destination_index': len(visits), 'sample_index': cursor,
                           'stamp': samples[cursor][0]})
    checks['six_destinations_independently_visited_in_order'] = (
        mission is not None and len(mission.get('goals', [])) == 6 and len(visits) == 6)
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
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', '--live', type=Path, required=True)
    parser.add_argument('--course', type=Path, required=True)
    parser.add_argument('--mission', type=Path, help='Defaults to autonomy.json beside course.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw = args.run.read_bytes()
    mission_path = args.mission or args.course.with_name('autonomy.json')
    mission = json.loads(mission_path.read_text()) if mission_path.exists() else None
    report = audit(json.loads(raw), json.loads(args.course.read_text()), mission)
    report['run_sha256'] = hashlib.sha256(raw).hexdigest()
    report['source_run'] = str(args.run)
    report['evaluation_course'] = str(args.course)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps({key: report.get(key) for key in (
        'passed', 'checks', 'minimum', 'maximum_interval_speed_mps',
        'final_distance_to_origin_m')}, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
