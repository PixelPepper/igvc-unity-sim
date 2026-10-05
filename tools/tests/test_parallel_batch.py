"""Offline checks for parallel batch splitting (no simulator)."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from parallel_batch import split


class SplitTests(unittest.TestCase):
    def test_alternating_arms_are_balanced_per_instance(self):
        trials = [dict(arm='baseline', settings=dict(escape=a), i=i) for i, a in enumerate(['A', 'B'] * 5)]
        for n in (2, 3, 4):
            shares = split(trials, n)
            self.assertEqual(sorted(t['i'] for s in shares.values() for t in s), list(range(10)))
            for share in shares.values():
                arms = [t['settings']['escape'] for t in share]
                self.assertLessEqual(abs(arms.count('A') - arms.count('B')), 1, (n, arms))

    def test_single_instance_keeps_order(self):
        trials = [dict(i=i) for i in range(5)]
        self.assertEqual([t['i'] for t in split(trials, 1)[1]], list(range(5)))


if __name__ == '__main__':
    unittest.main()
