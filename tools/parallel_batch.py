#!/usr/bin/env python3
"""Run one sandbox batch plan across N isolated simulator instances (run from WSL).

Shared resources are prepared once and sequentially (overlay check, course generation);
each instance then runs its round-robin share of the trials via
`tools/sandbox.ps1 -Instance n -Hidden -Batch <sub-plan>` with its own TCP port, ROS
domain, session folder and lease. Per-instance reports are merged into one
batch-report.json beside the plan, with the instance recorded on every row.

Wall-clock perception/planning budgets make CPU contention change robot behaviour, so
use the instance count established by calibration (docs/LEARNING_PLAN.md).
"""
import argparse
import json
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def windows(path):
    return subprocess.run(['wslpath', '-w', str(path)], capture_output=True, text=True, check=True).stdout.strip()


def ros(*argv):
    subprocess.run(['bash', str(ROOT / 'tools/run_ros.sh'), *argv], check=True, stdout=subprocess.DEVNULL)


def layouts(trials):
    return sorted({(t['seed'], t.get('difficulty') or 'normal') for t in trials if t.get('seed')})


def prepare(plan, folder, instances):
    """Verify the overlay and generate every layout once, before any instance starts."""
    workspace = Path.home() / 'igvc_ws'
    if subprocess.run(['bash', str(ROOT / 'tools/run_ros.sh'), 'python3', str(ROOT / 'tools/agents/verify_iteration_overlay.py'),
                       str(ROOT), str(workspace)], stdout=subprocess.DEVNULL).returncode != 0:
        subprocess.run(['bash', str(ROOT / 'tools/build_ros.sh')], check=True)
    if not (ROOT / 'artifacts/courses/seed-2027/autonomy.json').exists():
        ros('python3', str(ROOT / 'tools/generate_course_variant.py'), '--seed', '2027', '--difficulty', 'normal')
    trials = plan.get('trials') or [dict(arm=a) for a in plan['arms']]
    for seed, difficulty in layouts(trials):
        ros('python3', str(ROOT / 'tools/generate_course_variant.py'), '--seed', str(seed), '--difficulty', difficulty)
        for n in range(1, instances + 1):
            target = folder / f'instance-{n}/courses/{seed}-{difficulty}'
            target.mkdir(parents=True, exist_ok=True)
            for name in ('course.json', 'autonomy.json'):
                shutil.copy2(ROOT / f'artifacts/courses/seed-{seed}/{name}', target / name)
    return trials


def split(trials, instances):
    """Balance each condition (arm + settings) across instances, then total load.

    Plain round-robin over an A,B,A,B plan would put every A on one instance and every B
    on another, confounding the condition with the instance.
    """
    shares = {n: [] for n in range(1, instances + 1)}
    for trial in trials:
        key = json.dumps([trial.get('arm'), trial.get('settings')], sort_keys=True)
        same = lambda n: sum(json.dumps([t.get('arm'), t.get('settings')], sort_keys=True) == key for t in shares[n])
        shares[min(shares, key=lambda n: (same(n), len(shares[n]), n))].append(trial)
    return shares


def port_free(port):
    return not subprocess.run(['ss', '-H', '-ltn', f'sport = :{port}'], capture_output=True, text=True).stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('--instances', type=int, default=2)
    parser.add_argument('--stagger', type=float, default=45., help='Seconds between instance launches')
    parser.add_argument('--width', type=int, default=960)
    parser.add_argument('--height', type=int, default=600)
    args = parser.parse_args()
    if not 1 <= args.instances <= 8:
        raise SystemExit('--instances must be 1..8')
    plan = json.loads(args.plan.read_text())
    folder = args.plan.resolve().parent
    busy = [n for n in range(1, args.instances + 1) if not port_free(10000 + n)]
    if busy:
        raise SystemExit(f'Instances already own TCP ports: {[10000 + n for n in busy]}')
    trials = prepare(plan, folder, args.instances)
    shares = split(trials, args.instances)
    script = windows(ROOT / 'tools/sandbox.ps1')
    processes = {}
    for n, share in shares.items():
        if not share:
            continue
        sub = folder / f'instance-{n}'
        sub.mkdir(parents=True, exist_ok=True)
        (sub / 'plan.json').write_text(json.dumps(dict(schema_version=1, trial_timeout_s=plan.get('trial_timeout_s', 720),
                                                       trials=share), indent=1))
        log = (sub / 'launcher.log').open('w')
        processes[n] = (subprocess.Popen(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', script,
                                          '-Instance', str(n), '-Hidden', '-Width', str(args.width), '-Height', str(args.height),
                                          '-Batch', windows(sub / 'plan.json')], stdout=log, stderr=subprocess.STDOUT), log)
        print(f'instance {n}: {len(share)} trials', flush=True)
        if n != max(shares):
            time.sleep(args.stagger)
    exit_codes = {}
    for n, (process, log) in processes.items():
        exit_codes[n] = process.wait(); log.close()
    rows = []
    for n in processes:
        results = folder / f'instance-{n}/batch-results.json'
        if not results.exists():
            print(f'instance {n}: no results (exit {exit_codes[n]}); see {results.parent}/launcher.log')
            continue
        subprocess.run(['python3', str(ROOT / 'tools/sandbox_batch_report.py'), str(results),
                        '--sandbox', str(ROOT / f'artifacts/sandbox-instance-{n}')], check=True, stdout=subprocess.DEVNULL)
        for row in json.loads((results.parent / 'batch-report.json').read_text())['rows']:
            rows.append(dict(row, instance=n))
    import sandbox_batch_report as report
    merged = dict(schema_version=1, plan=str(args.plan), instances=args.instances, exit_codes=exit_codes, rows=rows,
                  summary=report.summary(rows), by_escape=report.summary(rows, lambda r: r.get('escape', 'legacy')),
                  by_instance=report.summary(rows, lambda r: f"instance {r['instance']}"),
                  by_policy=report.summary(rows, report.policy))
    (folder / 'batch-report.json').write_text(json.dumps(merged, indent=2))
    print(json.dumps(dict(summary=merged['summary'], by_instance=merged['by_instance']), indent=2))


if __name__ == '__main__':
    main()
