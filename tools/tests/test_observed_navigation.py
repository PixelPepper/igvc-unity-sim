"""Lane guidance must still obey observed collision geometry."""
import gzip
import json
from pathlib import Path
import math
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from observed_navigation import (plan_observed_navigation, select_observed_guidance,
                                 refine_corridor_guidance, _near_mouth_target)
from sensor_route_policy import _rectangle_clear


class ObservedNavigationTests(unittest.TestCase):
    footprint = (-1.12,.62,-.52,.52)

    def gate_fixture(self, blockage=None):
        paint = [(x/5,y) for x in range(25,91) for y in (4.,10.)]
        costs = [0]*12100
        if blockage is not None:
            # A small obstacle blocks the mouth midpoint but leaves both sides.
            # A full strip also leaves free space outside the observed lanes.
            rows = range(33,37) if blockage == 'barrel' else range(20,50)
            value = -1 if blockage == 'unknown' else 100
            for y in rows:
                for x in range(21,26):
                    costs[y*110+x] = value
        self.assertTrue(_rectangle_clear(2.,7.,0.,self.footprint,
            costs,110,110,.2,(0.,0.)))
        diagnostics = {}
        selection = select_observed_guidance(paint,(2.,7.),0.,(20.,15.),
            guidance_diagnostics=diagnostics)
        return paint,costs,selection,diagnostics['corridor']

    def test_blocked_midpoint_uses_supported_clear_lateral_gate_and_checked_route(self):
        paint,costs,original,corridor = self.gate_fixture('barrel')
        self.assertFalse(_rectangle_clear(*original['target'],original['yaw'],
            self.footprint,costs,110,110,.2,(0.,0.)))
        selected,evidence = refine_corridor_guidance(original,corridor,
            (0.,0.),.2,110,110,costs,self.footprint)
        self.assertIsNotNone(selected)
        self.assertEqual(selected['yaw'],original['yaw'])
        self.assertAlmostEqual(selected['target'][0],evidence['observed_station_span_m'][0])
        self.assertGreater(abs(selected['target'][1]-7.),.5)
        self.assertTrue(4.52 <= selected['target'][1] <= 9.48)
        self.assertAlmostEqual(evidence['station_projection_m'],.6)
        self.assertTrue(_rectangle_clear(*selected['target'],selected['yaw'],
            self.footprint,costs,110,110,.2,(0.,0.)))
        diagnostic = {}
        plan = plan_observed_navigation((0.,0.),.2,110,110,costs,
            (2.,7.),0.,(20.,15.),paint,guidance_diagnostics=diagnostic,
            robot_radius=.5,forward_only=True,minimum_turn_radius=.65,
            goal_footprint=self.footprint,min_goal_distance=.4,
            continuation_reserve=1.,max_search_seconds=.5)
        self.assertIsNotNone(plan)
        self.assertEqual(diagnostic['guidance_target'],selected['target'])
        # Reach alongside the obstacle, rather than merely stopping before it.
        self.assertGreater(plan['path'][-1][0],4.7)
        self.assertGreater(abs(plan['path'][-1][1]-7.),.5)
        self.assertTrue(plan['diagnostics']['full_footprint_sweep'])
        for point,yaw in zip(plan['path'],plan['path_yaws']):
            self.assertTrue(_rectangle_clear(*point,yaw,self.footprint,
                costs,110,110,.2,(0.,0.)))

    def test_full_gate_barrier_or_unknown_cannot_select_outside_lanes(self):
        for blockage in ('wall','unknown'):
            with self.subTest(blockage=blockage):
                _,costs,selection,corridor = self.gate_fixture(blockage)
                refined,evidence = refine_corridor_guidance(selection,corridor,
                    (0.,0.),.2,110,110,costs,self.footprint)
                self.assertIsNone(refined)
                self.assertEqual(evidence['reason'],'observed_gate_blocked')
                self.assertLessEqual(evidence['candidates_checked'],35)

    def test_clear_midpoint_and_non_corridor_intent_are_preserved(self):
        _,costs,selection,corridor = self.gate_fixture()
        refined,evidence = refine_corridor_guidance(selection,corridor,
            (0.,0.),.2,110,110,costs,self.footprint)
        self.assertEqual(refined,selection)
        self.assertEqual(evidence['reason'],'original_target_clear')
        for guidance in ('broad_gps','remembered_lane_entrance'):
            other = dict(guidance=guidance,target=[4.4,7.],yaw=None)
            refined,_ = refine_corridor_guidance(other,None,(0.,0.),.2,
                110,110,[-1]*12100,self.footprint)
            self.assertEqual(refined,other)

    def test_frozen_midpoint_is_not_laterally_retargeted(self):
        paint,costs,selection,_ = self.gate_fixture('barrel')
        diagnostic = {}
        plan_observed_navigation((0.,0.),.2,110,110,costs,(2.,7.),0.,
            (20.,15.),paint,frozen_guidance=selection,
            guidance_diagnostics=diagnostic,robot_radius=.5,forward_only=True,
            minimum_turn_radius=.65,goal_footprint=self.footprint,
            min_goal_distance=.4,max_search_seconds=.1)
        self.assertEqual(diagnostic['guidance_target'],selection['target'])
        self.assertNotIn('corridor_target_refinement',diagnostic)

    def test_unknown_far_target_retains_checked_partial_progress_and_intent(self):
        paint,_,_,_ = self.gate_fixture()
        costs = [0]*12100
        for y in range(110):
            for x in range(60,110):
                costs[y*110+x] = -1
        diagnostic = {}
        plan = plan_observed_navigation((0.,0.),.2,110,110,costs,
            (6.,7.),0.,(20.,15.),paint,lookahead=7.,
            guidance_diagnostics=diagnostic,robot_radius=.5,forward_only=True,
            minimum_turn_radius=.65,goal_footprint=self.footprint,
            min_goal_distance=.4,continuation_reserve=1.,max_search_seconds=.5)
        self.assertIsNotNone(plan)
        self.assertEqual(diagnostic['guidance'],'observed_lane_corridor')
        self.assertAlmostEqual(diagnostic['guidance_target'][0],13.)
        self.assertEqual(diagnostic['corridor_target_refinement']['reason'],
                         'observed_gate_blocked')
        self.assertGreater(plan['local_goal'][0],7.)
        for point,yaw in zip(plan['path'],plan['path_yaws']):
            self.assertTrue(_rectangle_clear(*point,yaw,self.footprint,
                costs,110,110,.2,(0.,0.)))

    def test_oblique_entry_uses_observed_overlap_beyond_radial_mouth_limit(self):
        lanes = [(x/10,y) for x in range(33,97) for y in (1.3,7.3)]
        diagnostic = {}
        plan = plan_observed_navigation((0.,0.),.2,110,110,[0]*12100,
            (2.5,5.8),-.9,(3.1,16.),lanes,lookahead=7.,
            guidance_diagnostics=diagnostic,robot_radius=.5,forward_only=True,
            minimum_turn_radius=.65,goal_footprint=(-1.12,.62,-.52,.52),
            min_goal_distance=.4,continuation_reserve=1.,max_search_seconds=.5)
        self.assertIsNotNone(plan)
        self.assertEqual(diagnostic['entrance_state'],'observed_mouth_handoff')
        mouth = diagnostic['corridor']['diagnostics']['mouth_entry']
        self.assertGreater(math.dist((2.5,5.8),mouth),1.1)
        target = diagnostic['guidance_target']
        self.assertGreater(target[0],6.)
        self.assertLessEqual(target[0],9.6)
        self.assertAlmostEqual(target[1],4.3,places=5)
        self.assertTrue(plan['diagnostics']['full_footprint_sweep'])

    def test_outside_observed_sides_or_before_supported_mouth_does_not_handoff(self):
        lanes = [(x/10,y) for x in range(33,97) for y in (1.3,7.3)]
        for pose in ((3.1,8.1),(1.8,5.8)):
            with self.subTest(pose=pose):
                diagnostic = {}
                select_observed_guidance(lanes,pose,-.9,(3.1,16.),
                    lookahead=7.,guidance_diagnostics=diagnostic)
                self.assertNotEqual(diagnostic.get('entrance_state'),'observed_mouth_handoff')

    def near_mouth_plan(self, barrier=None, paint=True):
        # Reproduces the integrated stop: axle between observed sides, near
        # their beginning, but oblique to the corridor. The mouth is behind the
        # axle and still ahead along body X; a short mouth goal cannot turn in.
        lanes = [(x/10,y) for x in range(33,97) for y in (1.3,7.3)] if paint else []
        costs = [0]*12100
        if barrier is not None:
            # The rotated body's maximum X is about 3.893 m. Place the strip
            # at 4.2 m, proving a clear start before blocking continuation.
            # Unknown is as blocking as lethal; a partial safe path is allowed.
            for y in range(110):
                for x in range(21,110):
                    costs[y*110+x] = barrier
            self.assertTrue(_rectangle_clear(3.1,5.19,-.9,
                (-1.12,.62,-.52,.52),costs,110,110,.2,(0.,0.)))
        diagnostic = {}
        plan = plan_observed_navigation((0.,0.),.2,110,110,costs,
            (3.1,5.19),-.9,(3.1,16.),lanes,lookahead=7.,
            guidance_diagnostics=diagnostic,robot_radius=.5,forward_only=True,
            minimum_turn_radius=.65,goal_footprint=(-1.12,.62,-.52,.52),
            min_goal_distance=.4,continuation_reserve=1.,max_search_seconds=.5)
        return plan, diagnostic, costs

    def test_near_oblique_mouth_hands_off_into_observed_overlap(self):
        plan, diagnostic, _ = self.near_mouth_plan()
        self.assertIsNotNone(plan)
        self.assertEqual(diagnostic['guidance'],'observed_lane_corridor')
        target = diagnostic['guidance_target']
        self.assertGreater(target[0],6.)
        self.assertLessEqual(target[0],9.6)
        self.assertAlmostEqual(target[1],4.3,places=5)
        self.assertGreater(plan['local_goal'][0],4.)
        self.assertEqual(diagnostic['lane_detection']['top_candidate']['entry_mode'],'visible_mouth')
        self.assertTrue(plan['diagnostics']['full_footprint_sweep'])

    def test_near_mouth_handoff_does_not_cross_wall_or_unknown(self):
        for value in (100,-1):
            with self.subTest(value=value):
                plan, diagnostic, costs = self.near_mouth_plan(barrier=value)
                if plan is not None:
                    for (x,y),yaw in zip(plan['path'],plan['path_yaws']):
                        self.assertLess(x,4.2)
                        self.assertTrue(_rectangle_clear(x,y,yaw,
                            (-1.12,.62,-.52,.52),costs,110,110,.2,(0.,0.)))
                self.assertEqual(diagnostic['guidance'],'observed_lane_corridor')
                self.assertGreater(diagnostic['guidance_target'][0],6.)

    def test_missing_boundary_support_cannot_create_corridor_handoff(self):
        _, diagnostic, _ = self.near_mouth_plan(paint=False)
        self.assertNotIn('entrance_state',diagnostic)
        self.assertEqual(diagnostic['guidance'],'broad_gps')
        self.assertIsNone(diagnostic['corridor'])

    def test_backup_does_not_resurrect_consumed_lane_extent(self):
        paint = [(x/10,y) for x in range(50,85) for y in (3.,7.)]
        current = select_observed_guidance(paint,(8.,5.),0.,(16.,5.),
            entrance_tracking=True,lookahead=7.)
        backed = select_observed_guidance(paint,(7.,5.),0.,(16.,5.),
            entrance_tracking=True,lookahead=7.)
        self.assertEqual(current['guidance'],'broad_gps')
        self.assertEqual(backed['guidance'],'observed_lane_corridor')
        plan = plan_observed_navigation((0.,0.),.2,110,110,[0]*12100,
            (7.,5.),0.,(16.,5.),paint,entrance_tracking=True,
            frozen_guidance=current,robot_radius=.5,forward_only=True,
            minimum_turn_radius=.65)
        self.assertEqual(plan['diagnostics']['guidance_target'],[16.,5.])
        self.assertGreater(plan['local_goal'][0],9.)

    def test_preserved_entrance_does_not_fallback_when_new_obstacle_blocks_it(self):
        selection = {'guidance':'observed_lane_corridor','target':[4.4,7.],'yaw':0.}
        costs=[0]*12100
        for y in range(110):
            for x in range(13,16):costs[y*110+x]=100
        diagnostic={}
        plan = plan_observed_navigation((0.,0.),.2,110,110,costs,
            (2.,7.),0.,(2.,15.),[],frozen_guidance=selection,
            guidance_diagnostics=diagnostic,robot_radius=.5,forward_only=True,
            minimum_turn_radius=.65,min_goal_distance=.4,max_search_seconds=.1)
        self.assertIsNone(plan)
        self.assertEqual(diagnostic['guidance_target'],[4.4,7.])
        self.assertEqual(diagnostic['guidance'],'observed_lane_corridor')

    def test_preserved_guidance_cannot_contain_route_geometry(self):
        with self.assertRaises(ValueError):
            plan_observed_navigation((0.,0.),.2,110,110,[0]*12100,
                (2.,7.),0.,(20.,15.),[],frozen_guidance={
                    'guidance':'broad_gps','target':[20.,15.],'yaw':None,'route':[]})

    def test_fixed_observed_entrance_survives_skewed_gps_intent(self):
        hint = {'entry':[12.,5.], 'direction':[1.,0.], 'observed_entrance':True}
        plan = plan_observed_navigation((0.,0.),.2,110,110,[0]*12100,
            (5.,5.),0.,(5.,16.),[],heading_hint=hint,entrance_tracking=True,
            robot_radius=.5,forward_only=True,minimum_turn_radius=.65)
        self.assertIsNotNone(plan)
        self.assertEqual(plan['diagnostics']['guidance'],'remembered_lane_entrance')
        self.assertEqual(plan['diagnostics']['guidance_target'],[12.,5.])

    def test_reached_observed_extent_does_not_keep_issuing_tiny_goal(self):
        paint = [(x/10,y) for x in range(50,85) for y in (3.,7.)]
        plan = plan_observed_navigation((0.,0.),.2,110,110,[0]*12100,
            (8.,5.),0.,(16.,5.),paint,entrance_tracking=True,
            robot_radius=.5,forward_only=True,minimum_turn_radius=.65)
        self.assertIsNotNone(plan)
        self.assertEqual(plan['diagnostics']['guidance'],'broad_gps')
        self.assertGreater(plan['local_goal'][0],9.)

    def test_fixed_entrance_still_cannot_plan_through_observed_wall(self):
        costs = [0]*12100
        for y in range(110):
            for x in range(30,33):
                costs[y*110+x] = 100
        hint = {'entry':[12.,5.], 'direction':[1.,0.], 'observed_entrance':True}
        plan = plan_observed_navigation((0.,0.),.2,110,110,costs,
            (5.,5.),0.,(5.,16.),[],heading_hint=hint,entrance_tracking=True,
            robot_radius=.5,forward_only=True,minimum_turn_radius=.65)
        if plan is not None:
            self.assertTrue(all(x < 6. for x,_ in plan['path']))
            self.assertEqual(plan['diagnostics']['guidance'],'remembered_lane_entrance')

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


