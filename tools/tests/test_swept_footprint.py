import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from swept_footprint import arc_sweep_box
from sensor_route_policy import _rectangle_clear, select_local_goal


class DirectedSweepTests(unittest.TestCase):
    def test_straight_sweep_adds_no_unnecessary_lateral_width(self):
        b=(-1.12,.62,-.52,.52)
        x,y,yaw,box=arc_sweep_box((0,0,0),(.5,0,0),b)
        self.assertEqual((x,y,yaw),(.25,0.,0.))
        self.assertAlmostEqual(box[0],-1.37)
        self.assertAlmostEqual(box[1],.87)
        self.assertEqual(box[2:],b[2:])

    def test_encloses_actual_corner_arcs_for_both_turn_directions(self):
        b=(-1.12,.62,-.52,.52)
        for radius in (.65,1.5,4.):
            for sign in (-1,1):
                angle=sign*.3
                end=(radius*math.sin(abs(angle)),sign*radius*(1-math.cos(angle)),angle)
                x,y,yaw,box=arc_sweep_box((0,0,0),end,b)
                c,s=math.cos(yaw),math.sin(yaw)
                for i in range(101):
                    a=angle*i/100
                    px,py=radius*math.sin(abs(a)),sign*radius*(1-math.cos(a))
                    for bx in b[:2]:
                        for by in b[2:]:
                            dx=px+math.cos(a)*bx-math.sin(a)*by-x
                            dy=py+math.sin(a)*bx+math.cos(a)*by-y
                            xx,yy=c*dx+s*dy,-s*dx+c*dy
                            self.assertTrue(box[0]-1e-12<=xx<=box[1]+1e-12)
                            self.assertTrue(box[2]-1e-12<=yy<=box[3]+1e-12)

    def test_thin_barrier_between_clear_endpoints_still_blocks_sweep(self):
        grid=[0]*10000;grid[50*100+50]=100
        b=(-.05,.05,-.05,.05)
        self.assertTrue(_rectangle_clear(.3,.505,0,b,grid,100,100,.01,(0,0)))
        self.assertTrue(_rectangle_clear(.7,.505,0,b,grid,100,100,.01,(0,0)))
        x,y,a,box=arc_sweep_box((.3,.505,0),(.7,.505,0),b)
        self.assertFalse(_rectangle_clear(x,y,a,box,grid,100,100,.01,(0,0)))

    def test_clear_parallel_motion_remains_possible_beside_close_wall(self):
        size=160;grid=[0]*(size*size)
        for y in range(65,160):
            grid[y*size:(y+1)*size]=[100]*size
        # Padded side is y=6.495, only5mm clear of the wall; positive X
        # translation is safe and must not require isotropic8mm extra clearance.
        plan=select_local_goal((0,0),.1,size,size,grid,(3.,5.975),0.,(8.,5.975),
            robot_radius=.5,forward_only=True,goal_footprint=(-1.12,.62,-.52,.52),
            minimum_turn_radius=.65,min_goal_distance=.4,continuation_reserve=1.,lookahead=7.)
        self.assertIsNotNone(plan)
        self.assertGreater(plan['local_goal'][0],7.)

    def test_rear_corner_arc_hits_hazard_missed_by_endpoint_checks(self):
        b=(-1.1,.6,-.5,.5); size=450; grid=[0]*(size*size)
        # The rear lower corner reaches approximately(.035,-.941) halfway
        # through a 90-degree left turn of driven-axle radius .65m.
        grid[106*size+203]=100
        self.assertTrue(_rectangle_clear(0,0,0,b,grid,size,size,.01,(-2,-2)))
        self.assertTrue(_rectangle_clear(.65,.65,math.pi/2,b,grid,size,size,.01,(-2,-2)))
        x,y,a,box=arc_sweep_box((0,0,0),(.65,.65,math.pi/2),b)
        self.assertFalse(_rectangle_clear(x,y,a,box,grid,size,size,.01,(-2,-2)))

    def test_tiny_angle_stays_finite_and_converges_to_straight(self):
        b=(-1.12,.62,-.52,.52)
        a=arc_sweep_box((10,20,0),(10.1,20,0),b)
        tiny=arc_sweep_box((10,20,0),(10.1,20,1e-14),b)
        self.assertTrue(all(math.isfinite(v) for v in (*tiny[:3],*tiny[3])))
        for expected,actual in zip(a[3],tiny[3]):
            self.assertAlmostEqual(expected,actual,places=12)
