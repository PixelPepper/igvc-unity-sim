import unittest
import numpy as np
from igvc_perception.terrain_projection import project_plane


class TerrainProjectionTests(unittest.TestCase):
    def setUp(self):
        self.K=np.array([[240.,0,159.5],[0,240.,119.5],[0,0,1.]])
        # Optical right=-worldY, down=-worldZ, forward=worldX.
        self.R=np.array([[0.,0,1],[-1,0,0],[0,-1,0]])
        self.origin=np.array([0.,0.,1.1])
        self.plane=dict(normal=[0.,0.,1.],offset=0.)

    def pixels_of(self,points):
        optical=(points-self.origin)@self.R
        homogeneous=optical@self.K.T
        return homogeneous[:,:2]/homogeneous[:,2,None]

    def test_known_world_points_flat_raised_and_ten_degree_slope(self):
        for height,degrees in ((0.,0.),(.195,0.),(.195,10.)):
            with self.subTest(height=height,degrees=degrees):
                angle=np.deg2rad(degrees)
                x=np.array([1.5,2.5,4.,6.]);y=np.array([-.5,.4,1.,-.7])
                points=np.column_stack((x,y,height+np.tan(angle)*x))
                plane=dict(normal=[-np.sin(angle),0.,np.cos(angle)],offset=-height*np.cos(angle))
                actual=project_plane(self.pixels_of(points),self.K,self.R,self.origin,plane)
                self.assertEqual(actual.dtype,np.float32)
                np.testing.assert_allclose(actual,points,atol=1e-6)

    def test_old_fixed_zero_plane_has_measurable_bias(self):
        point=np.array([[3.,.3,.195]])
        pixels=self.pixels_of(point)
        correct=project_plane(pixels,self.K,self.R,self.origin,dict(normal=[0,0,1],offset=-.195))
        incorrect=project_plane(pixels,self.K,self.R,self.origin,self.plane)
        np.testing.assert_allclose(correct,point,atol=1e-6)
        self.assertGreater(np.linalg.norm(incorrect-point),.5)

    def test_parallel_behind_camera_and_zero_intersection_discarded(self):
        pixels=np.array([[159.5,119.5],[159.5,80.]])
        self.assertEqual(project_plane(pixels,self.K,self.R,self.origin,self.plane).shape,(0,3))
        on_plane=project_plane([[159.5,200]],self.K,self.R,[0,0,0],self.plane,minimum=0)
        self.assertEqual(on_plane.shape,(0,3))

    def test_xy_range_is_from_camera_not_world_origin_or_ray_length(self):
        self.origin=np.array([50.,-20.,1.1])
        points=np.array([[50.5,-20,0],[51.5,-20,0],[53,-16,0],[61,-20,0]])
        actual=project_plane(self.pixels_of(points),self.K.ravel(),self.R,self.origin,self.plane,minimum=1,maximum=5.01)
        np.testing.assert_allclose(actual,points[1:3],atol=1e-6)

    def test_empty_pixels_have_stable_output_shape(self):
        actual=project_plane(np.empty((0,2)),self.K,self.R,self.origin,self.plane)
        self.assertEqual(actual.shape,(0,3));self.assertEqual(actual.dtype,np.float32)

    def test_invalid_inputs_rejected(self):
        valid=dict(pixels=[[160.,200.]],K=self.K,rotation=self.R,origin=self.origin,plane=self.plane)
        cases=[dict(pixels=[1,2]),dict(pixels=[[np.nan,2]]),dict(K=np.eye(2)),
               dict(K=np.zeros((3,3))),dict(K=np.full((3,3),np.inf)),
               dict(rotation=np.eye(3)*2),dict(rotation=np.diag([-1.,1,1])),
               dict(rotation=np.full((3,3),np.nan)),dict(origin=[0,0]),dict(origin=[0,0,np.inf]),
               dict(plane=dict(normal=[0,0,-1],offset=0)),dict(plane=dict(normal=[0,0,2],offset=0)),
               dict(plane=dict(normal=[1,0,0],offset=0)),dict(plane=dict(normal=[0,0,1],offset=np.nan)),
               dict(plane={}),dict(minimum=-1),dict(maximum=.5),dict(maximum=np.inf)]
        for changes in cases:
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                project_plane(**(valid|changes))


if __name__=='__main__':unittest.main()
