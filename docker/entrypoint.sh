#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/jazzy/setup.bash
source /opt/igvc/install/setup.bash
exec "$@"
