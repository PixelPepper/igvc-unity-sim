"""Measured-motion behavior of bounded post-backup target preservation."""
from pathlib import Path
import math
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recovery_intent import RecoveryIntent


class RecoveryIntentTests(unittest.TestCase):
    def intent(self, *, target=(8.,0.), trap=(1.,0.,0.), backup=(0.,0.,0.)):
        intent = RecoveryIntent()
        intent.install({'guidance':'observed_lane_corridor', 'target':list(target), 'yaw':0.},
                       trap, backup, 10., 2)
        return intent

    def test_target_is_copied_at_install_and_each_proposal(self):
        guidance = {'guidance':'broad_gps', 'target':[8.,0.], 'yaw':None}
        intent = RecoveryIntent()
        intent.install(guidance, (1.,0.,0.), (0.,0.,0.), 10., 2)
        guidance['target'][0] = -100.
        first = intent.propose((.2,0.,0.), 11., 2)
        first['target'][0] = -20.
        first['guidance'] = 'resurrected_mouth'
        self.assertEqual(intent.propose((.3,0.,0.), 12., 2),
                         {'guidance':'broad_gps', 'target':[8.,0.], 'yaw':None})
        self.assertTrue(intent.active)

    def test_positive_motion_must_improve_beyond_original_trap(self):
        intent = self.intent()
        self.assertIsNotNone(intent.propose((1.1,0.,0.), 11., 2))
        self.assertGreaterEqual(intent.diagnostics['positive_forward_m'], 1.)
        self.assertGreaterEqual(intent.diagnostics['net_distance_from_backup_m'], 1.)
        self.assertLess(intent.diagnostics['improvement_beyond_trap_m'], .5)
        self.assertIsNone(intent.propose((1.6,0.,0.), 12., 2))
        self.assertFalse(intent.active)
        self.assertEqual(intent.diagnostics['reason'], 'trap_cleared')

    def test_reverse_toward_target_does_not_earn_forward_progress(self):
        intent = self.intent(target=(-8.,0.), trap=(0.,0.,0.))
        self.assertIsNotNone(intent.propose((-2.,0.,0.), 11., 2))
        self.assertEqual(intent.diagnostics['positive_forward_m'], 0.)
        self.assertGreater(intent.diagnostics['improvement_beyond_trap_m'], .5)
        self.assertTrue(intent.active)

    def test_repeated_shuffles_cannot_clear_on_accumulated_distance_alone(self):
        intent = self.intent(trap=(0.,0.,0.))
        for index, x in enumerate((.8,0.,.8,0.,.8)):
            self.assertIsNotNone(intent.propose((x,0.,0.), 11.+index, 2))
        self.assertGreater(intent.diagnostics['positive_forward_m'], 2.)
        self.assertLess(intent.diagnostics['net_distance_from_backup_m'], 1.)
        self.assertTrue(intent.active)

    def test_heading_wrap_uses_physical_forward_direction(self):
        intent = self.intent(target=(-8.,0.), trap=(0.,0.,math.pi),
                             backup=(0.,0.,math.pi-.01))
        self.assertIsNone(intent.propose((-1.1,0.,-math.pi+.01), 11., 2))
        self.assertEqual(intent.diagnostics['reason'], 'trap_cleared')

    def test_target_arrival_is_terminal_even_without_one_metre_progress(self):
        intent = self.intent(target=(.3,0.))
        self.assertIsNone(intent.propose((.06,0.,0.), 11., 2))
        self.assertEqual(intent.diagnostics['reason'], 'target_reached')
        self.assertLess(intent.diagnostics['positive_forward_m'], 1.)

    def test_observed_target_arrival_requires_heading_alignment(self):
        intent = self.intent(target=(.3,0.))
        self.assertIsNotNone(intent.propose((.06,0.,.36),11.,2))
        self.assertTrue(intent.active)
        self.assertIsNone(intent.propose((.06,0.,.34),12.,2))
        self.assertEqual(intent.diagnostics['reason'], 'target_reached')

    def test_arrival_heading_wrap_and_gps_without_heading(self):
        for kind, desired, measured in (('observed_lane_corridor',math.pi-.01,-math.pi+.01),
                                        ('broad_gps',None,math.pi)):
            with self.subTest(kind=kind):
                intent = RecoveryIntent()
                intent.install({'guidance':kind,'target':[.3,0.],'yaw':desired},
                    (1.,0.,0.),(0.,0.,0.),10.,2)
                self.assertIsNone(intent.propose((.06,0.,measured),11.,2))
                self.assertEqual(intent.diagnostics['reason'], 'target_reached')

    def test_measured_escape_progress_can_complete_before_target_yaw_alignment(self):
        intent = RecoveryIntent()
        intent.install({'guidance':'observed_lane_corridor','target':[8.,0.],'yaw':math.pi},
            (1.,0.,0.),(0.,0.,0.),10.,2)
        self.assertIsNone(intent.propose((1.6,0.,0.),11.,2))
        self.assertEqual(intent.diagnostics['reason'], 'trap_cleared')

    def test_unknown_guidance_kind_is_rejected_by_shared_contract(self):
        intent = RecoveryIntent()
        with self.assertRaises(ValueError):
            intent.install({'guidance':'world_route','target':[8.,0.],'yaw':None},
                (1.,0.,0.),(0.,0.,0.),10.,2)
        self.assertFalse(intent.active)

    def test_expiry_is_absolute_and_keeps_explicit_reason(self):
        intent = self.intent()
        self.assertIsNotNone(intent.propose((0.,0.,0.), 39.99, 2))
        self.assertIsNone(intent.propose((0.,0.,0.), 40., 2))
        self.assertEqual(intent.diagnostics['reason'], 'expired')
        self.assertEqual(intent.diagnostics['age_s'], 30.)
        self.assertIsNone(intent.propose((2.,0.,0.), 41., 2))
        self.assertEqual(intent.diagnostics['reason'], 'expired')

    def test_destination_change_and_explicit_clear_discard_target(self):
        intent = self.intent()
        self.assertIsNone(intent.propose((0.,0.,0.), 11., 3))
        self.assertEqual(intent.diagnostics['reason'], 'destination_changed')
        intent = self.intent()
        intent.clear('cancelled')
        self.assertFalse(intent.active)
        self.assertEqual(intent.diagnostics['reason'], 'cancelled')

    def test_invalid_install_or_pose_and_clock_reset_fail_closed(self):
        for guidance in ({'guidance':'broad_gps','target':[math.nan,0.]},
                         {'guidance':'observed_lane_corridor','target':[1.,0.], 'yaw':math.inf}):
            intent = self.intent()
            with self.assertRaises(ValueError):
                intent.install(guidance,(0.,0.,0.),(0.,0.,0.),10.,2)
            self.assertFalse(intent.active)
        for pose, now, reason in (((math.inf,0.,0.),11.,'invalid_input'),
                                  ((0.,0.,0.),math.nan,'invalid_input'),
                                  ((0.,0.,0.),9.,'clock_reset')):
            intent = self.intent()
            self.assertIsNone(intent.propose(pose,now,2))
            self.assertEqual(intent.diagnostics['reason'], reason)

    def test_new_install_resets_previous_progress_and_clock(self):
        intent = self.intent()
        intent.propose((1.1,0.,0.),11.,2)
        intent.install({'guidance':'broad_gps','target':[8.,0.],'yaw':None},
                       (1.,0.,0.),(0.,0.,0.),20.,2)
        self.assertIsNotNone(intent.propose((.2,0.,0.),21.,2))
        self.assertAlmostEqual(intent.diagnostics['positive_forward_m'], .2)
        self.assertEqual(intent.diagnostics['age_s'], 1.)


if __name__ == '__main__':
    unittest.main()