class FrontMembershipHandoffTests(unittest.TestCase):
    """T-0008: recorded T-0006 stall (decision 80); observation-only fixture."""

    @classmethod
    def setUpClass(cls):
        with gzip.open(Path(__file__).with_name('fixtures')/'observed_mouth_20261005.json.gz', 'rt') as stream:
            cls.inputs = json.load(stream)['input']
        cls.footprint = tuple(cls.inputs['planner_options']['goal_footprint'])
        point = {}
        select_observed_guidance(cls.inputs['lane_points'], cls.inputs['robot_xy'], cls.inputs['robot_yaw'],
            cls.inputs['destination'], cls.inputs['heading_hint'], lookahead=7., guidance_diagnostics=point)
        cls.point = point
        cls.mouth = point['corridor']  # recorded visible_mouth corridor at the actual pose

    def select(self, footprint):
        diagnostic = {}
        selected = select_observed_guidance(self.inputs['lane_points'], self.inputs['robot_xy'],
            self.inputs['robot_yaw'], self.inputs['destination'], self.inputs['heading_hint'],
            lookahead=7., guidance_diagnostics=diagnostic, goal_footprint=footprint)
        return selected, diagnostic

    def shifted(self, along=0., across=0.):
        d = self.mouth['direction']
        x, y = self.inputs['robot_xy']
        return (x+along*d[0]-across*d[1], y+along*d[1]+across*d[0])

    def test_recorded_stall_front_hands_off_into_shared_span_point_mode_unchanged(self):
        selected, diagnostic = self.select(self.footprint)
        membership = diagnostic['mouth_membership']
        self.assertEqual((membership['result'], membership['membership_basis']), ('handoff', 'front_center'))
        self.assertAlmostEqual(membership['axle_station'], 19.870, places=3)
        self.assertAlmostEqual(membership['front_station'], 20.363, places=3)
        lo, hi = membership['shared_span']
        self.assertLessEqual(lo, membership['target_station'])
        self.assertLessEqual(membership['target_station'], hi)
        self.assertEqual(diagnostic['entrance_state'], 'observed_mouth_handoff')
        self.assertAlmostEqual(selected['target'][0], 28.986133, places=4)
        self.assertAlmostEqual(selected['target'][1], 24.446254, places=4)
        # Without a footprint the old axle test still keeps the visible mouth.
        self.assertEqual(self.point['mouth_membership']['result'], 'longitudinal_gate')
        self.assertEqual(self.point['mouth_membership']['membership_basis'], 'axle')
        self.assertNotIn('entrance_state', self.point)
        self.assertEqual(self.mouth['diagnostics']['entry_mode'], 'visible_mouth')

    def plan(self, costs):
        # Exact recorded options (0.5 s wall budget). Whether a route completes in
        # that budget is machine-dependent, so tests assert only timing-independent
        # properties; the recorded-budget route outcome is replay evidence.
        options = dict(self.inputs['planner_options'])
        diagnostic = {}
        plan = plan_observed_navigation(tuple(self.inputs['origin']), self.inputs['resolution'],
            self.inputs['width'], self.inputs['height'], costs, self.inputs['robot_xy'],
            self.inputs['robot_yaw'], self.inputs['destination'], self.inputs['lane_points'],
            heading_hint=self.inputs['heading_hint'], guidance_diagnostics=diagnostic, **options)
        return plan, diagnostic

    def assert_path_clear(self, plan, costs):
        for (x, y), yaw in zip(plan['path'], plan['path_yaws']):
            self.assertTrue(_rectangle_clear(x, y, yaw, self.footprint, costs, self.inputs['width'],
                self.inputs['height'], self.inputs['resolution'], tuple(self.inputs['origin'])))

    def test_recorded_stall_plans_toward_the_handoff_only_through_checked_poses(self):
        plan, diagnostic = self.plan(self.inputs['costs'])
        self.assertEqual(diagnostic['mouth_membership']['result'], 'handoff')
        self.assertAlmostEqual(diagnostic['guidance_target'][1], 24.446254, places=4)
        if plan is not None:
            self.assertTrue(plan['diagnostics']['full_footprint_sweep'])
            self.assert_path_clear(plan, self.inputs['costs'])

    def test_blocked_or_unknown_corridor_cannot_be_crossed_by_handoff(self):
        ox, oy = self.inputs['origin']
        res, width = self.inputs['resolution'], self.inputs['width']
        for value in (100, -1):
            with self.subTest(value=value):
                costs = list(self.inputs['costs'])
                for j in range(self.inputs['height']):
                    if oy+(j+.5)*res > 22.:
                        costs[j*width:(j+1)*width] = [value]*width
                plan, diagnostic = self.plan(costs)
                self.assertEqual(diagnostic['mouth_membership']['result'], 'handoff')
                if plan is not None:
                    self.assertTrue(all(y < 22. for _, y in plan['path']))
                    self.assert_path_clear(plan, costs)

    def test_gates_other_than_front_membership_still_reject(self):
        base_yaw = self.inputs['robot_yaw']
        axis_yaw = math.atan2(self.mouth['direction'][1], self.mouth['direction'][0])
        cases = {'front_short_of_threshold': (self.shifted(along=-.4), base_yaw, 'longitudinal_gate'),
                 'beyond_shared_span': (self.shifted(along=4.5), base_yaw, 'longitudinal_gate'),
                 'outside_lateral_sides': (self.shifted(across=-2.), base_yaw, 'lateral_gate'),
                 'wrong_heading': (self.inputs['robot_xy'], axis_yaw+1.4, 'heading_gate')}
        for name, (pose, yaw, reason) in cases.items():
            with self.subTest(name):
                membership = {}
                self.assertIsNone(_near_mouth_target(self.mouth, pose, yaw, 7., goal_footprint=self.footprint,
                                                     membership=membership))
                self.assertEqual(membership['result'], reason)
        for bad in ('x', (), (0., 'nan'), (-1., float('nan'), 0., 0.), (-1., -.5, 0., 0.)):
            with self.subTest(footprint=bad):
                membership = {}
                self.assertIsNone(_near_mouth_target(self.mouth, self.inputs['robot_xy'], base_yaw, 7.,
                                                     goal_footprint=bad, membership=membership))
                self.assertEqual(membership['membership_basis'], 'axle')

    def test_already_eligible_axle_keeps_the_same_target_with_or_without_footprint(self):
        pose = self.shifted(along=.4)
        targets = [_near_mouth_target(self.mouth, pose, self.inputs['robot_yaw'], 7., goal_footprint=footprint)
                   for footprint in (None, self.footprint)]
        self.assertIsNotNone(targets[0])
        self.assertEqual(targets[0], targets[1])


