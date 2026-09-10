"""Read-only RGB/perception snapshot for diagnosing a stopped course."""
import argparse,json,time
from pathlib import Path
import cv2,numpy as np,rclpy
from sensor_msgs.msg import Image
from std_msgs.msg import String
from rclpy.qos import qos_profile_sensor_data
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
rclpy.init();node=rclpy.create_node('igvc_course_frame_capture');latest={}
for key,topic,typ in [('rgb','/camera/color/image_raw',Image),('mask','/perception/lanes/debug',Image),('status','/perception/lanes/status',String)]:
    node.create_subscription(typ,topic,lambda m,k=key:latest.update({k:m}),qos_profile_sensor_data)
end=time.monotonic()+8
try:
    while len(latest)<3 and time.monotonic()<end:rclpy.spin_once(node,timeout_sec=.1)
    for key in ('rgb','mask'):
        m=latest[key];channels=3 if key=='rgb' else 1
        data=np.frombuffer(m.data,np.uint8).reshape(m.height,m.step)[:,:m.width*channels].reshape(m.height,m.width,channels)
        cv2.imwrite(str(a.output/(key+'.png')),cv2.cvtColor(data,cv2.COLOR_RGB2BGR) if channels==3 else data)
    print(latest['status'].data)
finally:node.destroy_node();rclpy.shutdown()
