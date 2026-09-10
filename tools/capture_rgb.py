"""Capture one actual ROS RGB image as PNG for visual inspection."""
from pathlib import Path
import sys
import time
import struct
import zlib
import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image

rclpy.init()
node = rclpy.create_node('igvc_capture_rgb')
received = []
node.create_subscription(Image, '/camera/color/image_raw', received.append, qos_profile_sensor_data)
deadline = time.monotonic() + 15
while not received and time.monotonic() < deadline:
    rclpy.spin_once(node, timeout_sec=0.2)
if not received:
    raise SystemExit('No RGB received')
msg = received[0]
assert msg.encoding == 'rgb8' and msg.step == msg.width * 3
def chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
pixels = bytes(msg.data)
rows = b''.join(b'\0' + pixels[y * msg.step:(y + 1) * msg.step] for y in range(msg.height))
png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', msg.width, msg.height, 8, 2, 0, 0, 0))
png += chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b'')
Path(sys.argv[1]).write_bytes(png)
print(f'Captured {msg.width}x{msg.height} {msg.encoding} frame={msg.header.frame_id}')
node.destroy_node()
rclpy.shutdown()
