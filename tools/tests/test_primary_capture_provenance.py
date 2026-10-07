"""Primary capture pose provenance: the real predictor, its capture wiring and the canonical classifier."""
import ast
import gzip
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / 'learning'))
from latency_compensation import (LEGACY_ESTIMATOR_ID, LatencyCompensator,  # noqa: E402
                                  capture_planning_inputs)
from navigation_decisions import compact_event_metadata  # noqa: E402
from snapshot_pose_provenance import classify_snapshot_pose  # noqa: E402
from dataset_policy import PosePolicy, admit_group, load_snapshot_provenance  # noqa: E402

POSE = (1., 2., .3)


def capture(compensator, pose=POSE, twist=None):
    """The capture wiring sensor_course uses, plus the snapshot payload it records (after a JSON round trip)."""
    planning, inputs, metadata = capture_planning_inputs(
        compensator, pose, twist, (0., -1.), .1, 2, 2, (0, 0, 100, -1), (5., 0.), [(1., 1.)], None, dict(a=1), None)
    snapshot = json.loads(json.dumps(dict(schema_version=1, input=inputs, metadata=dict(latency_compensation=metadata))))
    return planning, inputs, metadata, snapshot


def kind(snapshot):
    return classify_snapshot_pose(snapshot)['kind']


class BranchProvenanceTests(unittest.TestCase):
    def test_early_returns_are_measured(self):
        cases = [(LatencyCompensator(False), (.6, .4), 'disabled'),
                 (LatencyCompensator(True), None, 'no_twist'),
                 (LatencyCompensator(True), (float('nan'), .4), 'nonfinite_twist'),
                 (LatencyCompensator(True), (.6, float('inf')), 'nonfinite_twist'),
                 (LatencyCompensator(True), (.01, -.01), 'stationary')]
        for compensator, twist, reason in cases:
            with self.subTest(reason=reason, twist=twist):
                planning, inputs, metadata, snapshot = capture(compensator, twist=twist)
                self.assertEqual(planning, POSE)
                self.assertIs(metadata['applied'], False)
                self.assertIs(metadata['enabled'], compensator.enabled)
                self.assertEqual(metadata['reason'], reason)
                self.assertEqual(metadata['measured_pose'], list(POSE))
                self.assertEqual(metadata['planning_pose'], list(POSE))
                self.assertEqual(kind(snapshot), 'measured')
                self.assertEqual(compensator.predictions, 0)

    def test_extrapolation_is_predicted_and_values_unchanged(self):
        cases = [((0., 0., 0.), (.6, 0.), dict(initial_latency_s=.5), (.3, 0., 0.), 'extrapolated'),
                 ((0., 0., 0.), (1., 1.), dict(initial_latency_s=math.pi/2, max_shift_m=5.), (1., 1., math.pi/2),
                  'extrapolated'),
                 ((0., 0., 0.), (2., 0.), dict(initial_latency_s=1.2, max_shift_m=.5), (.5, 0., 0.),
                  'extrapolated_shift_scaled')]
        for pose, twist, options, expected, reason in cases:
            with self.subTest(reason=reason, twist=twist):
                compensator, reference = LatencyCompensator(True, **options), LatencyCompensator(True, **options)
                planning, inputs, metadata, snapshot = capture(compensator, pose, twist)
                self.assertEqual(planning, reference.predict(pose, twist))  # identical to the plain call
                for got, want in zip(planning, expected):
                    self.assertAlmostEqual(got, want, places=6)
                self.assertEqual((inputs['robot_xy'], inputs['robot_yaw']), (list(planning[:2]), planning[2]))
                self.assertIs(metadata['applied'], True)
                self.assertEqual(metadata['reason'], reason)
                self.assertEqual(metadata['planning_pose'], list(planning))
                self.assertEqual(metadata['latency_s'], compensator.latency)
                self.assertEqual(kind(snapshot), 'predicted')
                self.assertEqual(compensator.report(), reference.report())

    def test_zero_latency_extrapolation_is_applied_even_with_equal_poses(self):
        compensator = LatencyCompensator(True, initial_latency_s=0.)
        planning, _, metadata, snapshot = capture(compensator, (1., 2., 0.), (.6, 0.))
        self.assertEqual(planning, (1., 2., 0.))
        self.assertEqual(metadata['planning_pose'], metadata['measured_pose'])
        self.assertIs(metadata['applied'], True)
        self.assertEqual(kind(snapshot), 'predicted')  # never inferred measured from equality
        self.assertEqual(compensator.predictions, 1)

    def test_skip_after_applied_does_not_inherit_and_metadata_is_detached(self):
        compensator = LatencyCompensator(True, initial_latency_s=.5)
        _, _, first, _ = capture(compensator, (0., 0., 0.), (.6, 0.))
        kept = json.loads(json.dumps(first))
        _, _, second, snapshot = capture(compensator, (0., 0., 0.), None)
        self.assertIs(second['applied'], False)
        self.assertEqual(second['reason'], 'no_twist')
        self.assertEqual(kind(snapshot), 'measured')
        second['measured_pose'][0] = 99.
        second['estimator']['config']['max_shift_m'] = 99.
        self.assertEqual(first, kept)
        _, _, third, _ = capture(compensator, (0., 0., 0.), None)
        self.assertEqual(third['measured_pose'], [0., 0., 0.])
        self.assertEqual(third['estimator']['config']['max_shift_m'], 1.)
        # A plain predict() call in between leaves no branch for the next capture to read.
        compensator.predict((0., 0., 0.), (.6, 0.))
        _, _, fourth, _ = capture(compensator, (0., 0., 0.), (.01, 0.))
        self.assertEqual((fourth['applied'], fourth['reason']), (False, 'stationary'))


