"""Export broad GPS destinations offline, without exposing course geometry.

The source mission/course is privileged fixture data. Only the exported JSON
belongs in the autonomy process. Goals specify regions, not a drivable path.
"""
import argparse
import bisect
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ros2/src/igvc_gps'))
from igvc_gps.geodesy import LocalFrame

ORIGIN_FIELDS = ('latitude', 'longitude', 'altitude', 'world_frame', 'axes',
                 'model', 'noise_stddev_m')
# Six regional destinations, including the far-side region and start/finish.
# These intentionally do not encode slalom turns, lane gaps or ramp approaches.
REGION_FRACTIONS = (.16, .32, .54, .70, .84, 1.)


def export_mission(mission, course=None):
    """Return a new allowlisted mission, without mutating either source.

    Pass course to sample its centerline rather than its obstacle-aware guide.
    Mission-only export supports previously generated fixtures using their
    offline route geometry; that geometry is never copied to the output.
    """
    origin = {key: mission['origin'][key] for key in ORIGIN_FIELDS
              if key in mission['origin']}
    if any(isinstance(value, (dict, list, tuple)) for value in origin.values()):
        raise ValueError('Origin fields must be scalar values')
    frame = LocalFrame(origin)
    raw = ([(p['x'], p['y']) for p in course['centerline']] if course is not None
           else mission['route']['dense_xy'])
    points = [tuple(float(v) for v in p) for p in raw]
    if len(points) < 3 or any(len(p) != 2 or not all(map(math.isfinite, p))
                              for p in points):
        raise ValueError('Source must contain finite two-dimensional loop points')
    if math.dist(points[0], (0., 0.)) > 1e-6 or math.dist(points[-1], points[0]) > 1e-6:
        raise ValueError('Source loop must start and finish at the GPS origin')
    distances = [0.]
    for a, b in zip(points, points[1:]):
        distances.append(distances[-1] + math.dist(a, b))
    if distances[-1] <= 0.:
        raise ValueError('Source loop has zero length')
    goals = []
    for fraction in REGION_FRACTIONS[:-1]:
        distance = fraction * distances[-1]
        index = min(len(points) - 2, bisect.bisect_right(distances, distance) - 1)
        ratio = (distance - distances[index]) / (distances[index + 1] - distances[index])
        east, north = (a + ratio * (b - a) for a, b in zip(points[index], points[index + 1]))
        lat, lon, alt = frame.to_geodetic(east, north)
        goals.append(dict(latitude=lat, longitude=lon, altitude=alt, radius_m=2.))
    goals.append({**{key: origin[key] for key in ('latitude', 'longitude', 'altitude')},
                  'radius_m': .4})
    return dict(schema_version=1, origin=origin, goals=goals, max_speed_mps=2.2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mission', type=Path, required=True)
    parser.add_argument('--course', type=Path, help='Use the unshaped course centerline')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve() in {p.resolve() for p in (args.mission, args.course) if p}:
        parser.error('Output must be separate from the source mission and course')
    mission = json.loads(args.mission.read_text(encoding='utf-8-sig'))
    course = json.loads(args.course.read_text(encoding='utf-8-sig')) if args.course else None
    result = export_mission(mission, course)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
