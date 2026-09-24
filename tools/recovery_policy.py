"""Observed-space straight backup proposals; never executes motion or reads maps."""
import math
import time

from sensor_route_policy import _rectangle_clear, select_local_goal


def select_backup_recovery(origin_xy, resolution, width, height, costs,
                           robot_xy, robot_yaw, destination_xy, *, goal_footprint,
                           distances=(.6, .9, 1.2, 1.5, 1.8), max_backup_distance=1.8,
                           max_search_seconds=5., max_expansions=50000,
                           forward_planner=select_local_goal, forward_options=None):
    """Return the shortest checked backup with useful forward continuation.

    ``forward_planner`` takes select_local_goal's arguments; a partial applying
    observed_navigation's lane_points/heading_hint preserves lane-entry policy.
    Existing caller footprint padding is retained, with additional swept-motion
    padding. Unknown, lethal and inscribed centre cells remain blocked. The
    continuation must advance >=0.5 m beyond the original trap toward its actual
    guidance target, have >=1 m useful displacement/path and >=1 m checked reserve.

    Search time/expansions are shared across candidates. Time bounding is
    cooperative: callbacks must honor max_search_seconds, and the caller retains
    its external watchdog for input/clearance precomputation and execution.
    """
    started = time.monotonic()
    try:
        if (len(origin_xy) != 2 or len(robot_xy) != 2 or len(destination_xy) != 2
                or len(goal_footprint) != 4
                or not all(math.isfinite(v) for v in (*origin_xy, *robot_xy,
                    robot_yaw, *destination_xy, *goal_footprint, resolution,
                    max_backup_distance, max_search_seconds, *distances))
                or resolution <= 0 or not isinstance(width, int) or not isinstance(height, int)
                or width <= 0 or height <= 0 or width*height > 262144
                or len(costs) != width*height
                or any(not math.isfinite(v) or v < -1 or v > 100 for v in costs)
                or not 0 < max_backup_distance <= 2. or max_search_seconds <= 0
                or not isinstance(max_expansions, int) or not 1 <= max_expansions <= 100000
                or goal_footprint[0] >= goal_footprint[1]
                or goal_footprint[2] >= goal_footprint[3]
                or any(d <= 0 or d > 2. for d in distances)):
            return None
        candidates = sorted(set(d for d in distances if d <= max_backup_distance))
        options = dict(forward_options or {})
    except (TypeError, ValueError, OverflowError):
        return None
    if not candidates:
        return None

    # Sample spacing bounds straight swept motion; unlike a forward arc there
    # is no rotational contribution. A half-interval expansion protects every
    # point between adjacent samples, including the initial pose.
    spacing = min(.05, resolution/2)
    b = goal_footprint
    swept = (b[0]-spacing/2, b[1]+spacing/2, b[2]-spacing/2, b[3]+spacing/2)
    hx, hy = math.cos(robot_yaw), math.sin(robot_yaw)

    def pose(distance):
        return robot_xy[0]-distance*hx, robot_xy[1]-distance*hy

    def clear(distance):
        x, y = pose(distance)
        ix, iy = math.floor((x-origin_xy[0])/resolution), math.floor((y-origin_xy[1])/resolution)
        return (0 <= ix < width and 0 <= iy < height
                and 0 <= costs[iy*width+ix] < 99
                and _rectangle_clear(x, y, robot_yaw, swept, costs,
                                     width, height, resolution, origin_xy))

    if not clear(0.):
        return None
    checked_distance = 0.
    charged_expansions = 0
    attempts = []
    for i, distance in enumerate(candidates):
        remaining = max_search_seconds-(time.monotonic()-started)
        if remaining <= 0 or charged_expansions >= max_expansions:
            break
        intervals = math.ceil((distance-checked_distance)/spacing)
        for j in range(1, intervals+1):
            if not clear(checked_distance+(distance-checked_distance)*j/intervals):
                # Farther candidates must cross this same blocked rear sweep.
                return None
        checked_distance = distance
        remaining = max_search_seconds-(time.monotonic()-started)
        if remaining <= 0:
            break
        slots = len(candidates)-i
        expansion_allowance = max(1, (max_expansions-charged_expansions)//slots)
        # Reserve part of each time slice for the forward planner's masks/input
        # checks, which precede its own timed expansion loop.
        allowance = remaining/slots*.75
        settings = dict(options)
        settings.update(forward_only=True, goal_footprint=goal_footprint,
                        min_goal_distance=max(1., options.get('min_goal_distance', 0.)),
                        continuation_reserve=max(1., options.get('continuation_reserve', 0.)),
                        max_search_seconds=allowance, max_expansions=expansion_allowance)
        plan = forward_planner(origin_xy, resolution, width, height, costs,
                               pose(distance), robot_yaw, destination_xy, **settings)
        diagnostics = plan.get('diagnostics', {}) if plan is not None else {}
        used = diagnostics.get('expanded_cells', expansion_allowance)
        charged_expansions += min(expansion_allowance, max(0, used))
        attempts.append({'distance_m': distance, 'expansion_allowance': expansion_allowance,
                         'charged_expansions': min(expansion_allowance, max(0, used)),
                         'proposal_found': plan is not None})
        if plan is None:
            continue
        target = diagnostics.get('guidance_target', destination_xy)
        endpoint = diagnostics.get('endpoint', plan['local_goal'])
        trap_progress = math.dist(robot_xy, target)-math.dist(endpoint, target)
        if (diagnostics.get('local_path_length', 0.) < 1.
                or diagnostics.get('checked_continuation_length', 0.) < 1.
                or math.dist(pose(distance), plan['local_goal']) < 1.
                or math.dist(robot_xy, plan['local_goal']) < .4
                or trap_progress < .5):
            continue
        return {'distance_m': distance, 'backup_pose': pose(distance),
                'forward_plan': plan, 'diagnostics': {
                    'rear_sweep_checked_m': distance, 'rear_sample_spacing_m': spacing,
                    'original_trap_progress_m': trap_progress,
                    'elapsed_seconds': time.monotonic()-started,
                    'charged_expansions': charged_expansions, 'attempts': attempts,
                    'unknown_is_blocked': True, 'straight_backup_only': True}}
    return None
