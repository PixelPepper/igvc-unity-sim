"""Route alternatives: logged side options never change the chosen plan."""

import json
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sensor_route_policy
from sensor_route_policy import select_local_goal
from navigation_decisions import outcome_candidates

FOOTPRINT = (-1.12, .62, -.52, .52)
ALT_KEYS = ('route_alternatives', 'route_alternative_search', 'route_features')
W, H, R = 140, 80, .1


def barrel_world(barrel=(6.5, 4.1), radius=.45):
    costs = [0]*(W*H)
    for y in range(H):
        for x in range(W):
            if barrel and math.hypot((x+.5)*R-barrel[0], (y+.5)*R-barrel[1]) <= radius:
                costs[y*W+x] = 100
    return costs


def plan(costs, **options):
    settings = dict(robot_radius=.5, forward_only=True, goal_footprint=FOOTPRINT,
        minimum_turn_radius=.65, lookahead=7., max_path_length=14., min_progress=.1,
        min_goal_distance=.4, continuation_reserve=1., max_expansions=20000,
        alternative_search_fraction=1.)
    settings.update(options)
    return select_local_goal((0., 0.), R, W, H, costs, (2., 4.), 0., (13., 4.), **settings)


def without_alternatives(result):
    result = json.loads(json.dumps(result))
    for key in ALT_KEYS:
        result['diagnostics'].pop(key, None)
    return result


def body_clear(test, result, costs):
    """Independent check: sampled body points of every pose avoid hazards."""
    xmin, xmax, ymin, ymax = FOOTPRINT
    for (x, y), yaw in zip(result['path'], result['path_yaws']):
        for i in range(8):
            for j in range(6):
                bx, by = xmin+(xmax-xmin)*i/7, ymin+(ymax-ymin)*j/5
                px, py = x+math.cos(yaw)*bx-math.sin(yaw)*by, y+math.sin(yaw)*bx+math.cos(yaw)*by
                value = costs[math.floor(py/R)*W+math.floor(px/R)]
                test.assertTrue(0 <= value < 100, (x, y, yaw))


class RouteAlternativeTests(unittest.TestCase):
    def setUp(self):
        # Enough side-pass budget for this small, cheap synthetic search.
        patcher = patch.object(sensor_route_policy, '_MIN_SIDE_EXPANSIONS', 80)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_alternatives_never_change_the_chosen_plan(self):
        for costs in (barrel_world(), barrel_world(None), barrel_world((5., 3.5), .8)):
            baseline = plan(costs, route_alternatives=0)
            logged = plan(costs, route_alternatives=4)
            self.assertNotIn('route_alternatives', baseline['diagnostics'])
            self.assertEqual(without_alternatives(logged), without_alternatives(baseline))
            # Deterministic (count-bounded) logging for identical inputs.
            self.assertEqual(plan(costs)['diagnostics']['route_alternatives'],
                             logged['diagnostics']['route_alternatives'])

    def test_barrel_alternative_is_on_the_other_side_and_admissible(self):
        costs = barrel_world()
        result = plan(costs)
        chosen = result['diagnostics']['route_features']
        alternatives = result['diagnostics']['route_alternatives']
        self.assertTrue(alternatives)
        other = alternatives[0]
        self.assertEqual(other['distinct_by'], 'hazard_side')
        self.assertGreaterEqual(other['features']['hazard_cells_vs_chosen'], 3)
        # Chosen and alternative straddle the barrel centre line (y = 4.1).
        self.assertLess((result['path'][-1][1]-4.1)*(other['endpoint'][1]-4.1), 0)
        self.assertNotEqual(chosen['side_sign'], other['features']['side_sign'])
        self.assertEqual(set(other['features']), set(sensor_route_policy.ROUTE_FEATURE_KEYS))
        # Promote it through the hook: the resulting full path must be clear.
        switched = plan(costs, learned_scorer=lambda rows: [1.]+[0.]*(len(rows)-1), learned_weight=10.)
        self.assertEqual(switched['diagnostics']['learned_rerank']['chosen'], 1)
        self.assertEqual(list(switched['diagnostics']['endpoint']), other['endpoint'])
        self.assertEqual(list(switched['local_goal']), other['local_goal'])
        self.assertEqual(switched['diagnostics']['heuristic_endpoint'], result['diagnostics']['endpoint'])
        body_clear(self, switched, costs)
        body_clear(self, result, costs)

    def test_zero_weight_never_calls_scorer_and_failures_keep_heuristic(self):
        costs = barrel_world()
        baseline = plan(costs)
        def forbidden(rows):
            raise AssertionError('scorer called at weight 0')
        self.assertEqual(plan(costs, learned_scorer=forbidden, learned_weight=0.), baseline)
        for broken in (lambda rows: [0.], lambda rows: [float('nan')]*len(rows),
                       lambda rows: (_ for _ in ()).throw(ValueError('bad'))):
            result = plan(costs, learned_scorer=broken, learned_weight=5.)
            self.assertIn('error', result['diagnostics']['learned_rerank'])
            self.assertEqual(result['local_goal'], baseline['local_goal'])
        # A scorer agreeing with the heuristic keeps the choice exactly.
        kept = plan(costs, learned_scorer=lambda rows: [0.]*len(rows), learned_weight=5.)
        self.assertEqual(kept['path'], baseline['path'])

    def test_invalid_options_fail_closed(self):
        costs = barrel_world()
        for options in (dict(route_alternatives=9), dict(route_alternatives=-1),
                        dict(route_alternatives=True), dict(learned_weight=-1.),
                        dict(learned_weight=11.), dict(learned_weight=float('nan')),
                        dict(learned_weight=1.), dict(alternative_search_fraction=1.5),
                        dict(alternative_max_seconds=0.),
                        dict(learned_weight=1., learned_scorer=len, route_alternatives=0)):
            with self.subTest(options=options):
                self.assertIsNone(plan(costs, **options))

    def test_outcome_candidates_carry_route_alternatives(self):
        costs = barrel_world()
        result = plan(costs)
        diagnostics = dict(lane_detection=dict(accepted_candidates=[
            dict(entry=[12., 4.], direction=[1., 0.], score=1., confidence=.5)]))
        candidates = outcome_candidates(diagnostics, result)
        sources = [c['source'] for c in candidates]
        self.assertEqual(sources[:2], ['corridor', 'grid'])
        self.assertEqual(sources[2:], ['route_alt']*len(result['diagnostics']['route_alternatives']))
        grid, alt = candidates[1], candidates[2]
        for entry in (grid, alt):
            self.assertIn('min_lethal_clearance_m', entry['features'])
            self.assertIn('corridor_entry_distance_m', entry['features'])
        self.assertEqual(alt['distinct_by'], 'hazard_side')
        self.assertEqual(alt['path_length_m'], result['diagnostics']['route_alternatives'][0]['path_length'])
        text = json.dumps(candidates)
        # 'route_alt' is the sanctioned source label; nothing else world-like.
        for word in ('course', 'world', 'centerline', 'obstacle'):
            self.assertNotIn(word, text)
        self.assertLessEqual(len(outcome_candidates(diagnostics, result, limit=2)), 2)


if __name__ == '__main__':
    unittest.main()
