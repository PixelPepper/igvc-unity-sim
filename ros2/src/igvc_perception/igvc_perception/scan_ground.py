"""Suppress only lidar returns supported by a local observed ground surface.

This is a marking filter. Removed returns are NaN, never infinite clearing rays.
The caller retains raw measured ranges for its independent clearing input.
"""
import math
import numpy as np


def filter_ground_returns(ranges, angle_min, angle_increment, range_min, range_max,
                          rotation, origin, surface_points, ground_flags, *,
                          xy_radius=.3, height_tolerance=.04):
    """Return (ranges_copy, diagnostics); geometry is entirely observation-based.

    The nearest ground sample must be within xy_radius. At least three
    non-collinear samples within 0.6 m must agree on a plane with <=20 degree
    slope and <=25 mm maximum fitting residual. The larger plane neighborhood
    spans sparse organized depth rows without extrapolating outside support. The hit
    must be inside their XY convex support and within height_tolerance vertically.
    Nearby unclassified/elevated surface evidence preserves ambiguous returns.
    Caller enforces exact lidar TF and causal, fresh surface support.
    """
    values = np.asarray(ranges, dtype=float)
    rotation, origin = np.asarray(rotation, dtype=float), np.asarray(origin, dtype=float)
    params = [angle_min, angle_increment, range_min, range_max, xy_radius, height_tolerance]
    if (values.ndim != 1 or len(values) > 8192 or not all(math.isfinite(v) for v in params)
            or range_min < 0 or range_max <= range_min or not 0 < xy_radius <= .3
            or not 0 < height_tolerance <= .04
            or rotation.shape != (3, 3) or not np.isfinite(rotation).all()
            or not np.allclose(rotation.T@rotation, np.eye(3), atol=1e-6, rtol=0)
            or not np.isclose(np.linalg.det(rotation), 1., atol=1e-6, rtol=0)
            or origin.shape != (3,) or not np.isfinite(origin).all()):
        raise ValueError('Invalid scan geometry')
    output = values.copy()
    valid = np.isfinite(values) & (values >= range_min) & (values <= range_max)
    diagnostics = dict(valid_returns=int(valid.sum()), removed_ground=0,
                       ambiguous_returns=0, reason='supported_ground_filter')
    if surface_points is None or ground_flags is None:
        diagnostics['reason'] = 'no_surface_support'
        return output, diagnostics
    points, ground = np.asarray(surface_points, dtype=float), np.asarray(ground_flags)
    if (points.ndim != 2 or points.shape[1] != 3 or len(points) > 10000
            or not np.isfinite(points).all() or ground.dtype != np.bool_
            or ground.shape != (len(points),)):
        raise ValueError('Invalid observed surface support')
    if len(points) < 3 or int(ground.sum()) < 3:
        diagnostics['reason'] = 'insufficient_surface_support'
        return output, diagnostics
    ids = np.flatnonzero(valid)
    angles = angle_min+ids*angle_increment
    local = np.column_stack((values[ids]*np.cos(angles), values[ids]*np.sin(angles), np.zeros(len(ids))))
    hits = local@rotation.T+origin
    for start in range(0, len(hits), 128):
        batch = hits[start:start+128]
        squared = np.sum((batch[:, None, :2]-points[None, :, :2])**2, axis=2)
        for index, hit in enumerate(batch):
            nearby = squared[index] <= xy_radius**2
            # An obstacle near the measured height could be the real source of
            # this return, even when adjacent ground is visible behind it.
            if np.any(nearby & ~ground & (np.abs(points[:, 2]-hit[2]) <= .12)):
                diagnostics['ambiguous_returns'] += 1
                continue
            if not np.any(nearby & ground):
                continue
            support = points[(squared[index] <= .6**2) & ground]
            if len(support) < 3:
                continue
            xy = support[:, :2]-hit[:2]
            if np.any(xy.min(axis=0) > 0) or np.any(xy.max(axis=0) < 0):
                continue
            # An angular gap greater than pi places the hit outside the support
            # polygon. Do not extrapolate a road plane across an observed edge.
            directions = xy[np.linalg.norm(xy, axis=1) > 1e-9]
            angles = np.sort(np.arctan2(directions[:, 1], directions[:, 0]))
            if len(angles) < 3 or np.max(np.diff(np.r_[angles, angles[0]+2*np.pi])) > np.pi+1e-8:
                continue
            centered = xy-xy.mean(axis=0)
            eigenvalues = np.linalg.eigvalsh(centered.T@centered/len(centered))
            if eigenvalues[0] < .005**2:
                continue
            design = np.column_stack((xy, np.ones(len(xy))))
            coefficients, _, _, _ = np.linalg.lstsq(design, support[:, 2], rcond=None)
            if (np.linalg.norm(coefficients[:2]) > math.tan(math.radians(20))
                    or np.max(np.abs(design@coefficients-support[:, 2])) > .025
                    or abs(float(coefficients[2])-hit[2]) > height_tolerance):
                continue
            output[ids[start+index]] = np.nan
            diagnostics['removed_ground'] += 1
    return output, diagnostics
