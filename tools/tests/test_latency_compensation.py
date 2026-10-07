"""Offline checks for opt-in planning latency compensation."""
from pathlib import Path
import math
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from latency_compensation import LatencyCompensator


class LatencyCompensationTests(unittest.TestCase):
    def test_disabled_or_still_is_identity(self):
        pose = (1., 2., .3)
        self.assertEqual(LatencyCompensator(False).predict(pose, (.6, .4)), pose)
        self.assertEqual(LatencyCompensator(True).predict(pose, (0., 0.)), pose)
        self.assertEqual(LatencyCompensator(True).predict(pose, None), pose)

    def test_straight_and_arc_motion(self):
        c = LatencyCompensator(True, initial_latency_s=.5)
        x, y, yaw = c.predict((0., 0., 0.), (.6, 0.))
        self.assertAlmostEqual(x, .3); self.assertAlmostEqual(y, 0.); self.assertAlmostEqual(yaw, 0.)
        # Quarter turn: radius v/w = 1 m, quarter-circle end point (1, 1) heading pi/2.
        c = LatencyCompensator(True, initial_latency_s=math.pi/2, max_shift_m=5.)
        x, y, yaw = c.predict((0., 0., 0.), (1., 1.))
        self.assertAlmostEqual(x, 1., places=6); self.assertAlmostEqual(y, 1., places=6); self.assertAlmostEqual(yaw, math.pi/2)

    def test_latency_average_is_bounded(self):
        c = LatencyCompensator(True, initial_latency_s=.6, max_latency_s=1.2)
        c.observe_latency(.2); self.assertAlmostEqual(c.latency, .2)
        for v in (.6, .7, .8): c.observe_latency(v)
        self.assertAlmostEqual(c.latency, .2)  # low percentile: biased short
        c.observe_latency(10.); self.assertLessEqual(c.latency, 1.2)
        for bad in (None, float('nan'), -1.):
            before = c.latency; c.observe_latency(bad); self.assertEqual(c.latency, before)

    def test_shift_is_capped(self):
        c = LatencyCompensator(True, initial_latency_s=1.2, max_shift_m=.5)
        x, y, _ = c.predict((0., 0., 0.), (2., 0.))
        self.assertAlmostEqual(math.hypot(x, y), .5)


if __name__ == '__main__':
    unittest.main()
