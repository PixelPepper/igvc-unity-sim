#!/usr/bin/env python3
"""Replay captured depth through the current ground filter, without ROS or motion."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ros2/src/igvc_perception'))
from igvc_perception.depth import depth_points
from igvc_perception.ground import estimate_ground, terrain_obstacles
from igvc_perception.lanes import rotation_matrix
from igvc_perception.surfaces import classify_surfaces


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixture', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        parser.error('report exists; choose a new path')
    with np.load(args.fixture, allow_pickle=False) as fixture:
        depth, k = fixture['depth'], fixture['k']
        origin = fixture['origin']
        rotation = rotation_matrix(fixture['quaternion'])
        points = depth_points(depth, k, stride=4) @ rotation.T + origin
        candidate_image = depth.copy()
        candidate_image[:160] = np.nan
        candidates = depth_points(candidate_image, k, stride=4) @ rotation.T + origin
        result = dict(status='replayed', fixture=str(args.fixture),
                      stamp_ns=int(fixture['stamp_ns']), points=len(points),
                      candidates=len(candidates))
        try:
            plane = estimate_ground(candidates, origin)
            observed=classify_surfaces(depth,k,rotation,origin,plane)
            obstacles=observed['obstacles']
            result.update(ground=plane, ground_points=int(observed['ground_mask'].sum()),
                          legacy_obstacle_points=len(terrain_obstacles(points,origin,plane)),obstacle_points=len(obstacles),
                          obstacle_bounds=None if not len(obstacles) else
                          dict(min=obstacles.min(axis=0).tolist(), max=obstacles.max(axis=0).tolist()))
        except ValueError as exc:
            result.update(status='fit_rejected', reason=str(exc))
    result['limitations'] = ('Replays spatial filtering only, not transport, freshness or health. '
                             'A successful fit is not evidence that all visible surfaces share one plane.')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('x') as output:
        output.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
