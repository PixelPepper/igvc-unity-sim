#!/usr/bin/env python3
"""Promotion gate for a learning round: new scorer vs promoted scorer vs heuristic.

All are compared on the SAME course-held-out folds (GroupKFold by course hash); the new
recipe (train_scorer.make_model) is retrained per fold on all of the fold's training rows.
How the promoted ("current") model is treated -- ``mode`` in the report:
  * retrain   -- its RECIPE (hyperparameters + features, manifest ``recipe``) is retrained per
                 fold on the fold's training rows restricted to the runs it was originally
                 trained on (manifest ``data_runs``). Neither model is ever scored on courses
                 it trained on, so the promoted model gets no in-sample advantage.
  * unseen    -- no recipe: its exported JSON is scored only on decisions from courses it
                 never saw, and the whole comparison is restricted to those decisions.
  * heuristic -- fewer than MIN_UNSEEN such decisions (or its runs unknown): compared with
                 the heuristic only, and the report says so.
  * first     -- nothing promoted yet: compared with the heuristic.

Promotion rule (``decide``): mean regret strictly better than current AND heuristic,
top-1 not worse than current, sign test of new vs current p < 0.05 with more wins than
losses (vs heuristic when there is no current). The hook weight is the one among WEIGHTS with
the lowest held-out regret in hook form (score + w*prediction), never one whose top-1
is below the heuristic's; no such weight -> no promotion.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
from learned_scorer import LearnedScorer  # noqa: E402
from dataset_policy import (DatasetRejected, PosePolicy, add_pose_policy_arguments,  # noqa: E402
                            policy_from_args, read_dataset_rows)

WEIGHTS = (.5, 1., 2., 4., 8.)
MIN_UNSEEN = 100
HYPER = ('seed', 'n_estimators', 'max_depth', 'learning_rate')
ALPHA = .05
EPS = 1e-6


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def load_rows(path, pose_policy=None):
    """Pose-admitted decision groups (default measured only) with >= 2 candidates and exactly one
    heuristic choice: the same shared reader as train_scorer (dataset_policy.read_dataset_rows)."""
    return read_dataset_rows(path, pose_policy)[0]


def course_of(run, repo=REPO):
    for pattern in (f'artifacts/learning/replayed/{run}/run.json', f'artifacts/sandbox*/runs/{run}/run.json'):
        for path in sorted(Path(repo).glob(pattern)):
            try:
                return json.loads(path.read_text()).get('course_sha256') or run
            except (OSError, ValueError):
                pass
    return run


def sign_p(wins, losses):
    n = wins + losses
    if not n:
        return 1.
    try:
        from scipy.stats import binomtest
        return float(binomtest(wins, n, .5).pvalue)
    except ImportError:  # exact two-sided binomial
        k = min(wins, losses)
        tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
        return min(1., 2 * tail)


def _pick(members, values):
    return min(range(len(members)), key=lambda i: (values[i], not members[i]['heuristic_choice'], i))


def picks(rows, values, weight=None):
    """{group: chosen row} for argmin(values) or hook form score + weight*value."""
    by_group = {}
    for row, value in zip(rows, values):
        by_group.setdefault(row['group'], []).append((row, value))
    chosen = {}
    for group, members in by_group.items():
        rows_ = [m[0] for m in members]
        vals = [m[1] for m in members]
        if weight is not None:
            vals = [(r['features'].get('score') or 0.) + weight * v for r, v in zip(rows_, vals)]
        chosen[group] = rows_[_pick(rows_, vals)]
    return chosen


def heuristic_picks(rows):
    return {r['group']: r for r in rows if r['heuristic_choice']}


def metrics(chosen):
    n = len(chosen)
    if not n:
        return dict(decisions=0, top1=None, mean_regret_m=None)
    return dict(decisions=n, top1=round(sum(bool(r['teacher_best']) for r in chosen.values()) / n, 4),
                mean_regret_m=round(float(np.mean([r['regret_m'] for r in chosen.values()])), 4))


def paired(a, b):
    """Sign test of picks a vs b over decisions where their regrets differ."""
    wins = losses = differ = 0
    for group, row in a.items():
        other = b[group]
        if row is other:
            continue
        differ += 1
        if row['regret_m'] < other['regret_m'] - EPS:
            wins += 1
        elif row['regret_m'] > other['regret_m'] + EPS:
            losses += 1
    return dict(picks_differ=differ, wins=wins, losses=losses, sign_test_p=sign_p(wins, losses))


def default_recipe(features, seed=0):
    """train_scorer.make_model's hyperparameters plus the feature list: enough to retrain."""
    import inspect
    from train_scorer import make_model as factory
    recipe = {k: v.default for k, v in inspect.signature(factory).parameters.items()
              if v.default is not inspect.Parameter.empty}
    recipe.update(trainer='train_scorer.make_model', seed=seed, features=list(features))
    return recipe


