"""Bounded, ROS-free evidence for the legacy straight-backup recovery search.

`diagnose_backup_recovery` is the module-level (picklable) function submitted to
the existing spawn ProcessPoolExecutor in place of `select_backup_recovery`. In
the worker it fingerprints the arguments it actually received (after pickling),
runs the unchanged search with a stage trace, and returns ``(escape, evidence)``;
the escape object is returned as is. The mission fingerprints what it submitted
with the same function, so equal digests bind the trace to the exact search
inputs. On a failed search the mission may write the full inputs once with
`write_recovery_capture` (never into run.json). Nothing here moves the robot,
reads WORLD/course data or changes a safety gate.
"""
import array
from functools import partial
import gzip
import hashlib
import inspect
import json
import math
import time

from recovery_policy import select_backup_recovery

SCHEMA_VERSION = 1
MAX_TRACE = 32
MAX_ITEMS = 24
MAX_STRING = 200
MAX_DEPTH = 6
MAX_EVIDENCE_BYTES = 24000
MAX_CAPTURES = 4
_SIGNATURE = inspect.signature(select_backup_recovery)


def json_safe(value, depth=0):
    """Bounded JSON value: nonfinite floats become tagged strings; long lists/strings are cut."""
    if depth > MAX_DEPTH:
        return '<depth_limit>'
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else {'nonfinite': repr(value)}
    if isinstance(value, str):
        return value if len(value) <= MAX_STRING else value[:MAX_STRING]+'<truncated>'
    if isinstance(value, dict):
        items = list(value.items())
        result = {str(k)[:MAX_STRING]: json_safe(v, depth+1) for k, v in items[:MAX_ITEMS]}
        if len(items) > MAX_ITEMS:
            result['<omitted_keys>'] = len(items)-MAX_ITEMS
        return result
    if isinstance(value, (list, tuple, array.array)):
        items = list(value[:MAX_ITEMS])
        result = [json_safe(v, depth+1) for v in items]
        if len(value) > MAX_ITEMS:
            result.append({'<omitted_items>': len(value)-MAX_ITEMS})
        return result
    return '<'+type(value).__name__+'>'


