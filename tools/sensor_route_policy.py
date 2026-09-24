"""Select local waypoints from observed sensor costs, without a course oracle.

The caller supplies a current, axis-aligned ROS OccupancyGrid fused from lidar,
depth and camera paint observations, plus a broad destination. Unknown space and
paint/obstacle costs >=99 are impassable to the robot centre. Unknown and lethal
100 cells receive footprint clearance; already-inflated 99 cells do not receive
a second dilation. This module does not read any files.
It is a geometric proposal policy, not a vehicle controller or safety watchdog;
the caller must enforce freshness and execute/replan through its local controller.
"""

import heapq
import math
import time


def _circle_clear(x, y, radius, costs, width, height, resolution, origin):
    """Exact circle-versus-occupied-square check at a continuous pose."""
    ox, oy = origin
    cx, cy = math.floor((x-ox)/resolution), math.floor((y-oy)/resolution)
    if not (0 <= cx < width and 0 <= cy < height):
        return False
    if not 0 <= costs[cy*width+cx] < 99:
        return False
    low_x = math.floor((x-radius-ox)/resolution)
    high_x = math.floor((x+radius-ox)/resolution)
    low_y = math.floor((y-radius-oy)/resolution)
    high_y = math.floor((y+radius-oy)/resolution)
    if low_x < 0 or low_y < 0 or high_x >= width or high_y >= height:
        return False
    for iy in range(low_y, high_y+1):
        dy = max(oy+iy*resolution-y, 0., y-(oy+(iy+1)*resolution))
        for ix in range(low_x, high_x+1):
            value = costs[iy*width+ix]
            if value < 0 or value >= 100:
                dx = max(ox+ix*resolution-x, 0., x-(ox+(ix+1)*resolution))
                if dx*dx + dy*dy < radius*radius:
                    return False
    return True


def _rectangle_clear(x, y, yaw, bounds, costs, width, height, resolution, origin,
                     hazard_rows=None):
    """Separating-axis test of the oriented footprint and hazard cell squares."""
    xmin, xmax, ymin, ymax = bounds
    cosine, sine = math.cos(yaw), math.sin(yaw)
    hx, hy = (xmax-xmin)/2, (ymax-ymin)/2
    bx, by = (xmin+xmax)/2, (ymin+ymax)/2
    cx, cy = x + cosine*bx-sine*by, y+sine*bx+cosine*by
    ex, ey = abs(cosine)*hx+abs(sine)*hy, abs(sine)*hx+abs(cosine)*hy
    ox, oy = origin
    left, right = math.floor((cx-ex-ox)/resolution), math.floor((cx+ex-ox)/resolution)
    bottom, top = math.floor((cy-ey-oy)/resolution), math.floor((cy+ey-oy)/resolution)
    if left < 0 or bottom < 0 or right >= width or top >= height:
        return False
    half = resolution/2
    projected_half = half*(abs(cosine)+abs(sine))
    for iy in range(bottom, top+1):
        if hazard_rows is None:
            columns = range(left, right+1)
        else:
            bits = (hazard_rows[iy] >> left) & ((1 << (right-left+1))-1)
            columns = []
            while bits:
                bit = bits & -bits
                columns.append(left+bit.bit_length()-1)
                bits ^= bit
        for ix in columns:
            value = costs[iy*width+ix]
            if 0 <= value < 100:
                continue
            dx, dy = ox+(ix+.5)*resolution-cx, oy+(iy+.5)*resolution-cy
            if (abs(dx) <= ex+half and abs(dy) <= ey+half
                    and abs(dx*cosine+dy*sine) <= hx+projected_half
                    and abs(-dx*sine+dy*cosine) <= hy+projected_half):
                return False
    return True


