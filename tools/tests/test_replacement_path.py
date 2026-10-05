"""Opt-in replacement continuity: keep a running path only if it re-passes unchanged admission."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from path_entry import prepare_controller_plan  # noqa: E402
from replacement_path import (ActivePathRecord, CANCEL, DISABLED, RETAIN, SEND_NEW,  # noqa: E402
                              replacement_outcome)

FOOTPRINT = (-1.12, .62, -.52, .52)
GOAL_ID = 'a'*32


class Calls:
    def __init__(self, result=None):
        self.count, self.result = 0, result

    def __call__(self, *args):
        self.count += 1
        return self.result


class ReplacementContinuityTest(unittest.TestCase):
    def setUp(self):
        # An admitted straight checked path, as sent to FollowPath, on a free 8 m x 8 m grid.
        self.plan = {'path': [(2+i*.01, 3.) for i in range(301)], 'path_yaws': [0.]*301}
        self.costs = [0]*6400
        self.record = ActivePathRecord(self.plan, GOAL_ID, 2, 41, (5., 3.))

    def revalidator(self, pose, costs=None):
        calls = []

        def revalidate(plan):
            calls.append(plan)
            return prepare_controller_plan(plan, pose, (0, 0), .1, 80, 80,
                                           self.costs if costs is None else costs, FOOTPRINT)
        return revalidate, calls

    def decide(self, *, pose=(2.8, 3., 0.), costs=None, enabled=True, record='default', goal_id=GOAL_ID,
               destination=2, running=True, fresh=True, new_admitted=None):
        revalidate, calls = self.revalidator(pose, costs)
        freshness = Calls(fresh)
        choice, diagnostics = replacement_outcome(
            new_admitted, enabled=enabled, active=self.record if record == 'default' else record,
            active_goal_id=goal_id, destination=destination, action_running=running,
            revalidate=revalidate, still_fresh=freshness)
        return choice, diagnostics, len(calls), freshness.count

    def test_rejected_replacement_keeps_a_still_admissible_running_path(self):
        choice, diagnostics, revalidations, fresh_checks = self.decide()
        self.assertEqual(choice, RETAIN)
        self.assertEqual((revalidations, fresh_checks), (1, 1))
        self.assertEqual(diagnostics['reason'], 'active_path_revalidated')
        self.assertTrue(diagnostics['admission']['accepted'])
        self.assertEqual((diagnostics['active_goal_id'], diagnostics['active_sequence']), (GOAL_ID, 41))

    def test_blocked_or_unknown_running_path_is_cancelled(self):
        for value in (100, -1):
            with self.subTest(value=value):
                costs = self.costs.copy()
                costs[30*80+44] = value  # on the remaining suffix ahead of the robot
                choice, diagnostics, revalidations, fresh_checks = self.decide(costs=costs)
                self.assertEqual((choice, diagnostics['reason']), (CANCEL, 'active_path_not_admissible'))
                self.assertEqual(diagnostics['admission']['reason'], 'latest_observed_sweep_blocked')
                self.assertEqual((revalidations, fresh_checks), (1, 0))

    def test_pose_departure_or_consumed_path_is_cancelled_with_unchanged_limits(self):
        cases = {'cross-track 0.231 m > 0.10': ((2.8, 3.231, 0.), 'start_pose_departed_checked_path'),
                 'heading 0.676 rad > 0.15': ((2.8, 3., .676), 'start_pose_departed_checked_path'),
                 'consumed suffix': ((4.7, 3., 0.), 'checked_path_already_consumed')}
        for name, (pose, reason) in cases.items():
            with self.subTest(name):
                choice, diagnostics, _, fresh_checks = self.decide(pose=pose)
                self.assertEqual(choice, CANCEL)
                self.assertEqual(diagnostics['admission']['reason'], reason)
                self.assertEqual(fresh_checks, 0)

    def test_identity_destination_and_activity_fail_closed_without_rechecking(self):
        cases = {'no record': (dict(record=None), 'no_active_admitted_path'),
                 'action finished': (dict(running=False), 'active_action_not_running'),
                 'running state unknown': (dict(running=None), 'active_action_not_running'),
                 'other action (e.g. BackUp)': (dict(goal_id='b'*32), 'action_identity_mismatch'),
                 'no running handle': (dict(goal_id=None), 'action_identity_mismatch'),
                 'destination advanced': (dict(destination=3), 'destination_changed')}
        for name, (kwargs, reason) in cases.items():
            with self.subTest(name):
                choice, diagnostics, revalidations, fresh_checks = self.decide(**kwargs)
                self.assertEqual((choice, diagnostics['reason']), (CANCEL, reason))
                self.assertEqual((revalidations, fresh_checks, diagnostics['evaluated']), (0, 0, False))

    def test_stale_observations_after_revalidation_cancel_or_stop(self):
        choice, diagnostics, revalidations, _ = self.decide(fresh=False)
        self.assertEqual((choice, diagnostics['reason']), (CANCEL, 'observations_not_fresh_after_revalidation'))
        self.assertEqual(revalidations, 1)
        revalidate, _ = self.revalidator((2.8, 3., 0.))

        def stale():
            raise RuntimeError('Stale observation or simulator stream')
        with self.assertRaises(RuntimeError):  # the mission's freshness guard stops the run, as today
            replacement_outcome(None, enabled=True, active=self.record, active_goal_id=GOAL_ID, destination=2,
                                action_running=True, revalidate=revalidate, still_fresh=stale)

    def test_admitted_replacement_and_disabled_mode_never_run_the_fallback(self):
        choice, diagnostics, revalidations, fresh_checks = self.decide(new_admitted={'path': []})
        self.assertEqual((choice, diagnostics['reason'], revalidations, fresh_checks),
                         (SEND_NEW, 'replacement_admitted', 0, 0))
        choice, diagnostics, revalidations, fresh_checks = self.decide(enabled=False)
        self.assertEqual((choice, diagnostics['reason'], diagnostics['mode']), (CANCEL, DISABLED, 'off'))
        self.assertEqual((revalidations, fresh_checks), (0, 0))

    def test_revalidation_uses_the_running_plan_not_the_rejected_replacement(self):
        revalidate, calls = self.revalidator((2.8, 3., 0.))
        replacement_outcome(None, enabled=True, active=self.record, active_goal_id=GOAL_ID, destination=2,
                            action_running=True, revalidate=revalidate, still_fresh=lambda: True)
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0], self.plan)


if __name__ == '__main__':
    unittest.main()
