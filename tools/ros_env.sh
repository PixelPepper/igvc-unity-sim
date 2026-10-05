#!/usr/bin/env bash
# Source this file in WSL. Keep the transport probe isolated from other robots.
source /opt/ros/jazzy/setup.bash
# IGVC_INSTANCE=n (parallel simulations) moves the default domain to 60+n and TCP port to 10000+n.
if [[ -n "${IGVC_INSTANCE:-}" ]]; then
    export ROS_DOMAIN_ID="${IGVC_ROS_DOMAIN_ID:-$((60 + IGVC_INSTANCE))}"
    export IGVC_ROS_TCP_PORT="${IGVC_ROS_TCP_PORT:-$((10000 + IGVC_INSTANCE))}"
else
    export ROS_DOMAIN_ID="${IGVC_ROS_DOMAIN_ID:-42}"
fi
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
unset ROS_LOCALHOST_ONLY
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
igvc_repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export FASTRTPS_DEFAULT_PROFILES_FILE="$igvc_repo_root/ros2/config/fastdds.xml"
igvc_ros_workspace="${IGVC_ROS_WORKSPACE:-$HOME/igvc_ws}"
if [[ -f "$igvc_ros_workspace/install/setup.bash" ]]; then
    source "$igvc_ros_workspace/install/setup.bash"
fi
if [[ -f "$HOME/igvc_nav2_overlay/validated" ]]; then
    source "$HOME/igvc_nav2_overlay/install/local_setup.bash"
fi