def make_model(recipe):
    from train_scorer import make_model as factory
    return factory(**{k: recipe[k] for k in HYPER if k in recipe})


def _encode(rows, features):
    return LearnedScorer(dict(schema='igvc-route-scorer/1', features=list(features), fill_value=-1.,
                              base=0., learning_rate=1., trees=[])).matrix([r['features'] for r in rows])


def cross_validate(rows, new_recipe, current=None, folds=5, repo=REPO, model_factory=make_model):
    """Out-of-fold predictions on course-held-out folds.

    ``current``: None; dict(recipe=..., data_runs=[...]) to retrain the promoted recipe per
    fold; or dict(scorer=LearnedScorer) to score the exported promoted model as is."""
    from sklearn.model_selection import GroupKFold
    runs = sorted({r['run'] for r in rows})
    course = {run: course_of(run, repo) for run in runs}
    units = sorted(set(course.values()))
    if len(units) < 2:
        raise ValueError('Course-held-out CV needs at least two courses')
    X = _encode(rows, new_recipe['features'])
    y = np.array([r['regret_m'] for r in rows])
    unit = np.array([units.index(course[r['run']]) for r in rows])
    new_pred, cur_pred, fold_of = np.zeros(len(rows)), np.zeros(len(rows)), np.zeros(len(rows), dtype=int)
    retrain = current is not None and current.get('recipe') is not None
    if retrain:
        Xc = _encode(rows, current['recipe']['features'])
        original = set(current.get('data_runs') or ())
        own = np.array([r['run'] in original for r in rows])
    splitter = GroupKFold(n_splits=min(folds, len(units)))
    for k, (train, test) in enumerate(splitter.split(X, y, unit)):
        new_pred[test] = model_factory(new_recipe).fit(X[train], y[train]).predict(X[test])
        if retrain:
            subset = train[own[train]]
            # No original-run rows in this fold's training set: zero scores = the heuristic's pick.
            cur_pred[test] = (model_factory(current['recipe']).fit(Xc[subset], y[subset]).predict(Xc[test])
                              if len(subset) >= 2 else 0.)
        elif current is not None:
            cur_pred[test] = current['scorer'].score([rows[i]['features'] for i in test])
        fold_of[test] = k
    return dict(new=new_pred, current=cur_pred if current is not None else None, fold=fold_of,
                folds=splitter.n_splits, courses=len(units), course=course)


