import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from course_progress import CourseProgress, ProgressError


class ProgressTests(unittest.TestCase):
    def test_projection_excludes_segment_start_beyond_reachable_interval(self):
        audit = CourseProgress([(0, 0), (1, 0), (2, 0)])
        audit.progress = .9
        # A nearer later segment starts at 1.0, outside the allowed [.85,.95].
        # This reproduces the empty-intersection clamp from the seed-2027 failure.
        arc, lateral = audit._project((1.4, 0), max_step=.05)
        self.assertAlmostEqual(arc, .95)
        self.assertAlmostEqual(lateral, .45)

    def test_stationary_projection_cannot_gain_arc_from_later_segment(self):
        audit = CourseProgress([(0, 0), (1, 0), (2, 0)])
        audit.progress = .9
        arc, _ = audit._project((1.4, 0), max_step=0.)
        self.assertAlmostEqual(arc, .9)

    def walk(self, audit, points, start=0.):
        for i, (x, y) in enumerate(points):
            audit.update(x, y, start + i * .1)

    def test_straight_stationary_and_completion(self):
        audit = CourseProgress([(0, 0), (10, 0)], waypoint_arcs=[2, 5, 10])
        self.walk(audit, [(i / 10, 0) for i in range(101)])
        audit.update(10, 0, 10.1)
        self.assertTrue(audit.snapshot()['complete'])
        self.assertAlmostEqual(audit.traveled, 10)

    def test_closed_route_does_not_complete_at_start(self):
        route = [(0, 0), (4, 0), (4, 4), (0, 4), (0, 0)]
        audit = CourseProgress(route)
        audit.update(0, 0, 0)
        self.assertFalse(audit.snapshot()['complete'])
        samples = []
        for a, b in zip(route, route[1:]):
            samples.extend([(a[0] + (b[0]-a[0])*i/40,
                             a[1] + (b[1]-a[1])*i/40) for i in range(1, 41)])
        self.walk(audit, samples, .1)
        self.assertTrue(audit.snapshot()['complete'])

    def test_shortcut_across_course_rejected(self):
        audit = CourseProgress([(0, 0), (5, 0), (5, 5), (0, 5), (0, 0)])
        self.walk(audit, [(i / 10, 0) for i in range(26)])
        with self.assertRaises(ProgressError):
            self.walk(audit, [(2.5, i / 10) for i in range(1, 26)], 2.6)
        self.assertFalse(audit.snapshot()['complete'])

    def test_reverse_two_metres_then_recovery(self):
        audit = CourseProgress([(0, 0), (10, 0)])
        self.walk(audit, [(i / 10, 0) for i in range(41)])
        self.walk(audit, [(4-i/10, 0) for i in range(1, 21)], 4.1)
        self.assertAlmostEqual(audit.snapshot()['reverse_from_max_m'], 2)
        with self.assertRaisesRegex(ProgressError, 'Reverse'):
            audit.update(1.9, 0, 6.1)

    def test_nearby_parallel_branch_cannot_jump(self):
        audit = CourseProgress([(0, 0), (10, 0), (10, .5), (0, .5)])
        self.walk(audit, [(i/10, 0) for i in range(41)])
        self.walk(audit, [(4, i/10) for i in range(1, 6)], 4.1)
        self.assertLess(audit.progress, 5)
        self.assertFalse(audit.snapshot()['complete'])

    def test_teleport_and_reset_latch_failure(self):
        audit = CourseProgress([(0, 0), (10, 0)])
        audit.update(0, 0, 0)
        with self.assertRaisesRegex(ProgressError, 'Teleport'):
            audit.update(.251, 0, .1)
        with self.assertRaisesRegex(ProgressError, 'already invalid'):
            audit.update(.1, 0, .2)
        audit = CourseProgress([(0, 0), (10, 0)])
        audit.update(0, 0, 1, run_id='a')
        with self.assertRaisesRegex(ProgressError, 'reset forbidden'):
            audit.update(0, 0, 1.1, run_id='b')

    def test_saved_pause_resume_retains_order_and_distance(self):
        audit = CourseProgress([(0, 0), (10, 0)], waypoint_arcs=[2, 5, 10])
        self.walk(audit, [(i/10, 0) for i in range(31)])
        restored = CourseProgress.from_state(audit.export_state())
        restored.restore(audit.snapshot(), (3, 0), 100, None)
        self.assertEqual(restored.next_waypoint, 1)
        self.assertEqual(restored.maximum, 3)
        self.assertEqual(restored.traveled, audit.traveled)
        restored.update(3.1, 0, 100.1)
        self.assertAlmostEqual(restored.traveled, 3.1)
        with self.assertRaisesRegex(ProgressError, 'Resume requires'):
            restored.restore(restored.snapshot(), (3.21, 0), 110, None)

    def test_final_goal_can_stop_point_two_metres_early(self):
        audit = CourseProgress([(0, 0), (10, 0)], waypoint_arcs=[2, 5, 10],
                               waypoint_tolerance=.4)
        self.walk(audit, [(i/10, 0) for i in range(99)])
        self.assertTrue(audit.snapshot()['complete'])

    def test_small_reverse_then_full_forward_recovery(self):
        audit = CourseProgress([(0, 0), (5, 0)])
        self.walk(audit, [(i/10, 0) for i in range(31)])
        self.walk(audit, [(3-i/10, 0) for i in range(1, 6)], 3.1)
        self.walk(audit, [(2.5+i/10, 0) for i in range(1, 26)], 3.6)
        self.assertTrue(audit.snapshot()['complete'])
        self.assertAlmostEqual(audit.traveled, 6)

    def test_offset_obstacle_checkpoint_uses_actual_goal_xy(self):
        audit = CourseProgress([(0, 0), (5, 0)], waypoint_arcs=[2, 5],
                               waypoint_xy=[(2, 1), (5, 0)], waypoint_tolerance=.4)
        self.walk(audit, [(i/10, i/20) for i in range(21)])
        self.assertEqual(audit.next_waypoint, 1)
        self.walk(audit, [(2+i/10, 1-i/30) for i in range(1, 31)], 2.1)
        self.assertTrue(audit.snapshot()['complete'])

    def test_inside_corner_projection_is_continuous(self):
        audit = CourseProgress([(0, 0), (4, 0), (4, 4)], waypoint_arcs=[8])
        self.walk(audit, [(i/10, 0) for i in range(31)])
        self.walk(audit, [(3, i/10) for i in range(1, 11)], 3.1)
        previous = audit.progress
        # At the inside corner the unconstrained nearest segment switches by
        # roughly 2 m; traversed distance remains only 1 cm for this sample.
        audit.update(3.01, 1.01, 4.1)
        self.assertLessEqual(audit.progress - previous, 1.5 * (2**.5) * .01 + 1e-8)
        previous = audit.progress
        audit.update(3.01, 1.01, 4.2)
        self.assertEqual(audit.progress, previous)


if __name__ == '__main__':
    unittest.main()
