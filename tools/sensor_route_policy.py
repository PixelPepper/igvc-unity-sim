"""Select local waypoints from observed sensor costs, without a course oracle.

The caller supplies a current, axis-aligned ROS OccupancyGrid fused from lidar,
depth and camera paint observations, plus a broad destination. Unknown space and
paint/obstacle costs >=99 are impassable to the robot centre. Unknown and lethal
100 cells receive footprint clearance; already-inflated 99 cells do not receive
a second dilation. This module does not read any files.
It is a holonomic geometric policy, not a vehicle controller or safety watchdog;
the caller must enforce freshness and execute/replan through its local controller.
"""

import heapq
import math


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
                      lookahead=3.0, max_path_length=14.0, min_progress=0.25):
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
    """
    try:
        values = (*origin_xy, *robot_xy, robot_yaw, *destination_xy, resolution,
                  robot_radius, lookahead, max_path_length, min_progress)
        if (len(origin_xy) != 2 or len(robot_xy) != 2 or len(destination_xy) != 2
                or not all(math.isfinite(v) for v in values)
                or not isinstance(width, int) or not isinstance(height, int)
                or width <= 0 or height <= 0 or width * height > 262144
                or len(costs) != width * height or resolution <= 0
                or robot_radius < 0 or lookahead <= 0 or max_path_length <= 0
                or min_progress <= 0
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
    radius_cells = robot_radius / resolution + math.sqrt(2.0)
    clear = _clearance_mask(costs, width, height, radius_cells)
    start = sy * width + sx
    if not clear[start]:
        return None
    initial_distance = math.hypot(gx - rx, gy - ry)
    if initial_distance < min_progress:
        return None

    def point(index):
        return ox + (index % width + .5) * resolution, oy + (index // width + .5) * resolution

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
                  for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy]
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
            length = lengths[cell] + step
            if length > max_path_length:
                continue
            # Soft costs preserve inflation gradients; a heading penalty on
            # departure favours forward detours but permits a necessary turn.
            turn = 0.0
            if cell == start:
                alignment = math.cos(math.atan2(dy, dx) - robot_yaw)
                turn = .8 * (1.0 - alignment) + (1.0 if alignment < -.25 else 0.0)
            candidate = travel_cost + step * (1.0 + 4.0 * costs[other] / 98.0) + turn
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
    path = [full_path[0]]
    travelled = 0.0
    for position in full_path[1:]:
        travelled += math.dist(path[-1], position)
        path.append(position)
        if travelled >= lookahead:
            break
    # The target orientation follows the next path segment around a bend.
    index = len(path) - 1
    before, after = (path[-1], full_path[index + 1]) if index + 1 < len(full_path) else (path[-2], path[-1])
    yaw = math.atan2(after[1] - before[1], after[0] - before[0])
    return {
        'local_goal': path[-1], 'yaw': yaw, 'path': path,
        'diagnostics': {
            'expanded_cells': expanded, 'endpoint': point(best),
            'endpoint_progress': initial_distance - math.dist(point(best), destination_xy),
            'path_length': lengths[best], 'local_path_length': travelled,
            'weighted_cost': distances[best], 'robot_radius': robot_radius,
            'unknown_is_blocked': True,
        },
    }
