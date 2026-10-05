"""Paired observed-paint corridor proposals; no files, maps or drive commands.

A proposal is not a collision-free vehicle path. The caller must validate it
against fresh observed costs with the complete footprint before execution.
"""
import math
import numpy as np


def _segments(points, diagnostics=None, minimum_span=3.):
    """Extract at most eight spatially supported straight paint segments."""
    rng = np.random.default_rng(0)
    remaining = points.copy()
    segments = []
    def reject(reason):
        if diagnostics is not None:
            counts = diagnostics['segment_rejection_counts']
            counts[reason] = counts.get(reason, 0)+1
    for _ in range(8):
        if len(remaining) < 10:
            reject('insufficient_remaining_support')
            break
        best = None
        for _ in range(160):
            if diagnostics is not None:
                diagnostics['segment_sampling_trials'] += 1
            a, b = remaining[rng.choice(len(remaining), 2, replace=False)]
            delta = b-a
            length = np.linalg.norm(delta)
            if length < 2.:
                reject('hypothesis_baseline_below_2m')
                continue
            direction = delta/length
            normal = np.array([-direction[1], direction[0]])
            ids = np.flatnonzero(np.abs((remaining-a) @ normal) <= .14)
            if len(ids) < 10:
                reject('insufficient_hypothesis_support')
                continue
            longitudinal = (remaining[ids]-a) @ direction
            order = np.argsort(longitudinal, kind='stable')
            groups = np.split(order, np.flatnonzero(np.diff(longitudinal[order]) > 1.25)+1)
            for group in groups:
                if len(group) < 10:
                    reject('insufficient_contiguous_support')
                    continue
                selected = ids[group]
                support = remaining[selected]
                center = support.mean(axis=0)
                _, _, axes = np.linalg.svd(support-center, full_matrices=False)
                axis = axes[0]
                t = (support-center) @ axis
                lo, hi = np.quantile(t, [.02, .98])
                span = hi-lo
                if span < minimum_span:
                    reject('supported_span_below_minimum')
                    continue
                bins = len(np.unique(np.floor((t-lo)/.5).astype(int)))
                coverage = min(1., bins/(math.ceil(span/.5)+1))
                if bins < 6 or coverage < .7:
                    reject('insufficient_longitudinal_bins' if bins < 6 else 'insufficient_coverage')
                    continue
                residual = np.abs((support-center) @ np.array([-axis[1], axis[0]]))
                if float(np.quantile(residual, .95)) > .16:
                    reject('excessive_fit_residual')
                    continue
                score = (len(selected), span)
                if best is None or score > best[0]:
                    best = (score, selected, dict(center=center, axis=axis,
                            a=center+lo*axis, b=center+hi*axis,
                            span=float(span), count=len(selected), coverage=coverage))
        if best is None:
            reject('no_supported_segment_this_round')
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


# Observed-only features of one accepted corridor proposal, consumed by an
# optional learned re-ranker (tools/learning, --kind corridor). The first seven
# are the detector values logged in outcomes.jsonl; the rest derive from the
# proposal entry/direction, the robot pose, the GPS destination and the current
# observed costmap. Never course, world or teacher data.
CORRIDOR_LOGGED_FEATURES = ('score', 'gps_alignment', 'confidence', 'distance_m', 'overlap_m',
                            'pair_angle_deg', 'heading_dot')
CORRIDOR_FEATURES = CORRIDOR_LOGGED_FEATURES + (
    'entry_forward_m', 'entry_lateral_abs_m', 'entry_bearing_abs_rad', 'direction_goal_dot',
    'entry_goal_distance_m', 'goal_progress_m', 'goal_axis_offset_m', 'corridor_count',
    'score_gap', 'score_rank', 'distance_gap', 'chord_lethal_fraction', 'chord_unknown_fraction',
    'ahead_lethal_fraction', 'ahead_unknown_fraction', 'entry_lethal_clearance_m',
    'ahead_lethal_distance_m')


