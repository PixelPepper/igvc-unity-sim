#!/usr/bin/env python3
"""Compare load-sensitive measurements across parallel instance counts (read-only).

Robot outcomes are too noisy to compare from a few trials, so calibration uses
signals with hundreds of samples per trial: processing-health fail rate, planner
search wall time per decision, lane/depth/RGB message interarrival, Unity RGB
readback time and frame time. Pass one merged batch-report.json per instance count.
"""
import argparse
import json
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def percentile(values, q):
    values = sorted(values)
    return values[min(len(values) - 1, int(q * len(values)))] if values else None


def run_metrics(run_dir):
    run = json.loads((run_dir / 'run.json').read_text())
    totals = (run.get('mission_health_interval') or {}).get('totals') or {}
    streams = (run.get('sensor_health') or {}).get('streams') or {}
    search = []
    outcomes = run_dir / 'decisions/outcomes.jsonl'
    if outcomes.exists():
        for line in outcomes.read_text().splitlines():
            value = json.loads(line).get('search_wall_s')
            if isinstance(value, (int, float)):
                search.append(value)
    readback = re.search(r'meanReadbackMs=([0-9.]+)', run.get('sim_status') or '')
    return dict(health_pass=totals.get('pass', 0), health_fail=totals.get('fail', 0), search=search,
                lane_p95=((streams.get('lane_health') or {}).get('recent_interarrival_wall_s') or {}).get('p95'),
                depth_p95=((streams.get('depth_health') or {}).get('recent_interarrival_wall_s') or {}).get('p95'),
                rgb_p95=((streams.get('rgb') or {}).get('recent_interarrival_wall_s') or {}).get('p95'),
                readback_ms=float(readback.group(1)) if readback else None)


def summarise(report_path):
    report = json.loads(report_path.read_text())
    rows = [r for r in report['rows'] if r.get('run')]
    metrics, frames, frames_p99 = [], [], []
    for r in rows:
        sandbox = ROOT / ('artifacts/sandbox-instance-%d' % r['instance'] if r.get('instance') else 'artifacts/sandbox')
        run_dir = sandbox / 'runs' / r['run']
        if (run_dir / 'run.json').exists():
            metrics.append(run_metrics(run_dir)); frames.append(r['frame_ms_mean']); frames_p99.append(r['frame_ms_p99'])
    mean = lambda xs: statistics.fmean([x for x in xs if x is not None]) if any(x is not None for x in xs) else None
    search = [s for m in metrics for s in m['search']]
    samples = sum(m['health_pass'] + m['health_fail'] for m in metrics)
    return dict(instances=report.get('instances', 1), trials=len(metrics),
                six_of_six=sum(r['completed'] == 6 for r in rows),
                health_fail_rate=(sum(m['health_fail'] for m in metrics) / samples) if samples else None,
                health_samples=samples, decisions=len(search),
                search_p50_s=percentile(search, .5), search_p95_s=percentile(search, .95),
                lane_interarrival_p95_s=mean([m['lane_p95'] for m in metrics]),
                depth_interarrival_p95_s=mean([m['depth_p95'] for m in metrics]),
                rgb_interarrival_p95_s=mean([m['rgb_p95'] for m in metrics]),
                rgb_readback_ms=mean([m['readback_ms'] for m in metrics]),
                frame_ms=mean(frames), frame_p99_ms=mean(frames_p99))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reports', type=Path, nargs='+')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    table = [summarise(p) for p in args.reports]
    keys = ['instances', 'trials', 'six_of_six', 'health_fail_rate', 'decisions', 'search_p50_s', 'search_p95_s',
            'lane_interarrival_p95_s', 'depth_interarrival_p95_s', 'rgb_interarrival_p95_s', 'rgb_readback_ms', 'frame_ms', 'frame_p99_ms']
    print(' '.join(f'{k:>12.12s}' for k in keys))
    for row in table:
        print(' '.join(f'{row[k]:12.4g}' if isinstance(row[k], float) else f'{str(row[k]):>12s}' for k in keys))
    if args.output:
        args.output.write_text(json.dumps(table, indent=2))


if __name__ == '__main__':
    main()
