"""Learned lane-corridor re-rank: exact weight-0 identity, gates, fallback, data parity."""

import gzip
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / 'learning'))
import observed_navigation  # noqa: E402
from lane_corridor_policy import CORRIDOR_FEATURES, corridor_feature_rows, propose_lane_corridor  # noqa: E402
from navigation_decisions import outcome_candidates  # noqa: E402
from build_dataset import build_corridor_rows  # noqa: E402
from learned_scorer import LearnedScorer, SCHEMA  # noqa: E402


def stripe(y, start=2., end=12., step=.2):
    x = np.arange(start, end+step/2, step)
    return np.column_stack((x, np.full_like(x, y)))


# Three parallel lines: two accepted corridors (below and above the middle line).
POINTS = np.vstack((stripe(-3), stripe(0), stripe(3)))
ROBOT, YAW, GOAL = [0., -1.2], 0., [20., -1.]
ORIGIN, RES, W, H = [-5., -10.], .1, 300, 200


def costmap(barrier_y=None):
    costs = [0]*(W*H)
    if barrier_y is not None:  # an observed obstacle row inside one corridor
        iy = int((barrier_y-ORIGIN[1])/RES)
        for ix in range(int((4.-ORIGIN[0])/RES), int((9.-ORIGIN[0])/RES)):
            costs[iy*W+ix] = 100
    return (ORIGIN, RES, W, H, costs)


class PreferOther:
    """Stub corridor scorer: predicts high regret for the heuristic's pick."""
    decision = 'corridor'

    def score(self, rows):
        return [10. if row['score_rank'] == 0 else 0. for row in rows]


class Broken:
    decision = 'corridor'

    def score(self, rows):
        raise RuntimeError('boom')


def propose(**kwargs):
    diagnostics = {}
    result = propose_lane_corridor(POINTS, ROBOT, YAW, GOAL, min_width=1.2, lookahead=7.,
                                   diagnostics=diagnostics, **kwargs)
    return result, diagnostics


