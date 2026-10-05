"""Recorded ideal simulation regression; not hardware or re-entry validation."""
import hashlib
import json
from pathlib import Path
import unittest

import cv2
import numpy as np

from igvc_perception.lanes import lane_pixels, rotation_matrix
from igvc_perception.surface_projection import project_observed


FIXTURE = Path(__file__).resolve().parents[4]/'fixtures'/'white_barrel_cap'


class RecordedLaneProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.metadata = json.loads((FIXTURE/'metadata.json').read_text())
        cls.rgb = cv2.cvtColor(cv2.imread(str(FIXTURE/'rgb.png')), cv2.COLOR_BGR2RGB)
        with np.load(FIXTURE/'surfaces.npz', allow_pickle=False) as arrays:
            cls.surfaces = arrays['surfaces_xy_z_ground'].copy()

    def test_exact_source_acquisitions_and_fixture_integrity(self):
        m = self.metadata
        self.assertEqual(m['kind'], 'recorded_ideal_unity_simulation_fixture')
        self.assertEqual(m['depth_pairing_purpose'], 'projection_source')
        rgb_stamp, ground_stamp = m['anchor_acquisition_stamp_ns'], m['projection_ground_stamp_ns']
        self.assertLess(ground_stamp, rgb_stamp)  # Independent preceding exposure.
        self.assertEqual(m['lane_status']['stamp_ns'], rgb_stamp)
        self.assertEqual(m['lane_status']['ground_stamp_ns'], ground_stamp)
        for key in ('rgb', 'rgb_info', 'mask', 'lane_status'):
            observation = m['observations'][key]
            self.assertEqual(observation['acquisition_stamp_ns'], rgb_stamp)
            self.assertEqual(observation['pairing']['status'], 'exact')
        for key in ('depth', 'depth_info', 'surfaces'):
            observation = m['observations'][key]
            self.assertEqual(observation['acquisition_stamp_ns'], ground_stamp)
            self.assertEqual(observation['pairing']['target_stamp_ns'], ground_stamp)
            self.assertEqual(observation['pairing']['status'], 'exact')
        self.assertTrue(m['rgb_camera']['valid'])
        self.assertEqual(m['rgb_transform']['acquisition_stamp_ns'], rgb_stamp)
        self.assertEqual(m['depth_transform']['acquisition_stamp_ns'], ground_stamp)
        for name, digest in m['files_sha256'].items():
            self.assertEqual(hashlib.sha256((FIXTURE/name).read_bytes()).hexdigest(), digest)
        self.assertEqual(hashlib.sha256(self.surfaces.tobytes()).hexdigest(), m['surface_data_sha256'])
        self.assertLess(sum(p.stat().st_size for p in FIXTURE.iterdir() if p.is_file()), 150000)

    def test_accepted_white_barrel_cap_has_no_eligible_lane_projection(self):
        _, mask, _ = lane_pixels(self.rgb)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
        expected = self.metadata['white_barrel_cap']
        cap_labels = [i for i in range(1, count) if stats[i, :4].tolist() == expected['bbox_xywh']]
        self.assertEqual(len(cap_labels), 1, 'Known visible white-barrel cap must be exercised')
        cap = labels == cap_labels[0]
        self.assertEqual(int(cap.sum()), 811)
        y, x = np.nonzero(cap)
        cap_pixels = np.column_stack((x, y))
        tf = self.metadata['rgb_transform']
        args = dict(k=self.metadata['rgb_camera']['k'], rotation=rotation_matrix(tf['quaternion_xyzw']),
                    origin=tf['translation'], world_points=self.surfaces[:, :3])
        projected = project_observed(cap_pixels, **args, eligible_mask=self.surfaces[:, 3] > 0)
        self.assertEqual(len(projected), 0, 'Elevated barrel cap must never become ground paint')
        # The cap has observed depth; this proves eligibility rejection rather
        # than a fixture whose cap simply has no matching observations.
        without_ground_gate = project_observed(cap_pixels, **args)
        self.assertGreater(len(without_ground_gate), 0)
        # Exercise real near ground paint from the same image and depth source.
        paint_y, paint_x = np.nonzero((mask > 0) & ~cap & (np.indices(mask.shape)[0] > 300))
        paint_pixels = np.column_stack((paint_x, paint_y))
        self.assertGreater(len(paint_pixels), 0)
        paint = project_observed(paint_pixels, **args, eligible_mask=self.surfaces[:, 3] > 0)
        self.assertGreater(len(paint), 0, 'Ground eligibility must retain actually observed paint')


if __name__ == '__main__':
    unittest.main()
