#!/usr/bin/env python3
"""Sanitized broad-destination mission for the PROPOSED rule-dimensioned reference course (T-0091).

Reads ONLY the root-pinned spawn/goal metadata (metadata.json written by tools/reference_rules_geometry.py:
frame, spawn, odom_from_field, six goals). It never reads the world geometry/authoring input. Emits exactly the
existing autonomy schema accepted by tools/sensor_course.destinations: GPS origin, six broad goals
(latitude/longitude/altitude/radius_m) and max_speed_mps. No route, heading, boundary or obstacle geometry.

Frame: the Unity drive scene (ReferenceRulesDriveBuild) puts the north start-line centre at odom (0, 0) with the
robot heading north. For a field point (x east, y north):
    odom x (forward, north) = y - spawn_y
    odom y (left,    west)  = spawn_x - x
"""
import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'ros2/src/igvc_gps'))
from igvc_gps.geodesy import LocalFrame  # noqa: E402

DEFAULT_METADATA = ROOT/'artifacts/agents/T-0091/mission-metadata.json'
MAX_SPEED = .6
GOAL_NAMES = ('top-right gate', 'waypoint star 1', 'waypoint star 2', 'waypoint star 3', 'waypoint star 4',
              'south start/finish')
METADATA_KEYS = {'frame', 'spawn', 'odom_from_field', 'goals'}
ODOM = 'odom_x = y - spawn_y ; odom_y = spawn_x - x (spawn heading north)'


def _finite(*values):
    return all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in values)


def validate(meta):
    """Fail closed on anything but the exact spawn/goal metadata (no geometry may ride along)."""
    if not isinstance(meta, dict) or set(meta) != METADATA_KEYS:
        raise ValueError('metadata must contain exactly ' + ', '.join(sorted(METADATA_KEYS)))
    if meta['odom_from_field'] != ODOM:
        raise ValueError('unexpected odom transform')
    spawn = meta['spawn']
    if not isinstance(spawn, dict) or set(spawn) != {'field_xy', 'heading'} or spawn['heading'] != 'north':
        raise ValueError('spawn must be {field_xy, heading: north}')
    if not (isinstance(spawn['field_xy'], list) and len(spawn['field_xy']) == 2 and _finite(*spawn['field_xy'])):
        raise ValueError('spawn position must be two finite numbers')
    goals = meta['goals']
    if not isinstance(goals, list) or [g.get('name') if isinstance(g, dict) else None for g in goals] != list(GOAL_NAMES):
        raise ValueError('goals must be exactly, in order: ' + ', '.join(GOAL_NAMES))
    for g in goals:
        if set(g) != {'name', 'field_xy', 'radius_m'}:
            raise ValueError('goal keys must be name, field_xy, radius_m')
        if not (isinstance(g['field_xy'], list) and len(g['field_xy']) == 2 and _finite(*g['field_xy'])):
            raise ValueError('goal position must be two finite numbers')
        if not (_finite(g['radius_m']) and 0 < g['radius_m'] <= 5):
            raise ValueError('goal radius must be within (0, 5] m')
    return meta


def field_to_odom(meta, x, y):
    sx, sy = meta['spawn']['field_xy']
    return y-sy, sx-x


def build(meta, origin=None, max_speed=MAX_SPEED):
    validate(meta)
    if origin is None:
        origin = json.loads((ROOT/'ros2/src/igvc_gps/config/origin.json').read_text())
    if not (_finite(max_speed) and 0 < max_speed <= 2.2):
        raise ValueError('Invalid max speed')
    keys = ('latitude', 'longitude', 'altitude', 'world_frame', 'axes', 'model', 'noise_stddev_m')
    sanitized = {k: origin[k] for k in keys if k in origin}
    frame = LocalFrame(sanitized)
    goals = []
    for g in meta['goals']:
        ox, oy = field_to_odom(meta, *g['field_xy'])
        lat, lon, alt = frame.to_geodetic(ox, oy, 0.)
        goals.append(dict(latitude=lat, longitude=lon, altitude=alt, radius_m=float(g['radius_m'])))
    return dict(schema_version=1, origin=sanitized, goals=goals, max_speed_mps=float(max_speed))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--metadata', type=Path, default=DEFAULT_METADATA, help='pinned spawn/goal metadata.json')
    parser.add_argument('--out', type=Path, required=True, help='autonomy.json to write')
    parser.add_argument('--max-speed', type=float, default=MAX_SPEED)
    args = parser.parse_args(argv)
    mission = build(json.loads(args.metadata.read_text()), max_speed=args.max_speed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(mission, indent=2)+'\n')
    print(json.dumps(dict(out=str(args.out), goals=len(mission['goals']), max_speed_mps=mission['max_speed_mps'])))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
