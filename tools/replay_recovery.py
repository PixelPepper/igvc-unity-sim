#!/usr/bin/env python3
"""Offline replay of stall recovery: legacy straight backup vs trap-memory retrace.

Reads only a finished run directory (run.json + decisions/NNNNN.json.gz). For
every recorded recovery selection it rebuilds the observed grid, stall pose,
selected guidance and the robot's own recent trajectory exactly as the mission
saw them, then runs both policies. Teacher traps (artifacts/learning/labels/
<run>/traps.json) are used ONLY to grade the result afterwards; they are never
passed to a policy. No ROS, Unity or network access.

    python3 tools/replay_recovery.py artifacts/sandbox/runs/<run> [...] [--controls 8]
"""
import argparse
import gzip
import json
import math
import sys
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from observed_navigation import plan_observed_navigation  # noqa: E402
from recovery_policy import select_backup_recovery, select_trap_escape  # noqa: E402
from trap_memory import (TrapMemory, entry_heading, exclude_trapped_guidance,  # noqa: E402
                         point_in_regions, recent_path)

FORWARD_OPTIONS = dict(robot_radius=.5, lookahead=7., max_path_length=14., min_progress=.1,
                       forward_only=True, minimum_turn_radius=.65, min_goal_distance=.4,
                       continuation_reserve=1.)


def load_snapshot(run, sequence):
    with gzip.open(run/'decisions'/f'{sequence:05d}.json.gz', 'rt') as stream:
        return json.load(stream)


def history_until(trajectory, stamp_s):
    return [row for row in trajectory if row[0] <= stamp_s+1e-6]


def _polyline_distance(point, line):
    best = math.inf
    for (ax, ay), (bx, by) in zip(line, line[1:]):
        dx, dy = bx-ax, by-ay
        n = dx*dx+dy*dy
        t = 0. if n == 0 else max(0., min(1., ((point[0]-ax)*dx+(point[1]-ay)*dy)/n))
        best = min(best, math.hypot(point[0]-ax-t*dx, point[1]-ay-t*dy))
    return best


def grade(plan, trap):
    """Evaluation only: how close the continuation stays to the teacher route."""
    if plan is None or trap is None or len(trap.get('teacher_route_from_end') or []) < 2:
        return None
    route = trap['teacher_route_from_end']
    path = [p[:2] for p in plan['path']]
    deviations = [_polyline_distance(p, route) for p in path]
    end = plan['diagnostics'].get('endpoint', plan['local_goal'])[:2]
    return {'endpoint_to_teacher_route_m': round(_polyline_distance(end, route), 2),
            'max_path_to_teacher_route_m': round(max(deviations), 2),
            'teacher_side': _polyline_distance(end, route) <= 1.}


def match_trap(traps, pose, stamp_s):
    best = None
    for trap in traps:
        if trap['start_s']-30 <= stamp_s <= trap['end_s']+1:
            distance = math.dist(trap['end'][:2], pose[:2])
            if best is None or distance < best[0]:
                best = (distance, trap)
    return best[1] if best else None


def replay_event(run, data, event, traps, budget_scale=1.):
    snapshot = load_snapshot(run, event['sequence'])
    grid = snapshot['input']
    origin, resolution = tuple(grid['origin']), grid['resolution']
    width, height, costs = grid['width'], grid['height'], grid['costs']
    footprint = tuple(grid['planner_options']['goal_footprint'])
    options = dict(FORWARD_OPTIONS, body_clearance_weight=grid['planner_options'].get('body_clearance_weight', 0.))
    rx, ry, ryaw = event['selection_pose']
    destination = grid['destination']
    selected = event['selection']
    stamp_s = event['odom_stamp_ns']*1e-9
    trajectory = history_until(data['trajectory'], stamp_s)
    entrance = bool(grid['planner_options'].get('entrance_tracking'))

    def planner(selection):
        return partial(plan_observed_navigation, lane_points=[], frozen_guidance=selection,
                       entrance_tracking=entrance)

    legacy = select_backup_recovery(origin, resolution, width, height, costs, (rx, ry), ryaw,
                                    destination, goal_footprint=footprint,
                                    forward_planner=planner(selected),
                                    max_search_seconds=5.*budget_scale, forward_options=options)
    path = recent_path(trajectory, max_age_s=60., max_length_m=6.)
    memory = TrapMemory()
    region = memory.record((rx, ry, ryaw), 0., event['destination_index'], entry_heading(path))
    regions = memory.regions()
    retrace_selection, exclusion = exclude_trapped_guidance(selected, destination, regions,
                                                           stall_xy=(rx, ry))
    escape = None
    if retrace_selection is not None:
        escape = select_trap_escape(origin, resolution, width, height, costs, (rx, ry), ryaw,
                                    destination, goal_footprint=footprint, driven_path=path,
                                    trap_regions=regions, forward_planner=planner(retrace_selection),
                                    forward_options=options, straight_seconds=5.*budget_scale,
                                    retrace_seconds=8.*budget_scale)
    trap = match_trap(traps, (rx, ry), stamp_s)

    def summary(result):
        if result is None:
            return None
        plan = result['forward_plan']
        return {'type': result.get('escape_type', 'straight_backup'),
                'distance_m': result['distance_m'],
                'continuation_goal': [round(v, 2) for v in plan['local_goal'][:2]],
                'trap_progress_m': round(result['diagnostics']['original_trap_progress_m'], 2),
                'corridor_deviation_m': (round(result['diagnostics']['max_corridor_deviation_m'], 2)
                                         if 'max_corridor_deviation_m' in result['diagnostics'] else None),
                'path_enters_trap_region': any(point_in_regions(p[:2], regions) for p in plan['path']),
                'teacher': grade(plan, trap)}

    return {'run': run.name, 'sequence': event['sequence'], 'stamp_s': round(stamp_s, 2),
            'stall_pose': [round(v, 3) for v in (rx, ry, ryaw)],
            'guidance': selected['guidance'], 'trap_region': {'center': [round(v, 2) for v in region['center']],
                'radius': region['radius'], 'entry_yaw': region['entry_yaw']},
            'guidance_exclusion': exclusion.get('reason') if exclusion['excluded'] else None,
            'driven_path_m': round(sum(math.dist(a, b) for a, b in zip(path, path[1:])), 2),
            'legacy': summary(legacy), 'retrace': summary(escape),
            'teacher_trap': None if trap is None else {'start_s': trap['start_s'], 'end_s': trap['end_s'],
                                                      'verdict': trap.get('verdict')}}


