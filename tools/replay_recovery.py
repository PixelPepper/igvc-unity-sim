#!/usr/bin/env python3
"""Offline replay of stall recovery: legacy straight backup vs trap-memory retrace.

Reads only a finished run directory (run.json + decisions/NNNNN.json.gz). For
every recorded recovery_guidance_selected event it reconstructs a recovery
comparison from the event's selection pose and guidance, the grid of the
decision snapshot with the same sequence, the robot's own recorded trajectory,
fixed replay options (FORWARD_OPTIONS plus the snapshot's body clearance weight
and entrance tracking flag), the recorded continuation guidance and a fresh,
empty TrapMemory, then runs both policies. Teacher traps (artifacts/learning/
labels/<run>/traps.json) are used ONLY to grade the result afterwards; they are
never passed to a policy. No ROS, Unity or network access.

Stall rows are counterfactual reconstructions, never live-exact replays. Every
executed row carries replay_kind=counterfactual_reconstructed and
input_binding=not_evaluated: the snapshot grid is the latest planning request,
not a capture of the recovery call, and the live options, guidance, continuation
state and trap memory are not recorded. Equal grid stamps show only that the
event and snapshot name the same grid message; they prove neither full inputs
nor equivalent live state.

Stall rows (one per selected event, in run.json order, never replaced):
  event_index      position of the event in run.json decisions (sequences repeat)
  status/skipped   executed or skipped; reason explains admission or the skip
  grid_stamp       raw event and snapshot.metadata grid_stamp_ns, each with any
                   problem, and status match/mismatch/unknown/not_evaluated
  budget_scale, allow_grid_mismatch, replay_kind, input_binding
Executed rows add the legacy/retrace comparison fields unchanged. Admission:
  grid_stamp_match     both stamps are positive ints (not bool) and equal
  grid_stamp_mismatch  both valid but different; skipped unless opted in
  grid_stamp_unknown   either stamp missing or malformed (bool, float, zero,
                       negative, other types); skipped unless opted in
--allow-grid-mismatch executes mismatch/unknown rows as labelled counterfactuals.
These remain skipped even with the opt-in: event_malformed (fields the
reconstruction needs are missing or invalid), snapshot_missing,
snapshot_unreadable (gzip/decoding failure), snapshot_invalid_json and
snapshot_malformed (the grid/options the planners need are missing or invalid).
Planner errors are not caught. stall_counts reports selected = executed +
skipped, skipped_by_reason and by_status (status -> reason -> count).

Controls (--controls) pair a snapshot's planning pose with measured trajectory
history, so they execute only snapshots whose metadata proves that pose is
measured. Predicted, malformed and legacy snapshots without pose provenance are
reported as skipped rows with counts; there is no legacy override.

    python3 tools/replay_recovery.py artifacts/sandbox/runs/<run> [...] [--controls 8]
        [--allow-grid-mismatch]
"""
import argparse
import gzip
import json
import math
import sys
import zlib
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from observed_navigation import plan_observed_navigation  # noqa: E402
from recovery_policy import select_backup_recovery, select_trap_escape  # noqa: E402
from snapshot_pose_provenance import KINDS, MEASURED, classify_snapshot_pose  # noqa: E402
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


REPLAY_KIND = 'counterfactual_reconstructed'
INPUT_BINDING = 'not_evaluated'
EXECUTED_REASONS = ('grid_stamp_match', 'grid_stamp_mismatch', 'grid_stamp_unknown')
SKIP_REASONS = ('grid_stamp_mismatch', 'grid_stamp_unknown', 'event_malformed', 'snapshot_missing',
                'snapshot_unreadable', 'snapshot_invalid_json', 'snapshot_malformed')


def _number(value):
    return type(value) is int or (type(value) is float and math.isfinite(value))


def _numbers(value, length):
    return isinstance(value, (list, tuple)) and len(value) == length and all(_number(v) for v in value)


def _count(value):
    return type(value) is int and value > 0


def event_problem(event):
    """Why a selected event lacks a field its reconstruction needs, or None."""
    if not isinstance(event, dict):
        return 'event_not_object'
    if type(event.get('sequence')) is not int or event['sequence'] < 0:
        return 'sequence'
    if not _numbers(event.get('selection_pose'), 3):
        return 'selection_pose'
    selection = event.get('selection')
    if (not isinstance(selection, dict) or 'guidance' not in selection
            or not isinstance(selection.get('target'), (list, tuple)) or not _numbers(selection['target'][:2], 2)):
        return 'selection'
    if not _number(event.get('odom_stamp_ns')):
        return 'odom_stamp_ns'
    if 'destination_index' not in event:
        return 'destination_index'
    return None


