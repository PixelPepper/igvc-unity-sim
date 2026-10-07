#!/usr/bin/env python3
"""Shared pose-provenance admission for learning datasets (offline only).

A decision's snapshot input pose is the planning pose; with latency compensation
it is predicted rather than measured. Datasets admit decision groups by the
canonical tools/snapshot_pose_provenance classification of that snapshot:

  measured        always admitted
  predicted       only with allow_predicted
  unknown_legacy  only with allow_unknown_legacy (snapshots without the
                  metadata, and dataset rows built before pose_source existed:
                  reason ``dataset_row_unlabelled``)
  malformed       never admitted
  unavailable     never admitted (snapshot missing, unreadable or not schema 1)

Admission is per decision group and happens before any cardinality or
heuristic filter: a group is dropped whole when any member's kind is not
allowed or its members disagree on kind. Dropped groups are counted, never
replaced. This module does not rewrite snapshots, rows or values.

API for builders and later readers:
  PosePolicy(allow_predicted=False, allow_unknown_legacy=False)
  load_snapshot_provenance(path) -> (snapshot or None, {'kind', 'reason'})
  row_provenance(row)            -> {'kind', 'reason'} of a built dataset row
  admit_group(provenances, policy) -> (True, None) or (False, reason)
  filter_rows(rows, policy)      -> (kept rows, counts)
  PoseCounts, merge_counts       -> group/member/provenance counts with their semantics
"""
from dataclasses import dataclass
import gzip
import json
from pathlib import Path
import sys

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
from snapshot_pose_provenance import (  # noqa: E402  (canonical classifier, used unchanged)
    KINDS as SNAPSHOT_KINDS, MALFORMED, MEASURED, PREDICTED, UNKNOWN_LEGACY, classify_snapshot_pose)

UNAVAILABLE = 'unavailable'
POSE_KINDS = SNAPSHOT_KINDS+(UNAVAILABLE,)
DATASET_ROW_UNLABELLED = 'dataset_row_unlabelled'
SNAPSHOT_SCHEMA = 1


@dataclass(frozen=True)
class PosePolicy:
    """Which pose kinds a dataset admits. Measured always; malformed/unavailable never."""
    allow_predicted: bool = False
    allow_unknown_legacy: bool = False

    @property
    def allowed(self):
        return frozenset((MEASURED,)+((PREDICTED,) if self.allow_predicted else ())
                         +((UNKNOWN_LEGACY,) if self.allow_unknown_legacy else ()))

    def to_dict(self):
        return dict(allowed=sorted(self.allowed), allow_predicted=self.allow_predicted,
                    allow_unknown_legacy=self.allow_unknown_legacy)


def _provenance(kind, reason):
    return {'kind': kind, 'reason': reason}


def load_snapshot_provenance(path):
    """(snapshot, provenance) of one NNNNN.json.gz; snapshot is None when unavailable."""
    try:
        with gzip.open(path, 'rt', encoding='utf-8') as stream:
            snapshot = json.load(stream)
    except FileNotFoundError:
        return None, _provenance(UNAVAILABLE, 'snapshot_missing')
    except (OSError, EOFError, UnicodeDecodeError, ValueError):
        return None, _provenance(UNAVAILABLE, 'snapshot_unreadable')
    if not isinstance(snapshot, dict) or type(snapshot.get('schema_version')) is not int \
            or snapshot['schema_version'] != SNAPSHOT_SCHEMA or not isinstance(snapshot.get('input'), dict):
        return None, _provenance(UNAVAILABLE, 'snapshot_invalid')
    result = classify_snapshot_pose(snapshot)
    return snapshot, _provenance(result['kind'], result['reason'])


def row_provenance(row):
    """Provenance recorded on a built row; rows from before pose_source are unknown_legacy."""
    if not isinstance(row, dict) or ('pose_source' not in row and 'pose_reason' not in row):
        return _provenance(UNKNOWN_LEGACY, DATASET_ROW_UNLABELLED)
    kind, reason = row.get('pose_source'), row.get('pose_reason')
    if kind not in POSE_KINDS:
        return _provenance(MALFORMED, 'pose_source_invalid')
    if not isinstance(reason, str) or not reason:
        return _provenance(MALFORMED, 'pose_reason_invalid')
    return _provenance(kind, reason)


