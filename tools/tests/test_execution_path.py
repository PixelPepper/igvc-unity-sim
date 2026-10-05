import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from execution_path import controller_path


class ExecutionPathTests(unittest.TestCase):
    def test_keeps_checked_curve_and_orientations_without_shortcuts(self):
        angles = [i*.01 for i in range(101)]
        points = [(math.sin(a), 1-math.cos(a)) for a in angles]
        output = controller_path(dict(path=points, path_yaws=angles))
        self.assertEqual(output[0], (*points[0], angles[0]))
        self.assertEqual(output[-1], (*points[-1], angles[-1]))
        self.assertGreater(len(output), 15)
        self.assertLess(len(output), 30)
        original = set(zip(points, angles))
        self.assertTrue(all(((x,y),a) in original for x,y,a in output))
        self.assertTrue(all(math.dist(a[:2], b[:2]) <= .061 for a,b in zip(output,output[1:])))

    def test_rejects_unchecked_gap_and_missing_orientation(self):
        for plan in (dict(path=[(0,0),(1,0)],path_yaws=[0,0]),
                     dict(path=[(0,0),(.01,0)],path_yaws=[0]),
                     dict(path=[(0,0),(.01,0)],path_yaws=[0,float('nan')])):
            with self.assertRaises(ValueError):
                controller_path(plan)

    def test_short_goal_keeps_both_ends(self):
        self.assertEqual(controller_path(dict(path=[(0,0),(.02,0)],path_yaws=[0,0])),
                         [(0,0,0),(.02,0,0)])
