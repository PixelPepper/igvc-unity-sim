"""Canonical-description behavior tests; no ROS runtime required."""
import hashlib
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'ros2/src/igvc_sim_bridge'))
from igvc_sim_bridge.suspension_description import with_caster_suspension


class SuspensionDescriptionTests(unittest.TestCase):
    def setUp(self):
        self.path=ROOT/'ros2/src/igvc_description/urdf/r3_a.urdf'
        self.source=self.path.read_text()

    def test_original_unchanged_and_zero_pose_chain(self):
        digest=hashlib.sha256(self.path.read_bytes()).hexdigest()
        original=ET.fromstring(self.source)
        result=ET.fromstring(with_caster_suspension(self.source,.045))
        self.assertEqual(digest,hashlib.sha256(self.path.read_bytes()).hexdigest())
        for side in ('left','right'):
            before=original.find(f"joint[@name='{side}Caster']")
            after=result.find(f"joint[@name='{side}Caster']")
            slider=result.find(f"joint[@name='{side}_caster_suspension_joint']")
            self.assertEqual(before.find('origin').attrib,slider.find('origin').attrib)
            self.assertEqual(after.find('origin').get('xyz'),'0 0 0')
            self.assertEqual(after.find('origin').get('rpy'),'0 0 0')
            self.assertEqual(before.find('child').attrib,after.find('child').attrib)
            self.assertEqual(before.find('axis').attrib,after.find('axis').attrib)
            self.assertEqual(before.get('type'),after.get('type'))

    def test_slider_geometry_and_travel(self):
        robot=ET.fromstring(with_caster_suspension(self.source,.045))
        for side,sign in [('left',1),('right',-1)]:
            joint=robot.find(f"joint[@name='{side}_caster_suspension_joint']")
            self.assertEqual(joint.get('type'),'prismatic')
            self.assertEqual(joint.find('axis').get('xyz'),'0 0 1')
            self.assertEqual(joint.find('parent').get('link'),'base_link')
            child=joint.find('child').get('link')
            self.assertIsNotNone(robot.find(f"link[@name='{child}']"))
            self.assertEqual(robot.find(f"joint[@name='{side}Caster']/parent").get('link'),child)
            for a,b in zip(map(float,joint.find('origin').get('xyz').split()),[-.52775,sign*.24612,-.03635]):
                self.assertAlmostEqual(a,b,places=5)
            self.assertEqual(float(joint.find('limit').get('lower')),-.045)
            self.assertEqual(float(joint.find('limit').get('upper')),.045)

    def test_invalid_limits(self):
        for value in [0,-.01,.101,float('nan'),float('inf')]:
            with self.subTest(value=value),self.assertRaises(ValueError):
                with_caster_suspension(self.source,value)

    def test_missing_canonical_joint_rejected(self):
        root=ET.fromstring(self.source)
        root.remove(root.find("joint[@name='leftCaster']"))
        with self.assertRaises(ValueError):with_caster_suspension(ET.tostring(root,encoding='unicode'),.04)

    def test_noncanonical_parent_rejected(self):
        root=ET.fromstring(self.source)
        root.find("joint[@name='rightCaster']/parent").set('link','wheel_left')
        with self.assertRaises(ValueError):with_caster_suspension(ET.tostring(root,encoding='unicode'),.04)


if __name__=='__main__':unittest.main()
