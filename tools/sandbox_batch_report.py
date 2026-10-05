#!/usr/bin/env python3
"""Audit every run of a sandbox batch and summarise it by arm (read-only on run evidence)."""
import argparse
import json
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def audit(run_dir):
    output = run_dir / 'batch-audit.json'
    if not output.exists():
        subprocess.run([sys.executable, str(ROOT / 'tools/audit_sensor_run.py'), '--run', str(run_dir / 'run.json'),
                        '--course', str(run_dir / 'course.json'), '--mission', str(run_dir / 'autonomy.json'),
                        '--output', str(output)], check=False, stdout=subprocess.DEVNULL)
    return json.loads(output.read_text()) if output.exists() else None


def row(trial, sandbox):
    out = dict(index=trial['index'], arm=trial['arm'], seed=trial.get('seed', 0), difficulty=trial.get('difficulty', 'session'),
               speed_mps=trial.get('speed_mps'), controller=trial.get('controller'), escape=trial.get('escape') or 'legacy',
               route_weight=trial.get('route_weight', 0.), corridor_weight=trial.get('corridor_weight', 0.),
               run=trial.get('run'), state=trial['state'],
               completed=trial['completed_destinations'], infrastructure_retry=bool(trial.get('infrastructure_retry')),
               frame_ms_mean=trial['frame_ms_mean'],
               frame_ms_p99=trial['frame_ms_p99'], frame_ms_max=trial['frame_ms_max'], ghost_laps=trial['ghost_laps'])
    if not trial.get('run'):
        return out
    run_dir = sandbox / 'runs' / trial['run']
    run = json.loads((run_dir / 'run.json').read_text()) if (run_dir / 'run.json').exists() else {}
    health = run.get('mission_health_interval') or {}
    totals = health.get('totals') or {}
    report = audit(run_dir) or {}
    out.update(status=run.get('status'), reason=run.get('reason'), elapsed_wall_s=run.get('elapsed_wall_s'),
               backups=len(run.get('recoveries', [])), health_pass=totals.get('pass'), health_fail=totals.get('fail'),
               health_unknown=totals.get('unknown'), health_passed=health.get('passed'),
               audit_passed=report.get('passed'), min_clearance_m=(report.get('minimum') or {}).get('clearance_m'),
               sim_span_s=report.get('simulation_span_s'), return_m=report.get('final_distance_to_origin_m'))
    # Outside load (other programs, throttling) shows up as slower Unity frames; perception-freshness latches
    # follow it. Flag both so success rates can be read on undisturbed trials.
    out.update(disturbed=(out['frame_ms_mean'] or 0) > DISTURBED_FRAME_MS,
               perception_latch=(run.get('reason') or '').startswith('Autonomy gate stopped'))
    return out


DISTURBED_FRAME_MS = 18.5  # undisturbed trials average 16.7 ms


def policy(r):
    return f"route {r.get('route_weight', 0.):g} corridor {r.get('corridor_weight', 0.):g} escape {r.get('escape', 'legacy')}"


def summary(rows, key=lambda r: r['arm']):
    by_arm = {}
    # Repeated infrastructure failures are listed in rows but are not navigation evidence.
    for r in rows:
        if not r.get('infrastructure_retry'):
            by_arm.setdefault(key(r), []).append(r)
    result = {}
    for arm, items in by_arm.items():
        mean = lambda k: statistics.fmean([r[k] for r in items if isinstance(r.get(k), (int, float))] or [float('nan')])
        result[arm] = dict(trials=len(items), six_of_six=sum(r['completed'] == 6 for r in items),
                           audit_passed=sum(bool(r.get('audit_passed')) for r in items),
                           health_fail_samples=sum(r.get('health_fail') or 0 for r in items),
                           health_samples=sum((r.get('health_pass') or 0) + (r.get('health_fail') or 0) for r in items),
                           disturbed=sum(bool(r.get('disturbed')) for r in items),
                           perception_latches=sum(bool(r.get('perception_latch')) for r in items),
                           clean_trials=sum(not r.get('disturbed') and not r.get('perception_latch') for r in items),
                           clean_six_of_six=sum(r['completed'] == 6 and not r.get('disturbed') and not r.get('perception_latch') for r in items),
                           mean_elapsed_wall_s=mean('elapsed_wall_s'), mean_backups=mean('backups'),
                           mean_frame_ms=mean('frame_ms_mean'), mean_frame_p99_ms=mean('frame_ms_p99'))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('batch_results', type=Path)
    parser.add_argument('--sandbox', type=Path, default=ROOT / 'artifacts/sandbox')
    args = parser.parse_args()
    batch = json.loads(args.batch_results.read_text())
    rows = [row(t, args.sandbox) for t in batch['trials']]
    report = dict(schema_version=1, batch=str(args.batch_results), state=batch.get('state'), rows=rows, summary=summary(rows),
                  by_layout=summary(rows, lambda r: f"{r['arm']} seed {r['seed']} {r['difficulty']}"),
                  by_escape=summary(rows, lambda r: r['escape']),
                  by_policy=summary(rows, policy))
    out = args.batch_results.with_name('batch-report.json')
    out.write_text(json.dumps(report, indent=2))
    for r in rows:
        print(f"{r['index']:2d} {r['arm']:15s} {r['seed']}-{r['difficulty']:7s} {r['escape']:7s} {r['completed']}/6 audit={r.get('audit_passed')} health fail={r.get('health_fail')}"
              f" wall={r.get('elapsed_wall_s') or 0:.0f}s backups={r.get('backups')} frame={r['frame_ms_mean']:.1f}/{r['frame_ms_p99']:.1f}ms"
              f" ghosts={r['ghost_laps']} {r.get('reason') or ''}")
    print(json.dumps(report['summary'], indent=2))
    print('wrote', out)


if __name__ == '__main__':
    main()