def _cost_sampler(costmap):
    """Return cost(x, y): cell value, or None outside the observed grid."""
    origin, resolution, width, height, costs = costmap
    ox, oy, resolution, width, height = float(origin[0]), float(origin[1]), float(resolution), int(width), int(height)
    if not resolution > 0 or width <= 0 or height <= 0 or len(costs) < width*height:
        raise ValueError('Invalid costmap for corridor features')

    def cost(x, y):
        ix, iy = math.floor((x-ox)/resolution), math.floor((y-oy)/resolution)
        return costs[iy*width+ix] if 0 <= ix < width and 0 <= iy < height else None
    return cost


def _segment_fractions(cost, start, end, step=.2):
    length = math.dist(start, end)
    count = max(2, int(length/step)+1)
    lethal = unknown = 0
    for k in range(count):
        s = k/(count-1)
        value = cost(start[0]+(end[0]-start[0])*s, start[1]+(end[1]-start[1])*s)
        if value is None or value < 0:
            unknown += 1
        elif value >= 99:
            lethal += 1
    return lethal/count, unknown/count


def _first_lethal(cost, start, direction, limit, step):
    for k in range(int(limit/step)+1):
        value = cost(start[0]+direction[0]*k*step, start[1]+direction[1]*k*step)
        if value is not None and value >= 99:
            return k*step
    return limit


def corridor_feature_rows(candidates, robot_xy, robot_yaw, destination_xy, costmap=None):
    """One observed-only feature dict per accepted corridor candidate.

    ``candidates`` are accepted-candidate dicts (``entry``, ``direction`` and
    the logged detector values). ``costmap`` is (origin, resolution, width,
    height, costs) of the current observed grid; without it the costmap
    features are omitted (the scorer fills them). Group features compare each
    candidate with the others of the same decision.
    """
    rx, ry = float(robot_xy[0]), float(robot_xy[1])
    gx, gy = float(destination_xy[0]), float(destination_xy[1])
    heading = (math.cos(robot_yaw), math.sin(robot_yaw))
    goal_distance = math.hypot(gx-rx, gy-ry)
    goal_unit = ((gx-rx)/max(goal_distance, 1e-9), (gy-ry)/max(goal_distance, 1e-9))
    cost = _cost_sampler(costmap) if costmap is not None else None
    scores = [float(c['score']) for c in candidates]
    distances = [float(c['distance_m']) for c in candidates]
    order = sorted(range(len(candidates)), key=lambda k: (scores[k], k))
    rank = {k: r for r, k in enumerate(order)}
    rows = []
    for k, candidate in enumerate(candidates):
        ex, ey = float(candidate['entry'][0]), float(candidate['entry'][1])
        dx, dy = float(candidate['direction'][0]), float(candidate['direction'][1])
        norm = math.hypot(dx, dy)
        dx, dy = dx/norm, dy/norm
        vx, vy = ex-rx, ey-ry
        forward = vx*heading[0]+vy*heading[1]
        lateral = -vx*heading[1]+vy*heading[0]
        row = {name: float(candidate[name]) for name in CORRIDOR_LOGGED_FEATURES
               if type(candidate.get(name)) in (int, float) and math.isfinite(candidate[name])}
        row.update(entry_forward_m=forward, entry_lateral_abs_m=abs(lateral),
            entry_bearing_abs_rad=abs(math.atan2(lateral, forward)),
            direction_goal_dot=dx*goal_unit[0]+dy*goal_unit[1],
            entry_goal_distance_m=math.hypot(gx-ex, gy-ey),
            goal_progress_m=goal_distance-math.hypot(gx-ex, gy-ey),
            goal_axis_offset_m=abs(-(gx-ex)*dy+(gy-ey)*dx),
            corridor_count=float(len(candidates)), score_gap=scores[k]-scores[order[0]],
            score_rank=float(rank[k]), distance_gap=distances[k]-min(distances))
        if cost is not None:
            chord = _segment_fractions(cost, (rx, ry), (ex, ey))
            ahead = _segment_fractions(cost, (ex, ey), (ex+dx*6., ey+dy*6.))
            clearance = min(_first_lethal(cost, (ex, ey), (math.cos(a), math.sin(a)), 3., .15)
                            for a in (i*math.pi/4 for i in range(8)))
            row.update(chord_lethal_fraction=chord[0], chord_unknown_fraction=chord[1],
                ahead_lethal_fraction=ahead[0], ahead_unknown_fraction=ahead[1],
                entry_lethal_clearance_m=clearance,
                ahead_lethal_distance_m=_first_lethal(cost, (ex, ey), (dx, dy), 8., .2))
        rows.append(row)
    return rows


