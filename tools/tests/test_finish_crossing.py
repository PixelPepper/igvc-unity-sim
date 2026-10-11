"""Finish crossing contract: offset crossing, stationary/reverse/early/teleport rejection, invalid inputs."""
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from finish_crossing import (CONTRACT_VERSION, FIXTURE_LINE, FinishCrossingTracker,  # noqa: E402
                             FinishLine)


def drive(points, *, speed=1.5, dt=.05, t=0.):
    """Base_footprint samples along a polyline at constant speed, endpoints included."""
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


class FixtureLineTest(unittest.TestCase):
    def test_fixture_line_is_public_origin_with_ros_plus_x_normal(self):
        self.assertEqual(FIXTURE_LINE.center, (0., 0.))
        self.assertEqual(FIXTURE_LINE.normal, (1., 0.))
        self.assertEqual(FIXTURE_LINE.half_span_m, 3.)
        self.assertEqual(FinishCrossingTracker().policy()['contract_version'], CONTRACT_VERSION)

    def test_invalid_line_definitions_are_rejected(self):
        for kwargs in (dict(center_x=math.nan), dict(normal_x=math.inf), dict(normal_x=.5),
                       dict(half_span_m=0.), dict(half_span_m=-1.), dict(half_span_m=True)):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                FinishLine(**kwargs)
        with self.assertRaises(ValueError):
            FinishCrossingTracker(max_step_m=math.nan)


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
        self.assertTrue(tracker.report()['crossed'])

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
        self.assertIsNone(tracker.report()['crossing'])

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

        tracker = FinishCrossingTracker()
        decisions = run(tracker, drive([(-5., 0.), (-2., 0.)]))
        decisions.append(tracker.observe(decisions[-1]['sample_index']*.05+.05, 3., 0., eligible=True))
        self.assertEqual(decisions[-1]['outcome'], 'step_too_long')
        later = tracker.observe(100., 3.1, 0., eligible=True)
        self.assertEqual(later['outcome'], 'continuity_restart')
        self.assertFalse(tracker.report()['crossed'])

    def test_non_finite_and_malformed_samples_fail_closed(self):
        for bad in ((math.nan, 0., 0.), (1., math.inf, 0.), (1., 0., None), (1., True, 0.)):
            with self.subTest(bad=bad):
                tracker = FinishCrossingTracker()
                run(tracker, drive([(-4., 0.), (-.1, 0.)]))
                self.assertTrue(tracker.armed)
                self.assertEqual(tracker.observe(*bad, eligible=True)['outcome'], 'invalid_sample')
                self.assertFalse(tracker.armed)
                # Continuity broke, so a sample past the line cannot be credited.
                self.assertEqual(tracker.observe(99., .1, 0., eligible=True)['outcome'],
                                 'continuity_restart')
        tracker = FinishCrossingTracker()
        self.assertEqual(tracker.observe(0., -2., 0., eligible=1)['outcome'], 'invalid_sample')

    def test_non_increasing_stamps_break_continuity(self):
        tracker = FinishCrossingTracker()
        run(tracker, drive([(-4., 0.), (-.05, 0.)]))
        self.assertEqual(tracker.observe(0., .05, 0., eligible=True)['outcome'], 'discontinuous_interval')
        self.assertFalse(tracker.report()['crossed'])


if __name__ == '__main__':
    unittest.main()