def compare(rows, cv, mask=None, weights=WEIGHTS):
    """Metrics over the rows selected by ``mask`` (default all), per fold and overall."""
    keep = np.ones(len(rows), dtype=bool) if mask is None else np.asarray(mask, dtype=bool)
    rows = [r for r, k in zip(rows, keep) if k]
    cv = dict(cv, new=cv['new'][keep], fold=cv['fold'][keep],
              current=None if cv['current'] is None else cv['current'][keep])
    heur = heuristic_picks(rows)
    new = picks(rows, cv['new'])
    report = dict(folds=cv['folds'], courses=cv['courses'], decisions=len(heur),
                  overall=dict(new=metrics(new), heuristic=metrics(heur)),
                  new_vs_heuristic=paired(new, heur))
    cur = None
    if cv['current'] is not None:
        cur = picks(rows, cv['current'])
        report['overall']['current'] = metrics(cur)
        report['new_vs_current'] = paired(new, cur)
    per_fold = []
    for k in range(cv['folds']):
        groups = {r['group'] for r, f in zip(rows, cv['fold']) if f == k}
        sub = lambda d: {g: d[g] for g in groups}
        entry = dict(fold=k, new=metrics(sub(new)), heuristic=metrics(sub(heur)))
        if cur is not None:
            entry['current'] = metrics(sub(cur))
        per_fold.append(entry)
    report['per_fold'] = per_fold
    hook = {}
    for w in weights:
        chosen = picks(rows, cv['new'], w)
        hook[f'{w:g}'] = dict(metrics(chosen), **paired(chosen, heur))
    report['hook'] = hook
    return report


def recommend_weight(report):
    heuristic_top1 = report['overall']['heuristic']['top1']
    safe = [(v['mean_regret_m'], float(w)) for w, v in report['hook'].items() if v['top1'] >= heuristic_top1]
    return min(safe)[1] if safe else None


def decide(report):
    """Promotion decision and the reasons behind it (pure function of a compare() report)."""
    overall, reasons = report['overall'], []
    new, heur, cur = overall['new'], overall['heuristic'], overall.get('current')
    if not new['decisions']:
        return dict(promote=False, weight=None, reasons=['no held-out decisions'])
    if not new['mean_regret_m'] < heur['mean_regret_m']:
        reasons.append(f"regret {new['mean_regret_m']} not below heuristic {heur['mean_regret_m']}")
    if cur is not None:
        if not new['mean_regret_m'] < cur['mean_regret_m']:
            reasons.append(f"regret {new['mean_regret_m']} not below current {cur['mean_regret_m']}")
        if new['top1'] < cur['top1']:
            reasons.append(f"top-1 {new['top1']} below current {cur['top1']}")
        test, versus = report['new_vs_current'], 'current'
    else:
        test, versus = report['new_vs_heuristic'], 'heuristic'
    if not (test['sign_test_p'] < ALPHA and test['wins'] > test['losses']):
        reasons.append(f"sign test vs {versus}: {test['wins']}/{test['losses']} p={test['sign_test_p']:.3g} (need p<{ALPHA})")
    weight = recommend_weight(report)
    if weight is None:
        reasons.append('no hook weight keeps top-1 at or above the heuristic')
    promote = not reasons
    if promote:
        reasons.append(f"regret {new['mean_regret_m']} < heuristic {heur['mean_regret_m']}"
                       + (f" and current {cur['mean_regret_m']}" if cur else '')
                       + f"; sign test vs {versus} {test['wins']}/{test['losses']} p={test['sign_test_p']:.3g}")
    return dict(promote=promote, weight=weight if promote else None, recommended_weight=weight,
                versus=versus, reasons=reasons)