class GateStationRetreatTests(unittest.TestCase):
    """Recovery gate: a far station where observation ends may retreat along the same observed corridor,
    but only to stations strictly ahead of the stalled robot's front."""
    footprint = (-1.12, .62, -.52, .52)
    size, res = 110, .2
    # Observed boundaries along +x at y=4 and y=10 from x=1 to x=12; far gate selected at x=10.
    corridor = {'direction': [1., 0.], 'diagnostics': {'segments': [[[1., 4.], [12., 4.]], [[1., 10.], [12., 10.]]]}}
    selection = {'guidance': 'observed_lane_corridor', 'target': [10., 7.], 'yaw': 0.}
    robot = (2., 7.)  # front at x=2.62

    def costs(self, fills=()):
        grid = [0]*(self.size*self.size)
        for (x1, x2), value in fills:  # x range in metres, full height
            for iy in range(self.size):
                for ix in range(int(round(x1/self.res)), int(round(x2/self.res))):
                    grid[iy*self.size+ix] = value
        return grid

    def refine(self, costs, selection=None, corridor=None, step=.5, robot='default'):
        robot = self.robot if robot == 'default' else robot
        options = {} if step is None else {'station_retreat_step': step, 'retreat_ahead_of': robot}
        return refine_corridor_guidance(selection or self.selection, corridor or self.corridor, (0., 0.), self.res,
                                        self.size, self.size, costs, self.footprint, **options)

    def body_clear(self, target, costs):
        return _rectangle_clear(*target, 0., self.footprint, costs, self.size, self.size, self.res, (0., 0.))

    def test_unknown_beyond_observation_retreats_to_the_farthest_clear_known_station(self):
        costs = self.costs([((8., 22.), -1)])  # the grid is unobserved from x=8
        default, default_evidence = self.refine(costs, step=None)
        self.assertIsNone(default)
        self.assertEqual(default_evidence['reason'], 'observed_gate_blocked')
        self.assertNotIn('retreat_stations_checked', default_evidence)  # default behavior unchanged
        selected, evidence = self.refine(costs)
        self.assertEqual((evidence['reason'], evidence['retreat_stop']),
                         ('clear_gate_target_at_nearer_observed_station', 'found'))
        self.assertAlmostEqual(evidence['station_m'], 7.)  # 7.5 + front 0.62 would overlap unknown cells
        self.assertAlmostEqual(evidence['station_retreat_m'], 3.)
        self.assertEqual(evidence['retreat_stations_checked'], 6)
        self.assertAlmostEqual(selected['target'][0], 7.)
        self.assertEqual(selected['yaw'], 0.)
        self.assertTrue(self.body_clear(selected['target'], costs))
        self.assertTrue(4.52 <= selected['target'][1] <= 9.48)  # inside both observed boundaries
        for offset in (4.6, 5.5, 7., 8.5, 9.4):  # sampled: one step farther is not clear (unknown still blocks)
            self.assertFalse(self.body_clear([7.5, offset], costs))

    def test_never_retreats_to_or_behind_the_stalled_robot(self):
        costs = self.costs([((8., 22.), -1)])
        # Robot axle at x=7.5 (front 8.12): the only clear stations (<= 7.0) are behind its front.
        selected, evidence = self.refine(costs, robot=(7.5, 7.))
        self.assertIsNone(selected)
        self.assertEqual((evidence['reason'], evidence['retreat_stop']), ('observed_gate_blocked', 'robot_front'))
        self.assertAlmostEqual(evidence['robot_front_station_m'], 8.12)
        self.assertEqual(evidence['retreat_stations_checked'], 3)  # 9.5, 9.0, 8.5 only
        # The same scene with the robot farther back finds the ahead station 7.0.
        selected, evidence = self.refine(costs, robot=(5., 7.))
        self.assertAlmostEqual(selected['target'][0], 7.)
        self.assertGreater(selected['target'][0], evidence['robot_front_station_m'])

    def test_lethal_barrier_selects_a_station_before_it_never_beyond(self):
        costs = self.costs([((6., 6.2), 100), ((8., 22.), -1)])
        selected, evidence = self.refine(costs)
        self.assertLess(selected['target'][0]+self.footprint[1], 6.)
        self.assertAlmostEqual(evidence['station_m'], 5.)
        self.assertTrue(self.body_clear(selected['target'], costs))

    def test_no_clear_ahead_station_fails_closed(self):
        for name, fills in {'all unknown': [((0., 22.), -1)], 'all lethal': [((0., 22.), 100)]}.items():
            with self.subTest(name):
                selected, evidence = self.refine(self.costs(fills))
                self.assertIsNone(selected)
                self.assertEqual(evidence['reason'], 'observed_gate_blocked')
                self.assertEqual((evidence['retreat_stations_checked'], evidence['retreat_stop']), (14, 'robot_front'))
        # A robot behind the observed support stops at the support start instead (9.5 .. 1.0).
        selected, evidence = self.refine(self.costs([((0., 22.), -1)]), robot=(-1., 7.))
        self.assertEqual((evidence['retreat_stations_checked'], evidence['retreat_stop']), (18, 'observed_support_start'))

    def test_retreat_is_capped_at_64_stations(self):
        selected, evidence = self.refine(self.costs([((0., 22.), -1)]), step=.01, robot=(0., 7.))
        self.assertIsNone(selected)
        self.assertEqual((evidence['retreat_stations_checked'], evidence['retreat_stop']), (64, 'retreat_limit_64'))

    def test_sloped_support_uses_each_checked_station_and_reports_width_honestly(self):
        # Boundaries converge toward x=12: no body width at the far station 10, width nearer.
        sloped = {'direction': [1., 0.], 'diagnostics': {'segments': [[[1., 4.], [12., 6.9]], [[1., 10.], [12., 7.1]]]}}
        _, no_retreat = self.refine(self.costs([((8., 22.), -1)]), corridor=sloped, step=None)
        self.assertEqual(no_retreat['reason'], 'no_body_width_inside_observed_gate')
        selected, evidence = self.refine(self.costs([((8., 22.), -1)]), corridor=sloped)
        self.assertEqual(evidence['reason'], 'clear_gate_target_at_nearer_observed_station')
        lower, upper = evidence['admissible_lateral_span_m']
        self.assertLessEqual(lower, upper)  # the span reported is the selected nearer station's
        self.assertTrue(self.body_clear(selected['target'], self.costs([((8., 22.), -1)])))
        # Nearer stations have width but are blocked: the failure must not claim "no width" everywhere.
        _, blocked = self.refine(self.costs([((3., 22.), 100)]), corridor=sloped)
        self.assertEqual(blocked['reason'], 'observed_gate_blocked')

    def test_clear_far_station_is_kept_with_or_without_retreat(self):
        costs = self.costs()
        for step in (None, .5):
            selected, evidence = self.refine(costs, step=step)
            self.assertEqual(selected, self.selection)
            self.assertEqual(evidence['reason'], 'original_target_clear')
            self.assertNotIn('station_retreat_m', evidence)

    def test_corridor_too_narrow_for_the_body_is_rejected_at_every_station(self):
        narrow = {'direction': [1., 0.], 'diagnostics': {'segments': [[[1., 6.6], [12., 6.6]], [[1., 7.4], [12., 7.4]]]}}
        # The original far target must be blocked: a clear original target is accepted before any width check.
        costs = self.costs([((8., 22.), -1)])
        for step in (None, .5):
            selected, evidence = self.refine(costs, corridor=narrow, step=step)
            self.assertIsNone(selected)
            self.assertEqual(evidence['reason'], 'no_body_width_inside_observed_gate')

    def test_invalid_retreat_options_are_rejected_not_extrapolated(self):
        costs = self.costs([((8., 22.), -1)])
        for step in (-.5, 0, 0., math.nan, math.inf, True, '0.5', [.5]):
            with self.subTest(step=step), self.assertRaises(ValueError):
                self.refine(costs, step=step)
        for robot in (None, (math.nan, 7.), (1.,), (1., 2., 3.), ('2', 7.)):
            with self.subTest(robot=robot), self.assertRaises(ValueError):
                self.refine(costs, robot=robot)
        with self.assertRaises(ValueError):  # a robot position alone does not enable anything
            refine_corridor_guidance(self.selection, self.corridor, (0., 0.), self.res, self.size, self.size,
                                     costs, self.footprint, retreat_ahead_of=self.robot)

    def test_non_corridor_intent_is_never_retargeted(self):
        other = {'guidance': 'broad_gps', 'target': [10., 7.], 'yaw': None}
        selected, evidence = self.refine([-1]*(self.size*self.size), selection=other)
        self.assertEqual(selected, other)
        self.assertEqual(evidence['reason'], 'no_fresh_corridor_or_footprint')


if __name__ == '__main__':
    unittest.main()
