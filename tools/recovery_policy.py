"""Observed-space straight backup proposals; never executes motion or reads maps."""
import math
import time

from sensor_route_policy import _rectangle_clear, select_local_goal


def _valid_regions(regions):
    """Trap discs as ((x, y), radius); raise ValueError on malformed input."""
    result = []
    for region in regions or ():
        (x, y), radius = region['center'], region['radius']
        if not all(math.isfinite(v) for v in (x, y, radius)) or not 0 < radius <= 3.:
            raise ValueError('Invalid trap region')
        result.append({'center': (float(x), float(y)), 'radius': float(radius)})
    return result


def _in_regions(xy, regions):
    return any(math.dist(xy, r['center']) <= r['radius'] for r in regions)


def _accept_continuation(plan, trap_xy, start_xy, destination_xy, resolution, regions=()):
    """Shared continuation rule; returns (trap_progress, terminal, tolerance) or None.

    The continuation must advance >=0.5 m beyond the original trap toward its
    guidance target with >=1 m path/reserve (terminal arrival excepted), and
    must not end inside a remembered trap region.
    """
    diagnostics = plan.get('diagnostics', {})
    target = diagnostics.get('guidance_target', destination_xy)
    endpoint = diagnostics.get('endpoint', plan['local_goal'])
    trap_progress = math.dist(trap_xy, target)-math.dist(endpoint[:2], target)
    tolerance = max(resolution, .25)
    path = plan.get('path', [])
    terminal = bool(path) and all(math.dist(point[:2], target) <= tolerance
        for point in (endpoint, plan['local_goal'], path[-1]))
    if (diagnostics.get('local_path_length', 0.) < 1.
            or (not terminal and diagnostics.get('checked_continuation_length', 0.) < 1.)
            or math.dist(start_xy, plan['local_goal']) < 1.
            or math.dist(trap_xy, plan['local_goal']) < .4
            or math.dist(trap_xy, target) < .4
            or trap_progress < .5):
        return None
    if regions and (_in_regions(plan['local_goal'][:2], regions)
                    or _in_regions(endpoint[:2], regions)
                    or _in_regions(target[:2], regions)):
        return None
    return trap_progress, terminal, tolerance


