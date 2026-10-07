"""Guarded latency prediction over the real estimators (pure; spy admission; numeric expectations)."""
import json
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from guarded_latency_compensation import (GuardedLatencyCompensator, OdometrySample,  # noqa: E402
                                          admit_from_measured_pose, execution_mode_error, frozen_planner_inputs,
                                          rebase_heading_hint)
from latency_estimators import EMA, LOWER_QUARTILE  # noqa: E402
from snapshot_pose_provenance import classify_snapshot_pose  # noqa: E402

NS = 1_000_000_000
ORIGIN = (0., 0., 0.)


def odom(pose=ORIGIN, twist=(.5, 0.), stamp_s=10., received=100.65):
    return OdometrySample(tuple(pose), tuple(twist), round(stamp_s*NS), received)


def trained(kind, **options):
    """A compensator whose estimator holds exactly one admission: header interval 0.4 s, wall interval 0.7 s."""
    compensator = GuardedLatencyCompensator(kind, enabled=True, **options)
    planning, entry = odom(stamp_s=10.), odom(pose=(.2, 0., 0.), stamp_s=10.4, received=100.68)
    outcome = compensator.observe_admission(planning, entry, (.2, 0., 0.), now=100.7, submitted_at=100.)
    assert outcome['accepted'], outcome
    return compensator


def snapshot(context, inputs):
    return json.loads(json.dumps(dict(schema_version=1, input=inputs, metadata=dict(latency_compensation=context))))


def inputs_for(planning_pose):
    return frozen_planner_inputs((0., -1.), .1, 2, 2, (0, 0, 100, -1), planning_pose, (5., 0.), [(1., 1.)],
                                 None, dict(a=1), None)


class ClockAndPredictionTests(unittest.TestCase):
    def test_distinct_clocks_give_distinct_bounded_predictions(self):
        ema, quartile = trained(EMA), trained(LOWER_QUARTILE)
        self.assertAlmostEqual(ema.latency, .4, places=12)
        self.assertAlmostEqual(quartile.latency, .7, places=12)
        sample = odom(twist=(.5, 0.), received=200.)
        pose_e, ctx_e = ema.planning_context(sample, ORIGIN, 200.1)
        pose_q, ctx_q = quartile.planning_context(sample, ORIGIN, 200.1)
        self.assertAlmostEqual(pose_e[0], .2, places=12)
        self.assertAlmostEqual(pose_q[0], .35, places=12)
        self.assertEqual((pose_e[1], pose_e[2], pose_q[1], pose_q[2]), (0., 0., 0., 0.))
        self.assertEqual((ctx_e['applied'], ctx_q['applied'], ctx_e['reason']), (True, True, 'predicted'))
        self.assertAlmostEqual(ctx_q['horizon_s'], .7, places=12)
        self.assertEqual(ctx_e['identity']['estimator']['kind'], EMA)
        self.assertEqual(ctx_q['identity']['estimator']['kind'], LOWER_QUARTILE)

    def test_translation_cap_and_fast_rotation_cap(self):
        quartile = trained(LOWER_QUARTILE)  # estimate 0.7 s
        pose, ctx = quartile.planning_context(odom(twist=(2., 0.), received=200.), ORIGIN, 200.)
        self.assertAlmostEqual(ctx['horizon_s'], .5, places=12)  # 1 m / 2 m/s
        self.assertAlmostEqual(pose[0], 1., places=12)
        pose, ctx = quartile.planning_context(odom(twist=(.1, 3.), received=200.), ORIGIN, 200.)
        self.assertAlmostEqual(ctx['horizon_s'], .2, places=12)  # 0.6 rad / 3 rad/s
        self.assertAlmostEqual(pose[2], .6, places=12)
        self.assertAlmostEqual(pose[0], 0.018821415780, places=9)  # (0.1/3) sin 0.6
        self.assertAlmostEqual(pose[1], 0.005822146164, places=9)  # (0.1/3)(1 - cos 0.6)
        self.assertAlmostEqual(quartile.max_applied_yaw_shift, .6, places=12)
        self.assertLessEqual(quartile.max_applied_shift, 1.+1e-12)

    def test_zero_horizon_with_moving_twist_is_applied_and_predicted(self):
        compensator = GuardedLatencyCompensator(EMA, enabled=True, estimator_config=dict(initial_latency_s=0.))
        pose, ctx = compensator.planning_context(odom(twist=(.5, 0.), received=200.), ORIGIN, 200.)
        self.assertEqual(pose, ORIGIN)
        self.assertEqual((ctx['applied'], ctx['horizon_s']), (True, 0.))
        self.assertEqual(ctx['planning_pose'], ctx['measured_pose'])
        self.assertEqual(classify_snapshot_pose(snapshot(ctx, inputs_for(pose)))['kind'], 'predicted')


