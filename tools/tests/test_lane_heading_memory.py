import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lane_heading_memory import GapHeadingMemory


class GapHeadingMemoryTests(unittest.TestCase):
    def test_missing_pair_preserves_observed_direction_without_inventing_bounds(self):
        memory = GapHeadingMemory()
        self.assertTrue(memory.observe({'direction': [2., 0.]}, [0., 0.], 0.))
        self.assertFalse(memory.observe(None, [2., 0.], 2.))
        proposal = memory.propose([2., 0.], 0., 2., lookahead=7.)
        self.assertEqual(proposal['entry'], [9., 0.])
        self.assertTrue(proposal['heading_only'])
        self.assertFalse(proposal['diagnostics']['observed_lane_bounds'])
        self.assertFalse(proposal['diagnostics']['collision_checked'])

    def test_cumulative_travel_expires_even_after_returning_near_start(self):
        memory = GapHeadingMemory(max_travel=20.)
        memory.observe({'direction': [1., 0.]}, [0., 0.], 0.)
        memory.propose([8., 0.], 0., 1.)
        memory.propose([8., 8.], 0., 2.)
        self.assertIsNone(memory.propose([0., 0.], 0., 3.))

    def test_target_is_clamped_to_remaining_travel(self):
        memory = GapHeadingMemory(max_travel=20.)
        memory.observe({'direction': [1., 0.]}, [0., 0.], 0.)
        proposal = memory.propose([18., 0.], 0., 10., lookahead=7.)
        self.assertEqual(proposal['entry'], [20., 0.])
        self.assertEqual(proposal['diagnostics']['remaining_travel_m'], 2.)

    def test_age_and_clock_reset_clear_memory(self):
        for now in (60.01, -1.):
            memory = GapHeadingMemory()
            memory.observe({'direction': [1., 0.]}, [0., 0.], 0.)
            self.assertIsNone(memory.propose([1., 0.], 0., now))
            self.assertIsNone(memory.propose([1., 0.], 0., 1.))

    def test_opposite_heading_clears_but_new_pair_replaces(self):
        memory = GapHeadingMemory()
        memory.observe({'direction': [1., 0.]}, [0., 0.], 0.)
        self.assertIsNone(memory.propose([1., 0.], math.pi, 1.))
        memory.observe({'direction': [-1., 0.]}, [1., 0.], 2.)
        self.assertEqual(memory.propose([1., 0.], math.pi, 2.)['entry'], [-6., 0.])
        memory.observe({'direction': [0., 1.]}, [1., 0.], 3.)
        self.assertEqual(memory.propose([1., 0.], math.pi/2, 3.)['entry'], [1., 7.])

    def test_clear_and_invalid_observations_fail_closed(self):
        memory = GapHeadingMemory()
        memory.observe({'direction': [1., 0.]}, [0., 0.], 0.)
        memory.clear()
        self.assertIsNone(memory.propose([1., 0.], 0., 1.))
        self.assertFalse(memory.observe({'direction': [0., 0.]}, [0., 0.], 0.))
        self.assertFalse(memory.observe({'direction': [math.nan, 0.]}, [0., 0.], 0.))

    def test_heading_only_proposal_cannot_refresh_its_own_memory(self):
        memory = GapHeadingMemory()
        memory.observe({'direction': [1., 0.]}, [0., 0.], 0.)
        proposal = memory.propose([1., 0.], 0., 1.)
        self.assertFalse(memory.observe(proposal, [1., 0.], 1.))
        self.assertIsNone(memory.propose([2., 0.], 0., 2.))

    def test_slow_progress_retains_heading_up_to_generous_age(self):
        memory = GapHeadingMemory()
        memory.observe({'direction': [1., 0.]}, [0., 0.], 0.)
        self.assertIsNotNone(memory.propose([10., 0.], 0., 50.))
