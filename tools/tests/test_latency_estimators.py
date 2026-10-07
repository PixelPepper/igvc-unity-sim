"""Clock-bound latency estimators behind one gated interface (pure, synthetic numbers only)."""
import dataclasses
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from latency_estimators import (COMMON_REJECTS, EMA, EMA_REJECTS, KINDS, LOWER_QUARTILE,  # noqa: E402
                                LOWER_QUARTILE_REJECTS, SAMPLE_POLICY, AdmissionSample, OdometryIntervalEMA,
                                WallSubmitAdmissionLowerQuartile, make_estimator)

NS = 1_000_000_000


def sample(stamp_s=.4, wall_s=.7, planning_ns=10*NS, submit=100., age=.05, admission_ns=None, receipt=None):
    """An admission attempt whose odometry interval is ``stamp_s`` and wall interval ``wall_s``."""
    admission_wall = submit+wall_s if submit is not None and wall_s is not None else 100.7
    return AdmissionSample(planning_stamp_ns=planning_ns,
                           admission_stamp_ns=admission_ns if admission_ns is not None
                           else planning_ns+round(stamp_s*NS),
                           submit_wall_s=submit, admission_wall_s=admission_wall,
                           admission_receipt_wall_s=receipt if receipt is not None else admission_wall-age)


def wall(seconds):
    """A sample whose wall interval is exactly ``seconds`` (submit 0)."""
    return AdmissionSample(10*NS, 11*NS, 0., seconds, seconds)


class ClockSeparationTests(unittest.TestCase):
    def test_each_estimator_reads_only_its_own_clock(self):
        ema, quartile = OdometryIntervalEMA(), WallSubmitAdmissionLowerQuartile()
        attempt = sample(stamp_s=.4, wall_s=.7)
        self.assertAlmostEqual(ema.observe_admission(attempt).interval_s, .4, places=12)
        self.assertAlmostEqual(quartile.observe_admission(attempt).interval_s, .7, places=12)
        self.assertAlmostEqual(ema.latency, .4, places=12)
        self.assertAlmostEqual(quartile.latency, .7, places=12)

    def test_ema_ignores_the_submit_clock_quartile_requires_it(self):
        for submit, reason in ((None, 'missing_submit_clock'), (float('nan'), 'invalid_submit_clock'),
                               (True, 'invalid_submit_clock'), ('1', 'invalid_submit_clock')):
            with self.subTest(submit=submit):
                attempt = AdmissionSample(10*NS, 10*NS+300_000_000, submit, 50., 49.9)
                ema, quartile = OdometryIntervalEMA(), WallSubmitAdmissionLowerQuartile()
                accepted = ema.observe_admission(attempt)
                self.assertTrue(accepted.accepted)
                self.assertAlmostEqual(accepted.interval_s, .3, places=12)
                rejected = quartile.observe_admission(attempt)
                self.assertEqual((rejected.accepted, rejected.reason), (False, reason))
                self.assertEqual((quartile.latency, quartile.samples), (.3, 0))

    def test_negative_wall_interval_rejected_zero_accepted(self):
        quartile = WallSubmitAdmissionLowerQuartile()
        self.assertEqual(quartile.observe_admission(AdmissionSample(1, 2, 5., 4.9, 4.9)).reason,
                         'negative_wall_interval')
        zero = quartile.observe_admission(AdmissionSample(1, 2, 5., 5., 5.))
        self.assertEqual((zero.accepted, zero.interval_s, quartile.latency), (True, 0., 0.))


class ArithmeticTests(unittest.TestCase):
    def test_ema_first_sample_replaces_then_smooths(self):
        ema = OdometryIntervalEMA()
        self.assertEqual(ema.latency, .6)
        # .4 replaces .6; then .7*.4+.3*.8 = .52; .7*.52+.3*1.0 = .664; .7*.664+.3*.0001 = .46483
        for seconds, want in zip((.4, .8, 1., .0001), (.4, .52, .664, .46483)):
            ema.observe_admission(sample(stamp_s=seconds))
            self.assertAlmostEqual(ema.latency, want, places=9)
        self.assertEqual(ema.samples, 4)

    def test_lower_quartile_small_n_and_window_eviction(self):
        quartile = WallSubmitAdmissionLowerQuartile()
        self.assertEqual(quartile.latency, .3)
        for seconds, want in ((.5, .5), (.2, .2), (.9, .2), (.1, .1), (.3, .2), (.4, .2), (.6, .2), (.7, .2),
                              (.8, .3)):
            quartile.observe_admission(wall(seconds))
            self.assertEqual(quartile.latency, want, msg=seconds)
        small = WallSubmitAdmissionLowerQuartile(window=3)
        for seconds in (.1, .2, .3, .4):
            small.observe_admission(wall(seconds))
        self.assertEqual(small.report()['window_samples'], [.2, .3, .4])
        self.assertEqual(small.latency, .2)
        full = WallSubmitAdmissionLowerQuartile()
        for k in range(25):  # 0.01 .. 0.25: the first five are evicted from the window of 20
            full.observe_admission(wall((k+1)/100))
        self.assertEqual(len(full.report()['window_samples']), 20)
        self.assertEqual(full.latency, .1)  # sorted .06 .. .25, index (20-1)//4 = 4

    def test_clamping_is_counted_and_used(self):
        ema = OdometryIntervalEMA()
        clamped = ema.observe_admission(sample(stamp_s=3.))
        self.assertEqual((clamped.accepted, clamped.clamped, clamped.interval_s), (True, True, 1.2))
        self.assertEqual((ema.latency, ema.clamped_samples, ema.samples), (1.2, 1, 1))
        quartile = WallSubmitAdmissionLowerQuartile(max_latency_s=.5)
        quartile.observe_admission(wall(2.))
        quartile.observe_admission(wall(.4))
        self.assertEqual(quartile.report()['window_samples'], [.5, .4])
        self.assertEqual((quartile.latency, quartile.clamped_samples), (.4, 1))