class NoActionTests(unittest.TestCase):
    def test_disabled_returns_the_identical_measured_pose(self):
        compensator = GuardedLatencyCompensator(LOWER_QUARTILE, enabled=False)
        measured = (1., 2., .3)
        pose, ctx = compensator.planning_context(odom(pose=measured, twist=(1., 1.)), measured, 100.7)
        self.assertIs(pose, measured)
        self.assertEqual((ctx['applied'], ctx['reason'], compensator.skipped), (False, 'disabled', {}))
        self.assertEqual(classify_snapshot_pose(snapshot(ctx, inputs_for(pose)))['kind'], 'measured')

    def test_every_skip_returns_measured_and_is_counted(self):
        compensator = trained(EMA)
        measured = ORIGIN
        cases = [(None, 200., 'no_odometry_sample'),
                 (dict(pose=ORIGIN), 200., 'malformed_odometry_sample'),
                 (OdometrySample(ORIGIN, (float('nan'), 0.), 10*NS, 200.), 200., 'malformed_odometry_sample'),
                 (OdometrySample(ORIGIN, (.5, 0.), True, 200.), 200., 'malformed_odometry_sample'),
                 (OdometrySample(ORIGIN, (.5, 0.), 10*NS, 10**400), 200., 'malformed_odometry_sample'),
                 (odom(pose=(.1, 0., 0.), received=200.), 200., 'pose_not_from_sample'),
                 (odom(received=200.), float('nan'), 'invalid_now'),
                 (odom(received=200.1), 200., 'future_odometry_sample'),
                 (odom(received=199.7), 200., 'stale_odometry_sample'),
                 (odom(twist=(.01, -.01), received=200.), 200., 'stationary_twist')]
        for sample, now, reason in cases:
            with self.subTest(reason=reason, sample=sample):
                pose, ctx = compensator.planning_context(sample, measured, now)
                self.assertIs(pose, measured)
                self.assertEqual((ctx['applied'], ctx['reason'], ctx['planning_pose']), (False, reason, [0., 0., 0.]))
                self.assertEqual(classify_snapshot_pose(snapshot(ctx, inputs_for(pose)))['kind'], 'measured')
        self.assertEqual(compensator.predictions, 0)
        self.assertEqual(compensator.skipped, {'no_odometry_sample': 1, 'malformed_odometry_sample': 4,
                                               'pose_not_from_sample': 1, 'invalid_now': 1,
                                               'future_odometry_sample': 1, 'stale_odometry_sample': 1,
                                               'stationary_twist': 1})
        _, ctx = compensator.planning_context(odom(received=199.75), measured, 200.)  # age exactly 0.25 s
        self.assertTrue(ctx['applied'])

    def test_malformed_measured_pose_is_rejected_not_fabricated(self):
        compensator = trained(EMA)
        for bad in ((float('nan'), 0., 0.), (1., 2.), (10**400, 0., 0.), (True, 0., 0.), None, '000'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                compensator.planning_context(odom(received=200.), bad, 200.)

    def test_contexts_are_detached(self):
        compensator = trained(EMA)
        _, first = compensator.planning_context(odom(received=200.), ORIGIN, 200.)
        kept = json.loads(json.dumps(first))
        first['planning_pose'][0] = 99.
        first['identity']['prediction']['config']['max_shift_m'] = 9.
        _, second = compensator.planning_context(odom(received=200.), ORIGIN, 200.)
        self.assertEqual(second, kept)
        report = compensator.report()
        report['skipped']['x'] = 1
        report['estimator']['rejected']['y'] = 1
        self.assertEqual((compensator.report()['skipped'], compensator.estimator.rejected), ({}, {}))
        with self.assertRaises(AttributeError):
            compensator.config = None


class AdmissionTests(unittest.TestCase):
    def spy(self, result):
        calls = []

        def admit(*args):
            calls.append(args)
            return result
        return admit, calls

    def test_admission_sees_actual_pose_grid_footprint_once_and_result_is_returned(self):
        for kind in (EMA, LOWER_QUARTILE):
            for result in ((None, dict(reason='start_pose_departed_checked_path')),
                           (dict(path=[[0, 0]]), dict(reason='admitted'))):
                with self.subTest(kind=kind, admitted=result[0] is not None):
                    compensator = GuardedLatencyCompensator(kind, enabled=True)
                    planning = odom(stamp_s=10., received=100.)
                    _, ctx = compensator.planning_context(planning, ORIGIN, 100.05)
                    entry_pose = (.2, .01, .02)
                    entry = odom(pose=entry_pose, stamp_s=10.3, received=100.55)
                    grid = ((0., -1.), .1, 2, 2, (0, 0, 100, -1))
                    footprint = [[.5, .3], [-.5, .3]]
                    plan = dict(local_goal=[3., 0.])
                    admit, calls = self.spy(result)
                    admitted, admission, provenance = admit_from_measured_pose(
                        compensator, admit, plan, entry_pose, grid, footprint, planning, entry, ctx,
                        now=100.6, submitted_at=100.1)
                    self.assertEqual(calls, [(plan, entry_pose, *grid, footprint)])
                    self.assertIs(calls[0][1], entry_pose)  # the actual pose, never the prediction
                    self.assertIs(admitted, result[0])
                    self.assertIs(admission, result[1])
                    self.assertEqual(provenance['admission_pose'], list(entry_pose))
                    self.assertEqual(provenance['planning_pose'], ctx['planning_pose'])
                    self.assertTrue(provenance['latency_sample']['accepted'])
                    want = .3 if kind == EMA else .5  # header 10.3-10.0 vs wall 100.6-100.1
                    self.assertAlmostEqual(compensator.latency, want, places=9)
                    self.assertEqual((provenance['submitted_at_s'], provenance['admission_now_s']), (100.1, 100.6))

    def test_submit_clock_forwarding_and_entry_mismatch(self):
        planning, entry = odom(stamp_s=10., received=100.), odom(pose=(.2, 0., 0.), stamp_s=10.3, received=100.55)
        ema, quartile = (GuardedLatencyCompensator(k, enabled=True) for k in (EMA, LOWER_QUARTILE))
        ema_out = ema.observe_admission(planning, entry, (.2, 0., 0.), now=100.6, submitted_at=None)
        quartile_out = quartile.observe_admission(planning, entry, (.2, 0., 0.), now=100.6, submitted_at=None)
        self.assertTrue(ema_out['accepted'])  # the EMA never reads the submit clock
        self.assertEqual((quartile_out['sampled'], quartile_out['accepted'], quartile_out['reason']),
                         (True, False, 'missing_submit_clock'))
        self.assertEqual((quartile.latency, quartile.estimator.rejected), (.3, {'missing_submit_clock': 1}))
        stale = quartile.observe_admission(planning, odom(pose=(.2, 0., 0.), stamp_s=10.3, received=100.2),
                                           (.2, 0., 0.), now=100.6, submitted_at=100.1)
        self.assertEqual(stale['reason'], 'stale_admission_sample')
        mismatch = quartile.observe_admission(planning, entry, (.21, 0., 0.), now=100.6, submitted_at=100.1)
        missing = quartile.observe_admission(None, entry, (.2, 0., 0.), now=100.6, submitted_at=100.1)
        self.assertEqual((mismatch['sampled'], mismatch['reason']), (False, 'entry_pose_not_from_sample'))
        self.assertEqual(missing['reason'], 'missing_odometry_sample')
        self.assertEqual(quartile.not_sampled, {'entry_pose_not_from_sample': 1, 'missing_odometry_sample': 1})
        self.assertEqual(quartile.estimator.samples, 0)
        self.assertEqual(quartile.report()['estimator']['rejected'],
                         {'missing_submit_clock': 1, 'stale_admission_sample': 1})


class InputAndConfigTests(unittest.TestCase):
    def test_frozen_inputs_only_take_the_planning_pose(self):
        inputs = frozen_planner_inputs((1., 2.), .1, 3, 1, (0, 50, 100), (4., 5., .6), (9., 9.), [(1., 1.)],
                                       dict(entry=[2., 2.]), dict(lookahead=7.), dict(kind='x'))
        self.assertEqual(inputs, dict(origin=[1., 2.], resolution=.1, width=3, height=1, costs=[0, 50, 100],
                                      robot_xy=[4., 5.], robot_yaw=.6, destination=[9., 9.], lane_points=[(1., 1.)],
                                      heading_hint=dict(entry=[2., 2.]), planner_options=dict(lookahead=7.),
                                      frozen_guidance=dict(kind='x')))

    def test_heading_rebase_moves_only_pose_relative_hints(self):
        hint = dict(entry=[3., 1.], heading_only=True)
        rebased = rebase_heading_hint(hint, (0., 0., 0.), (.5, -.25, .1))
        self.assertEqual(rebased['entry'], [3.5, .75])
        self.assertEqual(rebased['rebased_from'], [3., 1.])
        self.assertEqual(hint, dict(entry=[3., 1.], heading_only=True))  # input untouched
        world = dict(entry=[3., 1.], heading_only=False)
        self.assertIs(rebase_heading_hint(world, (0., 0., 0.), (.5, 0., 0.)), world)
        self.assertIs(rebase_heading_hint(hint, (0., 0., 0.), (0., 0., 0.)), hint)
        self.assertIsNone(rebase_heading_hint(None, (0., 0., 0.), (.5, 0., 0.)))

    def test_execution_mode_and_strict_config(self):
        self.assertIsNone(execution_mode_error(True, 'checked-path'))
        self.assertIsNone(execution_mode_error(False, 'nav2-goal'))
        self.assertIn('checked-path', execution_mode_error(True, 'nav2-goal'))
        with self.assertRaises(TypeError):
            GuardedLatencyCompensator(enabled=True)  # estimator kind is required
        with self.assertRaises(TypeError):
            GuardedLatencyCompensator(EMA)  # enabled is required
        bad = [dict(kind='ema'), dict(enabled=1), dict(enabled='true'), dict(max_shift_m=0), dict(max_shift_m=2.5),
               dict(max_yaw_shift_rad=2.), dict(max_sample_age_s=0), dict(max_sample_age_s=True),
               dict(max_shift_m=10**400), dict(estimator_config=dict(max_sample_age_s=.5)),
               dict(estimator_config=dict(alpha=0))]
        for options in bad:
            options = dict(dict(kind=EMA, enabled=True), **options)
            with self.subTest(options=options), self.assertRaises(ValueError):
                GuardedLatencyCompensator(options.pop('kind'), **options)
        with self.assertRaises(TypeError):
            GuardedLatencyCompensator(EMA, enabled=True, estimator_config=dict(window=5))

    def test_shared_receipt_age_and_identity(self):
        compensator = GuardedLatencyCompensator(LOWER_QUARTILE, enabled=True, max_sample_age_s=.1,
                                                estimator_config=dict(window=7))
        self.assertEqual(compensator.estimator.config.max_sample_age_s, .1)
        self.assertEqual(compensator.config.max_sample_age_s, .1)
        identity = compensator.identity()
        self.assertEqual(identity['prediction']['id'], 'guarded_constant_twist_unicycle')
        self.assertFalse(identity['prediction']['end_pose_scaling'])
        self.assertFalse(identity['prediction']['legacy_equivalent'])
        self.assertEqual(identity['prediction']['applied'], 'extrapolation_branch_executed')
        self.assertEqual(identity['estimator']['config']['window'], 7)
        self.assertEqual(json.loads(json.dumps(compensator.report())), compensator.report())


if __name__ == '__main__':
    unittest.main()
