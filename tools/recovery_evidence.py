"""Bounded, ROS-free evidence for the legacy straight-backup recovery search.

`diagnose_backup_recovery` is the module-level (picklable) function submitted to
the existing spawn ProcessPoolExecutor in place of `select_backup_recovery`. In
the worker it fingerprints the arguments it actually received (after pickling),
runs the unchanged search with a stage trace, and returns ``(escape, evidence)``;
the escape object is returned as is. The mission fingerprints what it submitted
with the same function, so equal digests bind the trace to the exact search
inputs. On a failed search the mission defers the full inputs with
`DeferredCapture` and writes them once at cleanup (never into run.json).
Nothing here moves the robot, reads WORLD/course data or changes a safety gate.
"""
import array
from functools import partial
from pathlib import Path
import gzip
import hashlib
import importlib
import inspect
import json
import math
import time
import types

from recovery_policy import select_backup_recovery

SCHEMA_VERSION = 1
MAX_TRACE = 40  # above recovery_policy.TRACE_LIMIT + the terminal record
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


class Unrepresentable(ValueError):
    """An input has no complete, lossless encoding; no digest may be claimed for it."""


def _canonical(value):
    """Complete, lossless canonical form used only for hashing; anything else raises Unrepresentable."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return {'float': repr(value)}
    if isinstance(value, dict):
        if not all(isinstance(k, str) for k in value):
            raise Unrepresentable('non-string mapping key')
        return {'dict': [[k, _canonical(value[k])] for k in sorted(value)]}
    if isinstance(value, tuple):
        return {'tuple': [_canonical(v) for v in value]}
    if isinstance(value, list):
        return [_canonical(v) for v in value]
    if isinstance(value, array.array):
        return {'array': value.typecode, 'sha256': hashlib.sha256(value.tobytes()).hexdigest()}
    if isinstance(value, partial):
        return {'partial': _function_name(value.func), 'args': _canonical(list(value.args)),
                'keywords': _canonical(value.keywords)}
    if callable(value):
        return {'function': _function_name(value)}
    raise Unrepresentable('unsupported input type: '+type(value).__name__)


def _encode(value):
    """Reversible JSON form for captures: keeps tuples, arrays and nonfinite floats exactly."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else {'__float__': repr(value)}
    if isinstance(value, tuple):
        return {'__tuple__': [_encode(v) for v in value]}
    if isinstance(value, list):
        return [_encode(v) for v in value]
    if isinstance(value, array.array):
        return {'__array__': value.typecode, 'values': value.tolist()}
    if isinstance(value, dict) and all(isinstance(k, str) and not k.startswith('__') for k in value):
        return {k: _encode(v) for k, v in value.items()}
    raise Unrepresentable('capture cannot encode '+type(value).__name__)


def _decode(value):
    if isinstance(value, list):
        return [_decode(v) for v in value]
    if isinstance(value, dict):
        if '__float__' in value:
            return float(value['__float__'])
        if '__tuple__' in value:
            return tuple(_decode(v) for v in value['__tuple__'])
        if '__array__' in value:
            return array.array(value['__array__'], value['values'])
        return {k: _decode(v) for k, v in value.items()}
    return value


def _callable_name(function):
    return f'{getattr(function, "__module__", "?")}.{getattr(function, "__qualname__", type(function).__name__)}'


def _function_name(function):
    """Importable module-level function name; lambdas, closures, mocks and other objects are not identifiable."""
    if not isinstance(function, (types.FunctionType, types.BuiltinFunctionType)):
        raise Unrepresentable('callable is not a plain function: '+type(function).__name__)
    name = _callable_name(function)
    if '<' in name:
        raise Unrepresentable('function is not importable by name: '+name)
    return name