def _learned_rerank(proposals, accepted, scorer, weight, robot, robot_yaw, destination, costmap):
    """Return (index, record). Only reorders already-accepted proposals."""
    heuristic = min(range(len(proposals)), key=lambda k: proposals[k][0])
    record = dict(weight=float(weight), status='applied', heuristic_pair=accepted[heuristic]['pair'])
    try:
        if getattr(scorer, 'decision', 'corridor') != 'corridor':
            raise ValueError('scorer is not a corridor model')
        predicted = [float(v) for v in scorer.score(corridor_feature_rows(
            accepted, robot, robot_yaw, destination, costmap))]
        if len(predicted) != len(proposals) or not all(map(math.isfinite, predicted)):
            raise ValueError('scorer returned invalid predictions')
        final = [proposals[k][0]+weight*predicted[k] for k in range(len(proposals))]
        chosen = min(range(len(proposals)), key=lambda k: (final[k], k))
    except Exception as exc:  # never let a scorer change or break the policy
        record.update(status='error', error=repr(exc)[:200], selected_pair=accepted[heuristic]['pair'],
                      changed=False)
        return heuristic, record
    for candidate, value, total in zip(accepted, predicted, final):
        candidate.update(learned_regret_m=value, rerank_score=total)
    record.update(selected_pair=accepted[chosen]['pair'], changed=chosen != heuristic,
                  costmap_features=costmap is not None,
                  predicted_regret_m=predicted, final_scores=final)
    return chosen, record


