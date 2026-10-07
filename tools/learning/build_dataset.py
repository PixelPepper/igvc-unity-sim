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
            ``--corridor-label`` (required with ``--kind corridor``) selects
            the target: ``straight-v1`` = legacy teacher_cost_m (straight line
            to the entry, even through walls); ``path-v3`` = the separate
            corridor_target.cost_m (grid-path aware). Every label record must
            carry that mode (records without one are legacy straight-v1);
            other or mixed modes abort. Under path-v3 a whole decision group
            is omitted when any member's target is unavailable (blocked,
            search-limited, disconnected): no cost is guessed. All omissions
            are counted by reason in the stats.

Pose provenance (tools/learning/dataset_policy.py): each joined decision's
snapshot ``decisions/NNNNN.json.gz`` (NNNNN = outcome index) is classified with
tools/snapshot_pose_provenance before any group cardinality or heuristic filter.
Only measured poses are admitted by default; ``--allow-predicted`` and
``--allow-unknown-legacy`` (combinable) widen that. Malformed and unavailable
(missing, unreadable, not schema 1) snapshots are never admitted. Excluded
decision groups are dropped whole and counted; every row carries
``pose_source`` and ``pose_reason``; summary.json records ``pose_policy`` and
the counts.

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
from dataset_policy import PoseCounts, PosePolicy, admit_group, load_snapshot_provenance, merge_counts  # noqa: E402

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
# Corridor label modes written by reference_lab `label --corridor-label`; records without one predate it (legacy).
LEGACY_CORRIDOR_LABEL = 'straight-v1'
CORRIDOR_LABELS = (LEGACY_CORRIDOR_LABEL, 'path-v3')
AVAILABLE_TARGETS = ('line_of_sight', 'grid_path')
CORRIDOR_TARGET_STATUSES = AVAILABLE_TARGETS+('disconnected', 'search_limited', 'blocked_robot', 'blocked_entry',
                                              'entry_no_cost_to_go')


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
            stats['unlabelled'] = stats.get('unlabelled', 0)+1
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


def _pose_admission(decisions_dir, index, members, policy, counts):
    """(snapshot, provenance) when the decision passes pose admission, else None (counted)."""
    snapshot, provenance = load_snapshot_provenance(Path(decisions_dir)/f'{index:05d}.json.gz')
    admitted, reason = admit_group([provenance], policy)
    counts.record([provenance], admitted, reason, members)
    return (snapshot, provenance) if admitted else None


def build_rows(outcomes_path, labels_path, run_name, include_single=False, decisions_dir=None, pose_policy=None):
    """Yield one row per route candidate of every pose-admitted decision with labels.

    ``pose_policy`` defaults to PosePolicy() (measured only); snapshots are read
    from ``decisions_dir`` (default: the outcomes file's folder).
    """
    policy = pose_policy if pose_policy is not None else PosePolicy()
    decisions_dir = Path(decisions_dir) if decisions_dir is not None else Path(outcomes_path).parent
    stats = dict(decisions=0, joined=0, mismatched=0, groups=0, rows=0)
    counts = PoseCounts()
    rows = []
    for index, outcome, _, candidates, labelled in _joined(outcomes_path, labels_path, stats):
        members = sum(1 for c in candidates if c.get('source') in ROUTE_SOURCES)
        admission = _pose_admission(decisions_dir, index, members, policy, counts)
        if admission is None:
            continue
        provenance = admission[1]
        group =[(c, l) for c, l in zip(candidates, labelled)
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
                replayed=bool(outcome.get('replayed')),
                pose_source=provenance['kind'], pose_reason=provenance['reason']))
            stats['rows'] += 1
    stats['pose'] = counts.as_dict()
    return rows, stats


def label_mode(labels_path):
    """The single corridor label mode of a labels.jsonl; ValueError on mixed or unknown modes.

    Every raw record is checked before _read_jsonl's index deduplication could
    hide one: duplicate indices and contradictory corridor_label/corridor_cost
    aliases are rejected rather than resolved by picking a row. Malformed
    nonempty lines, non-object records and missing or non-integer indices fail
    closed with their line number; blank lines are tolerated.
    """
    modes, seen = set(), set()
    with Path(labels_path).open(encoding='utf-8') as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except ValueError as error:
                raise ValueError(f'{labels_path}:{number}: malformed label JSON ({error})') from None
            if not isinstance(record, dict):
                raise ValueError(f'{labels_path}:{number}: label record is not an object')
            index = record.get('index')
            if type(index) is not int:
                raise ValueError(f'{labels_path}:{number}: label index {index!r} is not an integer')
            if index in seen:
                raise ValueError(f'{labels_path}:{number}: duplicate label index {index}')
            seen.add(index)
            aliases = [record[key] for key in ('corridor_label', 'corridor_cost') if key in record]
            if len(aliases) == 2 and aliases[0] != aliases[1]:
                raise ValueError(f'{labels_path}#{index}: corridor_label {aliases[0]!r} '
                                 f'contradicts corridor_cost {aliases[1]!r}')
            mode = aliases[0] if aliases else LEGACY_CORRIDOR_LABEL
            if mode not in CORRIDOR_LABELS:
                raise ValueError(f'{labels_path}#{index}: unsupported corridor label mode {mode!r}')
            modes.add(mode)
    if len(modes) > 1:
        raise ValueError(f'{labels_path}: mixed corridor label modes {sorted(modes)}')
    return modes.pop() if modes else LEGACY_CORRIDOR_LABEL


