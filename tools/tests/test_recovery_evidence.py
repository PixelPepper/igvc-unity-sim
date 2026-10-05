"""Failed-backup evidence: real search branches, spawn transport, input binding and bounded JSON."""
import array
from concurrent.futures import ProcessPoolExecutor
from functools import partial
import gzip
import json
import math
import multiprocessing
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from observed_navigation import plan_observed_navigation  # noqa: E402
import recovery_evidence  # noqa: E402
from recovery_evidence import (describe_search_inputs, diagnose_backup_recovery, json_safe,  # noqa: E402
                               write_recovery_capture)
from recovery_policy import select_backup_recovery  # noqa: E402

SIZE = 160
FOOTPRINT = (-1.12, .62, -.52, .52)
OPTIONS = {'robot_radius': .5, 'minimum_turn_radius': 1.25, 'lookahead': 4.}
GUIDANCE = partial(plan_observed_navigation, lane_points=[], heading_hint=None)


def grid(*walls):
    costs = array.array('b', [0]*(SIZE*SIZE))  # the ROS OccupancyGrid.data type
    for x1, x2, y1, y2, value in walls:
        for y in range(y1, y2):
            costs[y*SIZE+x1:y*SIZE+x2] = array.array('b', [value]*(x2-x1))
    return costs


CORNER = (60, 63, 0, 60, 100)  # existing corner case: 0.6 m fails, 0.9 m escapes


def search_args(costs, robot=(5., 3.5), yaw=0.):
    return ((0, 0), .1, SIZE, SIZE, costs, robot, yaw, (9., 8.))


def kwargs(**overrides):
    return {'goal_footprint': FOOTPRINT, 'forward_planner': GUIDANCE, 'forward_options': OPTIONS, **overrides}


def comparable(escape):
    """Motion result fields; elapsed time and planner timing are excluded."""
    if escape is None:
        return None
    plan = escape['forward_plan']
    return (escape['distance_m'], escape['backup_pose'], plan['local_goal'], plan['path'],
            escape['diagnostics']['attempts'], escape['diagnostics']['original_trap_progress_m'])


def traced(costs, **overrides):
    trace = []
    result = select_backup_recovery(*search_args(costs), trace=trace, **kwargs(**overrides))
    return result, trace


