#!/usr/bin/env python3
"""Report what a saved run can and cannot say about its processing-health failures.

Read-only. Uses only what run.json retains: the armed health ledger, per-stream
telemetry, whole-run status reason counts, mission decisions and the odometry
trajectory. Rolling event buffers are bounded; when they no longer cover the
first failure, its cause is reported as undetermined and the missing timing
fields are listed. Whole-run counts are descriptive and are never matched to
failing samples. Never changes thresholds, samples or audit results.
"""

import argparse
import json
from pathlib import Path
import sys

UNDETERMINED = 'undetermined: per-failure telemetry does not cover the first failure'
# Constants restated from lane_node.py / depth_node.py for the illustration only.
NODE_TICK_WALL_S = 0.2       # steady-clock create_timer(.2)
SUCCESS_FRESH_SIM_S = 0.5    # acquisition bound, simulation clock
SUCCESS_FRESH_WALL_S = 0.5   # receipt bound, wall (monotonic) clock
# Monotonic time at telemetry initialization, if a future schema records it
# (sensor_telemetry.py keeps `started` internally; schema v1 does not export it).
TELEMETRY_ORIGIN_KEY = 'started_monotonic_s'


def get(value, *path):
    """Nested lookup that returns None instead of raising on absent or mistyped fields."""
    for key in path:
        if isinstance(value, dict):
            value = value.get(key)
        elif isinstance(value, list) and isinstance(key, int) and -len(value) <= key < len(value):
            value = value[key]
        else:
            return None
    return value


def _number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _sim_wall_ratio(decisions, lo, hi):
    window = [d for d in decisions
              if _number(get(d, 'odom_stamp_ns')) is not None and _number(get(d, 'monotonic_s')) is not None
              and lo <= d['odom_stamp_ns']/1e9 <= hi]
    if len(window) < 2 or window[-1]['monotonic_s'] <= window[0]['monotonic_s']:
        return None
    return ((window[-1]['odom_stamp_ns']-window[0]['odom_stamp_ns'])/1e9
            / (window[-1]['monotonic_s']-window[0]['monotonic_s']))


