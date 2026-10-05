import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recovery_budget import RecoveryBudget


class RecoveryBudgetTests(unittest.TestCase):
    def test_distinct_obstacles_rearm_after_forward_progress(self):
        budget = RecoveryBudget(total_limit=12)
        budget.consume((0, 0, 0))
        budget.observe((-.6, 0, 0))
        budget.observe((2.9, 0, 0))
        self.assertEqual(budget.local, 1)
        self.assertTrue(budget.observe((3.1, 0, 0)))
        budget.consume((10, 0, 0))
        self.assertEqual((budget.local, budget.total, budget.episodes_cleared), (1, 2, 1))

    def test_reversing_and_repeated_shuffles_do_not_rearm(self):
        budget = RecoveryBudget(total_limit=12)
        budget.consume((0, 0, 0))
        budget.observe((-4, 0, 0))
        self.assertEqual(budget.local, 1)
        budget.observe((0, 0, 0))
        for _ in range(20):
            budget.observe((-.6, 0, 0))
            budget.observe((0, 0, 0))
        budget.consume((0, 0, 0))
        self.assertFalse(budget.available)
        with self.assertRaises(RuntimeError):
            budget.consume((0, 0, 0))

    def test_global_limit_survives_successful_local_escapes(self):
        budget = RecoveryBudget(total_limit=2)
        budget.consume((0, 0, 0))
        budget.observe((4, 0, 0))
        budget.consume((4, 0, 0))
        budget.observe((8, 0, 0))
        self.assertEqual(budget.local, 0)
        self.assertFalse(budget.available)

    def test_turning_forward_and_yaw_wrap_are_valid_progress(self):
        budget = RecoveryBudget(total_limit=12)
        budget.consume((0, 0, math.pi-.01))
        self.assertTrue(budget.observe((-3.1, 0, -math.pi+.01)))

    def test_bad_odometry_cannot_rearm(self):
        budget = RecoveryBudget(total_limit=12)
        budget.consume((0, 0, 0))
        with self.assertRaises(ValueError):
            budget.observe((math.nan, 0, 0))
        self.assertEqual(budget.local, 1)
