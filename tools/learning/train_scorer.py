#!/usr/bin/env python3
"""Train the route-candidate scorer offline and export plain JSON (no pickles).

Input: rows from build_dataset.py (one per route candidate; group = decision).
Model: scikit-learn GradientBoostingRegressor predicting teacher regret (m)
from observed-only features; the policy picks the lowest prediction among
already-admissible candidates. Evaluation is GroupKFold BY RUN, so no decision
of a held-out run (or its correlated neighbours) is ever trained on.

Reported per held-out decision (groups with >= 2 route candidates):
  * top-1 agreement with the teacher's best candidate, model vs heuristic
    (heuristic = the candidate the current policy chose, source 'grid');
  * mean regret (m) of the model's pick vs the heuristic's pick;
  * a paired sign test over decisions where the two picks differ.
``--kind corridor`` trains the same model on accepted lane-corridor proposals
(build_dataset.py build --kind corridor; heuristic = lowest detector score)
over lane_corridor_policy.CORRIDOR_FEATURES and exports ``"decision":
"corridor"``. Requires scikit-learn + scipy offline only; runtime inference is
learned_scorer.py (numpy).
"""
import argparse
import json
import math
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
from build_dataset import FEATURES  # noqa: E402  (also puts tools/ on sys.path)
from learned_scorer import SCHEMA, LearnedScorer  # noqa: E402
from lane_corridor_policy import CORRIDOR_FEATURES  # noqa: E402
from dataset_policy import (DatasetRejected, add_pose_policy_arguments, policy_from_args,  # noqa: E402
                            read_dataset_rows)

KIND_FEATURES = dict(route=FEATURES, corridor=CORRIDOR_FEATURES)

FILL = -1.0  # Missing optional features (e.g. no lane corridor seen). All
             # real values are >= 0 except signed lateral/heading features.


def load_rows(path, pose_policy=None):
    """Usable rows (list) after pose admission (default measured only) and the ranking-group rule.

    dataset_policy.read_dataset_rows returns the same rows plus admission statistics.
    """
    return read_dataset_rows(path, pose_policy)[0]


def matrix(rows, features=FEATURES):
    X = np.full((len(rows), len(features)), FILL)
    for i, row in enumerate(rows):
        for j, name in enumerate(features):
            value = row['features'].get(name)
            if type(value) in (int, float) and math.isfinite(value):
                X[i, j] = value
    return X


def make_model(seed=0, n_estimators=150, max_depth=3, learning_rate=.05):
    from sklearn.ensemble import GradientBoostingRegressor
    return GradientBoostingRegressor(loss='squared_error', n_estimators=n_estimators, max_depth=max_depth,
        learning_rate=learning_rate, subsample=.8, min_samples_leaf=5, random_state=seed)


def export(model, features=FEATURES, decision='route'):
    """Plain-JSON trees. Only learned split/leaf weights over feature names."""
    init = model.init_
    base = float(np.ravel(getattr(init, 'constant_', [[0.]]))[0])
    trees = []
    for estimator in model.estimators_[:, 0]:
        tree = estimator.tree_
        trees.append(dict(feature=[int(v) for v in tree.feature], threshold=[float(v) for v in tree.threshold],
            left=[int(v) for v in tree.children_left], right=[int(v) for v in tree.children_right],
            value=[float(v) for v in tree.value[:, 0, 0]]))
    return dict(schema=SCHEMA, kind='gradient_boosted_regression_trees', decision=decision,
        target='teacher_regret_m',
        lower_is_better=True, features=list(features), fill_value=FILL, base=base,
        learning_rate=float(model.learning_rate), trees=trees,
        note='Weights over observed-only candidate features; contains no course/world/teacher data.')


def pick(members, values):
    return min(range(len(members)), key=lambda i: (values[i], not members[i]['heuristic_choice'], i))


