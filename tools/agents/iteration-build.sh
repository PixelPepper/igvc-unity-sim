#!/usr/bin/env bash
set -eo pipefail
iteration_root="$1"
source "$iteration_root/tools/ros_env.sh"
iteration_overlay="$IGVC_ROS_WORKSPACE"
iteration_endpoint="$iteration_root/artifacts/vendor/ROS-TCP-Endpoint"
test "$(git -C "$iteration_endpoint" rev-parse HEAD)" = 54c1a64b6d5ef6ffa0a0431570bb74329b79b15b
# Worker scope excludes description edits. Use the committed generated URDF;
# invoking xacro here would dirty it with a worktree-specific comment only.
test -z "$(git -C "$iteration_root" status --porcelain -- ros2/src/igvc_description)"
mkdir -p "$iteration_overlay"
cd "$iteration_overlay"
colcon --log-base "$iteration_overlay/log" build --executor sequential \
 --base-paths "$iteration_root/ros2/src" "$iteration_endpoint" \
 --build-base "$iteration_overlay/build" --install-base "$iteration_overlay/install" \
 --event-handlers console_direct+