class GateTests(unittest.TestCase):
    CASES = [
        (AdmissionSample(None, 5*NS, 0., 1., 1.), 'missing_odometry_stamp'),
        (AdmissionSample(5*NS, None, 0., 1., 1.), 'missing_odometry_stamp'),
        (AdmissionSample(True, 5*NS, 0., 1., 1.), 'invalid_odometry_stamp'),
        (AdmissionSample(1., 5*NS, 0., 1., 1.), 'invalid_odometry_stamp'),
        (AdmissionSample(5*NS, '6', 0., 1., 1.), 'invalid_odometry_stamp'),
        (AdmissionSample(5*NS, 5*NS, 0., 1., 1.), 'no_new_odometry'),
        (AdmissionSample(6*NS, 5*NS, 0., 1., 1.), 'odometry_clock_reset'),
        (AdmissionSample(5*NS, 6*NS, 0., float('nan'), 1.), 'invalid_receipt_clock'),
        (AdmissionSample(5*NS, 6*NS, 0., 1., None), 'invalid_receipt_clock'),
        (AdmissionSample(5*NS, 6*NS, 0., 1., False), 'invalid_receipt_clock'),
        (AdmissionSample(5*NS, 6*NS, 0., 1., 1.01), 'future_admission_receipt'),
        (AdmissionSample(5*NS, 6*NS, 0., 1., .74), 'stale_admission_sample'),
    ]

    def test_every_rejection_is_counted_and_changes_nothing(self):
        for make in (OdometryIntervalEMA, WallSubmitAdmissionLowerQuartile):
            estimator = make()
            initial = estimator.latency
            for attempt, reason in self.CASES:
                with self.subTest(estimator=make.__name__, reason=reason, attempt=attempt):
                    result = estimator.observe_admission(attempt)
                    self.assertEqual((result.accepted, result.reason, result.interval_s), (False, reason, None))
            self.assertEqual((estimator.latency, estimator.samples, estimator.clamped_samples), (initial, 0, 0))
            self.assertEqual(estimator.rejected_samples, len(self.CASES))
            self.assertEqual(estimator.rejected, {'missing_odometry_stamp': 2, 'invalid_odometry_stamp': 3,
                                                  'no_new_odometry': 1, 'odometry_clock_reset': 1,
                                                  'invalid_receipt_clock': 3, 'future_admission_receipt': 1,
                                                  'stale_admission_sample': 1})

    def test_receipt_age_boundary_and_custom_max_age(self):
        self.assertTrue(OdometryIntervalEMA().observe_admission(AdmissionSample(5*NS, 6*NS, 0., 1., .75)).accepted)
        strict = OdometryIntervalEMA(max_sample_age_s=.1)
        self.assertEqual(strict.observe_admission(AdmissionSample(5*NS, 6*NS, 0., 1., .8)).reason,
                         'stale_admission_sample')
        with self.assertRaises(TypeError):
            OdometryIntervalEMA().observe_admission(dict(planning_stamp_ns=1))

    def test_accepted_after_rejections_still_uses_first_sample_rule(self):
        ema = OdometryIntervalEMA()
        ema.observe_admission(AdmissionSample(5*NS, 5*NS, 0., 1., 1.))
        ema.observe_admission(sample(stamp_s=.25))
        self.assertAlmostEqual(ema.latency, .25, places=12)


