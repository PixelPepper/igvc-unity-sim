from pathlib import Path
import math
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from path_entry import prepare_controller_plan

FOOTPRINT=(-1.12,.62,-.52,.52)


def body_corner(x,y,yaw,bx,by):
    return x+math.cos(yaw)*bx-math.sin(yaw)*by, y+math.sin(yaw)*bx+math.cos(yaw)*by


class PathEntryTests(unittest.TestCase):
    def setUp(self):
        self.plan={'path':[(2+i*.01,3.) for i in range(301)],'path_yaws':[0.]*301}
        self.costs=[0]*6400

    def admit(self,pose,costs=None,plan=None):
        return prepare_controller_plan(self.plan if plan is None else plan,pose,(0,0),.1,80,80,
            self.costs if costs is None else costs,FOOTPRINT)

    def fine_admit(self,pose,hazards):
        # 2 cm cells resolve body clearances a few centimetres wide.
        costs=[0]*160000
        for x,y in hazards:
            costs[math.floor(y/.02)*400+math.floor(x/.02)]=100
        return prepare_controller_plan(self.plan,pose,(0,0),.02,400,400,costs,FOOTPRINT)

    def assert_forward_drivable(self,plan,diagnostic,pose,original):
        points,yaws=plan['path'],plan['path_yaws']
        self.assertEqual(points[0],tuple(pose[:2]))
        self.assertEqual(yaws[0],pose[2])
        for (a,ya),(b,yb) in zip(zip(points,yaws),zip(points[1:],yaws[1:])):
            turn=math.atan2(math.sin(yb-ya),math.cos(yb-ya))
            step=math.dist(a,b)
            self.assertGreater(step,0)
            self.assertLessEqual(step,.1)
            # Ideal differential drive on one arc: the chord points along the
            # mean body yaw, forward, with curvature inside the turn radius.
            mean=ya+turn/2
            dx,dy=b[0]-a[0],b[1]-a[1]
            self.assertGreater(dx*math.cos(mean)+dy*math.sin(mean),0)
            self.assertLess(abs(-dx*math.sin(mean)+dy*math.cos(mean)),1e-6*step+1e-9)
            self.assertLessEqual(abs(turn)/step,1/.65*1.001)
        join=diagnostic['join_index']
        self.assertEqual(points[diagnostic['connector_samples']:],list(original['path'][join:]))
        self.assertEqual(yaws[diagnostic['connector_samples']:],list(original['path_yaws'][join:]))

    def test_prunes_consumed_path_and_starts_at_current_pose(self):
        plan,diagnostic=self.admit((2.8,3.03,.03))
        self.assertTrue(diagnostic['accepted'])
        self.assertEqual(plan['path'][0],(2.8,3.03))
        self.assertEqual(plan['path_yaws'][0],.03)
        self.assertEqual(plan['path'][-1],self.plan['path'][-1])
        self.assertLess(len(plan['path']),len(self.plan['path']))

    def test_lateral_offset_is_joined_forward_not_sideways(self):
        # Review counterexample: parallel to the path, 8 cm to its side.
        pose=(2.8,3.08,0.)
        plan,diagnostic=self.admit(pose)
        self.assertTrue(diagnostic['accepted'])
        self.assert_forward_drivable(plan,diagnostic,pose,self.plan)
        first=plan['path'][1]
        self.assertLess(abs(math.atan2(first[1]-pose[1],first[0]-pose[0])),.15)
        self.assertGreater(self.plan['path'][diagnostic['join_index']][0],pose[0])

    def test_small_offsets_and_headings_join_forward_on_straight_and_curved_paths(self):
        radius=2.
        curved={'path':[(2+radius*math.sin(i*.01/radius),1+radius*(1-math.cos(i*.01/radius)))
                        for i in range(301)],'path_yaws':[i*.01/radius for i in range(301)]}
        # Between vertices, so a nearest-vertex join could lie behind the robot.
        for plan,s in ((self.plan,.805),(curved,.805)):
            for offset in (-.095,-.03,0.,.05,.095):
                for heading in (-.14,0.,.07,.14):
                    with self.subTest(curved=plan is curved,offset=offset,heading=heading):
                        i=80
                        yaw=plan['path_yaws'][i]
                        x=(plan['path'][i][0]+(s-i*.01)*math.cos(yaw)-offset*math.sin(yaw))
                        y=(plan['path'][i][1]+(s-i*.01)*math.sin(yaw)+offset*math.cos(yaw))
                        pose=(x,y,yaw+heading)
                        admitted,d=self.admit(pose,plan=plan)
                        self.assertTrue(d['accepted'],d)
                        self.assert_forward_drivable(admitted,d,pose,plan)

    def test_connector_tail_swing_is_checked(self):
        # Wall 2-4 cm beyond the left body side of both the pose and the path.
        # Joining from the left requires a right yaw, swinging the rear-left
        # corner into it; a zero-yaw sideways slide would never touch it.
        wall=[(1.+i*.02,3.63) for i in range(150)]
        plan,d=self.fine_admit((2.8,3.08,0.),wall)
        self.assertIsNone(plan)
        self.assertEqual(d['reason'],'latest_observed_sweep_blocked')
        self.assertTrue(d['connector_blocked'])
        self.assertGreater(d['rejected_sample'],0)

    def test_blocked_gentle_connector_falls_back_to_shorter_forward_join(self):
        pose=(2.8,3.08,0.)
        gentle,d=self.fine_admit(pose,[])
        self.assertTrue(d['accepted'])
        # Hazard where only the gentle connector's front-right corner dips,
        # still beyond the checked path's right body side at y=2.48.
        corners=[body_corner(x,y,yaw,.62,-.52) for (x,y),yaw in
                 zip(gentle['path'][:d['connector_samples']],gentle['path_yaws'])]
        lowest=min(corners,key=lambda c:c[1])
        self.assertLess(lowest[1],2.46)
        plan,shorter=self.fine_admit(pose,[(lowest[0],lowest[1]+.001)])
        self.assertTrue(shorter['accepted'],shorter)
        self.assertLess(shorter['join_index'],d['join_index'])
        self.assert_forward_drivable(plan,shorter,pose,self.plan)

    def test_rejects_stale_lateral_and_heading_departures(self):
        for pose in ((2.8,3.231,0.),(2.8,3.,.676)):
            plan,d=self.admit(pose)
            self.assertIsNone(plan)
            self.assertEqual(d['reason'],'start_pose_departed_checked_path')

    def test_rejects_consumed_path_and_unreachable_join(self):
        plan,d=self.admit((4.7,3.,0.))
        self.assertIsNone(plan)
        self.assertEqual(d['reason'],'checked_path_already_consumed')
        # Heading away near the end: no forward join within the turn radius.
        plan,d=self.admit((4.6,3.09,.14))
        self.assertIsNone(plan)
        self.assertEqual(d['reason'],'no_forward_connector_within_turn_radius')

    def test_new_obstacle_or_unknown_in_remaining_path_rejects(self):
        for value in (100,-1):
            costs=self.costs.copy();costs[30*80+44]=value
            plan,d=self.admit((2.8,3.,0.),costs)
            self.assertIsNone(plan)
            self.assertEqual(d['reason'],'latest_observed_sweep_blocked')

    def test_body_corner_is_checked_even_if_axle_clear(self):
        costs=self.costs.copy();costs[35*80+18]=100
        plan,d=self.admit((2.8,3.,0.),costs)
        self.assertIsNone(plan)
        self.assertEqual(d['rejected_sample'],0)