def _grid_digest(costs):
    """Lossless sha256 of the cost cells, or raise Unrepresentable.

    ROS OccupancyGrid int8 data hashes as signed bytes. Other cells (floats,
    out-of-range ints) hash by type and repr; the encoding name is part of the digest.
    """
    if costs is None:
        return None
    try:
        return {'cells': len(costs), 'encoding': 'int8',
                'sha256': hashlib.sha256(array.array('b', costs).tobytes()).hexdigest()}
    except (TypeError, ValueError, OverflowError):
        pass
    try:
        cells = list(costs)
    except TypeError as exc:
        raise Unrepresentable('grid is not a sequence') from exc
    if not all(type(v) in (int, float, bool) for v in cells):
        raise Unrepresentable('grid cell is not a number')
    encoded = json.dumps([[type(v).__name__, repr(v)] for v in cells]).encode()
    return {'cells': len(cells), 'encoding': 'typed_repr', 'sha256': hashlib.sha256(encoded).hexdigest()}


def describe_search_inputs(args, kwargs):
    """Effective select_backup_recovery inputs (defaults applied) and their sha256 digest.

    The digest covers every argument completely and losslessly; the description is
    bounded. If any input cannot be encoded so, the digest is None with a reason:
    no binding can then be claimed.
    """
    bound = _SIGNATURE.bind(*args, **kwargs)
    bound.apply_defaults()
    values = dict(bound.arguments)
    values.pop('trace', None)
    costs, continuation = values.pop('costs'), values.pop('continuation_costs')
    try:
        grids = {'costs': _grid_digest(costs), 'continuation_costs': _grid_digest(continuation)}
        canonical = {name: _canonical(value) for name, value in values.items()}
        digest = hashlib.sha256(json.dumps({'grids': grids, 'arguments': canonical}, sort_keys=True,
                                           allow_nan=False).encode()).hexdigest()
        unavailable = None
    except Unrepresentable as exc:
        grids, digest, unavailable = None, None, str(exc)[:MAX_STRING]
    planner = values['forward_planner']
    keywords = planner.keywords if isinstance(planner, partial) else {}
    summary = {name: json_safe(values[name]) for name in (
        'origin_xy', 'resolution', 'width', 'height', 'robot_xy', 'robot_yaw', 'destination_xy',
        'goal_footprint', 'distances', 'max_backup_distance', 'max_search_seconds', 'max_expansions',
        'forward_options', 'trap_regions')}
    summary.update(forward_planner=_callable_name(getattr(planner, 'func', planner)),
                   frozen_guidance=json_safe(keywords.get('frozen_guidance', '<not_a_keyword>')),
                   planner_keywords=sorted(keywords), grids=grids,
                   continuation_masking='none' if continuation is None else 'separate_grid')
    if unavailable is not None:
        return {'digest': None, 'unavailable': unavailable, 'inputs': summary}
    return {'digest': digest, 'inputs': summary}