def admit_group(provenances, policy):
    """(True, None) when every member's kind is allowed and all agree; else (False, reason)."""
    kinds = [p['kind'] for p in provenances]
    if not kinds:
        return False, 'empty_group'
    for kind in kinds:
        if kind not in policy.allowed:
            return False, f'kind_not_allowed:{kind}'
    if len(set(kinds)) > 1:
        return False, 'mixed_provenance'
    return True, None


BUILDER_SEMANTICS = dict(
    groups='joined decisions (outcome and labels aligned), including decisions with zero candidates of this kind',
    members='PRE-FILTER candidates of this kind per joined decision (route: grid/route_alt; corridor: corridor), '
            'counted before cardinality, guidance, target and finite-cost filters; NOT emitted dataset rows',
    provenance='one snapshot provenance per joined decision; unavailable = snapshot missing, unreadable or not '
               'schema 1 (never admitted)')
ROW_SEMANTICS = dict(
    groups='string row group values; each row with a non-string group is excluded alone as group_invalid',
    members='built dataset rows', provenance='one provenance per row (rows without fields: unknown_legacy)')


class PoseCounts:
    """Group, member and provenance counts by pose kind and reason (JSON-ready via as_dict).

    What a group and a member are is stated by the ``semantics`` passed to
    as_dict: BUILDER_SEMANTICS (decisions, pre-filter candidates) or
    ROW_SEMANTICS (row groups, rows).
    """

    def __init__(self):
        self.kinds, self.reasons = {}, {}
        self.admitted_groups = self.admitted_members = 0
        self.excluded_groups, self.excluded_members = {}, {}

    def record(self, provenances, admitted, reason, members):
        for p in provenances:
            self.kinds[p['kind']] = self.kinds.get(p['kind'], 0)+1
            key = f"{p['kind']}/{p['reason']}"
            self.reasons[key] = self.reasons.get(key, 0)+1
        if admitted:
            self.admitted_groups += 1
            self.admitted_members += members
        else:
            self.excluded_groups[reason] = self.excluded_groups.get(reason, 0)+1
            self.excluded_members[reason] = self.excluded_members.get(reason, 0)+members

    def as_dict(self, semantics, join=None):
        """Counts plus their meaning; ``join`` carries the builder's decisions/joined/mismatched/unlabelled."""
        result = dict(semantics=dict(semantics), provenance_by_kind=dict(sorted(self.kinds.items())),
                      provenance_by_reason=dict(sorted(self.reasons.items())),
                      admitted_groups=self.admitted_groups, admitted_members=self.admitted_members,
                      excluded_groups=dict(sorted(self.excluded_groups.items())),
                      excluded_members=dict(sorted(self.excluded_members.items())))
        if join is not None:
            result['join'] = dict(join)
        return result


def merge_counts(parts):
    """Sum PoseCounts.as_dict() mappings (e.g. per-run stats into a dataset total).

    Integers and nested integer mappings are summed; the ``semantics`` text is
    taken from the parts and must agree.
    """
    total = {}
    for part in parts:
        for key, value in part.items():
            if key == 'semantics':
                if total.setdefault(key, value) != value:
                    raise ValueError('cannot merge pose counts with different semantics')
            elif isinstance(value, dict):
                bucket = total.setdefault(key, {})
                for name, count in value.items():
                    bucket[name] = bucket.get(name, 0)+count
            else:
                total[key] = total.get(key, 0)+value
    return {k: v if k == 'semantics' else dict(sorted(v.items())) if isinstance(v, dict) else v
            for k, v in total.items()}


def filter_rows(rows, policy):
    """Whole-group admission of built rows (for readers); order kept, nothing replenished.

    A group value is used only when it is a string (checked before any hashing):
    rows with a missing, null, numeric, list or dict group, and non-dict rows,
    are excluded one by one as ``group_invalid`` and never admitted.
    """
    groups, order, counts = {}, [], PoseCounts()
    for row in rows:
        key = row.get('group') if isinstance(row, dict) else None
        if not isinstance(key, str):
            counts.record([row_provenance(row)], False, 'group_invalid', 1)
            continue
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(row)
    kept = set()
    for key in order:
        provenances = [row_provenance(r) for r in groups[key]]
        admitted, reason = admit_group(provenances, policy)
        counts.record(provenances, admitted, reason, len(provenances))
        if admitted:
            kept.add(key)
    return ([r for r in rows if isinstance(r, dict) and isinstance(r.get('group'), str) and r['group'] in kept],
            counts.as_dict(ROW_SEMANTICS))
