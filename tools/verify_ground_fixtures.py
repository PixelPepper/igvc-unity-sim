"""Read-only verification of actual GPU depth fixtures against analytic metadata."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'ros2/src/igvc_perception'))
from igvc_perception.depth import depth_points
from igvc_perception.ground import estimate_ground, terrain_obstacles
from igvc_perception.terrain_projection import project_plane


def verify(directory, name):
    meta_path, binary_path = directory/(name+'.json'), directory/(name+'.bin')
    meta_bytes, raw = meta_path.read_bytes(), binary_path.read_bytes()
    meta = json.loads(meta_bytes)
    if (meta['encoding'] != '32FC1' or meta['byte_order'] != 'little_endian'
            or meta['row_order'] != 'top_left' or (meta['height'], meta['width']) != (240, 320)
            or len(raw) != 240*320*4):
        raise ValueError('Fixture format mismatch')
    depth = np.frombuffer(raw, dtype='<f4').reshape(240, 320)
    origin = np.asarray(meta['camera_origin_ros'])
    rotation = np.asarray(meta['rotation_optical_to_ros']).reshape(3, 3)
    world = depth_points(depth, meta['K'], stride=4) @ rotation.T + origin
    lower = depth.copy()
    lower[:160] = np.nan
    candidates = depth_points(lower, meta['K'], stride=4) @ rotation.T + origin
    plane = estimate_ground(candidates, origin)
    expected_normal = np.asarray(meta['expected_plane_normal_ros'], dtype=float)
    expected_normal /= np.linalg.norm(expected_normal)
    expected_offset = float(meta['expected_plane_offset'])
    angle = float(np.degrees(np.arccos(np.clip(np.dot(plane['normal'], expected_normal), -1., 1.))))
    offset_error = abs(plane['offset']-expected_offset)
    obstacles = terrain_obstacles(world, origin, plane)
    # This known-plane mask comes from independent fixture truth, not fitted residual.
    known_plane = world[np.abs(world @ expected_normal+expected_offset) <= .02]
    false_ground = terrain_obstacles(known_plane, origin, plane)
    center, size = np.asarray(meta['obstacle_center_ros']), np.asarray(meta['obstacle_size_ros'])
    cube_observations = int(np.all(np.abs(obstacles-center) <= size/2+.02, axis=1).sum())
    # Surveyed plane locations are independent of the fitted coefficients.
    # Project them to RGB-style pinhole pixels, then recover them using the
    # plane estimated from the saved GPU depth buffer.
    xy=np.array([[x,y] for x in (1.5,2.,3.,4.) for y in (-.4,0.,.4)])
    z=-(xy@expected_normal[:2]+expected_offset)/expected_normal[2]
    surveyed=np.column_stack((xy,z))
    optical=(surveyed-origin)@rotation
    homogeneous=optical@np.asarray(meta['K']).reshape(3,3).T
    pixels=homogeneous[:,:2]/homogeneous[:,2,None]
    recovered=project_plane(pixels,meta['K'],rotation,origin,plane)
    projection_error=float(np.linalg.norm(recovered-surveyed,axis=1).max()) if recovered.shape==surveyed.shape else float('inf')
    checks = dict(confident=plane['inlier_fraction'] >= .6,
                  normal_angle_under_point2_deg=angle < .2,
                  offset_error_under_1cm=offset_error < .01,
                  at_least_five_cube_observations=cube_observations >= 5,
                  independent_known_ground_observed=len(known_plane) >= 100,
                  zero_ground_points_classified_obstacles=len(false_ground) == 0,
                  surveyed_plane_projection_under_1cm=projection_error < .01)
    return dict(name=name, passed=all(checks.values()), checks=checks, plane=plane,
                normal_angle_error_deg=angle, offset_error_m=offset_error,
                surveyed_projection_max_error_m=projection_error,
                total_points=len(world), lower_image_candidates=len(candidates),
                known_plane_points=len(known_plane), ground_false_obstacles=len(false_ground),
                obstacle_points=len(obstacles), cube_observations=cube_observations,
                depth_sha256=hashlib.sha256(raw).hexdigest(), metadata_sha256=hashlib.sha256(meta_bytes).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', type=Path, default=ROOT/'artifacts/checks/ground-fixtures')
    parser.add_argument('--output', type=Path, default=ROOT/'artifacts/checks/ground-render-live.json')
    args = parser.parse_args()
    results = []
    for name in ('flat', 'raised', 'inclined'):
        try:
            results.append(verify(args.fixtures, name))
        except (ValueError, KeyError, OSError) as exc:
            results.append(dict(name=name, passed=False, error=str(exc)))
    report = dict(passed=all(r['passed'] for r in results), fixtures=results,
                  scope='Actual saved GPU renders plus pure projection/ground classification; '
                        'not a live ROS transport, watchdog or moving-terrain validation.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
