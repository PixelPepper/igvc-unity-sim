"""Finite-ramp body containment, independent of ROS and Unity."""
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from course_judge import ramp_body_evidence


class RampContainmentTests(unittest.TestCase):
    ramp = dict(id='finite',x=0.,y=0.,yaw=0.,width=3.,rise_length=3.,deck_length=2.)

    def test_angled_entry_with_rear_on_flat_ground_is_valid(self):
        # At first entry the rear corner is outside the extended side line,
        # behind x=0; the front portion over the ramp is near its center.
        samples = [[0.,-2.,-.6,.52],[.2,-.765,-.558,.52],
                   [.4,.5,0.,0.],[.6,4.,0.,0.],[.8,10.,0.,0.]]
        result = ramp_body_evidence(samples,self.ramp)
        self.assertTrue(result['passed'],result)
        self.assertGreater(result['conservative_side_margin_m'],.5)

    def test_actual_side_overhang_fails_while_axle_is_inside(self):
        # At x=4 the y=1.6 side is over the finite ramp, beyond its y=1.5 edge.
        samples = [[0.,-2.,0.,0.],[.2,4.,1.1,0.],[.4,10.,0.,0.]]
        self.assertFalse(ramp_body_evidence(samples,self.ramp)['passed'])

    def test_unrelated_longitudinal_stripe_crossing_is_not_ramp_entry(self):
        # A different part of the loop crosses x=0..8 twenty metres away,
        # before the later real ramp approach and traversal.
        samples = [[0.,10.,-20.,0.],[.2,-2.,-20.,0.],
                   [.4,-2.,0.,0.],[.6,4.,0.,0.],[.8,10.,0.,0.]]
        result = ramp_body_evidence(samples,self.ramp)
        self.assertTrue(result['passed'],result)
        self.assertGreater(result['entry_trajectory_index'],2.)

    def test_turn_before_trailing_body_departure_is_rejected(self):
        # The axle is beyond x=8, but the corner (7.9,1.65) is still over the
        # ramp and outside its side; checking only the axle would miss it.
        samples = [[0.,-2.,0.,0.],[.2,7.,0.,0.],
                   [.4,8.4,1.05,math.pi/2],[.6,10.5,1.05,math.pi/2]]
        self.assertFalse(ramp_body_evidence(samples,self.ramp)['passed'])

    def test_between_sample_rotation_overhang_is_rejected(self):
        # Both recorded orientations fit (y=.1..1.1). Halfway through the
        # clockwise rotation, the rear corner reaches y=1.7 at x=3.5.
        samples = [[0.,-2.,0.,0.],[.2,4.,.6,0.],
                   [.4,4.,.6,-math.pi],[.6,10.,0.,-math.pi]]
        result = ramp_body_evidence(samples,self.ramp)
        self.assertFalse(result['passed'])
        self.assertGreater(result['trajectory_index'],1.)
        self.assertLess(result['trajectory_index'],2.)

    def test_sampling_gap_or_repeated_stamp_fails_closed(self):
        for stamp in (0.,.51):
            with self.subTest(stamp=stamp):
                result = ramp_body_evidence([[0.,-2.,0.,0.],[stamp,10.,0.,0.]],self.ramp)
                self.assertFalse(result['passed'])
                self.assertIn('Sampling gap',result['reason'])

    def test_entry_without_full_departure_is_incomplete(self):
        result = ramp_body_evidence([[0.,-2.,0.,0.],[.2,8.5,0.,0.]],self.ramp)
        self.assertFalse(result['passed'])
        self.assertEqual(result['reason'],'No complete body entry and departure')


if __name__=='__main__':
    unittest.main()
