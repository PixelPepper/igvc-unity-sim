#!/usr/bin/env python3
"""Read-only IGVC profile compatibility report; never certifies a physical robot."""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / 'config/competition/igvc-2027-autonav.json'


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def aggregate(checks):
    states = {check['status'] for check in checks}
    return 'fail' if 'fail' in states else 'unknown' if 'unknown' in states else 'pass'


def validate(course, autonomy, run=None, profile=None, settings=None):
    """Compare declared fixture evidence. Missing/ambiguous evidence stays unknown."""
    if profile is None:
        profile = json.loads(DEFAULT_PROFILE.read_text(encoding='utf-8-sig'))
    if (not isinstance(profile, dict) or profile.get('schema_version') != 1
            or profile.get('profile_id') != 'igvc-2027-autonav-v1'):
        raise ValueError('Unsupported competition profile')
    if not isinstance(course, dict) or not isinstance(autonomy, dict):
        raise ValueError('Course and autonomy must be JSON objects')
    if run is not None and not isinstance(run, dict):
        raise ValueError('Run must be a JSON object')
    if settings is None:
        settings = {}
    if not isinstance(settings, dict):
        raise ValueError('Settings receipt must be a JSON object')
    req = profile['requirements']
    ft = profile['conversions']['metres_per_foot']
    mph = profile['conversions']['mps_per_mph']
    cap = req['maximum_speed_mph'] * mph
    checks = []

    def add(name, status, detail, observed=None, expected=None, scope='configuration'):
        checks.append(dict(id=name, status=status, scope=scope, detail=detail,
                           observed=observed, expected=expected))

    allowed = {'schema_version', 'origin', 'goals', 'max_speed_mps'}
    add('sanitized_autonomy_keys', 'pass' if set(autonomy) == allowed else 'fail',
        'Runtime accepts exactly four top-level keys; profile metadata belongs in a separate settings receipt.',
        sorted(autonomy), sorted(allowed))

    units = course.get('units') == 'm'
    add('course_units', 'pass' if units else 'unknown',
        'Legacy course dimensions require an explicit metres declaration.', course.get('units'), 'm')
    speed = autonomy.get('max_speed_mps')
    add('configured_speed_cap', 'unknown' if speed is None else
        'pass' if number(speed) and 0 < speed <= cap else 'fail',
        'Declared software cap only; hardware governor remains unverified.', speed, cap)
    comp = settings
    timeout = comp.get('timeout_wall_s')
    add('configured_run_timeout', 'unknown' if timeout is None else
        'pass' if number(timeout) and 0 < timeout <= req['run_time_limit_s'] else 'fail',
        'Checks the declared overall run budget, not an individual goal timeout.', timeout, req['run_time_limit_s'])
    requested = comp.get('requested_speed_mps')
    add('requested_speed_cap', 'unknown' if requested is None else
        'pass' if number(requested) and 0 < requested <= cap else 'fail',
        'Requested runtime ceiling; this is not a measured qualification speed.', requested, cap)
    goals = autonomy.get('goals')
    count = len(goals) if isinstance(goals, list) else None
    expected_count = 2 * req['provided_waypoint_pairs']
    add('organizer_waypoint_count', 'unknown' if count is None else
        'pass' if count == expected_count else 'fail',
        'Two supplied waypoint pairs correspond to four destinations; count alone does not prove provenance.', count, expected_count)
    pairs = comp.get('waypoint_pairs')
    valid_pairs = (isinstance(pairs, list) and len(pairs) == req['provided_waypoint_pairs']
                   and all(isinstance(p, list) and len(p) == 2 for p in pairs)
                   and all(type(i) is int for p in pairs for i in p)
                   and sorted(i for p in pairs for i in p) == list(range(expected_count)))
    add('organizer_waypoint_pairing', 'unknown' if pairs is None else
        'pass' if valid_pairs else 'fail', 'Pairs index the four goals exactly once.', pairs, [[0, 1], [2, 3]])
    guidance = comp.get('guidance')
    add('organizer_waypoint_guidance', 'unknown' if guidance is None else
        'pass' if guidance == 'organizer_waypoints' else 'fail',
        'A declared source of organizer waypoints is required; six sampled training regions are different guidance.', guidance, 'organizer_waypoints')
    ramps = course.get('ramps')
    if not isinstance(ramps, list):
        add('ramp_grade', 'unknown', 'Ramp list not supplied.')
    for index, ramp in enumerate(ramps or []):
        if not isinstance(ramp, dict):
            raise ValueError('Each ramp must be an object')
        height, length = ramp.get('height'), ramp.get('rise_length')
        grade = height / length if number(height) and number(length) and height >= 0 and length > 0 else None
        add(f'ramp_grade_{index}', 'unknown' if not units or grade is None else
            'pass' if grade <= req['maximum_ramp_grade_ratio'] + 1e-12 else 'fail',
            'Grade is rise/horizontal run; 15 percent is about 8.53 degrees, not 15 degrees.',
            grade, req['maximum_ramp_grade_ratio'])
    obstacles = course.get('obstacles')
    if not isinstance(obstacles, list):
        add('simulated_potholes', 'unknown', 'Obstacle list not supplied.')
    for index, hole in enumerate(obstacles or []):
        if not isinstance(hole, dict):
            raise ValueError('Each obstacle must be an object')
        if hole.get('kind') != 'pothole':
            continue
        width, length = hole.get('width'), hole.get('length')
        diameter = req['simulated_pothole']['diameter_ft'] * ft
        dimensions_ok = (number(width) and number(length) and
                         math.isclose(width, diameter, abs_tol=1e-6) and
                         math.isclose(length, diameter, abs_tol=1e-6))
        add(f'pothole_diameter_{index}', 'unknown' if not units else
            'pass' if dimensions_ok else 'fail', 'Rule simulated potholes have two-foot diameter.',
            [width, length], diameter)
        representation = hole.get('representation')
        depth = hole.get('depth')
        color = hole.get('color')
        physical = number(depth) and depth > 0
        dark = color is not None and color not in ('white', '#ffffff', '#FFFFFF')
        declared = representation == req['simulated_pothole']['representation']
        invalid_depth = depth is not None and (not number(depth) or depth < 0)
        add(f'pothole_representation_{index}', 'fail' if invalid_depth or physical or dark or
            representation is not None and not declared else 'pass' if declared else 'unknown',
            'Dark physical depressions are training hazards; rule potholes are solid white circles.',
            dict(representation=representation, color=color, depth=depth), req['simulated_pothole']['representation'])
    passages = course.get('passage_widths_m')
    add('minimum_passage', 'unknown' if passages is None else
        'pass' if isinstance(passages, list) and passages and all(number(v) and v >= req['minimum_passage_width_ft'] * ft for v in passages) else 'fail',
        'Requires declared obstacle-edge to boundary-edge clear openings; lane width alone is insufficient.',
        passages, req['minimum_passage_width_ft'] * ft)
    add('opening_speed_window', 'unknown', 'Rulebook narrative and traffic table disagree; organizer clarification required.',
        profile['opening_speed_conflict'], scope='judges')
    if run is not None:
        for field, limit in (('timeout_wall_s', req['run_time_limit_s']), ('requested_speed_mps', cap)):
            value = run.get(field)
            add('run_setting_' + field, 'unknown' if value is None else
                'pass' if number(value) and 0 < value <= limit else 'fail',
                'Runtime setting ceiling, not physical behavior or qualification evidence.', value, limit, scope='run')
        elapsed = run.get('elapsed_wall_s')
        add('run_elapsed', 'unknown' if elapsed is None else 'pass' if number(elapsed) and
            0 <= elapsed <= req['run_time_limit_s'] else 'fail',
            'Recorded wall seconds only; correspondence with judge-start/stop remains unverified.', elapsed,
            req['run_time_limit_s'], scope='run')
        trajectory = run.get('trajectory')
        valid = (isinstance(trajectory, list) and len(trajectory) >= 2 and
                 all(isinstance(p, list) and len(p) >= 3 and all(number(v) for v in p[:3]) for p in trajectory))
        if valid:
            intervals = [(b[0] - a[0], math.hypot(b[1] - a[1], b[2] - a[2])) for a, b in zip(trajectory, trajectory[1:])]
            valid = all(dt > 0 for dt, distance in intervals)
        if valid:
            speeds = [distance / dt for dt, distance in intervals]
            maximum = max(speeds)
            average = sum(distance for dt, distance in intervals) / sum(dt for dt, distance in intervals)
            add('sampled_run_speed', 'fail' if maximum > cap + 1e-9 else 'unknown',
                'A chord-speed violation disproves the cap; samples below it cannot bound speed between samples.',
                maximum, cap, scope='run')
            add('sampled_average_speed', 'unknown',
                'Sampled chord average is diagnostic; it is not judge-measured course distance or full-run timing.',
                average, req['average_speed_mph_exclusive_minimum'] * mph, scope='run')
        else:
            add('sampled_run_speed', 'unknown', 'Need finite [time_s, x_m, y_m, ...] samples with strictly increasing timestamps.', scope='run')
    for index, requirement in enumerate(profile['unknown_requirements']):
        add(f'external_requirement_{index}', 'unknown', requirement, scope='hardware_or_judges')
    return dict(schema_version=1, profile_id=profile['profile_id'], provenance=profile['provenance'],
                status=aggregate(checks), configuration_status=aggregate([c for c in checks if c['scope'] == 'configuration']),
                certification=False, checks=checks,
                limits='Declared fixture settings and sampled observations only; pass never certifies competition compliance.')