def _local_endpoint(full, yaws, lookahead, goal_footprint, costs, width,
                    height, resolution, origin, destination=None,
                    min_goal_distance=0., continuation_reserve=0.):
    lengths = [0.]
    for a, b in zip(full, full[1:]):
        lengths.append(lengths[-1] + math.dist(a, b))
    preferred = next((i for i, distance in enumerate(lengths) if distance >= lookahead),
                     len(full)-1)
    if goal_footprint is None and min_goal_distance == 0 and continuation_reserve == 0:
        return preferred, lengths[preferred]
    terminal = (destination is not None
                and math.dist(full[-1], destination) <= max(resolution, .25))
    candidates = [preferred] + sorted(
        (i for i in range(1, len(full)) if i != preferred and (
            lengths[i] >= 1. or min_goal_distance > 0 or continuation_reserve > 0)),
        key=lambda i: abs(lengths[i]-lengths[preferred]))
    for i in candidates:
        if math.dist(full[0], full[i]) < min_goal_distance:
            continue
        if not terminal and lengths[-1]-lengths[i] < continuation_reserve:
            continue
        if goal_footprint is None or _rectangle_clear(
                *full[i], yaws[i], goal_footprint, costs, width,
                height, resolution, origin):
            return i, lengths[i]
    return None


