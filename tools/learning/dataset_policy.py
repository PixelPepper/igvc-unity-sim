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
  PoseCounts                     -> per-run/per-kind decision, row and group counts
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


class PoseCounts:
    """Group, row and member counts by pose kind and reason (JSON-ready via as_dict).

    A member is one provenance: one snapshot per decision in the builders, one row in filter_rows.
    """

    def __init__(self):
        self.decisions, self.reasons = {}, {}
        self.admitted_groups = self.admitted_rows = 0
        self.excluded_groups, self.excluded_rows = {}, {}

    def record(self, provenances, admitted, reason, rows):
        for p in provenances:
            self.decisions[p['kind']] = self.decisions.get(p['kind'], 0)+1
            key = f"{p['kind']}/{p['reason']}"
            self.reasons[key] = self.reasons.get(key, 0)+1
        if admitted:
            self.admitted_groups += 1
            self.admitted_rows += rows
        else:
            self.excluded_groups[reason] = self.excluded_groups.get(reason, 0)+1
            self.excluded_rows[reason] = self.excluded_rows.get(reason, 0)+rows

    def as_dict(self):
        return dict(members_by_kind=dict(sorted(self.decisions.items())),
                    members_by_reason=dict(sorted(self.reasons.items())),
                    admitted_groups=self.admitted_groups, admitted_rows=self.admitted_rows,
                    excluded_groups=dict(sorted(self.excluded_groups.items())),
                    excluded_rows=dict(sorted(self.excluded_rows.items())))


def merge_counts(parts):
    """Sum PoseCounts.as_dict() mappings (e.g. per-run stats into a dataset total)."""
    total = dict(members_by_kind={}, members_by_reason={}, admitted_groups=0, admitted_rows=0,
                 excluded_groups={}, excluded_rows={})
    for part in parts:
        for key, value in part.items():
            if isinstance(value, dict):
                for name, count in value.items():
                    total[key][name] = total[key].get(name, 0)+count
            else:
                total[key] += value
    return {k: dict(sorted(v.items())) if isinstance(v, dict) else v for k, v in total.items()}


def filter_rows(rows, policy):
    """Whole-group admission of built rows (for readers); order kept, nothing replenished."""
    groups, order = {}, []
    for row in rows:
        key = row.get('group') if isinstance(row, dict) else None
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(row)
    counts, kept = PoseCounts(), set()
    for key in order:
        members = groups[key]
        if not isinstance(key, str):
            counts.record([row_provenance(r) for r in members], False, 'group_absent', len(members))
            continue
        provenances = [row_provenance(r) for r in members]
        admitted, reason = admit_group(provenances, policy)
        counts.record(provenances, admitted, reason, len(members))
        if admitted:
            kept.add(key)
    return [r for r in rows if isinstance(r, dict) and r.get('group') in kept], counts.as_dict()
