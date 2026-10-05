"""Bounded, asynchronous recording of the exact observed planner inputs.

Snapshots (``NNNNN.json.gz``, schema_version=1) hold replay inputs only. The
per-decision outcome (``outcomes.jsonl``, schema_version=2) joins the robot's
own choice, candidates, admission and action result by the same index. Both
contain only what the robot observed or decided; no course/world data.
"""
import gzip
import json
import math
from pathlib import Path
import queue
import threading

OUTCOME_FILE = 'outcomes.jsonl'
OUTCOME_ACTIONS = ('accepted', 'rejected', 'succeeded', 'aborted', 'canceled', 'not_sent')
# action_msgs/GoalStatus terminal codes.
_TERMINAL_STATUS = {4: 'succeeded', 5: 'canceled', 6: 'aborted'}
# Mirrors sensor_route_policy.ROUTE_FEATURE_KEYS (kept literal: no planner import here).
ROUTE_FEATURE_NAMES = ('score', 'weighted_cost', 'path_length_m', 'local_path_length_m',
    'endpoint_progress_m', 'remaining_m', 'body_risk', 'heading_change_rad', 'abs_turning_rad',
    'target_bearing_error_rad', 'lateral_mean_m', 'lateral_max_abs_m', 'endpoint_lateral_m',
    'side_sign', 'min_lethal_clearance_m', 'left_clearance_m', 'right_clearance_m',
    'min_unknown_clearance_m', 'unknown_fraction_end', 'unknown_fraction_ahead',
    'lethal_fraction_ahead', 'hazard_cells_vs_chosen')


def compact_event_metadata(metadata):
    """Keep replay arrays on disk while retaining provenance in ROS events."""
    result = {key:value for key,value in metadata.items() if key != 'memory_refresh_input'}
    evidence = metadata.get('memory_refresh_input')
    if evidence is not None:
        result['memory_refresh_input_summary'] = dict(rows=len(evidence['evidence_rows']),
            receipt_age_wall_s=evidence['receipt_age_wall_s'])
    return result


class DecisionRecorder:
    def __init__(self, directory, capacity=8, outcome_capacity=64):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=False)
        self.pending = queue.Queue(maxsize=capacity)
        self.saved = 0
        self.dropped = 0
        self.errors = []
        self.worker = threading.Thread(target=self._write, daemon=True)
        self.worker.start()
        # Small outcome lines get their own bounded queue so large snapshots
        # never crowd them out; the planning loop only ever does put_nowait.
        self.outcome_pending = queue.Queue(maxsize=outcome_capacity)
        self.outcomes_saved = 0
        self.outcomes_dropped = 0
        self.outcome_errors = []
        self.outcome_worker = threading.Thread(target=self._write_outcomes, daemon=True)
        self.outcome_worker.start()

    def submit(self, sequence, inputs, metadata):
        """Caller owns a detached snapshot; never enqueue mutable live caches."""
        payload = dict(schema_version=1, input=inputs, metadata=metadata)
        try:
            self.pending.put_nowait((sequence, payload))
            return f'{sequence:05d}.json.gz'
        except queue.Full:
            self.dropped += 1
            return None

    def submit_outcome(self, record):
        """Queue one schema_version=2 outcome line; never blocks the caller."""
        try:
            self.outcome_pending.put_nowait(record)
            return True
        except queue.Full:
            self.outcomes_dropped += 1
            return False

    def _write(self):
        while True:
            item = self.pending.get()
            try:
                if item is None:
                    return
                sequence, payload = item
                path = self.directory / f'{sequence:05d}.json.gz'
                with path.open('xb') as stream:
                    with gzip.GzipFile(fileobj=stream, mode='wb') as zipped:
                        zipped.write(json.dumps(payload, allow_nan=False).encode())
                self.saved += 1
            except (OSError, ValueError, TypeError) as exc:
                if len(self.errors) < 8:
                    self.errors.append(str(exc))
            finally:
                self.pending.task_done()

    def _write_outcomes(self):
        stream = None
        try:
            while True:
                record = self.outcome_pending.get()
                try:
                    if record is None:
                        return
                    line = json.dumps(record, allow_nan=False, separators=(',', ':'))+'\n'
                    if stream is None:
                        stream = (self.directory / OUTCOME_FILE).open('a', encoding='utf-8')
                    stream.write(line)
                    stream.flush()
                    self.outcomes_saved += 1
                except (OSError, ValueError, TypeError) as exc:
                    if len(self.outcome_errors) < 8:
                        self.outcome_errors.append(str(exc))
                finally:
                    self.outcome_pending.task_done()
        finally:
            if stream is not None:
                stream.close()

    def close(self):
        try:
            self.pending.put(None, timeout=2.)
        except queue.Full:
            self.errors.append('Writer queue did not drain within two seconds')
        self.worker.join(timeout=10.)
        if self.worker.is_alive():
            self.errors.append('Writer shutdown timed out; capture is incomplete')
        try:
            self.outcome_pending.put(None, timeout=2.)
        except queue.Full:
            self.outcome_errors.append('Outcome queue did not drain within two seconds')
        self.outcome_worker.join(timeout=5.)
        if self.outcome_worker.is_alive():
            self.outcome_errors.append('Outcome writer shutdown timed out; outcomes are incomplete')
        return dict(saved=self.saved, dropped=self.dropped, errors=self.errors,
                    directory=str(self.directory), drained=not self.worker.is_alive(),
                    outcomes=dict(file=OUTCOME_FILE, saved=self.outcomes_saved,
                                  dropped=self.outcomes_dropped, errors=self.outcome_errors,
                                  drained=not self.outcome_worker.is_alive()))