class IdentityAndConfigTests(unittest.TestCase):
    def test_default_identities_differ_and_name_the_rules(self):
        ema, quartile = make_estimator(EMA).identity(), make_estimator(LOWER_QUARTILE).identity()
        self.assertEqual(KINDS, (EMA, LOWER_QUARTILE))
        self.assertEqual((ema['kind'], ema['timebase']), (EMA, 'odometry_header_stamp_ns'))
        self.assertEqual((quartile['kind'], quartile['timebase']), (LOWER_QUARTILE, 'local_monotonic_s'))
        self.assertEqual(ema['config'], dict(initial_latency_s=.6, max_latency_s=1.2, max_sample_age_s=.25, alpha=.3))
        self.assertEqual(quartile['config'], dict(initial_latency_s=.3, max_latency_s=1.2, max_sample_age_s=.25,
                                                  window=20))
        self.assertEqual(quartile['statistic'], 'sorted_window[(n-1)//4]')
        self.assertIn('not the legacy end-to-end experiment', quartile['legacy_relation'])
        for identity in (ema, quartile):
            self.assertEqual((identity['sample_policy']['id'], identity['sample_policy']['version']),
                             (SAMPLE_POLICY, 1))
            self.assertEqual(identity['sample_policy']['rejects'], list(COMMON_REJECTS))
            self.assertEqual(json.loads(json.dumps(identity)), identity)
            self.assertFalse({'max_shift_m', 'max_yaw_shift_rad', 'horizon'} & set(identity['config']))

    def test_custom_settings_are_reported(self):
        identity = make_estimator(EMA, initial_latency_s=.5, alpha=.5, max_latency_s=2, max_sample_age_s=.5).identity()
        self.assertEqual(identity['config'], dict(initial_latency_s=.5, max_latency_s=2., max_sample_age_s=.5,
                                                  alpha=.5))
        quartile = make_estimator(LOWER_QUARTILE, window=7, initial_latency_s=0).identity()
        self.assertEqual((quartile['config']['window'], quartile['config']['initial_latency_s']), (7, 0.))

    def test_strict_selection_and_config(self):
        for kind in ('ema', None, 1, 'Odometry_header_interval_ema', ''):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                make_estimator(kind)
        with self.assertRaises(TypeError):
            make_estimator(EMA, window=5)
        with self.assertRaises(TypeError):
            make_estimator(LOWER_QUARTILE, alpha=.3)
        bad = [(EMA, dict(alpha=0)), (EMA, dict(alpha=1.5)), (EMA, dict(alpha=True)), (EMA, dict(alpha='0.3')),
               (EMA, dict(max_latency_s=0)), (EMA, dict(max_latency_s=6)), (EMA, dict(max_latency_s=True)),
               (EMA, dict(initial_latency_s=-.1)), (EMA, dict(initial_latency_s=2.)),
               (EMA, dict(max_sample_age_s=0)), (EMA, dict(max_sample_age_s=1.5)),
               (EMA, dict(initial_latency_s=float('nan'))),
               (LOWER_QUARTILE, dict(window=0)), (LOWER_QUARTILE, dict(window=2.)),
               (LOWER_QUARTILE, dict(window=True)), (LOWER_QUARTILE, dict(window=1001))]
        for kind, config in bad:
            with self.subTest(kind=kind, config=config), self.assertRaises(ValueError):
                make_estimator(kind, **config)

    def test_config_is_frozen_and_reports_are_detached(self):
        estimator = make_estimator(LOWER_QUARTILE)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            estimator.config.window = 3
        with self.assertRaises(AttributeError):  # the public config cannot be replaced either
            estimator.config = dataclasses.replace(estimator.config, window=3)
        self.assertEqual(estimator.config.window, 20)
        estimator.observe_admission(wall(.5))
        estimator.observe_admission(AdmissionSample(None, 1, 0., 1., 1.))
        report = estimator.report()
        report['rejected']['missing_odometry_stamp'] = 99
        report['window_samples'].append(9.)
        report['identity']['config']['window'] = 3
        again = estimator.report()
        self.assertEqual(again['rejected'], {'missing_odometry_stamp': 1})
        self.assertEqual(again['window_samples'], [.5])
        self.assertEqual(again['identity']['config']['window'], 20)
        self.assertEqual((again['samples'], again['rejected_samples'], again['latency_s']), (1, 1, .5))
        self.assertEqual(json.loads(json.dumps(again)), again)


