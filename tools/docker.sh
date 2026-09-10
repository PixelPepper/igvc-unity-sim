#!/usr/bin/env bash
set -euo pipefail
if ! command -v python3 >/dev/null 2>&1; then
    echo 'Install Python 3 (Ubuntu: sudo apt install python3) before using this launcher.' >&2
    exit 1
fi
exec python3 "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/linux_session.py" "$@"
