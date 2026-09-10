import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from approach_speed import approach_speed


class ApproachSpeedChecks(unittest.TestCase):
    def test_far_goal_caps_at_competition_margin(self):
        self.assertEqual(approach_speed(100), 2.2)
        self.assertEqual(approach_speed(100, maximum=1.0), 1.0)

    def test_braking_and_latency_consume_available_distance(self):
        for distance in (0.3, 0.5, 1.0, 1.5):
            speed = approach_speed(distance)
            self.assertAlmostEqual(speed * .2 + speed**2 / (2 * 2.0), distance - .2)

    def test_arrival_floor_never_sends_unlimited_sentinel(self):
        for distance in (0., .1, .2, .200001):
            self.assertEqual(approach_speed(distance), .05)

    def test_monotonic_distance_and_latency(self):
        speeds = [approach_speed(i / 100) for i in range(501)]
        self.assertTrue(all(a <= b for a, b in zip(speeds, speeds[1:])))
        self.assertLess(approach_speed(1, latency=.4), approach_speed(1, latency=.2))
        self.assertLess(approach_speed(1, deceleration=1), approach_speed(1, deceleration=2))

    def test_zero_latency_matches_constant_deceleration(self):
        self.assertAlmostEqual(approach_speed(.7, latency=0), math.sqrt(2))

    def test_invalid_inputs(self):
        for distance in (-1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                approach_speed(distance)
        for keyword, value in [('maximum', 0), ('maximum', 2.3), ('deceleration', 0),
                               ('latency', -1), ('reserve', -1), ('maximum', float('nan')),
                               ('deceleration', float('inf')), ('latency', float('nan')),
                               ('reserve', float('inf'))]:
            with self.subTest(keyword=keyword, value=value), self.assertRaises(ValueError):
                approach_speed(1, **{keyword: value})


if __name__ == '__main__':
    unittest.main()
