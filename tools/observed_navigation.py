"""Choose a sensor-derived lane entrance before using broad GPS direction."""
import math

from lane_corridor_policy import propose_lane_corridor
from sensor_route_policy import select_local_goal, _rectangle_clear


def valid_guidance(value):
    try:
        return (isinstance(value, dict) and set(value) == {'guidance', 'target', 'yaw'}
            and value['guidance'] in ('observed_lane_corridor', 'remembered_lane_entrance',
                                     'remembered_lane_heading', 'broad_gps')
            and len(value['target']) == 2
            and all(type(v) in (float, int) and math.isfinite(v) and abs(v) <= 1e6
                    for v in value['target'])
            and (value['yaw'] is None or (type(value['yaw']) in (float, int)
                                         and math.isfinite(value['yaw'])))
            and (value['guidance'] != 'broad_gps' or value['yaw'] is None))
    except (TypeError, ValueError):
        return False


def refine_corridor_guidance(selection, corridor, origin, resolution, width,
                             height, costs, footprint):
    """Return (selection or None, evidence) for a fresh observed corridor gate.

    A blocked midpoint does not block every lateral position. Sample at most
    35 positions within both observed boundaries, retaining the selected yaw.
    A mouth before their overlap is projected to its shared support start;
    boundaries are never extrapolated beyond their recorded endpoints. Current
    costs check the entire padded body, including its portion before support.
    This admits a goal footprint, not a route: the caller must still plan/check
    the continuous path. None means no checked gate target, never GPS fallback.
    """
    evidence = {'original_target': list(selection['target']),
                'selected_lateral_offset_m': None, 'candidates_checked': 0,
                'collision_checked': False}
    if (corridor is None or selection['guidance'] != 'observed_lane_corridor'
            or footprint is None):
        evidence['reason'] = 'no_fresh_corridor_or_footprint'
        return selection, evidence
    yaw = selection['yaw']
    if yaw is None:
        evidence['reason'] = 'missing_corridor_heading'
        return None, evidence

    def clear(target):
        ix = math.floor((target[0]-origin[0])/resolution)
        iy = math.floor((target[1]-origin[1])/resolution)
        return (0 <= ix < width and 0 <= iy < height
                and 0 <= costs[iy*width+ix] < 99
                and _rectangle_clear(*target,yaw,footprint,costs,width,height,
                                     resolution,origin))

    evidence['collision_checked'] = True
    evidence['original_target_clear'] = clear(selection['target'])
    if evidence['original_target_clear']:
        evidence.update(reason='original_target_clear',selected_lateral_offset_m=0.)
        return selection, evidence
    direction = corridor['direction']
    normal = (-direction[1],direction[0])
    dot = lambda point, axis: sum(a*b for a,b in zip(point,axis))
    segments = corridor['diagnostics']['segments']
    spans = [sorted(dot(point,direction) for point in segment) for segment in segments]
    lo, hi = max(span[0] for span in spans), min(span[1] for span in spans)
    original_t = dot(selection['target'],direction)
    station = min(hi,max(lo,original_t))
    evidence.update(observed_station_span_m=[lo,hi],station_m=station,
                    station_projection_m=station-original_t)
    if hi < lo:
        evidence['reason'] = 'no_shared_observed_station'
        return None, evidence

    def lateral(segment, t):
        a,b = segment
        return dot(a,normal)+(t-dot(a,direction))*(dot(b,normal)-dot(a,normal))/(dot(b,direction)-dot(a,direction))

    # Account for boundary slopes over the body's observed longitudinal portion.
    # Full footprint clearance against costs covers the unobserved portion.
    stations = [station,max(lo,min(hi,station+footprint[0])),
                max(lo,min(hi,station+footprint[1]))]
    sides = [sorted(lateral(segment,t) for segment in segments) for t in stations]
    lower = max(pair[0] for pair in sides)-footprint[2]
    upper = min(pair[1] for pair in sides)-footprint[3]
    center = sum(lateral(segment,station) for segment in segments)/len(segments)
    evidence['admissible_lateral_span_m'] = [lower,upper]
    if lower > upper:
        evidence['reason'] = 'no_body_width_inside_observed_gate'
        return None, evidence
    step = max(.25,(upper-lower)/32)
    samples = {lower,upper,min(upper,max(lower,center))}
    samples.update(lower+k*step for k in range(1,33) if lower+k*step < upper)
    for offset in sorted(samples,key=lambda value:(abs(value-center),value)):
        target = [direction[k]*station+normal[k]*offset for k in range(2)]
        evidence['candidates_checked'] += 1
        if clear(target):
            evidence.update(reason='clear_lateral_gate_target',selected_target=target,
                            selected_lateral_offset_m=offset-center)
            return {**selection,'target':target}, evidence
    evidence['reason'] = 'observed_gate_blocked'
    return None, evidence


