#!/usr/bin/env bash
set -eo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$repo_root/tools/ros_env.sh"
exec "$@"
