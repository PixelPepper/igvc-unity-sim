"""Offline recovery controls execute only snapshots whose planning pose is proven measured.

All snapshots and trajectories are synthetic; no run directory, course, WORLD or
teacher label is read. Planning functions are mocked so the tests observe exactly
which snapshots reach a planner and with what arguments.
"""
from pathlib import Path
from unittest import mock
import copy
import math
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import replay_recovery
from snapshot_pose_provenance import classify_snapshot_pose

RUN = Path('synthetic-run-not-on-disk')


def snapshot(pose=(1., 2., .3), *, measured=None, enabled=False, applied=False, context=True):
    """A minimal snapshot payload; robot_xy/robot_yaw hold the planning pose."""
    payload = {'schema_version': 1,
               'input': {'origin': [-5., -5.], 'resolution': .5, 'width': 4, 'height': 4,
                         'costs': [0]*16, 'robot_xy': [pose[0], pose[1]], 'robot_yaw': pose[2],
                         'destination': [8., 9.],
                         'planner_options': {'goal_footprint': [.4, .3], 'body_clearance_weight': .2}},
               'metadata': {'source_sha256': 'synthetic'}}
    if context:
        payload['metadata']['latency_compensation'] = {
            'enabled': enabled, 'applied': applied,
            'measured_pose': list(pose if measured is None else measured), 'planning_pose': list(pose)}
    return payload


def latency(payload):
    return payload['metadata']['latency_compensation']


class ClassifierTest(unittest.TestCase):
    def kind(self, payload):
        return classify_snapshot_pose(payload)['kind']

    def test_not_applied_with_identical_poses_is_measured(self):
        self.assertEqual(self.kind(snapshot()), 'measured')
        self.assertEqual(self.kind(snapshot(enabled=True)), 'measured')

    def test_applied_prediction_is_predicted(self):
        payload = snapshot((1.2, 2., .3), measured=(1., 2., .3), enabled=True, applied=True)
        self.assertEqual(self.kind(payload), 'predicted')

    def test_zero_motion_applied_prediction_stays_predicted(self):
        payload = snapshot(enabled=True, applied=True)
        self.assertEqual(latency(payload)['measured_pose'], latency(payload)['planning_pose'])
        self.assertEqual(self.kind(payload), 'predicted')

    def test_missing_metadata_or_key_is_unknown_not_measured(self):
        payload = snapshot()
        del payload['metadata']
        self.assertEqual(classify_snapshot_pose(payload),
                         {'kind': 'unknown_legacy', 'reason': 'metadata_absent'})
        self.assertEqual(classify_snapshot_pose(snapshot(context=False)),
                         {'kind': 'unknown_legacy', 'reason': 'latency_compensation_absent'})

    def test_flags_must_be_strict_booleans(self):
        for flag in ('enabled', 'applied'):
            for value in (0, 1, 'false', None, 0.):
                payload = snapshot()
                latency(payload)[flag] = value
                with self.subTest(flag=flag, value=value):
                    self.assertEqual(self.kind(payload), 'malformed')
            payload = snapshot()
            del latency(payload)[flag]
            with self.subTest(flag=flag, missing=True):
                self.assertEqual(self.kind(payload), 'malformed')

    def test_poses_must_be_finite_three_element_numbers(self):
        bad = ([1., 2.], [1., 2., .3, 0.], [1., math.nan, .3], [math.inf, 2., .3],
               [1., 2., True], ['1', 2., .3], None, {'x': 1.})
        for key in ('measured_pose', 'planning_pose'):
            for value in bad:
                payload = snapshot()
                latency(payload)[key] = value
                with self.subTest(key=key, value=value):
                    self.assertEqual(self.kind(payload), 'malformed')

    def test_recorded_input_pose_must_be_finite_and_match_planning_pose(self):
        payload = snapshot()
        payload['input']['robot_yaw'] = math.nan
        self.assertEqual(self.kind(payload), 'malformed')
        payload = snapshot()
        payload['input']['robot_xy'] = [1., 2.001]
        self.assertEqual(classify_snapshot_pose(payload)['reason'], 'planning_pose_input_mismatch')
        predicted = snapshot((1.2, 2., .3), measured=(1., 2., .3), enabled=True, applied=True)
        predicted['input']['robot_xy'] = [1., 2.]
        self.assertEqual(self.kind(predicted), 'malformed')

    def test_contradictory_flags_and_poses_are_malformed(self):
        disabled = snapshot((1.2, 2., .3), measured=(1., 2., .3), enabled=False, applied=True)
        self.assertEqual(classify_snapshot_pose(disabled)['reason'], 'applied_while_disabled')
        unapplied = snapshot((1.2, 2., .3), measured=(1., 2., .3), enabled=True, applied=False)
        self.assertEqual(classify_snapshot_pose(unapplied)['reason'], 'not_applied_pose_mismatch')

    def test_non_object_containers_are_malformed(self):
        self.assertEqual(self.kind(None), 'malformed')
        payload = snapshot()
        payload['metadata'] = None
        self.assertEqual(self.kind(payload), 'malformed')
        payload = snapshot()
        payload['metadata']['latency_compensation'] = None
        self.assertEqual(self.kind(payload), 'malformed')

    def test_classifier_does_not_mutate_snapshot(self):
        payload = snapshot((1.2, 2., .3), measured=(1., 2., .3), enabled=True, applied=True)
        before = copy.deepcopy(payload)
        classify_snapshot_pose(payload)
        self.assertEqual(payload, before)


