#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
cd "$1"
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
export PYTHONPATH="$PWD/tools:$PWD/ros2/src/igvc_perception:$PWD/ros2/src/igvc_gps:$PWD/ros2/src/igvc_sim_bridge"
case "$2" in
  sonnet) python3 -m unittest discover -s ros2/src/igvc_perception/test -v ;;
  opus) python3 -m unittest tools.tests.test_path_entry tools.tests.test_execution_path tools.tests.test_sensor_route_policy tools.tests.test_swept_footprint tools.tests.test_observed_navigation -v ;;
  *) exit 2 ;;
esac
