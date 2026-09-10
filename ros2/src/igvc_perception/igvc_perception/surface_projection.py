"""Bounded RGB-ray projection onto visible observed depth, without a plane fallback."""
import cv2
import numpy as np


def project_observed(pixels, k, rotation, origin, world_points,
                     max_pixel_distance=8., eligible_mask=None):
    """Return supported world XYZ for 640x480 RGB queries, preserving query order.

    Rotation maps optical coordinates into world. All observations occlude;
    only visible observations selected by eligible_mask may support output.
    Caller owns temporal freshness. Output uses the query ray at the matched
    optical Z, approximating the local surface over at most the pixel radius.
    """
    try:
        pixels = np.asarray(pixels, dtype=float)
        k = np.asarray(k, dtype=float)
        rotation = np.asarray(rotation, dtype=float)
        origin = np.asarray(origin, dtype=float)
        points = np.asarray(world_points, dtype=float)
        radius = float(max_pixel_distance)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError('Malformed projection inputs') from exc
    if pixels.ndim != 2 or pixels.shape[1] != 2 or not np.isfinite(pixels).all():
        raise ValueError('Pixels must be finite Nx2')
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError('World points must be Nx3')
    if k.shape not in ((9,), (3, 3)) or not np.isfinite(k).all():
        raise ValueError('K must be finite 3x3 or flat nine')
    k = k.reshape(3, 3)
    if (k[0, 0] <= 0 or k[1, 1] <= 0 or abs(k[1, 0]) > 1e-9
            or not np.allclose(k[2], [0, 0, 1], atol=1e-9, rtol=0)
            or not 0 <= k[0, 2] < 640 or not 0 <= k[1, 2] < 480):
        raise ValueError('Invalid RGB pinhole intrinsics')
    if (rotation.shape != (3, 3) or not np.isfinite(rotation).all()
            or not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-6, rtol=0)
            or not np.isclose(np.linalg.det(rotation), 1., atol=1e-6, rtol=0)):
        raise ValueError('Rotation must be proper orthonormal 3x3')
    if origin.shape != (3,) or not np.isfinite(origin).all():
        raise ValueError('Origin must be finite XYZ')
    if not np.isfinite(radius) or not 0 <= radius <= 32:
        raise ValueError('Pixel radius must be finite and within 0..32')
    if eligible_mask is None:
        eligible = np.ones(len(points), dtype=bool)
    else:
        eligible = np.asarray(eligible_mask)
        if eligible.dtype != np.bool_ or eligible.shape != (len(points),):
            raise ValueError('Eligibility must be a boolean per observation')
    empty = np.empty((0, 3), dtype=np.float32)
    if not len(points) or not len(pixels):
        return empty
    finite = np.isfinite(points).all(axis=1)
    points, eligible = points[finite], eligible[finite]
    optical = (points-origin) @ rotation
    valid = np.isfinite(optical).all(axis=1) & (optical[:, 2] >= .2) & (optical[:, 2] <= 10.)
    optical, eligible = optical[valid], eligible[valid]
    if not len(optical):
        return empty
    projected = optical @ k.T
    uv = projected[:, :2] / projected[:, 2, None]
    inside = (uv[:, 0] >= 0) & (uv[:, 0] <= 639) & (uv[:, 1] >= 0) & (uv[:, 1] <= 479)
    uv, optical, eligible = uv[inside], optical[inside], eligible[inside]
    if not len(uv):
        return empty
    bins = np.rint(uv).astype(np.int32)
    ids = bins[:, 1]*640+bins[:, 0]
    # Nearest Z wins per raster bin; ties prefer ineligible to fail conservatively.
    order = np.lexsort((eligible.astype(np.int8), optical[:, 2], ids))
    _, first = np.unique(ids[order], return_index=True)
    chosen = order[first]
    ids, uv, optical, eligible = ids[chosen], uv[chosen], optical[chosen], eligible[chosen]
    raster = np.ones((480, 640), dtype=np.uint8)
    raster.flat[ids] = 0
    _, labels = cv2.distanceTransformWithLabels(raster, cv2.DIST_L2, 5,
                                               labelType=cv2.DIST_LABEL_PIXEL)
    # Label assignment is obtained from the actual raster, not assumed ordering.
    lookup = np.full(int(labels.max())+1, -1, dtype=np.int32)
    lookup[labels.ravel()[ids]] = np.arange(len(ids))
    query_inside = ((pixels[:, 0] >= 0) & (pixels[:, 0] <= 639)
                    & (pixels[:, 1] >= 0) & (pixels[:, 1] <= 479))
    queries = pixels[query_inside]
    if not len(queries):
        return empty
    bins = np.rint(queries).astype(np.int32)
    selected = lookup[labels[bins[:, 1], bins[:, 0]]]
    supported = selected >= 0
    safe = np.maximum(selected, 0)
    # Distance transform chooses a raster neighbor; continuous distance is the
    # final strict bound. A rejected nearest point never falls through occluders.
    supported &= eligible[safe] & (np.linalg.norm(queries-uv[safe], axis=1) <= radius)
    queries, selected = queries[supported], selected[supported]
    if not len(queries):
        return empty
    rays = np.linalg.solve(k, np.column_stack((queries, np.ones(len(queries)))).T).T
    result = (rays*optical[selected, 2, None]) @ rotation.T + origin
    return result.astype(np.float32)