def diagnose(run, window_s=6.0):
    unavailable = []
    interval = get(run, 'mission_health_interval')
    health = get(run, 'sensor_health')
    report = {'passed': get(interval, 'passed'), 'totals': get(interval, 'totals'),
              'health_sample_reason_counts': get(interval, 'reason_counts'),
              'first_fail': get(interval, 'first_fail'), 'unavailable': unavailable}
    if not isinstance(interval, dict):
        unavailable.append('mission_health_interval (armed health ledger)')
    if not isinstance(health, dict):
        unavailable.append('sensor_health (stream telemetry and status reasons)')

    first = report['first_fail']
    fail_mono = _number(get(first, 'monotonic_s'))
    fail_ns = _number(get(first, 'odom_stamp_ns'))
    fail_count = _number(get(interval, 'totals', 'fail'))
    if not first:
        if not isinstance(interval, dict):
            report['first_failure_cause'] = 'undetermined: health ledger unavailable'
        elif fail_count is None:
            report['first_failure_cause'] = 'undetermined: first_fail missing and failing-sample count unavailable'
        elif fail_count > 0:
            report['first_failure_cause'] = ('contradiction: totals report %d failing samples but first_fail '
                                             'is missing' % fail_count)
        else:
            report['first_failure_cause'] = 'no failing health sample recorded'
    elif fail_mono is None or fail_ns is None:
        unavailable.append('first_fail monotonic_s/odom_stamp_ns')
        report['first_failure_cause'] = UNDETERMINED

    # Bounded rings, judged independently. The ledger shares the failure's
    # monotonic clock. Status events use elapsed_s from telemetry
    # initialization; schema v1 does not export that origin, and the mission
    # arm time is a different event, so status alignment is unknown unless a
    # recorded origin exists.
    coverage = {'health_ledger': 'unavailable', 'status_events': 'unavailable'}
    if fail_mono is not None:
        ledger_start = _number(get(interval, 'recent_events', 0, 'monotonic_s'))
        if ledger_start is not None:
            coverage['health_ledger'] = 'covers_failure' if ledger_start <= fail_mono else 'evicted_before_failure'
        if coverage['health_ledger'] != 'covers_failure':
            unavailable.append('per-sample health ledger at first failure (ring starts at monotonic %s s)'
                               % ledger_start)
        status_start = _number(get(health, 'recent_events', 0, 'elapsed_s'))
        origin = _number(get(health, TELEMETRY_ORIGIN_KEY))
        if status_start is not None:
            coverage['status_events'] = ('alignment_unknown' if origin is None else
                                         'covers_failure' if origin+status_start <= fail_mono
                                         else 'evicted_before_failure')
        if coverage['status_events'] != 'covers_failure':
            unavailable.append('per-message perception status events at first failure: node reason, pairing '
                               'stamps, receipt age, TF wait, processing duration (%s)' % coverage['status_events'])
        report['first_failure_cause'] = (
            'per-failure status events retained; inspect sensor_health.recent_events'
            if coverage['status_events'] == 'covers_failure' else UNDETERMINED)
    report['retained_event_coverage'] = coverage
    unavailable += ['per-frame image interarrival and acquisition lag at first failure',
                    'node-side processing duration and scheduling; Unity frame time',
                    'WSLg/compositor restart time']

    reasons = get(health, 'status_reason_counts')
    report['whole_run_status_reason_counts'] = {
        'descriptive_only': 'whole-session status-message counts; not tied to or reconciled with failing samples',
        'counts': ({name: reasons.get(name) for name in ('lanes', 'depth_processing', 'lane_health', 'depth_health')}
                   if isinstance(reasons, dict) else None)}
    if not isinstance(reasons, dict):
        unavailable.append('status_reason_counts')

    streams = get(health, 'streams')
    report['input_streams_whole_run'] = {}
    for name in ('clock', 'rgb', 'depth'):
        stream = get(streams, name)
        if not isinstance(stream, dict):
            unavailable.append(f'stream telemetry: {name}')
            continue
        report['input_streams_whole_run'][name] = {
            'max_gap_wall_s_unlocalized': stream.get('max_gap_s'),
            'interarrival_wall_s_final_window': stream.get('recent_interarrival_wall_s'),
            'negative_lag_samples': stream.get('negative_lag_samples')}

    lags = {name: get(health, 'processing_health_summary', 'checks', name, 'acquisition_lag_sim_s')
            for name in ('lanes', 'depth_processing')}
    report['freshness_illustration'] = {
        'illustrative_only': 'not an observed margin at the failure',
        'success_bound': {'acquisition_sim_s': SUCCESS_FRESH_SIM_S, 'receipt_wall_s': SUCCESS_FRESH_WALL_S},
        'node_tick_wall_s': NODE_TICK_WALL_S,
        'final_window_subscriber_lag_sim_s': lags,
        'assumptions': ['lag is measured at the mission subscriber in the final window, not node-side or at failure',
                        'a wall-clock tick spans about tick * sim/wall-ratio simulation seconds']}

    trajectory = get(run, 'trajectory')
    times = [p[0] for p in trajectory if isinstance(p, list) and p and _number(p[0]) is not None] \
        if isinstance(trajectory, list) else []
    if len(times) < 2:
        unavailable.append('odometry trajectory')
        report['odometry_sim_stamps'] = None
    else:
        gaps = list(zip(times, times[1:]))
        near = [b-a for a, b in gaps if fail_ns is not None and abs(a-fail_ns/1e9) <= window_s]
        report['odometry_sim_stamps'] = {
            'max_gap_sim_s_near_failure': round(max(near), 4) if near else None,
            'max_gap_sim_s_whole_run': round(max(b-a for a, b in gaps), 4),
            'scope': 'simulation-stamp continuity only; cannot exclude short wall-time scheduling or transport stalls'}

    decisions = get(run, 'decisions')
    decisions = [d for d in decisions if isinstance(d, dict)] if isinstance(decisions, list) else []
    if not decisions:
        unavailable.append('mission decisions')
    report['sim_wall_ratio'] = {
        'near_failure': None if fail_ns is None else _sim_wall_ratio(decisions, fail_ns/1e9-window_s,
                                                                     fail_ns/1e9+window_s),
        'whole_run': _sim_wall_ratio(decisions, float('-inf'), float('inf'))}
    report['decision_inputs_near_failure'] = [] if fail_mono is None else [
        {'sequence': d.get('sequence'), 'dt_from_fail_wall_s': round(d['monotonic_s']-fail_mono, 3),
         'odom_s': d['odom_stamp_ns']/1e9 if _number(d.get('odom_stamp_ns')) is not None else None,
         'lane_age_wall_s': get(d, 'input_metadata', 'lane_age_wall_s'),
         'grid_age_wall_s': get(d, 'input_metadata', 'grid_age_wall_s')}
        for d in decisions if d.get('phase') == 'requested' and _number(d.get('monotonic_s')) is not None
        and abs(d['monotonic_s']-fail_mono) <= window_s]
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path, help='saved run.json (read-only)')
    parser.add_argument('--output', type=Path, help='write JSON report here (must not exist)')
    parser.add_argument('--window-s', type=float, default=6.0)
    args = parser.parse_args(argv)
    report = diagnose(json.loads(args.run.read_text(encoding='utf-8')), args.window_s)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        try:
            with args.output.open('x', encoding='utf-8') as handle:  # atomic no-overwrite
                handle.write(text + '\n')
        except FileExistsError:
            print(f'refusing to overwrite {args.output}', file=sys.stderr)
            return 1
    else:
        print(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
