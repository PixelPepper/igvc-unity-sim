"""Trap memory and corridor-retrace escape: bounds, sweeps and legacy equivalence."""
import ast
from pathlib import Path
import math
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recovery_budget import RecoveryBudget
from recovery_policy import select_backup_recovery, select_retrace_recovery, select_trap_escape
from trap_memory import (TrapMemory, entry_heading, exclude_trapped_guidance, mask_costs,
                         point_in_regions, recent_path)

SIZE = 160
RES = .1
FOOTPRINT = (-1.12, .62, -.52, .52)
ROBOT = (8., 8.)


def grid():
    return [0]*(SIZE*SIZE)


def block(costs, x1, x2, y1, y2, value=100):
    """Cells with centres in [x1,x2)x[y1,y2) metres."""
    for iy in range(round(y1/RES), round(y2/RES)):
        for ix in range(round(x1/RES), round(x2/RES)):
            costs[iy*SIZE+ix] = value


def straight_history(length=5., lateral=0.):
    """The robot drove along +X into ROBOT; newest point is the current pose."""
    steps = int(length/.05)
    return [(ROBOT[0]-length+i*.05, ROBOT[1]+lateral) for i in range(steps+1)]


def planner_needing(min_backup):
    """Forward planner mock: a useful continuation exists only from x <= 8-min_backup."""
    def forward(origin, resolution, width, height, costs, start, yaw, destination, **settings):
        if start[0] > ROBOT[0]-min_backup+1e-6:
            return None
        return {'local_goal': (start[0]+.5, start[1]+3.), 'path': [start, (start[0]+.5, start[1]+3.)],
                'diagnostics': {'expanded_cells': 10, 'local_path_length': 3.,
                                'checked_continuation_length': 1.5, 'endpoint': (start[0]+1., 13.),
                                'guidance_target': (8.5, 14.)}}
    return Mock(side_effect=forward)


class TrapMemoryTests(unittest.TestCase):
    def test_region_sits_ahead_of_the_bumper_and_reports_bounds(self):
        memory = TrapMemory()
        region = memory.record((1., 2., 0.), 10., 3, entry_yaw=.1)
        self.assertEqual(region['center'], [2.4, 2.])
        self.assertEqual(memory.regions(), [{'center': [2.4, 2.], 'radius': .8}])
        self.assertFalse(point_in_regions((1., 2.), memory.regions()))   # stall pose stays outside
        self.assertTrue(point_in_regions((1.7, 2.), memory.regions()))   # just ahead of the bumper
        self.assertEqual(memory.report()['active'][0]['entry_yaw'], .1)

    def test_expiry_by_age_distance_destination_and_capacity(self):
        memory = TrapMemory(max_age_s=60., release_distance_m=8., max_regions=2)
        memory.record((0., 0., 0.), 0., 1)
        self.assertEqual(memory.observe((1., 0., 0.), 59., 1), [])
        self.assertEqual([r['expired_reason'] for r in memory.observe((1., 0., 0.), 60., 1)], ['expired'])
        memory.record((0., 0., 0.), 100., 1)
        self.assertEqual([r['expired_reason'] for r in memory.observe((9.5, 0., 0.), 101., 1)],
                         ['released_by_distance'])
        memory.record((0., 0., 0.), 200., 1)
        self.assertEqual([r['expired_reason'] for r in memory.observe((0., 0., 0.), 201., 2)],
                         ['destination_changed'])
        for t in range(3):
            memory.record((t, 0., 0.), 300.+t, 1)
        self.assertEqual(len(memory.regions()), 2)
        self.assertEqual(memory.report()['expired'][-1]['expired_reason'], 'capacity')
        self.assertTrue(memory.active)
        with self.assertRaises(ValueError):
            TrapMemory(radius_m=5.)
        with self.assertRaises(ValueError):
            memory.record((math.nan, 0., 0.), 1., 1)

    def test_recent_path_is_bounded_in_age_and_length(self):
        rows = [[t*.1, t*.01, 0., 0.] for t in range(2000)]  # 20 m over 200 s
        path = recent_path(rows, max_age_s=60., max_length_m=6.)
        self.assertLessEqual(sum(math.dist(a, b) for a, b in zip(path, path[1:])), 6.+1e-9)
        self.assertEqual(path[-1], (rows[-1][1], 0.))
        short = recent_path(rows, max_age_s=10., max_length_m=6.)
        self.assertLessEqual(short[-1][0]-short[0][0], 1.+1e-6)  # 10 s at 0.1 m/s
        self.assertAlmostEqual(entry_heading(path), 0.)

    def test_mask_is_a_copy_and_keeps_only_the_current_body_clear(self):
        costs = grid()
        regions = [{'center': [8., 8.], 'radius': 1.}]
        masked, changed = mask_costs(costs, SIZE, SIZE, RES, (0., 0.), regions)
        self.assertEqual(costs, grid())
        self.assertGreater(changed, 250)
        self.assertEqual(masked[80*SIZE+80], 100)
        kept, _ = mask_costs(costs, SIZE, SIZE, RES, (0., 0.), regions, keep_clear=(7.5, 8., 0., FOOTPRINT))
        self.assertEqual(kept[80*SIZE+75], 0)      # under the current body
        self.assertEqual(kept[80*SIZE+88], 100)    # ahead of the bumper

    def test_guidance_inside_trap_or_already_reached_falls_back_to_gps(self):
        regions = [{'center': [2., 0.], 'radius': .8}]
        observed = {'guidance': 'observed_lane_corridor', 'target': [2.2, 0.], 'yaw': 0.}
        selection, info = exclude_trapped_guidance(observed, (20., 0.), regions, stall_xy=(0., 0.))
        self.assertEqual(selection, {'guidance': 'broad_gps', 'target': [20., 0.], 'yaw': None})
        self.assertTrue(info['target_inside_trap'])
        reached = {**observed, 'target': [.5, .1]}
        self.assertTrue(exclude_trapped_guidance(reached, (20., 0.), regions, (0., 0.))[1]['target_consumed'])
        self.assertIsNone(exclude_trapped_guidance(observed, (2., .1), regions, (0., 0.))[0])
        clear = {**observed, 'target': [0., 5.]}
        self.assertIs(exclude_trapped_guidance(clear, (20., 0.), regions, (0., 0.))[0], clear)


