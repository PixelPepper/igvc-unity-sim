"""Lane guidance must still obey observed collision geometry."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from observed_navigation import plan_observed_navigation


class ObservedNavigationTests(unittest.TestCase):
    def test_remembered_straight_yields_to_broad_corner_direction(self):
        hint={'entry':[12.,5.], 'direction':[1.,0.]}
        plan=plan_observed_navigation((0.,0.),.2,110,110,[0]*12100,
            (5.,5.),0.,(5.,16.),[],heading_hint=hint,robot_radius=.5,
            forward_only=True,minimum_turn_radius=.65)
        self.assertIsNotNone(plan)
        self.assertEqual(plan['diagnostics']['guidance'],'broad_gps')

    def test_skewed_gps_does_not_pull_goal_outside_visible_corridor(self):
        paint = [(x/5, y) for x in range(25, 91) for y in (4., 10.)]
        plan = plan_observed_navigation((0., 0.), .2, 110, 110, [0]*12100,
            (2., 7.), 0., (20., 15.), paint, robot_radius=.5,
            forward_only=True, minimum_turn_radius=.65)
        self.assertIsNotNone(plan)
        self.assertEqual(plan['diagnostics']['guidance'], 'observed_lane_corridor')
        self.assertLess(abs(plan['local_goal'][1]-7.), .5)

    def test_observed_wall_blocks_lane_proposal(self):
        paint = [(x/5, y) for x in range(25, 91) for y in (4., 10.)]
        costs = [0]*12100
        for y in range(110):
            for x in range(18, 21):
                costs[y*110+x] = 100
        plan = plan_observed_navigation((0., 0.), .2, 110, 110, costs,
            (2., 7.), 0., (20., 15.), paint, robot_radius=.5,
            forward_only=True, minimum_turn_radius=.65)
        if plan is not None:
            self.assertEqual(plan['diagnostics']['guidance'], 'observed_lane_corridor')
            self.assertTrue(all(x < 3.6 for x, _ in plan['path']))


if __name__ == '__main__':
    unittest.main()