def _near_mouth_target(corridor, robot_xy, robot_yaw, lookahead):
    """Advance an entered mouth only into the two observed boundary spans.

    This is guidance, never clearance authority. An oblique approach may need
    room inside the corridor to turn; the forward planner checks the full body
    against current costs rather than trying to align at a nearby/aft mouth.
    """
    # Entering is determined by longitudinal/lateral membership below, not
    # distance to the center: an oblique entry may still be far from that point.
    if corridor['diagnostics'].get('entry_mode') != 'visible_mouth':
        return None
    direction = corridor['direction']
    normal = (-direction[1], direction[0])
    heading = (math.cos(robot_yaw), math.sin(robot_yaw))
    dot = lambda point, axis: sum(a*b for a,b in zip(point,axis))
    if dot(direction, heading) < .25:
        return None
    segments = corridor['diagnostics']['segments']
    spans = [sorted(dot(point,direction) for point in segment) for segment in segments]
    lo, hi = max(span[0] for span in spans), min(span[1] for span in spans)
    robot_t = dot(robot_xy,direction)
    if not lo-1. <= robot_t <= hi:
        return None

    def lateral(segment, t):
        a,b = segment
        denominator = dot(b,direction)-dot(a,direction)
        return dot(a,normal)+(t-dot(a,direction))*(dot(b,normal)-dot(a,normal))/denominator

    sides = sorted(lateral(segment,max(lo,robot_t)) for segment in segments)
    if not sides[0]+.25 <= dot(robot_xy,normal) <= sides[1]-.25:
        return None
    t = min(hi,max(lo,robot_t+lookahead))
    if t-robot_t < 1.:
        return None
    center = sum(lateral(segment,t) for segment in segments)/len(segments)
    target = [direction[k]*t+normal[k]*center for k in range(2)]
    if dot([target[k]-robot_xy[k] for k in range(2)],heading) <= .25:
        return None
    return target


def select_observed_guidance(lane_points, robot_xy, robot_yaw, destination,
                             heading_hint=None, *, entrance_tracking=False,
                             lookahead=3., guidance_diagnostics=None,
                             corridor_scorer=None, corridor_weight=0., costmap=None):
    """Select intent at the actual pose, independently of collision search.

    The small returned target can be preserved through hypothetical backup
    evaluation. Re-running perception selection at those poses would change
    which already-observed entrance is considered consumed.

    Optional ``corridor_scorer``/``corridor_weight`` re-rank only accepted lane
    proposals (see lane_corridor_policy.propose_lane_corridor); ``costmap`` is
    the current observed (origin, resolution, width, height, costs).
    """
    diagnostic = guidance_diagnostics if guidance_diagnostics is not None else {}
    lane_diagnostic = {}
    corridor = None
    # Preserve the short final arrival rather than pursuing a lane beyond it.
    if math.dist(robot_xy, destination) > 1.0:
        # Only an active hook passes extra arguments, so a weight of 0 calls
        # the detector exactly as before.
        rerank = (dict(corridor_scorer=corridor_scorer, corridor_weight=corridor_weight,
                       costmap=costmap) if corridor_scorer is not None and corridor_weight else {})
        corridor = propose_lane_corridor(lane_points, robot_xy, robot_yaw, destination,
                                         min_width=1.2,
                                         lookahead=lookahead,
                                         diagnostics=lane_diagnostic, **rerank)
    if corridor is not None:
        interior = _near_mouth_target(corridor, robot_xy, robot_yaw, lookahead)
        if interior is not None:
            diagnostic['entrance_state'] = 'observed_mouth_handoff'
            # Leave detector evidence unchanged; record the guidance handoff
            # separately so replay can distinguish mouth from interior intent.
            corridor = {**corridor, 'entry': interior, 'center': interior,
                'diagnostics': {**corridor['diagnostics'], 'entry_mode': 'handoff',
                                'mouth_entry': list(corridor['entry'])}}
    # A supported segment can end just in front of the axle. Treat its reached
    # extent as consumed; repeatedly issuing that same tiny goal can deadlock
    # inside Nav2's arrival tolerance. All observed paint stays in the costmap.
    extent_reached = (entrance_tracking and corridor is not None
                      and corridor['diagnostics'].get('entry_mode') == 'inside'
                      and math.dist(robot_xy, corridor['entry']) <= .7)
    if extent_reached:
        diagnostic['entrance_state'] = 'observed_extent_reached'
        corridor = None
        heading_hint = None
    use_hint = corridor is None and heading_hint is not None and math.dist(robot_xy, destination) > 1.
    fixed_entrance = bool(use_hint and entrance_tracking and heading_hint.get('observed_entrance'))
    if use_hint and not fixed_entrance:
        dx, dy = destination[0]-robot_xy[0], destination[1]-robot_xy[1]
        hx, hy = heading_hint['direction']
        # GPS remains broad intent: an old straight must not override a corner
        # whose destination now lies more than 60 degrees off that direction.
        use_hint = (dx*hx+dy*hy)/max(math.hypot(dx,dy), 1e-9) >= .5
    target = corridor['entry'] if corridor is not None else heading_hint['entry'] if use_hint else destination
    guidance = ('observed_lane_corridor' if corridor else
                'remembered_lane_entrance' if fixed_entrance else
                'remembered_lane_heading' if use_hint else 'broad_gps')
    direction = corridor['direction'] if corridor else heading_hint['direction'] if use_hint else None
    target_yaw = math.atan2(direction[1], direction[0]) if direction is not None else None
    diagnostic.update(lane_detection=lane_diagnostic,
                      guidance=guidance,
                      guidance_target=list(target), guidance_yaw=target_yaw,
                      heading_hint_used=bool(use_hint))
    # Keep valid perception evidence even when collision search finds no path.
    diagnostic['corridor'] = corridor
    selected = dict(guidance=guidance, target=list(target), yaw=target_yaw)
    diagnostic['selected_guidance'] = selected
    return selected


