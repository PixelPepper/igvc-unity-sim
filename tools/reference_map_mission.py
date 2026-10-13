#!/usr/bin/env python3
"""Sanitized broad-destination mission for the image-traced reference map (T-0090).

Emits ONLY the autonomy schema accepted by tools/sensor_course.destinations: GPS origin, broad goals
(latitude/longitude/altitude/radius_m) and max_speed_mps. No route, heading, boundary or obstacle
geometry is exported; the robot must find the course with its sensors.

Frame: the drivable scene (Unity ReferenceDriveBuild) places the centre of the NORTH start line, image
pixel (960.5, 439), at odom (0, 0) with the robot heading image-up (north). With the traced map's isotropic
0.035 m/px scale this gives, for an image pixel (px, py):
    odom x (forward, image up)  = (439 - py) * 0.035
    odom y (left,    image left) = (960.5 - px) * 0.035
The GPS origin follows ros2/src/igvc_gps/config/origin.json (synthetic ideal GPS from odometry).

Destinations, in driving order (top -> left No Man's Land stars -> bottom -> south finish):
    top-right broad gate, the four pictured waypoint stars, south start/finish line centre.
"""
import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'ros2/src/igvc_gps'))
from igvc_gps.geodesy import LocalFrame  # noqa: E402

SCALE = .035
SPAWN_PX = (960.5, 439.)
MAX_SPEED = .6
# Image pixels of each broad destination with its acceptance radius (m).
DESTINATIONS_PX = (
    ('top-right gate', (940., 106.), 3.),
    ('waypoint star 1', (169., 250.), 2.),
    ('waypoint star 2', (164., 539.), 2.),
    ('waypoint star 3', (159., 633.), 2.),
    ('waypoint star 4', (177., 928.), 2.),
    ('south start/finish', (960.5, 711.), 2.),
)


def pixel_to_odom(px, py):
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (px, py)):
        raise ValueError('Pixel coordinates must be finite numbers')
    if not (0 <= px <= 1049 and 0 <= py <= 1160):
        raise ValueError('Pixel outside the traced image')
    return (SPAWN_PX[1]-py)*SCALE, (SPAWN_PX[0]-px)*SCALE


def build(origin=None, max_speed=MAX_SPEED):
    if origin is None:
        origin = json.loads((ROOT/'ros2/src/igvc_gps/config/origin.json').read_text())
    if not (isinstance(max_speed, (int, float)) and math.isfinite(max_speed) and 0 < max_speed <= 2.2):
        raise ValueError('Invalid max speed')
    keys = ('latitude', 'longitude', 'altitude', 'world_frame', 'axes', 'model', 'noise_stddev_m')
    sanitized = {k: origin[k] for k in keys if k in origin}
    frame = LocalFrame(sanitized)
    goals = []
    for _, (px, py), radius in DESTINATIONS_PX:
        x, y = pixel_to_odom(px, py)
        lat, lon, alt = frame.to_geodetic(x, y, 0.)
        goals.append(dict(latitude=lat, longitude=lon, altitude=alt, radius_m=float(radius)))
    return dict(schema_version=1, origin=sanitized, goals=goals, max_speed_mps=float(max_speed))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, required=True, help='autonomy.json to write')
    parser.add_argument('--max-speed', type=float, default=MAX_SPEED)
    args = parser.parse_args(argv)
    mission = build(max_speed=args.max_speed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(mission, indent=2)+'\n')
    print(json.dumps(dict(out=str(args.out), goals=len(mission['goals']), max_speed_mps=mission['max_speed_mps'])))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
