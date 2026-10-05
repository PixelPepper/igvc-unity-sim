import unittest

from igvc_perception.point_memory import PointMemory


class PointEvidenceTests(unittest.TestCase):
    def test_retained_points_keep_original_acquisition_and_age(self):
        memory = PointMemory(1200., 100)
        memory.observe([('a', (1., 2., 0.))], 12_123456789, 10.)
        memory.observe([('b', (3., 4., 0.))], 13_987654321, 11.)
        rows = memory.evidence_rows(12.)
        self.assertEqual(rows[0][3:], (2., 1, 0, 12, 123456789))
        self.assertEqual(rows[1][3:], (1., 1, 0, 13, 987654321))

    def test_duplicate_frames_do_not_earn_confirmation(self):
        memory = PointMemory(1200., 100)
        for i in range(6):
            memory.observe([('a', (1., 2., 0.))], 12_123456789, 10.+i*.2)
        self.assertEqual(memory.evidence_rows(12.)[0][4:6], (1, 0))
        for i in range(1, 5):
            memory.observe([('a', (1., 2., 0.))], 12_123456789+i, 12.+i*.2)
        self.assertEqual(memory.evidence_rows(13.)[0][4:6], (5, 1))

    def test_clear_removes_provenance(self):
        memory = PointMemory(1200., 100)
        memory.observe([('a', (1., 2., 0.))], 1, 10.)
        memory.clear()
        self.assertEqual(memory.evidence_rows(11.), [])