def snapshot_problem(snapshot):
    """Why a snapshot lacks grid/options the planners need, or None."""
    grid = snapshot.get('input') if isinstance(snapshot, dict) else None
    if not isinstance(grid, dict):
        return 'input'
    if not _numbers(grid.get('origin'), 2):
        return 'origin'
    if not _number(grid.get('resolution')) or grid['resolution'] <= 0:
        return 'resolution'
    if not _count(grid.get('width')) or not _count(grid.get('height')):
        return 'size'
    costs = grid.get('costs')
    if (not isinstance(costs, list) or len(costs) != grid['width']*grid['height']
            or not all(type(c) is int for c in costs)):
        return 'costs'
    if not _numbers(grid.get('destination'), 2):
        return 'destination'
    options = grid.get('planner_options')
    if not isinstance(options, dict) or not _numbers(options.get('goal_footprint'), 2):
        return 'goal_footprint'
    if 'body_clearance_weight' in options and not _number(options['body_clearance_weight']):
        return 'body_clearance_weight'
    return None


def acquire_snapshot(run, sequence):
    """(snapshot, None) or (None, (skip reason, detail)); only acquisition errors are caught."""
    try:
        snapshot = load_snapshot(run, sequence)
    except FileNotFoundError as error:
        return None, ('snapshot_missing', type(error).__name__)
    except json.JSONDecodeError as error:
        return None, ('snapshot_invalid_json', type(error).__name__)
    except (OSError, EOFError, zlib.error, UnicodeDecodeError) as error:
        return None, ('snapshot_unreadable', type(error).__name__)
    problem = snapshot_problem(snapshot)
    return (None, ('snapshot_malformed', problem)) if problem else (snapshot, None)


def stamp_field(container, key):
    """The raw stamp and why it cannot be compared; the value is never coerced."""
    if not isinstance(container, dict):
        return {'value': None, 'type': None, 'problem': 'container_not_object'}
    if key not in container:
        return {'value': None, 'type': None, 'problem': 'absent'}
    value = container[key]
    kind = type(value).__name__
    if _count(value):
        return {'value': value, 'type': kind, 'problem': None}
    # Keep JSON-safe scalars verbatim; containers and non-finite floats keep only their type.
    safe = value is None or isinstance(value, (bool, int, str)) or _number(value)
    problem = 'bool' if isinstance(value, bool) else 'not_positive' if type(value) is int else 'not_int'
    return {'value': value if safe else None, 'type': kind, 'problem': problem}


def grid_stamp(event, snapshot):
    """Compare event.grid_stamp_ns with snapshot.metadata.grid_stamp_ns."""
    stamps = {'event': stamp_field(event, 'grid_stamp_ns'), 'snapshot': None}
    if snapshot is None:
        return dict(stamps, status='not_evaluated')
    metadata = snapshot.get('metadata')
    stamps['snapshot'] = (stamp_field(metadata, 'grid_stamp_ns') if 'metadata' in snapshot
                          else {'value': None, 'type': None, 'problem': 'metadata_absent'})
    if stamps['event']['problem'] or stamps['snapshot']['problem']:
        return dict(stamps, status='unknown')
    same = stamps['event']['value'] == stamps['snapshot']['value']
    return dict(stamps, status='match' if same else 'mismatch')


def replay_event(run, data, event, traps, budget_scale=1., *, event_index=None, allow_grid_mismatch=False):
    """One fixed stall row: an executed counterfactual reconstruction or a skip with its reason."""
    row = {'run': run.name, 'event_index': event_index,
           'sequence': event.get('sequence') if isinstance(event, dict) else None,
           'replay_kind': None, 'input_binding': INPUT_BINDING, 'budget_scale': budget_scale,
           'allow_grid_mismatch': allow_grid_mismatch}
    problem = event_problem(event)
    if problem:
        return dict(row, status='skipped', skipped=True, reason='event_malformed', detail=problem,
                    grid_stamp=grid_stamp(event, None))
    snapshot, failure = acquire_snapshot(run, event['sequence'])
    stamps = grid_stamp(event, snapshot)
    if failure:
        return dict(row, status='skipped', skipped=True, reason=failure[0], detail=failure[1], grid_stamp=stamps)
    reason = 'grid_stamp_'+stamps['status']
    if stamps['status'] != 'match' and not allow_grid_mismatch:
        return dict(row, status='skipped', skipped=True, reason=reason, detail=None, grid_stamp=stamps)
    row.update(replay_kind=REPLAY_KIND, status='executed', skipped=False, reason=reason, detail=None,
               grid_stamp=stamps)
    row.update(reconstruct_event(run, data, event, snapshot, traps, budget_scale))
    return row


