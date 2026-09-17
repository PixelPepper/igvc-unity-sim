"""Behavioural checks for navigation using only observed sensor costs."""

import ast
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sensor_route_policy import select_local_goal


class SensorRoutePolicyTests(unittest.TestCase):
    size = 60
    resolution = .2

    def grid(self):
        return [0] * (self.size * self.size)

    def run_policy(self, costs, start=(2.1, 6.1), destination=(10.1, 6.1), **kwargs):
        return select_local_goal((0, 0), self.resolution, self.size, self.size,
                                 costs, start, 0., destination, **kwargs)

    def mark(self, costs, x1, x2, y1, y2, cost=100):
        for y in range(y1, y2):
            for x in range(x1, x2):
                costs[y * self.size + x] = cost

    def assert_footprint_clear(self, result, costs):
        self.assertIsNotNone(result)
        blocked = [(x * .2, y * .2) for y in range(self.size)
                   for x in range(self.size) if costs[y * self.size + x] < 0
                   or costs[y * self.size + x] >= 100]
        # Sample swept path, measuring to obstacle squares rather than centres.
        for a, b in zip(result['path'], result['path'][1:]):
            for t in (0., .25, .5, .75, 1.):
                px, py = (a[i] + t * (b[i] - a[i]) for i in (0, 1))
                centre_cost = costs[math.floor(py / .2) * self.size + math.floor(px / .2)]
                self.assertTrue(0 <= centre_cost < 99)
                for x, y in blocked:
                    distance = math.hypot(max(x - px, 0, px - x - .2),
                                          max(y - py, 0, py - y - .2))
                    self.assertGreaterEqual(distance + 1e-9, .65)

    def test_observed_obstacle_detour(self):
        costs = self.grid()
        self.mark(costs, 24, 27, 20, 40)
        result = self.run_policy(costs, lookahead=14.)
        self.assert_footprint_clear(result, costs)
        self.assertGreater(result['local_goal'][0], 7.)
        self.assertTrue(any(abs(p[1] - 6.1) > 2.5 for p in result['path']))

    def test_painted_barrier_and_unknown_are_impassable(self):
        for cost in (-1, 100):
            with self.subTest(cost=cost):
                costs = self.grid()
                self.mark(costs, 24, 27, 0, 60, cost)
                result = self.run_policy(costs, lookahead=14.)
                self.assert_footprint_clear(result, costs)
                self.assertLess(result['local_goal'][0], 4.2)

    def test_inscribed_band_is_not_dilated_twice(self):
        costs = self.grid()
        # A 2.2 m corridor between physical walls, with existing 0.6 m
        # inscribed bands. Its middle safely fits the unchanged 0.65 m radius.
        self.mark(costs, 0, 60, 0, 25, 100)
        self.mark(costs, 0, 60, 36, 60, 100)
        self.mark(costs, 0, 60, 25, 28, 99)
        self.mark(costs, 0, 60, 33, 36, 99)
        result = self.run_policy(costs, lookahead=14.)
        self.assert_footprint_clear(result, costs)
        self.assertLess(math.dist(result['local_goal'], (10.1, 6.1)), .3)
        self.assertEqual(result['diagnostics']['robot_radius'], .65)

    def test_inscribed_cells_still_block_robot_centres(self):
        costs = self.grid()
        self.mark(costs, 24, 27, 0, 60, 99)
        result = self.run_policy(costs, lookahead=14.)
        self.assert_footprint_clear(result, costs)
        self.assertLess(result['local_goal'][0], 4.8)
        self.assertIsNone(self.run_policy(costs, start=(4.9, 6.1)))

    def test_cost_98_remains_traversable(self):
        costs = [98] * (self.size * self.size)
        result = self.run_policy(costs)
        self.assert_footprint_clear(result, costs)
        self.assertGreater(result['local_goal'][0], 2.1)

    def test_goal_bias_cannot_cross_wall(self):
        costs = self.grid()
        self.mark(costs, 24, 27, 0, 60)
        result = self.run_policy(costs, start=(3.9, 6.1), destination=(1000., 6.1))
        self.assertIsNone(result)

    def test_new_sensor_obstacle_changes_detour(self):
        lower, upper = self.grid(), self.grid()
        self.mark(lower, 24, 27, 0, 35)
        self.mark(upper, 24, 27, 25, 60)
        left = self.run_policy(lower, lookahead=14.)
        right = self.run_policy(upper, lookahead=14.)
        self.assert_footprint_clear(left, lower)
        self.assert_footprint_clear(right, upper)
        self.assertGreater(max(p[1] for p in left['path']), 7.5)
        self.assertLess(min(p[1] for p in right['path']), 4.5)

    def test_unknown_robot_and_narrow_passage_fail_closed(self):
        self.assertIsNone(self.run_policy([-1] * (self.size ** 2)))
        costs = self.grid()
        self.mark(costs, 0, 60, 0, 28)
        self.mark(costs, 0, 60, 33, 60)
        self.assertIsNone(self.run_policy(costs))

    def test_inflation_costs_prefer_clear_lane(self):
        costs = self.grid()
        self.mark(costs, 15, 40, 27, 34, 80)
        result = self.run_policy(costs, lookahead=14.)
        self.assertIsNotNone(result)
        self.assertTrue(any(p[1] < 5.4 or p[1] > 6.8 for p in result['path']))

    def test_invalid_inputs_fail_closed(self):
        self.assertIsNone(self.run_policy(self.grid(), start=(float('nan'), 1.)))
        self.assertIsNone(self.run_policy(self.grid()[:-1]))
        self.assertIsNone(self.run_policy(self.grid(), start=(-1., 6.)))

    def assert_forward_path(self, result, heading):
        self.assertIsNotNone(result)
        for a,b in zip(result['path'],result['path'][1:]):
            if math.dist(a,b)<1e-10:
                continue
            delta=math.atan2(b[1]-a[1],b[0]-a[0])-heading
            self.assertLessEqual(abs(math.atan2(math.sin(delta),math.cos(delta))),math.radians(80.)+1e-9)
        delta=result['yaw']-heading
        self.assertLessEqual(abs(math.atan2(math.sin(delta),math.cos(delta))),math.radians(80.)+1e-9)

    def test_forward_only_allows_obstacle_detour_without_backward_snap(self):
        costs=self.grid()
        self.mark(costs,24,27,25,35)
        result=self.run_policy(costs,start=(2.19,6.19),lookahead=14.,forward_only=True)
        self.assert_footprint_clear(result,costs)
        self.assert_forward_path(result,0.)
        self.assertGreater(result['local_goal'][0],8.)
        self.assertTrue(any(abs(p[1]-6.19)>1.5 for p in result['path']))

    def test_forward_only_rejects_destination_behind(self):
        self.assertIsNone(self.run_policy(self.grid(),destination=(1.1,6.1),forward_only=True))
        self.assertIsNotNone(self.run_policy(self.grid(),destination=(1.1,6.1)))

    def test_forward_only_trapped_reverse_escape_fails_closed(self):
        costs=self.grid()
        self.mark(costs,25,28,20,41)
        self.mark(costs,10,28,20,23)
        self.mark(costs,10,28,38,41)
        options=dict(start=(4.1,6.1),destination=(9.1,6.1),max_path_length=25.,lookahead=25.)
        escape=self.run_policy(costs,**options)
        self.assert_footprint_clear(escape,costs)
        self.assertTrue(any(b[0]<a[0] for a,b in zip(escape['path'],escape['path'][1:])))
        self.assertIsNone(self.run_policy(costs,forward_only=True,**options))

    def test_forward_only_gradual_bend_uses_updated_heading(self):
        costs=self.grid()
        for pose,heading,target in (((2.1,2.1),0.,(8.1,6.1)),
                                    ((5.1,4.1),math.pi/4,(7.1,9.1)),
                                    ((6.1,7.1),math.pi/2,(6.1,10.1))):
            with self.subTest(heading=heading):
                result=select_local_goal((0,0),self.resolution,self.size,self.size,
                                         costs,pose,heading,target,forward_only=True)
                self.assert_forward_path(result,heading)
                self.assertGreater(result['diagnostics']['endpoint_progress'],.25)

    def test_no_route_or_map_file_dependency(self):
        import sensor_route_policy
        tree = ast.parse(Path(sensor_route_policy.__file__).read_text())
        imports = [n.names[0].name for n in ast.walk(tree) if isinstance(n, ast.Import)]
        self.assertEqual(set(imports), {'heapq', 'math'})
        calls = [n.func.id for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
        self.assertNotIn('open', calls)
        self.assertIsNotNone(self.run_policy(self.grid()))


if __name__ == '__main__':
    unittest.main()
