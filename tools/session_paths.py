"""Per-instance session paths for parallel simulations.

Unset IGVC_INSTANCE keeps the original single-simulator layout (artifacts/session,
TCP 10000, domain 42). Instance n (1..8) gets its own session/log folders, TCP port
10000+n and, via ros_env.sh, ROS domain 60+n, so isolated instances never share state.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_INSTANCES = 8


def instance():
    value = os.environ.get('IGVC_INSTANCE', '').strip()
    if not value:
        return None
    if not value.isdigit() or not 1 <= int(value) <= MAX_INSTANCES:
        raise ValueError(f'IGVC_INSTANCE must be 1..{MAX_INSTANCES}')
    return int(value)


def session_dir(root=ROOT):
    n = instance()
    return Path(root) / 'artifacts/session' / (f'instance-{n}' if n else '')


def log_dir(root=ROOT):
    n = instance()
    return Path(root) / 'artifacts/logs' / (f'instance-{n}' if n else '')


def tcp_port():
    n = instance()
    return 10000 + (n or 0)