def _canonical(value):
    """Complete (uncut) canonical form used only for hashing; floats keep repr precision."""
    if isinstance(value, float):
        return {'float': repr(value)}
    if isinstance(value, dict):
        return {str(k): _canonical(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        return [_canonical(v) for v in value]
    if isinstance(value, array.array):
        return {'array': value.typecode, 'sha256': hashlib.sha256(value.tobytes()).hexdigest()}
    if isinstance(value, partial):
        return {'partial': _callable_name(value.func), 'args': _canonical(list(value.args)),
                'keywords': _canonical(value.keywords)}
    if callable(value):
        return {'callable': _callable_name(value)}
    return value


def _callable_name(function):
    return f'{getattr(function, "__module__", "?")}.{getattr(function, "__qualname__", type(function).__name__)}'


def _grid_digest(costs):
    """sha256 of the cost cells as signed bytes (ROS OccupancyGrid int8), with the cell count."""
    if costs is None:
        return None
    try:
        return {'cells': len(costs), 'sha256': hashlib.sha256(array.array('b', costs).tobytes()).hexdigest()}
    except (TypeError, ValueError, OverflowError) as exc:
        return {'unavailable': type(exc).__name__}


def describe_search_inputs(args, kwargs):
    """Effective select_backup_recovery inputs (defaults applied) and their sha256 digest.

    The digest covers every argument completely; the description is bounded. A
    grid or argument that cannot be described is reported, never guessed.
    """
    bound = _SIGNATURE.bind(*args, **kwargs)
    bound.apply_defaults()
    values = dict(bound.arguments)
    values.pop('trace', None)
    costs, continuation = values.pop('costs'), values.pop('continuation_costs')
    grids = {'costs': _grid_digest(costs), 'continuation_costs': _grid_digest(continuation)}
    canonical = {name: _canonical(value) for name, value in values.items()}
    digest = hashlib.sha256(json.dumps({'grids': grids, 'arguments': canonical}, sort_keys=True,
                                       default=repr).encode()).hexdigest()
    planner = values['forward_planner']
    keywords = getattr(planner, 'keywords', {})
    summary = {name: json_safe(values[name]) for name in (
        'origin_xy', 'resolution', 'width', 'height', 'robot_xy', 'robot_yaw', 'destination_xy',
        'goal_footprint', 'distances', 'max_backup_distance', 'max_search_seconds', 'max_expansions',
        'forward_options', 'trap_regions')}
    summary.update(forward_planner=_callable_name(getattr(planner, 'func', planner)),
                   frozen_guidance=json_safe(keywords.get('frozen_guidance', '<not_a_keyword>')),
                   planner_keywords=sorted(keywords), grids=grids,
                   continuation_masking='none' if continuation is None else 'separate_grid')
    return {'digest': digest, 'inputs': summary}


def _bounded(evidence):
    text = json.dumps(evidence, allow_nan=False)
    if len(text) <= MAX_EVIDENCE_BYTES:
        return evidence
    trimmed = {**evidence, 'trace': [{k: record.get(k) for k in ('stage', 'reason', 'verdict', 'distance_m')
                                      if k in record} for record in evidence.get('trace', [])],
               'trace_detail_dropped_for_size': len(text)}
    trimmed['input_binding'] = {'digest': evidence['input_binding'].get('digest'),
                                'inputs_dropped_for_size': True}
    return trimmed


def diagnose_backup_recovery(*args, **kwargs):
    """Worker entry point: (unchanged escape or None, bounded evidence).

    Evidence failures are recorded in the evidence; they never alter or skip the search.
    """
    started = time.monotonic()
    try:
        binding = describe_search_inputs(args, kwargs)
    except Exception as exc:  # noqa: BLE001 - reported, the search still runs unchanged
        binding = {'digest': None, 'error': f'{type(exc).__name__}: {exc}'[:MAX_STRING]}
    trace = []
    escape = select_backup_recovery(*args, trace=trace, **kwargs)
    try:
        evidence = _bounded({
            'schema_version': SCHEMA_VERSION, 'search': 'legacy_straight_backup',
            'result': 'escape' if escape is not None else 'none',
            'returned_stage': trace[-1]['stage'] if trace else None,
            'input_binding': json_safe(binding), 'trace': json_safe(trace[:MAX_TRACE]),
            'trace_records': len(trace), 'worker_wall_s': time.monotonic()-started})
    except Exception as exc:  # noqa: BLE001
        evidence = {'schema_version': SCHEMA_VERSION, 'error': f'{type(exc).__name__}: {exc}'[:MAX_STRING]}
    return escape, evidence


def write_recovery_capture(path, args, kwargs, context):
    """Write the complete search inputs once (gzip JSON, exclusive create); returns the digest.

    ``context`` holds observation provenance (stamps, frames, ages); the forward
    planner is recorded by name and keywords, since a function cannot be stored.
    """
    bound = _SIGNATURE.bind(*args, **kwargs)
    bound.apply_defaults()
    values = dict(bound.arguments)
    values.pop('trace', None)
    planner = values.pop('forward_planner')
    payload = {'schema_version': SCHEMA_VERSION, 'digest': describe_search_inputs(args, kwargs)['digest'],
               'context': json_safe(context),
               'forward_planner': {'function': _callable_name(getattr(planner, 'func', planner)),
                                   'keywords': dict(getattr(planner, 'keywords', {}))},
               'arguments': {name: list(value) if isinstance(value, (array.array, tuple)) else value
                             for name, value in values.items()}}
    encoded = json.dumps(payload, allow_nan=False).encode()
    with open(path, 'xb') as stream, gzip.GzipFile(fileobj=stream, mode='wb') as zipped:
        zipped.write(encoded)
    return payload['digest'], len(encoded)