def load(path):
    raw = path.read_bytes()
    def reject_constant(value):
        raise ValueError('Non-finite JSON number: ' + value)
    value = json.loads(raw.decode('utf-8-sig'), parse_constant=reject_constant)
    pending = [value]
    while pending:
        item = pending.pop()
        if type(item) is float and not math.isfinite(item):
            raise ValueError('Non-finite JSON number')
        if isinstance(item, dict):
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    return value, hashlib.sha256(raw).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--course', type=Path, required=True)
    parser.add_argument('--autonomy', type=Path, required=True)
    parser.add_argument('--run', type=Path)
    parser.add_argument('--settings', type=Path, help='Separate optional runtime/provenance receipt; never loaded by autonomy')
    parser.add_argument('--profile', type=Path, default=DEFAULT_PROFILE)
    args = parser.parse_args(argv)
    try:
        inputs = {name: load(path) for name, path in vars(args).items() if path is not None}
        report = validate(inputs['course'][0], inputs['autonomy'][0],
                          inputs.get('run', (None,))[0], inputs['profile'][0], inputs.get('settings', ({},))[0])
        if args.run and 'course_sha256' in inputs['run'][0]:
            matching = inputs['run'][0]['course_sha256'] == inputs['course'][1]
            report['checks'].append(dict(id='run_course_binding', status='pass' if matching else 'fail', scope='run',
                                         detail='Run course digest compared to the exact input file bytes.',
                                         observed=inputs['run'][0]['course_sha256'], expected=inputs['course'][1]))
            report['status'] = aggregate(report['checks'])
        report['inputs'] = {name: dict(path=str(getattr(args, name).resolve()), sha256=values[1]) for name, values in inputs.items()}
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps(dict(schema_version=1, status='fail', error=str(exc), certification=False)))
        return 1
    print(json.dumps(report, indent=2, allow_nan=False))
    return {'pass': 0, 'fail': 1, 'unknown': 2}[report['status']]


if __name__ == '__main__':
    raise SystemExit(main())
