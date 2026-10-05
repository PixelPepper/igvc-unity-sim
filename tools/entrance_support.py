"""Admit memory refresh only with recent observations of both paint supports."""
import math
import numpy as np


def corridor_fresh_support(corridor, evidence_rows, receipt_age_s, max_age_s=1.5):
    """Evidence rows: x,y,z,age_wall_s,count,confirmed,stamp_sec,stamp_nanosec.

    This checks refresh evidence, not collision clearance or lane identity.
    Retained paint remains usable in the obstacle map even when refresh fails.
    """
    result = dict(valid=False, support_counts=[], max_age_s=max_age_s)
    if corridor is None:
        return dict(result, reason='no_corridor')
    try:
        segments = np.asarray(corridor['diagnostics']['segments'], dtype=float)
        points = np.asarray(evidence_rows, dtype=float)
        if (segments.shape != (2,2,2) or not np.isfinite(segments).all()
                or points.ndim != 2 or points.shape[1] != 8 or len(points) > 8000
                or not np.isfinite(points).all() or not math.isfinite(receipt_age_s)
                or receipt_age_s < 0 or receipt_age_s > max_age_s
                or (points[:,3] < 0).any()):
            raise ValueError('invalid_or_stale_evidence')
        recent = points[points[:,3]+receipt_age_s <= max_age_s]
        support_stamps = []
        for a, b in segments:
            delta = b-a
            length = float(np.linalg.norm(delta))
            if length < .5:
                raise ValueError('unsupported_segment')
            direction = delta/length
            along = (recent[:,:2]-a) @ direction
            lateral = np.abs((recent[:,:2]-a) @ np.array([-direction[1],direction[0]]))
            supported = recent[(along >= -.15) & (along <= length+.15) & (lateral <= .22)]
            selected = supported[:,:2]
            unique = np.unique(np.floor(selected/.075).astype(np.int64), axis=0)
            span = float(np.ptp((selected-a) @ direction)) if len(selected) else 0.
            result['support_counts'].append(dict(cells=len(unique), span_m=span))
            support_stamps.append(max((int(p[6])*1_000_000_000+int(p[7]) for p in supported),default=0))
        result['valid'] = all(row['cells'] >= 3 and row['span_m'] >= .5
                              for row in result['support_counts'])
        result['reason'] = 'recent_bilateral_support' if result['valid'] else 'no_recent_bilateral_support'
        if result['valid']:
            result['support_stamp_ns'] = min(support_stamps)
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        result['reason'] = str(exc)
    return result