class RepresentabilityTests(unittest.TestCase):
    """Finite inputs whose arithmetic leaves the float range are rejected before clamping, never raised."""

    def test_overflowing_wall_interval_is_rejected_not_clamped(self):
        attempt = AdmissionSample(5*NS, 6*NS, -1e308, 1e308, 1e308)  # 1e308 - -1e308 = inf
        quartile = WallSubmitAdmissionLowerQuartile()
        result = quartile.observe_admission(attempt)
        self.assertEqual((result.accepted, result.reason), (False, 'invalid_wall_interval'))
        self.assertEqual((quartile.latency, quartile.samples, quartile.clamped_samples), (.3, 0, 0))
        self.assertEqual(quartile.rejected, {'invalid_wall_interval': 1})
        ema = OdometryIntervalEMA()  # never reads the submit clock
        self.assertAlmostEqual(ema.observe_admission(attempt).interval_s, 1., places=12)

    def test_overflowing_receipt_age_is_rejected(self):
        for admission, receipt in ((1e308, -1e308), (10**308, -10**308)):
            for make in (OdometryIntervalEMA, WallSubmitAdmissionLowerQuartile):
                with self.subTest(admission=admission, estimator=make.__name__):
                    estimator = make()
                    result = estimator.observe_admission(AdmissionSample(5*NS, 6*NS, 0., admission, receipt))
                    self.assertEqual(result.reason, 'invalid_receipt_age')
                    self.assertEqual((estimator.samples, estimator.rejected), (0, {'invalid_receipt_age': 1}))

    def test_huge_integer_clocks_and_stamps(self):
        huge = 10**400
        for make in (OdometryIntervalEMA, WallSubmitAdmissionLowerQuartile):
            with self.subTest(estimator=make.__name__):
                self.assertEqual(make().observe_admission(AdmissionSample(5*NS, 6*NS, 0., huge, 1.)).reason,
                                 'invalid_receipt_clock')
                self.assertEqual(make().observe_admission(AdmissionSample(5*NS, 6*NS, 0., 1., -huge)).reason,
                                 'invalid_receipt_clock')
        ema = OdometryIntervalEMA()
        result = ema.observe_admission(AdmissionSample(0, huge, None, 1., 1.))  # exact int delta, no float
        self.assertEqual((result.reason, ema.latency, ema.clamped_samples), ('invalid_odometry_interval', .6, 0))
        quartile = WallSubmitAdmissionLowerQuartile()
        self.assertEqual(quartile.observe_admission(AdmissionSample(5*NS, 6*NS, huge, 1., 1.)).reason,
                         'invalid_submit_clock')
        # The quartile reads only the wall clock, so a huge but ordered stamp pair is not its concern.
        accepted = quartile.observe_admission(AdmissionSample(0, huge, 0., .5, .5))
        self.assertEqual((accepted.accepted, quartile.latency), (True, .5))

    def test_huge_integer_config_is_a_value_error(self):
        huge = 10**400
        for kind, config in ((EMA, dict(initial_latency_s=huge)), (EMA, dict(max_latency_s=huge)),
                             (EMA, dict(max_sample_age_s=huge)), (EMA, dict(alpha=huge)),
                             (LOWER_QUARTILE, dict(window=huge)), (LOWER_QUARTILE, dict(max_latency_s=-huge))):
            with self.subTest(kind=kind, config=list(config)), self.assertRaises(ValueError):
                make_estimator(kind, **config)

    def test_per_kind_identity_rejects(self):
        ema, quartile = OdometryIntervalEMA().identity(), WallSubmitAdmissionLowerQuartile().identity()
        self.assertEqual(ema['rejects'], list(EMA_REJECTS))
        self.assertEqual(quartile['rejects'], list(LOWER_QUARTILE_REJECTS))
        self.assertFalse([r for r in ema['rejects'] + ema['sample_policy']['rejects'] if 'submit' in r or 'wall' in r])
        self.assertEqual(ema['sample_policy'], quartile['sample_policy'])
        self.assertFalse(set(EMA_REJECTS) & set(COMMON_REJECTS) or set(LOWER_QUARTILE_REJECTS) & set(COMMON_REJECTS))

    def test_accepted_after_overflow_rejections_is_unchanged(self):
        quartile = WallSubmitAdmissionLowerQuartile()
        quartile.observe_admission(AdmissionSample(5*NS, 6*NS, -1e308, 1e308, 1e308))
        quartile.observe_admission(AdmissionSample(5*NS, 6*NS, 0., 1e308, -1e308))
        quartile.observe_admission(wall(.4))
        quartile.observe_admission(wall(2.))  # finite and above max: still clamped and counted
        self.assertEqual(quartile.report()['window_samples'], [.4, 1.2])
        self.assertEqual((quartile.latency, quartile.samples, quartile.clamped_samples, quartile.rejected_samples),
                         (.4, 2, 1, 2))
        ema = OdometryIntervalEMA()
        ema.observe_admission(AdmissionSample(0, 10**400, None, 1., 1.))
        ema.observe_admission(sample(stamp_s=.25))
        self.assertAlmostEqual(ema.latency, .25, places=12)  # first ACCEPTED sample still replaces the initial


if __name__ == '__main__':
    unittest.main()
