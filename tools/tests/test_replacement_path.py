"""Opt-in replacement continuity: send only geometry that re-passed unchanged admission."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from path_entry import prepare_controller_plan  # noqa: E402
from replacement_path import (ActivePathRecord, CANCEL, DISABLED, SEND_NEW, SEND_REVALIDATED,  # noqa: E402
                              replacement_outcome, running_action, snapshot_revalidator)

FOOTPRINT = (-1.12, .62, -.52, .52)
UUID = bytes(range(16))
GOAL_ID = UUID.hex()


class Calls:
    def __init__(self, result=None):
        self.count, self.result = 0, result

    def __call__(self, *args):
        self.count += 1
        return self.result


def grid(costs):
    """A duck-typed OccupancyGrid: free 8 m x 8 m at 0.1 m from the origin."""
    origin = SimpleNamespace(position=SimpleNamespace(x=0., y=0.))
    return SimpleNamespace(info=SimpleNamespace(origin=origin, resolution=.1, width=80, height=80), data=costs)


class ReplacementContinuityTest(unittest.TestCase):
    def setUp(self):
        # An admitted straight checked path, as sent to FollowPath.
        self.plan = {'path': [(2+i*.01, 3.) for i in range(301)], 'path_yaws': [0.]*301,
                     'local_goal': (5., 3.), 'yaw': 0.}
        self.costs = [0]*6400
        self.record = ActivePathRecord(self.plan, GOAL_ID, 2, 41, (5., 3.))

    def revalidator(self, pose, costs=None, snapshot=True):
        calls = []
        checked = snapshot_revalidator(prepare_controller_plan, pose,
                                       grid(self.costs if costs is None else costs) if snapshot else None, FOOTPRINT)

        def revalidate(plan):
            calls.append(plan)
            return checked(plan)
        return revalidate, calls

    def decide(self, *, pose=(2.8, 3., 0.), costs=None, enabled=True, record='default', goal_id=GOAL_ID,
               destination=2, running=True, fresh=True, new_admitted=None, snapshot=True, revalidate=None):
        own, calls = self.revalidator(pose, costs, snapshot)
        freshness = Calls(fresh)
        choice, plan, diagnostics = replacement_outcome(
            new_admitted, enabled=enabled, active=self.record if record == 'default' else record,
            active_goal_id=goal_id, destination=destination, action_running=running,
            revalidate=revalidate or own, still_fresh=freshness)
        return choice, plan, diagnostics, len(calls), freshness.count

    def assert_sends_checked_geometry(self, pose):
        choice, plan, diagnostics, revalidations, fresh_checks = self.decide(pose=pose)
        self.assertEqual((choice, diagnostics['reason']), (SEND_REVALIDATED, 'active_path_revalidated'))
        self.assertEqual((revalidations, fresh_checks), (1, 1))
        # The sent plan is exactly what admission returned: a connector from the pose, then the
        # running path's own suffix, unchanged and index-aligned.
        expected, admission = prepare_controller_plan(self.plan, pose, (0., 0.), .1, 80, 80, self.costs, FOOTPRINT)
        self.assertEqual(plan, expected)
        self.assertEqual(diagnostics['admission'], admission)
        join, connector = diagnostics['join_index'], diagnostics['connector_samples']
        self.assertEqual(plan['path'][connector:], self.plan['path'][join:])
        self.assertEqual(plan['path'][0], pose[:2])
        self.assertEqual(diagnostics['sent_path_points'], len(plan['path']))
        self.assertEqual((diagnostics['active_goal_id'], diagnostics['active_sequence']), (GOAL_ID, 41))
        self.assertEqual((plan['local_goal'], plan['yaw']), ((5., 3.), 0.))
        return diagnostics

    def test_on_path_sends_the_checked_connector_and_suffix(self):
        self.assert_sends_checked_geometry((2.8, 3., 0.))

    def test_offset_and_heading_near_limits_send_a_nontrivial_checked_connector(self):
        diagnostics = self.assert_sends_checked_geometry((2.8, 3.09, -.14))
        self.assertAlmostEqual(diagnostics['admission']['cross_track_m'], .09)
        self.assertAlmostEqual(diagnostics['admission']['heading_error_rad'], .14)
        self.assertGreater(diagnostics['connector_samples'], 1)
        self.assertTrue(any(abs(k) > 1e-6 for k in diagnostics['admission']['connector_curvatures']))

    def test_suffix_that_does_not_match_the_running_path_is_cancelled(self):
        def diverged(plan):
            admitted, admission = prepare_controller_plan(plan, (2.8, 3., 0.), (0., 0.), .1, 80, 80,
                                                          self.costs, FOOTPRINT)
            tail = admitted['path'][-1]
            return {**admitted, 'path': admitted['path'][:-1]+[(tail[0], tail[1]+.05)]}, admission
        choice, plan, diagnostics, _, fresh_checks = self.decide(revalidate=diverged)
        self.assertEqual((choice, plan, diagnostics['reason']), (CANCEL, None, 'revalidated_suffix_mismatch'))
        self.assertEqual(fresh_checks, 0)

    def test_blocked_or_unknown_running_path_is_cancelled(self):
        for value in (100, -1):
            with self.subTest(value=value):
                costs = self.costs.copy()
                costs[30*80+44] = value  # on the remaining suffix ahead of the robot
                choice, plan, diagnostics, revalidations, fresh_checks = self.decide(costs=costs)
                self.assertEqual((choice, plan, diagnostics['reason']), (CANCEL, None, 'active_path_not_admissible'))
                self.assertEqual(diagnostics['admission']['reason'], 'latest_observed_sweep_blocked')
                self.assertEqual((revalidations, fresh_checks), (1, 0))

    def test_pose_departure_or_consumed_path_is_cancelled_with_unchanged_limits(self):
        cases = {'cross-track 0.231 m > 0.10': ((2.8, 3.231, 0.), 'start_pose_departed_checked_path'),
                 'heading 0.676 rad > 0.15': ((2.8, 3., .676), 'start_pose_departed_checked_path'),
                 'just over both limits': ((2.8, 3.101, -.14), 'start_pose_departed_checked_path'),
                 'consumed suffix': ((4.7, 3., 0.), 'checked_path_already_consumed')}
        for name, (pose, reason) in cases.items():
            with self.subTest(name):
                choice, plan, diagnostics, _, fresh_checks = self.decide(pose=pose)
                self.assertEqual((choice, plan), (CANCEL, None))
                self.assertEqual(diagnostics['admission']['reason'], reason)
                self.assertEqual(fresh_checks, 0)

    def test_missing_snapshot_cancels_instead_of_crashing(self):
        choice, plan, diagnostics, revalidations, fresh_checks = self.decide(snapshot=False)
        self.assertEqual((choice, plan, diagnostics['reason']), (CANCEL, None, 'active_path_not_admissible'))
        self.assertEqual(diagnostics['admission']['reason'], 'observed_snapshot_unavailable')
        self.assertEqual((revalidations, fresh_checks), (1, 0))

    def test_identity_destination_and_activity_fail_closed_without_rechecking(self):
        cases = {'no record': (dict(record=None), 'no_active_admitted_path'),
                 'action finished': (dict(running=False), 'active_action_not_running'),
                 'running state unknown': (dict(running=None), 'active_action_not_running'),
                 'other action (e.g. BackUp)': (dict(goal_id='b'*32), 'action_identity_mismatch'),
                 'no running handle': (dict(goal_id=None), 'action_identity_mismatch'),
                 'destination advanced': (dict(destination=3), 'destination_changed')}
        for name, (kwargs, reason) in cases.items():
            with self.subTest(name):
                choice, plan, diagnostics, revalidations, fresh_checks = self.decide(**kwargs)
                self.assertEqual((choice, plan, diagnostics['reason']), (CANCEL, None, reason))
                self.assertEqual((revalidations, fresh_checks, diagnostics['evaluated']), (0, 0, False))

    def test_running_action_from_fake_live_handles(self):
        handle = SimpleNamespace(goal_id=SimpleNamespace(uuid=list(UUID)))  # ROS exposes uint8[16]
        pending, finished = SimpleNamespace(done=lambda: False), SimpleNamespace(done=lambda: True)
        self.assertEqual(running_action(handle, pending), (GOAL_ID, True))
        self.assertEqual(running_action(handle, finished), (GOAL_ID, False))
        self.assertEqual(running_action(handle, None), (GOAL_ID, False))
        self.assertEqual(running_action(None, None), (None, False))
        backup = SimpleNamespace(goal_id=SimpleNamespace(uuid=bytes(16)))
        backup_id, running = running_action(backup, pending)
        choice, _, diagnostics, revalidations, _ = self.decide(goal_id=backup_id, running=running)
        self.assertEqual((choice, diagnostics['reason'], revalidations), (CANCEL, 'action_identity_mismatch', 0))

    def test_stale_observations_after_revalidation_cancel_or_stop(self):
        choice, plan, diagnostics, revalidations, _ = self.decide(fresh=False)
        self.assertEqual((choice, plan, diagnostics['reason']),
                         (CANCEL, None, 'observations_not_fresh_after_revalidation'))
        self.assertEqual(revalidations, 1)
        revalidate, _ = self.revalidator((2.8, 3., 0.))

        def stale():
            raise RuntimeError('Stale observation or simulator stream')
        with self.assertRaises(RuntimeError):  # the mission's freshness guard stops the run, as today
            replacement_outcome(None, enabled=True, active=self.record, active_goal_id=GOAL_ID, destination=2,
                                action_running=True, revalidate=revalidate, still_fresh=stale)

    def test_admitted_replacement_and_disabled_mode_never_run_the_fallback(self):
        replacement = {'path': []}
        choice, plan, diagnostics, revalidations, fresh_checks = self.decide(new_admitted=replacement)
        self.assertEqual((choice, diagnostics['reason'], revalidations, fresh_checks),
                         (SEND_NEW, 'replacement_admitted', 0, 0))
        self.assertIs(plan, replacement)
        choice, plan, diagnostics, revalidations, fresh_checks = self.decide(enabled=False)
        self.assertEqual((choice, plan, diagnostics['reason'], diagnostics['mode']), (CANCEL, None, DISABLED, 'off'))
        self.assertEqual((revalidations, fresh_checks), (0, 0))

    def test_revalidation_uses_the_running_plan_not_the_rejected_replacement(self):
        revalidate, calls = self.revalidator((2.8, 3., 0.))
        replacement_outcome(None, enabled=True, active=self.record, active_goal_id=GOAL_ID, destination=2,
                            action_running=True, revalidate=revalidate, still_fresh=lambda: True)
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0], self.plan)

    def test_mission_wiring_uses_the_rejecting_snapshot_and_sends_the_returned_plan(self):
        source = (Path(__file__).resolve().parents[1]/'sensor_course.py').read_text()
        self.assertIn("getattr(args, 'revalidate_active_path', False) is True", source)
        self.assertIn('snapshot_revalidator(prepare_controller_plan, entry_pose, entry_grid,', source)
        branch = source[source.index('if choice == SEND_REVALIDATED:'):source.index('plan = admitted\n')]
        self.assertIn('admitted = fallback_plan', branch)
        self.assertIn('cancel_action(handle); handle = None', branch)
        self.assertNotIn('latest[', branch)


if __name__ == '__main__':
    unittest.main()