def stall_counts(rows):
    """Selected, executed and skipped stall rows; skips and statuses by reason."""
    by_status = {'executed': {reason: 0 for reason in EXECUTED_REASONS},
                 'skipped': {reason: 0 for reason in SKIP_REASONS}}
    for row in rows:
        by_status[row['status']][row['reason']] += 1
    executed, skipped = (sum(by_status[status].values()) for status in ('executed', 'skipped'))
    return {'selected': len(rows), 'executed': executed, 'skipped': skipped,
            'skipped_by_reason': dict(by_status['skipped']), 'by_status': by_status}


def reconstruct_event(run, data, event, snapshot, traps, budget_scale=1.):
    """Both policies on one admitted event, with a fresh TrapMemory rather than the live one."""
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
    # Selection is fixed before provenance is read: ineligible snapshots become
    # skipped rows and are never replaced by searching further snapshots.
    for event in requests[::step][:count]:
        snapshot = load_snapshot(run, event['sequence'])
        provenance = classify_snapshot_pose(snapshot)
        if provenance['kind'] != MEASURED:
            # The trajectory history below is measured; pairing it with a
            # predicted or unverified planning pose would not be a like-for-like control.
            rows.append({'sequence': event['sequence'], 'skipped': True,
                         'pose_provenance': provenance['kind'], 'skip_reason': provenance['reason']})
            continue
        grid = snapshot['input']
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

        rows.append({'sequence': event['sequence'], 'skipped': False, 'pose_provenance': MEASURED,
                     'legacy': None if legacy is None else legacy['distance_m'],
                     'retrace_no_memory': None if new is None else [new['escape_type'], new['distance_m']],
                     'same_distance': (None if legacy is None else legacy['distance_m']) ==
                         (None if new is None or new['escape_type'] != 'straight_backup' else new['distance_m']),
                     'same_goal': goal(legacy) == goal(new) if new is None or new['escape_type'] == 'straight_backup'
                         else legacy is None,
                     'legacy_repeat_same_goal': goal(legacy) == goal(repeat)})
    return rows


def control_counts(rows):
    """Selected, executed and skipped control rows, with skips by pose provenance."""
    skipped = {kind: 0 for kind in KINDS if kind != MEASURED}
    for row in rows:
        if row['skipped']:
            skipped[row['pose_provenance']] += 1
    return {'selected': len(rows), 'executed': sum(not row['skipped'] for row in rows),
            'skipped': sum(skipped.values()), 'skipped_by_provenance': skipped}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('runs', nargs='+', type=Path)
    parser.add_argument('--labels-root', type=Path,
                        default=Path(__file__).resolve().parents[1]/'artifacts/learning/labels')
    parser.add_argument('--controls', type=int, default=0,
                        help='Non-trap snapshots per run. Only snapshots whose metadata proves a measured '
                             'planning pose are executed; predicted, malformed and legacy snapshots '
                             'without pose provenance are reported as skipped and not replaced.')
    parser.add_argument('--budget-scale', type=float, default=1.)
    parser.add_argument('--allow-grid-mismatch', action='store_true',
                        help='Also execute stall rows whose event and snapshot grid stamps differ or are '
                             'missing/malformed, labelled grid_stamp_mismatch/grid_stamp_unknown. Missing, '
                             'unreadable or malformed snapshots stay skipped.')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    report = []
    for run in args.runs:
        data = json.loads((run/'run.json').read_text())
        trap_file = args.labels_root/run.name/'traps.json'
        traps = json.loads(trap_file.read_text())['traps'] if trap_file.exists() else []
        # Selection is fixed before any snapshot is read; skipped events are never replaced.
        events = [(index, e) for index, e in enumerate(data.get('decisions', []))
                  if e['phase'] == 'recovery_guidance_selected']
        controls = replay_controls(run, data, args.controls, args.budget_scale)
        stalls = [replay_event(run, data, e, traps, args.budget_scale, event_index=index,
                               allow_grid_mismatch=args.allow_grid_mismatch) for index, e in events]
        entry = {'run': run.name, 'reason': data.get('reason'),
                 'stalls': stalls, 'stall_counts': stall_counts(stalls),
                 'controls': controls, 'control_counts': control_counts(controls)}
        report.append(entry)
        print(json.dumps(entry, indent=1), flush=True)
    if args.output:
        args.output.write_text(json.dumps(report, indent=2)+'\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
