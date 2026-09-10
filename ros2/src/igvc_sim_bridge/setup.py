from glob import glob
from setuptools import setup

setup(name='igvc_sim_bridge', version='0.1.0', packages=['igvc_sim_bridge'],
      # Windows/WSL clocks can differ; never reuse stale timestamp-cached Python modules.
      options={'build_py': {'force': True}, 'install_lib': {'force': True}},
      data_files=[('share/ament_index/resource_index/packages', ['resource/igvc_sim_bridge']),
                  ('share/igvc_sim_bridge', ['package.xml']),
                  ('share/igvc_sim_bridge/launch', glob('launch/*.py')),
                  ('share/igvc_sim_bridge/rviz', glob('rviz/*.rviz'))],
      install_requires=['setuptools'], zip_safe=True,
      entry_points={'console_scripts': ['probe_adapter = igvc_sim_bridge.probe_adapter:main',
                                       'verify_probe = igvc_sim_bridge.verify_probe:main']})
