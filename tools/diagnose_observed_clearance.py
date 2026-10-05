"""Explain a saved planner rejection using observed cells only; no motion or map oracle."""
import argparse
import json
import math
from pathlib import Path
from sensor_route_policy import _rectangle_clear


def diagnose(snapshot):
    width, height = snapshot['width'], snapshot['height']
    costs, resolution, origin = snapshot['costs'], snapshot['resolution'], snapshot['origin']
    x, y, yaw = snapshot['pose']
    bounds = tuple(snapshot.get('goal_footprint', (-1.12, .62, -.52, .52)))
    if (not isinstance(width, int) or not isinstance(height, int) or min(width, height) <= 0
            or len(costs) != width*height or not all(isinstance(c, int) and -1 <= c <= 100 for c in costs)
            or not math.isfinite(resolution) or resolution <= 0
            or len(origin) != 2 or len(bounds) != 4
            or not all(math.isfinite(v) for v in [x, y, yaw, *origin, *bounds])
            or bounds[0] >= bounds[1] or bounds[2] >= bounds[3]):
        raise ValueError('Invalid observed grid, pose or footprint')
    clear = lambda px, py: _rectangle_clear(px, py, yaw, bounds, costs,
                                            width, height, resolution, origin)
    # Isolate each candidate with the same SAT routine used by the planner.
    # This explains that routine; it is not independent physical collision evidence.
    reach = math.hypot(max(abs(bounds[0]), abs(bounds[1])), max(abs(bounds[2]), abs(bounds[3])))+resolution
    blockers = []
    empty = [0]*(width*height)
    inside_grid = _rectangle_clear(x, y, yaw, bounds, empty, width, height, resolution, origin)
    for iy in range(max(0, math.floor((y-reach-origin[1])/resolution)),
                    min(height, math.ceil((y+reach-origin[1])/resolution)+1)):
        for ix in range(max(0, math.floor((x-reach-origin[0])/resolution)),
                        min(width, math.ceil((x+reach-origin[0])/resolution)+1)):
            value = costs[iy*width+ix]
            if 0 <= value < 100:
                continue
            empty[iy*width+ix] = value
            intersects = not _rectangle_clear(x, y, yaw, bounds, empty,
                                              width, height, resolution, origin)
            empty[iy*width+ix] = 0
            if inside_grid and intersects:
                cx, cy = origin[0]+(ix+.5)*resolution, origin[1]+(iy+.5)*resolution
                paint = snapshot.get('lane_points', [])
                nearest = min((math.dist((cx, cy), p[:2]) for p in paint), default=None)
                blockers.append({'cell': [ix, iy], 'world_xy': [cx, cy], 'cost': value,
                                 'nearest_remembered_paint_m': nearest})
    rear = 0.
    if clear(x, y):
        for step in range(1, 37):
            distance = step*.05
            if not clear(x-distance*math.cos(yaw), y-distance*math.sin(yaw)):
                break
            rear = distance
    ix, iy = math.floor((x-origin[0])/resolution), math.floor((y-origin[1])/resolution)
    center = costs[iy*width+ix] if 0 <= ix < width and 0 <= iy < height else None
    return {'footprint': bounds, 'footprint_source': 'recorded Nav2 parameters' if 'goal_footprint' in snapshot else 'current default; old snapshot lacks parameters',
            'pose': [x, y, yaw], 'inside_grid': inside_grid, 'center_cost': center,
            'center_passes': center is not None and 0 <= center < 99,
            'footprint_clear': clear(x, y), 'blocking_cell_count': len(blockers),
            'blocking_cells': blockers[:64], 'sampled_rear_clearance_m': rear,
            'limits': 'Observed costmap explanation, not ground truth. Paint proximity does not prove '
                'which layer created a cell. Rear checks sample at 0.05 m and do not authorize backup '
                'or establish useful forward continuation. Old snapshots may lack time alignment.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observations', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--grid', choices=('global', 'local'), help='Select a grid from an atomic paired capture')
    args = parser.parse_args()
    snapshot = json.loads(args.observations.read_text())
    report = diagnose(snapshot[args.grid] if args.grid else snapshot)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps({key: report[key] for key in ('footprint_clear', 'blocking_cell_count', 'sampled_rear_clearance_m')}))