def _bounded(evidence):
    text = json.dumps(evidence, allow_nan=False)
    if len(text) <= MAX_EVIDENCE_BYTES:
        return evidence
    trimmed = {**evidence, 'trace': [{k: record.get(k) for k in ('stage', 'reason', 'verdict', 'ended_by',
                                                                 'distance_m', 'returned_here') if k in record}
                                     for record in evidence.get('trace', [])],
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
        # The search always ends with exactly one record flagged returned_here; keep it whatever the cap.
        final = trace[-1] if trace and trace[-1].get('returned_here') else None
        kept = trace if len(trace) <= MAX_TRACE else trace[:MAX_TRACE-1]+trace[-1:]
        evidence = _bounded({
            'schema_version': SCHEMA_VERSION, 'search': 'legacy_straight_backup',
            'result': 'escape' if escape is not None else 'none',
            'returned_stage': final['stage'] if final else None,
            'returned_reason': (final.get('reason') or final.get('verdict') or final.get('ended_by'))
                               if final else None,
            'input_binding': json_safe(binding), 'trace': [json_safe(record) for record in kept],
            'trace_records': len(trace), 'worker_wall_s': time.monotonic()-started})
    except Exception as exc:  # noqa: BLE001
        evidence = {'schema_version': SCHEMA_VERSION, 'error': f'{type(exc).__name__}: {exc}'[:MAX_STRING]}
    return escape, evidence


class DeferredCapture:
    """Holds a failed search's exact inputs so the slow capture write runs only at cleanup.

    `defer` is O(1): it keeps references to the frozen argument objects and marks
    the report record deferred, so a failure never blocks the mission's live
    callbacks. `flush` (called once command authority is released and the health
    interval has ended, before the report is saved) writes the capture and updates
    the same report record, including whether the inputs still match the worker's
    digest. Errors are recorded in the record, never raised.
    """

    def __init__(self, writer=None):
        self.writer = writer or write_recovery_capture
        self.pending = []

    def defer(self, path, args, kwargs, context, worker_digest, record):
        if len(self.pending) < MAX_CAPTURES:
            record['capture'] = 'deferred_until_cleanup'
            self.pending.append((path, args, kwargs, context, worker_digest, record))
        else:
            record['capture'] = 'unavailable: capture cap reached'

    def flush(self, clock=time.monotonic):
        pending, self.pending = self.pending, []
        for path, args, kwargs, context, worker_digest, record in pending:
            started = clock()
            try:
                digest, size = self.writer(path, args, kwargs, context)
                record['capture'] = {'file': Path(path).name, 'digest': digest, 'uncompressed_bytes': size,
                                     'matches_worker_digest': digest == worker_digest,
                                     'deferred': True, 'write_wall_s': clock()-started}
            except Exception as exc:  # noqa: BLE001 - recorded in the saved report
                record['capture'] = f'failed: {type(exc).__name__}: {exc}'[:MAX_STRING]


_POSITIONAL = ('origin_xy', 'resolution', 'width', 'height', 'costs', 'robot_xy', 'robot_yaw', 'destination_xy')


def load_capture_inputs(payload):
    """(args, kwargs) rebuilt from a capture payload; the planner function is imported by name."""
    module_name, _, qualname = payload['forward_planner']['function'].rpartition('.')
    function = importlib.import_module(module_name)
    for part in qualname.split('.'):
        function = getattr(function, part)
    planner = payload['forward_planner']
    if planner['partial']:
        function = partial(function, *_decode(planner['args']), **_decode(planner['keywords']))
    arguments = _decode(payload['arguments'])
    kwargs = {name: value for name, value in arguments.items() if name not in _POSITIONAL}
    kwargs['forward_planner'] = function
    return tuple(arguments[name] for name in _POSITIONAL), kwargs


def write_recovery_capture(path, args, kwargs, context):
    """Write the complete search inputs once (gzip JSON, exclusive create); returns (digest, bytes).

    ``context`` holds observation provenance (stamps, frames, ages). The forward
    planner is stored as its importable function name plus partial positional
    arguments and keywords. The capture is refused (Unrepresentable) unless the
    inputs have a lossless digest AND the encoded file, decoded and rebuilt,
    reproduces that exact digest; it never claims a binding it cannot show.
    """
    digest = describe_search_inputs(args, kwargs)
    if digest['digest'] is None:
        raise Unrepresentable('capture unavailable: '+digest.get('unavailable', 'no digest'))
    bound = _SIGNATURE.bind(*args, **kwargs)
    bound.apply_defaults()
    values = dict(bound.arguments)
    values.pop('trace', None)
    planner = values.pop('forward_planner')
    is_partial = isinstance(planner, partial)
    payload = {'schema_version': SCHEMA_VERSION, 'digest': digest['digest'], 'context': json_safe(context),
               'forward_planner': {'function': _function_name(planner.func if is_partial else planner),
                                   'partial': is_partial,
                                   'args': _encode(list(planner.args)) if is_partial else [],
                                   'keywords': _encode(dict(planner.keywords)) if is_partial else {}},
               'arguments': _encode(values)}
    encoded = json.dumps(payload, allow_nan=False).encode()
    replay_args, replay_kwargs = load_capture_inputs(json.loads(encoded))
    if describe_search_inputs(replay_args, replay_kwargs)['digest'] != digest['digest']:
        raise Unrepresentable('capture unavailable: encoded inputs do not reproduce the search digest')
    with open(path, 'xb') as stream, gzip.GzipFile(fileobj=stream, mode='wb') as zipped:
        zipped.write(encoded)
    return digest['digest'], len(encoded)
