from glob import glob
from setuptools import setup

setup(name='igvc_gps', version='0.1.0', packages=['igvc_gps'],
      options={'build_py': {'force': True}, 'install_lib': {'force': True}},
      data_files=[('share/ament_index/resource_index/packages', ['resource/igvc_gps']),
                  ('share/igvc_gps', ['package.xml']),
                  ('share/igvc_gps/config', glob('config/*.json')),
                  ('share/igvc_gps/launch', glob('launch/*.py'))],
      install_requires=['setuptools'], zip_safe=True,
      entry_points={'console_scripts': ['synthetic_gps = igvc_gps.synthetic_gps:main']})
