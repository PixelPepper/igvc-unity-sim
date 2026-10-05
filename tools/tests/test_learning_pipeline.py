"""Offline learning pipeline: join, grouped training, JSON export, numpy inference."""

import json
from pathlib import Path
import random
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / 'learning'))
from build_dataset import build_rows, FEATURES
from learned_scorer import LearnedScorer, SCHEMA
from navigation_decisions import ROUTE_FEATURE_NAMES
from sensor_route_policy import ROUTE_FEATURE_KEYS

try:
    import sklearn  # noqa: F401
    HAVE_SKLEARN = True
except ImportError:
    HAVE_SKLEARN = False


def write_jsonl(path, records):
    Path(path).write_text(''.join(json.dumps(r)+'\n' for r in records))


def synthetic_rows(runs=4, decisions=40, seed=1):
    """Teacher prefers larger observed clearance; the heuristic ignores it."""
    rng = random.Random(seed)
    rows = []
    for run in range(runs):
        for index in range(decisions):
            members = []
            for k in range(3):
                clearance = rng.uniform(.2, 2.)
                cost = 10. - 2.*clearance + rng.gauss(0, .05)
                members.append(dict(run=f'r{run}', index=index, group=f'r{run}:{index}', source='grid' if k == 0 else 'route_alt',
                    heuristic_choice=k == 0, features=dict(score=rng.uniform(0, 1), min_lethal_clearance_m=clearance),
                    teacher_cost_m=cost))
            best = min(m['teacher_cost_m'] for m in members)
            for m in members:
                m['regret_m'] = m['teacher_cost_m'] - best
                m['teacher_best'] = m['teacher_cost_m'] == best
            rows += members
    return rows


class LearningPipelineTests(unittest.TestCase):
    def test_feature_names_agree_across_modules(self):
        self.assertEqual(tuple(ROUTE_FEATURE_KEYS), tuple(ROUTE_FEATURE_NAMES))
        self.assertEqual(tuple(FEATURES[:-1]), tuple(ROUTE_FEATURE_KEYS))

    def test_join_uses_route_candidates_and_teacher_targets_only(self):
        outcomes = [
            dict(schema_version=2, index=1, destination_index=0, candidates=[
                dict(source='corridor', endpoint=[3., 0., 0.], features=dict(confidence=.5)),
                dict(source='grid', endpoint=[5., 0.], features=dict(score=1., min_lethal_clearance_m=.4)),
                dict(source='route_alt', endpoint=[5., 2.], distinct_by='hazard_side',
                     features=dict(score=1.5, min_lethal_clearance_m=1.2))]),
            dict(schema_version=2, index=2, candidates=[  # only one route option: no ranking signal
                dict(source='grid', endpoint=[1., 0.], features={})]),
            dict(schema_version=2, index=3, candidates=[  # endpoint mismatch: skipped
                dict(source='grid', endpoint=[1., 0.], features={}),
                dict(source='route_alt', endpoint=[1., 1.], features={})])]
        labels = [
            dict(index=1, candidates=[dict(source='corridor', endpoint=[3., 0.], teacher_cost_m=9.),
                                      dict(source='grid', endpoint=[5., 0.], teacher_cost_m=12.),
                                      dict(source='route_alt', endpoint=[5., 2.], teacher_cost_m=11.)]),
            dict(index=2, candidates=[dict(source='grid', endpoint=[1., 0.], teacher_cost_m=5.)]),
            dict(index=3, candidates=[dict(source='grid', endpoint=[1., 0.], teacher_cost_m=5.),
                                      dict(source='route_alt', endpoint=[9., 9.], teacher_cost_m=4.)])]
        with tempfile.TemporaryDirectory() as directory:
            write_jsonl(Path(directory)/'o.jsonl', outcomes)
            write_jsonl(Path(directory)/'l.jsonl', labels)
            rows, stats = build_rows(Path(directory)/'o.jsonl', Path(directory)/'l.jsonl', 'runA')
        self.assertEqual(stats['mismatched'], 1)
        self.assertEqual(stats['groups'], 1)
        self.assertEqual([r['source'] for r in rows], ['grid', 'route_alt'])
        grid, alt = rows
        # Regret is relative to the best ROUTE candidate (corridor excluded).
        self.assertAlmostEqual(grid['regret_m'], 1.)
        self.assertAlmostEqual(alt['regret_m'], 0.)
        self.assertTrue(alt['teacher_best'] and grid['heuristic_choice'])
        self.assertNotIn('teacher_cost_m', grid['features'])
        self.assertEqual(alt['features'], dict(score=1.5, min_lethal_clearance_m=1.2))

    def test_scorer_rejects_malformed_models_and_fills_missing(self):
        good = dict(schema=SCHEMA, features=['a', 'b'], fill_value=-1., base=.5, learning_rate=.1,
                    trees=[dict(feature=[1, -2, -2], threshold=[0., -2., -2.], left=[1, -1, -1],
                                right=[2, -1, -1], value=[0., -1., 1.])])
        scorer = LearnedScorer(good)
        self.assertEqual(scorer.score([dict(b=1.), dict(b=-3.), dict()]), [.6, .4, .4])
        for broken in (dict(good, schema='x'), dict(good, trees=[dict(good['trees'][0], left=[0, -1, -1])]),
                       dict(good, trees=[dict(good['trees'][0], feature=[5, -2, -2])]),
                       dict(good, base=float('nan'))):
            with self.assertRaises((ValueError, KeyError)):
                LearnedScorer(broken)

    @unittest.skipUnless(HAVE_SKLEARN, 'scikit-learn is an offline-only dependency')
    def test_grouped_training_learns_signal_and_export_matches_sklearn(self):
        import numpy as np
        import train_scorer
        rows = synthetic_rows()
        report = train_scorer.cross_validate(rows, folds=4, n_estimators=60)
        self.assertEqual(report['folds'], 4)
        self.assertGreater(report['model']['top1_model'], report['model']['top1_heuristic'] + .2)
        self.assertLess(report['model']['mean_regret_model_m'], report['model']['mean_regret_heuristic_m'])
        model = train_scorer.make_model(n_estimators=40).fit(train_scorer.matrix(rows),
                                                             np.array([r['regret_m'] for r in rows]))
        exported = json.loads(json.dumps(train_scorer.export(model)))
        X = train_scorer.matrix(rows)
        self.assertLess(np.max(np.abs(LearnedScorer(exported).predict_matrix(X)-model.predict(X))), 1e-9)
        self.assertNotIn('teacher', json.dumps(exported['features']))
        with self.assertRaises(ValueError):
            train_scorer.cross_validate([r for r in rows if r['run'] == 'r0'])


if __name__ == '__main__':
    unittest.main()