def read_outcomes(directory):
    """Return {index: record} from a capture's outcomes.jsonl (later lines win).

    Malformed or non-v2 lines are skipped; a missing file yields {}.
    """
    path = Path(directory) / OUTCOME_FILE
    result = {}
    if not path.exists():
        return result
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if (isinstance(record, dict) and record.get('schema_version') == 2
                    and type(record.get('index')) is int):
                result[record['index']] = record
    return result


def _number(value):
    return float(value) if type(value) in (int, float) and math.isfinite(value) else None


def _point(value, digits=3):
    try:
        values = [_number(v) for v in value]
    except TypeError:
        return None
    return [round(v, digits) for v in values] if values and None not in values else None


def decimate_path(path, limit=60):
    """Keep first/last and evenly spaced interior XY points, at most ``limit``."""
    if not path:
        return None
    points = [_point(list(p)[:2]) for p in path]
    if None in points:
        return None
    if len(points) <= limit:
        return points
    step = (len(points)-1)/(limit-1)
    return [points[round(k*step)] for k in range(limit)]


def _features(source, keys):
    return {key: _number(source[key]) for key in keys if _number(source.get(key)) is not None}


def _route_row(route, keys):
    """Observed-only numeric features of one route proposal (no world data)."""
    return {key: _number(route[key]) for key in keys if _number(route.get(key)) is not None}


def _corridor_entries(lane):
    entries = []
    for candidate in lane.get('accepted_candidates') or []:
        entry = _point(candidate.get('entry'), 4)
        if entry is not None:
            entries.append(entry[:2])
    return entries


def outcome_candidates(diagnostics, plan, limit=32):
    """Admissible alternatives the policies already computed, in the snapshot frame.

    'corridor' entries are lane-pair proposals that passed every detector gate
    (geometric, not collision checked); 'grid' is the route-search endpoint
    that passed the swept-footprint search; 'route_alt' entries are other
    route-search endpoints on a different observed side that passed the same
    search and endpoint admission (``sensor_route_policy`` diagnostics). Route
    entries carry the same observed-only feature names plus the distance to
    the nearest accepted lane-corridor entry. Observed-only by construction.
    """
    candidates = []
    lane = (diagnostics or {}).get('lane_detection') or {}
    for candidate in lane.get('accepted_candidates') or []:
        entry, direction = _point(candidate.get('entry'), 4), _point(candidate.get('direction'), 6)
        if entry is None:
            continue
        endpoint = entry + ([round(math.atan2(direction[1], direction[0]), 4)] if direction else [])
        candidates.append(dict(endpoint=endpoint, path_length_m=None, score=_number(candidate.get('score')),
            source='corridor', features=_features(candidate, ('gps_alignment', 'confidence', 'distance_m',
                                                              'overlap_m', 'pair_angle_deg', 'heading_dot',
                                                              # present only when a learned corridor re-rank ran
                                                              'learned_regret_m', 'rerank_score'))))
    candidates.sort(key=lambda c: float('inf') if c['score'] is None else c['score'])
    route = (plan or {}).get('diagnostics') or {}
    alternatives = [alt for alt in route.get('route_alternatives') or [] if isinstance(alt, dict)]
    alternatives = alternatives[:max(0, limit-2)]
    candidates = candidates[:max(0, limit-1-len(alternatives))]
    entries = _corridor_entries(lane)
    def lane_proximity(endpoint):
        if not entries or endpoint is None:
            return {}
        return dict(corridor_entry_distance_m=round(min(math.dist(endpoint[:2], e) for e in entries), 4))
    endpoint = _point(route.get('endpoint') or [], 4)
    if endpoint is not None:
        features = _features(route, ('endpoint_progress', 'local_path_length', 'checked_continuation_length',
                                     'destination_yaw_error_rad', 'body_clearance_weighted_risk',
                                     'expanded_cells'))
        features.update(_route_row(route.get('route_features') or {}, ROUTE_FEATURE_NAMES))
        features.update(lane_proximity(endpoint))
        candidates.append(dict(endpoint=endpoint, path_length_m=_number(route.get('path_length')),
            score=_number(route.get('weighted_cost')), source='grid', features=features))
    for alt in alternatives:
        alt_endpoint = _point(alt.get('endpoint') or [], 4)
        if alt_endpoint is None:
            continue
        features = _route_row(alt.get('features') or {}, ROUTE_FEATURE_NAMES)
        features.update(lane_proximity(alt_endpoint))
        entry = dict(endpoint=alt_endpoint, path_length_m=_number(alt.get('path_length')),
            score=_number(alt.get('weighted_cost')), source='route_alt', features=features)
        if alt.get('distinct_by') in ('hazard_side', 'lateral_side'):
            entry['distinct_by'] = alt['distinct_by']
        candidates.append(entry)
    return candidates