class ReplayControlsTest(unittest.TestCase):
    """Calls the real replay_controls with recorded planner calls."""

    def run_controls(self, snapshots, count, trajectory=None, recoveries=()):
        sequences = sorted(snapshots)
        data = {'decisions': [{'phase': 'requested', 'sequence': s, 'capture_file': f'{s:05d}.json.gz',
                               'odom_stamp_ns': int(s*1e9)} for s in sequences]
                + [{'phase': 'recovery_guidance_selected', 'sequence': s} for s in recoveries],
                'trajectory': trajectory if trajectory is not None else
                [[float(t), .1*t, 0., 0.] for t in range(0, max(sequences)+3)]}
        self.loaded, self.backup, self.escape = [], [], []

        def load(run, sequence):
            self.assertEqual(run, RUN)
            self.loaded.append(sequence)
            return snapshots[sequence]

        def backup(*args, **kwargs):
            self.backup.append((args, kwargs))
            return {'distance_m': .6, 'forward_plan': {'local_goal': [3., 4., 0.]}}

        def escape(*args, **kwargs):
            self.escape.append((args, kwargs))
            return {'escape_type': 'straight_backup', 'distance_m': .6,
                    'forward_plan': {'local_goal': [3., 4., 0.]}}

        with mock.patch.object(replay_recovery, 'load_snapshot', side_effect=load), \
                mock.patch.object(replay_recovery, 'select_backup_recovery', side_effect=backup), \
                mock.patch.object(replay_recovery, 'select_trap_escape', side_effect=escape), \
                mock.patch.object(replay_recovery, 'plan_observed_navigation',
                                  side_effect=AssertionError('planner must stay mocked')):
            return replay_recovery.replay_controls(RUN, data, count)

    def test_ineligible_snapshots_are_skipped_rows_and_invoke_no_planner(self):
        legacy = snapshot(context=False)
        nan = snapshot()
        latency(nan)['measured_pose'] = [math.nan, 2., .3]
        snapshots = {1: snapshot(), 2: snapshot((1.2, 2., .3), measured=(1., 2., .3), enabled=True, applied=True),
                     3: legacy, 4: nan, 5: snapshot(enabled=True, applied=True), 6: snapshot((4., 5., 1.))}
        rows = self.run_controls(snapshots, 6)
        self.assertEqual([row['sequence'] for row in rows], [1, 2, 3, 4, 5, 6])
        self.assertEqual([row['pose_provenance'] for row in rows],
                         ['measured', 'predicted', 'unknown_legacy', 'malformed', 'predicted', 'measured'])
        self.assertEqual([row['skipped'] for row in rows], [False, True, True, True, True, False])
        self.assertEqual(rows[3]['skip_reason'], 'measured_pose_invalid')
        for row in rows:
            if row['skipped']:
                self.assertNotIn('legacy', row)
        # Two backup calls (primary and repeat) and one escape per executed control only.
        self.assertEqual(len(self.backup), 4)
        self.assertEqual(len(self.escape), 2)
        self.assertEqual({args[5] for args, _ in self.backup + self.escape}, {(1., 2.), (4., 5.)})
        self.assertEqual(replay_recovery.control_counts(rows),
                         {'selected': 6, 'executed': 2, 'skipped': 4,
                          'skipped_by_provenance': {'predicted': 2, 'unknown_legacy': 1, 'malformed': 1}})

    def test_out_of_float_range_json_integers_are_malformed_skips(self):
        huge = 10**400  # a valid JSON integer that float() cannot represent
        cases = {1: ('measured_pose', 0, 'measured_pose_invalid'),
                 2: ('planning_pose', 1, 'planning_pose_invalid'),
                 3: ('robot_xy', 0, 'input_pose_invalid'),
                 4: ('robot_xy', 1, 'input_pose_invalid'),
                 5: ('robot_yaw', None, 'input_pose_invalid')}
        snapshots = {}
        for sequence, (key, index, _) in cases.items():
            payload = snapshot()
            if key == 'robot_yaw':
                payload['input']['robot_yaw'] = huge
            elif key == 'robot_xy':
                payload['input']['robot_xy'][index] = huge
            else:
                latency(payload)[key][index] = huge
            snapshots[sequence] = payload
        # Ordinary JSON integers remain valid measured poses.
        snapshots[6] = snapshot((1, 2, 0))
        rows = self.run_controls(snapshots, 6)
        self.assertEqual([row['sequence'] for row in rows], [1, 2, 3, 4, 5, 6])
        for row in rows[:5]:
            with self.subTest(sequence=row['sequence']):
                self.assertTrue(row['skipped'])
                self.assertEqual(row['pose_provenance'], 'malformed')
                self.assertEqual(row['skip_reason'], cases[row['sequence']][2])
        self.assertFalse(rows[5]['skipped'])
        self.assertEqual(rows[5]['pose_provenance'], 'measured')
        self.assertEqual(len(self.backup), 2)
        self.assertEqual(len(self.escape), 1)
        self.assertEqual({args[5] for args, _ in self.backup + self.escape}, {(1, 2)})

    def test_measured_snapshot_arguments_and_history_are_unchanged(self):
        measured = snapshot((1., 2., .3))
        before = copy.deepcopy(measured)
        trajectory = [[0., 0., 0., 0.], [1., .5, 0., 0.], [2., 1., 0., 0.], [3., 9., 9., 0.]]
        rows = self.run_controls({2: measured}, 1, trajectory=trajectory)
        self.assertEqual(measured, before)
        self.assertFalse(rows[0]['skipped'])
        args, kwargs = self.backup[0]
        grid = measured['input']
        self.assertEqual(args, ((-5., -5.), .5, 4, 4, grid['costs'], (1., 2.), .3, [8., 9.]))
        self.assertIs(args[4], grid['costs'])
        self.assertEqual(kwargs['goal_footprint'], (.4, .3))
        self.assertEqual(kwargs['forward_options']['body_clearance_weight'], .2)
        # History is measured odometry up to the request stamp; the later row is excluded.
        escape_args, escape_kwargs = self.escape[0]
        self.assertEqual(escape_args, args)
        self.assertEqual(escape_kwargs['driven_path'][-1], (1., 0.))
        self.assertNotIn((9., 9.), escape_kwargs['driven_path'])
        self.assertEqual(escape_kwargs['trap_regions'], [])

    def test_selection_is_fixed_and_skips_are_not_replaced(self):
        predicted = {s: snapshot(enabled=True, applied=True) for s in range(10)}
        predicted.update({s: snapshot() for s in (1, 2, 4, 5, 7, 8)})
        rows = self.run_controls(predicted, 3, recoveries=())
        # step = 10//3 = 3 selects 0, 3, 6 -- all predicted -- and nothing else is searched.
        self.assertEqual(self.loaded, [0, 3, 6])
        self.assertEqual([row['sequence'] for row in rows], [0, 3, 6])
        self.assertTrue(all(row['skipped'] for row in rows))
        self.assertEqual(self.backup, [])
        self.assertEqual(self.escape, [])
        self.assertEqual(replay_recovery.control_counts(rows)['executed'], 0)

    def test_recovery_sequences_remain_excluded_before_selection(self):
        snapshots = {s: snapshot() for s in range(1, 7)}
        rows = self.run_controls(snapshots, 2, recoveries=(1, 2))
        # Four non-recovery requests remain; step 2 selects 3 and 5.
        self.assertEqual(self.loaded, [3, 5])
        self.assertEqual([row['sequence'] for row in rows], [3, 5])
        self.assertFalse(any(row['skipped'] for row in rows))

    def test_no_selection_returns_empty(self):
        self.assertEqual(self.run_controls({1: snapshot()}, 0), [])
        self.assertEqual(self.loaded, [])
        self.assertEqual(replay_recovery.control_counts([]),
                         {'selected': 0, 'executed': 0, 'skipped': 0,
                          'skipped_by_provenance': {'predicted': 0, 'unknown_legacy': 0, 'malformed': 0}})


if __name__ == '__main__':
    unittest.main()
