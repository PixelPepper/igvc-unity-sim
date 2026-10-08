"""Null planner results retain only a bounded executed-stage record."""
from collections import OrderedDict
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from observed_navigation import plan_observed_navigation, evaluate_observed_navigation
from sensor_route_policy import (select_local_goal, FORWARD_REJECTION_STAGES,
                                 FORWARD_REJECTION_VERSION)

KEYS = {'version', 'stage', 'evidence', 'route_returned', 'forward_search_evaluated',
        'expanded_states', 'expansion_limit', 'budget_exhausted',
        'time_budget_exhausted', 'search_exhausted'}
FOOTPRINT = (-1.12, .62, -.52, .52)
OPTIONS = dict(robot_radius=.3, forward_only=True, minimum_turn_radius=.65)
BROAD = {'guidance': 'broad_gps', 'target': [6.1, 6.1], 'yaw': None}


def open_grid():
    return [0]*14400


def wall_grid():
    # A full-height lethal wall between the robot and its destination.
    costs = open_grid()
    for y in range(120):
        for x in range(36, 39):
            costs[y*120+x] = 100
    return costs


def plan(costs, robot=(3.1, 6.1), destination=(9.1, 6.1), **options):
    return select_local_goal((0., 0.), .1, 120, 120, costs, robot, 0., destination,
                             **{**OPTIONS, **options})


def wrapped(result):
    """A direct plan as returned by the wrapper for BROAD guidance."""
    result['diagnostics'].update(guidance='broad_gps', guidance_target=[6.1, 6.1],
                                 guidance_yaw=None)
    return result


