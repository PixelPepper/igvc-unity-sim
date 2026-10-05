"""Mission completion evidence: ordered finish, moved pose, bounded retention, malformed inputs."""
import json
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mission_completion import MissionCompletionRecorder  # noqa: E402

GOALS = [(10., 0., 2.), (0., 0., .4)]  # intermediate 2.0 m handoff, final 0.4 m return


def drive_to_finish(recorder, trajectory, *, speed=.6, dt=.05):
    """Approach the final goal along -x from x=1.0, as the mission loop would, until inside 0.4 m."""
    t, x = 100., 1.
    while True:
        trajectory.append([t, x, .02, math.pi])
        pose = (x, .02, math.pi)
        recorder.observe_loop(t, pose, int(t*1e9), t-.01, 1, len(trajectory)-1)
        if math.hypot(x, .02) <= .4:
            recorder.arrival(t, pose, int(t*1e9), t-.01, 1, len(trajectory)-1)
            return t, x
        t += dt
        x -= speed*dt


class MissionCompletionTest(unittest.TestCase):
    def test_ordered_finish_with_motion_during_cleanup(self):
        recorder, trajectory = MissionCompletionRecorder(GOALS), []
        recorder.arrival(50., (8.5, 0., 0.), 50_000_000_000, 49.99, 0, 0)  # intermediate handoff
        t, x = drive_to_finish(recorder, trajectory)
        # Cleanup spins the executor: odometry keeps arriving while autonomy is disabled and the action cancels.
        for step, name in enumerate(('cleanup_start', 'disable autonomy', 'cancel action', 'reset unmarked mode',
                                     'mission_health_end'), 1):
            x -= .01
            trajectory.append([t+.02*step, x, .02, math.pi])
            recorder.phase(name, t+.02*step, (x, .02, math.pi), int((t+.02*step)*1e9), t+.02*step-.005, 2,
                           len(trajectory)-1)
        report = recorder.report(trajectory)
        final = report['final_arrival']
        self.assertTrue(final['final'])
        self.assertEqual(final['radius_m'], .4)
        self.assertLessEqual(final['goal_distance_m'], .4)
        self.assertEqual([a['destination_index'] for a in report['arrivals']], [0, 1])
        self.assertEqual([p['name'] for p in report['phases']],
                         ['cleanup_start', 'disable autonomy', 'cancel action', 'reset unmarked mode',
                          'mission_health_end'])
        self.assertEqual(report['endpoint']['trajectory_index'], len(trajectory)-1)
        self.assertAlmostEqual(report['after_final_arrival']['moved_m'], .05, places=9)
        self.assertEqual(report['after_final_arrival']['trajectory_samples'], 5)
        self.assertLess(report['after_final_arrival']['goal_distance_change_m'], 0)  # still approaching
        self.assertAlmostEqual(report['loop_dt_s']['mean'], .05, places=9)
        self.assertAlmostEqual(final['odom_receipt_age_s'], .01, places=9)
        json.dumps(report, allow_nan=False)

    def test_missing_malformed_and_nonfinite_values_are_null_and_named(self):
        recorder = MissionCompletionRecorder(GOALS)
        recorder.observe_loop(float('nan'), None, 1.5, None, 'one', -1)
        recorder.observe_loop(10., (1., float('inf'), 0.), -5, float('nan'), 7, 3)
        recorder.phase('cancel action', 11., (1., 2.), None, None, 1, None, ok=False, error=RuntimeError('x'*500))
        report = recorder.report([[float('nan'), 'bad'], ])
        first, second = report['loop_samples']
        self.assertEqual(set(first['unavailable']), {'monotonic_s', 'pose', 'odom_stamp_ns', 'odom_receipt_age_s',
                                                     'destination_index', 'trajectory_index', 'goal_distance_m'})
        self.assertIsNone(first['loop_dt_s'])
        self.assertIsNone(second['loop_dt_s'])  # previous evaluation had no valid time: no invented interval
        self.assertIsNone(second['goal_distance_m'])  # destination 7 does not exist
        phase = report['phases'][0]
        self.assertFalse(phase['ok'])
        self.assertEqual(len(phase['error']), 200)
        self.assertEqual(set(report['endpoint']['unavailable']), {'odom_stamp_s', 'pose', 'final_goal_distance_m'})
        self.assertIsNone(report['final_arrival'])
        json.dumps(report, allow_nan=False)

    def test_loop_retention_is_bounded_and_dt_uses_actual_evaluations(self):
        recorder = MissionCompletionRecorder(GOALS, loop_samples=8)
        for i in range(200):
            recorder.observe_loop(i*.07, (5., 0., 0.), i*70_000_000, i*.07, 1, i)
        report = recorder.report([[0., 5., 0., 0.]])
        self.assertEqual((report['loop_samples_total'], report['loop_samples_retained']), (200, 8))
        self.assertEqual(report['loop_samples'][0]['trajectory_index'], 192)
        self.assertEqual(report['loop_dt_s']['count'], 8)
        self.assertAlmostEqual(report['loop_dt_s']['max'], .07, places=9)

    def test_stopped_before_final_destination_reports_no_final_arrival(self):
        recorder = MissionCompletionRecorder(GOALS)
        recorder.arrival(50., (8.5, 0., 0.), 1, 49.9, 0, 4)
        recorder.arrival(51., (8.4, 0., 0.), 2, 50.9, 0, 5)  # duplicate destination: first decision kept
        recorder.phase('cleanup_start', 52., (8., 0., 0.), 3, 51.9, 1, 6)
        report = recorder.report([[52., 8., 0., 0.]])
        self.assertEqual(len(report['arrivals']), 1)
        self.assertEqual(report['arrivals'][0]['trajectory_index'], 4)
        self.assertIsNone(report['final_arrival'])
        self.assertIsNone(report['after_final_arrival'])
        self.assertAlmostEqual(report['endpoint']['final_goal_distance_m'], 8.)

    def test_phase_cap_counts_dropped_phases(self):
        recorder = MissionCompletionRecorder(GOALS, phase_limit=4)
        for i in range(6):
            recorder.phase(f'p{i}', float(i), (0., 0., 0.), i, float(i), 1, i)
        report = recorder.report([])
        self.assertEqual(([p['name'] for p in report['phases']], report['phases_dropped']), (['p0', 'p1', 'p2', 'p3'], 2))
        self.assertEqual(set(report['endpoint']['unavailable']),
                         {'trajectory_index', 'odom_stamp_s', 'pose', 'final_goal_distance_m'})

    def test_invalid_construction_is_rejected(self):
        for goals, options in (([(0., 0., float('nan'))], {}), (GOALS, {'loop_samples': 1}),
                               (GOALS, {'phase_limit': 2})):
            with self.subTest(goals=goals, options=options):
                with self.assertRaises(ValueError):
                    MissionCompletionRecorder(goals, **options)


if __name__ == '__main__':
    unittest.main()
