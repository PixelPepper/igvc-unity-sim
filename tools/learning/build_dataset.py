#!/usr/bin/env python3
"""Join observed decision candidates with hindsight teacher labels (offline only).

Two steps:

``replay``  re-plans every saved snapshot of a run with the CURRENT observed-only
            policy (tools/observed_navigation.py, which now logs route
            alternatives) and writes a separate run copy under
            artifacts/learning/replayed/<run>/ whose decisions/outcomes.jsonl
            carries the replayed candidates. The source run is never modified.
            Label it afterwards with the teacher, e.g. (Windows)::

              dotnet run -c Release --project tools/reference_lab -- label
                  --runs artifacts/learning/replayed --out artifacts/learning/labels-replayed

``build``   joins outcomes.jsonl candidates (features X, observed-only) with the
            teacher's labels.jsonl (target y) into one JSONL row per ROUTE
            candidate ('grid' = heuristic choice, 'route_alt' = admissible
            alternative). y is the teacher regret within that decision's route
            candidates; group = decision; run is kept for grouped CV.
            ``--kind corridor`` instead emits one row per ACCEPTED lane-corridor
            proposal of decisions with >= 2 of them whose guidance was the
            observed corridor; the heuristic choice is the lowest detector
            score. Features are lane_corridor_policy.corridor_feature_rows of
            the logged candidate plus the decision's own observed snapshot
            (pose, GPS destination, costmap): the same function the runtime
            re-rank uses. y is the teacher regret within the corridor group.

Teacher/world-derived values appear ONLY as targets (``teacher_cost_m``,
``regret_m``, ``teacher_best``); features come from what the robot logged.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import math
import os
from pathlib import Path
import shutil
import sys

TOOLS = Path(__file__).resolve().parents[1]
REPO = TOOLS.parent
sys.path.insert(0, str(TOOLS))

ROUTE_SOURCES = ('grid', 'route_alt')
# Observed-only features consumed by the scorer (route policy + lane proximity).
FEATURES = ('score', 'weighted_cost', 'path_length_m', 'local_path_length_m',
    'endpoint_progress_m', 'remaining_m', 'body_risk', 'heading_change_rad', 'abs_turning_rad',
    'target_bearing_error_rad', 'lateral_mean_m', 'lateral_max_abs_m', 'endpoint_lateral_m',
    'side_sign', 'min_lethal_clearance_m', 'left_clearance_m', 'right_clearance_m',
    'min_unknown_clearance_m', 'unknown_fraction_end', 'unknown_fraction_ahead',
    'lethal_fraction_ahead', 'hazard_cells_vs_chosen', 'corridor_entry_distance_m')
COPY_FILES = ('course.json', 'run.json', 'autonomy.json')
CORRIDOR_SOURCE = 'corridor'


def _replay_one(path, fraction):
    from replay_navigation_decision import load_snapshot
    from observed_navigation import evaluate_observed_navigation
    from navigation_decisions import decimate_path, outcome_candidates, _point, _number
    snapshot, _ = load_snapshot(Path(path))
    inputs = snapshot['input']
    options = dict(inputs['planner_options'])
    if options.get('forward_only'):
        options['alternative_search_fraction'] = fraction
    evaluation = evaluate_observed_navigation(inputs['origin'], inputs['resolution'], inputs['width'],
        inputs['height'], inputs['costs'], inputs['robot_xy'], inputs['robot_yaw'], inputs['destination'],
        inputs['lane_points'], heading_hint=inputs['heading_hint'],
        frozen_guidance=inputs.get('frozen_guidance'), **options)
    plan, diagnostics = evaluation['plan'], evaluation['diagnostics']
    source = diagnostics.get('guidance') if isinstance(diagnostics.get('guidance'), str) else None
    record = dict(schema_version=2, index=int(Path(path).name.split('.')[0]),
        destination_index=snapshot.get('metadata', {}).get('destination_index'),
        plan=dict(endpoint=None, path=None, source=source), candidates=outcome_candidates(diagnostics, plan),
        search_wall_s=_number(evaluation['search_wall_s']), admitted=None, action='not_sent',
        robot_xy_after=None, progress_m=None, replayed=True)
    if plan is not None:
        goal, yaw = _point(plan.get('local_goal') or []), _number(plan.get('yaw'))
        record['plan'].update(endpoint=goal+[round(yaw, 4)] if goal and yaw is not None else goal,
                              path=decimate_path(plan.get('path')))
    return record


def _link_or_copy(source, target):
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)


def replay_run(run_dir, out_root, fraction=.1, jobs=4):
    run_dir, out_root = Path(run_dir).resolve(), Path(out_root).resolve()
    decisions = sorted((run_dir/'decisions').glob('*.json.gz'))
    if not decisions or not all((run_dir/name).exists() for name in ('course.json', 'run.json')):
        raise ValueError(f'{run_dir.name}: needs decisions/*.json.gz, course.json and run.json')
    target = out_root/run_dir.name
    if target.resolve() == run_dir:
        raise ValueError('Replay output must differ from the source run')
    (target/'decisions').mkdir(parents=True, exist_ok=True)
    for name in COPY_FILES:
        if (run_dir/name).exists():
            shutil.copy2(run_dir/name, target/name)
    for snapshot in decisions:
        if not (target/'decisions'/snapshot.name).exists():
            _link_or_copy(snapshot, target/'decisions'/snapshot.name)
    # Keep the robot's logged outcome (admission/action/progress) when present.
    logged = {}
    if (run_dir/'decisions'/'outcomes.jsonl').exists():
        from navigation_decisions import read_outcomes
        logged = read_outcomes(run_dir/'decisions')
    records, failures = [], 0
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        for path, future in [(p, pool.submit(_replay_one, str(p), fraction)) for p in decisions]:
            try:
                record = future.result()
            except Exception as exc:  # one bad snapshot must not drop a run
                failures += 1
                print(f'replay failed {path.name}: {exc!r}', file=sys.stderr)
                continue
            old = logged.get(record['index'])
            if old:
                record.update({k: old.get(k) for k in ('admitted', 'action', 'robot_xy_after', 'progress_m')})
                record['logged_plan_endpoint'] = (old.get('plan') or {}).get('endpoint')
            records.append(record)
    with (target/'decisions'/'outcomes.jsonl').open('w', encoding='utf-8') as stream:
        for record in records:
            stream.write(json.dumps(record, allow_nan=False, separators=(',', ':'))+'\n')
    alternatives = sum(1 for r in records for c in r['candidates'] if c['source'] == 'route_alt')
    with_alt = sum(1 for r in records if any(c['source'] == 'route_alt' for c in r['candidates']))
    return dict(run=run_dir.name, snapshots=len(decisions), replayed=len(records), failures=failures,
                decisions_with_alternatives=with_alt, alternatives=alternatives, out=str(target))


def _read_jsonl(path):
    rows = {}
    with Path(path).open(encoding='utf-8') as stream:
        for line in stream:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if isinstance(record, dict) and type(record.get('index')) is int:
                rows[record['index']] = record
    return rows


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _joined(outcomes_path, labels_path, stats):
    """Yield (index, outcome, label, candidates, labelled) whose candidates align."""
    outcomes, labels = _read_jsonl(outcomes_path), _read_jsonl(labels_path)
    for index in sorted(outcomes):
        stats['decisions'] += 1
        outcome, label = outcomes[index], labels.get(index)
        if label is None or not isinstance(label.get('candidates'), list):
            continue
        candidates, labelled = outcome.get('candidates') or [], label['candidates']
        if len(candidates) != len(labelled) or any(
                not c.get('endpoint') or not l.get('endpoint')
                or math.dist(c['endpoint'][:2], l['endpoint'][:2]) > 2e-3
                or c.get('source') != l.get('source') for c, l in zip(candidates, labelled)):
            stats['mismatched'] += 1
            continue
        stats['joined'] += 1
        yield index, outcome, label, candidates, labelled


def build_rows(outcomes_path, labels_path, run_name, include_single=False):
    """Yield one row per route candidate of every decision with labels."""
    stats = dict(decisions=0, joined=0, mismatched=0, groups=0, rows=0)
    rows = []
    for index, outcome, _, candidates, labelled in _joined(outcomes_path, labels_path, stats):
        group = [(c, l) for c, l in zip(candidates, labelled)
                 if c.get('source') in ROUTE_SOURCES and _finite(l.get('teacher_cost_m'))]
        if not any(c['source'] == 'grid' for c, _ in group) or (len(group) < 2 and not include_single):
            continue
        best = min(l['teacher_cost_m'] for _, l in group)
        best_index = min(range(len(group)), key=lambda i: group[i][1]['teacher_cost_m'])
        stats['groups'] += 1
        for k, (candidate, label_row) in enumerate(group):
            features = {name: candidate.get('features', {}).get(name) for name in FEATURES
                        if _finite(candidate.get('features', {}).get(name))}
            rows.append(dict(run=run_name, index=index, group=f'{run_name}:{index}',
                destination_index=outcome.get('destination_index'), source=candidate['source'],
                heuristic_choice=candidate['source'] == 'grid', features=features,
                distinct_by=candidate.get('distinct_by'), endpoint=candidate['endpoint'][:2],
                teacher_cost_m=label_row['teacher_cost_m'],
                regret_m=round(label_row['teacher_cost_m']-best, 4), teacher_best=k == best_index,
                replayed=bool(outcome.get('replayed'))))
            stats['rows'] += 1
    return rows, stats


def _load_snapshot_input(path):
    import gzip
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        return json.load(stream)['input']


def build_corridor_rows(outcomes_path, labels_path, run_name, decisions_dir=None):
    """One row per accepted corridor proposal of decisions with >= 2 of them.

    Only decisions whose executed guidance was the observed corridor count
    (otherwise the corridor choice did not steer the robot). Costmap features
    come from the decision's own snapshot (observed inputs only).
    """
    from lane_corridor_policy import corridor_feature_rows
    stats = dict(decisions=0, joined=0, mismatched=0, groups=0, rows=0, not_corridor_guidance=0,
                 missing_snapshot=0)
    rows = []
    decisions_dir = Path(decisions_dir) if decisions_dir is not None else Path(outcomes_path).parent
    for index, outcome, label, candidates, labelled in _joined(outcomes_path, labels_path, stats):
        group = [(c, l) for c, l in zip(candidates, labelled)
                 if c.get('source') == CORRIDOR_SOURCE and _finite(l.get('teacher_cost_m'))
                 and len(c['endpoint']) >= 3 and _finite(c.get('score'))]
        if len(group) < 2:
            continue
        if (outcome.get('plan') or {}).get('source') != 'observed_lane_corridor':
            stats['not_corridor_guidance'] += 1
            continue
        try:
            inputs = _load_snapshot_input(decisions_dir/f'{index:05d}.json.gz')
            robot, yaw, destination = inputs['robot_xy'], inputs['robot_yaw'], inputs['destination']
            costmap = (inputs['origin'], inputs['resolution'], inputs['width'], inputs['height'],
                       inputs['costs'])
        except (OSError, ValueError, KeyError, EOFError):
            stats['missing_snapshot'] += 1
            continue
        proposals = [dict(c.get('features') or {}, score=c['score'], entry=c['endpoint'][:2],
                          direction=[math.cos(c['endpoint'][2]), math.sin(c['endpoint'][2])])
                     for c, _ in group]
        features = corridor_feature_rows(proposals, robot, yaw, destination, costmap)
        # The detector keeps the lowest score (outcomes list corridors in that order).
        heuristic = min(range(len(group)), key=lambda k: (group[k][0]['score'], k))
        best_index = min(range(len(group)), key=lambda k: group[k][1]['teacher_cost_m'])
        best = group[best_index][1]['teacher_cost_m']
        stats['groups'] += 1
        for k, ((candidate, label_row), row_features) in enumerate(zip(group, features)):
            rows.append(dict(run=run_name, index=index, group=f'{run_name}:{index}',
                destination_index=outcome.get('destination_index'), stamp_s=label.get('stamp_s'),
                source=CORRIDOR_SOURCE, heuristic_choice=k == heuristic,
                features={name: value for name, value in row_features.items() if _finite(value)},
                endpoint=candidate['endpoint'][:2], endpoint_cell=label_row.get('endpoint_cell'),
                teacher_cost_m=label_row['teacher_cost_m'],
                regret_m=round(label_row['teacher_cost_m']-best, 4), teacher_best=k == best_index,
                replayed=bool(outcome.get('replayed'))))
            stats['rows'] += 1
    return rows, stats


def _build_one(kind, outcomes, labels, name):
    if kind == 'corridor':
        return build_corridor_rows(outcomes, labels, name)
    return build_rows(outcomes, labels, name)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    replay = sub.add_parser('replay', help='re-plan snapshots into artifacts/learning/replayed/<run>')
    replay.add_argument('--runs', nargs='+', required=True, help='run folders (or names under artifacts/sandbox/runs)')
    replay.add_argument('--out-root', type=Path, default=REPO/'artifacts/learning/replayed')
    replay.add_argument('--fraction', type=float, default=.1, help='alternative continuation fraction (live default .1)')
    replay.add_argument('--jobs', type=int, default=4)
    build = sub.add_parser('build', help='join outcomes + teacher labels into per-candidate rows')
    build.add_argument('--runs', nargs='+', required=True)
    build.add_argument('--runs-root', type=Path, default=REPO/'artifacts/learning/replayed',
                       help='where <run>/decisions/outcomes.jsonl lives (artifacts/sandbox/runs for logged data)')
    build.add_argument('--labels-root', type=Path, default=REPO/'artifacts/learning/labels-replayed')
    build.add_argument('--out', type=Path,
                       help='default artifacts/learning/dataset/<kind>_candidates.jsonl')
    build.add_argument('--kind', choices=('route', 'corridor'), default='route',
                       help='route candidates (default) or accepted lane-corridor proposals')
    build.add_argument('--jobs', type=int, default=1, help='parallel runs (corridor reads snapshots)')
    args = parser.parse_args(argv)

    def run_path(value, root):
        path = Path(value)
        return path if path.exists() and path.is_dir() else root/value

    if args.command == 'replay':
        for value in args.runs:
            summary = replay_run(run_path(value, REPO/'artifacts/sandbox/runs'), args.out_root,
                                 args.fraction, args.jobs)
            print(json.dumps(summary))
        return 0
    if args.out is None:
        args.out = REPO/f'artifacts/learning/dataset/{args.kind}_candidates.jsonl'
    all_rows, report, work = [], {}, []
    for value in args.runs:
        name = Path(value).name
        outcomes = run_path(value, args.runs_root)/'decisions'/'outcomes.jsonl'
        labels = args.labels_root/name/'labels.jsonl'
        if not outcomes.exists() or not labels.exists():
            report[name] = dict(error='missing outcomes.jsonl or labels.jsonl')
            continue
        work.append((name, outcomes, labels))
    if args.jobs > 1 and work:
        with ProcessPoolExecutor(max_workers=args.jobs) as pool:
            results = list(pool.map(_build_one, *zip(*[(args.kind, o, l, n) for n, o, l in work])))
    else:
        results = [_build_one(args.kind, o, l, n) for n, o, l in work]
    for (name, _, _), (rows, stats) in zip(work, results):
        all_rows += rows
        report[name] = stats
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('w', encoding='utf-8') as stream:
        for row in all_rows:
            stream.write(json.dumps(row, separators=(',', ':'))+'\n')
    summary = dict(out=str(args.out), kind=args.kind, runs=report, rows=len(all_rows),
                   groups=len({r['group'] for r in all_rows}),
                   runs_with_groups=len({r['run'] for r in all_rows}))
    args.out.with_suffix('.summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
