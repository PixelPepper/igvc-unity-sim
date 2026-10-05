from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from capture_observed_clearance import validate_pair


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.receipts = {k: dict(arrival_wall_s=10.,stamp_ns=10_000_000_000,frame='odom')
                         for k in ('global','local','odom','lanes')}
        self.stationary = [(9.,1.,2.,0.,0.,0.,0.), (10.,1.,2.,0.,0.,0.,0.)]

    def test_accepts_fresh_stationary_pair(self):
        validate_pair(self.receipts,10.,self.stationary)

    def test_stale_zero_velocity_odom_is_rejected(self):
        self.receipts['odom']['arrival_wall_s'] = 7.
        with self.assertRaises(RuntimeError):
            validate_pair(self.receipts,10.,self.stationary)

    def test_fresh_receipts_with_old_acquisition_are_rejected(self):
        self.receipts['global']['stamp_ns'] = 8_000_000_000
        with self.assertRaises(RuntimeError):
            validate_pair(self.receipts,10.,self.stationary)

    def test_stationary_claim_cannot_hide_pose_drift(self):
        self.stationary[-1] = (10.,1.1,2.,0.,0.,0.,0.)
        with self.assertRaises(RuntimeError):
            validate_pair(self.receipts,10.,self.stationary)

    def test_moving_or_single_sample_rejected(self):
        for samples in ([self.stationary[-1]], [self.stationary[0],(10.,1.,2.,0.,0.,0.,.1)]):
            with self.subTest(samples=samples), self.assertRaises(RuntimeError):
                validate_pair(self.receipts,10.,samples)


if __name__ == '__main__':
    unittest.main()