def _corridor_target(label_row, mode, labels_path, index):
    """(cost, None) or (None, omission reason) for one corridor candidate label."""
    if mode == LEGACY_CORRIDOR_LABEL:
        cost = label_row.get('teacher_cost_m')
        return (cost, None) if _finite(cost) else (None, 'nonfinite_legacy_cost')
    target = label_row.get('corridor_target')
    if not isinstance(target, dict) or target.get('status') not in CORRIDOR_TARGET_STATUSES:
        raise ValueError(f'{labels_path}#{index}: path-v3 corridor candidate without a valid corridor_target')
    if target['status'] not in AVAILABLE_TARGETS:
        return None, target['status']
    if not _finite(target.get('cost_m')):
        raise ValueError(f'{labels_path}#{index}: available corridor_target without a finite cost_m')
    return target['cost_m'], None


def build_corridor_rows(outcomes_path, labels_path, run_name, decisions_dir=None,
                        corridor_label=LEGACY_CORRIDOR_LABEL, pose_policy=None):
    """One row per accepted corridor proposal of decisions with >= 2 of them.

    Only decisions whose executed guidance was the observed corridor count
    (otherwise the corridor choice did not steer the robot). Costmap features
    come from the decision's own snapshot (observed inputs only). The target
    is the selected ``corridor_label`` mode's cost; labels in any other mode
    raise ValueError. Under path-v3 a group with any unavailable target is
    omitted whole (``omitted_target`` counts reasons per candidate status).
    Pose admission (``pose_policy``, default measured only) runs first.
    """
    from lane_corridor_policy import corridor_feature_rows
    if corridor_label not in CORRIDOR_LABELS:
        raise ValueError(f'unsupported corridor label mode {corridor_label!r}')
    found = label_mode(labels_path)
    if found != corridor_label:
        raise ValueError(f'{labels_path}: labels are {found}, dataset selected {corridor_label}')
    stats = dict(decisions=0, joined=0, mismatched=0, unlabelled=0, groups=0, rows=0, fewer_than_two=0,
                 not_corridor_guidance=0, missing_snapshot=0, dropped_candidates={}, omitted_target_groups=0,
                 omitted_target={})
    policy = pose_policy if pose_policy is not None else PosePolicy()
    counts = PoseCounts()
    rows = []
    decisions_dir = Path(decisions_dir) if decisions_dir is not None else Path(outcomes_path).parent
    for index, outcome, label, candidates, labelled in _joined(outcomes_path, labels_path, stats):
        members = sum(1 for c in candidates if c.get('source') == CORRIDOR_SOURCE)
        admission = _pose_admission(decisions_dir, index, members, policy, counts)
        if admission is None:
            continue
        snapshot, provenance = admission
        group, unavailable = [], []
        for c, l in zip(candidates, labelled):
            if c.get('source') != CORRIDOR_SOURCE:
                continue
            if len(c['endpoint']) < 3 or not _finite(c.get('score')):
                stats['dropped_candidates']['no_entry_direction_or_score'] = \
                    stats['dropped_candidates'].get('no_entry_direction_or_score', 0)+1
                continue
            cost, reason = _corridor_target(l, corridor_label, labels_path, index)
            if reason == 'nonfinite_legacy_cost':  # legacy behaviour: drop the candidate, now counted
                stats['dropped_candidates'][reason] = stats['dropped_candidates'].get(reason, 0)+1
            elif reason is not None:
                unavailable.append(reason)
            else:
                group.append((c, l, cost))
        if len(group)+len(unavailable) < 2:
            stats['fewer_than_two'] += 1
            continue
        if (outcome.get('plan') or {}).get('source') != 'observed_lane_corridor':
            stats['not_corridor_guidance'] += 1
            continue
        if unavailable:
            stats['omitted_target_groups'] += 1
            for reason in unavailable:
                stats['omitted_target'][reason] = stats['omitted_target'].get(reason, 0)+1
            continue
        try:
            inputs = snapshot['input']
            robot, yaw, destination = inputs['robot_xy'], inputs['robot_yaw'], inputs['destination']
            costmap = (inputs['origin'], inputs['resolution'], inputs['width'], inputs['height'],
                       inputs['costs'])
        except KeyError:  # loadable schema-1 snapshot without the costmap inputs
            stats['missing_snapshot'] += 1
            continue
        proposals = [dict(c.get('features') or {}, score=c['score'], entry=c['endpoint'][:2],
                          direction=[math.cos(c['endpoint'][2]), math.sin(c['endpoint'][2])])
                     for c, _, _ in group]
        features = corridor_feature_rows(proposals, robot, yaw, destination, costmap)
        # The detector keeps the lowest score (outcomes list corridors in that order).
        heuristic = min(range(len(group)), key=lambda k: (group[k][0]['score'], k))
        best_index = min(range(len(group)), key=lambda k: group[k][2])
        best = group[best_index][2]
        stats['groups'] += 1
        for k, ((candidate, label_row, cost), row_features) in enumerate(zip(group, features)):
            row = dict(run=run_name, index=index, group=f'{run_name}:{index}',
                destination_index=outcome.get('destination_index'), stamp_s=label.get('stamp_s'),
                source=CORRIDOR_SOURCE, heuristic_choice=k == heuristic,
                features={name: value for name, value in row_features.items() if _finite(value)},
                endpoint=candidate['endpoint'][:2], endpoint_cell=label_row.get('endpoint_cell'),
                teacher_cost_m=cost, regret_m=round(cost-best, 4), teacher_best=k == best_index,
                replayed=bool(outcome.get('replayed')),
                pose_source=provenance['kind'], pose_reason=provenance['reason'])
            if corridor_label != LEGACY_CORRIDOR_LABEL:  # legacy rows keep their exact previous shape
                row.update(corridor_label=corridor_label, corridor_status=label_row['corridor_target']['status'])
            rows.append(row)
            stats['rows'] += 1
    stats['pose'] = counts.as_dict()
    return rows, stats


