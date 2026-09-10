#!/usr/bin/env bash
set -eo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$repo_root/tools/ros_env.sh"
# Expand the canonical description before installing it or importing it into Unity.
xacro "$repo_root/ros2/src/igvc_description/urdf/r3_a.urdf.xacro" \
    -o "$repo_root/ros2/src/igvc_description/urdf/r3_a.urdf"
endpoint="$repo_root/artifacts/vendor/ROS-TCP-Endpoint"
pin=54c1a64b6d5ef6ffa0a0431570bb74329b79b15b
if [[ ! -d "$endpoint/.git" ]]; then
    git clone https://github.com/Unity-Technologies/ROS-TCP-Endpoint.git "$endpoint"
    git -C "$endpoint" checkout "$pin"
fi
[[ "$(git -C "$endpoint" rev-parse HEAD)" == "$pin" ]] || { echo 'Endpoint pin mismatch'; exit 1; }
mkdir -p "$HOME/igvc_ws"
cd "$HOME/igvc_ws"
colcon --log-base "$HOME/igvc_ws/log" build \
    --executor sequential \
    --base-paths "$repo_root/ros2/src" "$endpoint" \
    --build-base "$HOME/igvc_ws/build" --install-base "$HOME/igvc_ws/install" \
    --event-handlers console_direct+
