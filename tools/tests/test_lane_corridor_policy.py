import sys
from pathlib import Path
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lane_corridor_policy import propose_lane_corridor


def stripe(y, start=2., end=12., step=.2):
    x = np.arange(start, end+step/2, step)
    return np.column_stack((x, np.full_like(x, y)))


class LaneCorridorTests(unittest.TestCase):
    def test_inside_pair_centers_independently_of_skewed_gps(self):
        points = np.vstack((stripe(-3), stripe(3)))
        result = propose_lane_corridor(points, [0, 1], 0., [20, 14])
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result['entry'][1], 0., delta=.1)
        self.assertGreater(result['entry'][0], 2.)
        self.assertEqual(result['diagnostics']['entry_mode'], 'inside')

    def test_long_lookahead_stays_within_observed_support(self):
        points = np.vstack((stripe(-3, 2, 10), stripe(3, 2, 10)))
        short = propose_lane_corridor(points, [0, 0], 0., [20, 0])
        long = propose_lane_corridor(points, [0, 0], 0., [20, 0], lookahead=7.)
        clamped = propose_lane_corridor(points, [0, 0], 0., [20, 0], lookahead=14.)
        self.assertGreater(long['entry'][0], short['entry'][0])
        self.assertAlmostEqual(long['entry'][0], 7.)
        self.assertLessEqual(clamped['entry'][0], 10.)
        ends = [max(p[0] for p in segment) for segment in clamped['diagnostics']['segments']]
        self.assertAlmostEqual(clamped['entry'][0], min(ends))

    def test_long_lookahead_preserves_outside_mouth_and_rejects_invalid_values(self):
        points = np.vstack((stripe(-3, 5, 14), stripe(3, 5, 14)))
        short = propose_lane_corridor(points, [0, 5], 0., [20, 0])
        long = propose_lane_corridor(points, [0, 5], 0., [20, 0], lookahead=7.)
        self.assertEqual(short['entry'], long['entry'])
        for lookahead in (0., -1., 15., float('nan'), float('inf')):
            self.assertIsNone(propose_lane_corridor(points, [0, 5], 0., [20, 0], lookahead=lookahead))

    def test_reentry_uses_visible_mouth_not_crossing_side_paint(self):
        points = np.vstack((stripe(-3, 5, 14), stripe(3, 5, 14)))
        result = propose_lane_corridor(points, [0, 5], 0., [20, 12])
        self.assertIsNotNone(result)
        self.assertLess(result['entry'][0], 5.)
        self.assertAlmostEqual(result['entry'][1], 0., delta=.1)
        self.assertEqual(result['diagnostics']['entry_mode'], 'visible_mouth')

    def test_outside_continuous_sides_does_not_propose_crossing(self):
        points = np.vstack((stripe(-3, -2, 12), stripe(3, -2, 12)))
        self.assertIsNone(propose_lane_corridor(points, [0, 5], 0., [20, 0]))

    def test_gap_between_observed_segments_allows_reentry(self):
        points = np.vstack([stripe(side, start, end) for side in (-3., 3.)
                            for start, end in ((0., 4.), (8., 14.))])
        result = propose_lane_corridor(points, [4., 5.], 0., [20., 10.])
        self.assertIsNotNone(result)
        self.assertGreater(result['entry'][0], 4.)
        self.assertLess(result['entry'][0], 8.)
        self.assertAlmostEqual(result['entry'][1], 0., delta=.1)

    def test_single_crossing_short_and_behind_lines_are_rejected(self):
        crossed = np.vstack((stripe(0), np.column_stack((np.full(51, 5.), np.linspace(-5, 5, 51)))))
        for points in (stripe(-3), crossed, np.vstack((stripe(-3, 4, 6), stripe(3, 4, 6))),
                       np.vstack((stripe(-3, -14, -4), stripe(3, -14, -4)))):
            with self.subTest(points=points.shape):
                self.assertIsNone(propose_lane_corridor(points, [0, 0], 0., [20, 0]))

    def test_intervening_parallel_barrier_is_not_ignored(self):
        points = np.vstack((stripe(-3), stripe(3), stripe(0)))
        result = propose_lane_corridor(points, [0, -1.5], 0., [20, -1.5])
        self.assertIsNotNone(result)
        self.assertLess(result['diagnostics']['width_m'], 4.)
        self.assertAlmostEqual(result['entry'][1], -1.5, delta=.1)

    def test_rotation_and_translation_preserve_observed_proposal(self):
        points = np.vstack((stripe(-3), stripe(3)))
        angle = .8;rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        origin = np.array([17., -8.])
        result = propose_lane_corridor(points@rotation.T+origin, origin, angle, np.array([20., 8.])@rotation.T+origin)
        self.assertIsNotNone(result)
        entry = (np.array(result['entry'])-origin)@rotation
        self.assertAlmostEqual(entry[1], 0., delta=.15)

    def test_no_longitudinal_overlap_or_impossible_width(self):
        for points in (np.vstack((stripe(-3, 0, 5), stripe(3, 8, 13))),
                       np.vstack((stripe(-5), stripe(5)))):
            self.assertIsNone(propose_lane_corridor(points, [0, 0], 0., [20, 0]))

    def test_behind_destination_and_nonfinite_observations_are_rejected(self):
        points = np.vstack((stripe(-3), stripe(3)))
        self.assertIsNone(propose_lane_corridor(points, [0, 0], 0., [-20, 0]))
        points[0, 0] = np.nan
        self.assertIsNone(propose_lane_corridor(points, [0, 0], 0., [20, 0]))
