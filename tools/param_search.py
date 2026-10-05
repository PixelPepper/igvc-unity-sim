#!/usr/bin/env python3
"""Robust sandbox parameter search across course seeds (LEARNING_PLAN phase 2).

Each iteration proposes navigation settings within the sandbox allowlist, runs them on the
training seeds through one real-time sandbox batch (tools/sandbox.ps1 -Batch), audits the
runs, and scores them. Proposals come from a Gaussian-process expected-improvement search
when scikit-learn/scipy are installed, otherwise a seeded random search (reported as such).
`validate` compares the best settings with the accepted baseline on held-out seeds.

The robot only ever receives the settings: courses and audits are used here for scoring.
"""
import argparse
import json
import math
import random
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from sandbox_profile import DEFAULTS, LIMITS, validate_settings

ROOT = Path(__file__).resolve().parents[1]
# Searched dimensions (subset of the allowlist). Speed stays below the 2.2 m/s ceiling until robust.
SPACE = dict(speed_mps=(.4, 1.2), inflation_m=(.2, .6), clearance_weight=(0., 6.),
             planning_budget_s=(.3, 1.5), lookahead_m=(.4, 1.2))


def score(row):
    """Per-trial score; higher is better. Progress first, then audited quality, then time."""
    if row.get('state') is None or not row.get('run'):
        return -100.
    s = 100. * row['completed'] / 6 + (50. if row['completed'] == 6 else 0.)
    if row['completed'] == 6 and row.get('sim_span_s'):
        s -= .1 * row['sim_span_s']
    s -= 5. * (row.get('backups') or 0)
    s -= 40. if (row.get('health_fail') or 0) > 0 else 0.
    clearance = row.get('min_clearance_m')
    s -= 30. if clearance is not None and clearance < .1 else 0.
    s += 20. if row.get('audit_passed') else 0.
    return s


def encode(settings):
    return [(settings[k] - lo) / (hi - lo) for k, (lo, hi) in SPACE.items()]


def decode(x):
    settings = dict(DEFAULTS)
    for v, (k, (lo, hi)) in zip(x, SPACE.items()):
        settings[k] = round(float(lo + min(1., max(0., float(v))) * (hi - lo)), 3)
    return validate_settings(settings)


def propose(history, rng, initial=6):
    """Random start, then GP-EI over random candidates (random search if sklearn is missing)."""
    if len(history) < initial:
        n = len(SPACE)
        return decode([rng.random() for _ in range(n)]), 'initial-random'
    try:
        import numpy as np
        from scipy.stats import norm
        from sklearn.gaussian_process import GaussianProcessRegressor
        from sklearn.gaussian_process.kernels import Matern, WhiteKernel, ConstantKernel
    except ImportError:
        return decode([rng.random() for _ in SPACE]), 'random (scikit-learn/scipy not installed)'
    X = np.array([encode(h['settings']) for h in history]); y = np.array([h['objective'] for h in history])
    mean, std = y.mean(), y.std() or 1.
    gp = GaussianProcessRegressor(ConstantKernel() * Matern(nu=2.5, length_scale=[.3] * len(SPACE)) + WhiteKernel(.3),
                                  normalize_y=False, random_state=rng.randrange(1 << 30)).fit(X, (y - mean) / std)
    candidates = np.array([[rng.random() for _ in SPACE] for _ in range(4000)])
    mu, sigma = gp.predict(candidates, return_std=True)
    best = ((y - mean) / std).max()
    z = (mu - best) / np.maximum(sigma, 1e-9)
    ei = (mu - best) * norm.cdf(z) + sigma * norm.pdf(z)
    return decode(candidates[int(ei.argmax())]), 'gp-ei'