def _build_one(kind, outcomes, labels, name, corridor_label=None, pose_policy=None):
    if kind == 'corridor':
        return build_corridor_rows(outcomes, labels, name, corridor_label=corridor_label, pose_policy=pose_policy)
    return build_rows(outcomes, labels, name, pose_policy=pose_policy)


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
    build.add_argument('--corridor-label', choices=CORRIDOR_LABELS,
                       help='required with --kind corridor: straight-v1 (legacy teacher_cost_m) or path-v3 '
                            '(corridor_target.cost_m, unavailable groups omitted); labels must match')
    build.add_argument('--allow-predicted', action='store_true',
                       help='also admit decisions planned from a latency-predicted pose (default: measured only)')
    build.add_argument('--allow-unknown-legacy', action='store_true',
                       help='also admit snapshots without pose-provenance metadata (default: measured only)')
    args = parser.parse_args(argv)
    if args.command == 'build' and (args.kind == 'corridor') != (args.corridor_label is not None):
        parser.error('--corridor-label is required with --kind corridor and only valid with it')

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
    policy = PosePolicy(allow_predicted=args.allow_predicted, allow_unknown_legacy=args.allow_unknown_legacy)
    all_rows, report, work = [], {}, []
    for value in args.runs:
        name = Path(value).name
        outcomes = run_path(value, args.runs_root)/'decisions'/'outcomes.jsonl'
        labels = args.labels_root/name/'labels.jsonl'
        if not outcomes.exists() or not labels.exists():
            report[name] = dict(error='missing outcomes.jsonl or labels.jsonl')
            continue
        work.append((name, outcomes, labels))
    try:  # a label-mode mismatch in any run aborts the whole dataset (no partial or mixed output)
        if args.jobs > 1 and work:
            with ProcessPoolExecutor(max_workers=args.jobs) as pool:
                results = list(pool.map(_build_one, *zip(*[(args.kind, o, l, n, args.corridor_label, policy)
                                                           for n, o, l in work])))
        else:
            results = [_build_one(args.kind, o, l, n, args.corridor_label, policy) for n, o, l in work]
    except ValueError as error:
        print(f'REJECTED: {error}', file=sys.stderr)
        return 2
    for (name, _, _), (rows, stats) in zip(work, results):
        all_rows += rows
        report[name] = stats
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('w', encoding='utf-8') as stream:
        for row in all_rows:
            stream.write(json.dumps(row, separators=(',', ':'))+'\n')
    summary = dict(out=str(args.out), kind=args.kind, corridor_label=args.corridor_label, runs=report, rows=len(all_rows),
                   groups=len({r['group'] for r in all_rows}),
                   runs_with_groups=len({r['run'] for r in all_rows}), pose_policy=policy.to_dict(),
                   pose=merge_counts([stats['pose'] for stats in report.values() if 'pose' in stats]))
    args.out.with_suffix('.summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