def evaluate(rows, predictions, weight=None):
    """Per-decision picks: model (argmin prediction) or hook form score+w*pred."""
    by_group = {}
    for row, prediction in zip(rows, predictions):
        by_group.setdefault(row['group'], []).append((row, prediction))
    result = dict(decisions=0, model_top1=0, heuristic_top1=0, model_regret=[], heuristic_regret=[],
                  model_better=0, heuristic_better=0, differ=0)
    for members in by_group.values():
        rows_, values = [m[0] for m in members], [m[1] for m in members]
        if weight is not None:
            values = [r['features'].get('score', 0.) + weight*v for r, v in zip(rows_, values)]
        model_pick = rows_[pick(rows_, values)]
        heuristic = next(r for r in rows_ if r['heuristic_choice'])
        result['decisions'] += 1
        result['model_top1'] += model_pick['teacher_best']
        result['heuristic_top1'] += heuristic['teacher_best']
        result['model_regret'].append(model_pick['regret_m'])
        result['heuristic_regret'].append(heuristic['regret_m'])
        if model_pick is not heuristic:
            result['differ'] += 1
            if model_pick['regret_m'] < heuristic['regret_m'] - 1e-6:
                result['model_better'] += 1
            elif model_pick['regret_m'] > heuristic['regret_m'] + 1e-6:
                result['heuristic_better'] += 1
    return result


def summarize(result):
    n = max(result['decisions'], 1)
    wins, losses = result['model_better'], result['heuristic_better']
    try:
        from scipy.stats import binomtest
        p = float(binomtest(wins, wins+losses, .5).pvalue) if wins+losses else 1.
    except ImportError:
        p = None
    return dict(decisions=result['decisions'],
        top1_model=round(result['model_top1']/n, 4), top1_heuristic=round(result['heuristic_top1']/n, 4),
        mean_regret_model_m=round(float(np.mean(result['model_regret'] or [0])), 4),
        mean_regret_heuristic_m=round(float(np.mean(result['heuristic_regret'] or [0])), 4),
        picks_differ=result['differ'], model_better=wins, heuristic_better=losses, sign_test_p=p)


def course_of(run):
    """Course identity of a run (its simulator course hash), so repeated runs of one layout share a fold."""
    for path in sorted(REPO.glob(f'artifacts/sandbox*/runs/{run}/run.json')):
        try:
            return json.loads(path.read_text()).get('course_sha256') or run
        except (OSError, ValueError):
            pass
    return run


