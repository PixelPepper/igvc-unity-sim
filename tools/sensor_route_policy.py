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
from swept_footprint import arc_sweep_box


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


def _body_clearance_risk(x, y, yaw, bounds, costs, width, height, resolution,
                         origin, hazard_rows, scale):
    """Bounded soft preference in four rectangular bands around the whole body.

    Unknown/lethal squares (and the observed-grid boundary) count as hazards;
    cost 99 is already inflated and is not dilated again. These bands measure
    distance in body coordinates, not exact Euclidean clearance. They never
    participate in collision admission, and a positive risk remains traversable.
    """
    xmin, xmax, ymin, ymax = bounds
    def clear(margin):
        return _rectangle_clear(x, y, yaw,
            (xmin-margin, xmax+margin, ymin-margin, ymax+margin),
            costs, width, height, resolution, origin, hazard_rows)
    if clear(scale):
        return 0.
    for fraction, risk in ((.25, 1.), (.5, .75), (.75, .5)):
        if not clear(scale*fraction):
            return risk
    return .25


def _local_endpoint(full, yaws, lookahead, goal_footprint, costs, width,
                    height, resolution, origin, destination=None,
                    min_goal_distance=0., continuation_reserve=0.,
                    destination_yaw=None, destination_yaw_tolerance=.35):
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
        if (destination_yaw is not None and math.dist(full[i], destination) <= .7
                and abs(math.atan2(math.sin(yaws[i]-destination_yaw),
                                   math.cos(yaws[i]-destination_yaw))) > destination_yaw_tolerance):
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
                  continuation_reserve=0., destination_yaw=None, destination_yaw_tolerance=.35,
                  body_clearance_weight=0., body_clearance_scale=.30,
                  route_alternatives=0, alternative_max_seconds=None,
                  learned_scorer=None, learned_weight=0., alternative_search_fraction=.1):
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
    footprint_mask, hazard_rows = None, None
    if goal_footprint is not None:
        xmin, xmax, ymin, ymax = goal_footprint
        corner_radius = math.hypot(max(abs(xmin), abs(xmax)),
                                   max(abs(ymin), abs(ymax)))
        # Conservative radius for the fast empty-neighborhood shortcut.
        # Near hazards, directed interval boxes below check the actual sweep.
        margin = step / samples / 2 * (1 + corner_radius * angle_step / step)
        hazard_rows = [0] * height
        for cell, value in enumerate(costs):
            if value < 0 or value >= 100:
                hazard_rows[cell//width] |= 1 << (cell % width)
        footprint_mask = _clearance_mask(costs, width, height,
            (corner_radius+margin)/resolution + math.sqrt(2.))
        # The starting body itself must be clear. Directed interval envelopes
        # below check future motion; a symmetric extra margin here would
        # incorrectly forbid moving parallel to or away from a nearby cell.
        if not _rectangle_clear(*robot_xy, robot_yaw, goal_footprint,
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
    nodes = [(robot_xy[0], robot_xy[1], 0, 0., 0., -1, (), 0.)]
    seen = {key(*robot_xy, 0): 0.}
    queue = [(initial, 0)]
    best, best_score, expanded = None, float('inf'), 0
    best_route = None
    collect_alternatives = route_alternatives > 0
    alternative_pool = []

    def reconstruct(candidate_index):
        chain = []
        while nodes[candidate_index][5] != -1:
            chain.append(candidate_index)
            candidate_index = nodes[candidate_index][5]
        full, yaws = [tuple(robot_xy)], [robot_yaw]
        for candidate_index in reversed(chain):
            node = nodes[candidate_index]
            previous_heading = nodes[node[5]][2]
            turn = (node[2]-previous_heading+8) % 16-8
            for i, position in enumerate(node[6], 1):
                full.append(position)
                yaws.append(robot_yaw+(previous_heading+turn*i/samples)*angle_step)
        return full, yaws

    expansion_limit = max_expansions
    search_started = time.monotonic() if max_search_seconds is not None else None
    time_budget_exhausted = False
    # Phase 0 is the unchanged search. Only when alternatives are requested and
    # a choice exists, two bounded side passes (phase +1 = left of the chosen
    # route, -1 = right) restart from the robot with the SAME primitives,
    # checks and priorities, and only add qualifying states to the alternative
    # pool; they never change best/best_route or the main diagnostics, which
    # are fixed beforehand.
    continuation, extra, extra_limit, continuation_total = 0, 0, 0, 0
    choice_chain = []
    while True:
        while queue and (extra < extra_limit if continuation else expanded < expansion_limit):
            if (not continuation and max_search_seconds is not None and expanded % 64 == 0
                    and time.monotonic()-search_started >= max_search_seconds):
                time_budget_exhausted = True
                break
            _, index = heapq.heappop(queue)
            x, y, heading, travel, length, parent, segment, accumulated_risk = nodes[index]
            if travel != seen.get(key(x, y, heading)):
                continue
            if continuation:
                # Near the robot both passes share the root fan; beyond it a pass
                # keeps only states on its own side, outside the chosen tube.
                if (math.dist((x, y), robot_xy) >= 1.
                        and _side_of_route(x, y, choice_chain) != continuation):
                    continue
                extra += 1
            else:
                expanded += 1
            remaining = math.dist((x, y), destination)
            heading_error = (abs(math.atan2(math.sin(robot_yaw+heading*angle_step-destination_yaw),
                                           math.cos(robot_yaw+heading*angle_step-destination_yaw)))
                             if destination_yaw is not None else 0.)
            aligned = destination_yaw is None or heading_error <= destination_yaw_tolerance
            # A near-terminal primitive may be closer than the minimum usable
            # goal displacement. Keep searching instead of declaring arrival and
            # then rejecting the only reconstructed path in _local_endpoint.
            if (initial - remaining >= min_progress
                    and math.dist(robot_xy, (x, y)) >= min_goal_distance
                    and (remaining > .7 or aligned)):
                # Prefer observed destination progress over a cheap endpoint in a
                # nearby dead end. Traversal still uses soft-cost-aware dominance.
                score = (remaining + minimum_turn_radius*heading_error + .01 * travel
                         + accumulated_risk)
                terminal = remaining <= max(resolution, .25) and aligned
                # A partial chain must fit BOTH the minimum local displacement
                # and the checked continuation. A cheap short chain cannot win
                # ranking and later mask a usable, already-checked alternative.
                # This length gate is necessary only; curved-path displacement,
                # heading and the actual local body still require admission.
                enough_length = length >= min_goal_distance + (0. if terminal else continuation_reserve)
                if collect_alternatives and enough_length:
                    # Record only; ranking/break decisions below are unchanged.
                    alternative_pool.append((score, index))
                if not continuation and enough_length and (score < best_score or terminal):
                    full, yaws = reconstruct(index)
                    selected = _local_endpoint(full, yaws, lookahead, goal_footprint,
                        costs, width, height, resolution, origin, destination,
                        min_goal_distance, continuation_reserve,
                        destination_yaw, destination_yaw_tolerance)
                    if selected is not None:
                        best, best_score = index, score
                        best_route = (full, yaws, selected)
                        if terminal:
                            break
            if length + step > max_length:
                continue
            for turn in (0, -1, 1):
                segment = []
                soft = 0.
                previous_x, previous_y, _ = key(x, y, 0)
                previous_pose = (x, y, robot_yaw+heading*angle_step)
                for dx, dy in primitives[heading, turn]:
                    px, py = x + dx, y + dy
                    sample_yaw = robot_yaw + (heading + turn*(len(segment)+1)/samples)*angle_step
                    if destination_yaw is not None and math.dist((px,py),destination) <= .7:
                        error = abs(math.atan2(math.sin(sample_yaw-destination_yaw),math.cos(sample_yaw-destination_yaw)))
                        # A robot initially near the mouth and misaligned may leave
                        # to make turning room, but cannot advance through it and
                        # return later to disguise an incompatible entry heading.
                        if (error > destination_yaw_tolerance and
                                math.dist((px,py),destination) <= math.dist(previous_pose[:2],destination)+1e-8):
                            break
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
                        sx,sy,syaw,bounds = arc_sweep_box(previous_pose,
                            (px,py,sample_yaw),goal_footprint)
                        if not _rectangle_clear(sx, sy, syaw, bounds,
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
                    previous_pose = (px,py,robot_yaw+(heading+turn*len(segment)/samples)*angle_step)
                if len(segment) != samples:
                    continue
                nx, ny = segment[-1]
                nh = (heading + turn) % 16
                body_risk = 0.
                if body_clearance_weight:
                    # Preference quadrature is bounded at three samples per
                    # primitive. Hard swept-body checks above still use ALL samples.
                    for sample_index in (math.ceil(samples/3), math.ceil(2*samples/3), samples):
                        px, py = segment[sample_index-1]
                        pyaw = robot_yaw+(heading+turn*sample_index/samples)*angle_step
                        body_risk += _body_clearance_risk(px, py, pyaw, goal_footprint,
                            costs, width, height, resolution, origin, hazard_rows,
                            body_clearance_scale)
                    body_risk *= body_clearance_weight*step/3
                candidate = travel + step * (1 + 2 * soft / samples) + body_risk
                state = key(nx, ny, nh)
                if candidate >= seen.get(state, float('inf')):
                    continue
                seen[state] = candidate
                nodes.append((nx, ny, nh, candidate, length + step, index, segment,
                              accumulated_risk+body_risk))
                # Destination distance guides expansion, but never prunes an edge
                # for temporarily going away from the destination.
                nh_error = (abs(math.atan2(math.sin(robot_yaw+nh*angle_step-destination_yaw),
                                          math.cos(robot_yaw+nh*angle_step-destination_yaw)))
                            if destination_yaw is not None else 0.)
                priority = candidate + 1.5 * (math.dist((nx, ny), destination)+minimum_turn_radius*nh_error)
                if continuation:
                    # Side passes are greedier so a small budget reaches past the
                    # obstacle; ordering only, never admission.
                    priority += _SIDE_GREED * (math.dist((nx, ny), destination)+minimum_turn_radius*nh_error)
                heapq.heappush(queue, (priority, len(nodes) - 1))
        if continuation == -1 or best is None or not collect_alternatives:
            break
        if continuation == 0:
            queue_left = bool(queue)
            result = _forward_result(nodes, best, best_route, expanded, expansion_limit,
                time_budget_exhausted, queue_left, initial, destination, robot_radius,
                goal_footprint, destination_yaw, destination_yaw_tolerance, step, angle_step,
                body_clearance_weight, body_clearance_scale)
            # Budget: by default 10% of the main expansions, split between the
            # two sides; count-bounded (no clock), so for identical inputs and
            # main search the alternatives are deterministic. Each side pass expands
            # only states strictly on that side of the chosen route (outside a
            # .5 m tube past its first metre), with fresh dominance, so the
            # cheapest such states round observed obstacles the other way.
            extra_limit = (max(_MIN_SIDE_EXPANSIONS, int(expanded*alternative_search_fraction/2))
                           if alternative_search_fraction else 0)
            choice_chain = _route_tube(_node_chain(nodes, best, robot_xy))
            main_nodes = len(nodes)
            main_sides = _sides_of_route([n[:2] for n in nodes], choice_chain, robot_xy)
        continuation_total += extra
        continuation, extra = (1 if continuation == 0 else -1), 0
        # Seed each side pass with the main search's already-checked states on
        # that side (or near the robot), so it starts where the main search
        # branched instead of re-expanding the root fan.
        queue, seen = [], {}
        for i in range(main_nodes):
            if main_sides[i] == continuation or main_sides[i] == 2:
                nx, ny, nh, travelled = nodes[i][:4]
                state = key(nx, ny, nh)
                if travelled < seen.get(state, float('inf')):
                    seen[state] = travelled
                    nh_error = (abs(_wrap(robot_yaw+nh*angle_step-destination_yaw))
                                if destination_yaw is not None else 0.)
                    queue.append((travelled + (1.5+_SIDE_GREED)*(math.dist((nx, ny), destination)
                                                  + minimum_turn_radius*nh_error), i))
        heapq.heapify(queue)
    if best is None:
        return None
    if not collect_alternatives:
        return _forward_result(nodes, best, best_route, expanded, expansion_limit,
            time_budget_exhausted, bool(queue), initial, destination, robot_radius,
            goal_footprint, destination_yaw, destination_yaw_tolerance, step, angle_step,
            body_clearance_weight, body_clearance_scale)
    started = time.monotonic() if alternative_max_seconds is not None else None
    chosen = dict(node=best, route=best_route, score=best_score)
    alternatives, scanned = _route_alternatives(chosen, alternative_pool, nodes, reconstruct,
        route_alternatives, alternative_max_seconds, started, lookahead, goal_footprint,
        costs, width, height, resolution, origin, destination, min_goal_distance,
        continuation_reserve, destination_yaw, destination_yaw_tolerance)
    features = _route_feature_rows([chosen]+alternatives, nodes, costs, width, height,
        resolution, origin, robot_xy, robot_yaw, destination, initial)
    diagnostics = result['diagnostics']
    diagnostics['route_features'] = features[0]
    diagnostics['route_alternatives'] = [dict(
        endpoint=list(nodes[alt['node']][:2]),
        local_goal=list(alt['route'][0][alt['route'][2][0]]),
        path_length=nodes[alt['node']][4], local_path_length=alt['route'][2][1],
        weighted_cost=nodes[alt['node']][3], score=alt['score'],
        distinct_by=alt['distinct_by'], features=row)
        for alt, row in zip(alternatives, features[1:])]
    diagnostics['route_alternative_search'] = dict(pool=len(alternative_pool), scanned=scanned,
        limit=route_alternatives, continuation_expansions=continuation_total+extra,
        side_pass_limit=extra_limit)
    if learned_weight and learned_scorer is not None and alternatives:
        options = [chosen] + alternatives
        rerank = dict(weight=learned_weight, chosen=0)
        try:
            score = getattr(learned_scorer, 'score', learned_scorer)
            learned = [float(v) for v in score(features)]
            if len(learned) != len(options) or not all(math.isfinite(v) for v in learned):
                raise ValueError('learned scorer returned invalid scores')
            # Re-ranks ONLY already-admissible proposals; ties keep the heuristic.
            totals = [option['score'] + learned_weight*value for option, value in zip(options, learned)]
            choice = min(range(len(options)), key=lambda i: (totals[i], i))
            rerank.update(chosen=choice, learned=learned, totals=totals)
        except (TypeError, ValueError, ArithmeticError) as exc:
            choice = 0
            rerank['error'] = str(exc)[:200]
        if choice:
            option = options[choice]
            replacement = _forward_result(nodes, option['node'], option['route'], expanded,
                expansion_limit, time_budget_exhausted, queue_left, initial, destination, robot_radius,
                goal_footprint, destination_yaw, destination_yaw_tolerance, step, angle_step,
                body_clearance_weight, body_clearance_scale)
            for key in ('route_alternatives', 'route_alternative_search'):
                replacement['diagnostics'][key] = diagnostics[key]
            replacement['diagnostics']['route_features'] = features[choice]
            replacement['diagnostics']['heuristic_endpoint'] = diagnostics['endpoint']
            result, diagnostics = replacement, replacement['diagnostics']
        diagnostics['learned_rerank'] = rerank
    return result


def _forward_result(nodes, best, best_route, expanded, expansion_limit,
                    time_budget_exhausted, queue_left, initial, destination, robot_radius,
                    goal_footprint, destination_yaw, destination_yaw_tolerance, step,
                    angle_step, body_clearance_weight, body_clearance_scale):
    full, yaws, selected = best_route
    index, travelled = selected
    path = full[:index+1]
    endpoint = nodes[best][:2]
    result = {'local_goal': path[-1],
            'yaw': math.atan2(math.sin(yaws[index]), math.cos(yaws[index])),
            'path': path, 'path_yaws': yaws[:index+1], 'diagnostics': {
                'expanded_cells': expanded, 'expansion_limit': expansion_limit,
                'budget_exhausted': time_budget_exhausted or (
                    expanded >= expansion_limit and queue_left),
                'time_budget_exhausted': time_budget_exhausted,
                'search_exhausted': not queue_left, 'endpoint': endpoint,
                'endpoint_progress': initial - math.dist(endpoint, destination),
                'path_length': nodes[best][4], 'local_path_length': travelled,
                'checked_continuation_length': sum(math.dist(a, b)
                    for a, b in zip(full[index:], full[index+1:])),
                'weighted_cost': nodes[best][3], 'robot_radius': robot_radius,
                'unknown_is_blocked': True, 'forward_only': True,
                'full_footprint_sweep': goal_footprint is not None,
                'destination_yaw': destination_yaw,
                'destination_yaw_error_rad': (abs(math.atan2(math.sin(yaws[index]-destination_yaw),math.cos(yaws[index]-destination_yaw))) if destination_yaw is not None else None),
                'mouth_reached_with_alignment': (destination_yaw is not None and math.dist(path[-1],destination)<=.7 and abs(math.atan2(math.sin(yaws[index]-destination_yaw),math.cos(yaws[index]-destination_yaw)))<=destination_yaw_tolerance),
                'minimum_turn_radius': step / angle_step}}
    if body_clearance_weight:
        result['diagnostics'].update(body_clearance_weight=body_clearance_weight,
            body_clearance_scale_m=body_clearance_scale,
            body_clearance_weighted_risk=nodes[best][7],
            body_clearance_preference_samples_per_primitive=3,
            body_clearance_preference_metric='rectangular_body_bands')
    return result


_MIN_SIDE_EXPANSIONS = 16
_SIDE_GREED = 2.5
# Observed-only per-candidate features shared by logging and learned scoring.
ROUTE_FEATURE_KEYS = ('score', 'weighted_cost', 'path_length_m', 'local_path_length_m',
    'endpoint_progress_m', 'remaining_m', 'body_risk', 'heading_change_rad', 'abs_turning_rad',
    'target_bearing_error_rad', 'lateral_mean_m', 'lateral_max_abs_m', 'endpoint_lateral_m',
    'side_sign', 'min_lethal_clearance_m', 'left_clearance_m', 'right_clearance_m',
    'min_unknown_clearance_m', 'unknown_fraction_end', 'unknown_fraction_ahead',
    'lethal_fraction_ahead', 'hazard_cells_vs_chosen')
_CLEARANCE_CAP = 3.


def _wrap(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


def _route_tube(chain, skip=1.):
    """Segments of ``chain`` beyond its first ``skip`` metres."""
    segments, travelled = [], 0.
    for a, b in zip(chain, chain[1:]):
        travelled += math.dist(a, b)
        if travelled >= skip:
            segments.append((a, b))
    return segments


def _side_of_route(x, y, segments, tube=.5):
    """0 inside the tube, else +1 left / -1 right of the nearest segment."""
    best, side = float('inf'), 1
    for (ax, ay), (bx, by) in segments:
        dx, dy = bx-ax, by-ay
        span = dx*dx + dy*dy
        t = 0. if span <= 1e-12 else min(max(((x-ax)*dx+(y-ay)*dy)/span, 0.), 1.)
        gap = math.hypot(x-ax-t*dx, y-ay-t*dy)
        if gap < best:
            best, side = gap, (1 if dx*(y-ay)-dy*(x-ax) >= 0 else -1)
    if best < tube:
        return 0
    return side


def _sides_of_route(points, segments, robot_xy, tube=.5, near=1.):
    """Vectorized ``_side_of_route``; 2 marks points within ``near`` of the robot."""
    import numpy as np
    pts = np.asarray(points, dtype=float).reshape(-1, 2)
    result = np.full(len(pts), 2, dtype=np.int8)
    far = np.hypot(pts[:, 0]-robot_xy[0], pts[:, 1]-robot_xy[1]) >= near
    if not segments or not far.any():
        return result
    a = np.asarray([s[0] for s in segments], dtype=float)
    d = np.asarray([s[1] for s in segments], dtype=float) - a
    span = np.maximum((d*d).sum(axis=1), 1e-12)
    rel = pts[far, None, :] - a[None, :, :]
    t = np.clip((rel*d[None]).sum(axis=2)/span, 0., 1.)
    gap = np.hypot(rel[..., 0]-t*d[:, 0], rel[..., 1]-t*d[:, 1])
    nearest = gap.argmin(axis=1)
    rows = np.arange(len(nearest))
    cross = d[nearest, 0]*rel[rows, nearest, 1] - d[nearest, 1]*rel[rows, nearest, 0]
    side = np.where(cross >= 0, 1, -1)
    side[gap[rows, nearest] < tube] = 0
    result[far] = side
    return result


def _node_chain(nodes, index, robot_xy):
    """Primitive endpoints from the root: a cheap polyline (chord error ~1 cm)."""
    chain = []
    while nodes[index][5] != -1:
        chain.append(nodes[index][:2])
        index = nodes[index][5]
    return [tuple(robot_xy)] + chain[::-1]


def _truncate(chain, axis, extent):
    """Prefix of ``chain`` up to along-``axis`` coordinate ``extent``."""
    origin = chain[0]
    def along(point):
        return (point[0]-origin[0])*axis[0] + (point[1]-origin[1])*axis[1]
    result = [chain[0]]
    for a, b in zip(chain, chain[1:]):
        if along(b) >= extent:
            span = along(b)-along(a)
            t = 1. if span <= 1e-9 else min(max((extent-along(a))/span, 0.), 1.)
            result.append((a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1])))
            return result
        result.append(b)
    return result


def _obstacle_cells_between(path_a, path_b, points, axis=None):
    """Count hazard points (lethal/unknown) inside path_a + reversed(path_b).

    Both paths start at the robot. With ``axis`` (unit robot-to-target), both
    are first cut at the smaller of their along-axis extents, so the closing
    segment is short and lateral; an obstacle the shorter route has not yet
    reached separates nothing. Even-odd containment. Hazards strictly between
    two routes mean they pass that observed obstacle (or unobserved shadow) on
    different sides (different homotopy class).
    """
    import numpy as np
    if len(points) == 0:
        return 0
    if axis is not None:
        def reach(chain):
            return max((p[0]-chain[0][0])*axis[0] + (p[1]-chain[0][1])*axis[1] for p in chain)
        extent = min(reach(path_a), reach(path_b))
        path_a, path_b = _truncate(path_a, axis, extent), _truncate(path_b, axis, extent)
    polygon = np.asarray(list(path_a) + list(path_b[::-1]), dtype=float)
    low, high = polygon.min(axis=0), polygon.max(axis=0)
    inside_box = np.all((points >= low) & (points <= high), axis=1)
    px, py = points[inside_box, 0], points[inside_box, 1]
    if px.size == 0:
        return 0
    inside = np.zeros(px.size, dtype=bool)
    x1, y1 = polygon[:, 0], polygon[:, 1]
    x2, y2 = np.roll(x1, -1), np.roll(y1, -1)
    for ax, ay, bx, by in zip(x1, y1, x2, y2):
        if ay == by:
            continue
        crossing = (ay > py) != (by > py)
        xint = ax + (py-ay)*(bx-ax)/(by-ay)
        inside ^= crossing & (px < xint)
    return int(inside.sum())


def _window(costs, width, height, resolution, origin, low, high, margin):
    """Row-sliced numpy view of the observed grid around a metric box."""
    import numpy as np
    ox, oy = origin
    x0 = max(0, math.floor((low[0]-margin-ox)/resolution))
    y0 = max(0, math.floor((low[1]-margin-oy)/resolution))
    x1 = min(width, math.floor((high[0]+margin-ox)/resolution)+1)
    y1 = min(height, math.floor((high[1]+margin-oy)/resolution)+1)
    if x1 <= x0 or y1 <= y0:
        return None
    grid = np.array([costs[row*width+x0:row*width+x1] for row in range(y0, y1)], dtype=np.int16)
    return grid, x0, y0


def _lethal_points(costs, width, height, resolution, origin, low, high, margin):
    import numpy as np
    window = _window(costs, width, height, resolution, origin, low, high, margin)
    if window is None:
        return np.zeros((0, 2)), np.zeros((0, 2)), np.zeros((0, 2))
    grid, x0, y0 = window
    lethal = np.argwhere(grid >= 100)
    unknown = grid < 0
    known = ~unknown
    border = np.zeros_like(unknown)
    border[1:, :] |= known[:-1, :]
    border[:-1, :] |= known[1:, :]
    border[:, 1:] |= known[:, :-1]
    border[:, :-1] |= known[:, 1:]
    frontier = np.argwhere(unknown & border)
    def centres(cells):
        return np.column_stack(((cells[:, 1]+x0+.5)*resolution+origin[0],
                                (cells[:, 0]+y0+.5)*resolution+origin[1])).astype(float)
    # Unknown cells on a 2-cell lattice: enough to see an unobserved shadow
    # between two routes while bounding containment tests.
    blocked = (grid >= 100)
    blocked[::2, ::2] |= unknown[::2, ::2]
    return centres(lethal), centres(frontier), centres(np.argwhere(blocked))


def _route_alternatives(chosen, pool, nodes, reconstruct, limit, max_seconds, started,
                        lookahead, goal_footprint, costs, width, height, resolution,
                        origin, destination, min_goal_distance, continuation_reserve,
                        destination_yaw, destination_yaw_tolerance):
    """Up to ``limit`` admissible endpoints on a different side than the choice.

    Candidates are states the main search or its bounded side passes expanded
    with the same primitives and swept checks, and that met the same
    progress/length qualification as the choice; every returned one also
    passes the same ``_local_endpoint`` admission (goal footprint, reserve,
    entrance yaw). No relaxed check. ``distinct_by`` is 'hazard_side' when
    >= 3 lethal/unknown cells lie between it and every earlier option, else
    'lateral_side' for opposite sides (>= .5 m) of the robot-to-target line.
    Bounded by a 12x scan budget and optional wall seconds.
    """
    robot_xy = nodes[0][:2]
    chosen['chain'] = _node_chain(nodes, chosen['node'], robot_xy)
    # Spatial diversity: the best-scored qualifying state per 1 m endpoint
    # bucket, so the scan is not spent on near-duplicates of the choice.
    buckets = {}
    for score, index in pool:
        if index == chosen['node']:
            continue
        x, y = nodes[index][0], nodes[index][1]
        bucket = (math.floor(x), math.floor(y))
        if bucket not in buckets or (score, index) < buckets[bucket]:
            buckets[bucket] = (score, index)
    chosen_end = nodes[chosen['node']][:2]
    scan = [dict(node=index, score=score, chain=_node_chain(nodes, index, robot_xy))
            for score, index in heapq.nsmallest(12*limit, (
                item for item in buckets.values()
                if math.dist(nodes[item[1]][:2], chosen_end) >= .5))]
    if not scan:
        return [], 0
    everything = [p for option in [chosen]+scan for p in option['chain']]
    low = (min(p[0] for p in everything), min(p[1] for p in everything))
    high = (max(p[0] for p in everything), max(p[1] for p in everything))
    lethal, frontier, blocked = _lethal_points(costs, width, height, resolution, origin,
                                               low, high, _CLEARANCE_CAP+.5)
    chosen['clouds'] = (lethal, frontier, blocked)
    ux, uy = destination[0]-robot_xy[0], destination[1]-robot_xy[1]
    norm = math.hypot(ux, uy) or 1.
    def lateral(point):
        return (-(point[0]-robot_xy[0])*uy + (point[1]-robot_xy[1])*ux)/norm
    accepted, scanned = [], 0
    for option in scan:
        if len(accepted) >= limit or (max_seconds is not None
                                      and time.monotonic()-started >= max_seconds):
            break
        scanned += 1
        reason = None
        for index, other in enumerate([chosen]+accepted):
            between = _obstacle_cells_between(option['chain'], other['chain'], blocked,
                                              (ux/norm, uy/norm))
            if index == 0:
                option['cells_vs_chosen'] = between
            a, b = lateral(option['chain'][-1]), lateral(other['chain'][-1])
            if between >= 3:
                why = 'hazard_side'
            elif (a*b < 0 and min(abs(a), abs(b)) >= .5
                  and math.dist(option['chain'][-1], other['chain'][-1]) >= 1.):
                why = 'lateral_side'
            else:
                reason = None
                break
            reason = reason or why
        if reason is None:
            continue
        full, yaws = reconstruct(option['node'])
        selected = _local_endpoint(full, yaws, lookahead, goal_footprint, costs, width,
            height, resolution, origin, destination, min_goal_distance,
            continuation_reserve, destination_yaw, destination_yaw_tolerance)
        if selected is None:
            continue
        option.update(route=(full, yaws, selected), distinct_by=reason)
        accepted.append(option)
    return accepted, scanned


def _route_feature_rows(options, nodes, costs, width, height, resolution, origin,
                        robot_xy, robot_yaw, destination, initial):
    """Observed-only geometry for each option (chosen first). No world data."""
    import numpy as np
    chains = [option.get('chain') or _node_chain(nodes, option['node'], robot_xy)
              for option in options]
    everything = [p for chain in chains for p in chain]
    low = (min(p[0] for p in everything), min(p[1] for p in everything))
    high = (max(p[0] for p in everything), max(p[1] for p in everything))
    # Reuse the alternative scan's cloud: its box covers every option here.
    clouds = options[0].get('clouds')
    if clouds is None:
        clouds = _lethal_points(costs, width, height, resolution, origin, low, high,
                                _CLEARANCE_CAP+.5)
    lethal, frontier, _ = clouds
    ox, oy = origin
    def cost_at(x, y):
        cx, cy = math.floor((x-ox)/resolution), math.floor((y-oy)/resolution)
        return costs[cy*width+cx] if 0 <= cx < width and 0 <= cy < height else -1
    ux, uy = destination[0]-robot_xy[0], destination[1]-robot_xy[1]
    norm = math.hypot(ux, uy) or 1.
    rows = []
    for option, chain in zip(options, chains):
        node = nodes[option['node']]
        full, yaws, (local_index, travelled) = option['route']
        pts = np.asarray(chain, dtype=float)
        tangents = np.diff(pts, axis=0)
        tangents = np.vstack((tangents[:1], tangents)) if len(tangents) else np.array([[1., 0.]])
        tangents /= np.maximum(np.linalg.norm(tangents, axis=1, keepdims=True), 1e-9)
        def nearest(cloud, sided=False):
            if len(cloud) == 0:
                return (_CLEARANCE_CAP,)*3 if sided else _CLEARANCE_CAP
            delta = cloud[None, :, :]-pts[:, None, :]
            distance = np.hypot(delta[..., 0], delta[..., 1])
            overall = min(float(distance.min()), _CLEARANCE_CAP)
            if not sided:
                return overall
            cross = tangents[:, None, 0]*delta[..., 1]-tangents[:, None, 1]*delta[..., 0]
            left = distance[cross > 0]
            right = distance[cross <= 0]
            return (overall, min(float(left.min()), _CLEARANCE_CAP) if left.size else _CLEARANCE_CAP,
                    min(float(right.min()), _CLEARANCE_CAP) if right.size else _CLEARANCE_CAP)
        clearance, left, right = nearest(lethal, True)
        end_x, end_y = node[0], node[1]
        end_yaw = yaws[-1]
        ahead = [cost_at(end_x+math.cos(end_yaw)*d-math.sin(end_yaw)*s,
                         end_y+math.sin(end_yaw)*d+math.cos(end_yaw)*s)
                 for d in (.5, 1., 1.5, 2., 2.5, 3.) for s in (-1., -.5, 0., .5, 1.)]
        disc = [cost_at(end_x+dx*.25, end_y+dy*.25) for dx in range(-4, 5) for dy in range(-4, 5)
                if dx*dx+dy*dy <= 16]
        laterals = [(-(p[0]-robot_xy[0])*uy+(p[1]-robot_xy[1])*ux)/norm for p in chain[1:]] or [0.]
        remaining = math.dist((end_x, end_y), destination)
        bearing = math.atan2(destination[1]-end_y, destination[0]-end_x)
        mean_lateral = sum(laterals)/len(laterals)
        row = dict(score=option['score'], weighted_cost=node[3], path_length_m=node[4],
            local_path_length_m=travelled, endpoint_progress_m=initial-remaining,
            remaining_m=remaining, body_risk=node[7],
            heading_change_rad=_wrap(end_yaw-robot_yaw),
            abs_turning_rad=sum(abs(_wrap(b-a)) for a, b in zip(yaws[::8], yaws[8::8]+[yaws[-1]])),
            target_bearing_error_rad=abs(_wrap(end_yaw-bearing)) if remaining > .25 else 0.,
            lateral_mean_m=mean_lateral, lateral_max_abs_m=max(abs(v) for v in laterals),
            endpoint_lateral_m=laterals[-1],
            side_sign=float((mean_lateral > .1)-(mean_lateral < -.1)),
            min_lethal_clearance_m=clearance, left_clearance_m=left, right_clearance_m=right,
            min_unknown_clearance_m=nearest(frontier),
            unknown_fraction_end=sum(v < 0 for v in disc)/len(disc),
            unknown_fraction_ahead=sum(v < 0 for v in ahead)/len(ahead),
            lethal_fraction_ahead=sum(v >= 99 for v in ahead)/len(ahead),
            hazard_cells_vs_chosen=float(option.get('cells_vs_chosen', 0)))
        rows.append({key: round(float(row[key]), 4) for key in ROUTE_FEATURE_KEYS})
    return rows


def _clearance_mask(costs, width, height, radius_cells):
    """Dilate physical hazards, then block already-inscribed centre cells.

    Nav2 Costmap2DPublisher translates raw 253 (inscribed) to 99, raw 254
    (lethal) to 100, and raw 255 (unknown) to -1. Dilation around 99 would
    double-count the footprint already represented by that inflation band.
    """
    import numpy as np

    extent = math.floor(radius_cells)
    if 2*extent >= min(width, height):
        return bytearray(width*height)
    spans = [(dy, math.floor(math.sqrt(radius_cells ** 2 - dy ** 2)))
             for dy in range(-extent, extent + 1)]
    grid = np.asarray(costs).reshape(height, width)
    hazards = (grid < 0) | (grid >= 100)
    prefixes = np.zeros((height, width+1), dtype=np.int32)
    np.cumsum(hazards, axis=1, dtype=np.int32, out=prefixes[:, 1:])
    # Same disk spans and exclusive prefix endpoints as the scalar policy.
    # Outer extent cells remain zero, even if no physical hazards exist there.
    interior = grid[extent:height-extent, extent:width-extent] < 99
    for dy, dx in spans:
        rows = prefixes[extent+dy:height-extent+dy]
        interior &= (rows[:, extent+dx+1:width-extent+dx+1] ==
                     rows[:, extent-dx:width-extent-dx])
    clear = np.zeros((height, width), dtype=np.uint8)
    clear[extent:height-extent, extent:width-extent] = interior
    return bytearray(clear.tobytes())


def select_local_goal(origin_xy, resolution, width, height, costs,
                      robot_xy, robot_yaw, destination_xy, *, robot_radius=0.65,
                      lookahead=3.0, max_path_length=14.0, min_progress=0.25,
                      forward_only=False, goal_footprint=None,
                      minimum_turn_radius=1.25, max_expansions=10000,
                      max_search_seconds=None, min_goal_distance=0.,
                      continuation_reserve=0., destination_yaw=None, destination_yaw_tolerance=.35,
                      body_clearance_weight=0., body_clearance_scale=.30,
                      route_alternatives=4, alternative_max_seconds=None,
                      learned_scorer=None, learned_weight=0., alternative_search_fraction=.1):
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
    Successful forward paths also return ``path_yaws``, the exact primitive
    sample orientations used by the swept footprint checks, one per path point.
    Optional ``destination_yaw`` constrains an observed entrance approach in
    forward mode only. Checked poses within .7 m cannot advance toward the
    entrance with heading error above ``destination_yaw_tolerance`` (default
    .35 rad). An initially misaligned nearby robot may move outward to make
    turning room. Partial detours outside that region remain eligible; a
    returned nearby endpoint must meet the orientation tolerance. None keeps
    the position-only policy. This constraint requires sensor-backed direction
    from the caller; broad GPS alone does not establish an entrance heading.
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
    Optional ``body_clearance_weight`` (0..10, default 0) also penalizes proximity
    of the entire configured body to unknown/lethal cells, using four rectangular
    bands of ``body_clearance_scale`` (0..1 m exclusive at zero, default .30 m).
    Positive weight requires forward mode and a configured footprint. At most
    three preference samples per primitive contribute a distance-integrated risk
    to dominance and endpoint ranking; this is not a continuous clearance proof.
    No extra hard margin is introduced, so narrow clear routes remain eligible.
    Weight zero performs no preference checks and preserves baseline results.
    Forward mode also logs up to ``route_alternatives`` (0..8, default 4)
    admissible endpoints on a different side of an observed obstacle (or of the
    robot-to-target line) in ``diagnostics.route_alternatives``, with the same
    observed-only features as ``diagnostics.route_features``. They come from
    states this search already expanded and pass the same endpoint admission;
    the chosen plan is unchanged. Two side passes (left/right of the chosen
    route) with the same primitives and checks add candidate states; together
    they are bounded by ``alternative_search_fraction`` (0..1, default .1) of
    the main search's expansions (count only, deterministic). Optional
    ``alternative_max_seconds`` (default None) also wall-limits the endpoint scan. Optional
    ``learned_scorer`` (callable or object with ``score(rows) -> scores``) and
    ``learned_weight`` (0..10, default 0) re-rank ONLY among the chosen and
    logged admissible alternatives by ``score + weight*learned``; weight 0 never
    calls the scorer, and any scorer error keeps the heuristic choice.
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
        if (not math.isfinite(body_clearance_weight) or not 0 <= body_clearance_weight <= 10
                or not math.isfinite(body_clearance_scale) or not 0 < body_clearance_scale <= 1
                or (body_clearance_weight > 0 and (not forward_only or goal_footprint is None))):
            return None
        if (destination_yaw is not None and (not forward_only or not math.isfinite(destination_yaw))
                or not math.isfinite(destination_yaw_tolerance) or not 0 < destination_yaw_tolerance <= math.pi/2):
            return None
        if max_search_seconds is not None and (
                not math.isfinite(max_search_seconds) or max_search_seconds <= 0):
            return None
        if (not isinstance(route_alternatives, int) or isinstance(route_alternatives, bool)
                or not 0 <= route_alternatives <= 8
                or alternative_max_seconds is not None and (
                    not math.isfinite(alternative_max_seconds) or alternative_max_seconds <= 0)
                or not math.isfinite(learned_weight) or not 0 <= learned_weight <= 10
                or not math.isfinite(alternative_search_fraction)
                or not 0 <= alternative_search_fraction <= 1
                or (learned_weight > 0 and (learned_scorer is None or not forward_only
                                            or route_alternatives == 0))):
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
                             max_search_seconds, min_goal_distance, continuation_reserve,
                             destination_yaw, destination_yaw_tolerance,
                             body_clearance_weight, body_clearance_scale,
                             route_alternatives, alternative_max_seconds,
                             learned_scorer, learned_weight, alternative_search_fraction)

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
