#!/usr/bin/env bash
# Source this file in WSL. Keep the transport probe isolated from other robots.
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID="${IGVC_ROS_DOMAIN_ID:-42}"
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
unset ROS_LOCALHOST_ONLY
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
igvc_repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export FASTRTPS_DEFAULT_PROFILES_FILE="$igvc_repo_root/ros2/config/fastdds.xml"
if [[ -f "$HOME/igvc_ws/install/setup.bash" ]]; then
    source "$HOME/igvc_ws/install/setup.bash"
fi
if [[ -f "$HOME/igvc_nav2_overlay/validated" ]]; then
    source "$HOME/igvc_nav2_overlay/install/local_setup.bash"
fi