def select_backup_recovery(origin_xy, resolution, width, height, costs,
                           robot_xy, robot_yaw, destination_xy, *, goal_footprint,
                           distances=(.6, .9, 1.2, 1.5, 1.8), max_backup_distance=1.8,
                           max_search_seconds=5., max_expansions=50000,
                           forward_planner=select_local_goal, forward_options=None,
                           continuation_costs=None, trap_regions=()):
    """Return the shortest checked backup with useful forward continuation.

    Defaults reproduce the original (legacy) behaviour exactly. Optional
    ``continuation_costs`` (a trap-masked COPY of ``costs``) is given only to
    the forward continuation; the rear sweep is always checked on ``costs``.
    ``trap_regions`` additionally rejects continuations ending inside them.

    ``forward_planner`` takes select_local_goal's arguments; a partial applying
    observed_navigation's lane_points/heading_hint preserves lane-entry policy.
    Existing caller footprint padding is retained. Fixed-yaw straight sweeps
    extend only the body's longitudinal bounds, exactly covering the translation
    without extra side padding. Unknown, lethal and inscribed centre cells remain blocked. The
    continuation must advance >=0.5 m beyond the original trap toward its actual
    guidance target and have >=1 m useful displacement/path. Partial paths need
    >=1 m checked reserve; a returned path reaching its guidance target within
    max(resolution, 0.25 m) may finish there without a reserve beyond the target.

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
        continuation_grid = costs if continuation_costs is None else continuation_costs
        if len(continuation_grid) != width*height:
            return None
        trap_regions = _valid_regions(trap_regions)
    except (TypeError, ValueError, OverflowError):
        return None
    if not candidates:
        return None

    # At fixed yaw, the continuous union over a rearward translation is exactly
    # the same oriented rectangle extended along negative body X. Keep spacing
    # for centre-cell checks; body clearance covers whole intervals, not samples.
    spacing = min(.05, resolution/2)
    b = goal_footprint
    hx, hy = math.cos(robot_yaw), math.sin(robot_yaw)

    def pose(distance):
        return robot_xy[0]-distance*hx, robot_xy[1]-distance*hy

    def clear(distance, previous=None):
        x, y = pose(distance)
        ix, iy = math.floor((x-origin_xy[0])/resolution), math.floor((y-origin_xy[1])/resolution)
        # Anchor at the later (rearward) pose: the earlier body is ahead by
        # distance-previous. Their union leaves both lateral edges unchanged.
        swept = b if previous is None else (b[0], b[1]+distance-previous, b[2], b[3])
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
        previous = checked_distance
        for j in range(1, intervals+1):
            current = checked_distance+(distance-checked_distance)*j/intervals
            if not clear(current, previous):
                # Farther candidates must cross this same blocked rear sweep.
                return None
            previous = current
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
        plan = forward_planner(origin_xy, resolution, width, height, continuation_grid,
                               pose(distance), robot_yaw, destination_xy, **settings)
        diagnostics = plan.get('diagnostics', {}) if plan is not None else {}
        used = diagnostics.get('expanded_cells', expansion_allowance)
        charged_expansions += min(expansion_allowance, max(0, used))
        attempts.append({'distance_m': distance, 'expansion_allowance': expansion_allowance,
                         'charged_expansions': min(expansion_allowance, max(0, used)),
                         'proposal_found': plan is not None})
        if plan is None:
            continue
        accepted = _accept_continuation(plan, robot_xy, pose(distance), destination_xy,
                                        resolution, trap_regions)
        if accepted is None:
            continue
        trap_progress, terminal, tolerance = accepted
        return {'distance_m': distance, 'backup_pose': pose(distance),
                'forward_plan': plan, 'diagnostics': {
                    'rear_sweep_checked_m': distance, 'rear_sample_spacing_m': spacing,
                    'rear_body_sweep': 'exact_fixed_yaw_rectangle_union',
                    'original_trap_progress_m': trap_progress,
                    'terminal_escape': terminal,
                    'terminal_tolerance_m': tolerance,
                    'elapsed_seconds': time.monotonic()-started,
                    'charged_expansions': charged_expansions, 'attempts': attempts,
                    'unknown_is_blocked': True, 'straight_backup_only': True}}
    return None


def _distance_to_polyline(point, polyline):
    if len(polyline) == 1:
        return math.dist(point, polyline[0])
    best = math.inf
    for (ax, ay), (bx, by) in zip(polyline, polyline[1:]):
        dx, dy = bx-ax, by-ay
        length2 = dx*dx+dy*dy
        t = 0. if length2 == 0 else max(0., min(1., ((point[0]-ax)*dx+(point[1]-ay)*dy)/length2))
        best = min(best, math.hypot(point[0]-ax-t*dx, point[1]-ay-t*dy))
    return best


def select_retrace_recovery(origin_xy, resolution, width, height, costs,
                            robot_xy, robot_yaw, destination_xy, *, goal_footprint,
                            driven_path, continuation_costs=None, trap_regions=(),
                            distances=(2.2, 2.8, 3.4, 4.0), max_retrace_distance=4.,
                            corridor_tolerance=1., max_search_seconds=8., max_expansions=50000,
                            forward_planner=select_local_goal, forward_options=None):
    """Longer straight BackUp that retraces the robot's own recently driven corridor.

    Only the existing Nav2 BackUp primitive is proposed (fixed yaw, same
    0.1 m/s), so execution is unchanged; only its length grows beyond the
    1.8 m straight search, up to max_retrace_distance (<=4 m) and never
    beyond the driven path length. Every rear axle sample must lie within
    corridor_tolerance of driven_path (odometry history, oldest first, newest
    = current pose), so the body backs through space it occupied moments ago.
    The 1.0 m default is about one body width (padded half-width 0.52 m): the
    backing body always overlaps the driven swath; the remainder is covered
    only by the grid check below.
    The whole-body sweep is ALSO checked against the CURRENT observed grid
    with the straight-backup rules (unknown/lethal body cells and inscribed
    centre cells block). The forward continuation is searched on
    continuation_costs (trap-masked copy) and must satisfy the same acceptance
    rule as the straight backup and avoid trap_regions.
    """
    started = time.monotonic()
    try:
        path = [(float(p[0]), float(p[1])) for p in driven_path]
        if (len(origin_xy) != 2 or len(robot_xy) != 2 or len(destination_xy) != 2
                or len(goal_footprint) != 4 or len(path) < 2
                or not all(math.isfinite(v) for v in (*origin_xy, *robot_xy, robot_yaw,
                    *destination_xy, *goal_footprint, resolution, max_retrace_distance,
                    corridor_tolerance, max_search_seconds, *distances))
                or not all(math.isfinite(v) for p in path for v in p)
                or resolution <= 0 or not isinstance(width, int) or not isinstance(height, int)
                or width <= 0 or height <= 0 or width*height > 262144
                or len(costs) != width*height
                or any(not math.isfinite(v) or v < -1 or v > 100 for v in costs)
                or not 0 < max_retrace_distance <= 4. or not 0 < corridor_tolerance <= 1.
                or max_search_seconds <= 0
                or not isinstance(max_expansions, int) or not 1 <= max_expansions <= 100000
                or goal_footprint[0] >= goal_footprint[1]
                or goal_footprint[2] >= goal_footprint[3]
                or any(d <= 0 or d > 4. for d in distances)):
            return None
        continuation_grid = costs if continuation_costs is None else continuation_costs
        if len(continuation_grid) != width*height:
            return None
        regions = _valid_regions(trap_regions)
        options = dict(forward_options or {})
    except (TypeError, ValueError, OverflowError, KeyError):
        return None
    driven = sum(math.dist(a, b) for a, b in zip(path, path[1:]))
    # The newest history point must be the current axle position.
    if math.dist(path[-1], robot_xy) > .1:
        return None
    candidates = sorted(set(d for d in distances if d <= min(max_retrace_distance, driven)))
    if not candidates:
        return None
    spacing = min(.05, resolution/2)
    b = goal_footprint
    hx, hy = math.cos(robot_yaw), math.sin(robot_yaw)

    def pose(distance):
        return robot_xy[0]-distance*hx, robot_xy[1]-distance*hy

    def clear(distance, previous=None):
        x, y = pose(distance)
        ix, iy = math.floor((x-origin_xy[0])/resolution), math.floor((y-origin_xy[1])/resolution)
        swept = b if previous is None else (b[0], b[1]+distance-previous, b[2], b[3])
        return (0 <= ix < width and 0 <= iy < height
                and 0 <= costs[iy*width+ix] < 99
                and _distance_to_polyline((x, y), path) <= corridor_tolerance
                and _rectangle_clear(x, y, robot_yaw, swept, costs,
                                     width, height, resolution, origin_xy))

    if not clear(0.):
        return None
    checked_distance = 0.
    charged_expansions = 0
    attempts = []
    max_deviation = 0.
    for i, distance in enumerate(candidates):
        remaining = max_search_seconds-(time.monotonic()-started)
        if remaining <= 0 or charged_expansions >= max_expansions:
            break
        intervals = math.ceil((distance-checked_distance)/spacing)
        previous = checked_distance
        for j in range(1, intervals+1):
            current = checked_distance+(distance-checked_distance)*j/intervals
            if not clear(current, previous):
                # Farther candidates must cross this same blocked/uncontained sweep.
                return None
            max_deviation = max(max_deviation, _distance_to_polyline(pose(current), path))
            previous = current
        checked_distance = distance
        remaining = max_search_seconds-(time.monotonic()-started)
        if remaining <= 0:
            break
        slots = len(candidates)-i
        expansion_allowance = max(1, (max_expansions-charged_expansions)//slots)
        allowance = remaining/slots*.75
        settings = dict(options)
        settings.update(forward_only=True, goal_footprint=goal_footprint,
                        min_goal_distance=max(1., options.get('min_goal_distance', 0.)),
                        continuation_reserve=max(1., options.get('continuation_reserve', 0.)),
                        max_search_seconds=allowance, max_expansions=expansion_allowance)
        plan = forward_planner(origin_xy, resolution, width, height, continuation_grid,
                               pose(distance), robot_yaw, destination_xy, **settings)
        diagnostics = plan.get('diagnostics', {}) if plan is not None else {}
        used = min(expansion_allowance, max(0, diagnostics.get('expanded_cells', expansion_allowance)))
        charged_expansions += used
        attempts.append({'distance_m': distance, 'expansion_allowance': expansion_allowance,
                         'charged_expansions': used, 'proposal_found': plan is not None})
        if plan is None:
            continue
        accepted = _accept_continuation(plan, robot_xy, pose(distance), destination_xy,
                                        resolution, regions)
        if accepted is None:
            continue
        trap_progress, terminal, tolerance = accepted
        return {'distance_m': distance, 'backup_pose': pose(distance),
                'forward_plan': plan, 'escape_type': 'retrace_backup', 'diagnostics': {
                    'rear_sweep_checked_m': distance, 'rear_sample_spacing_m': spacing,
                    'rear_body_sweep': 'exact_fixed_yaw_rectangle_union',
                    'driven_path_length_m': driven,
                    'corridor_tolerance_m': corridor_tolerance,
                    'max_corridor_deviation_m': max_deviation,
                    'original_trap_progress_m': trap_progress,
                    'terminal_escape': terminal, 'terminal_tolerance_m': tolerance,
                    'elapsed_seconds': time.monotonic()-started,
                    'charged_expansions': charged_expansions, 'attempts': attempts,
                    'unknown_is_blocked': True, 'straight_backup_only': True}}
    return None


def select_trap_escape(origin_xy, resolution, width, height, costs,
                       robot_xy, robot_yaw, destination_xy, *, goal_footprint,
                       driven_path, trap_regions, forward_planner=select_local_goal,
                       forward_options=None, straight_seconds=5., retrace_seconds=8.):
    """Retrace-mode recovery: straight search first, then the corridor retrace.

    Each continuation is planned on a trap-masked COPY of the observed grid in
    which only the cells under that candidate's own starting body stay
    unmasked: a short backup whose body still touches the region can turn away,
    but any motion into the region is blocked. Rear sweeps always use the
    unmodified grid. Returns the escape (with 'escape_type') or None. The
    straight search keeps the legacy 5 s budget; the retrace has its own,
    because each long continuation search needs ~1-1.5 s of planner time.
    """
    from trap_memory import mask_costs
    try:
        regions = _valid_regions(trap_regions)
        plain = [dict(center=r['center'], radius=r['radius']) for r in regions]
    except (TypeError, ValueError, OverflowError, KeyError, IndexError):
        return None
    masked_cells = []

    def masked_planner(origin, res, w, h, grid, start_xy, start_yaw, destination, **settings):
        masked, changed = mask_costs(grid, w, h, res, origin, plain,
                                     keep_clear=(start_xy[0], start_xy[1], start_yaw, goal_footprint))
        masked_cells.append(changed)
        return forward_planner(origin, res, w, h, masked, start_xy, start_yaw, destination, **settings)

    common = dict(goal_footprint=goal_footprint,
                  forward_planner=masked_planner if plain else forward_planner,
                  forward_options=forward_options, trap_regions=regions)
    escape = select_backup_recovery(origin_xy, resolution, width, height, costs,
                                    robot_xy, robot_yaw, destination_xy,
                                    max_search_seconds=straight_seconds, **common)
    if escape is not None:
        escape['escape_type'] = 'straight_backup'
    else:
        escape = select_retrace_recovery(origin_xy, resolution, width, height, costs,
                                         robot_xy, robot_yaw, destination_xy,
                                         driven_path=driven_path,
                                         max_search_seconds=retrace_seconds, **common)
    if escape is not None:
        escape['diagnostics'].update(escape_type=escape['escape_type'],
            trap_masked_cells=masked_cells[-1] if masked_cells else 0,
            trap_regions=[dict(center=list(r['center']), radius=r['radius']) for r in regions])
    return escape
