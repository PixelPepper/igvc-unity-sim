"""Paired observed-paint corridor proposals; no files, maps or drive commands.

A proposal is not a collision-free vehicle path. The caller must validate it
against fresh observed costs with the complete footprint before execution.
"""
import math
import numpy as np


def _segments(points):
    """Extract at most eight spatially supported straight paint segments."""
    rng = np.random.default_rng(0)
    remaining = points.copy()
    segments = []
    for _ in range(8):
        if len(remaining) < 10:
            break
        best = None
        for _ in range(160):
            a, b = remaining[rng.choice(len(remaining), 2, replace=False)]
            delta = b-a
            length = np.linalg.norm(delta)
            if length < 2.:
                continue
            direction = delta/length
            normal = np.array([-direction[1], direction[0]])
            ids = np.flatnonzero(np.abs((remaining-a) @ normal) <= .14)
            if len(ids) < 10:
                continue
            longitudinal = (remaining[ids]-a) @ direction
            order = np.argsort(longitudinal, kind='stable')
            groups = np.split(order, np.flatnonzero(np.diff(longitudinal[order]) > 1.25)+1)
            for group in groups:
                if len(group) < 10:
                    continue
                selected = ids[group]
                support = remaining[selected]
                center = support.mean(axis=0)
                _, _, axes = np.linalg.svd(support-center, full_matrices=False)
                axis = axes[0]
                t = (support-center) @ axis
                lo, hi = np.quantile(t, [.02, .98])
                span = hi-lo
                if span < 3.:
                    continue
                bins = len(np.unique(np.floor((t-lo)/.5).astype(int)))
                coverage = min(1., bins/(math.ceil(span/.5)+1))
                if bins < 6 or coverage < .7:
                    continue
                residual = np.abs((support-center) @ np.array([-axis[1], axis[0]]))
                if float(np.quantile(residual, .95)) > .16:
                    continue
                score = (len(selected), span)
                if best is None or score > best[0]:
                    best = (score, selected, dict(center=center, axis=axis,
                            a=center+lo*axis, b=center+hi*axis,
                            span=float(span), count=len(selected), coverage=coverage))
        if best is None:
            break
        segments.append(best[2])
        remaining = np.delete(remaining, best[1], axis=0)
    return segments


def _crosses(a, b, segment):
    """Reject direct entry chords crossing the interior of observed paint."""
    c, d = segment['a'], segment['b']
    ab, cd = b-a, d-c
    cross = lambda u, v: float(u[0]*v[1]-u[1]*v[0])
    denominator = cross(ab, cd)
    if abs(denominator) < 1e-9:
        return False
    t, u = cross(c-a, cd)/denominator, cross(c-a, ab)/denominator
    return 0. < t <= 1. and 0. <= u <= 1.


