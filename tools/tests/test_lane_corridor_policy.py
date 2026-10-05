import sys
from pathlib import Path
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lane_corridor_policy import propose_lane_corridor, replay_lane_corridor


def stripe(y, start=2., end=12., step=.2):
    x = np.arange(start, end+step/2, step)
    return np.column_stack((x, np.full_like(x, y)))


class LaneCorridorTests(unittest.TestCase):
    def test_inside_pair_centers_independently_of_skewed_gps(self):
        points = np.vstack((stripe(-3), stripe(3)))
        result = propose_lane_corridor(points, [4, 1], 0., [20, 14])
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result['entry'][1], 0., delta=.1)
        self.assertGreater(result['entry'][0], 2.)
        self.assertEqual(result['diagnostics']['entry_mode'], 'inside')

    def test_long_lookahead_stays_within_observed_support(self):
        points = np.vstack((stripe(-3, 2, 10), stripe(3, 2, 10)))
        short = propose_lane_corridor(points, [3, 0], 0., [20, 0])
        long = propose_lane_corridor(points, [3, 0], 0., [20, 0], lookahead=7.)
        clamped = propose_lane_corridor(points, [3, 0], 0., [20, 0], lookahead=14.)
        self.assertGreater(long['entry'][0], short['entry'][0])
        self.assertEqual(long['entry'],clamped['entry'])
        self.assertLessEqual(clamped['entry'][0], 10.)
        ends = [max(p[0] for p in segment) for segment in clamped['diagnostics']['segments']]
        self.assertAlmostEqual(clamped['entry'][0], min(ends))

    def test_before_observed_overlap_uses_mouth_with_nearby_destination(self):
        points = np.vstack((stripe(-1.5, 0, 8), stripe(1.5, 0, 8)))
        # The robot is between the side-line extensions, but three metres
        # before the paint. An inside lookahead would overshoot the GPS goal
        # at x=2 and incorrectly reject this plainly supported approach.
        short = propose_lane_corridor(points, [-3, 0], 0., [2, 0])
        long = propose_lane_corridor(points, [-3, 0], 0., [2, 0], lookahead=7.)
        self.assertIsNotNone(short)
        self.assertIsNotNone(long)
        self.assertEqual(long['diagnostics']['entry_mode'],'visible_mouth')
        self.assertGreater(long['entry'][0],-.7)
        self.assertLess(long['entry'][0],0.)
        self.assertAlmostEqual(long['entry'][1],0.,delta=.05)
        self.assertEqual(short['entry'],long['entry'])
        # The fix must not reverse intent or invent continued paint past its end.
        self.assertIsNone(propose_lane_corridor(points,[-3,0],0.,[-5,0],lookahead=7.))
        self.assertIsNone(propose_lane_corridor(points,[10,0],0.,[20,0],lookahead=7.))
        # A vehicle within longitudinal support, but outside its continuous
        # painted side, still cannot cut across that side to enter.
        self.assertIsNone(propose_lane_corridor(points,[3,3],0.,[10,0],lookahead=7.))

    def test_long_lookahead_preserves_outside_mouth_and_rejects_invalid_values(self):
        points = np.vstack((stripe(-3, 5, 14), stripe(3, 5, 14)))
        short = propose_lane_corridor(points, [0, 5], 0., [20, 0])
        long = propose_lane_corridor(points, [0, 5], 0., [20, 0], lookahead=7.)
        self.assertEqual(short['entry'], long['entry'])
        for lookahead in (0., -1., 15., float('nan'), float('inf')):
            self.assertIsNone(propose_lane_corridor(points, [0, 5], 0., [20, 0], lookahead=lookahead))

    def test_aligned_approach_hands_off_at_mouth_into_actual_observed_overlap(self):
        points = np.vstack((stripe(-3), stripe(3)))
        approach = propose_lane_corridor(points, [0,0], 0., [20,0])
        mouth = approach['entry'][0]
        lo = max(min(p[0] for p in s) for s in approach['diagnostics']['segments'])
        near = propose_lane_corridor(points, [mouth-.1,0], 0., [20,0])
        reached = propose_lane_corridor(points, [mouth+.1,0], 0., [20,0])
        inside = propose_lane_corridor(points, [lo+.2,0], 0., [20,0])
        self.assertEqual(approach['diagnostics']['entry_mode'], 'visible_mouth')
        for result in (near, reached):
            self.assertIsNotNone(result)
            self.assertEqual(result['diagnostics']['entry_mode'], 'entering')
            observed_lo = max(min(p[0] for p in s) for s in result['diagnostics']['segments'])
            observed_hi = min(max(p[0] for p in s) for s in result['diagnostics']['segments'])
            self.assertGreaterEqual(result['entry'][0], observed_lo)
            self.assertLessEqual(result['entry'][0], observed_hi)
            self.assertGreater(result['entry'][0], mouth+1.)
        self.assertEqual(inside['diagnostics']['entry_mode'], 'inside')

    def test_farther_approach_does_not_skip_observed_mouth(self):
        points = np.vstack((stripe(-3), stripe(3)))
        approach = propose_lane_corridor(points, [0,0], 0., [20,0])
        mouth = approach['entry'][0]
        for lookahead in (3.,14.):
            result = propose_lane_corridor(points, [mouth-.4,0], 0., [20,0], lookahead=lookahead)
            self.assertEqual(result['diagnostics']['entry_mode'], 'visible_mouth')
            self.assertAlmostEqual(result['entry'][0], mouth)

    def test_sideways_approach_at_mouth_does_not_advance_into_overlap(self):
        points = np.vstack((stripe(-3), stripe(3)))
        approach = propose_lane_corridor(points, [0,0], 0., [20,0])
        mouth = approach['entry'][0]
        # Lateral offset keeps the mouth ahead of a sideways approach so the
        # diagnostic must propose the mouth, not merely fail a tiny-goal gate.
        for yaw in (.4, 1.):
            result = propose_lane_corridor(points, [mouth-.1,-1.], yaw, [20,0])
            self.assertIsNotNone(result)
            self.assertEqual(result['diagnostics']['entry_mode'], 'visible_mouth')
            self.assertLess(result['entry'][0], min(p[0] for s in result['diagnostics']['segments'] for p in s))
        diagnostics = {}
        result = propose_lane_corridor(points, [mouth-.1,2.9], 0., [20,0], diagnostics=diagnostics)
        self.assertIsNone(result)
        self.assertEqual(diagnostics['top_candidate']['entry_mode'], 'visible_mouth')

    def test_entering_target_ignores_skewed_gps_and_clamps_to_observed_end(self):
        points = np.vstack((stripe(-3), stripe(3)))
        approach = propose_lane_corridor(points, [0,0], 0., [20,0])
        robot = [approach['entry'][0]+.1, .5]
        straight = propose_lane_corridor(points, robot, .2, [20,0], lookahead=14.)
        skewed = propose_lane_corridor(points, robot, .2, [20,14], lookahead=14.)
        self.assertEqual(skewed['diagnostics']['entry_mode'], 'entering')
        self.assertEqual(straight['entry'], skewed['entry'])
        self.assertAlmostEqual(skewed['entry'][1], 0., delta=.1)
        end = min(max(p[0] for p in segment) for segment in skewed['diagnostics']['segments'])
        self.assertAlmostEqual(skewed['entry'][0], end)

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

    def test_diagnostics_preserve_selected_geometry_and_explain_choice(self):
        fixtures = [np.vstack((stripe(-3), stripe(3))),
                    np.vstack((stripe(-3, 5, 14), stripe(3, 5, 14))),
                    np.vstack((stripe(-3), stripe(3), stripe(0)))]
        for points, robot in zip(fixtures, ([0, 1], [0, 5], [0, -1.5])):
            with self.subTest(robot=robot):
                original = propose_lane_corridor(points, robot, 0., [20, 0])
                diagnostics = {'previous': 'removed'}
                explained = propose_lane_corridor(points, robot, 0., [20, 0], diagnostics=diagnostics)
                self.assertEqual(explained, original)
                self.assertEqual(diagnostics['status'], 'accepted')
                self.assertNotIn('previous', diagnostics)
                self.assertEqual(diagnostics['top_candidate']['entry'], original['entry'])
                self.assertEqual(diagnostics['selected_pair'], diagnostics['top_candidate']['pair'])
                self.assertLessEqual(len(diagnostics['segments']), 8)
                self.assertLessEqual(len(diagnostics['pair_candidates']), 28)
        self.assertGreater(diagnostics['pair_rejection_counts']['intervening_parallel_barrier'], 0)

    def test_missing_corridor_reasons_survive_none_result(self):
        examples = [([], 'invalid_input'), (stripe(0, 4, 5), 'insufficient_input_points'),
                    (np.vstack((stripe(-3, -14, -4), stripe(3, -14, -4))), 'insufficient_points_after_spatial_gates'),
                    (stripe(-3), 'insufficient_extracted_segments'),
                    (np.vstack((stripe(-5), stripe(5))), 'all_pairs_rejected')]
        for points, reason in examples:
            with self.subTest(reason=reason):
                diagnostics = {}
                original = propose_lane_corridor(points, [0, 0], 0., [20, 0])
                self.assertIsNone(original)
                self.assertIsNone(propose_lane_corridor(points, [0, 0], 0., [20, 0], diagnostics=diagnostics))
                self.assertEqual(diagnostics['reason'], reason)
        self.assertEqual(diagnostics['pair_rejection_counts']['width_above_maximum'], 1)
        self.assertEqual(diagnostics['top_candidate']['reason'], 'width_above_maximum')

    def test_gating_counts_explain_duplicates_and_behind_points(self):
        points = np.vstack((stripe(-3), stripe(3)))
        raw = np.vstack((points, points, [[100, 100], [-10, 0]]))
        diagnostics = {}
        propose_lane_corridor(raw, [0, 0], 0., [20, 0], diagnostics=diagnostics)
        counts = diagnostics['point_counts']
        self.assertEqual(counts['input'], len(raw))
        self.assertEqual(counts['outside_range'], 1)
        self.assertEqual(counts['behind_rear_gate'], 1)
        self.assertEqual(counts['after_deduplication'], len(points))
        self.assertGreater(diagnostics['segment_sampling_trials'], 0)
        self.assertGreater(sum(diagnostics['segment_rejection_counts'].values()), 0)

    def test_replay_can_change_one_gate_without_changing_production(self):
        angle = np.radians(80.)
        rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        points = np.vstack((stripe(-3), stripe(3))) @ rotation.T
        destination = np.array([20., 0.]) @ rotation.T
        diagnostics = {}
        self.assertIsNone(propose_lane_corridor(points, [0, 0], 0., destination, diagnostics=diagnostics))
        self.assertGreater(diagnostics['pair_rejection_counts']['corridor_heading_below_gate'], 0)
        result = replay_lane_corridor(points, [0, 0], 0., destination, variation={'heading_gate': .1}, diagnostics=diagnostics)
        self.assertIsNotNone(result)
        self.assertEqual(diagnostics['replay_variation'], {'heading_gate': .1})
        self.assertIsNone(propose_lane_corridor(points, [0, 0], 0., destination))
        with self.assertRaises(ValueError):
            replay_lane_corridor(points, [0, 0], 0., destination, variation={'heading_gate': .1, 'segment_span': 2.})