class CorridorRerankTests(unittest.TestCase):
    def test_scene_has_two_accepted_corridors(self):
        _, diagnostics = propose()
        self.assertEqual(len(diagnostics['accepted_candidates']), 2)

    def test_weight_zero_or_no_scorer_is_exactly_the_heuristic(self):
        baseline = propose()
        for kwargs in (dict(corridor_scorer=PreferOther(), corridor_weight=0.),
                       dict(corridor_scorer=None, corridor_weight=16.)):
            self.assertEqual(json.dumps(propose(**kwargs), sort_keys=True),
                             json.dumps(baseline, sort_keys=True))

    def test_rerank_only_switches_between_accepted_proposals(self):
        (base, base_diag), (hook, diag) = propose(), propose(corridor_scorer=PreferOther(), corridor_weight=1.,
                                                            costmap=costmap())
        accepted = [c['pair'] for c in base_diag['accepted_candidates']]
        self.assertNotEqual(hook['entry'], base['entry'])
        self.assertIn(diag['selected_pair'], accepted)
        self.assertNotEqual(diag['selected_pair'], base_diag['selected_pair'])
        self.assertEqual(diag['corridor_rerank']['status'], 'applied')
        self.assertTrue(diag['corridor_rerank']['changed'])
        self.assertEqual(diag['top_candidate_basis'], 'learned_rerank')
        self.assertTrue(hook['diagnostics']['learned_rerank']['changed'])
        # The same gates rejected the same pairs.
        self.assertEqual(diag['pair_rejection_counts'], base_diag['pair_rejection_counts'])
        # Logged per candidate so outcomes.jsonl can show the re-rank.
        logged = [c['features'] for c in outcome_candidates(dict(lane_detection=diag), None)]
        self.assertTrue(all('learned_regret_m' in f and 'rerank_score' in f for f in logged))

    def test_scorer_failure_or_wrong_model_falls_back_with_flag(self):
        base, _ = propose()
        route_model = LearnedScorer(dict(schema=SCHEMA, features=['score'], fill_value=-1., base=0.,
                                         learning_rate=.1, trees=[]))
        self.assertEqual(route_model.decision, 'route')
        for scorer in (Broken(), route_model):
            result, diagnostics = propose(corridor_scorer=scorer, corridor_weight=1.)
            self.assertEqual(result['entry'], base['entry'])
            self.assertEqual(diagnostics['corridor_rerank']['status'], 'error')
            self.assertFalse(result['diagnostics']['learned_rerank']['changed'])

    def test_costmap_features_see_an_observed_obstacle_in_one_corridor(self):
        _, diagnostics = propose()
        rows = corridor_feature_rows(diagnostics['accepted_candidates'], ROBOT, YAW, GOAL, costmap(-1.5))
        lower = min(range(2), key=lambda k: diagnostics['accepted_candidates'][k]['entry'][1])
        self.assertLess(rows[lower]['ahead_lethal_distance_m'], 8.)
        self.assertEqual(rows[1-lower]['ahead_lethal_distance_m'], 8.)
        self.assertTrue(set(rows[0]) <= set(CORRIDOR_FEATURES))

    def test_planner_never_receives_corridor_options(self):
        received = {}

        def fake_select_local_goal(*args, **kwargs):
            received.update(kwargs, target=list(args[7]))
            return None

        original = observed_navigation.select_local_goal
        observed_navigation.select_local_goal = fake_select_local_goal
        try:
            args = costmap() + (ROBOT, YAW, GOAL, POINTS)
            options = dict(lookahead=7., goal_footprint=None)
            observed_navigation.plan_observed_navigation(*args, **options)
            base_target = received['target']
            received.clear()
            diagnostics = {}
            observed_navigation.plan_observed_navigation(*args, guidance_diagnostics=diagnostics,
                corridor_scorer=PreferOther(), corridor_weight=1., **options)
        finally:
            observed_navigation.select_local_goal = original
        self.assertNotIn('corridor_scorer', received)
        self.assertNotIn('corridor_weight', received)
        self.assertNotEqual(received['target'], base_target)
        self.assertTrue(diagnostics['lane_detection']['corridor_rerank']['changed'])

    def test_dataset_rows_match_runtime_features(self):
        cmap = costmap(-1.5)
        diagnostics = {}
        observed_navigation.select_observed_guidance(POINTS, ROBOT, YAW, GOAL, lookahead=7.,
                                                     guidance_diagnostics=diagnostics)
        candidates = outcome_candidates(diagnostics, None)
        runtime = corridor_feature_rows(diagnostics['lane_detection']['accepted_candidates'],
                                        ROBOT, YAW, GOAL, cmap)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            outcome = dict(schema_version=2, index=3, destination_index=0, candidates=candidates,
                           plan=dict(source='observed_lane_corridor'))
            label = dict(index=3, stamp_s=1., candidates=[dict(source=c['source'], endpoint=c['endpoint'][:2],
                         endpoint_cell='free', teacher_cost_m=10.+k) for k, c in enumerate(candidates)])
            (tmp/'outcomes.jsonl').write_text(json.dumps(outcome)+'\n')
            (tmp/'labels.jsonl').write_text(json.dumps(label)+'\n')
            snapshot = dict(schema_version=1, input=dict(origin=cmap[0], resolution=RES, width=W, height=H,
                            costs=cmap[4], robot_xy=ROBOT, robot_yaw=YAW, destination=GOAL), metadata={})
            with gzip.open(tmp/'00003.json.gz', 'wt') as stream:
                json.dump(snapshot, stream)
            rows, stats = build_corridor_rows(tmp/'outcomes.jsonl', tmp/'labels.jsonl', 'run')
        self.assertEqual((stats['groups'], len(rows)), (1, 2))
        self.assertEqual([r['heuristic_choice'] for r in rows], [True, False])
        self.assertEqual([r['regret_m'] for r in rows], [0., 1.])
        for row in rows:
            k = min(range(2), key=lambda j: np.hypot(*np.subtract(
                diagnostics['lane_detection']['accepted_candidates'][j]['entry'], row['endpoint'])))
            self.assertEqual(set(row['features']), set(runtime[k]))
            for name, value in row['features'].items():
                self.assertAlmostEqual(value, runtime[k][name], delta=1e-3, msg=name)


if __name__ == '__main__':
    unittest.main()