def cross_validate(rows, folds=5, seed=0, weight=None, group_by='run', features=FEATURES,
                   predictions_out=None, **params):
    """Grouped CV report. ``weight`` may be one hook weight or a list of them;
    ``predictions_out`` (a list) receives the held-out prediction per row."""
    from sklearn.model_selection import GroupKFold
    runs = sorted({r['run'] for r in rows})
    key = {name: (course_of(name) if group_by == 'course' else name) for name in runs}
    units = sorted(set(key.values()))
    if len(units) < 2:
        raise ValueError(f'Grouped CV by {group_by} needs at least two {group_by}s with alternative groups')
    X, y = matrix(rows, features), np.array([r['regret_m'] for r in rows])
    run_ids = np.array([units.index(key[r['run']]) for r in rows])
    predictions = np.zeros(len(rows))
    splitter = GroupKFold(n_splits=min(folds, len(units)))
    for train, test in splitter.split(X, y, run_ids):
        model = make_model(seed, **params).fit(X[train], y[train])
        predictions[test] = model.predict(X[test])
    report = dict(model=summarize(evaluate(rows, predictions)), folds=splitter.n_splits, group_by=group_by, groups=len(units))
    for value in ([] if weight is None else weight if isinstance(weight, (list, tuple)) else [weight]):
        report[f'hook_weight_{value:g}'] = summarize(evaluate(rows, predictions, value))
    if predictions_out is not None:
        predictions_out.extend(float(v) for v in predictions)
    per_run = {}
    for name in runs:
        subset = [i for i, r in enumerate(rows) if r['run'] == name]
        per_run[name] = summarize(evaluate([rows[i] for i in subset], predictions[subset]))
    report['per_run'] = per_run
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--kind', choices=('route', 'corridor'), default='route',
                        help='route candidates (default) or accepted lane-corridor proposals')
    parser.add_argument('--dataset', type=Path, help='default artifacts/learning/dataset/<kind>_candidates.jsonl')
    parser.add_argument('--model-out', type=Path, help='default artifacts/learning/models/<kind>_scorer.json')
    parser.add_argument('--report-out', type=Path)
    parser.add_argument('--predictions-out', type=Path,
                        help='optional JSONL of held-out CV predictions (group, index, prediction)')
    parser.add_argument('--folds', type=int, default=5)
    parser.add_argument('--hook-weight', type=float, nargs='+', default=[1.],
                        help='hook form score + w*prediction evaluated at each weight')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--group-by', choices=('run', 'course'), default='course',
                        help='Cross-validation unit; course keeps repeated runs of a layout in one fold')
    add_pose_policy_arguments(parser)
    args = parser.parse_args(argv)
    features = KIND_FEATURES[args.kind]
    args.dataset = args.dataset or REPO/f'artifacts/learning/dataset/{args.kind}_candidates.jsonl'
    args.model_out = args.model_out or REPO/f'artifacts/learning/models/{args.kind}_scorer.json'
    policy = policy_from_args(args)

    def write_report(report):
        text = json.dumps(report, indent=2)
        if args.report_out:  # also for rejected or empty datasets, so exclusions stay reviewable
            args.report_out.parent.mkdir(parents=True, exist_ok=True)
            args.report_out.write_text(text+'\n', encoding='utf-8')
        print(text)

    try:
        rows, admission = read_dataset_rows(args.dataset, policy)
    except DatasetRejected as exc:  # malformed dataset: rejected whole, nothing fitted
        write_report(dict(kind=args.kind, dataset=str(args.dataset), pose_policy=policy.to_dict(),
                          error=f'rejected dataset: {exc}'))
        return 2
    # rows/decisions are the final usable counts; dataset_admission has pre-pose and pose-admitted counts.
    report = dict(kind=args.kind, dataset=str(args.dataset), rows=len(rows),
                  decisions=len({r['group'] for r in rows}), runs=sorted({r['run'] for r in rows}),
                  pose_policy=policy.to_dict(), dataset_admission=admission)
    if not rows:
        report['error'] = 'No pose-admitted decision has >= 2 labelled candidates; nothing to learn.'
        write_report(report)
        return 1
    held_out = []
    weights = args.hook_weight[0] if len(args.hook_weight) == 1 else args.hook_weight
    try:
        report['cross_validation'] = cross_validate(rows, args.folds, args.seed, weights, args.group_by,
                                                    features, held_out)
    except ValueError as exc:
        report['cross_validation'] = dict(error=str(exc))
    if args.predictions_out and held_out:
        args.predictions_out.parent.mkdir(parents=True, exist_ok=True)
        with args.predictions_out.open('w', encoding='utf-8') as stream:
            for row, value in zip(rows, held_out):
                stream.write(json.dumps(dict(group=row['group'], run=row['run'], index=row['index'],
                    endpoint=row['endpoint'], prediction=value), separators=(',', ':'))+'\n')
    X = matrix(rows, features)
    model = make_model(args.seed).fit(X, np.array([r['regret_m'] for r in rows]))
    exported = export(model, features, args.kind)
    # Parity: numpy inference must reproduce sklearn on the training matrix.
    parity = float(np.max(np.abs(LearnedScorer(exported).predict_matrix(X) - model.predict(X))))
    report['export_parity_max_abs'] = parity
    if parity > 1e-9:
        raise SystemExit(f'Exported model disagrees with sklearn by {parity}')
    args.model_out.parent.mkdir(parents=True, exist_ok=True)
    args.model_out.write_text(json.dumps(exported, separators=(',', ':'))+'\n', encoding='utf-8')
    report['model_out'] = str(args.model_out)
    write_report(report)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
