#!/usr/bin/env bash
set -eo pipefail
cd "$(dirname "$0")/.."
source_dir=artifacts/vendor/scr_simulator
pin=0298b11c4f469404d08b37ad98431cdab6e02818
mkdir -p artifacts/vendor artifacts/checks artifacts/logs
if [[ ! -d "$source_dir" ]]; then
    git clone https://github.com/SoonerRobotics/scr_simulator.git "$source_dir"
    git -C "$source_dir" checkout "$pin"
fi
[[ "$(git -C "$source_dir" rev-parse HEAD)" == "$pin" ]] || { echo 'Existing Sooner checkout has a different revision'; exit 1; }
python3 tools/import_sooner_course.py
