"""Simulator entrypoints must run camera processing on the simulation clock."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

from launch import LaunchContext
from launch_ros.actions import Node as LaunchNode
from launch_ros.utilities import evaluate_parameters, normalize_parameters
import rclpy
from rclpy.context import Context
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.time import Time

SRC = Path(__file__).resolve().parents[2]
ENTRYPOINTS = {
    'perception': SRC / 'igvc_perception/launch/perception.launch.py',
    'local_navigation': SRC / 'igvc_navigation/launch/local_navigation.launch.py',
}
CAMERA_NODES = ('lane_detector', 'depth_processor')


class RecordingNode(LaunchNode):
    """Real launch_ros Node that also remembers its constructor arguments."""
    created = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.recorded = kwargs
        RecordingNode.created.append(self)


def effective_parameters(entrypoint, share):
    spec = importlib.util.spec_from_file_location(f'launch_{entrypoint}', ENTRYPOINTS[entrypoint])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.Node = RecordingNode
    # Only package-share lookup is stubbed; the MPPI overlay marker is a temp file.
    module.get_package_share_directory = lambda package: str(share)
    RecordingNode.created = []
    description = module.generate_launch_description()
    context = LaunchContext()
    resolved = {}
    for node in RecordingNode.created:
        if node.recorded['package'] != 'igvc_perception':
            continue
        params = {}
        for item in evaluate_parameters(context, normalize_parameters(
                node.recorded.get('parameters', []))):
            params.update(item)
        resolved[node.recorded['executable']] = params
    return description, resolved


class SimulationClockLaunchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.share = Path(self.temp.name)
        (self.share / 'igvc-footprint-cost-critic-v1').write_text('marker')

    def tearDown(self):
        self.temp.cleanup()

    def test_camera_nodes_use_sim_time_in_every_simulator_entrypoint(self):
        for entrypoint in ENTRYPOINTS:
            description, resolved = effective_parameters(entrypoint, self.share)
            self.assertTrue(description.entities)
            for executable in CAMERA_NODES:
                with self.subTest(entrypoint=entrypoint, node=executable):
                    self.assertIn(executable, resolved)
                    self.assertIs(resolved[executable].get('use_sim_time'), True)

    def test_unrelated_parameters_are_preserved(self):
        _, resolved = effective_parameters('local_navigation', self.share)
        self.assertEqual(resolved['lane_detector']['point_ttl'], 1200.0)
        self.assertIs(resolved['scan_ground_filter']['use_sim_time'], True)
        _, resolved = effective_parameters('perception', self.share)
        self.assertNotIn('point_ttl', resolved['lane_detector'])


class SimulationClockBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.context = Context()
        rclpy.init(context=self.context)
        self.temp = tempfile.TemporaryDirectory()
        share = Path(self.temp.name)
        (share / 'igvc-footprint-cost-critic-v1').write_text('marker')
        self.resolved = {name: effective_parameters(name, share)[1] for name in ENTRYPOINTS}

    def tearDown(self):
        self.temp.cleanup()
        rclpy.shutdown(context=self.context)

    def make_node(self, name, use_sim_time):
        node = Node(name, context=self.context,
                    parameter_overrides=[Parameter('use_sim_time', value=use_sim_time)])
        self.addCleanup(node.destroy_node)
        return node

    def test_resolved_parameter_puts_node_clock_on_simulation_time(self):
        acquisition = Time(seconds=10, nanoseconds=0)
        for entrypoint, resolved in self.resolved.items():
            for executable in CAMERA_NODES:
                with self.subTest(entrypoint=entrypoint, node=executable):
                    node = self.make_node(executable, resolved[executable]['use_sim_time'])
                    clock = node.get_clock()
                    self.assertTrue(clock.ros_time_is_active)
                    # Deterministic stand-in for one /clock message from the simulator.
                    clock.set_ros_time_override(Time(seconds=10, nanoseconds=50_000_000))
                    now = clock.now().nanoseconds
                    self.assertEqual(now - acquisition.nanoseconds, 50_000_000)
                    wall = Node(f'{executable}_wall', context=self.context)
                    self.addCleanup(wall.destroy_node)
                    self.assertGreater(abs(wall.get_clock().now().nanoseconds - now), 10**15)

    def test_hardware_default_remains_wall_clock(self):
        node = Node('lane_detector_hardware', context=self.context)
        self.addCleanup(node.destroy_node)
        self.assertFalse(node.get_parameter('use_sim_time').value)
        self.assertFalse(node.get_clock().ros_time_is_active)


if __name__ == '__main__':
    unittest.main()
