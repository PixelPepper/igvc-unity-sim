"""Fixed-size paired microbenchmark of hazard-bit _rectangle_clear (T-0057).

Usage:
  git show <base>:tools/sensor_route_policy.py > baseline_policy.py
  python tools/benchmarks/rectangle_hazard_enumeration.py \
      --baseline baseline_policy.py [--candidate tools/sensor_route_policy.py]

Fixtures are generated synthetic observed grids only (fixed seed); no capture,
course, WORLD or teacher data is read. Decisions of both modules (hazard-bit
path) and the baseline scalar path are compared first; timing is refused on any
mismatch. Then one warmup and exactly five paired rounds run, alternating which
module goes first. There are no adaptive repetitions or significance tests.

Predeclared gate (median candidate time / median baseline time per stratum):
mixed <= 1.00, dense_early_rejection < 1.00, empty <= 1.10 and sparse <= 1.10.
Passing is microbenchmark evidence only, not live navigation benefit.
"""

import argparse
import gc
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import statistics
import sys
import time

TOOLS = Path(__file__).resolve().parents[1]
SEED = 57
WIDTH, HEIGHT, RESOLUTION, ORIGIN = 200, 200, .05, (-5., -5.)
CALLS_PER_STRATUM = 1500
ROUNDS = 5
TIME_CAP_SECONDS = 60.
BODIES = ((-.80, .30, -.33, .37), (-.95, .45, -.38, .38), (-.60, .25, -.30, .30))
STRATA = ('empty', 'sparse', 'dense_early_rejection', 'mixed')
UNKNOWN, INFLATED, LETHAL = -1, 99, 100


def load(path, name):
    path = Path(path).resolve()
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, hashlib.sha256(path.read_bytes()).hexdigest(), str(path)


def free_cost(rng):
    return INFLATED if rng.random() < .05 else rng.randint(0, 98)


def grid(stratum, rng):
    """Synthetic observed costs; hazards are unknown (-1) or lethal (100)."""
    n = WIDTH*HEIGHT
    if stratum == 'empty':
        return [free_cost(rng) for _ in range(n)]
    if stratum == 'sparse':
        return [(LETHAL if rng.random() < .5 else UNKNOWN) if rng.random() < .003
                else free_cost(rng) for _ in range(n)]
    if stratum == 'dense_early_rejection':
        return [(LETHAL if rng.random() < .5 else UNKNOWN) if rng.random() < .6
                else free_cost(rng) for _ in range(n)]
    costs = [free_cost(rng) for _ in range(n)]
    for _ in range(25):     # dense lethal/unknown blocks
        x0, y0 = rng.randrange(WIDTH), rng.randrange(HEIGHT)
        w, h, value = rng.randint(3, 30), rng.randint(3, 30), rng.choice((LETHAL, UNKNOWN))
        for iy in range(y0, min(HEIGHT, y0+h)):
            for ix in range(x0, min(WIDTH, x0+w)):
                costs[iy*WIDTH+ix] = value
    for _ in range(6):      # painted-line-like lethal strokes
        x, y, heading = rng.uniform(0, WIDTH), rng.uniform(0, HEIGHT), rng.uniform(0, math.tau)
        for _ in range(150):
            ix, iy = int(x), int(y)
            if 0 <= ix < WIDTH and 0 <= iy < HEIGHT:
                costs[iy*WIDTH+ix] = LETHAL
            x, y = x+math.cos(heading), y+math.sin(heading)
    for i in range(n):      # sparse scatter
        if rng.random() < .002:
            costs[i] = UNKNOWN
    return costs


def hazard_bits(costs):
    rows = [0] * HEIGHT
    for iy in range(HEIGHT):
        base = iy*WIDTH
        rows[iy] = sum(1 << ix for ix in range(WIDTH) if not 0 <= costs[base+ix] < 100)
    return rows


def fixtures():
    rng = random.Random(SEED)
    result = {}
    span_x, span_y = WIDTH*RESOLUTION, HEIGHT*RESOLUTION
    for stratum in STRATA:
        costs = grid(stratum, rng)
        rows = hazard_bits(costs)
        poses = [(ORIGIN[0]+rng.uniform(1.2, span_x-1.2), ORIGIN[1]+rng.uniform(1.2, span_y-1.2),
                  rng.uniform(-math.pi, math.pi), rng.choice(BODIES))
                 for _ in range(CALLS_PER_STRATUM)]
        result[stratum] = costs, rows, poses
    return result


def decide(function, costs, rows, poses):
    return [function(x, y, yaw, bounds, costs, WIDTH, HEIGHT, RESOLUTION, ORIGIN, rows)
            for x, y, yaw, bounds in poses]


def timed(function, costs, rows, poses):
    clock = time.perf_counter_ns
    start = clock()
    for x, y, yaw, bounds in poses:
        function(x, y, yaw, bounds, costs, WIDTH, HEIGHT, RESOLUTION, ORIGIN, rows)
    return clock()-start


