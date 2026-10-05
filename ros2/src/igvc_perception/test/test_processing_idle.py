"""Real node tick methods with Jazzy messages and deterministic transport/TF."""
from collections import OrderedDict
from contextlib import ExitStack
import json
from pathlib import Path
import sys
from types import MethodType, SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import numpy as np
from std_msgs.msg import Header, String
from sensor_msgs.msg import Image, CameraInfo
from igvc_perception import depth_node, lane_node
from igvc_perception.point_memory import PointMemory
from igvc_perception.terrain_history import GroundHistory


class Publisher:
    def __init__(self): self.messages = []
    def publish(self, message): self.messages.append(message)
    def get_subscription_count(self): return 0


class ProcessingIdleTests(unittest.TestCase):
    def make_node(self, kind):
        module = depth_node if kind == 'depth' else lane_node
        cls = module.DepthNode if kind == 'depth' else module.LaneNode
        node = SimpleNamespace(images=OrderedDict(), infos=OrderedDict(),
            last_stamp=0, processing_healthy=False, last_success_receipt=float('-inf'),
            last_success_stamp=0, last_tick_wall=None, last_tick_ros=None,
            ground_prior=None, ground_prior_wall=float('-inf'), ground_prior_stamp=0,
            last_success=float('-inf'), last_arrival_stamp=0,
            points=PointMemory(8.,8000), hazard_points=PointMemory(8.,4000),
            surfaces=OrderedDict(), ground_history=GroundHistory(), ros_now=10_050_000_000)
        for name in ('healthy','status','valid','cloud','obstacles','surfaces_pub',
                     'debug','evidence','hazard_cloud','hazard_debug'):
            setattr(node,name,Publisher())
        if kind == 'depth': node.surfaces = Publisher()
        node.get_clock = lambda: SimpleNamespace(now=lambda: SimpleNamespace(nanoseconds=node.ros_now))
        for name in ('tick','success_is_fresh','reset'):
            setattr(node,name,MethodType(getattr(cls,name),node))
        node.stamp = cls.stamp
        if kind == 'depth':
            node.cache = MethodType(cls.cache,node)
            node.message = cls.message
        else:
            for name in ('clear','publish_cloud','image','info','ground_status','surface_cloud'):
                setattr(node,name,MethodType(getattr(cls,name),node))
            node.cache = cls.cache
        node.tf_ready = True
        node.tf = SimpleNamespace(can_transform=lambda *a: node.tf_ready,
            lookup_transform=lambda *a: SimpleNamespace(header=node.images[max(node.images)][0].header,
                transform=SimpleNamespace(translation=SimpleNamespace(x=0.,y=0.,z=1.),
                    rotation=SimpleNamespace(x=0.,y=0.,z=0.,w=1.))))
        return module,node

    def pair(self, node, kind, wall=100., stamp=10_000_000_000, malformed=False):
        header=Header(frame_id='camera')
        header.stamp.sec,header.stamp.nanosec=divmod(stamp,1_000_000_000)
        width,height=(320,240) if kind=='depth' else (640,480)
        step=width*(4 if kind=='depth' else 3)
        image=Image(header=header,width=width,height=height,step=step,
            encoding='bad' if malformed else '32FC1' if kind=='depth' else 'rgb8',
            data=bytes(height*step))
        info=CameraInfo(header=header,width=width,height=height,
            k=[100.,0.,width/2,0.,100.,height/2,0.,0.,1.])
        node.images[stamp]=(image,wall);node.infos[stamp]=(info,wall)
        if kind=='lane':
            plane={'inlier_fraction':.9,'rms_m':.01,'slope_deg':0.}
            node.ground_history.update({'valid':True,'stamp_ns':stamp,'ground':plane},wall)
            node.surfaces[stamp]=(np.empty((0,4)),wall)

    def tick(self, module, node, wall):
        with patch.object(module.time,'monotonic',return_value=wall): node.tick()

    def succeed(self, module, node, kind):
        self.pair(node,kind)
        with ExitStack() as stack:
            if kind=='depth':
                stack.enter_context(patch.object(module,'depth_points',return_value=np.empty((0,3))))
                stack.enter_context(patch.object(module,'estimate_ground',return_value={}))
                stack.enter_context(patch.object(module,'classify_surfaces',return_value={
                    'obstacles':np.empty((0,3)),'valid_mask':np.zeros((1,1),bool),
                    'ground_mask':np.zeros((1,1),bool),'grid_world':np.zeros((1,1,3))}))
            else:
                mask=np.zeros((480,640),np.uint8)
                stack.enter_context(patch.object(module,'lane_pixels',return_value=(np.empty((0,2)),mask,0)))
                stack.enter_context(patch.object(module,'hazard_pixels',return_value=(np.empty((0,2)),mask,0)))
                stack.enter_context(patch.object(module,'project_observed',return_value=np.empty((0,3))))
            self.tick(module,node,100.05)
        self.assertTrue(node.healthy.messages[-1].data)
        self.assertTrue(node.processing_healthy)

    def counts(self,node):
        return {k:len(v.messages) for k,v in vars(node).items() if isinstance(v,Publisher)}

    def test_idle_and_new_pair_tf_jitter_leave_all_publications_untouched(self):
        for kind in ('depth','lane'):
            with self.subTest(kind=kind):
                module,node=self.make_node(kind);self.succeed(module,node,kind)
                before=self.counts(node);stamp=node.last_success_stamp
                node.ros_now=10_250_000_000
                self.tick(module,node,100.25)
                self.assertEqual(self.counts(node),before)
                self.assertEqual(node.last_success_stamp,stamp)
                self.pair(node,kind,wall=100.2,stamp=10_200_000_000)
                node.tf_ready=False
                self.tick(module,node,100.4)
                self.assertEqual(self.counts(node),before)
                self.assertEqual(node.last_success_receipt,100.)
                # Visibility false is a successfully processed empty lane frame.
                if kind=='lane': self.assertFalse(node.valid.messages[-1].data)
                self.tick(module,node,100.501)
                self.assertFalse(node.healthy.messages[-1].data)

    def test_missing_pair_and_each_existing_freshness_deadline_fail_closed(self):
        for kind in ('depth','lane'):
            module,node=self.make_node(kind)
            self.tick(module,node,100.)
            self.assertFalse(node.healthy.messages[-1].data)
            for wall,ros in ((100.501,10_250_000_000),(100.25,10_500_000_001)):
                with self.subTest(kind=kind,wall=wall,ros=ros):
                    module,node=self.make_node(kind);self.succeed(module,node,kind)
                    node.ros_now=ros;self.tick(module,node,wall)
                    self.assertFalse(node.healthy.messages[-1].data)
                    self.assertFalse(node.processing_healthy)

    def test_malformed_new_pair_cannot_resurrect_success_on_idle(self):
        for kind in ('depth','lane'):
            with self.subTest(kind=kind):
                module,node=self.make_node(kind);self.succeed(module,node,kind)
                self.pair(node,kind,100.1,10_100_000_000,malformed=True)
                node.ros_now=10_150_000_000
                self.tick(module,node,100.15)
                self.assertFalse(node.healthy.messages[-1].data)
                self.assertFalse(node.processing_healthy)
                node.images.clear();node.infos.clear()
                self.tick(module,node,100.2)
                self.assertFalse(node.healthy.messages[-1].data)
                self.assertIn('pair',json.loads(node.status.messages[-1].data)['reason'])

    def test_reset_and_receipt_or_ros_clock_regression_invalidate_success(self):
        for kind in ('depth','lane'):
            for action in ('reset','wall_backwards','ros_backwards','image_backwards'):
                with self.subTest(kind=kind,action=action):
                    module,node=self.make_node(kind);self.succeed(module,node,kind)
                    if action=='reset': node.reset(None,SimpleNamespace())
                    elif action=='image_backwards':
                        old=node.images[10_000_000_000][0]
                        old.header.stamp.sec=9
                        with patch.object(module.time,'monotonic',return_value=100.1):
                            if kind=='depth': node.cache(node.images,old)
                            else:
                                node.last_arrival_stamp=10_000_000_000
                                node.image(old)
                    else:
                        if action=='ros_backwards': node.ros_now=9_900_000_000
                        self.tick(module,node,99.9 if action=='wall_backwards' else 100.1)
                    self.assertFalse(node.processing_healthy)
                    self.assertFalse(node.healthy.messages[-1].data)
                    self.tick(module,node,100.2)
                    self.assertFalse(node.healthy.messages[-1].data)

    def test_lane_explicit_failed_depth_or_malformed_surface_invalidates_idle(self):
        for failure in ('ground','surface'):
            with self.subTest(failure=failure):
                module,node=self.make_node('lane');self.succeed(module,node,'lane')
                if failure=='ground': node.ground_status(String(data='{"valid":false}'))
                else: node.surface_cloud(SimpleNamespace(header=Header(frame_id='bad')))
                self.tick(module,node,100.2)
                self.assertFalse(node.healthy.messages[-1].data)


if __name__=='__main__': unittest.main()
