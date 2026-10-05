#!/usr/bin/env python3
"""Compare recorded selected approaches with Nav2 paths, without world geometry."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

import numpy as np


def path_distance(reference, actual, spacing=.1):
    """Symmetric sampled distance; different routes are not necessarily unsafe."""
    def resample(points):
        result = []
        for a, b in zip(points, points[1:]):
            n = max(1, math.ceil(math.dist(a, b)/spacing))
            if len(result)+n > 4000:
                raise ValueError('Path too long for bounded comparison')
            result.extend([(a[0]+(b[0]-a[0])*i/n, a[1]+(b[1]-a[1])*i/n) for i in range(n)])
        result.append(points[-1])
        return np.asarray(result)
    if not reference or not actual:
        raise ValueError('Both paths are required')
    a, b = resample(reference), resample(actual)
    # Chunk pairwise work rather than allocate a 4000x4000 distance tensor.
    def nearest(source, target):
        return np.concatenate([np.sqrt(((part[:, None, :]-target[None, :, :])**2).sum(axis=2)).min(axis=1)
                               for part in np.array_split(source, max(1, math.ceil(len(source)/128)))])
    ab, ba = nearest(a, b), nearest(b, a)
    return dict(symmetric_max_m=float(max(ab.max(), ba.max())),
                reference_to_nav_p95_m=float(np.quantile(ab, .95)),
                nav_to_reference_p95_m=float(np.quantile(ba, .95)))


def analyze(history):
    evaluated, requested = {}, {}
    active = None
    comparisons = []
    reasons, guidance = Counter(), Counter()
    transitions = []
    previous_guidance = None
    input_ages = []
    for event in history:
        if event['topic'] == '/mission/decision':
            data = event['payload']
            sequence = data.get('sequence')
            if data.get('phase') == 'requested':
                requested[sequence] = data
            elif data.get('phase') == 'evaluated':
                evaluated[sequence] = data
                diagnostics = data['diagnostics']
                mode = diagnostics['guidance']
                guidance[mode] += 1
                reasons[diagnostics.get('lane_detection', {}).get('reason', 'not_requested')] += 1
                input_ages.append(data['input_age_wall_s'])
                if mode != previous_guidance:
                    transitions.append(dict(sequence=sequence, guidance=mode, pose=data['pose'],
                                            odom_stamp_ns=data['odom_stamp_ns'],
                                            lane_reason=diagnostics.get('lane_detection', {}).get('reason')))
                    previous_guidance = mode
            elif data.get('phase') == 'sent_goal':
                active = dict(event=data, evaluated=evaluated.get(sequence), matched=False)
            elif data.get('phase') == 'mission_end':
                active = None
            elif (data.get('phase') == 'action_result' and active
                  and data.get('goal_id') == active['event']['goal_id']):
                active = None
        elif event['topic'] == '/plan' and active and not active['matched']:
            sent, evaluated_event = active['event'], active['evaluated']
            if not evaluated_event or not evaluated_event.get('plan') or event.get('truncated'):
                continue
            actual = [p['position'][:2] for p in event['poses']]
            reference = evaluated_event['plan']['path']
            if (not actual or event.get('frame_id') != 'odom'
                    or event.get('acquisition_stamp_ns') is None or sent.get('odom_stamp_ns') is None
                    or event['acquisition_stamp_ns'] < sent['odom_stamp_ns']
                    or not 0 <= event['received_monotonic_s']-sent['monotonic_s'] <= 3.
                    or math.dist(actual[-1], sent['goal']) > .5):
                continue
            # Navigation started from a later moving pose. Compare only reference
            # from its nearest sample to the actual start, not the old path tail.
            offset = min(range(len(reference)), key=lambda i: math.dist(reference[i], actual[0]))
            if len(reference)-offset < 2 or math.dist(reference[offset], actual[0]) > .5:
                continue
            comparison = dict(sequence=sent['sequence'], goal_id=sent['goal_id'],
                matched_by='endpoint_and_acquisition_time_not_path_goal_uuid',
                start_offset_m=math.dist(reference[offset], actual[0]),
                input_age_wall_s=evaluated_event['input_age_wall_s'],
                nav_stamp_ns=event['acquisition_stamp_ns'],
                **path_distance(reference[offset:], actual))
            comparisons.append(comparison)
            active['matched'] = True
    return dict(schema_version=1, evaluated_decisions=sum(guidance.values()),
                guidance_counts=dict(guidance), lane_rejection_counts=dict(reasons),
                guidance_transitions=transitions,
                input_age_wall_s=None if not input_ages else dict(
                    median=float(np.median(input_ages)), p95=float(np.quantile(input_ages,.95)), max=max(input_ages)),
                matched_paths=comparisons,
                limitations='Path matching uses endpoint/time because nav_msgs/Path has no action UUID. '
                    'Differences may be valid replanning, not proof of collision or wrong course intent. '
                    'Sparse camera capture is not full-rate sensor replay.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--episode', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with (args.episode/'history.jsonl').open() as stream:
        report = analyze(json.loads(line) for line in stream)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    print(json.dumps({k:v for k,v in report.items() if k not in ('matched_paths','guidance_transitions')}))


if __name__ == '__main__':
    main()
