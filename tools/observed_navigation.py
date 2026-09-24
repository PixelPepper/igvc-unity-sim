"""Choose a sensor-derived lane entrance before using broad GPS direction."""
import math

from lane_corridor_policy import propose_lane_corridor
from sensor_route_policy import select_local_goal


def plan_observed_navigation(origin, resolution, width, height, costs,
                             robot_xy, robot_yaw, destination, lane_points, heading_hint=None,
                             **planner_options):
    corridor = None
    # Preserve the short final arrival rather than pursuing a lane beyond it.
    if math.dist(robot_xy, destination) > 1.0:
        corridor = propose_lane_corridor(lane_points, robot_xy, robot_yaw, destination,
                                         min_width=1.2,
                                         lookahead=planner_options.get('lookahead', 3.0))
    use_hint = corridor is None and heading_hint is not None and math.dist(robot_xy, destination) > 1.
    if use_hint:
        dx, dy = destination[0]-robot_xy[0], destination[1]-robot_xy[1]
        hx, hy = heading_hint['direction']
        # GPS remains broad intent: an old straight must not override a corner
        # whose destination now lies more than 60 degrees off that direction.
        use_hint = (dx*hx+dy*hy)/max(math.hypot(dx,dy), 1e-9) >= .5
    target = corridor['entry'] if corridor is not None else heading_hint['entry'] if use_hint else destination
    plan = select_local_goal(origin, resolution, width, height, costs,
                             robot_xy, robot_yaw, target, **planner_options)
    # A blocked visible entrance must not silently fall back to the GPS shortcut.
    if plan is not None:
        plan['diagnostics']['guidance'] = ('observed_lane_corridor' if corridor else
                                          'remembered_lane_heading' if use_hint else 'broad_gps')
        plan['diagnostics']['guidance_target'] = list(target)
        if corridor is not None:
            plan['diagnostics']['corridor'] = corridor
        elif use_hint:
            plan['diagnostics']['heading_hint'] = heading_hint
    return plan
