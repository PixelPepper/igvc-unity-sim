#!/usr/bin/env python3
"""Explain processing-health failures in a saved sensor-led run, read-only.

Reconstructs the failing interval from what run.json retains: the armed health
ledger, per-stream telemetry, status reason counts, mission decisions and the
odometry trajectory. Rolling event buffers are bounded, so the report states
which timing fields were not retained for the failure instead of guessing them.
Never changes thresholds or rejudges samples; audit acceptance is unaffected.
"""

import argparse
import json
from pathlib import Path
import sys

# Failure-type reasons the perception nodes publish (lane_node.py / depth_node.py).
# Anything else in status_reason_counts is a successful or benign status.
PAIRING_REASONS = {'no_new_exact_stamp_pair', 'no_new_pair', 'waiting_for_depth_ground_or_rgb_tf',
                   'acquisition_tf_not_ready'}
BENIGN_REASONS = {'valid', 'unknown', 'supported_ground_filter'}
NODE_TICK_S = 0.2           # create_timer(.2) in both perception nodes
SUCCESS_FRESH_SIM_S = 0.5   # success_is_fresh acquisition bound (500_000_000 ns)
SUCCESS_FRESH_WALL_S = 0.5  # success_is_fresh receipt bound


def _sim_wall_ratio(decisions, lo, hi):
    window = [d for d in decisions if lo <= d['odom_stamp_ns']/1e9 <= hi]
    if len(window) < 2 or window[-1]['monotonic_s'] <= window[0]['monotonic_s']:
        return None
    return ((window[-1]['odom_stamp_ns']-window[0]['odom_stamp_ns'])/1e9
            / (window[-1]['monotonic_s']-window[0]['monotonic_s']))


def classify_reasons(reason_counts):
    """Split each processing stream's status reasons into pairing waits, faults and benign."""
    result = {}
    for stream in ('lanes', 'depth_processing'):
        counts = reason_counts.get(stream, {})
        result[stream] = {
            'pairing_or_tf_wait': {k: v for k, v in counts.items() if k in PAIRING_REASONS},
            'processing_fault': {k: v for k, v in counts.items()
                                 if k not in PAIRING_REASONS and k not in BENIGN_REASONS},
            'benign': {k: v for k, v in counts.items() if k in BENIGN_REASONS},
        }
    return result


def diagnose(run, window_s=6.0):
    interval = run['mission_health_interval']
    first = interval.get('first_fail')
    health = run['sensor_health']
    report = {'passed': interval.get('passed'), 'totals': interval.get('totals'),
              'reason_counts': interval.get('reason_counts'), 'first_fail': first,
              'unavailable': []}
    if not first:
        report['finding'] = 'no failing health sample recorded'
        return report
    fail_sim = first['odom_stamp_ns']/1e9
    fail_mono = first['monotonic_s']

    # Bounded rings: say whether they still cover the failure.
    ledger_events = interval.get('recent_events') or []
    if not ledger_events or ledger_events[0]['monotonic_s'] > fail_mono:
        report['unavailable'].append(
            'per-sample health ledger at failure (ring of %d starts at odom %.2f s)'
            % (len(ledger_events), ledger_events[0]['odom_stamp_ns']/1e9 if ledger_events else float('nan')))
    status_events = health.get('recent_events') or []
    start_mono = interval['start']['monotonic_s']
    if not status_events or status_events[0]['elapsed_s'] > fail_mono-start_mono:
        report['unavailable'].append(
            'per-message perception status/health events at failure: node reason, pairing stamps, '
            'receipt age, TF wait, processing duration (status ring holds only the final events)')
    report['unavailable'] += [
        'per-frame image interarrival and acquisition lag at failure (only whole-run max and final-window percentiles)',
        'perception node CPU/scheduling and Unity frame time (not recorded by the run)',
        'WSLg/compositor restart time (not recorded by the run)']

    report['status_reasons'] = classify_reasons(health.get('status_reason_counts', {}))
    report['health_topic_false_counts'] = {
        name: health.get('status_reason_counts', {}).get(name, {}).get('False', 0)
        for name in ('lane_health', 'depth_health')}

    streams = health['streams']
    report['input_streams'] = {
        name: {'max_gap_wall_s': streams[name]['max_gap_s'],
               'interarrival_wall_s_final_window': streams[name]['recent_interarrival_wall_s'],
               'negative_lag_samples': streams[name]['negative_lag_samples']}
        for name in ('clock', 'rgb', 'depth') if name in streams}

    # Freshness margin: an idle tick keeps health only if the last success
    # acquisition is <= 0.5 s sim old. Lag at processing + one tick consumes it.
    checks = health.get('processing_health_summary', {}).get('checks', {})
    lags = {name: check.get('acquisition_lag_sim_s') for name, check in checks.items()}
    report['freshness_margin'] = {
        'bound_sim_s': SUCCESS_FRESH_SIM_S, 'bound_wall_s': SUCCESS_FRESH_WALL_S, 'tick_s': NODE_TICK_S,
        'final_output_acquisition_lag_sim_s': lags,
        'margin_after_one_idle_tick_sim_s': {
            name: None if lag is None else round(SUCCESS_FRESH_SIM_S-lag-NODE_TICK_S, 3)
            for name, lag in lags.items()},
        'note': 'lag measured at mission receipt in the final window only; at-failure lag unavailable'}

    trajectory_times = [point[0] for point in run.get('trajectory', [])]
    near = [(b-a, a) for a, b in zip(trajectory_times, trajectory_times[1:])
            if fail_sim-window_s <= a <= fail_sim+window_s]
    report['odometry'] = {
        'max_gap_sim_s_near_failure': round(max((g for g, _ in near), default=0.0), 4),
        'max_gap_sim_s_whole_run': round(max((b-a for a, b in zip(trajectory_times, trajectory_times[1:])),
                                             default=0.0), 4)}

    decisions = run.get('decisions', [])
    report['sim_wall_ratio'] = {
        'near_failure': _sim_wall_ratio(decisions, fail_sim-window_s, fail_sim+window_s),
        'whole_run': _sim_wall_ratio(decisions, float('-inf'), float('inf'))}
    report['decision_inputs_near_failure'] = [
        {'sequence': d['sequence'], 'dt_from_fail_wall_s': round(d['monotonic_s']-fail_mono, 3),
         'odom_s': d['odom_stamp_ns']/1e9,
         'lane_age_wall_s': d['input_metadata'].get('lane_age_wall_s'),
         'grid_age_wall_s': d['input_metadata'].get('grid_age_wall_s')}
        for d in decisions if d['phase'] == 'requested' and d.get('input_metadata')
        and abs(d['monotonic_s']-fail_mono) <= window_s]

    faults = sum(sum(v['processing_fault'].values()) for v in report['status_reasons'].values())
    waits = sum(sum(v['pairing_or_tf_wait'].values()) for v in report['status_reasons'].values())
    report['finding'] = (
        'pairing/freshness wait, no processing fault recorded' if waits and not faults else
        'processing fault reasons recorded; inspect processing_fault' if faults else
        'no failure reason retained; cause undetermined')
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
        if args.output.exists():
            print(f'refusing to overwrite {args.output}', file=sys.stderr)
            return 1
        args.output.write_text(text + '\n', encoding='utf-8')
    else:
        print(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