class ForwardRejectionEvidenceTests(unittest.TestCase):
    def evidence(self, costs, **options):
        """Return (record, result) and require the sink not to change the result."""
        record = {}
        result = plan(costs, rejection_diagnostics=record, **options)
        self.assertEqual(result, plan(costs, **options))
        self.assertEqual(set(record), KEYS)
        self.assertEqual(record['version'], FORWARD_REJECTION_VERSION)
        self.assertIn(record['stage'], FORWARD_REJECTION_STAGES)
        self.assertEqual(record['evidence'], 'executed_stage_not_causal_proof')
        for value in record.values():
            self.assertIn(type(value), (type(None), bool, int, str))
        return record, result

    def assert_stage_only(self, record, stage):
        self.assertEqual(record['stage'], stage)
        self.assertFalse(record['route_returned'])
        self.assertFalse(record['forward_search_evaluated'])
        for key in ('expanded_states', 'expansion_limit', 'budget_exhausted',
                    'time_budget_exhausted', 'search_exhausted'):
            self.assertIsNone(record[key])

    def test_early_rejections_are_distinct_executed_stages(self):
        blocked = open_grid()
        blocked[61*120+31] = 100
        cases = (
            ('invalid_options_or_input', open_grid(), {'max_expansions': 0}),
            ('invalid_options_or_input', [0]*10, {}),
            ('start_outside_grid', open_grid(), {'robot': (-1., 6.1)}),
            ('start_clearance_rejected', blocked, {}),
            ('progress_target_too_close', open_grid(), {'destination': (3.2, 6.1)}),
        )
        for stage, costs, options in cases:
            for forward in (True, False):
                with self.subTest(stage=stage, forward=forward):
                    record, result = self.evidence(costs, **{**options, 'forward_only': forward})
                    self.assertIsNone(result)
                    self.assert_stage_only(record, stage)

    def test_starting_body_rejection_is_not_reported_as_search(self):
        costs = open_grid()
        # Behind the axle: outside the start circle, inside the padded body.
        costs[61*120+23] = 100
        self.assertIsNotNone(plan(costs))
        record, result = self.evidence(costs, goal_footprint=FOOTPRINT)
        self.assertIsNone(result)
        self.assert_stage_only(record, 'start_footprint_rejected')

    def test_no_candidate_search_keeps_existing_counters_only(self):
        record, result = self.evidence(wall_grid(), destination=(6.1, 6.1),
                                       min_progress=1., max_expansions=300)
        self.assertIsNone(result)
        self.assertEqual(record['stage'], 'forward_no_admissible_candidate')
        self.assertFalse(record['route_returned'])
        self.assertTrue(record['forward_search_evaluated'])
        self.assertEqual(record['expansion_limit'], 300)
        self.assertTrue(1 <= record['expanded_states'] <= 300)
        self.assertFalse(record['time_budget_exhausted'])
        self.assertEqual(record['budget_exhausted'],
                         record['expanded_states'] >= 300 and not record['search_exhausted'])
        again, _ = self.evidence(wall_grid(), destination=(6.1, 6.1),
                                 min_progress=1., max_expansions=300)
        self.assertEqual(again, record)

    def test_root_only_search_exhausts_queue_without_budget(self):
        # Every primitive exceeds the path length, so only the start is expanded.
        record, result = self.evidence(open_grid(), max_path_length=.1)
        self.assertIsNone(result)
        self.assertEqual(record['stage'], 'forward_no_admissible_candidate')
        self.assertEqual(record['expanded_states'], 1)
        self.assertTrue(record['search_exhausted'])
        self.assertFalse(record['budget_exhausted'])
        self.assertFalse(record['time_budget_exhausted'])

    def test_success_clears_reused_rejection_state(self):
        record = {}
        self.assertIsNone(plan(open_grid(), max_path_length=.1, rejection_diagnostics=record))
        self.assertEqual(record['expanded_states'], 1)
        result = plan(open_grid(), rejection_diagnostics=record)
        self.assertIsNotNone(result)
        self.assertEqual(result, plan(open_grid()))
        self.assertNotIn('forward_rejection', result['diagnostics'])
        self.assertEqual(set(record), KEYS)
        self.assertEqual(record['stage'], 'forward_route_returned')
        self.assertTrue(record['route_returned'])
        self.assertTrue(record['forward_search_evaluated'])
        for key in ('expanded_states', 'expansion_limit', 'budget_exhausted',
                    'time_budget_exhausted', 'search_exhausted'):
            self.assertIsNone(record[key])

    def test_non_forward_search_records_no_rejection(self):
        for costs, destination in ((open_grid(), (9.1, 6.1)), (wall_grid(), (6.1, 6.1))):
            record = {}
            plan(open_grid(), max_path_length=.1, rejection_diagnostics=record)
            result = plan(costs, destination=destination, forward_only=False,
                          rejection_diagnostics=record)
            self.assertEqual(result, plan(costs, destination=destination, forward_only=False))
            self.assertEqual(set(record), KEYS)
            self.assertEqual(record['stage'], 'not_forward_search')
            self.assertIsNone(record['route_returned'])
            self.assertFalse(record['forward_search_evaluated'])
            self.assertIsNone(record['expanded_states'])
            self.assertIsNone(record['search_exhausted'])

    def test_unsupported_sinks_are_ignored(self):
        for costs, options in ((open_grid(), {}), (open_grid(), {'max_expansions': 0}),
                               (wall_grid(), {'destination': (6.1, 6.1), 'min_progress': 1.,
                                              'max_expansions': 300})):
            baseline = plan(costs, **options)
            for sink in ([], OrderedDict(), 'sink', 3, object()):
                with self.subTest(sink=type(sink).__name__, options=options):
                    self.assertEqual(plan(costs, rejection_diagnostics=sink, **options), baseline)
                    if isinstance(sink, (list, dict)):
                        self.assertEqual(len(sink), 0)

    def test_wrapper_retains_detached_null_stage(self):
        options = dict(OPTIONS, min_progress=1., max_expansions=300)
        args = ((0., 0.), .1, 120, 120, wall_grid(), (3.1, 6.1), 0., (6.1, 6.1), [])
        sink, diagnostic = {}, {}
        result = plan_observed_navigation(*args, guidance_diagnostics=diagnostic,
                                          frozen_guidance=BROAD, rejection_diagnostics=sink,
                                          **options)
        self.assertIsNone(result)
        self.assertFalse(diagnostic['route_found'])
        retained = diagnostic['forward_rejection']
        self.assertEqual(retained['stage'], 'forward_no_admissible_candidate')
        self.assertEqual(retained, sink)
        self.assertIsNot(retained, sink)
        sink.clear()
        self.assertEqual(retained['stage'], 'forward_no_admissible_candidate')
        evaluation = evaluate_observed_navigation(*args, frozen_guidance=BROAD, **options)
        self.assertIsNone(evaluation['plan'])
        self.assertEqual(evaluation['diagnostics']['forward_rejection'], retained)
        # Reusing the envelope for a successful plan leaves no stale rejection.
        open_args = args[:4] + (open_grid(),) + args[5:]
        result = plan_observed_navigation(*open_args, guidance_diagnostics=diagnostic,
                                          frozen_guidance=BROAD, **OPTIONS)
        self.assertEqual(result, wrapped(plan(open_grid(), destination=(6.1, 6.1))))
        self.assertTrue(diagnostic['route_found'])
        self.assertEqual(diagnostic['forward_rejection']['stage'], 'forward_route_returned')
        self.assertIsNone(diagnostic['forward_rejection']['expanded_states'])
        self.assertNotIn('forward_rejection', result['diagnostics'])
        self.assertEqual(retained['stage'], 'forward_no_admissible_candidate')

    def test_wrapper_ignores_unsupported_sink(self):
        args = ((0., 0.), .1, 120, 120, open_grid(), (3.1, 6.1), 0., (6.1, 6.1), [])
        diagnostic = {}
        result = plan_observed_navigation(*args, guidance_diagnostics=diagnostic,
                                          frozen_guidance=BROAD, rejection_diagnostics=[],
                                          **dict(OPTIONS, forward_only=False))
        self.assertEqual(result, wrapped(plan(open_grid(), destination=(6.1, 6.1),
                                              forward_only=False)))
        self.assertEqual(diagnostic['forward_rejection']['stage'], 'not_forward_search')


if __name__ == '__main__':
    unittest.main()