def _forward_goal(clear, costs, width, height, resolution, origin,
                  robot_xy, robot_yaw, destination, robot_radius, lookahead,
                  max_length, min_progress, goal_footprint=None,
                  minimum_turn_radius=1.25, max_expansions=10000,
                  max_search_seconds=None, min_goal_distance=0.,
                  continuation_reserve=0.):
    """Bounded hybrid search: continuous poses, quantized position/heading keys.

    Only forward straight and circular primitives exist, with bounded curvature;
    pose coordinates are never snapped to grid centres. The grid is used for
    dominance and collision checks only. This is an observed-space proposal,
    not a replacement for the execution controller's full-footprint checks.
    """
    ox, oy = origin
    angle_step = math.pi / 8
    step = max(minimum_turn_radius * angle_step, resolution * 2)
    # Finer intervals tighten the conservative translation/rotation envelope.
    # Coarse half-cell intervals can reject an otherwise clear corridor solely
    # because the long rear footprint amplifies the angular sweep allowance.
    samples = 4 * max(2, math.ceil(step / (resolution * .5)))
    # Every point on an arc is within half a sample interval of an endpoint.
    # This extra radius therefore bounds the entire swept circle between checks.
    swept_radius = robot_radius + step / samples / 2
    footprint_mask, swept_footprint, hazard_rows = None, None, None
    if goal_footprint is not None:
        xmin, xmax, ymin, ymax = goal_footprint
        corner_radius = math.hypot(max(abs(xmin), abs(xmax)),
                                   max(abs(ymin), abs(ymax)))
        # Between two samples, any footprint point travels no faster than
        # translation plus angular speed times its distance from the axle.
        # Expand both rectangle axes by that half-interval displacement.
        margin = step / samples / 2 * (1 + corner_radius * angle_step / step)
        swept_footprint = (xmin-margin, xmax+margin, ymin-margin, ymax+margin)
        hazard_rows = [0] * height
        for cell, value in enumerate(costs):
            if value < 0 or value >= 100:
                hazard_rows[cell//width] |= 1 << (cell % width)
        footprint_mask = _clearance_mask(costs, width, height,
            (corner_radius+margin)/resolution + math.sqrt(2.))
        if not _rectangle_clear(*robot_xy, robot_yaw, swept_footprint,
                                costs, width, height, resolution, origin, hazard_rows):
            return None
    primitives = {}
    for heading in range(16):
        yaw = robot_yaw + heading * angle_step
        for turn in (-1, 0, 1):
            curvature = turn * angle_step / step
            offsets = []
            for i in range(1, samples + 1):
                distance = step * i / samples
                angle = yaw + curvature * distance
                if turn:
                    dx = (math.sin(angle) - math.sin(yaw)) / curvature
                    dy = (math.cos(yaw) - math.cos(angle)) / curvature
                else:
                    dx, dy = distance * math.cos(yaw), distance * math.sin(yaw)
                offsets.append((dx, dy))
            primitives[heading, turn] = offsets

    def key(x, y, heading):
        return (math.floor((x - ox) / resolution),
                math.floor((y - oy) / resolution), heading)

    initial = math.dist(robot_xy, destination)
    # Immutable nodes preserve the exact checked trajectory even if another
    # continuous pose later replaces the best cost for a quantized state.
    nodes = [(robot_xy[0], robot_xy[1], 0, 0., 0., -1, ())]
    seen = {key(*robot_xy, 0): 0.}
    queue = [(initial, 0)]
    best, best_score, expanded = None, float('inf'), 0
    expansion_limit = max_expansions
    search_started = time.monotonic() if max_search_seconds is not None else None
    time_budget_exhausted = False
    while queue and expanded < expansion_limit:
        if (max_search_seconds is not None and expanded % 64 == 0
                and time.monotonic()-search_started >= max_search_seconds):
            time_budget_exhausted = True
            break
        _, index = heapq.heappop(queue)
        x, y, heading, travel, length, parent, segment = nodes[index]
        if travel != seen.get(key(x, y, heading)):
            continue
        expanded += 1
        remaining = math.dist((x, y), destination)
        if initial - remaining >= min_progress:
            # Prefer observed destination progress over a cheap endpoint in a
            # nearby dead end. Traversal still uses soft-cost-aware dominance.
            score = remaining + .01 * travel
            if score < best_score:
                best, best_score = index, score
            if remaining <= max(resolution, .25):
                best = index
                break
        if length + step > max_length:
            continue
        for turn in (0, -1, 1):
            segment = []
            soft = 0.
            previous_x, previous_y, _ = key(x, y, 0)
            for dx, dy in primitives[heading, turn]:
                px, py = x + dx, y + dy
                cx, cy, _ = key(px, py, 0)
                if not (0 <= cx < width and 0 <= cy < height):
                    break
                cell = cy * width + cx
                if not clear[cell] and not _circle_clear(
                        px, py, swept_radius, costs, width, height, resolution, origin):
                    break
                if footprint_mask is not None and not footprint_mask[cell]:
                    sample_yaw = robot_yaw + (
                        heading + turn*(len(segment)+1)/samples)*angle_step
                    if not _rectangle_clear(px, py, sample_yaw, swept_footprint,
                                            costs, width, height, resolution, origin,
                                            hazard_rows):
                        break
                # Samples are <= half a cell apart. Check both side cells
                # when crossing a grid corner, including undilated cost 99.
                if (cx != previous_x and cy != previous_y
                        and (not 0 <= costs[previous_y * width + cx] < 99
                             or not 0 <= costs[cy * width + previous_x] < 99)):
                    break
                soft += costs[cell] / 98.
                segment.append((px, py))
                previous_x, previous_y = cx, cy
            if len(segment) != samples:
                continue
            nx, ny = segment[-1]
            nh = (heading + turn) % 16
            candidate = travel + step * (1 + 2 * soft / samples)
            state = key(nx, ny, nh)
            if candidate >= seen.get(state, float('inf')):
                continue
            seen[state] = candidate
            nodes.append((nx, ny, nh, candidate, length + step, index, segment))
            # Destination distance guides expansion, but never prunes an edge
            # for temporarily going away from the destination.
            priority = candidate + 1.5 * math.dist((nx, ny), destination)
            heapq.heappush(queue, (priority, len(nodes) - 1))
    if best is None:
        return None
    chain = []
    index = best
    while nodes[index][5] != -1:
        chain.append(index)
        index = nodes[index][5]
    full, yaws = [tuple(robot_xy)], [robot_yaw]
    for index in reversed(chain):
        node = nodes[index]
        previous_heading = nodes[node[5]][2]
        turn = (node[2]-previous_heading+8) % 16-8
        for i, position in enumerate(node[6], 1):
            full.append(position)
            yaws.append(robot_yaw+(previous_heading+turn*i/samples)*angle_step)
    selected = _local_endpoint(full, yaws, lookahead, goal_footprint, costs,
                               width, height, resolution, origin, destination,
                               min_goal_distance, continuation_reserve)
    if selected is None:
        return None
    index, travelled = selected
    path = full[:index+1]
    endpoint = nodes[best][:2]
    return {'local_goal': path[-1],
            'yaw': math.atan2(math.sin(yaws[index]), math.cos(yaws[index])),
            'path': path, 'diagnostics': {
                'expanded_cells': expanded, 'expansion_limit': expansion_limit,
                'budget_exhausted': time_budget_exhausted or (
                    expanded >= expansion_limit and bool(queue)),
                'time_budget_exhausted': time_budget_exhausted,
                'search_exhausted': not queue, 'endpoint': endpoint,
                'endpoint_progress': initial - math.dist(endpoint, destination),
                'path_length': nodes[best][4], 'local_path_length': travelled,
                'checked_continuation_length': sum(math.dist(a, b)
                    for a, b in zip(full[index:], full[index+1:])),
                'weighted_cost': nodes[best][3], 'robot_radius': robot_radius,
                'unknown_is_blocked': True, 'forward_only': True,
                'full_footprint_sweep': goal_footprint is not None,
                'minimum_turn_radius': step / angle_step}}


def _clearance_mask(costs, width, height, radius_cells):
    """Dilate physical hazards, then block already-inscribed centre cells.

    Nav2 Costmap2DPublisher translates raw 253 (inscribed) to 99, raw 254
    (lethal) to 100, and raw 255 (unknown) to -1. Dilation around 99 would
    double-count the footprint already represented by that inflation band.
    """
    prefixes = []
    for y in range(height):
        row = [0]
        for value in costs[y * width:(y + 1) * width]:
            row.append(row[-1] + int(value < 0 or value >= 100))
        prefixes.append(row)
    extent = math.floor(radius_cells)
    spans = [(dy, math.floor(math.sqrt(radius_cells ** 2 - dy ** 2)))
             for dy in range(-extent, extent + 1)]
    clear = bytearray(width * height)
    for y in range(extent, height - extent):
        for x in range(extent, width - extent):
            if costs[y * width + x] < 99 and all(
                    prefixes[y + dy][x + dx + 1] == prefixes[y + dy][x - dx]
                    for dy, dx in spans):
                clear[y * width + x] = 1
    return clear


def select_local_goal(origin_xy, resolution, width, height, costs,
                      robot_xy, robot_yaw, destination_xy, *, robot_radius=0.65,
                      lookahead=3.0, max_path_length=14.0, min_progress=0.25,
                      forward_only=False, goal_footprint=None,
                      minimum_turn_radius=1.25, max_expansions=10000,
                      max_search_seconds=None, min_goal_distance=0.,
                      continuation_reserve=0.):
    """Return ``{local_goal, yaw, path, diagnostics}``, or fail closed with None.

    Coordinates and distances are metres, yaw is radians, and ``costs`` is the
    row-major OccupancyGrid array (-1 unknown, 0..100 cost). ``path`` includes
    the actual robot position then cell centres through the selected local goal.
    ``diagnostics.endpoint`` describes the further reachable point used to choose
    the detour; it need not equal the short lookahead local goal. No edge crosses
    unknown/lethal cells, and a conservative circular clearance defaults to .65 m.
    Inscribed cost 99 blocks centres without a second footprint dilation. Soft
    inflation costs 1..98 are penalized in addition to explicit hazard clearance.

    Bounded Dijkstra searches observed free space, allowing temporary movement
    away from the destination to round an observed obstacle. A candidate must
    reduce destination distance by ``min_progress``. If none exists, the robot is
    unsafe, or input is invalid, return None rather than inventing an escape.
    There is no claim of completeness when a detour exceeds the observed horizon.
    With ``forward_only``, a bounded heading-state search uses forward arcs with
    at least ``minimum_turn_radius`` (default 1.25 m). It may curve behind the
    initial heading, but cannot
    reverse or pivot. Quantized search and the expansion cap are not complete.
    ``max_expansions`` bounds forward search (default 10,000, maximum 100,000).
    Optional ``max_search_seconds`` bounds the forward expansion loop, checking
    every 64 expanded states and returning the best already-validated proposal.
    It does not bound input checking or clearance precomputation; the caller must
    retain its external watchdog. None leaves timing out of search decisions.
    ``min_goal_distance`` strictly requires a Euclidean displacement from the
    current pose (default 0). Set it beyond the execution goal tolerance to avoid
    goals acknowledged without motion. ``continuation_reserve`` (default 0)
    leaves that much already-checked path beyond the local goal, unless the path
    endpoint reaches the actual destination within the search arrival tolerance.
    The reserve can shorten the requested lookahead. It preserves observed room
    to stop, not proof of an escape route or future navigability. The minimum
    remains strict for terminal goals; callers handle already-arrived missions.
    Endpoint scoring prioritizes progress, with a small traversal-cost penalty;
    path expansion and state dominance continue to penalize soft obstacle costs.
    Conservative grid clearance is a fast acceptance test; otherwise continuous
    arc samples check circles against hazard squares with half-sample sweep
    padding. This avoids rejecting safe poses solely from cell-centre padding.
    Optional ``goal_footprint=(xmin,xmax,ymin,ymax)`` includes caller-supplied
    padding and checks the local goal's oriented rectangle against unknown and
    lethal squares. In forward mode it additionally validates every primitive's
    swept rectangle, using translation-plus-rotation sample padding. If necessary
    another path pose at least 1 m along the path is selected; a valid original
    short final approach remains allowed. The holonomic mode checks only the
    goal rectangle. Nav2 must still validate and safely execute its own path.
    """
    try:
        if max_search_seconds is not None and (
                not math.isfinite(max_search_seconds) or max_search_seconds <= 0):
            return None
        if goal_footprint is not None and (
                len(goal_footprint) != 4
                or not all(math.isfinite(v) for v in goal_footprint)
                or goal_footprint[0] >= goal_footprint[1]
                or goal_footprint[2] >= goal_footprint[3]):
            return None
        values = (*origin_xy, *robot_xy, robot_yaw, *destination_xy, resolution,
                  robot_radius, lookahead, max_path_length, min_progress,
                  minimum_turn_radius, min_goal_distance, continuation_reserve)
        if (len(origin_xy) != 2 or len(robot_xy) != 2 or len(destination_xy) != 2
                or not all(math.isfinite(v) for v in values)
                or not isinstance(width, int) or not isinstance(height, int)
                or width <= 0 or height <= 0 or width * height > 262144
                or len(costs) != width * height or resolution <= 0
                or robot_radius < 0 or lookahead <= 0 or max_path_length <= 0
                or min_progress <= 0
                or minimum_turn_radius <= 0
                or min_goal_distance < 0 or continuation_reserve < 0
                or not isinstance(max_expansions, int)
                or not 1 <= max_expansions <= 100000
                or any(not math.isfinite(v) or v < -1 or v > 100 for v in costs)):
            return None
    except (TypeError, ValueError, OverflowError):
        return None

    ox, oy = origin_xy
    rx, ry = robot_xy
    gx, gy = destination_xy
    sx, sy = math.floor((rx - ox) / resolution), math.floor((ry - oy) / resolution)
    if not (0 <= sx < width and 0 <= sy < height):
        return None
    # Extra cell diagonal covers obstacle cell area, swept grid edges and the
    # initial robot-to-cell-centre offset, not merely point obstacle centres.
    # Include the sample-sweep allowance even on the fast-acceptance branch.
    sweep_padding = resolution*.25 if forward_only else 0.
    radius_cells = (robot_radius+sweep_padding) / resolution + math.sqrt(2.0)
    clear = _clearance_mask(costs, width, height, radius_cells)
    start = sy * width + sx
    if not clear[start] and not (forward_only and _circle_clear(
            rx, ry, robot_radius + resolution*.25,
            costs, width, height, resolution, origin_xy)):
        return None
    initial_distance = math.hypot(gx - rx, gy - ry)
    if initial_distance < min_progress:
        return None

    def point(index):
        return ox + (index % width + .5) * resolution, oy + (index // width + .5) * resolution

    if forward_only:
        return _forward_goal(clear, costs, width, height, resolution,
                             origin_xy, robot_xy, robot_yaw, destination_xy,
                             robot_radius, lookahead, max_path_length, min_progress,
                             goal_footprint, minimum_turn_radius, max_expansions,
                             max_search_seconds, min_goal_distance, continuation_reserve)

    infinity = float('inf')
    count = width * height
    distances = [infinity] * count
    lengths = [infinity] * count
    parents = [-1] * count
    distances[start] = 0.0
    lengths[start] = math.dist(robot_xy, point(start))
    queue = [(0.0, start)]
    best, best_score = None, infinity
    expanded = 0
    neighbours = [(dx, dy, math.hypot(dx, dy) * resolution)
                  for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                  if dx or dy]
    while queue:
        travel_cost, cell = heapq.heappop(queue)
        if travel_cost != distances[cell]:
            continue
        expanded += 1
        x, y = cell % width, cell // width
        px, py = point(cell)
        remaining = math.hypot(gx - px, gy - py)
        progress = initial_distance - remaining
        if cell != start and progress >= min_progress:
            score = remaining + .22 * travel_cost
            if score < best_score:
                best, best_score = cell, score
        for dx, dy, step in neighbours:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < width and 0 <= ny < height):
                continue
            other = ny * width + nx
            if not clear[other]:
                continue
            if dx and dy and (not clear[y * width + nx] or not clear[ny * width + x]):
                continue
            edge_length = step
            length = lengths[cell] + edge_length
            if length > max_path_length:
                continue
            # Soft costs preserve inflation gradients; a heading penalty on
            # departure favours forward detours but permits a necessary turn.
            turn = 0.0
            if cell == start:
                alignment = math.cos(math.atan2(dy, dx) - robot_yaw)
                turn = .8 * (1.0 - alignment) + (1.0 if alignment < -.25 else 0.0)
            candidate = travel_cost + edge_length * (1.0 + 2.0 * costs[other] / 98.0) + turn
            if candidate < distances[other]:
                distances[other] = candidate
                lengths[other] = length
                parents[other] = cell
                heapq.heappush(queue, (candidate, other))
    if best is None:
        return None

    cells = [best]
    while cells[-1] != start:
        cells.append(parents[cells[-1]])
    cells.reverse()
    full_path = [tuple(robot_xy)] + [point(cell) for cell in cells]
    yaws = [math.atan2(b[1]-a[1], b[0]-a[0])
            for a, b in zip(full_path, full_path[1:])]
    yaws.append(yaws[-1])
    selected = _local_endpoint(full_path, yaws, lookahead, goal_footprint, costs,
                               width, height, resolution, origin_xy, destination_xy,
                               min_goal_distance, continuation_reserve)
    if selected is None:
        return None
    index, travelled = selected
    path, yaw = full_path[:index+1], yaws[index]
    return {
        'local_goal': path[-1], 'yaw': yaw, 'path': path,
        'diagnostics': {
            'expanded_cells': expanded, 'endpoint': point(best),
            'endpoint_progress': initial_distance - math.dist(point(best), destination_xy),
            'path_length': lengths[best], 'local_path_length': travelled,
            'weighted_cost': distances[best], 'robot_radius': robot_radius,
            'unknown_is_blocked': True,
            'forward_only': forward_only,
        },
    }
