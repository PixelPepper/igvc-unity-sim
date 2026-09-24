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

    def assert_forward_path(self, result, heading, minimum_radius=1.25):
        self.assertIsNotNone(result)
        previous_heading, previous_length = heading, 0.
        for a, b in zip(result['path'], result['path'][1:]):
            length = math.dist(a, b)
            self.assertGreater(length, 0.)
            current = math.atan2(b[1]-a[1], b[0]-a[0])
            delta = abs(math.atan2(math.sin(current-previous_heading),
                                   math.cos(current-previous_heading)))
            # Continuous forward arcs, no reversing edge or heading pivot.
            self.assertLessEqual(delta, (length + previous_length) / 2 / minimum_radius + .001)
            previous_heading, previous_length = current, length

    def test_forward_only_allows_obstacle_detour_without_backward_snap(self):
        costs=self.grid()
        self.mark(costs,24,27,25,35)
        result=self.run_policy(costs,start=(2.19,6.19),lookahead=14.,forward_only=True)
        self.assert_footprint_clear(result,costs)
        self.assert_forward_path(result,0.)
        self.assertGreater(result['local_goal'][0],8.)
        self.assertTrue(any(abs(p[1]-6.19)>1.5 for p in result['path']))

    def test_forward_detour_can_initially_move_away(self):
        start, target = (6.1, 3.1), (3.1, 7.1)
        result = self.run_policy(self.grid(), start=start, destination=target,
                                 forward_only=True, lookahead=14.)
        self.assert_forward_path(result, 0.)
        self.assertGreater(math.dist(result['path'][1], target), math.dist(start, target))
        self.assertLess(math.dist(result['local_goal'], target), .3)

    def test_forward_continuous_pose_uses_actual_clearance(self):
        # A pose 0.57 m from a wall clears a 0.5 m circle and its sampled
        # sweep, although conservative cell-centre padding rejects the cell.
        for hazard in (-1, 100):
            costs = self.grid()
            self.mark(costs, 30, 60, 0, 60, hazard)
            result = select_local_goal((0, 0), .2, 60, 60, costs,
                (5.43, 2.1), math.pi/2, (5.43, 9.1), robot_radius=.5,
                forward_only=True, lookahead=10.)
            self.assert_forward_path(result, math.pi/2)
            self.assertGreater(result['local_goal'][1], 8.)
            for x, y in result['path']:
                self.assertGreaterEqual(6.-x, .5)
            # A footprint actually intersecting that same wall stays blocked.
            self.assertIsNone(select_local_goal((0, 0), .2, 60, 60, costs,
                (5.51, 2.1), math.pi/2, (5.51, 9.1), robot_radius=.5,
                forward_only=True))

    def test_forward_exact_fallback_cannot_enter_inscribed_cells(self):
        costs = self.grid()
        self.mark(costs, 30, 31, 0, 60, 99)
        result = self.run_policy(costs, start=(5.1, 6.1),
                                 forward_only=True, lookahead=14.)
        self.assertIsNotNone(result)
        self.assertTrue(all(x < 6. for x, y in result['path']))

    def test_goal_footprint_rejects_rear_corner_collision(self):
        costs = self.grid()
        self.mark(costs, 21, 22, 27, 28, 100)
        options = dict(start=(2.1, 6.1), destination=(10.1, 6.1),
                       robot_radius=.2, forward_only=True, lookahead=3.)
        point_goal = self.run_policy(costs, **options)
        rectangular_goal = self.run_policy(costs,
            goal_footprint=(-1.12, .62, -.52, .52), **options)
        self.assertIsNotNone(rectangular_goal)
        # The hazard [4.2,4.4] x [5.4,5.6] clears the proposal circle but
        # intersects the rear corner of the initially selected rectangle.
        self.assertAlmostEqual(point_goal['local_goal'][1], 6.1)
        self.assertLess(point_goal['local_goal'][0]-1.12, 4.4)
        from sensor_route_policy import _rectangle_clear
        self.assertTrue(_rectangle_clear(*rectangular_goal['local_goal'],
            rectangular_goal['yaw'], (-1.12, .62, -.52, .52), costs, 60, 60, .2, (0, 0)))
        self.assertGreaterEqual(rectangular_goal['diagnostics']['local_path_length'], 1.)

    def test_rectangular_path_avoids_intermediate_rear_corner_collision(self):
        from sensor_route_policy import _rectangle_clear
        costs = self.grid()
        self.mark(costs, 21, 22, 27, 28, 100)
        bounds = (-1.12, .62, -.52, .52)
        options = dict(start=(2.1, 6.1), destination=(10.1, 6.1),
                       robot_radius=.2, forward_only=True, lookahead=7.)
        circle = self.run_policy(costs, **options)
        rectangle = self.run_policy(costs, goal_footprint=bounds, **options)
        self.assertIsNotNone(rectangle)
        # Both terminal poses fit, but the circle-only route clips the rear
        # rectangle against an earlier obstacle. The whole new route must fit.
        self.assertTrue(_rectangle_clear(*circle['local_goal'], circle['yaw'],
            bounds, costs, 60, 60, .2, (0, 0)))
        def collisions(result):
            return [not _rectangle_clear(*b, math.atan2(b[1]-a[1], b[0]-a[0]),
                        bounds, costs, 60, 60, .2, (0, 0))
                    for a, b in zip(result['path'], result['path'][1:])]
        self.assertTrue(any(collisions(circle)))
        self.assertFalse(any(collisions(rectangle)))

    def test_goal_footprint_allows_short_final_approach(self):
        result = self.run_policy(self.grid(), destination=(2.7, 6.1),
            forward_only=True, goal_footprint=(-1.12, .62, -.52, .52))
        self.assertIsNotNone(result)
        self.assertLess(result['diagnostics']['local_path_length'], 1.)

    def test_configured_radius_allows_tight_observed_forward_bend(self):
        size, resolution = 120, .1
        costs = [0 if .4 < math.hypot((i % size+.5)*resolution-6,
                                     (i // size+.5)*resolution-6) < 1.2 else -1
                 for i in range(size*size)]
        options = dict(robot_radius=.15, lookahead=5., max_path_length=8.,
                       min_progress=.1, forward_only=True)
        args = ((0, 0), resolution, size, size, costs, (6., 5.2), 0., (5.8, 6.8))
        self.assertIsNone(select_local_goal(*args, **options))
        result = select_local_goal(*args, minimum_turn_radius=.65, **options)
        self.assert_forward_path(result, 0., minimum_radius=.65)
        self.assertLess(math.dist(result['local_goal'], (5.8, 6.8)), .25)
        self.assertAlmostEqual(result['diagnostics']['minimum_turn_radius'], .65)
        self.assertIsNone(select_local_goal(*args, minimum_turn_radius=0., **options))

    def test_longer_observed_detour_beats_cheap_dead_end(self):
        costs = self.grid()
        self.mark(costs, 0, 40, 35, 38, 100)
        result = select_local_goal((0, 0), .2, 60, 60, costs,
            (3.1, 3.1), math.pi/2, (3.1, 10.1), robot_radius=.3,
            forward_only=True, lookahead=20., max_path_length=12.,
            minimum_turn_radius=.65, max_expansions=50000)
        self.assertIsNotNone(result)
        # Stopping immediately before the horizontal wall is cheap. The
        # longer observed route around its right edge makes greater progress.
        self.assertGreater(max(x for x, y in result['path']), 8.)
        self.assertGreater(result['local_goal'][1], 9.)
        self.assertLess(result['local_goal'][0], 6.)
        self.assertGreater(result['diagnostics']['path_length'], 10.)
        self.assertLessEqual(result['diagnostics']['expanded_cells'], 50000)

    def test_search_time_budget_returns_only_checked_progress(self):
        from unittest.mock import patch
        costs = self.grid()
        self.mark(costs, 24, 27, 0, 60, 100)
        with patch('sensor_route_policy.time.monotonic', side_effect=[0., 0., 6.]):
            result = self.run_policy(costs, destination=(100., 6.1),
                forward_only=True, lookahead=14., max_search_seconds=5.)
        self.assert_footprint_clear(result, costs)
        self.assertLess(result['local_goal'][0], 4.2)
        self.assertEqual(result['diagnostics']['expanded_cells'], 64)
        self.assertTrue(result['diagnostics']['budget_exhausted'])
        self.assertTrue(result['diagnostics']['time_budget_exhausted'])
        # An expired budget before a safe candidate exists cannot invent one.
        with patch('sensor_route_policy.time.monotonic', side_effect=[0., 6.]):
            self.assertIsNone(self.run_policy(costs, forward_only=True,
                                              max_search_seconds=5.))

    def test_minimum_goal_distance_rejects_tolerance_sized_advance(self):
        args = ((0, 0), .1, 120, 120, [0]*14400, (2.1, 6.1), 0., (10.1, 6.1))
        options = dict(forward_only=True, minimum_turn_radius=.65,
                       max_path_length=.3, goal_footprint=(-1.12, .62, -.52, .52))
        short = select_local_goal(*args, **options)
        self.assertIsNotNone(short)
        self.assertLess(math.dist((2.1, 6.1), short['local_goal']), .3)
        self.assertIsNone(select_local_goal(*args, min_goal_distance=.4, **options))

    def test_continuation_reserve_stops_before_checked_dead_end(self):
        costs = self.grid()
        self.mark(costs, 25, 28, 0, 60, 100)
        options = dict(forward_only=True, minimum_turn_radius=.65,
                       lookahead=4., goal_footprint=(-1.12, .62, -.52, .52))
        unrestricted = self.run_policy(costs, **options)
        reserved = self.run_policy(costs, min_goal_distance=.4,
                                   continuation_reserve=1., **options)
        self.assertIsNotNone(reserved)
        self.assertGreaterEqual(reserved['diagnostics']['checked_continuation_length'], 1.)
        self.assertLess(reserved['local_goal'][0], unrestricted['local_goal'][0]-.9)
        self.assertGreaterEqual(math.dist((2.1, 6.1), reserved['local_goal']), .4)

    def test_reserve_exempts_reachable_terminal_goal_but_keeps_minimum(self):
        args = ((0, 0), .1, 120, 120, [0]*14400, (2.1, 6.1), 0., (2.7, 6.1))
        result = select_local_goal(*args, forward_only=True, minimum_turn_radius=.65,
            goal_footprint=(-1.12, .62, -.52, .52), min_goal_distance=.4,
            continuation_reserve=1.)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(math.dist((2.1, 6.1), result['local_goal']), .4)
        self.assertLess(math.dist((2.7, 6.1), result['local_goal']), .15)
        self.assertLess(result['diagnostics']['checked_continuation_length'], 1.)

    def test_swept_rectangle_passes_observed_corridor_without_coarse_padding_block(self):
        from sensor_route_policy import _rectangle_clear
        costs = self.grid()
        self.mark(costs, 0, 60, 0, 27, 100)
        self.mark(costs, 0, 60, 33, 60, 100)
        bounds = (-1.12, .62, -.52, .52)
        # The observed corridor is 1.2 m wide. The padded footprint fits,
        # but half-cell sampling's rotation envelope rejected even its start.
        result = self.run_policy(costs, start=(2.1, 6.), destination=(10.1, 6.),
            robot_radius=.5, forward_only=True, minimum_turn_radius=.65,
            goal_footprint=bounds, lookahead=10., min_goal_distance=.4,
            continuation_reserve=1.)
        self.assertIsNotNone(result)
        self.assertGreater(result['local_goal'][0], 9.5)
        self.assertTrue(result['diagnostics']['full_footprint_sweep'])
        for a, b in zip(result['path'], result['path'][1:]):
            yaw = math.atan2(b[1]-a[1], b[0]-a[0])
            self.assertTrue(_rectangle_clear(*b, yaw, bounds, costs, 60, 60, .2, (0, 0)))

    def test_goal_footprint_rotation_and_unknown_collision(self):
        from sensor_route_policy import _rectangle_clear
        for hazard in (-1, 100):
            costs = self.grid()
            self.mark(costs, 21, 22, 27, 28, hazard)
            bounds = (-1.12, .62, -.52, .52)
            self.assertFalse(_rectangle_clear(5.1, 6.1, 0., bounds, costs,
                                             60, 60, .2, (0, 0)))
            self.assertTrue(_rectangle_clear(5.1, 6.1, math.pi/2, bounds,
                                            costs, 60, 60, .2, (0, 0)))

    def test_forward_observed_corridor_bends_more_than_90_degrees(self):
        costs = [-1] * (self.size ** 2)
        for y in range(self.size):
            for x in range(self.size):
                px, py = (x+.5)*.2, (y+.5)*.2
                if 1.1 < math.hypot(px-5.1, py-6.1) < 4.:
                    costs[y*self.size+x] = 0
        result = self.run_policy(costs, start=(5.1, 3.5), destination=(4.1, 8.5),
                                 forward_only=True, lookahead=14.)
        self.assert_footprint_clear(result, costs)
        self.assert_forward_path(result, 0.)
        self.assertLess(math.dist(result['local_goal'], (4.1, 8.5)), .3)
        self.assertTrue(any(b[0] < a[0] for a, b in zip(result['path'], result['path'][1:])))

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
        self.assertEqual(set(imports), {'heapq', 'math', 'time'})
        calls = [n.func.id for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
        self.assertNotIn('open', calls)
        self.assertIsNotNone(self.run_policy(self.grid()))


if __name__ == '__main__':
    unittest.main()