def _propose_lane_corridor(lane_points, robot_xy, robot_yaw, destination_xy, *,
                          min_width=2., max_width=8., horizon=14., lookahead=3.,
                          diagnostics=None, variation=None, corridor_scorer=None,
                          corridor_weight=0., costmap=None):
    """Return entry/center/direction/yaw/confidence/diagnostics, or None.

    Outside a pair, propose its forward visible mouth, 0.6 m before the paired
    paint overlap, rather than a later midpoint across a painted side. Inside
    a pair, propose a center lookahead metres ahead, clamped to observed overlap.
    Confidence describes geometric support,
    not semantic certainty that the paint belongs to the competition corridor.
    """
    settings = dict(heading_gate=.25, segment_span=3., pair_angle_deg=8.)
    if variation is not None:
        if not isinstance(variation, dict) or len(variation) != 1 or not set(variation) <= set(settings):
            raise ValueError('Replay requires exactly one supported variation')
        key, value = next(iter(variation.items()))
        ranges = dict(heading_gate=(0., 1.), segment_span=(.5, 14.), pair_angle_deg=(0., 45.))
        if type(value) not in (int, float) or not math.isfinite(value) or not ranges[key][0] <= value <= ranges[key][1]:
            raise ValueError('Replay variation outside supported range')
        settings[key] = value
    if diagnostics is not None:
        if not isinstance(diagnostics, dict):
            raise ValueError('diagnostics must be a dictionary')
        diagnostics.clear()
        diagnostics.update(schema_version=1, status='rejected', reason=None,
            point_counts={}, segments=[], segment_rejection_counts={}, segment_sampling_trials=0,
            pair_rejection_counts={}, pair_candidates=[], accepted_candidates=[],
            selected_pair=None, top_candidate=None, top_candidate_basis=None,
            settings={**settings, 'min_width': min_width, 'max_width': max_width,
                      'horizon': horizon, 'lookahead': lookahead}, replay_variation=variation)

    def finish_failure(reason):
        if diagnostics is not None:
            diagnostics['reason'] = reason
            if diagnostics['pair_candidates']:
                diagnostics['top_candidate'] = max(diagnostics['pair_candidates'], key=lambda c:c['gates_passed'])
                diagnostics['top_candidate_basis'] = 'furthest_completed_gate; not a drivable-route ranking'
        return None

    try:
        points = np.asarray(lane_points, dtype=float)
        robot, destination = np.asarray(robot_xy, dtype=float), np.asarray(destination_xy, dtype=float)
        scalars = np.asarray([robot_yaw, min_width, max_width, horizon, lookahead], dtype=float)
        if diagnostics is not None:
            diagnostics['point_counts']['input'] = len(points) if points.ndim else 0
        if (points.ndim != 2 or points.shape[1] != 2 or len(points) < 20
                or robot.shape != (2,) or destination.shape != (2,)
                or not np.isfinite(points).all() or not np.isfinite(robot).all()
                or not np.isfinite(destination).all() or not np.isfinite(scalars).all()
                or not 0 < min_width <= max_width <= 12 or not 1 <= horizon <= 30
                or not 0 < lookahead <= horizon):
            return finish_failure('insufficient_input_points' if points.ndim == 2 and points.shape[1] == 2 and len(points) < 20 else 'invalid_input')
    except (ValueError, TypeError, OverflowError):
        return finish_failure('invalid_input')
    heading = np.array([math.cos(robot_yaw), math.sin(robot_yaw)])
    delta = points-robot
    # Spatial filtering and raster deduplication bound dense repeated history.
    range_gate = np.linalg.norm(delta, axis=1) <= horizon+max_width
    rear_gate = delta @ heading >= -2.
    if diagnostics is not None:
        diagnostics['point_counts'].update(outside_range=int((~range_gate).sum()),
            behind_rear_gate=int((range_gate & ~rear_gate).sum()))
    points = points[range_gate & rear_gate]
    if diagnostics is not None:
        diagnostics['point_counts']['after_spatial_gates'] = len(points)
    if len(points) < 20:
        return finish_failure('insufficient_points_after_spatial_gates')
    bins = np.floor(points/.1).astype(np.int64)
    _, indices = np.unique(bins, axis=0, return_index=True)
    points = points[np.sort(indices)]
    if diagnostics is not None:
        diagnostics['point_counts']['after_deduplication'] = len(points)
    if len(points) > 4000:
        points = points[np.linspace(0, len(points)-1, 4000, dtype=int)]
    if diagnostics is not None:
        diagnostics['point_counts']['after_point_cap'] = len(points)
    segments = _segments(points, diagnostics, settings['segment_span'])
    if diagnostics is not None:
        diagnostics['segments'] = [dict(index=i, center=s['center'].tolist(), axis=s['axis'].tolist(),
            a=s['a'].tolist(), b=s['b'].tolist(), span_m=s['span'], support_count=s['count'], coverage=s['coverage'])
            for i,s in enumerate(segments)]
    if len(segments) < 2:
        return finish_failure('insufficient_extracted_segments')
    proposals, accepted = [], []
    for i, first in enumerate(segments):
        for j in range(i+1, len(segments)):
            second = segments[j]
            candidate = dict(pair=[i, j], status='rejected', reason=None, gates_passed=0)
            if diagnostics is not None:
                diagnostics['pair_candidates'].append(candidate)

            def reject_pair(reason, gate, **geometry):
                if diagnostics is not None:
                    candidate.update(reason=reason, gates_passed=gate, **geometry)
                    counts = diagnostics['pair_rejection_counts']
                    counts[reason] = counts.get(reason, 0)+1

            alignment = float(first['axis'] @ second['axis'])
            candidate['pair_angle_deg'] = math.degrees(math.acos(min(1., abs(alignment))))
            if abs(alignment) < math.cos(math.radians(settings['pair_angle_deg'])):
                reject_pair('pair_angle_above_limit', 0)
                continue
            direction = first['axis'] + second['axis'] * (1 if alignment >= 0 else -1)
            direction /= np.linalg.norm(direction)
            if direction @ heading < 0:
                direction = -direction
            candidate['heading_dot'] = float(direction @ heading)
            if direction @ heading < settings['heading_gate']:
                reject_pair('corridor_heading_below_gate', 1)
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
            candidate['overlap_m'] = overlap
            if overlap < 3.:
                reject_pair('overlap_below_3m', 2)
                continue
            widths = [abs(lateral(first, t)-lateral(second, t)) for t in (lo, (lo+hi)/2, hi)]
            width = widths[1]
            candidate['width_samples_m'] = widths
            if min(widths) < min_width or max(widths) > max_width or max(widths)-min(widths) > max(.35, width*.15):
                reject_pair('width_below_minimum' if min(widths) < min_width else
                            'width_above_maximum' if max(widths) > max_width else 'width_variation_above_limit', 3)
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
                reject_pair('intervening_parallel_barrier', 4, barrier_segment=k)
                continue
            robot_t = float(robot @ direction)
            reference_t = min(hi, max(lo, robot_t))
            left, right = sorted((lateral(first, reference_t), lateral(second, reference_t)))
            # Side-line extensions do not establish longitudinal membership.
            # Before the observed overlap, approach its mouth rather than skip
            # past a nearby broad destination with an inside lookahead target.
            between_sides = left+.25 <= robot @ normal <= right-.25
            inside = between_sides and lo <= robot_t <= hi
            # The mouth lies 0.6 m before observed overlap. Once a centred,
            # aligned axle is within 0.25 m longitudinally of that mouth, hand
            # off to a target inside actual support rather than a reached mouth.
            entering = (between_sides and lo-.85 <= robot_t <= lo
                        and direction @ heading >= math.cos(.35))
            entry_mode = 'entering' if entering else 'inside' if inside else 'visible_mouth'
            t = min(hi, max(lo, robot_t+lookahead)) if inside or entering else lo-.6
            center = direction*t+normal*(lateral(first, t)+lateral(second, t))/2
            displacement = center-robot
            distance = float(np.linalg.norm(displacement))
            candidate.update(entry=center.tolist(), direction=direction.tolist(), distance_m=distance,
                             entry_mode=entry_mode)
            if distance > horizon or displacement @ heading <= .25:
                reject_pair('entry_beyond_horizon' if distance > horizon else 'entry_not_forward', 5,
                            forward_displacement_m=float(displacement @ heading))
                continue
            # A mildly skewed GPS destination must not pull entry outside the
            # observed pair, but a corridor pointing away from it is rejected.
            gps_delta = destination-center
            if gps_delta @ direction < -.5:
                reject_pair('destination_behind_corridor', 6, destination_forward_m=float(gps_delta @ direction))
                continue
            if any(_crosses(robot, center, segment) for segment in segments):
                reject_pair('entry_chord_crosses_paint', 7)
                continue
            confidence = min(1., overlap/6.)*min(first['coverage'], second['coverage'])*abs(alignment)
            gps_alignment = float(gps_delta @ direction/max(np.linalg.norm(gps_delta), 1e-9))
            score = distance + .5*(1.-gps_alignment) - 1.5*confidence
            candidate.update(status='accepted', reason='geometric_corridor_supported', gates_passed=8,
                             score=float(score), confidence=float(confidence), gps_alignment=gps_alignment)
            if diagnostics is not None:
                diagnostics['accepted_candidates'].append(candidate)
            accepted.append(candidate)
            proposals.append((score, dict(entry=center.tolist(), center=center.tolist(),
                direction=direction.tolist(), yaw=math.atan2(direction[1], direction[0]),
                confidence=float(confidence), diagnostics=dict(width_m=width,
                    overlap_m=overlap, support_counts=[first['count'], second['count']],
                    segments=[[first['a'].tolist(), first['b'].tolist()],
                              [second['a'].tolist(), second['b'].tolist()]],
                    extracted_segments=len(segments), entry_mode=entry_mode,
                    gps_alignment=gps_alignment, collision_checked=False))))
    if not proposals:
        return finish_failure('all_pairs_rejected')
    if corridor_scorer is None or not corridor_weight or len(proposals) < 2:
        selected = min(proposals, key=lambda item:item[0])[1]
        if diagnostics is not None:
            top = min(diagnostics['accepted_candidates'], key=lambda c:c['score'])
            diagnostics.update(status='accepted', reason='geometric_corridor_supported',
                               selected_pair=top['pair'], top_candidate=top,
                               top_candidate_basis='lowest_accepted_score')
        return selected
    # Optional learned re-rank among proposals that passed every gate above.
    chosen, rerank = _learned_rerank(proposals, accepted, corridor_scorer, corridor_weight,
                                     robot, robot_yaw, destination, costmap)
    selected = proposals[chosen][1]
    selected['diagnostics']['learned_rerank'] = {key: rerank[key] for key in
        ('weight', 'status', 'heuristic_pair', 'selected_pair', 'changed', 'error') if key in rerank}
    if diagnostics is not None:
        diagnostics.update(status='accepted', reason='geometric_corridor_supported',
                           selected_pair=accepted[chosen]['pair'], top_candidate=accepted[chosen],
                           top_candidate_basis=('learned_rerank' if rerank['status'] == 'applied'
                                                else 'lowest_accepted_score'),
                           corridor_rerank=rerank)
    return selected


