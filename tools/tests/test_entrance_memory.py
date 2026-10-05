import copy
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from entrance_memory import ObservedEntranceMemory


def corridor(entry=(10., 0.), direction=(1., 0.)):
    return dict(entry=list(entry), direction=list(direction), confidence=.44,
        diagnostics=dict(segments=[[[8., -3.], [12., -3.]], [[8., 3.], [12., 3.]]]))


class ObservedEntranceMemoryTests(unittest.TestCase):
    def test_lateral_shift_and_lookahead_never_translate_observed_target(self):
        memory = ObservedEntranceMemory()
        memory.observe(corridor(), [0., 0.], 0.)
        memory.observe(None, [2., 3.], 1.)
        proposal = memory.propose([2., 3.], .9, 1., lookahead=100.)
        self.assertEqual(proposal['entry'], [10., 0.])
        self.assertEqual(proposal['diagnostics']['state'], 'in_gap')
        self.assertTrue(proposal['observed_entrance'])
        self.assertFalse(proposal['heading_only'])
        self.assertFalse(proposal['collision_checked'])
        self.assertFalse(proposal['diagnostics']['observed_lane_bounds'])
        self.assertNotIn('free_cells', proposal)

    def test_recorded_corner_fixed_entry_does_not_drift_to_northern_target(self):
        memory = ObservedEntranceMemory()
        observed = corridor((25.216250, 44.070486), (-.8065045364, .5912279026))
        memory.observe(observed, [27.183726, 40.820118], 0.)
        proposal = memory.propose([26.115, 41.185], 2.771, 1.)
        self.assertEqual(proposal['entry'], observed['entry'])
        self.assertAlmostEqual(proposal['yaw'], 2.50901216, places=7)

    def test_d81_entrance_is_consumed_before_d87_and_explicit_clear_resets_it(self):
        observed = dict(entry=[25.21625007, 44.0704863],
            direction=[-.806504536, .591227903], confidence=.44027,
            diagnostics=dict(segments=[[[25.77572, 47.43193], [30.27296, 44.18947]],
                                       [[25.83172, 39.80306], [23.41067, 41.60747]]]))
        memory = ObservedEntranceMemory()
        self.assertTrue(memory.observe(observed, [27.18, 40.82], 0.))
        memory.observe(None, [26., 42.], 1.)
        self.assertEqual(memory.propose([26., 42.], 2.5, 1.)['entry'], observed['entry'])
        self.assertIsNone(memory.propose([24., 44.], 2.5, 2.))
        self.assertEqual(memory.diagnostics['reason'], 'entrance_passed')
        self.assertIsNone(memory.propose([21., 45.], 2.5, 3.))
        # Retained identical support cannot resurrect a consumed entrance.
        self.assertFalse(memory.observe(observed, [27.18, 40.82], 4.))
        self.assertIsNone(memory.propose([26., 42.], 2.5, 5.))
        memory.clear()  # Caller deliberately resets support on destination change.
        self.assertTrue(memory.observe(observed, [27.18, 40.82], 6.))
        self.assertEqual(memory.propose([26., 42.], 2.5, 7.)['entry'], observed['entry'])

    def test_reached_target_is_consumed_without_tangent_extension(self):
        memory = ObservedEntranceMemory()
        memory.observe(corridor(), [0., 0.], 0.)
        self.assertIsNone(memory.propose([9.4, 0.], 0., 1.))
        self.assertEqual(memory.diagnostics['reason'], 'entrance_reached')
        self.assertEqual(memory.diagnostics['state'], 'reacquiring')
        self.assertIsNone(memory.propose([10.5, 0.], 0., 2.))

    def test_crossing_target_plane_far_laterally_never_drives_back(self):
        memory = ObservedEntranceMemory()
        memory.observe(corridor(), [0., 0.], 0.)
        self.assertIsNone(memory.propose([10.1, 3.], 0., 1.))
        self.assertEqual(memory.diagnostics['reason'], 'entrance_passed')

    def test_rotated_observation_and_motion_produce_rotated_fixed_target(self):
        theta = 1.234
        def rotate(point):
            x, y = point
            return [x*math.cos(theta)-y*math.sin(theta), x*math.sin(theta)+y*math.cos(theta)]
        observation = corridor()
        rotated = copy.deepcopy(observation)
        rotated['entry'] = rotate(observation['entry'])
        rotated['direction'] = rotate(observation['direction'])
        rotated['diagnostics']['segments'] = [[rotate(p) for p in s] for s in observation['diagnostics']['segments']]
        memory = ObservedEntranceMemory()
        self.assertTrue(memory.observe(rotated, rotate([0., 0.]), 0.))
        proposal = memory.propose(rotate([2., 3.]), theta+.9, 1.)
        self.assertEqual(proposal['entry'], rotated['entry'])
        self.assertAlmostEqual(proposal['yaw'], theta)
        self.assertAlmostEqual(proposal['diagnostics']['distance_since_support_m'], math.sqrt(13.))
        self.assertIsNone(memory.propose(rotate([10.1, 3.]), theta, 2.))
        self.assertEqual(memory.diagnostics['reason'], 'entrance_passed')

    def test_cumulative_curved_and_reversing_motion_expires(self):
        memory = ObservedEntranceMemory()
        memory.observe(corridor(), [0., 0.], 0.)
        self.assertIsNotNone(memory.propose([0., 8.], math.pi, 1.))
        self.assertIsNotNone(memory.propose([8., 8.], 0., 2.))
        self.assertIsNone(memory.propose([0., 0.], 0., 3.))
        self.assertEqual(memory.diagnostics['reason'], 'travel_limit')
        self.assertGreater(memory.diagnostics['distance_since_support_m'], 20.)

    def test_exact_limits_remain_valid_then_expire(self):
        memory = ObservedEntranceMemory(max_travel=20.)
        memory.observe(corridor(), [0., 0.], 0.)
        self.assertIsNotNone(memory.propose([0., 20.], 0., 60.))
        self.assertIsNone(memory.propose([0., 20.], 0., 60.01))
        self.assertEqual(memory.diagnostics['reason'], 'age_limit')
        self.assertAlmostEqual(memory.diagnostics['age_s'], 60.01)

    def test_clock_reset_cannot_be_refreshed_by_new_observation(self):
        memory = ObservedEntranceMemory()
        memory.observe(corridor(), [0., 0.], 5.)
        self.assertFalse(memory.observe(corridor(), [0., 0.], 4.))
        self.assertEqual(memory.diagnostics['reason'], 'clock_reset')
        self.assertIsNone(memory.propose([0., 0.], 0., 5.))

    def test_synthetic_or_invalid_observations_cannot_refresh_age(self):
        for change in ({'heading_only': True}, {'observed_entrance': True},
                       {'confidence': math.nan}, {'direction': [0., 0.]},
                       {'diagnostics': {}}, {'entry': [math.inf, 0.]}):
            with self.subTest(change=change):
                memory = ObservedEntranceMemory()
                memory.observe(corridor(), [0., 0.], 0.)
                fake = corridor()
                fake.update(change)
                self.assertFalse(memory.observe(fake, [1., 0.], 59.))
                self.assertEqual(memory.observed_at, 0.)
                self.assertIsNone(memory.propose([1., 0.], 0., 61.))

    def test_own_proposal_rejected_and_does_not_refresh(self):
        memory = ObservedEntranceMemory()
        memory.observe(corridor(), [0., 0.], 0.)
        proposal = memory.propose([1., 0.], 0., 59.)
        self.assertFalse(memory.observe(proposal, [1., 0.], 59.))
        self.assertIsNone(memory.propose([1., 0.], 0., 61.))

    def test_identical_geometry_does_not_refresh_despite_changed_confidence(self):
        memory = ObservedEntranceMemory()
        memory.observe(corridor(), [0., 0.], 0.)
        repeated = corridor()
        repeated['confidence'] = .9
        self.assertFalse(memory.observe(repeated, [1., 0.], 59.))
        self.assertEqual(memory.observed_at, 0.)
        self.assertEqual(memory.diagnostics['reason'], 'repeated_geometry')
        self.assertIsNone(memory.propose([1., 0.], 0., 61.))
        self.assertFalse(memory.observe(repeated, [1., 0.], 62.))
        self.assertIsNone(memory.propose([1., 0.], 0., 63.))
        self.assertTrue(memory.observe(corridor(entry=(11., 0.)), [1., 0.], 64.))
        self.assertEqual(memory.observed_at, 64.)

    def test_new_bilateral_acquisition_renews_active_fixed_geometry(self):
        memory = ObservedEntranceMemory()
        memory.observe(corridor(), [0., 0.], 0., support_stamp_ns=100)
        memory.propose([1., 2.], .5, 58.)
        renewed = corridor()
        renewed['confidence'] = .8
        self.assertTrue(memory.observe(renewed, [1., 2.], 59., support_stamp_ns=200))
        proposal = memory.propose([2., 2.], .5, 61.)
        self.assertEqual(proposal['entry'], [10., 0.])
        self.assertEqual(proposal['confidence'], .8)
        self.assertEqual(proposal['diagnostics']['observed_pose'], [1., 2.])
        self.assertEqual(proposal['diagnostics']['age_s'], 2.)
        self.assertEqual(proposal['diagnostics']['distance_since_support_m'], 1.)
        self.assertEqual(proposal['diagnostics']['support_stamp_ns'], 200)

    def test_cloud_headers_missing_same_older_or_invalid_proof_do_not_renew(self):
        for proof in (None, 100, 99, 0, -1, True, 101., '101'):
            with self.subTest(proof=proof):
                memory = ObservedEntranceMemory()
                memory.observe(corridor(), [0., 0.], 0., support_stamp_ns=100)
                self.assertFalse(memory.observe(corridor(), [1., 0.], 59., support_stamp_ns=proof))
                self.assertEqual(memory.observed_at, 0.)
                self.assertIsNone(memory.propose([1., 0.], 0., 61.))

    def test_new_acquisition_proof_does_not_resurrect_consumed_geometry(self):
        for pose in ([9.4, 0.], [10.1, 3.]):
            with self.subTest(pose=pose):
                memory = ObservedEntranceMemory()
                memory.observe(corridor(), [0., 0.], 0., support_stamp_ns=100)
                self.assertIsNone(memory.propose(pose, 0., 1.))
                self.assertFalse(memory.observe(corridor(), [0., 0.], 2., support_stamp_ns=200))
                self.assertIsNone(memory.propose([0., 0.], 0., 3.))
                memory.clear()
                self.assertTrue(memory.observe(corridor(), [0., 0.], 4., support_stamp_ns=200))

    def test_observation_and_proposal_do_not_share_mutable_geometry(self):
        observation = corridor()
        memory = ObservedEntranceMemory()
        memory.observe(observation, [0., 0.], 0.)
        observation['entry'][0] = -100.
        observation['diagnostics']['segments'][0][0][0] = -100.
        proposal = memory.propose([1., 0.], 0., 1.)
        proposal['entry'][0] = -50.
        proposal['diagnostics']['segments'][0][0][0] = -50.
        again = memory.propose([1., 0.], 0., 1.)
        self.assertEqual(again['entry'], [10., 0.])
        self.assertEqual(again['diagnostics']['segments'][0][0], [8., -3.])
        self.assertEqual(again['diagnostics']['observed_pose'], [0., 0.])

    def test_clear_for_destination_change_and_bad_input_fail_closed(self):
        memory = ObservedEntranceMemory()
        memory.observe(corridor(), [0., 0.], 0.)
        memory.clear()
        self.assertEqual(memory.diagnostics['state'], 'unobserved')
        self.assertIsNone(memory.propose([0., 0.], 0., 1.))
        memory.observe(corridor(), [0., 0.], 0.)
        self.assertIsNone(memory.propose([math.nan, 0.], 0., 1.))
        self.assertEqual(memory.diagnostics['reason'], 'invalid_input')


if __name__ == '__main__':
    unittest.main()
