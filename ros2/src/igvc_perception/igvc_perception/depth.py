"""Ideal depth geometry only; no ROS, simulator labels or course geometry.

Input is a decoded 240x320 floating-point image in metres, with optical Z
depth (not Euclidean range). Rows run top to bottom; optical axes are right,
down, forward. Transport byte order and Image.step decoding belong to caller.
"""
import numpy as np


def depth_points(depth, k, stride=4):
    """Project valid sampled pixels to Nx3 optical XYZ, returned as float32.

    CameraInfo K must describe this 320x240 image (do not reuse RGB K without
    scaling). Valid optical Z is inclusive 0.2..10 m; NaN/inf/other depths drop.
    Pixel coordinates are integer centres, sampled from row/column zero.
    """
    depth = np.asarray(depth)
    if depth.shape != (240, 320) or depth.dtype.kind != 'f':
        raise ValueError('Expected 240x320 floating-point optical-Z depth image')
    if isinstance(stride, (bool, np.bool_)) or not isinstance(stride, (int, np.integer)) or stride < 1:
        raise ValueError('stride must be a positive integer')
    k = np.asarray(k, dtype=float)
    if k.shape not in ((3, 3), (9,)):
        raise ValueError('K must be 3x3 or nine row-major values')
    k = k.reshape(3, 3)
    if (not np.isfinite(k).all() or k[0, 0] <= 0 or k[1, 1] <= 0
            or not np.allclose(k[2], [0, 0, 1], atol=1e-9, rtol=0)
            or abs(k[1, 0]) > 1e-9
            or not (0 <= k[0, 2] < 320 and 0 <= k[1, 2] < 240)):
        raise ValueError('Invalid pinhole intrinsics for 320x240 image')
    rows, cols = np.mgrid[0:240:stride, 0:320:stride]
    z = depth[::stride, ::stride].ravel()
    valid = np.isfinite(z) & (z >= .2) & (z <= 10.)
    pixels = np.column_stack((cols.ravel()[valid], rows.ravel()[valid], np.ones(valid.sum())))
    rays = pixels @ np.linalg.inv(k).T
    # K's final row makes rays[:,2] == 1; multiplying by Z preserves axial depth.
    points = rays*z[valid, None]
    points = points[np.isfinite(points).all(axis=1)]
    return points.astype(np.float32)


def obstacle_points(opticalpoints, rotation, origin, ground_z=0):
    """Transform to odom and keep heights 0.12..1.8 m above ground_z.

    Rotation maps optical vectors into odom; origin is the camera position in
    odom. Maximum range is 10 m Euclidean distance from the camera. Invalid
    points and points behind the optical camera are dropped. This does not
    detect negative obstacles, estimate terrain, or model stereo uncertainty.
    """
    points = np.asarray(opticalpoints, dtype=float)
    rotation = np.asarray(rotation, dtype=float)
    origin = np.asarray(origin, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError('Expected Nx3 optical points')
    if (rotation.shape != (3, 3) or not np.isfinite(rotation).all()
            or not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-6, rtol=0)
            or not np.isclose(np.linalg.det(rotation), 1., atol=1e-6, rtol=0)):
        raise ValueError('rotation must be a finite proper orthonormal matrix')
    if origin.shape != (3,) or not np.isfinite(origin).all() or not np.isfinite(ground_z):
        raise ValueError('Expected finite camera origin and ground height')
    valid = np.isfinite(points).all(axis=1) & (points[:, 2] > 0)
    points = points[valid]
    points = points[np.linalg.norm(points, axis=1) <= 10.]
    world = points @ rotation.T + origin
    height = world[:, 2]-ground_z
    world = world[np.isfinite(world).all(axis=1) & (height >= .12) & (height <= 1.8)]
    return world.astype(np.float32)
