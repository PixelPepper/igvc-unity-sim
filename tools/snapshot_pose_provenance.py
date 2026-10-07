#!/usr/bin/env python3
"""Reader-side pose provenance of a recorded navigation decision snapshot.

A snapshot's input robot_xy/robot_yaw is the planning pose. With latency
compensation applied that pose is predicted, not measured, so offline tools that
pair it with measured trajectory history must know which one they hold. This
module only classifies; it never rewrites metadata or snapshot inputs.

Kinds:
  measured        metadata says compensation was not applied and measured,
                  planning and input poses are identical.
  predicted       compensation applied (enabled) and the input pose is the
                  planning pose. It may equal the measured pose at zero motion.
  unknown_legacy  the snapshot has no metadata or no latency_compensation key.
                  A missing flag is never read as measured.
  malformed       metadata is present but has the wrong shape or type, is
                  non-finite, contradictory or does not match the input pose.
"""
import math

MEASURED = 'measured'
PREDICTED = 'predicted'
UNKNOWN_LEGACY = 'unknown_legacy'
MALFORMED = 'malformed'
KINDS = (MEASURED, PREDICTED, UNKNOWN_LEGACY, MALFORMED)


def _finite_number(value):
    """True for a non-bool int or float that is finite and within float range."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        # JSON integers are unbounded; one beyond float range is not a pose.
        return math.isfinite(float(value))
    except OverflowError:
        return False


def _pose(value):
    """The original finite (x, y, yaw) values as a tuple, or None.

    Values are not converted: Python compares int and float exactly, whereas
    float() would collapse distinct integers above 2**53 into equal poses.
    """
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None
    if not all(_finite_number(v) for v in value):
        return None
    return tuple(value)


def _input_pose(grid):
    if not isinstance(grid, dict):
        return None
    xy, yaw = grid.get('robot_xy'), grid.get('robot_yaw')
    if not isinstance(xy, (list, tuple)) or len(xy) != 2:
        return None
    return _pose([*xy, yaw])


def _result(kind, reason):
    return {'kind': kind, 'reason': reason}


def classify_snapshot_pose(snapshot):
    """Return {'kind', 'reason'} for one loaded snapshot payload."""
    if not isinstance(snapshot, dict):
        return _result(MALFORMED, 'snapshot_not_object')
    if 'metadata' not in snapshot:
        return _result(UNKNOWN_LEGACY, 'metadata_absent')
    metadata = snapshot['metadata']
    if not isinstance(metadata, dict):
        return _result(MALFORMED, 'metadata_not_object')
    if 'latency_compensation' not in metadata:
        return _result(UNKNOWN_LEGACY, 'latency_compensation_absent')
    context = metadata['latency_compensation']
    if not isinstance(context, dict):
        return _result(MALFORMED, 'latency_compensation_not_object')
    for flag in ('enabled', 'applied'):
        if flag not in context:
            return _result(MALFORMED, f'{flag}_absent')
        if not isinstance(context[flag], bool):
            return _result(MALFORMED, f'{flag}_not_boolean')
    measured = _pose(context.get('measured_pose'))
    if measured is None:
        return _result(MALFORMED, 'measured_pose_invalid')
    planning = _pose(context.get('planning_pose'))
    if planning is None:
        return _result(MALFORMED, 'planning_pose_invalid')
    recorded = _input_pose(snapshot.get('input'))
    if recorded is None:
        return _result(MALFORMED, 'input_pose_invalid')
    # The recorder copies the planning pose into the input, so JSON round trips
    # keep them bit-identical; any difference means the record is inconsistent.
    if planning != recorded:
        return _result(MALFORMED, 'planning_pose_input_mismatch')
    if context['applied']:
        if not context['enabled']:
            return _result(MALFORMED, 'applied_while_disabled')
        return _result(PREDICTED, 'latency_compensation_applied')
    if measured != planning:
        return _result(MALFORMED, 'not_applied_pose_mismatch')
    return _result(MEASURED, 'latency_compensation_not_applied')
