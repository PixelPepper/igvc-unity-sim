from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analyze_navigation_episode import path_distance, analyze


class NavigationAnalysisTests(unittest.TestCase):
    def test_same_route_different_sampling(self):
        result = path_distance([(0, 0), (5, 0)], [(0, 0), (1, 0), (5, 0)])
        self.assertLess(result['symmetric_max_m'], .051)

    def test_detects_same_endpoint_different_approach(self):
        result = path_distance([(0, 0), (5, 0)], [(0, 0), (2.5, 2), (5, 0)])
        self.assertGreater(result['symmetric_max_m'], 1.9)

    def test_path_for_other_goal_is_not_compared(self):
        decision = lambda payload: dict(topic='/mission/decision', payload=payload)
        history = [decision(dict(phase='evaluated', sequence=1, pose=[0,0,0], odom_stamp_ns=100,
                    input_age_wall_s=.1, diagnostics=dict(guidance='broad_gps'),
                    plan=dict(path=[[0,0],[5,0]]))),
                   decision(dict(phase='sent_goal', sequence=1, goal=[5,0], goal_id='one',
                                 monotonic_s=2., odom_stamp_ns=100)),
                   dict(topic='/plan', acquisition_stamp_ns=101, received_monotonic_s=2.1,
                        frame_id='odom', poses=[dict(position=[0,0,0]),dict(position=[3,3,0])])]
        self.assertEqual(analyze(history)['matched_paths'], [])

    def test_cancelled_goal_is_not_associated_with_late_path(self):
        decision = lambda payload: dict(topic='/mission/decision', payload=payload)
        history = [decision(dict(phase='evaluated', sequence=1, pose=[0,0,0], odom_stamp_ns=100,
                    input_age_wall_s=.1, diagnostics=dict(guidance='broad_gps'),
                    plan=dict(path=[[0,0],[5,0]]))),
                   decision(dict(phase='sent_goal', sequence=1, goal=[5,0], goal_id='one',
                                 monotonic_s=2., odom_stamp_ns=100)),
                   decision(dict(phase='action_result', sequence=2, action_sequence=1,
                                 goal_id='one', status=5)),
                   dict(topic='/plan', acquisition_stamp_ns=101, received_monotonic_s=2.1,
                        frame_id='odom', poses=[dict(position=[0,0,0]),dict(position=[5,0,0])])]
        self.assertEqual(analyze(history)['matched_paths'], [])