class DecisionOutcomes:
    """Join each decision's choice, admission and action result into one v2 line.

    A record is emitted once its progress is known (the next decision, or the
    mission end) and its action is no longer merely 'accepted', or at close.
    Destinations are held only to compute progress and are never written.
    """
    def __init__(self, submit, max_open=64):
        self.submit = submit
        self.max_open = max_open
        self.open = {}

    def begin(self, index, destination_index, robot_xy, destination):
        for record in self.open.values():
            if record['robot_xy_after'] is None:
                self._finish_progress(record, robot_xy)
        self.open[index] = dict(schema_version=2, index=index, destination_index=destination_index,
            plan=dict(endpoint=None, path=None, source=None), candidates=[], search_wall_s=None,
            admitted=None, action='not_sent', robot_xy_after=None, progress_m=None,
            _start=tuple(robot_xy), _destination=tuple(destination))
        self._flush()
        while len(self.open) > self.max_open:
            self._emit(min(self.open))

    def evaluated(self, index, plan, diagnostics, search_wall_s):
        record = self.open.get(index)
        if record is None:
            return
        diagnostics = diagnostics or {}
        source = diagnostics.get('guidance')
        source = source if isinstance(source, str) else None
        if plan is not None:
            goal, yaw = _point(plan.get('local_goal') or []), _number(plan.get('yaw'))
            record['plan'] = dict(endpoint=goal+[round(yaw, 4)] if goal and yaw is not None else goal,
                                  path=decimate_path(plan.get('path')), source=source)
        else:
            record['plan']['source'] = source
        record['candidates'] = outcome_candidates(diagnostics, plan)
        record['search_wall_s'] = _number(search_wall_s)

    def update(self, index, **fields):
        record = self.open.get(index)
        if record is None:
            return
        if 'action' in fields and fields['action'] not in OUTCOME_ACTIONS:
            raise ValueError('Unknown outcome action')
        record.update(fields)
        self._flush()

    def result(self, index, status):
        self.update(index, action=_TERMINAL_STATUS.get(status, 'accepted'))

    def close(self, robot_xy=None):
        for record in self.open.values():
            if record['robot_xy_after'] is None and robot_xy is not None:
                self._finish_progress(record, robot_xy)
        for index in sorted(self.open):
            self._emit(index)

    def _finish_progress(self, record, robot_xy):
        destination = record['_destination']
        record['robot_xy_after'] = _point(robot_xy)
        record['progress_m'] = round(math.dist(record['_start'], destination)
                                     - math.dist(tuple(robot_xy), destination), 4)

    def _flush(self):
        for index in sorted(self.open):
            record = self.open[index]
            if record['robot_xy_after'] is not None and record['action'] != 'accepted':
                self._emit(index)

    def _emit(self, index):
        record = self.open.pop(index)
        record = {key: value for key, value in record.items() if not key.startswith('_')}
        if self.submit is not None:
            self.submit(record)
