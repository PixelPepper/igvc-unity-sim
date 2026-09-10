"""Compare delivered image/clock rates using one selected subscription QoS."""
import sys
import time
import json
import rclpy
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image
from rosgraph_msgs.msg import Clock

rclpy.init()
node = rclpy.create_node('igvc_stream_measure')
qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE if sys.argv[1] == 'reliable' else ReliabilityPolicy.BEST_EFFORT)
counts = {'image': 0, 'clock': 0}
first = {}
last = {}
def receive(name, msg):
    counts[name] += 1
    s = msg.header.stamp if name == 'image' else msg.clock
    stamp = s.sec + s.nanosec * 1e-9
    first.setdefault(name, stamp)
    last[name] = stamp
node.create_subscription(Image, '/camera/color/image_raw', lambda m: receive('image', m), qos)
node.create_subscription(Clock, '/clock', lambda m: receive('clock', m), qos)
start = time.monotonic()
while time.monotonic() - start < 15:
    rclpy.spin_once(node, timeout_sec=0.1)
print(json.dumps({'qos': sys.argv[1], 'counts': counts, 'elapsed': time.monotonic()-start, 'first': first, 'last': last}))
node.destroy_node()
rclpy.shutdown()
