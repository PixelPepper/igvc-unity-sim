#!/usr/bin/env python3
"""Replay a saved observation-only decision without ROS, Unity, or course data.

Usage: --snapshot 00001.json.gz [--diagnostics-only] [--output report.json].
Exactly one optional --heading-gate/--segment-span/--pair-angle-deg experiment
may be applied; production defaults are never modified. Results are proposals,
not permission to move. Wall-limited searches can differ between machines.
"""
import argparse
from contextlib import nullcontext
import gzip
import hashlib
import json
import math
from pathlib import Path
import time
from unittest.mock import patch
import zlib

from lane_corridor_policy import propose_lane_corridor, replay_lane_corridor
import observed_navigation
from observed_navigation import plan_observed_navigation

MAX_SNAPSHOT_BYTES = 16 * 1024 * 1024
INPUT_KEYS = {'origin', 'resolution', 'width', 'height', 'costs', 'robot_xy',
              'robot_yaw', 'destination', 'lane_points', 'heading_hint', 'planner_options'}
OPTION_KEYS = {'robot_radius', 'lookahead', 'max_path_length', 'min_progress',
               'forward_only', 'goal_footprint', 'minimum_turn_radius',
               'max_expansions', 'max_search_seconds', 'min_goal_distance', 'continuation_reserve',
               'entrance_tracking', 'body_clearance_weight', 'body_clearance_scale'}


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def xy(value):
    return isinstance(value, list) and len(value) == 2 and all(finite(v) and abs(v) <= 1e6 for v in value)


def validate_snapshot(snapshot):
    """Reject unsupported data before calling numerical/search code.

    Replay safety bounds: 262144 cells, 100000 lane points, 0.005..1m cells,
    coordinates within +/-1e6m, footprint/radius <=5m, search <=30s/100000 states.
    These are offline admission limits, not changed navigation defaults.
    """
    if (not isinstance(snapshot, dict) or not {'schema_version', 'input'} <= set(snapshot)
            or not set(snapshot) <= {'schema_version', 'input', 'metadata'}
            or type(snapshot['schema_version']) is not int or snapshot['schema_version'] != 1):
        raise ValueError('Expected schema_version=1, input and optional metadata only')
    if 'metadata' in snapshot and not isinstance(snapshot['metadata'], dict):
        raise ValueError('metadata must be an object')
    inputs = snapshot['input']
    if (not isinstance(inputs, dict) or not INPUT_KEYS <= set(inputs)
            or not set(inputs) <= INPUT_KEYS | {'frozen_guidance'}):
        raise ValueError('Input must contain exactly the observation-only replay fields; course/world/route data is unsupported')
    width, height = inputs['width'], inputs['height']
    if type(width) is not int or type(height) is not int or min(width, height) <= 0 or width*height > 262144:
        raise ValueError('Grid dimensions must be positive integers with at most 262144 cells')
    costs = inputs['costs']
    if (not isinstance(costs, list) or len(costs) != width*height
            or any(type(v) is not int or not -1 <= v <= 100 for v in costs)):
        raise ValueError('Grid costs must be an exact row-major integer array in [-1,100]')
    if not finite(inputs['resolution']) or not .005 <= inputs['resolution'] <= 1.:
        raise ValueError('Replay resolution must be within [0.005,1] metres')
    if (not all(xy(inputs[k]) for k in ('origin', 'robot_xy', 'destination'))
            or not finite(inputs['robot_yaw'])):
        raise ValueError('Expected finite metric XY coordinates and yaw radians')
    points = inputs['lane_points']
    if not isinstance(points, list) or len(points) > 100000 or not all(xy(p) for p in points):
        raise ValueError('lane_points must contain at most 100000 finite metric XY observations')
    hint = inputs['heading_hint']
    frozen = inputs.get('frozen_guidance')
    if frozen is not None and not observed_navigation.valid_guidance(frozen):
        raise ValueError('Invalid preserved observed guidance')
    if hint is not None and (not isinstance(hint, dict) or not {'entry', 'direction'} <= set(hint)
            or not xy(hint['entry']) or not xy(hint['direction']) or math.hypot(*hint['direction']) == 0):
        raise ValueError('heading_hint requires finite entry and nonzero direction, or null')
    options = inputs['planner_options']
    if not isinstance(options, dict) or not set(options) <= OPTION_KEYS:
        raise ValueError('Unsupported planner_options')
    for key, value in options.items():
        if key in ('forward_only', 'entrance_tracking'):
            if type(value) is not bool:
                raise ValueError(key+' must be boolean')
        elif key == 'goal_footprint':
            if value is not None and (not isinstance(value, list) or len(value) != 4
                    or not all(finite(v) and abs(v) <= 5 for v in value)
                    or value[0] >= value[1] or value[2] >= value[3]):
                raise ValueError('Invalid goal_footprint')
        elif key == 'max_expansions':
            if type(value) is not int or not 1 <= value <= 100000:
                raise ValueError('max_expansions must be within [1,100000]')
        elif key == 'max_search_seconds':
            if value is not None and (not finite(value) or not 0 < value <= 30):
                raise ValueError('max_search_seconds must be null or within (0,30]')
        elif key == 'body_clearance_weight':
            if not finite(value) or not 0 <= value <= 10:
                raise ValueError('body_clearance_weight must be within [0,10]')
        elif key == 'body_clearance_scale':
            if not finite(value) or not 0 < value <= 1:
                raise ValueError('body_clearance_scale must be within (0,1]')
        elif not finite(value) or value < 0 or (key not in ('robot_radius', 'min_goal_distance', 'continuation_reserve') and value == 0):
            raise ValueError('Invalid numeric planner option: ' + key)
    if options.get('robot_radius', .65) > 5:
        raise ValueError('Replay robot_radius must not exceed 5 metres')
    if options.get('minimum_turn_radius', 1.25) > 5:
        raise ValueError('Replay minimum_turn_radius must not exceed 5 metres')
    if any(options.get(key, 0) > 100 for key in ('lookahead', 'max_path_length', 'min_progress',
                                               'min_goal_distance', 'continuation_reserve')):
        raise ValueError('Replay path/goal distances must not exceed 100 metres')
    return inputs


