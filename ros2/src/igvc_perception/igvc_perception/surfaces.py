"""Conservative observed surface connectivity, not semantic traversability or contact.

An organized range image supplies local normals and adjacency. The near fitted
plane seeds connectivity only; it is never extrapolated to label connected ramps.
"""
from collections import deque
import numpy as np
from .depth import depth_points


def classify_surfaces(depth, k, rotation, origin, plane):
    """Return stride-four world grid, valid/ground masks and positive obstacles.

    Missing samples and rejected edges are not filled. Geometry alone cannot
    distinguish a genuinely connected shallow object top from a shallow ramp.
    """
    depth = np.asarray(depth)
    depth_points(depth, k, stride=4)  # Shared image/intrinsics validation.
    k = np.asarray(k, dtype=float).reshape(3, 3)
    rotation = np.asarray(rotation, dtype=float)
    origin = np.asarray(origin, dtype=float)
    if (rotation.shape != (3, 3) or not np.isfinite(rotation).all()
            or not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-6, rtol=0)
            or not np.isclose(np.linalg.det(rotation), 1., atol=1e-6, rtol=0)
            or origin.shape != (3,) or not np.isfinite(origin).all()):
        raise ValueError('Invalid camera transform')
    try:
        normal = np.asarray(plane['normal'], dtype=float)
        offset = float(plane['offset'])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('Invalid observed ground plane') from exc
    if (normal.shape != (3,) or not np.isfinite(normal).all() or not np.isfinite(offset)
            or not np.isclose(np.linalg.norm(normal), 1., atol=1e-6, rtol=0)
            or normal[2] < np.cos(np.deg2rad(20))
            or not .4 <= normal @ origin + offset <= 2.):
        raise ValueError('Invalid observed ground plane')
    rows, cols = np.mgrid[0:240:4, 0:320:4]
    rays = np.stack((cols, rows, np.ones_like(rows)), axis=-1) @ np.linalg.inv(k).T
    axial = depth[::4, ::4]
    with np.errstate(invalid='ignore', over='ignore'):
        optical = rays * axial[..., None]
        world = optical @ rotation.T + origin
        valid = (np.isfinite(world).all(axis=-1) & (axial >= .2) & (axial <= 10)
                 & (np.linalg.norm(optical, axis=-1) <= 10))
    world[~valid] = np.nan
    h, w = valid.shape

    # One-sided derivatives avoid smearing normals across depth discontinuities.
    # Select the shorter valid edge on each image axis; do not infer missing edges.
    derivatives = []
    for axis in (1, 0):
        positive = np.full_like(world, np.nan)
        negative = np.full_like(world, np.nan)
        if axis == 1:
            positive[:, :-1] = world[:, 1:] - world[:, :-1]
            negative[:, 1:] = world[:, 1:] - world[:, :-1]
        else:
            positive[:-1] = world[1:] - world[:-1]
            negative[1:] = world[1:] - world[:-1]
        lp = np.linalg.norm(positive, axis=-1)
        ln = np.linalg.norm(negative, axis=-1)
        use_positive = np.isfinite(lp) & (~np.isfinite(ln) | (lp <= ln))
        derivatives.append(np.where(use_positive[..., None], positive, negative))
    normals = np.cross(derivatives[0], derivatives[1])
    lengths = np.linalg.norm(normals, axis=-1)
    with np.errstate(invalid='ignore', divide='ignore'):
        normals = normals / lengths[..., None]
    normals *= np.where(normals[..., 2] < 0, -1., 1.)[..., None]
    walkable = valid & np.isfinite(normals).all(axis=-1) & (normals[..., 2] >= np.cos(np.deg2rad(20)))
    seeds = walkable & (rows >= 160) & (np.abs(world @ normal + offset) <= .035)
    if np.count_nonzero(seeds) < 100:
        raise ValueError('No confident observed ground seeds')

    # At a crease the shorter derivative may follow the other surface at one
    # endpoint. Require agreement with at least one observed tangent, while both
    # endpoint normals and the connecting edge must still satisfy slope limits.
    # A ledge between horizontal surfaces disagrees with both tangents.
    # A metric edge cap also prevents long occlusion jumps at grazing incidence.
    ground = seeds.copy()
    queue = deque(map(tuple, np.argwhere(seeds)))
    while queue:
        y, x = queue.popleft()
        for yy, xx in ((y-1, x), (y+1, x), (y, x-1), (y, x+1)):
            if not (0 <= yy < h and 0 <= xx < w) or ground[yy, xx] or not walkable[yy, xx]:
                continue
            delta = world[yy, xx] - world[y, x]
            horizontal = np.linalg.norm(delta[:2])
            if (np.linalg.norm(delta) > 2.
                    or abs(delta[2]) > np.tan(np.deg2rad(20)) * horizontal + .035
                    or min(abs(normals[y, x] @ delta), abs(normals[yy, xx] @ delta)) > .035):
                continue
            ground[yy, xx] = True
            queue.append((yy, xx))

    # Unconnected points remain candidates. Compare against the spatially nearest
    # supported sample's tangent plane within 1 m; otherwise use the near plane.
    supported = world[ground]
    supported_normals = normals[ground]
    candidates = world[valid & ~ground]
    keep = []
    for start in range(0, len(candidates), 128):
        points = candidates[start:start+128]
        distances = np.sum((points[:, None, :2] - supported[None, :, :2]) ** 2, axis=2)
        nearest = distances.argmin(axis=1)
        residual = np.sum((points-supported[nearest]) * supported_normals[nearest], axis=1)
        residual = np.where(distances[np.arange(len(points)), nearest] <= 1., residual,
                            points @ normal + offset)
        keep.extend(points[(residual >= .12) & (residual <= 1.8)])
    return dict(grid_world=world.astype(np.float32), valid_mask=valid,
                ground_mask=ground, obstacles=np.asarray(keep, dtype=np.float32).reshape(-1, 3))
