"""Offline replay admission, retained rejection evidence, and experiment isolation."""
import contextlib
import copy
import gzip
import io
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import observed_navigation
from observed_navigation import plan_observed_navigation
import replay_navigation_decision as replay_tool
from replay_navigation_decision import load_snapshot, main, replay, validate_snapshot


def snapshot():
    return {'schema_version': 1, 'metadata': {'odom_stamp_ns': 100, 'input_age_wall_s': .1},
            'input': {'origin': [-5., -5.], 'resolution': .25, 'width': 40, 'height': 40,
                      'costs': [0]*1600, 'robot_xy': [0., 0.], 'robot_yaw': 0.,
                      'destination': [4., 0.], 'lane_points': [], 'heading_hint': None,
                      'planner_options': {'robot_radius': .5, 'lookahead': 2., 'max_path_length': 6.,
                                          'min_progress': .1, 'max_expansions': 1000}}}


class NavigationReplayTests(unittest.TestCase):
    def test_clearance_preference_snapshot_replays_with_bounded_options(self):
        source = snapshot()
        options = source['input']['planner_options']
        options.update(forward_only=True,goal_footprint=[-1.12,.62,-.52,.52],
                       body_clearance_weight=3.,body_clearance_scale=.3)
        self.assertEqual(replay(source)['status'],'route_found')
        for key,value in (('body_clearance_weight',-1),('body_clearance_weight',11),
                          ('body_clearance_weight',float('nan')),
                          ('body_clearance_scale',0),('body_clearance_scale',1.1)):
            invalid = copy.deepcopy(source)
            invalid['input']['planner_options'][key] = value
            with self.subTest(key=key,value=value), self.assertRaises(ValueError):
                validate_snapshot(invalid)
        options['body_clearance_weight'] = 0
        validate_snapshot(source)

    def test_preserved_recovery_target_is_replayed_and_schema_bounded(self):
        source=snapshot()
        source['input']['frozen_guidance']={
            'guidance':'broad_gps','target':[3.,0.],'yaw':None}
        report=replay(source)
        self.assertEqual(report['diagnostics']['guidance_target'],[3.,0.])
        source['input']['frozen_guidance']['route']=[]
        with self.assertRaises(ValueError):validate_snapshot(source)

    def test_fixed_entrance_policy_survives_snapshot_replay(self):
        source = snapshot()
        source['input']['planner_options']['entrance_tracking'] = True
        source['input']['heading_hint'] = dict(entry=[3.,0.],direction=[1.,0.],observed_entrance=True)
        source['input']['destination'] = [0.,4.]
        report = replay(source)
        self.assertEqual(report['diagnostics']['guidance'],'remembered_lane_entrance')
        self.assertEqual(report['diagnostics']['guidance_target'],[3.,0.])
        source['input']['planner_options']['entrance_tracking'] = 1
        with self.assertRaises(ValueError):
            validate_snapshot(source)

    def test_full_replay_matches_observed_planner_and_preserves_input(self):
        source = snapshot(); before = copy.deepcopy(source); inputs = source['input']
        expected = plan_observed_navigation(inputs['origin'], inputs['resolution'], inputs['width'], inputs['height'],
            inputs['costs'], inputs['robot_xy'], inputs['robot_yaw'], inputs['destination'], inputs['lane_points'],
            heading_hint=inputs['heading_hint'], **inputs['planner_options'])
        report = replay(source)
        self.assertEqual(report['plan'], expected)
        self.assertEqual(report['status'], 'route_found')
        self.assertEqual(report['diagnostics']['guidance'], 'broad_gps')
        self.assertEqual(report['diagnostics']['lane_detection']['reason'], 'invalid_input')
        self.assertEqual(source, before)

    def test_no_route_keeps_detector_rejection_and_guidance(self):
        source = snapshot(); source['input']['costs'] = [100]*1600
        report = replay(source)
        self.assertIsNone(report['plan'])
        self.assertEqual(report['status'], 'no_route')
        self.assertEqual(report['diagnostics']['lane_detection']['status'], 'rejected')
        self.assertEqual(report['diagnostics']['guidance'], 'broad_gps')
        self.assertFalse(report['diagnostics']['route_found'])

    def test_diagnostics_only_does_not_run_search(self):
        with patch('replay_navigation_decision.plan_observed_navigation', side_effect=AssertionError('search invoked')):
            report = replay(snapshot(), diagnostics_only=True)
        self.assertEqual(report['status'], 'diagnostics_only')
        self.assertIsNone(report['diagnostics']['route_found'])
        self.assertEqual(report['diagnostics']['lane_detection']['reason'], 'invalid_input')

    def test_experimental_gate_is_explicit_and_production_function_restored(self):
        source = snapshot(); inputs = source['input']; angle = math.radians(80)
        direction = [math.cos(angle), math.sin(angle)]
        inputs['destination'] = [20*d for d in direction]
        inputs['lane_points'] = [[t*direction[0]-side*direction[1], t*direction[1]+side*direction[0]]
                                for side in (-3., 3.) for t in [2.+.2*i for i in range(51)]]
        baseline = replay(source, diagnostics_only=True)
        changed = replay(source, diagnostics_only=True, variation={'heading_gate': .1})
        self.assertEqual(baseline['diagnostics']['lane_detection']['status'], 'rejected')
        self.assertEqual(changed['diagnostics']['lane_detection']['status'], 'accepted')
        original = observed_navigation.propose_lane_corridor
        # Small-grid search checks that the temporary override is always restored.
        full = replay(source, variation={'heading_gate': .1})
        self.assertIs(observed_navigation.propose_lane_corridor, original)
        self.assertEqual(full['diagnostics']['guidance'], 'observed_lane_corridor')
        self.assertEqual(replay(source, diagnostics_only=True)['diagnostics']['lane_detection']['status'], 'rejected')

    def test_invalid_variation_rejected_even_when_final_goal_skips_detector(self):
        source = snapshot(); source['input']['destination'] = [.2, 0.]
        for variation in ({'heading_gate': float('nan')}, {'pair_angle_deg': 46},
                          {'heading_gate': .1, 'segment_span': 2.}, {'unknown': 1.}):
            with self.subTest(variation=variation), self.assertRaises(ValueError):
                replay(source, variation=variation)

    def test_rejects_oracle_fields_and_invalid_grid_payload(self):
        changes = [('course', {}), ('width', True), ('costs', [0]), ('resolution', .000001),
                   ('robot_xy', [float('inf'), 0.]), ('lane_points', [[0., 0., 1.]]),
                   ('heading_hint', {'entry': [1, 1], 'direction': [0, 0]}),
                   ('planner_options', {'unsupported': 1}), ('planner_options', {'forward_only': 1}),
                   ('planner_options', {'minimum_turn_radius': 1000})]
        for key, value in changes:
            source = snapshot(); source['input'][key] = value
            with self.subTest(field=key), self.assertRaises(ValueError):
                validate_snapshot(source)
        source = snapshot(); source['recorded_world'] = {}
        with self.assertRaises(ValueError):
            validate_snapshot(source)
        source = snapshot(); source['schema_version'] = True
        with self.assertRaises(ValueError):
            validate_snapshot(source)

    def test_gzip_cli_records_hash_and_never_changes_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'00001.json.gz'
            with gzip.open(path, 'wt', encoding='utf-8') as stream:
                json.dump(snapshot(), stream)
            before = path.read_bytes(); output = io.StringIO()
            destination = Path(directory)/'report.json'
            with contextlib.redirect_stdout(output):
                code = main(['--snapshot', str(path), '--diagnostics-only', '--output', str(destination)])
            report = json.loads(output.getvalue())
            self.assertEqual(code, 0)
            self.assertEqual(report, json.loads(destination.read_text()))
            self.assertEqual(len(report['expanded_snapshot_sha256']), 64)
            self.assertEqual(path.read_bytes(), before)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(['--snapshot', str(path), '--output', str(path)]), 1)
            self.assertEqual(path.read_bytes(), before)

    def test_nonfinite_and_corrupt_gzip_return_structured_cli_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'invalid.json'
            source = snapshot(); source['input']['resolution'] = float('nan')
            path.write_text(json.dumps(source))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(['--snapshot', str(path)]), 1)
            self.assertIn('Non-finite', json.loads(output.getvalue())['error'])
            bad_gzip = Path(directory)/'bad.json.gz'; bad_gzip.write_bytes(b'not gzip')
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(['--snapshot', str(bad_gzip)]), 1)

    def test_gzip_expansion_is_bounded_before_parsing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'large.json.gz'
            with gzip.open(path, 'wt', encoding='utf-8') as stream:
                stream.write('x'*20000)
            with patch.object(replay_tool, 'MAX_SNAPSHOT_BYTES', 8192), self.assertRaisesRegex(ValueError, 'Expanded snapshot'):
                load_snapshot(path)


if __name__ == '__main__':
    unittest.main()
