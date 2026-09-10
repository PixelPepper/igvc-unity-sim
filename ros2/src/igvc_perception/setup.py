from glob import glob
from setuptools import setup

setup(name='igvc_perception', version='0.1.0', packages=['igvc_perception'],
      options={'build_py': {'force': True}, 'install_lib': {'force': True}},
      data_files=[('share/ament_index/resource_index/packages', ['resource/igvc_perception']),
                  ('share/igvc_perception', ['package.xml']),
                  ('share/igvc_perception/launch', glob('launch/*.launch.py'))],
      install_requires=['setuptools'], zip_safe=True,
      entry_points={'console_scripts': ['lane_detector = igvc_perception.lane_node:main',
                                       'depth_processor = igvc_perception.depth_node:main']})
