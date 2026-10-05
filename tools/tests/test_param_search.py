"""Offline checks for the sandbox parameter-search driver (no simulator)."""
from pathlib import Path
import random
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from param_search import SPACE, decode, encode, parse_seeds, propose, score
from sandbox_profile import DEFAULTS, LIMITS


class ParamSearchTests(unittest.TestCase):
    def test_score_orders_outcomes(self):
        base = dict(state='completed', run='r', completed=6, sim_span_s=360, backups=0, health_fail=0, min_clearance_m=.2, audit_passed=True)
        self.assertGreater(score(base), score(dict(base, completed=4, audit_passed=False)))
        self.assertGreater(score(base), score(dict(base, sim_span_s=420)))
        self.assertGreater(score(base), score(dict(base, health_fail=3)))
        self.assertGreater(score(base), score(dict(base, backups=2)))
        self.assertGreater(score(dict(base, completed=1)), score(dict(base, run=None)))

    def test_decode_stays_inside_allowlist(self):
        rng = random.Random(4)
        for _ in range(500):
            s = decode([rng.uniform(-.5, 1.5) for _ in SPACE])
            for key, (lo, hi) in LIMITS.items():
                self.assertTrue(lo <= s[key] <= hi, key)
            for key, (lo, hi) in SPACE.items():
                self.assertTrue(lo <= s[key] <= hi, key)
            self.assertEqual((s['controller'], s['execution']), (DEFAULTS['controller'], DEFAULTS['execution']))

    def test_encode_decode_round_trip(self):
        s = decode([.25, .5, .75, .1, .9])
        for a, b in zip(encode(s), [.25, .5, .75, .1, .9]):
            self.assertAlmostEqual(a, b, places=2)

    def test_propose_is_seeded_and_valid(self):
        history = [dict(settings=decode([random.Random(i).random() for _ in SPACE]), objective=float(i)) for i in range(8)]
        a, method = propose(history, random.Random(9)); b, _ = propose(history, random.Random(9))
        self.assertEqual(a, b)
        self.assertIn(method, ('gp-ei', 'random (scikit-learn/scipy not installed)'))
        for key, (lo, hi) in SPACE.items():
            self.assertTrue(lo <= a[key] <= hi and type(a[key]) is float, key)

    def test_parse_seeds(self):
        self.assertEqual(parse_seeds('2031:hard,2032'), [(2031, 'hard'), (2032, 'normal')])


if __name__ == '__main__':
    unittest.main()
