"""ROS-sourced unit checks for mission behavior at separate painted-line gaps."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from full_course import Mission


class GapModeChecks(unittest.TestCase):
    def mode(self, arc):
        mission=Mission.__new__(Mission)
        mission.config={'route':{'dense_s_m':[0,10,20,32,42,52],
                                 'dense_modes':['painted','unmarked','painted','unmarked','painted','painted']}}
        mission.points=[{'route_s_m':arc}]
        return mission.course_zone(0)

    def test_gap_interiors_allow_missing_paint(self):
        self.assertTrue(self.mode(15))
        self.assertTrue(self.mode(37))

    def test_ramp_middle_still_requires_paint(self):
        self.assertFalse(self.mode(26))
        self.assertFalse(self.mode(3))
        self.assertFalse(self.mode(49))

    def test_camera_transition_precedes_gap(self):
        self.assertTrue(self.mode(8))
        self.assertTrue(self.mode(30))
        self.assertFalse(self.mode(6))


if __name__=='__main__':unittest.main()