class DestinationProtectionTests(unittest.TestCase):
    def test_stall_near_destination_is_not_remembered(self):
        memory = TrapMemory()
        # Region centre 1.4 m ahead lands 0.4 m from the goal: within the 2 m goal radius.
        self.assertIsNone(memory.record((0., 0., 0.), 0., 5, protect_xy=(1.8, 0.), protect_radius_m=2.))
        self.assertFalse(memory.active)

    def test_distant_destination_still_records(self):
        memory = TrapMemory()
        region = memory.record((0., 0., 0.), 0., 5, protect_xy=(20., 0.), protect_radius_m=2.)
        self.assertIsNotNone(region)
        self.assertTrue(memory.active)


class RetraceTests(unittest.TestCase):
    def retrace(self, costs, history, forward, **options):
        return select_retrace_recovery((0., 0.), RES, SIZE, SIZE, costs, ROBOT, 0., (8.5, 14.),
                                       goal_footprint=FOOTPRINT, driven_path=history,
                                       forward_planner=forward, **options)

    def test_long_retrace_succeeds_where_straight_backup_cannot(self):
        costs = grid()
        self.assertIsNone(select_backup_recovery((0., 0.), RES, SIZE, SIZE, costs, ROBOT, 0., (8.5, 14.),
            goal_footprint=FOOTPRINT, forward_planner=planner_needing(2.5)))
        result = self.retrace(costs, straight_history(), planner_needing(2.5))
        self.assertEqual(result['escape_type'], 'retrace_backup')
        self.assertEqual(result['distance_m'], 2.8)
        self.assertAlmostEqual(result['backup_pose'][0], 5.2)
        self.assertLessEqual(result['diagnostics']['max_corridor_deviation_m'], 1e-9)

    def test_never_longer_than_driven_path_or_four_metres(self):
        self.assertIsNone(self.retrace(grid(), straight_history(2.)[-41:], planner_needing(2.5)))
        self.assertIsNone(self.retrace(grid(), straight_history(), planner_needing(2.5),
                                       distances=(4.5,)))

    def test_swept_body_into_lethal_or_unknown_rejects_retrace(self):
        for value in (100, -1):
            with self.subTest(value=value):
                costs = grid()
                # 2.2 m sweep clear (rear edge reaches x=4.68); 2.8 m reaches 4.08.
                block(costs, 4.2, 4.3, 7., 9., value)
                forward = planner_needing(2.5)
                self.assertIsNone(self.retrace(costs, straight_history(), forward))
                self.assertTrue(all(call.args[5][0] > 5.5 for call in forward.call_args_list))

    def test_retrace_must_stay_in_the_driven_corridor(self):
        forward = planner_needing(2.5)
        # The robot reached its pose sideways: odometry 1.5 m to the side.
        history = straight_history(lateral=1.5)+[ROBOT]
        self.assertIsNone(self.retrace(grid(), history, forward))
        forward.assert_not_called()
        self.assertIsNone(self.retrace(grid(), straight_history()[:-20], forward))  # stale history

    def test_continuation_into_trap_disc_is_rejected(self):
        def into_trap(origin, resolution, width, height, costs, start, yaw, destination, **settings):
            return {'local_goal': (9.5, 8.), 'path': [start, (9.5, 8.)],
                    'diagnostics': {'expanded_cells': 5, 'local_path_length': 4.,
                                    'checked_continuation_length': 2., 'endpoint': (12., 8.),
                                    'guidance_target': (14., 8.)}}
        regions = [{'center': [9.4, 8.], 'radius': .8}]
        self.assertIsNotNone(self.retrace(grid(), straight_history(), into_trap))
        self.assertIsNone(self.retrace(grid(), straight_history(), into_trap, trap_regions=regions))

    def test_trap_escape_masks_the_continuation_grid_only(self):
        seen = []

        def forward(origin, resolution, width, height, costs, start, yaw, destination, **settings):
            seen.append((start[0], costs[80*SIZE+95], costs[80*SIZE+int(start[0]/RES)]))
            return planner_needing(2.5)(origin, resolution, width, height, costs, start, yaw,
                                        destination, **settings)
        costs = grid()
        result = select_trap_escape((0., 0.), RES, SIZE, SIZE, costs, ROBOT, 0., (8.5, 14.),
            goal_footprint=FOOTPRINT, driven_path=straight_history(),
            trap_regions=[{'center': [9.4, 8.], 'radius': .8}], forward_planner=forward)
        self.assertEqual(result['escape_type'], 'retrace_backup')
        self.assertEqual(costs, grid())                       # caller grid untouched
        self.assertTrue(all(ahead == 100 and under == 0 for _, ahead, under in seen))