def run(baseline_path, candidate_path):
    started = time.perf_counter()
    baseline, baseline_hash, baseline_path = load(baseline_path, 't0057_baseline_policy')
    candidate, candidate_hash, candidate_path = load(candidate_path, 't0057_candidate_policy')
    report = {
        'benchmark': 'rectangle_hazard_enumeration', 'seed': SEED,
        'grid': {'width': WIDTH, 'height': HEIGHT, 'resolution': RESOLUTION, 'origin': ORIGIN},
        'calls_per_stratum': CALLS_PER_STRATUM, 'warmup_rounds': 1, 'rounds': ROUNDS,
        'time_cap_seconds': TIME_CAP_SECONDS, 'python': sys.version,
        'baseline': {'path': baseline_path, 'sha256': baseline_hash},
        'candidate': {'path': candidate_path, 'sha256': candidate_hash},
    }
    data = fixtures()
    functions = {'baseline': baseline._rectangle_clear, 'candidate': candidate._rectangle_clear}

    counts, mismatches = {}, {}
    for stratum, (costs, rows, poses) in data.items():
        costs_before, rows_before = list(costs), list(rows)
        scalar = decide(baseline._rectangle_clear, costs, None, poses)
        base = decide(functions['baseline'], costs, rows, poses)
        cand = decide(functions['candidate'], costs, rows, poses)
        bad = [i for i, (s, b, c) in enumerate(zip(scalar, base, cand)) if not s == b == c]
        if costs != costs_before or rows != rows_before:
            bad.append('inputs_mutated')
        counts[stratum] = {'calls': len(poses), 'clear': sum(cand), 'blocked': len(cand)-sum(cand),
                           'hazard_cells': sum(bin(r).count('1') for r in rows)}
        if bad:
            mismatches[stratum] = bad[:20] + (['...'] if len(bad) > 20 else [])
    report['counts'] = counts
    if mismatches:
        report.update(status='decision_mismatch', mismatches=mismatches,
                      gate={'evaluated': False, 'accepted': False})
        return report

    timings = {s: {'baseline': [], 'candidate': []} for s in STRATA}
    warmup = {s: {} for s in STRATA}
    orders = []
    status = 'complete'
    gc_was_enabled = gc.isenabled()
    gc.collect()
    gc.disable()
    try:
        for round_index in range(1+ROUNDS):
            order = ('baseline', 'candidate') if round_index % 2 == 0 else ('candidate', 'baseline')
            if round_index:
                orders.append(list(order))
            for stratum in STRATA:
                for name in order:
                    if time.perf_counter()-started > TIME_CAP_SECONDS:
                        status = 'time_cap_exceeded'
                        break
                    elapsed = timed(functions[name], *data[stratum])
                    if round_index:
                        timings[stratum][name].append(elapsed)
                    else:
                        warmup[stratum][name] = elapsed
                if status != 'complete':
                    break
            if status != 'complete':
                break
    finally:
        if gc_was_enabled:
            gc.enable()

    report.update(status=status, round_orders=orders, warmup_ns=warmup, timings_ns=timings,
                  elapsed_seconds=time.perf_counter()-started)
    if status != 'complete':
        report['gate'] = {'evaluated': False, 'accepted': False}
        return report
    strata = {}
    for stratum in STRATA:
        b, c = timings[stratum]['baseline'], timings[stratum]['candidate']
        strata[stratum] = {
            'baseline_median_ns': statistics.median(b),
            'candidate_median_ns': statistics.median(c),
            'ratio': statistics.median(c)/statistics.median(b),
            'paired_round_ratios': [ci/bi for bi, ci in zip(b, c)],
        }
    report['strata'] = strata
    ratio = {s: strata[s]['ratio'] for s in STRATA}
    checks = {'mixed_ratio<=1.00': ratio['mixed'] <= 1.,
              'dense_early_rejection_ratio<1.00': ratio['dense_early_rejection'] < 1.,
              'empty_ratio<=1.10': ratio['empty'] <= 1.1,
              'sparse_ratio<=1.10': ratio['sparse'] <= 1.1}
    report['gate'] = {'evaluated': True, 'checks': checks, 'accepted': all(checks.values()),
                      'note': 'microbenchmark evidence only, not live benefit'}
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--baseline', required=True, help='immutable baseline sensor_route_policy.py')
    parser.add_argument('--candidate', default=str(TOOLS/'sensor_route_policy.py'))
    parser.add_argument('--output', help='also write the JSON report here')
    args = parser.parse_args(argv)
    sys.path.insert(0, str(TOOLS))   # both modules import swept_footprint
    report = run(args.baseline, args.candidate)
    text = json.dumps(report, indent=2)
    print(text)
    if args.output:
        Path(args.output).write_text(text+'\n')
    return 0 if report['status'] == 'complete' else 1


if __name__ == '__main__':
    sys.exit(main())