def gate(dataset, new_model_path, current=None, repo=REPO, model_factory=make_model, seed=0, pose_policy=None):
    """``current``: None, or the promoted model's manifest entry (path, recipe, data_runs).

    ``pose_policy`` (dataset_policy.PosePolicy, default measured only) is applied by the shared
    reader before the ranking-group rule, for direct callers (run_round) and the CLI alike. The
    report records the policy and pre-pose / pose-admitted / usable counts, also when no usable
    rows remain (never promotable). A malformed dataset raises dataset_policy.DatasetRejected (a
    ValueError); CV and model errors propagate unchanged and the CLI reports them separately.
    """
    policy = pose_policy if pose_policy is not None else PosePolicy()
    rows, admission = read_dataset_rows(dataset, policy)
    if not rows:
        return dict(dataset=str(dataset), error='no usable decision groups', rows=0,
                    pose_policy=policy.to_dict(), dataset_admission=admission,
                    decision=dict(promote=False, weight=None, reasons=['empty dataset']))
    new_model = json.loads(Path(new_model_path).read_text(encoding='utf-8'))
    new_recipe = default_recipe(new_model['features'], seed)
    current_path = Path(repo) / current['path'] if current and current.get('path') else None
    data_runs = list((current or {}).get('data_runs') or [])
    notes, mask = [], None
    if current is None:
        mode, spec = 'first', None
    elif current.get('recipe') and data_runs:
        mode, spec = 'retrain', dict(recipe=current['recipe'], data_runs=data_runs)
        notes.append('current recipe retrained per fold on its original runs: no in-sample advantage')
    else:
        mode, spec = 'unseen', dict(scorer=LearnedScorer(json.loads(current_path.read_text(encoding='utf-8'))))
    cv = cross_validate(rows, new_recipe, spec, repo=repo, model_factory=model_factory)
    seen_courses = {course_of(run, repo) for run in data_runs}
    seen = np.array([cv['course'][r['run']] in seen_courses for r in rows])
    groups = len({r['group'] for r in rows})
    unseen = len({r['group'] for r, s in zip(rows, seen) if not s})
    if mode == 'unseen':
        if data_runs and unseen >= MIN_UNSEEN:
            mask = ~seen
            notes.append(f'no current recipe: gated only on the {unseen} decisions from courses the current model never saw')
        else:
            mode, cv['current'] = 'heuristic', None
            notes.append(f'no current recipe and {unseen} decisions on courses the current model never saw '
                         f'(< {MIN_UNSEEN}' + ('' if data_runs else '; its training runs are unknown')
                         + '): compared with the heuristic only')
    report = compare(rows, cv, mask)
    report.update(mode=mode, notes=notes, dataset=str(dataset), rows=len(rows), new_model=str(new_model_path),
                  new_sha256=sha256(new_model_path), new_recipe=new_recipe,
                  current_model=str(current_path) if current_path else None,
                  current_sha256=sha256(current_path) if current_path and current_path.exists() else None,
                  current_seen_fraction=round(1 - unseen / max(groups, 1), 4) if current else None,
                  pose_policy=policy.to_dict(), dataset_admission=admission)
    report['decision'] = decide(report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--new', type=Path, required=True)
    parser.add_argument('--current', type=Path, help='JSON file holding the promoted model\'s manifest entry')
    parser.add_argument('--out', type=Path)
    add_pose_policy_arguments(parser)
    args = parser.parse_args(argv)
    current = json.loads(args.current.read_text(encoding='utf-8')) if args.current else None
    policy = policy_from_args(args)
    status = 0
    try:
        report = gate(args.dataset, args.new, current, pose_policy=policy)
    except DatasetRejected as exc:  # malformed dataset file: rejected whole, never promotable
        report, status = dict(dataset=str(args.dataset), error=f'rejected dataset: {exc}', error_kind='dataset',
                              pose_policy=policy.to_dict(),
                              decision=dict(promote=False, weight=None, reasons=['rejected dataset'])), 2
    except Exception as exc:  # model file, CV or evaluation failure: not a dataset rejection; still fail closed
        report, status = dict(dataset=str(args.dataset), error=f'gate evaluation failed: {type(exc).__name__}: {exc}',
                              error_kind='evaluation', pose_policy=policy.to_dict(),
                              decision=dict(promote=False, weight=None, reasons=['gate evaluation failed'])), 3
    text = json.dumps(report, indent=2)
    if args.out:  # also for empty or rejected datasets, so exclusions stay reviewable
        args.out.write_text(text + '\n', encoding='utf-8')
    print(json.dumps(report['decision'], indent=2))
    return status


if __name__ == '__main__':
    raise SystemExit(main())