def propose_lane_corridor(lane_points, robot_xy, robot_yaw, destination_xy, *,
                          min_width=2., max_width=8., horizon=14., lookahead=3., diagnostics=None,
                          corridor_scorer=None, corridor_weight=0., costmap=None):
    """Production policy. Optional diagnostics records gates even on rejection.

    Default thresholds and proposal selection are unchanged. At most eight
    segments and 28 pairs are retained; diagnostics cannot establish drivable
    clearance or semantic lane identity.

    Optional ``corridor_scorer`` (a corridor LearnedScorer) re-ranks ONLY the
    accepted proposals by heuristic score + ``corridor_weight`` * predicted
    teacher regret (lower wins); ``costmap`` = (origin, resolution, width,
    height, costs) supplies its observed costmap features. Weight 0 or no
    scorer is exactly the heuristic; a scorer error falls back to it and is
    flagged in diagnostics['corridor_rerank'].
    """
    return _propose_lane_corridor(lane_points, robot_xy, robot_yaw, destination_xy,
        min_width=min_width, max_width=max_width, horizon=horizon, lookahead=lookahead,
        diagnostics=diagnostics, corridor_scorer=corridor_scorer,
        corridor_weight=corridor_weight, costmap=costmap)


def replay_lane_corridor(lane_points, robot_xy, robot_yaw, destination_xy, *, variation, **options):
    """Explicit offline experiment only: alter exactly one extraction/pair gate.

    Accepted keys: heading_gate, segment_span, pair_angle_deg. Other extraction
    support and three-metre overlap checks stay unchanged; a lower segment-span
    threshold alone does not remove the overlap requirement.
    """
    return _propose_lane_corridor(lane_points, robot_xy, robot_yaw, destination_xy,
                                 variation=variation, **options)
