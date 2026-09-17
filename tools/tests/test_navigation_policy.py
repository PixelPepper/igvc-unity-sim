import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'ros2/src/igvc_sim_bridge'))
from igvc_sim_bridge.navigation_policy import forward_command_allowed


class NavigationPolicyTests(unittest.TestCase):
    def test_forward_straight_arc_and_stop(self):
        for command in ((0.,0.),(.7,0.),(.7,.35),(.7,-.35),(2.2,1.)):
            self.assertTrue(forward_command_allowed(*command))

    def test_reverse_spin_and_tight_turn_stop(self):
        for command in ((-.1,0.),(-.1,.2),(0.,.2),(0.,-.2),(.05,.5),(float('nan'),0.)):
            self.assertFalse(forward_command_allowed(*command))
