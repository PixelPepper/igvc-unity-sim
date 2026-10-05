"""Behavioral tests for observed, fully swept straight backup proposals."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from functools import partial
import math
import multiprocessing
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recovery_policy import select_backup_recovery
from observed_navigation import plan_observed_navigation
from sensor_route_policy import _rectangle_clear


class RecoveryPolicyTests(unittest.TestCase):
    size = 160
    footprint = (-1.12, .62, -.52, .52)

    def grid(self):
        return [0]*(self.size*self.size)

    def wall(self, costs, x1, x2, y1=0, y2=160, value=100):
        for y in range(y1, y2):
            costs[y*self.size+x1:y*self.size+x2] = [value]*(x2-x1)

    def plan(self, costs, **options):
        return select_backup_recovery((0,0), .1, self.size, self.size, costs,
            (5.,3.5), 0., (9.,8.), goal_footprint=self.footprint,
            forward_options={'robot_radius':.5,'minimum_turn_radius':1.25,'lookahead':4.},
            **options)

    def test_adequate_backup_unlocks_corner_when_point_three_does_not(self):
        costs = self.grid()
        self.wall(costs,60,63,0,60)
        self.assertIsNone(self.plan(costs, distances=(.3,)))
        result = self.plan(costs)
        self.assertIsNotNone(result)
        self.assertEqual(result['distance_m'], .9)
        self.assertEqual([a['distance_m'] for a in result['diagnostics']['attempts']], [.6,.9])
        forward = result['forward_plan']
        self.assertGreaterEqual(forward['diagnostics']['local_path_length'],1.)
        self.assertGreaterEqual(forward['diagnostics']['checked_continuation_length'],1.)
        self.assertGreater(result['diagnostics']['original_trap_progress_m'],1.)
        for i in range(91):
            self.assertTrue(_rectangle_clear(5.-i*.01,3.5,0.,self.footprint,
                                             costs,self.size,self.size,.1,(0,0)))

    def test_blocked_and_unknown_rear_stop_before_any_forward_search(self):
        for hazard in (-1,100):
            with self.subTest(hazard=hazard):
                costs=self.grid()
                self.wall(costs,37,38,value=hazard)
                forward=Mock(return_value=None)
                self.assertIsNone(self.plan(costs,forward_planner=forward))
                forward.assert_not_called()

    def test_parallel_close_hazard_preserves_configured_side_clearance(self):
        costs = self.grid()
        # The painted row starts at Y=4.10; the padded body ends at Y=4.09.
        # Old isotropic 0.025m sweep padding falsely intersected this row.
        self.wall(costs, 20, 57, 41, 42)
        self.assertFalse(_rectangle_clear(5., 3.57, 0.,
            (-1.145, .645, -.545, .545), costs, self.size, self.size, .1, (0,0)))
        for y, expected in ((3.57, True), (3.59, False)):
            with self.subTest(body_y=y):
                forward = Mock(return_value={'local_goal': (7., y), 'diagnostics': {
                    'expanded_cells': 1, 'local_path_length': 3.,
                    'checked_continuation_length': 1., 'endpoint': (8., 8.)}})
                result = select_backup_recovery((0,0), .1, self.size, self.size,
                    costs, (5.,y), 0., (9.,8.), goal_footprint=self.footprint,
                    distances=(.6,), forward_planner=forward)
                self.assertEqual(result is not None, expected)
                if expected:
                    self.assertEqual(result['distance_m'], .6)
                    self.assertEqual(result['diagnostics']['rear_body_sweep'],
                                     'exact_fixed_yaw_rectangle_union')
                else:
                    forward.assert_not_called()

    def test_rotated_sweep_rejects_thin_rear_barrier_between_clear_endpoints(self):
        costs = self.grid()
        self.wall(costs, 20, 41, 25, 26)
        footprint = (-.1,.1,-.1,.1)
        for y in (3.5, 1.7):
            self.assertTrue(_rectangle_clear(3.5,y,math.pi/2,footprint,
                costs,self.size,self.size,.1,(0,0)))
        forward = Mock(return_value=None)
        self.assertIsNone(select_backup_recovery((0,0),.1,self.size,self.size,
            costs,(3.5,3.5),math.pi/2,(9.,8.),goal_footprint=footprint,
            distances=(1.8,),forward_planner=forward))
        forward.assert_not_called()

    def test_observed_navigation_partial_survives_spawn_and_preserves_guidance(self):
        costs = self.grid()
        self.wall(costs, 60, 63, 0, 60)
        guidance = partial(plan_observed_navigation, lane_points=[], heading_hint=None)
        with ProcessPoolExecutor(max_workers=1,
                                 mp_context=multiprocessing.get_context('spawn')) as pool:
            result = pool.submit(select_backup_recovery, (0, 0), .1,
                self.size, self.size, costs, (5., 3.5), 0., (9., 8.),
                goal_footprint=self.footprint, forward_planner=guidance,
                forward_options={'robot_radius': .5, 'minimum_turn_radius': 1.25,
                                 'lookahead': 4.}).result(timeout=10.)
        self.assertIsNotNone(result)
        self.assertEqual(result['distance_m'], .9)
        diagnostics = result['forward_plan']['diagnostics']
        self.assertEqual(diagnostics['guidance'], 'broad_gps')
        self.assertEqual(diagnostics['guidance_target'], [9., 8.])
        self.assertGreaterEqual(diagnostics['checked_continuation_length'], 1.)

    def test_rear_sweep_rejects_barrier_between_clear_candidate_endpoints(self):
        costs=self.grid()
        self.wall(costs,25,26)
        # Small footprint isolates a thin wall between start and candidate;
        # endpoint-only validation would incorrectly allow the longer backup.
        forward=Mock(return_value=None)
        result=select_backup_recovery((0,0),.1,self.size,self.size,costs,
            (3.5,3.5),0.,(9.,8.),goal_footprint=(-.1,.1,-.1,.1),
            distances=(1.8,),forward_planner=forward)
        self.assertIsNone(result)
        forward.assert_not_called()

    def test_forward_route_that_only_returns_to_original_trap_is_rejected(self):
        costs=self.grid()
        def forward(*args,**kwargs):
            return {'local_goal':(5.,3.5),'path':[(4.,3.5),(5.,3.5)],
                'diagnostics':{'expanded_cells':1,'local_path_length':1.2,
                    'checked_continuation_length':2.,'endpoint':(8.,8.)}}
        self.assertIsNone(self.plan(costs,forward_planner=forward))

    def test_nearby_terminal_escape_needs_no_reserve_beyond_reached_target(self):
        # A real checked route from the backed-up pose can finish at a nearby
        # target instead of requiring an artificial extra metre beyond it.
        result = select_backup_recovery((0,0), .1, self.size, self.size,
            self.grid(), (5.,3.5), 0., (6.,3.5), goal_footprint=self.footprint,
            distances=(.6,), forward_options={'robot_radius':.5,
                'minimum_turn_radius':1.25, 'lookahead':7.})
        self.assertIsNotNone(result)
        self.assertTrue(result['diagnostics']['terminal_escape'])
        self.assertEqual(result['forward_plan']['diagnostics']['checked_continuation_length'], 0.)
        self.assertLessEqual(math.dist(result['forward_plan']['path'][-1], (6.,3.5)), .25)
        self.assertGreaterEqual(result['diagnostics']['original_trap_progress_m'], .5)

    def test_nonterminal_dead_end_and_terminal_return_to_trap_are_rejected(self):
        for target, goal in (((8.,3.5),(5.6,3.5)), ((5.2,3.5),(5.2,3.5))):
            with self.subTest(target=target):
                forward = Mock(return_value={'local_goal':goal,
                    'path':[(3.8,3.5),goal], 'diagnostics':{
                        'guidance_target':target, 'endpoint':goal,
                        'expanded_cells':1, 'local_path_length':math.dist((3.8,3.5),goal),
                        'checked_continuation_length':0.}})
                self.assertIsNone(select_backup_recovery((0,0),.1,self.size,self.size,
                    self.grid(),(5.,3.5),0.,(9.,8.),goal_footprint=self.footprint,
                    distances=(1.2,),forward_planner=forward))
                forward.assert_called_once()

    def test_full_route_terminal_diagnostics_do_not_certify_truncated_local_path(self):
        forward = Mock(return_value={'local_goal':(5.6,3.5),
            'path':[(4.4,3.5),(5.6,3.5)], 'diagnostics':{
                'guidance_target':(8.,3.5), 'endpoint':(8.,3.5),
                'expanded_cells':1, 'local_path_length':1.2,
                'checked_continuation_length':0.}})
        self.assertIsNone(self.plan(self.grid(),distances=(.6,),forward_planner=forward))

    def test_no_forward_escape_in_observed_closed_corridor(self):
        costs=self.grid()
        self.wall(costs,60,63)
        self.wall(costs,0,160,0,26)
        self.wall(costs,0,160,44,160)
        self.assertIsNone(select_backup_recovery((0,0),.1,self.size,self.size,costs,
            (5.,3.5),0.,(9.,3.5),goal_footprint=self.footprint,
            forward_options={'robot_radius':.5,'minimum_turn_radius':1.25}))

    def test_total_expansion_allocation_and_expired_time_fail_closed(self):
        calls=[]
        def forward(*args,**kwargs):
            calls.append(kwargs['max_expansions'])
            return None
        self.assertIsNone(self.plan(self.grid(),forward_planner=forward,max_expansions=100))
        self.assertLessEqual(sum(calls),100)
        forward=Mock(return_value=None)
        with patch('recovery_policy.time.monotonic',side_effect=[0.,6.]):
            self.assertIsNone(self.plan(self.grid(),forward_planner=forward,max_search_seconds=5.))
        forward.assert_not_called()

    def test_invalid_distance_or_unknown_start_fail_closed(self):
        self.assertIsNone(self.plan(self.grid(),max_backup_distance=2.1))
        self.assertIsNone(self.plan(self.grid(),distances=(float('nan'),)))
        self.assertIsNone(self.plan([-1]*(self.size*self.size)))


if __name__=='__main__':
    unittest.main()
