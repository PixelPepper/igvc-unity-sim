#!/usr/bin/env bash
set -eo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
overlay="$HOME/igvc_nav2_overlay"
pin=6be3614013ec586051b86c97b919b293281490fe
test "$(dpkg-query -W -f='${Version}' ros-jazzy-nav2-mppi-controller | cut -d- -f1)" = 1.3.12
mkdir -p "$overlay"
if [[ ! -d "$overlay/upstream" ]]; then
    git clone --depth 1 --branch 1.3.12 https://github.com/ros-navigation/navigation2.git "$overlay/upstream"
fi
test "$(git -C "$overlay/upstream" rev-parse HEAD)" = "$pin"
if [[ ! -f "$overlay/upstream/nav2_mppi_controller/igvc-footprint-cost-critic-v1" ]]; then
    python3 "$repo_root/docker/patch_nav2_cost_critic.py" "$overlay/upstream"
fi
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths "$overlay/upstream/nav2_mppi_controller" --ignore-src --rosdistro jazzy -y
cd "$overlay"
rm -f "$overlay/validated"
MAKEFLAGS=-j2 CMAKE_BUILD_PARALLEL_LEVEL=2 colcon build --executor sequential \
    --base-paths upstream/nav2_mppi_controller --packages-select nav2_mppi_controller \
    --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
colcon test --packages-select nav2_mppi_controller --ctest-args -R '^critics_tests$' --output-on-failure
colcon test-result --verbose
printf '%s\n' "$pin" > validated