def propose_lane_corridor(lane_points, robot_xy, robot_yaw, destination_xy, *,
                          min_width=2., max_width=8., horizon=14., lookahead=3.):
    """Return entry/center/direction/yaw/confidence/diagnostics, or None.

    Outside a pair, propose its forward visible mouth, 0.6 m before the paired
    paint overlap, rather than a later midpoint across a painted side. Inside
    a pair, propose a center lookahead metres ahead, clamped to observed overlap.
    Confidence describes geometric support,
    not semantic certainty that the paint belongs to the competition corridor.
    """
    try:
        points = np.asarray(lane_points, dtype=float)
        robot, destination = np.asarray(robot_xy, dtype=float), np.asarray(destination_xy, dtype=float)
        scalars = np.asarray([robot_yaw, min_width, max_width, horizon, lookahead], dtype=float)
        if (points.ndim != 2 or points.shape[1] != 2 or len(points) < 20
                or robot.shape != (2,) or destination.shape != (2,)
                or not np.isfinite(points).all() or not np.isfinite(robot).all()
                or not np.isfinite(destination).all() or not np.isfinite(scalars).all()
                or not 0 < min_width <= max_width <= 12 or not 1 <= horizon <= 30
                or not 0 < lookahead <= horizon):
            return None
    except (ValueError, TypeError, OverflowError):
        return None
    heading = np.array([math.cos(robot_yaw), math.sin(robot_yaw)])
    delta = points-robot
    # Spatial filtering and raster deduplication bound dense repeated history.
    points = points[(np.linalg.norm(delta, axis=1) <= horizon+max_width)
                    & (delta @ heading >= -2.)]
    if len(points) < 20:
        return None
    bins = np.floor(points/.1).astype(np.int64)
    _, indices = np.unique(bins, axis=0, return_index=True)
    points = points[np.sort(indices)]
    if len(points) > 4000:
        points = points[np.linspace(0, len(points)-1, 4000, dtype=int)]
    segments = _segments(points)
    proposals = []
    for i, first in enumerate(segments):
        for j in range(i+1, len(segments)):
            second = segments[j]
            alignment = float(first['axis'] @ second['axis'])
            if abs(alignment) < math.cos(math.radians(8.)):
                continue
            direction = first['axis'] + second['axis'] * (1 if alignment >= 0 else -1)
            direction /= np.linalg.norm(direction)
            if direction @ heading < 0:
                direction = -direction
            if direction @ heading < .25:
                continue
            normal = np.array([-direction[1], direction[0]])

            def bounds(segment):
                return sorted((float(segment['a'] @ direction), float(segment['b'] @ direction)))

            def lateral(segment, t):
                return float(segment['center'] @ normal +
                    (t-segment['center'] @ direction)*(segment['axis'] @ normal)/(segment['axis'] @ direction))

            aa, bb = bounds(first), bounds(second)
            lo, hi = max(aa[0], bb[0]), min(aa[1], bb[1])
            overlap = hi-lo
            if overlap < 3.:
                continue
            widths = [abs(lateral(first, t)-lateral(second, t)) for t in (lo, (lo+hi)/2, hi)]
            width = widths[1]
            if min(widths) < min_width or max(widths) > max_width or max(widths)-min(widths) > max(.35, width*.15):
                continue
            # Do not explain away a third supported parallel barrier by pairing
            # the more distant outside lines around it.
            obstructed = False
            for k, other in enumerate(segments):
                if k in (i, j) or abs(other['axis'] @ direction) < math.cos(math.radians(8.)):
                    continue
                cc = bounds(other)
                shared_lo, shared_hi = max(lo, cc[0]), min(hi, cc[1])
                if shared_hi-shared_lo < 2.:
                    continue
                t = (shared_lo+shared_hi)/2
                left, right = sorted((lateral(first, t), lateral(second, t)))
                if left+.3 < lateral(other, t) < right-.3:
                    obstructed = True
                    break
            if obstructed:
                continue
            robot_t = float(robot @ direction)
            reference_t = min(hi, max(lo, robot_t))
            left, right = sorted((lateral(first, reference_t), lateral(second, reference_t)))
            inside = left+.25 <= robot @ normal <= right-.25
            t = min(hi, max(lo, robot_t+lookahead)) if inside else lo-.6
            center = direction*t+normal*(lateral(first, t)+lateral(second, t))/2
            displacement = center-robot
            distance = float(np.linalg.norm(displacement))
            if distance > horizon or displacement @ heading <= .25:
                continue
            # A mildly skewed GPS destination must not pull entry outside the
            # observed pair, but a corridor pointing away from it is rejected.
            gps_delta = destination-center
            if gps_delta @ direction < -.5:
                continue
            if any(_crosses(robot, center, segment) for segment in segments):
                continue
            confidence = min(1., overlap/6.)*min(first['coverage'], second['coverage'])*abs(alignment)
            gps_alignment = float(gps_delta @ direction/max(np.linalg.norm(gps_delta), 1e-9))
            score = distance + .5*(1.-gps_alignment) - 1.5*confidence
            proposals.append((score, dict(entry=center.tolist(), center=center.tolist(),
                direction=direction.tolist(), yaw=math.atan2(direction[1], direction[0]),
                confidence=float(confidence), diagnostics=dict(width_m=width,
                    overlap_m=overlap, support_counts=[first['count'], second['count']],
                    segments=[[first['a'].tolist(), first['b'].tolist()],
                              [second['a'].tolist(), second['b'].tolist()]],
                    extracted_segments=len(segments), entry_mode='inside' if inside else 'visible_mouth',
                    gps_alignment=gps_alignment, collision_checked=False))))
    return min(proposals, key=lambda item:item[0])[1] if proposals else None