def plan_observed_navigation(origin, resolution, width, height, costs,
                             robot_xy, robot_yaw, destination, lane_points, heading_hint=None,
                             guidance_diagnostics=None, entrance_tracking=False,
                             frozen_guidance=None, **planner_options):
    diagnostic = guidance_diagnostics if guidance_diagnostics is not None else {}
    # Corridor re-rank options belong to guidance only; select_local_goal never sees them.
    corridor_scorer = planner_options.pop('corridor_scorer', None)
    corridor_weight = planner_options.pop('corridor_weight', 0.)
    if frozen_guidance is None:
        selected = select_observed_guidance(lane_points, robot_xy, robot_yaw, destination,
            heading_hint, entrance_tracking=entrance_tracking,
            lookahead=planner_options.get('lookahead', 3.), guidance_diagnostics=diagnostic,
            corridor_scorer=corridor_scorer, corridor_weight=corridor_weight,
            costmap=(origin, resolution, width, height, costs))
        if diagnostic['corridor'] is not None:
            refined, refinement = refine_corridor_guidance(selected, diagnostic['corridor'],
                origin,resolution,width,height,costs,planner_options.get('goal_footprint'))
            diagnostic['corridor_target_refinement'] = refinement
            # No checked alternative is not proof that all forward progress is
            # blocked. Preserve original intent for the planner's existing safe
            # partial-route behavior; never replace it with broad GPS intent.
            if refined is not None:
                selected = refined
            diagnostic.update(selected_guidance=selected,guidance_target=list(selected['target']))
            diagnostic['corridor'] = {**diagnostic['corridor'],'entry':list(selected['target'])}
    else:
        selected = frozen_guidance
        if not valid_guidance(selected):
            raise ValueError('Invalid preserved observed guidance')
        diagnostic.update(guidance=selected['guidance'], guidance_target=list(selected['target']),
            guidance_yaw=selected['yaw'], selected_guidance=selected,
            corridor=None, lane_detection={'reason': 'preserved_recovery_intent'},
            heading_hint_used=False)
    target = selected['target']
    corridor = diagnostic['corridor']
    # Direction at an observed entrance is part of the guidance, unlike the
    # deliberately heading-free broad GPS destinations.
    if selected['yaw'] is not None and planner_options.get('forward_only', False):
        planner_options['destination_yaw'] = selected['yaw']
    plan = select_local_goal(origin, resolution, width, height, costs,
                             robot_xy, robot_yaw, target, **planner_options)
    # A blocked visible entrance must not silently fall back to the GPS shortcut.
    if plan is not None:
        plan['diagnostics']['guidance'] = selected['guidance']
        plan['diagnostics']['guidance_target'] = list(target)
        plan['diagnostics']['guidance_yaw'] = selected['yaw']
        if corridor is not None:
            plan['diagnostics']['corridor'] = corridor
        elif diagnostic['heading_hint_used']:
            plan['diagnostics']['heading_hint'] = heading_hint
    diagnostic['route_found'] = plan is not None
    return plan


def evaluate_observed_navigation(*args, **kwargs):
    """Process-worker envelope retains rejection evidence even without a path."""
    import time
    started = time.monotonic()
    diagnostics = {}
    plan = plan_observed_navigation(*args, guidance_diagnostics=diagnostics, **kwargs)
    return dict(plan=plan, diagnostics=diagnostics,
                search_wall_s=time.monotonic()-started)