class EstimatorIdentityTests(unittest.TestCase):
    def test_identity_reflects_constructor_and_is_not_an_average(self):
        compensator = LatencyCompensator(True, initial_latency_s=.45, alpha=.9, max_latency_s=2., max_shift_m=.7)
        identity = compensator.estimator_identity()
        self.assertEqual((identity['id'], identity['version'], identity['window']), (LEGACY_ESTIMATOR_ID, 1, 20))
        self.assertNotIn('ema', identity['id'])
        self.assertEqual(identity['statistic'], 'sorted_window[(n-1)//4]')
        self.assertEqual(identity['interval_clock'], 'local_monotonic')
        self.assertEqual(identity['shift_bound'], 'end_pose_scaled_to_max_shift_m')
        self.assertEqual(identity['config'], dict(initial_latency_s=.45, max_latency_s=2., max_shift_m=.7,
                                                  alpha=.9, alpha_used=False))
        self.assertEqual(LatencyCompensator().estimator_identity()['config']['initial_latency_s'], .3)
        self.assertIsNot(compensator.estimator_identity(), identity)

    def test_latency_math_and_report_fields_are_unchanged(self):
        compensator = LatencyCompensator(True, initial_latency_s=.6, max_latency_s=1.2)
        compensator.observe_latency(.2)
        self.assertAlmostEqual(compensator.latency, .2)
        for value in (.6, .7, .8):
            compensator.observe_latency(value)
        self.assertAlmostEqual(compensator.latency, .2)
        for value in range(30):
            compensator.observe_latency(5.)
        self.assertEqual(len(compensator.recent), 20)
        self.assertEqual(compensator.latency, 1.2)
        self.assertEqual(set(compensator.report()),
                         {'enabled', 'latency_s', 'latency_samples', 'predictions', 'max_applied_shift_m'})


class DatasetAdmissionTests(unittest.TestCase):
    def provenance(self, payload):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / '00001.json.gz'
            with gzip.open(path, 'wt', encoding='utf-8') as stream:
                json.dump(payload, stream)
            return load_snapshot_provenance(path)[1]

    def test_measured_admitted_predicted_needs_opt_in_history_stays_unknown(self):
        _, inputs, _, disabled = capture(LatencyCompensator(False), twist=(.6, .4))
        _, _, _, predicted = capture(LatencyCompensator(True, initial_latency_s=.5), twist=(.6, .4))
        measured, applied = self.provenance(disabled), self.provenance(predicted)
        self.assertEqual(measured['kind'], 'measured')
        self.assertEqual(applied['kind'], 'predicted')
        self.assertTrue(admit_group([measured], PosePolicy())[0])
        self.assertFalse(admit_group([applied], PosePolicy())[0])
        self.assertTrue(admit_group([applied], PosePolicy(allow_predicted=True))[0])
        for historical in (dict(schema_version=1, input=inputs),
                           dict(schema_version=1, input=inputs, metadata=dict(frame='odom'))):
            unknown = self.provenance(historical)
            self.assertEqual(unknown['kind'], 'unknown_legacy')
            self.assertFalse(admit_group([unknown], PosePolicy(allow_predicted=True))[0])


class SensorCourseWiringTests(unittest.TestCase):
    """sensor_course builds planner inputs and the provenance from ONE capture_planning_inputs call."""

    def test_capture_wiring(self):
        tree = ast.parse((TOOLS / 'sensor_course.py').read_text(encoding='utf-8'))
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
        captures = [c for c in calls if getattr(c.func, 'id', None) == 'capture_planning_inputs']
        self.assertEqual(len(captures), 1)
        direct = [c for c in calls if isinstance(c.func, ast.Attribute) and c.func.attr in ('predict', 'predict_with_provenance')
                  and getattr(c.func.value, 'id', None) == 'latency_compensator']
        self.assertEqual(direct, [])  # no second, unrecorded prediction
        # Snapshot metadata dict(..., latency_compensation=latency_metadata) and the event's detached copy.
        values = [k.value for c in calls if getattr(c.func, 'id', None) == 'dict' for k in c.keywords
                  if k.arg == 'latency_compensation']
        self.assertEqual(len(values), 2)
        self.assertIn('latency_metadata', [getattr(v, 'id', None) for v in values])
        self.assertIn('latency_metadata', ast.dump(values[1]) + ast.dump(values[0]))
        # The requested event keeps provenance alongside the compacted metadata.
        self.assertEqual(compact_event_metadata(dict(latency_compensation=dict(applied=False)))['latency_compensation'],
                         dict(applied=False))


if __name__ == '__main__':
    unittest.main()