def load_snapshot(path):
    # Outcome logs (schema_version=2) are hindsight records, never replay input.
    if path.name == 'outcomes.jsonl':
        raise ValueError('outcomes.jsonl is an outcome log, not a replay snapshot')
    if path.stat().st_size > MAX_SNAPSHOT_BYTES:
        raise ValueError('Snapshot file exceeds 16 MiB')
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rb') as stream:
        raw = stream.read(MAX_SNAPSHOT_BYTES+1)
    if len(raw) > MAX_SNAPSHOT_BYTES:
        raise ValueError('Expanded snapshot exceeds 16 MiB')
    def reject_constant(value):
        raise ValueError('Non-finite JSON constant: ' + value)
    def parse_float(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError('Non-finite JSON float')
        return result
    snapshot = json.loads(raw.decode('utf-8-sig'), parse_constant=reject_constant, parse_float=parse_float)
    validate_snapshot(snapshot)
    return snapshot, hashlib.sha256(raw).hexdigest()


def replay(snapshot, *, diagnostics_only=False, variation=None):
    inputs = validate_snapshot(snapshot)
    # Validate even when the final-arrival shortcut never calls the detector.
    if variation is not None:
        ranges = dict(heading_gate=(0., 1.), segment_span=(.5, 14.), pair_angle_deg=(0., 45.))
        if not isinstance(variation, dict) or len(variation) != 1 or not set(variation) <= set(ranges):
            raise ValueError('Replay requires exactly one supported variation')
        key, value = next(iter(variation.items()))
        if not finite(value) or not ranges[key][0] <= value <= ranges[key][1]:
            raise ValueError('Replay variation outside supported range')
    lane_diagnostics = {}
    started = time.monotonic()
    if diagnostics_only:
        function = propose_lane_corridor if variation is None else replay_lane_corridor
        options = {} if variation is None else {'variation': variation}
        corridor = function(inputs['lane_points'], inputs['robot_xy'], inputs['robot_yaw'], inputs['destination'],
                            min_width=1.2, lookahead=inputs['planner_options'].get('lookahead', 3.),
                            diagnostics=lane_diagnostics, **options)
        plan = None
        decision = dict(lane_detection=lane_diagnostics, corridor=corridor,
                        route_found=None, guidance=None,
                        reason='Lane detector inspected directly; full navigation and final-arrival gate not evaluated')
    else:
        def experiment(*args, **kwargs):
            return replay_lane_corridor(*args, variation=variation, **kwargs)
        context = nullcontext() if variation is None else patch.object(observed_navigation, 'propose_lane_corridor', experiment)
        decision = {}
        with context:
            plan = plan_observed_navigation(inputs['origin'], inputs['resolution'], inputs['width'], inputs['height'],
                inputs['costs'], inputs['robot_xy'], inputs['robot_yaw'], inputs['destination'], inputs['lane_points'],
                heading_hint=inputs['heading_hint'], guidance_diagnostics=decision,
                frozen_guidance=inputs.get('frozen_guidance'), **inputs['planner_options'])
        lane_diagnostics = decision['lane_detection']
    return dict(schema_version=1, status='diagnostics_only' if diagnostics_only else 'route_found' if plan else 'no_route',
                plan=plan, diagnostics=decision, search_wall_s=time.monotonic()-started,
                top_candidate=lane_diagnostics.get('top_candidate'), replay_variation=variation,
                snapshot_metadata=snapshot.get('metadata', {}),
                limits='Saved observations only; no course/world oracle or commands. Geometric candidates do not prove clearance. '
                       'Wall-limited search outcomes can differ by machine; replay does not reconstruct Nav2 execution.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--diagnostics-only', action='store_true')
    experiments = parser.add_mutually_exclusive_group()
    experiments.add_argument('--heading-gate', type=float, help='Offline pair heading dot threshold [0,1], default 0.25')
    experiments.add_argument('--segment-span', type=float, help='Offline minimum segment span [0.5,14]m, default 3; overlap stays 3m')
    experiments.add_argument('--pair-angle-deg', type=float, help='Offline maximum pair angle [0,45] degrees, default 8')
    args = parser.parse_args(argv)
    variation = {name: getattr(args, name) for name in ('heading_gate', 'segment_span', 'pair_angle_deg') if getattr(args, name) is not None} or None
    try:
        if args.output and args.output.resolve() == args.snapshot.resolve():
            raise ValueError('Output must be separate from the snapshot')
        snapshot, digest = load_snapshot(args.snapshot)
        report = replay(snapshot, diagnostics_only=args.diagnostics_only, variation=variation)
        report.update(snapshot_path=str(args.snapshot.resolve()), expanded_snapshot_sha256=digest)
        encoded = json.dumps(report, indent=2, allow_nan=False)+'\n'
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded, encoding='utf-8')
        print(encoded, end='')
        return 0
    except (ValueError, OSError, TypeError, KeyError, OverflowError, RecursionError, EOFError, zlib.error) as exc:
        print(json.dumps(dict(schema_version=1, status='invalid_snapshot_or_options', error=str(exc))))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