class RecoveryEvidenceTest(unittest.TestCase):
    def test_trace_never_changes_success_or_failure_results(self):
        cases = {'escape at 0.9 m': (grid(CORNER), {}),
                 'rear blocked': (grid((37, 38, 0, 160, 100)), {}),
                 'no proposal': (grid(), {'forward_planner': Mock(return_value=None)})}
        for name, (costs, overrides) in cases.items():
            with self.subTest(name):
                plain = select_backup_recovery(*search_args(costs), **kwargs(**overrides))
                result, trace = traced(costs, **overrides)
                self.assertEqual(comparable(result), comparable(plain))
                self.assertTrue(trace)
        result, trace = traced(grid(CORNER))
        self.assertEqual(result['distance_m'], .9)
        self.assertEqual([(r['stage'], r.get('distance_m')) for r in trace],
                         [('inputs_valid', None), ('candidate', .6), ('candidate', .9)])
        self.assertNotEqual(trace[1]['verdict'], 'accepted')
        self.assertEqual(trace[2]['verdict'], 'accepted')
        self.assertEqual(trace[0]['candidates_m'], [.6, .9, 1.2, 1.5, 1.8])

    def test_input_validation_stages(self):
        costs = grid()
        cases = {'nonfinite yaw': (dict(), dict(yaw=math.nan), 'invalid_inputs'),
                 'distance beyond limit': (dict(distances=(1.9,)), {}, 'no_candidate_within_max_backup_distance'),
                 'continuation grid size': (dict(continuation_costs=[0]), {}, 'continuation_grid_size'),
                 'malformed trap region': (dict(trap_regions=[{'center': (1., 1.), 'radius': 9.}]), {},
                                           'exception')}
        for name, (overrides, pose, reason) in cases.items():
            with self.subTest(name):
                trace = []
                self.assertIsNone(select_backup_recovery(*search_args(costs, **pose), trace=trace,
                                                         **kwargs(**overrides)))
                self.assertEqual([(r['stage'], r['reason']) for r in trace], [('input_validation', reason)])
        trace = []
        self.assertIsNone(select_backup_recovery((0, 0), .1, 0, 0, [], (5., 3.5), 0., (9., 8.), trace=trace,
                                                 **kwargs()))
        self.assertEqual(trace[0]['reason'], 'invalid_inputs')

    def test_initial_clearance_names_the_failed_check(self):
        cases = {'unknown under the centre': ((50, 51, 35, 36, -1), 'center_cell_unknown'),
                 'lethal under the centre': ((50, 51, 35, 36, 100), 'center_cell_lethal_or_inscribed'),
                 'hazard under the body only': ((50, 51, 39, 40, 100), 'body_rectangle_blocked')}
        for name, (wall, reason) in cases.items():
            with self.subTest(name):
                forward = Mock(return_value=None)
                result, trace = traced(grid(wall), forward_planner=forward)
                self.assertIsNone(result)
                self.assertEqual([(r['stage'], r.get('reason')) for r in trace],
                                 [('inputs_valid', None), ('initial_clearance', reason)])
                forward.assert_not_called()
        trace = []
        self.assertIsNone(select_backup_recovery(*search_args(grid(), robot=(-1., 3.5)), trace=trace, **kwargs()))
        self.assertEqual(trace[-1]['reason'], 'center_outside_grid')

    def test_blocked_or_unknown_rear_sweep_reports_distance_and_skipped_candidates(self):
        for value in (-1, 100):
            with self.subTest(value=value):
                forward = Mock(return_value=None)
                result, trace = traced(grid((37, 38, 0, 160, value)), forward_planner=forward)
                self.assertIsNone(result)
                rear = trace[-1]
                self.assertEqual((rear['stage'], rear['reason'], rear['candidate_m']),
                                 ('rear_sweep_blocked', 'body_rectangle_blocked', .6))
                self.assertEqual(rear['unattempted_candidates_m'], [.6, .9, 1.2, 1.5, 1.8])
                self.assertLess(rear['blocked_at_m'], .6+1e-9)
                forward.assert_not_called()
        # A farther blocked sweep is reported after the earlier candidate was actually searched.
        forward = Mock(return_value=None)
        result, trace = traced(grid((30, 31, 0, 160, 100)), forward_planner=forward)
        self.assertEqual([r['stage'] for r in trace][-2:], ['candidate', 'rear_sweep_blocked'])
        self.assertEqual((trace[-2]['distance_m'], trace[-1]['candidate_m']), (.6, .9))
        self.assertEqual(forward.call_count, 1)

    def test_no_proposal_and_rejected_continuations_report_each_attempt_and_budget(self):
        result, trace = traced(grid(), forward_planner=Mock(return_value=None))
        self.assertIsNone(result)
        candidates = [r for r in trace if r['stage'] == 'candidate']
        self.assertEqual([r['distance_m'] for r in candidates], [.6, .9, 1.2, 1.5, 1.8])
        self.assertEqual({r['verdict'] for r in candidates}, {'no_forward_proposal'})
        self.assertEqual(sum(r['charged_expansions'] for r in candidates), trace[-1]['charged_expansions'])
        self.assertEqual((trace[-1]['stage'], trace[-1]['attempted_m']),
                         ('search_ended_without_escape', [.6, .9, 1.2, 1.5, 1.8]))

        def short(*args, **settings):
            return {'local_goal': (args[5][0]+.5, args[5][1]), 'path': [args[5], (args[5][0]+.5, args[5][1])],
                    'diagnostics': {'expanded_cells': 7, 'local_path_length': .5,
                                    'checked_continuation_length': 2.}}
        result, trace = traced(grid(), forward_planner=short)
        self.assertIsNone(result)
        candidates = [r for r in trace if r['stage'] == 'candidate']
        self.assertEqual({r['verdict'] for r in candidates}, {'local_path_below_1m'})
        self.assertEqual({r['charged_expansions'] for r in candidates}, {7})

    def test_time_and_expansion_exhaustion(self):
        result, trace = traced(grid(), forward_planner=Mock(return_value=None), max_search_seconds=1e-9)
        self.assertIsNone(result)
        self.assertEqual((trace[-2]['stage'], trace[-2]['reason']), ('budget_exhausted', 'time'))
        self.assertEqual(trace[-1]['attempted_m'], [])

        def greedy(*args, **settings):
            return {'local_goal': (0., 0.), 'path': [], 'diagnostics': {'expanded_cells': 10**6}}
        result, trace = traced(grid(), forward_planner=greedy, max_expansions=1)
        self.assertIsNone(result)
        exhausted = [r for r in trace if r['stage'] == 'budget_exhausted']
        self.assertEqual((exhausted[0]['reason'], exhausted[0]['before_candidate_m']), ('expansions', .9))
        self.assertEqual(trace[-1]['charged_expansions'], 1)

    def test_spawn_transport_binds_trace_to_the_received_inputs(self):
        cases = {'escape': (grid(CORNER), 'escape', 'candidate'),
                 'rear blocked': (grid((37, 38, 0, 160, -1)), 'none', 'rear_sweep_blocked')}
        with ProcessPoolExecutor(max_workers=1, mp_context=multiprocessing.get_context('spawn')) as pool:
            for name, (costs, outcome, stage) in cases.items():
                with self.subTest(name):
                    submitted = describe_search_inputs(search_args(costs), kwargs())['digest']
                    escape, evidence = pool.submit(diagnose_backup_recovery, *search_args(costs),
                                                   **kwargs()).result(timeout=20.)
                    direct = select_backup_recovery(*search_args(costs), **kwargs())
                    self.assertEqual(comparable(escape), comparable(direct))
                    self.assertEqual((evidence['result'], evidence['returned_stage']), (outcome, stage))
                    self.assertEqual(evidence['input_binding']['digest'], submitted)
                    json.dumps(evidence, allow_nan=False)
            # Any change to a search input changes the digest.
            changed = grid(CORNER)
            changed[0] = 1
            self.assertNotEqual(describe_search_inputs(search_args(changed), kwargs())['digest'],
                                describe_search_inputs(search_args(grid(CORNER)), kwargs())['digest'])
            self.assertNotEqual(describe_search_inputs(search_args(grid()), kwargs(max_expansions=2))['digest'],
                                describe_search_inputs(search_args(grid()), kwargs())['digest'])

    def test_capture_reproduces_the_exact_search_and_its_trace(self):
        costs = grid((37, 38, 0, 160, -1), (100, 101, 5, 6, 100))
        context = {'grid_stamp_ns': 12, 'odom_frame': 'odom', 'grid_age_wall_s': math.inf}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'recovery-00149.json.gz'
            digest, size = write_recovery_capture(path, search_args(costs), kwargs(), context)
            with self.assertRaises(FileExistsError):  # exclusive: never overwrites a capture
                write_recovery_capture(path, search_args(costs), kwargs(), context)
            payload = json.loads(gzip.decompress(path.read_bytes()))
        self.assertEqual(payload['context']['grid_age_wall_s'], {'nonfinite': 'inf'})
        self.assertEqual(payload['forward_planner']['function'], 'observed_navigation.plan_observed_navigation')
        replay_kwargs = {name: payload['arguments'][name] for name in payload['arguments']
                         if name not in ('origin_xy', 'resolution', 'width', 'height', 'costs', 'robot_xy',
                                         'robot_yaw', 'destination_xy')}
        replay_kwargs['forward_planner'] = partial(plan_observed_navigation, **payload['forward_planner']['keywords'])
        replay_args = tuple(payload['arguments'][name] for name in (
            'origin_xy', 'resolution', 'width', 'height', 'costs', 'robot_xy', 'robot_yaw', 'destination_xy'))
        self.assertEqual(describe_search_inputs(replay_args, replay_kwargs)['digest'], digest)
        self.assertEqual(digest, describe_search_inputs(search_args(costs), kwargs())['digest'])
        original = diagnose_backup_recovery(*search_args(costs), **kwargs())[1]
        replayed = diagnose_backup_recovery(*replay_args, **replay_kwargs)[1]
        strip = [{k: v for k, v in r.items() if k != 'elapsed_s'} for r in original['trace']]
        self.assertEqual([{k: v for k, v in r.items() if k != 'elapsed_s'} for r in replayed['trace']], strip)
        self.assertEqual(payload['arguments']['distances'], [.6, .9, 1.2, 1.5, 1.8])
        self.assertGreater(size, SIZE*SIZE)

    def test_json_safety_and_size_bounds(self):
        self.assertEqual(json_safe([math.nan, -math.inf, 1.5]), [{'nonfinite': 'nan'}, {'nonfinite': '-inf'}, 1.5])
        long = json_safe(list(range(1000)))
        self.assertEqual((len(long), long[-1]), (25, {'<omitted_items>': 976}))
        self.assertTrue(json_safe('x'*1000).endswith('<truncated>'))
        self.assertEqual(json_safe(object()), '<object>')
        nested = json_safe({'a': {'b': {'c': {'d': {'e': {'f': {'g': {'h': 1}}}}}}}})
        self.assertIn('<depth_limit>', json.dumps(nested))

        def planner(*args, **settings):
            return {'local_goal': (0., 0.), 'path': [], 'diagnostics': {'expanded_cells': 1,
                                                                         'local_path_length': math.nan}}
        with patch.object(recovery_evidence, 'MAX_EVIDENCE_BYTES', 400):
            escape, evidence = diagnose_backup_recovery(*search_args(grid()), **kwargs(forward_planner=planner))
        self.assertIsNone(escape)
        text = json.dumps(evidence, allow_nan=False)
        self.assertIn('trace_detail_dropped_for_size', evidence)
        self.assertEqual(evidence['input_binding']['inputs_dropped_for_size'], True)
        self.assertEqual(evidence['trace'][-1]['stage'], 'search_ended_without_escape')
        self.assertLess(len(text), 4000)

    def test_unbindable_inputs_are_reported_and_the_search_still_runs(self):
        with self.assertRaises(TypeError):  # the search itself rejects unknown keywords, as before
            select_backup_recovery(*search_args(grid()), unexpected=1, **kwargs())
        with patch.object(recovery_evidence, 'describe_search_inputs', side_effect=RuntimeError('boom')):
            escape, evidence = diagnose_backup_recovery(*search_args(grid(CORNER)), **kwargs())
        self.assertEqual(escape['distance_m'], .9)
        self.assertEqual((evidence['input_binding']['digest'], evidence['input_binding']['error']),
                         (None, 'RuntimeError: boom'))


if __name__ == '__main__':
    unittest.main()
