#!/usr/bin/env bash
# Behavioral checks with ROS Python types, without processes or robot motion.
set -eo pipefail
source /opt/ros/jazzy/setup.bash
set -u
igvc_check_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$igvc_check_root"
export PYTHONPATH="$igvc_check_root/ros2/src/igvc_perception:$igvc_check_root/ros2/src/igvc_gps:$igvc_check_root/ros2/src/igvc_sim_bridge${PYTHONPATH:+:$PYTHONPATH}"
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
python3 -m unittest discover -s tools/tests -v
python3 -m unittest discover -s ros2/src/igvc_perception/test -v
python3 -m unittest discover -s ros2/src/igvc_gps/test -v
