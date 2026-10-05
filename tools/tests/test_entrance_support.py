from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from entrance_support import corridor_fresh_support


class EntranceSupportTests(unittest.TestCase):
    def setUp(self):
        self.corridor = dict(diagnostics=dict(segments=[[[0,-2],[4,-2]],[[0,2],[4,2]]]))
        self.points = [[x,y,0,.2,5,1,10,0] for x in (0, .5, 1, 2, 3) for y in (-2,2)]

    def test_recent_ground_paint_on_both_sides_can_refresh(self):
        support = corridor_fresh_support(self.corridor,self.points,.1)
        self.assertTrue(support['valid'])
        self.assertEqual(support['support_stamp_ns'],10_000_000_000)

    def test_acquisition_proof_uses_the_older_supported_side(self):
        for point in self.points:
            if point[1] > 0:
                point[6] = 11
        self.assertEqual(corridor_fresh_support(self.corridor,self.points,.1)['support_stamp_ns'],
                         10_000_000_000)

    def test_new_cloud_header_cannot_refresh_old_points(self):
        for point in self.points:
            point[3] = 120.
        self.assertFalse(corridor_fresh_support(self.corridor,self.points,.001)['valid'])

    def test_single_side_and_duplicate_points_are_not_bilateral_support(self):
        for points in ([p for p in self.points if p[1] < 0], [self.points[0]]*50):
            self.assertFalse(corridor_fresh_support(self.corridor,points,.1)['valid'])

    def test_reception_delay_counts_toward_age(self):
        self.assertFalse(corridor_fresh_support(self.corridor,self.points,1.4)['valid'])