def run_batch(folder, trials):
    folder.mkdir(parents=True, exist_ok=True)
    plan = folder / 'plan.json'
    plan.write_text(json.dumps(dict(schema_version=1, trial_timeout_s=720, trials=trials), indent=2))
    windows_plan = subprocess.run(['wslpath', '-w', str(plan)], capture_output=True, text=True, check=True).stdout.strip()
    windows_script = subprocess.run(['wslpath', '-w', str(ROOT / 'tools/sandbox.ps1')], capture_output=True, text=True, check=True).stdout.strip()
    with (folder / 'launcher.log').open('w') as log:
        subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', windows_script, '-Batch', windows_plan],
                       stdout=log, stderr=subprocess.STDOUT, check=False)
    results = folder / 'batch-results.json'
    if not results.exists():
        raise RuntimeError('Batch produced no results; see ' + str(folder / 'launcher.log'))
    subprocess.run(['python3', str(ROOT / 'tools/sandbox_batch_report.py'), str(results)], check=True, stdout=subprocess.DEVNULL)
    return json.loads((folder / 'batch-report.json').read_text())


def trials_for(settings, seeds, repeats=1):
    return [dict(arm='baseline', seed=seed, difficulty=difficulty, settings=settings)
            for _ in range(repeats) for seed, difficulty in seeds]


def parse_seeds(text):
    pairs = []
    for item in text.split(','):
        seed, _, difficulty = item.partition(':')
        pairs.append((int(seed), difficulty or 'normal'))
    return pairs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('search', 'validate', 'status'))
    parser.add_argument('--study', type=Path, default=ROOT / 'artifacts/learning/param-search')
    parser.add_argument('--train-seeds', default='2031:normal,2032:hard,2033:easy')
    parser.add_argument('--holdout-seeds', default='2041:normal,2042:hard,2043:normal')
    parser.add_argument('--iterations', type=int, default=1, help='Batches to run now (each ~20 min per 3 seeds)')
    parser.add_argument('--repeats', type=int, default=2, help='validate: repeats per held-out seed and arm')
    parser.add_argument('--seed', type=int, default=2027)
    args = parser.parse_args()
    args.study.mkdir(parents=True, exist_ok=True)
    state_path = args.study / 'state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else dict(schema_version=1, history=[], space=SPACE)
    rng = random.Random(args.seed + len(state['history']))
    if args.command == 'status':
        ranked = sorted(state['history'], key=lambda h: -h['objective'])
        for h in ranked[:10]:
            print(f"{h['objective']:8.1f} {h['method']:12s} {json.dumps({k: h['settings'][k] for k in SPACE})} six/{len(h['scores'])}={h['six_of_six']}")
        return
    if args.command == 'search':
        seeds = parse_seeds(args.train_seeds)
        for _ in range(args.iterations):
            # The accepted baseline is always evaluated first so every candidate has a paired reference.
            settings, method = (dict(DEFAULTS), 'baseline') if not state['history'] else propose(state['history'], rng)
            folder = args.study / ('iter-%03d-' % len(state['history']) + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S'))
            report = run_batch(folder, trials_for(settings, seeds))
            scores = [score(r) for r in report['rows']]
            state['history'].append(dict(settings=settings, method=method, folder=str(folder.relative_to(ROOT)), seeds=seeds,
                                         scores=scores, objective=sum(scores) / len(scores) - .5 * (max(scores) - min(scores)),
                                         six_of_six=sum(r['completed'] == 6 for r in report['rows'])))
            state_path.write_text(json.dumps(state, indent=2))
            print(f"iteration {len(state['history'])-1}: {method} objective {state['history'][-1]['objective']:.1f} scores {scores}")
        return
    best = max((h for h in state['history'] if h['method'] != 'baseline'), key=lambda h: h['objective'], default=None)
    if best is None:
        raise SystemExit('No searched candidate yet')
    seeds = parse_seeds(args.holdout_seeds)
    trials = []
    for seed, difficulty in seeds:
        for _ in range(args.repeats):
            # Alternate arms per seed so drift affects both equally.
            trials += [dict(arm='baseline', seed=seed, difficulty=difficulty, settings=dict(DEFAULTS)),
                       dict(arm='baseline', seed=seed, difficulty=difficulty, settings=best['settings'])]
    folder = args.study / ('validate-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S'))
    report = run_batch(folder, trials)
    arms = {'accepted': [], 'candidate': []}
    for i, r in enumerate(report['rows']):
        arms['candidate' if i % 2 else 'accepted'].append(score(r))
    result = {k: dict(mean=sum(v) / len(v), scores=v) for k, v in arms.items()}
    result['candidate_settings'] = best['settings']
    (folder / 'validation.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