def replay_controls(run, data, count, budget_scale=1.):
    """Non-trap snapshots: retrace mode with no trap memory must equal legacy."""
    requests = [e for e in data.get('decisions', []) if e['phase'] == 'requested' and e.get('capture_file')]
    stalls = {e['sequence'] for e in data.get('decisions', []) if e['phase'].startswith('recovery')}
    requests = [e for e in requests if e['sequence'] not in stalls]
    if not requests or count <= 0:
        return []
    step = max(1, len(requests)//count)
    rows = []
    for event in requests[::step][:count]:
        grid = load_snapshot(run, event['sequence'])['input']
        origin, resolution = tuple(grid['origin']), grid['resolution']
        footprint = tuple(grid['planner_options']['goal_footprint'])
        options = dict(FORWARD_OPTIONS, body_clearance_weight=grid['planner_options'].get('body_clearance_weight', 0.))
        selection = {'guidance': 'broad_gps', 'target': list(grid['destination']), 'yaw': None}
        forward = partial(plan_observed_navigation, lane_points=[], frozen_guidance=selection)
        x, y = grid['robot_xy']
        yaw = grid['robot_yaw']
        args = (origin, resolution, grid['width'], grid['height'], grid['costs'], (x, y), yaw, grid['destination'])
        legacy = select_backup_recovery(*args, goal_footprint=footprint, forward_planner=forward,
                                        max_search_seconds=5.*budget_scale, forward_options=options)
        trajectory = history_until(data['trajectory'], event['odom_stamp_ns']*1e-9)
        new = select_trap_escape(*args, goal_footprint=footprint, driven_path=recent_path(trajectory),
                                 trap_regions=[], forward_planner=forward,
                                 forward_options=options, straight_seconds=5.*budget_scale,
                                    retrace_seconds=8.*budget_scale)
        # The forward search is wall-clock bounded, so an identical repeat of
        # the legacy call is the reference for run-to-run search variation.
        repeat = select_backup_recovery(*args, goal_footprint=footprint, forward_planner=forward,
                                        max_search_seconds=5.*budget_scale, forward_options=options)

        def goal(result):
            return None if result is None else [round(v, 3) for v in result['forward_plan']['local_goal'][:2]]

        rows.append({'sequence': event['sequence'],
                     'legacy': None if legacy is None else legacy['distance_m'],
                     'retrace_no_memory': None if new is None else [new['escape_type'], new['distance_m']],
                     'same_distance': (None if legacy is None else legacy['distance_m']) ==
                         (None if new is None or new['escape_type'] != 'straight_backup' else new['distance_m']),
                     'same_goal': goal(legacy) == goal(new) if new is None or new['escape_type'] == 'straight_backup'
                         else legacy is None,
                     'legacy_repeat_same_goal': goal(legacy) == goal(repeat)})
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('runs', nargs='+', type=Path)
    parser.add_argument('--labels-root', type=Path,
                        default=Path(__file__).resolve().parents[1]/'artifacts/learning/labels')
    parser.add_argument('--controls', type=int, default=0, help='Non-trap snapshots per run')
    parser.add_argument('--budget-scale', type=float, default=1.)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    report = []
    for run in args.runs:
        data = json.loads((run/'run.json').read_text())
        trap_file = args.labels_root/run.name/'traps.json'
        traps = json.loads(trap_file.read_text())['traps'] if trap_file.exists() else []
        events = [e for e in data.get('decisions', []) if e['phase'] == 'recovery_guidance_selected']
        entry = {'run': run.name, 'reason': data.get('reason'),
                 'stalls': [replay_event(run, data, e, traps, args.budget_scale) for e in events],
                 'controls': replay_controls(run, data, args.controls, args.budget_scale)}
        report.append(entry)
        print(json.dumps(entry, indent=1), flush=True)
    if args.output:
        args.output.write_text(json.dumps(report, indent=2)+'\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
