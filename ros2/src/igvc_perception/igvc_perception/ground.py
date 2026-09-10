"""Deterministic camera-relative ground fitting; no global-height oracle."""
import numpy as np


def _inputs(world, camera_origin):
    points = np.asarray(world, dtype=float)
    origin = np.asarray(camera_origin, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
        raise ValueError('Expected finite Nx3 world points')
    if origin.shape != (3,) or not np.isfinite(origin).all():
        raise ValueError('Expected finite camera origin')
    return points, origin


def _geometry(normal, offset, origin):
    slope = float(np.degrees(np.arccos(np.clip(normal[2], -1., 1.))))
    clearance = float(normal @ origin + offset)
    if slope > 20. or not .4 <= clearance <= 2.:
        raise ValueError('Ground slope or camera clearance outside supported limits')
    return slope


def _support(points):
    xy = points[:, :2]-points[:, :2].mean(axis=0)
    _, values, axes = np.linalg.svd(xy, full_matrices=False)
    if len(values) < 2 or values[1]/np.sqrt(len(points)) < .15:
        raise ValueError('Ground support is collinear or too narrow')
    projected = xy @ axes.T
    spans = np.quantile(projected, .95, axis=0)-np.quantile(projected, .05, axis=0)
    if spans[0] < 1. or spans[1] < .5:
        raise ValueError('Insufficient two-dimensional horizontal ground extent')


def estimate_ground(world, camera_origin):
    """Fit n.dot(world)+offset=0 with upward unit n, or raise ValueError.

    Caller supplies lower-image ground candidates. At most 1600 points and
    64 seeded hypotheses are used. Confidence requires >=100 inliers and
    >=60% of the sampled candidates within 35 mm, slope <=20 degrees and
    signed camera-to-plane distance 0.4..2 m. A failure must not imply Z=0.
    """
    points, origin = _inputs(world, camera_origin)
    if len(points) < 100:
        raise ValueError('At least 100 ground candidates required')
    rng = np.random.default_rng(0)
    if len(points) > 1600:
        points = points[np.sort(rng.choice(len(points), 1600, replace=False))]
    best = None
    for _ in range(64):
        a, b, c = points[rng.choice(len(points), 3, replace=False)]
        normal = np.cross(b-a, c-a)
        length = np.linalg.norm(normal)
        if length < 1e-9:
            continue
        normal /= length
        if normal[2] < 0:
            normal = -normal
        offset = -float(normal @ a)
        try:
            _geometry(normal, offset, origin)
        except ValueError:
            continue
        residual = np.abs(points @ normal + offset)
        mask = residual <= .035
        count = int(mask.sum())
        if count < 100 or count/len(points) < .6:
            continue
        score = (count, -float(np.mean(residual[mask]**2)))
        if best is None or score > best[0]:
            best = (score, mask)
    if best is None:
        raise ValueError('No confident ground plane')
    mask = best[1]
    # Two bounded least-squares refinements stabilize noisy hypotheses.
    for _ in range(2):
        inliers = points[mask]
        _support(inliers)
        center = inliers.mean(axis=0)
        _, _, axes = np.linalg.svd(inliers-center, full_matrices=False)
        normal = axes[-1]
        if normal[2] < 0:
            normal = -normal
        offset = -float(normal @ center)
        slope = _geometry(normal, offset, origin)
        residual = points @ normal + offset
        mask = np.abs(residual) <= .035
        if mask.sum() < 100 or mask.mean() < .6:
            raise ValueError('Ground confidence lost after refinement')
    _support(points[mask])
    rms = float(np.sqrt(np.mean(residual[mask]**2)))
    if not np.isfinite(rms) or rms > .035:
        raise ValueError('Ground residual too large')
    return dict(normal=normal.tolist(), offset=offset,
                inlier_fraction=float(mask.mean()), rms_m=rms, slope_deg=slope)


def terrain_obstacles(world, camera_origin, plane):
    """Retain signed plane heights 0.12..1.8 m and camera ranges <=10 m."""
    points, origin = _inputs(world, camera_origin)
    normal = np.asarray(plane['normal'], dtype=float)
    offset = float(plane['offset'])
    if (normal.shape != (3,) or not np.isfinite(normal).all() or not np.isfinite(offset)
            or not np.isclose(np.linalg.norm(normal), 1., atol=1e-6, rtol=0)):
        raise ValueError('Invalid ground plane')
    _geometry(normal, offset, origin)
    height = points @ normal + offset
    mask = (height >= .12) & (height <= 1.8) & (np.linalg.norm(points-origin, axis=1) <= 10.)
    return points[mask].astype(np.float32)
