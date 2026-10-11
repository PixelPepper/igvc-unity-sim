"""Finish crossing contract: offset crossing, stationary/jitter/reverse/early/teleport/speed rejection, invalid inputs."""
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from finish_crossing import (CONTRACT_VERSION, FIXTURE_LINE, LEGACY_CONTRACT,  # noqa: E402
                             FinishCrossingTracker, FinishLine, select_contract)


def drive(points, *, speed=1.5, dt=.05, t=0.):
    """Base_footprint samples along a polyline at constant speed (20 Hz odom), endpoints included."""
    samples = [(t, *points[0])]
    for a, b in zip(points, points[1:]):
        steps = max(1, math.ceil(math.dist(a, b)/(speed*dt)))
        for k in range(1, steps+1):
            t += dt
            samples.append((t, a[0]+(b[0]-a[0])*k/steps, a[1]+(b[1]-a[1])*k/steps))
    return samples


def run(tracker, samples, eligible_from=0):
    return [tracker.observe(t, x, y, eligible=i >= eligible_from) for i, (t, x, y) in enumerate(samples)]


def outcomes(decisions):
    return {d['outcome'] for d in decisions}


def scalars(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from scalars(item)
    elif isinstance(value, list):
        for item in value:
            yield from scalars(item)
    elif isinstance(value, float):
        yield value


class FixtureLineTest(unittest.TestCase):
    def test_fixture_line_is_public_origin_with_ros_plus_x_normal(self):
        self.assertEqual(FIXTURE_LINE.center, (0., 0.))
        self.assertEqual(FIXTURE_LINE.normal, (1., 0.))
        self.assertEqual(FIXTURE_LINE.half_span_m, 3.)
        policy = FinishCrossingTracker().policy()
        self.assertEqual(policy['contract_version'], CONTRACT_VERSION)
        self.assertEqual(policy['max_speed_mps'], 2.2)
        self.assertEqual(policy['audit_tolerance'], 1e-6)

    def test_invalid_line_definitions_are_rejected(self):
        for kwargs in (dict(center_x=math.nan), dict(normal_x=math.inf), dict(normal_x=.5),
                       dict(half_span_m=0.), dict(half_span_m=-1.), dict(half_span_m=True),
                       dict(center_x=10**400), dict(half_span_m=10**400),
                       dict(normal_x=1e308, normal_y=1e308), dict(normal_x=1.7e308, normal_y=1.7e308)):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                FinishLine(**kwargs)
        for kwargs in (dict(max_step_m=math.nan), dict(max_step_m=10**400), dict(max_speed_mps=0.),
                       dict(max_interval_s=True), dict(line='origin')):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                FinishCrossingTracker(**kwargs)


class ContractSelectionTest(unittest.TestCase):
    def test_absent_block_is_legacy_and_wrong_versions_fail_closed(self):
        self.assertEqual(select_contract({}), LEGACY_CONTRACT)
        self.assertEqual(select_contract(dict(finish_crossing=FinishCrossingTracker().report())),
                         CONTRACT_VERSION)
        for run in (dict(finish_crossing={}), dict(finish_crossing=None),
                    dict(finish_crossing=dict(contract_version='finish-crossing/2')), None):
            with self.subTest(run=run), self.assertRaises(ValueError):
                select_contract(run)


class CrossingTest(unittest.TestCase):
    def test_offset_crossing_away_from_midpoint_succeeds_without_endpoint_at_origin(self):
        tracker = FinishCrossingTracker()
        samples = drive([(-6., 2.2), (4., 2.2)])
        decisions = run(tracker, samples)
        crossed = [d for d in decisions if d['crossed']]
        self.assertEqual(len(crossed), 1)
        crossing = crossed[0]['crossing']
        self.assertAlmostEqual(crossing['x'], 0., places=9)
        self.assertAlmostEqual(crossing['lateral_m'], 2.2, places=9)
        self.assertGreater(crossing['direction_cosine'], .99)
        # The run ends 4 m past the line and 4.6 m from origin; no radius applies.
        self.assertGreater(math.hypot(*samples[-1][1:]), 4.)
        self.assertEqual(decisions[-1]['outcome'], 'already_crossed')
        report = tracker.report()
        self.assertTrue(report['crossed'])
        self.assertEqual(report['last_candidate']['outcome'], 'crossed')
        self.assertEqual(report['last_outcome']['outcome'], 'already_crossed')

    def test_differing_start_and_final_headings_do_not_define_the_line(self):
        # Start leaving origin north-east, finish crossing diagonally south-east.
        # Headings are not inputs; only the fixed +X line through origin counts.
        tracker = FinishCrossingTracker()
        loop = [(0., 0.), (3., 3.), (-4., 3.), (-4., 1.5), (2., 0.)]
        decisions = run(tracker, drive(loop), eligible_from=40)
        crossed = [d for d in decisions if d['crossed']]
        self.assertEqual(len(crossed), 1)
        crossing = crossed[0]['crossing']
        self.assertAlmostEqual(crossing['x'], 0., places=9)
        self.assertTrue(0. < crossing['lateral_m'] < 3.)
        self.assertTrue(0. < crossing['direction_cosine'] < 1.)

    def test_startup_and_early_crossings_get_no_credit(self):
        tracker = FinishCrossingTracker()
        # Leave origin forward, return behind the line, cross again, all before
        # the first five ordered visits make the tracker eligible.
        samples = drive([(0., 0.), (2., 0.), (2., 2.), (-3., 2.), (2., 2.)])
        decisions = run(tracker, samples, eligible_from=len(samples))
        self.assertFalse(any(d['crossed'] for d in decisions))
        self.assertIn('ineligible', outcomes(decisions))
        report = tracker.report()
        self.assertIsNone(report['crossing'])
        self.assertEqual(report['last_candidate']['outcome'], 'ineligible')

    def test_crossing_without_eligible_approach_is_not_armed(self):
        # Eligibility begins only 0.3 m behind the line: no armed approach.
        tracker = FinishCrossingTracker()
        samples = drive([(-5., 0.), (-.3, 0.), (2., 0.)])
        start = next(i for i, s in enumerate(samples) if s[1] >= -.3)
        decisions = run(tracker, samples, eligible_from=start)
        self.assertFalse(any(d['crossed'] for d in decisions))
        self.assertIn('not_armed', outcomes(decisions))

    def test_stationary_on_or_near_line_never_crosses(self):
        tracker = FinishCrossingTracker()
        samples = drive([(-3., 0.), (0., 0.)])  # stops exactly on the line
        run(tracker, samples)
        decisions = [tracker.observe(samples[-1][0]+.05*k, 0., 0., eligible=True) for k in range(1, 41)]
        self.assertEqual(outcomes(decisions), {'stationary'})
        self.assertFalse(tracker.report()['crossed'])

    def test_tiny_forward_jitter_from_the_line_is_rejected(self):
        tracker = FinishCrossingTracker()
        samples = drive([(-3., 0.), (0., 0.)])
        run(tracker, samples)
        self.assertTrue(tracker.armed)
        t = samples[-1][0]
        jitter = tracker.observe(t+.05, 5e-7, 0., eligible=True)
        self.assertEqual(jitter['outcome'], 'tiny_jitter')
        self.assertFalse(jitter['crossed'])
        self.assertFalse(tracker.armed)
        later = [tracker.observe(t+.05*k, 5e-7, 0., eligible=True) for k in range(2, 22)]
        self.assertEqual(outcomes(later), {'stationary'})
        report = tracker.report()
        self.assertFalse(report['crossed'])
        self.assertEqual(report['last_candidate']['outcome'], 'tiny_jitter')

    def test_reverse_crossing_is_rejected_and_disarms(self):
        tracker = FinishCrossingTracker()
        # Start ahead, back across the line, then creep forward from 0.5 m behind.
        decisions = run(tracker, drive([(2., 1.), (-.5, 1.), (1., 1.)]))
        self.assertIn('reverse', outcomes(decisions))
        self.assertIn('not_armed', outcomes(decisions))
        self.assertFalse(any(d['crossed'] for d in decisions))

    def test_far_off_and_teleport_crossings_are_rejected(self):
        tracker = FinishCrossingTracker()
        # Armed inside the lane, then veers out to cross 4 m from the midpoint.
        decisions = run(tracker, drive([(-5., 2.), (-1.5, 2.), (1.5, 6.)]))
        self.assertIn('outside_span', outcomes(decisions))
        self.assertFalse(any(d['crossed'] for d in decisions))
        self.assertEqual(tracker.report()['last_candidate']['outcome'], 'outside_span')

        tracker = FinishCrossingTracker()
        samples = drive([(-5., 0.), (-2., 0.)])
        run(tracker, samples)
        t = samples[-1][0]
        self.assertEqual(tracker.observe(t+.05, 3., 0., eligible=True)['outcome'], 'step_too_long')
        later = tracker.observe(t+.1, 3.1, 0., eligible=True)
        self.assertEqual(later['outcome'], 'continuity_restart')
        self.assertFalse(tracker.report()['crossed'])

    def test_short_interval_jump_over_speed_limit_is_rejected(self):
        tracker = FinishCrossingTracker()
        samples = drive([(-4., 0.), (-.1, 0.)])
        run(tracker, samples)
        self.assertTrue(tracker.armed)
        t = samples[-1][0]
        # 0.22 m in 0.01 s is 22 m/s: inside the 1.2 m step bound, far over 2.2 m/s.
        jump = tracker.observe(t+.01, .12, 0., eligible=True)
        self.assertEqual(jump['outcome'], 'speed_too_high')
        self.assertFalse(jump['crossed'])
        self.assertFalse(tracker.armed)
        self.assertEqual(tracker.observe(t+.06, .2, 0., eligible=True)['outcome'], 'continuity_restart')
        self.assertFalse(tracker.report()['crossed'])

    def test_crossing_at_the_speed_limit_is_credited(self):
        tracker = FinishCrossingTracker()
        samples = drive([(-4., 0.), (-.05, 0.)])
        run(tracker, samples)
        decision = tracker.observe(samples[-1][0]+.05, .06, 0., eligible=True)  # 0.11 m / 0.05 s
        self.assertEqual(decision['outcome'], 'crossed')
        self.assertAlmostEqual(decision['crossing']['speed_mps'], 2.2, places=9)

    def test_non_finite_and_malformed_samples_fail_closed(self):
        for bad in ((math.nan, 0., 0.), (1., math.inf, 0.), (1., 0., None), (1., True, 0.),
                    (10**400, 0., 0.), (1., -10**400, 0.)):
            with self.subTest(bad=bad):
                tracker = FinishCrossingTracker()
                samples = drive([(-4., 0.), (-.1, 0.)])
                run(tracker, samples)
                self.assertTrue(tracker.armed)
                decision = tracker.observe(*bad, eligible=True)
                self.assertEqual(decision['outcome'], 'invalid_sample')
                self.assertTrue(all(map(math.isfinite, scalars(decision))))
                self.assertFalse(tracker.armed)
                # Continuity broke, so a sample past the line cannot be credited.
                self.assertEqual(tracker.observe(samples[-1][0]+.1, .1, 0., eligible=True)['outcome'],
                                 'continuity_restart')
        tracker = FinishCrossingTracker()
        self.assertEqual(tracker.observe(0., -2., 0., eligible=1)['outcome'], 'invalid_sample')

    def test_extreme_finite_values_overflowing_arithmetic_fail_closed(self):
        cases = (
            # Step subtraction overflows: x jumps from -1e308 to +1e308.
            (FinishCrossingTracker(), [(0., -1e308, 0.), (.05, 1e308, 0.)]),
            # Interval subtraction overflows.
            (FinishCrossingTracker(), [(-1e308, -2., 0.), (1e308, -2., 0.)]),
            # Projection subtraction overflows against an extreme line center.
            (FinishCrossingTracker(FinishLine(center_x=-1e308)), [(0., 1e308, 0.)]),
        )
        for tracker, bad in cases:
            with self.subTest(bad=bad):
                decisions = [tracker.observe(*s, eligible=True) for s in bad]
                self.assertEqual(decisions[-1]['outcome'], 'invalid_sample')
                self.assertFalse(tracker.armed)
                self.assertIsNone(tracker.previous)
                report = tracker.report()
                for value in (decisions, report):
                    self.assertTrue(all(map(math.isfinite, scalars(value))))
                self.assertEqual(report['last_outcome']['outcome'], 'invalid_sample')
        # An ordinary crossing still succeeds after the overflow is rejected.
        tracker = cases[0][0]
        decisions = run(tracker, drive([(-4., 1.), (2., 1.)], t=1.))
        self.assertEqual(decisions[0]['outcome'], 'continuity_restart')
        self.assertTrue(tracker.report()['crossed'])

    def test_non_increasing_stamps_break_continuity(self):
        tracker = FinishCrossingTracker()
        run(tracker, drive([(-4., 0.), (-.05, 0.)]))
        self.assertEqual(tracker.observe(0., .05, 0., eligible=True)['outcome'], 'discontinuous_interval')
        self.assertFalse(tracker.report()['crossed'])


if __name__ == '__main__':
    unittest.main()
