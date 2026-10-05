"""Admit an asynchronous observed path from the robot's latest measured pose.

Only live observed costs are accepted. This does not execute motion or smooth
the checked trajectory. A stale path is rejected rather than joined by a turn
or shortcut that the forward planner did not check.

A small tracking offset is joined by a forward biarc: two tangent circular arcs
from the measured pose to an unchanged path vertex ahead of the robot's segment
projection. Each connector pose faces along its own motion, curvature is bounded
by the planner's turn radius and the join matches the path yaw, so the joined
sequence is drivable by a forward differential-drive robot. Sideways, backward
or turn-in-place joins are never produced.

Correcting a lateral offset requires yaw, which swings the long rear body. The
gentlest (longest) feasible join is preferred and shorter joins are only used
when the observed sweep blocks it; every connector sweep is checked.
"""
import math
from sensor_route_policy import _rectangle_clear
from swept_footprint import arc_sweep_box

# Relative floating-point allowance for comparing computed connector curvature with
# 1/min_turn_radius. About 0.65 nm of radius at 0.65 m; not a physical relaxation.
CURVATURE_RELATIVE_ALLOWANCE = 1e-9


def _wrap(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


def _arc_pose(x, y, yaw, curvature, distance):
    half = curvature*distance/2
    chord = distance if abs(half) < 1e-9 else math.sin(half)/half*distance
    return x+chord*math.cos(yaw+half), y+chord*math.sin(yaw+half), yaw+2*half


def _arc(start, yaw, end):
    """Forward constant-curvature arc from a pose through a point, or None."""
    wx, wy = end[0]-start[0], end[1]-start[1]
    chord = math.hypot(wx, wy)
    along, across = math.cos(yaw)*wx+math.sin(yaw)*wy, math.cos(yaw)*wy-math.sin(yaw)*wx
    if chord < 1e-9 or along <= 0:
        return None
    half = math.atan2(across, along)
    length = chord if abs(half) < 1e-9 else chord*half/math.sin(half)
    return 2*math.sin(half)/chord, length


def _biarc(pose, end, end_yaw):
    """Equal-tangent-length biarc; returns [(curvature, length), ...] or None."""
    t0 = math.cos(pose[2]), math.sin(pose[2])
    t1 = math.cos(end_yaw), math.sin(end_yaw)
    vx, vy = end[0]-pose[0], end[1]-pose[1]
    vt = vx*(t0[0]+t1[0])+vy*(t0[1]+t1[1])
    a = 2*(1-(t0[0]*t1[0]+t0[1]*t1[1]))
    root = math.sqrt(max(vt*vt+a*(vx*vx+vy*vy), 0.))
    # Stable positive root of a*d*d + 2*vt*d - |v|^2 = 0; d > 0 is forward.
    if vt+root <= 1e-12:
        return None
    d = (vx*vx+vy*vy)/(vt+root)
    middle = ((pose[0]+end[0]+d*(t0[0]-t1[0]))/2, (pose[1]+end[1]+d*(t0[1]-t1[1]))/2)
    first = _arc(pose[:2], pose[2], middle)
    if first is None:
        return None
    middle_yaw = pose[2]+first[0]*first[1]
    second = _arc(middle, middle_yaw, end)
    if second is None or abs(_wrap(middle_yaw+second[0]*second[1]-end_yaw)) > 1e-6:
        return None
    return [first, second]


def _connector(pose, arcs):
    """Exact arc samples from the pose, excluding the join vertex itself."""
    points, yaws = [tuple(pose[:2])], [pose[2]]
    x, y, yaw = pose
    for curvature, length in arcs:
        steps = max(1, math.ceil(length/.01))
        for i in range(1, steps+1):
            points.append(_arc_pose(x, y, yaw, curvature, length*i/steps)[:2])
            yaws.append(yaw+curvature*length*i/steps)
        x, y, yaw = (*points[-1], yaws[-1])
    # The final sample coincides with the join; keep the checked vertex instead.
    return points[:-1], yaws[:-1]


def prepare_controller_plan(plan, pose, origin, resolution, width, height, costs,
                            footprint, *, max_cross_track=.10, max_heading_error=.15,
                            min_turn_radius=.65, max_connector_length=1.5,
                            connector_spacing=.1):
    points, yaws = plan['path'], plan['path_yaws']
    diagnostic = {'accepted': False}
    if (len(points) != len(yaws) or len(points) < 2 or len(pose) != 3
            or not all(math.isfinite(v) for v in pose)):
        diagnostic['reason'] = 'invalid_pose_or_path'
        return None, diagnostic
    # Continuous projection onto path segments, not the nearest vertex, so a
    # robot between vertices is never asked to return to one behind it.
    best = None
    for k in range(len(points)-1):
        (ax, ay), (bx, by) = points[k], points[k+1]
        sx, sy = bx-ax, by-ay
        squared = sx*sx+sy*sy
        u = 0. if squared == 0 else min(1., max(0., ((pose[0]-ax)*sx+(pose[1]-ay)*sy)/squared))
        distance = math.dist(pose[:2], (ax+u*sx, ay+u*sy))
        if best is None or distance < best[0]:
            best = (distance, k, u)
    distance, index, fraction = best
    reference = yaws[index]+_wrap(yaws[index+1]-yaws[index])*fraction
    turn = _wrap(reference-pose[2])
    diagnostic.update(nearest_index=index, cross_track_m=distance, heading_error_rad=turn)
    if distance > max_cross_track or abs(turn) > max_heading_error:
        diagnostic['reason'] = 'start_pose_departed_checked_path'
        return None, diagnostic
    if math.dist(pose[:2], points[-1]) < .35:
        diagnostic['reason'] = 'checked_path_already_consumed'
        return None, diagnostic
    # Feasible joins: vertices strictly ahead of the projection whose biarc is
    # forward and within the planner's curvature limit. The suffix is unchanged.
    limit = 1/min_turn_radius
    # Comparison-only arithmetic allowance: a checked path exactly at the turn
    # limit reproduces it to within rounding (3.9968e-15..7.0448e-11 relative on
    # T-0009 decision 212); genuine excess began at 1.13e-2. The configured
    # radius, connector geometry and every sweep are unchanged.
    admissible = limit*(1+CURVATURE_RELATIVE_ALLOWANCE)
    travelled = math.dist(points[index], points[index+1])*(1-fraction)
    feasible = []
    for j in range(index+1, len(points)):
        if j > index+1:
            travelled += math.dist(points[j-1], points[j])
        if travelled > max_connector_length:
            break
        if travelled <= 1e-9:
            continue
        arcs = _biarc(pose, points[j], yaws[j])
        if arcs is not None and all(abs(k) <= admissible for k, _ in arcs):
            feasible.append((travelled, j, arcs))
    if not feasible:
        diagnostic['reason'] = 'no_forward_connector_within_turn_radius'
        return None, diagnostic
    ordered = []
    for candidate in reversed(feasible):
        if not ordered or ordered[-1][0]-candidate[0] >= connector_spacing:
            ordered.append(candidate)
    if ordered[-1] is not feasible[0]:
        ordered.append(feasible[0])
    hazards = [0]*height
    for cell,value in enumerate(costs):
        if value < 0 or value >= 100:
            hazards[cell//width] |= 1 << (cell%width)

    def blocked(samples, start, previous):
        for i, ((x,y),yaw) in enumerate(samples, start):
            ix,iy=math.floor((x-origin[0])/resolution),math.floor((y-origin[1])/resolution)
            # Every interval lies on one constant-curvature arc: a biarc piece
            # or a checked planner primitive, matching arc_sweep_box.
            sx,sy,angle,bounds = (x,y,yaw,footprint) if previous is None else arc_sweep_box(
                previous,(x,y,yaw),footprint)
            if (not 0 <= ix < width or not 0 <= iy < height
                    or not 0 <= costs[iy*width+ix] < 99
                    or not _rectangle_clear(sx,sy,angle,bounds,costs,width,height,resolution,origin,hazards)):
                return i
            previous = (x,y,yaw)
        return None

    rejected = blocked([(pose[:2], pose[2])], 0, None)
    chosen = None
    for _, join, arcs in (ordered if rejected is None else ()):
        connector_points, connector_yaws = _connector(pose, arcs)
        rejected = blocked(list(zip(connector_points, connector_yaws))[1:]
                           +[(points[join], yaws[join])], 1, tuple(pose))
        if rejected is None:
            chosen = join, arcs, connector_points, connector_yaws
            break
    if chosen is not None:
        join, arcs, joined_points, joined_yaws = chosen
        # A shorter join's suffix contains this one, so a blocked suffix
        # cannot be avoided by trying another connector.
        rejected = blocked(list(zip(points[join+1:], yaws[join+1:])), len(joined_points)+1,
                           (*points[join], yaws[join]))
    if rejected is not None:
        diagnostic.update(reason='latest_observed_sweep_blocked', rejected_sample=rejected,
                          connector_blocked=chosen is None and rejected > 0)
        return None, diagnostic
    connector_samples = len(joined_points)
    joined_points = joined_points+list(points[join:])
    joined_yaws = joined_yaws+list(yaws[join:])
    diagnostic.update(accepted=True,reason='latest_pose_and_observed_sweep_clear',
                      join_index=join, connector_samples=connector_samples,
                      connector_distance_m=sum(length for _, length in arcs),
                      connector_curvatures=[k for k, _ in arcs],
                      connector_candidates=len(ordered),
                      sweep_model='forward_biarc_and_directed_interval_enclosures')
    return {**plan,'path':joined_points,'path_yaws':joined_yaws},diagnostic
