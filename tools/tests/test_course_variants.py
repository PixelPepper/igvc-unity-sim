"""Independent geometric assertions against generated public course data."""
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from generate_course_variant import generate


def rectangle(x,y,yaw,extents):
    c,s=math.cos(yaw),math.sin(yaw)
    a,b,h=extents
    return [(x+c*u-s*v,y+s*u+c*v) for u,v in ((a,-h),(b,-h),(b,h),(a,h))]


def segment_distance(p,a,b):
    v=(b[0]-a[0],b[1]-a[1]);length=v[0]**2+v[1]**2
    t=sum((p[k]-a[k])*v[k] for k in range(2))/length if length else 0
    t=min(1,max(0,t))
    return math.dist(p,(a[0]+t*v[0],a[1]+t*v[1]))


def separated_with_margin(a,b,margin):
    # A separating projection gap is a conservative independent clearance proof.
    for poly in (a,b):
        for i in range(4):
            p,q=poly[i],poly[(i+1)%4]
            length=math.dist(p,q);n=((p[1]-q[1])/length,(q[0]-p[0])/length)
            pa=[sum(v[k]*n[k] for k in range(2)) for v in a]
            pb=[sum(v[k]*n[k] for k in range(2)) for v in b]
            if max(min(pb)-max(pa),min(pa)-max(pb))>=margin:return True
    return False


class CourseVariantChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.course,cls.mission=generate(2027,'normal')

    def test_seed_determinism_and_variation(self):
        self.assertEqual((self.course,self.mission),generate(2027,'normal'))
        other,_=generate(2028,'normal')
        self.assertNotEqual(self.course['centerline'],other['centerline'])
        self.assertNotEqual(self.course['obstacles'],other['obstacles'])

    def test_closed_origin_forward_and_spacing(self):
        points=self.mission['route']['dense_xy']
        self.assertEqual(points[0],(0.,0.));self.assertEqual(points[-1],(0.,0.))
        self.assertGreater(points[1][0],0);self.assertLess(points[-2][0],0)
        self.assertAlmostEqual(points[1][1],0);self.assertAlmostEqual(points[-2][1],0)
        self.assertTrue(all(0<math.dist(a,b)<=.251 for a,b in zip(points,points[1:])))
        self.assertEqual(self.mission['waypoints'][-1]['yaw'],0)
        self.assertTrue(70<=len(self.mission['waypoints'])<=90)

    def test_counts_and_pothole_dimensions(self):
        kinds=[o['kind'] for o in self.course['obstacles']]
        self.assertEqual(kinds.count('barrel'),24);self.assertEqual(kinds.count('barricade'),8)
        self.assertEqual(kinds.count('pothole'),2)
        for o in self.course['obstacles']:
            if o['kind']=='pothole':
                self.assertTrue(.7<=o['width']<=1.1);self.assertTrue(.12<=o['depth']<=.25)
        easy,_=generate(13,'easy');hard,_=generate(13,'hard')
        self.assertEqual(sum(o['kind']=='pothole' for o in easy['obstacles']),1)
        self.assertEqual(sum(o['kind']=='pothole' for o in hard['obstacles']),3)

    def test_independent_route_footprint_clearance(self):
        points=self.mission['route']['dense_xy']
        # Also inspect interpolated half-steps, independently from generator checks.
        for i in range(len(points)-1):
            before=points[i-1] if i else points[-2];after=points[i+1]
            yaw=math.atan2(after[1]-before[1],after[0]-before[0])
            for t in (0.,.5):
                p=tuple(points[i][k]*(1-t)+after[k]*t for k in range(2))
                body=rectangle(*p,yaw,(-1.1,.6,.5))
                for o in self.course['obstacles']:
                    if math.dist(p,(o['x'],o['y']))>4:continue
                    if o['kind']=='barricade':
                        obstacle=rectangle(o['x'],o['y'],o['yaw'],(-o['length']/2,o['length']/2,o['width']/2))
                        self.assertTrue(separated_with_margin(body,obstacle,.2),o['id'])
                    else:
                        c,s=math.cos(yaw),math.sin(yaw);dx,dy=o['x']-p[0],o['y']-p[1]
                        local=(c*dx+s*dy,-s*dx+c*dy)
                        near=(min(.6,max(-1.1,local[0])),min(.5,max(-.5,local[1])))
                        self.assertGreaterEqual(math.dist(local,near)-o['width']/2,.2,o['id'])

    def test_no_obstacle_overlap(self):
        obstacles=self.course['obstacles']
        for i,a in enumerate(obstacles):
            for b in obstacles[i+1:]:
                # Bounding circles are stricter than the actual barricade shape.
                ra=math.hypot(a['length'],a['width'])/2 if a['kind']=='barricade' else a['width']/2
                rb=math.hypot(b['length'],b['width'])/2 if b['kind']=='barricade' else b['width']/2
                if math.dist((a['x'],a['y']),(b['x'],b['y']))>=ra+rb+.2:continue
                pa=rectangle(a['x'],a['y'],a['yaw'],(-a['length']/2,a['length']/2,a['width']/2))
                pb=rectangle(b['x'],b['y'],b['yaw'],(-b['length']/2,b['length']/2,b['width']/2))
                self.assertTrue(separated_with_margin(pa,pb,.2))

    def test_ramp_reservation_excludes_full_obstacle_extent(self):
        ramp=self.course['ramps'][0]
        self.assertEqual(self.course['schema_version'],1)
        self.assertEqual((ramp['x'],ramp['y'],ramp['width'],ramp['height']),(2.,0.,3.,.4))
        # Independent AABB/circle checks on the fixed yaw-zero reservation x1..11,y+-2.
        reserved=rectangle(6.,0.,0.,(-5.,5.,2.))
        for obstacle in self.course['obstacles']:
            if obstacle['kind']=='barricade':
                shape=rectangle(obstacle['x'],obstacle['y'],obstacle['yaw'],
                                (-obstacle['length']/2,obstacle['length']/2,obstacle['width']/2))
                self.assertTrue(separated_with_margin(reserved,shape,1e-9),obstacle['id'])
            else:
                closest=(min(11.,max(1.,obstacle['x'])),min(2.,max(-2.,obstacle['y'])))
                radius=max(obstacle['length'],obstacle['width'])/2+.85 if obstacle['kind']=='pothole' else obstacle['width']/2
                self.assertGreater(math.dist((obstacle['x'],obstacle['y']),closest),radius)

    def test_critical_ramp_poses_follow_dense_route_in_order(self):
        goals=self.mission['waypoints'];critical=[g for g in goals if 'ramp_checkpoint' in g]
        self.assertEqual([g['ramp_checkpoint'] for g in critical],
                         ['approach','start','deck_start','deck_end','exit','departure'])
        self.assertEqual([g['odom_xy'][0] for g in critical],[1.,2.,5.,7.,10.,11.])
        self.assertTrue(all(a['route_s_m']<b['route_s_m'] for a,b in zip(goals,goals[1:])))
        route=self.mission['route']
        for goal in critical:
            i=route['dense_s_m'].index(goal['route_s_m'])
            self.assertEqual(route['dense_xy'][i],goal['odom_xy'])
            self.assertEqual(goal['odom_xy'][1],0.)
        self.assertEqual(goals[-1]['odom_xy'],[0.,0.])

    def test_seed_and_difficulty_variants_cross_ramp_center(self):
        for seed,difficulty in [(7,'easy'),(2028,'normal'),(2029,'hard')]:
            with self.subTest(seed=seed,difficulty=difficulty):
                course,mission=generate(seed,difficulty)
                points=mission['route']['dense_xy']
                exit_index=next(i for i,p in enumerate(points) if p==(11.,0.))
                crossing=[p for p in points[:exit_index+1] if 2<=p[0]<=10]
                self.assertGreater(len(crossing),25)
                self.assertTrue(all(abs(p[1])<.65 for p in crossing))
                self.assertTrue(all(b[0]>a[0] for a,b in zip(points[:exit_index],points[1:exit_index+1])))
                self.assertEqual(course['ramps'],self.course['ramps'])

    def test_painted_boundary_margin(self):
        points=self.mission['route']['dense_xy'];normals=[]
        for i in range(len(points)-1):
            a=points[i-1] if i else points[-2];b=points[i+1]
            angle=math.atan2(b[1]-a[1],b[0]-a[0]);normals.append((-math.sin(angle),math.cos(angle)))
        normals.append(normals[0])
        widths=[p['half_width'] for p in self.course['centerline']]
        lines=[[(p[0]+side*w*n[0],p[1]+side*w*n[1]) for p,n,w in zip(points,normals,widths)] for side in (-1,1)]
        for i in range(0,len(points)-1,3):
            yaw=math.atan2(-normals[i][0],normals[i][1]);body=rectangle(*points[i],yaw,(-1.1,.6,.5))
            for line in lines:
                for j in range(max(0,i-16),min(len(points)-1,i+17)):
                    if not self.course['centerline'][j]['painted']:continue
                    self.assertGreater(min(segment_distance(p,line[j],line[j+1]) for p in body),.2)

    def test_ramp_paint_inside_edges_and_tapered(self):
        for p in self.course['centerline']:
            if 2<=p['x']<=10 and abs(p['y'])<.01:
                self.assertAlmostEqual(p['half_width'],1.44)
                self.assertLessEqual(p['half_width']+.06,1.5+1e-9)
        self.assertEqual(self.course['centerline'][0]['half_width'],3.)


if __name__=='__main__':unittest.main()
