import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'ros2/src/igvc_perception'))
from igvc_perception.point_memory import PointMemory


class PointMemoryTests(unittest.TestCase):
    def test_fresh_is_visible_but_isolated_detection_expires(self):
        memory = PointMemory(1200., 10)
        memory.observe([((1, 2), (1., 2., 0.))], 1, 0.)
        self.assertEqual(list(memory.values()), [((1., 2., 0.), 0.)])
        memory.expire(3.01)
        self.assertEqual(len(memory), 0)

    def test_distinct_frames_and_elapsed_span_confirm_real_paint(self):
        memory = PointMemory(1200., 10)
        for stamp, now in ((1, 0.), (2, .1), (3, .2), (4, .3), (5, .45)):
            memory.observe([((1, 2), (1., 2., 0.))], stamp, now)
        memory.expire(1000.)
        self.assertEqual(len(memory), 1)
        memory.expire(1201.)
        self.assertEqual(len(memory), 0)

    def test_duplicate_pixels_and_replayed_frame_do_not_confirm_or_refresh(self):
        memory = PointMemory(1200., 10)
        memory.observe([((1, 2), (1., 2., 0.))]*100, 1, 0.)
        memory.observe([((1, 2), (1., 2., 0.))], 1, 2.)
        memory.expire(3.01)
        self.assertEqual(len(memory), 0)

    def test_five_frames_in_short_burst_are_not_long_lived(self):
        memory = PointMemory(1200., 10)
        for stamp in (1, 2, 3, 4, 5):
            memory.observe([((1, 2), (1., 2., 0.))], stamp, stamp*.01)
        memory.expire(3.1)
        self.assertEqual(len(memory), 0)

    def test_reset_removes_confirmation_and_expired_candidate_starts_over(self):
        memory = PointMemory(1200., 10)
        for stamp in (1, 2, 3, 4, 5):
            memory.observe([((1, 2), (1., 2., 0.))], stamp, stamp*.2)
        memory.clear()
        memory.observe([((1, 2), (1., 2., 0.))], 6, 1.)
        memory.observe([((1, 2), (1., 2., 0.))], 7, 5.)
        memory.observe([((1, 2), (1., 2., 0.))], 8, 5.2)
        memory.expire(8.3)
        self.assertEqual(len(memory), 0)

    def test_capacity_and_short_configured_ttl_are_respected(self):
        memory = PointMemory(1., 2)
        memory.observe([(i, (i, 0., 0.)) for i in range(3)], 1, 0.)
        self.assertEqual(len(memory), 2)
        memory.expire(1.1)
        self.assertEqual(len(memory), 0)