class LegacyEquivalenceTests(unittest.TestCase):
    def test_default_arguments_pass_the_identical_grid_and_result(self):
        costs = grid()
        block(costs, 9.5, 9.8, 0., 6.)
        received = []

        def forward(origin, resolution, width, height, grid_in, *args, **kwargs):
            received.append(grid_in)
            return planner_needing(.9)(origin, resolution, width, height, grid_in, *args, **kwargs)
        legacy = select_backup_recovery((0., 0.), RES, SIZE, SIZE, costs, ROBOT, 0., (8.5, 14.),
                                        goal_footprint=FOOTPRINT, forward_planner=forward)
        self.assertTrue(all(g is costs for g in received))
        self.assertEqual(legacy['distance_m'], .9)
        new = select_trap_escape((0., 0.), RES, SIZE, SIZE, costs, ROBOT, 0., (8.5, 14.),
                                 goal_footprint=FOOTPRINT, driven_path=straight_history(),
                                 trap_regions=[], forward_planner=planner_needing(.9))
        self.assertEqual(new['escape_type'], 'straight_backup')
        self.assertEqual((new['distance_m'], new['backup_pose'], new['forward_plan']),
                         (legacy['distance_m'], legacy['backup_pose'], legacy['forward_plan']))
        self.assertEqual(new['diagnostics']['attempts'], legacy['diagnostics']['attempts'])

    def test_cli_defaults_to_legacy_and_builds_memory_only_for_retrace(self):
        source = (Path(__file__).resolve().parents[1]/'sensor_course.py').read_text()
        tree = ast.parse(source)
        escape = [call for call in ast.walk(tree) if isinstance(call, ast.Call)
                  and getattr(call.func, 'attr', '') == 'add_argument'
                  and call.args and getattr(call.args[0], 'value', '') == '--escape']
        self.assertEqual(len(escape), 1)
        keywords = {k.arg: ast.literal_eval(k.value) for k in escape[0].keywords if k.arg in ('choices', 'default')}
        self.assertEqual(keywords, {'choices': ('legacy', 'retrace'), 'default': 'legacy'})
        self.assertIn("trap_memory = TrapMemory() if args.escape == 'retrace' else None", source)

    def test_each_executed_escape_consumes_one_budget_attempt(self):
        budget = RecoveryBudget(total_limit=4)
        budget.consume((8., 8., 0.))    # straight or retrace: one attempt each
        budget.consume((5.2, 8., 0.))
        self.assertFalse(budget.available)
        self.assertEqual(budget.report()['total_attempts'], 2)


if __name__ == '__main__':
    unittest.main()
