"""Read-only sampled footprint/barrel and motion audit of a saved course run."""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RADIUS = .2682114


def clearance(x, y, yaw, barrel):
    """Signed circle clearance from an oriented axle-relative rectangle."""
    dx, dy = barrel[0]-x, barrel[1]-y
    c, s = math.cos(yaw), math.sin(yaw)
    bx, by = c*dx+s*dy, -s*dx+c*dy
    return math.hypot(max(-1.1-bx, 0., bx-.6), max(abs(by)-.5, 0.))-RADIUS


def audit(live, route):
    samples = live['trajectory']
    barrels = [b['xy'] for b in route['barrel_instances']]
    if not samples or len(barrels) != 41:
        raise ValueError('Nonempty trajectory and exactly 41 source barrels required')
    minimum = None
    negative_samples = negative_pairs = 0
    gaps, nonincreasing, jumps = [], [], []
    traveled = backward = backward_across_gaps = max_speed = 0.
    reverse_intervals = 0
    per_barrel = [math.inf]*len(barrels)
    for i, sample in enumerate(samples):
        if len(sample) != 4 or not all(math.isfinite(v) for v in sample):
            raise ValueError('Expected finite [simulation stamp seconds, x, y, yaw]')
        stamp, x, y, yaw = sample
        distances = [clearance(x,y,yaw,b) for b in barrels]
        idx = min(range(len(barrels)), key=distances.__getitem__)
        if minimum is None or distances[idx] < minimum['clearance_m']:
            minimum = dict(clearance_m=distances[idx], sample_index=i, sample=sample,
                           barrel_index=idx, barrel_xy=barrels[idx])
        negative_samples += int(distances[idx] < 0)
        negative_pairs += sum(d < 0 for d in distances)
        per_barrel = [min(a,b) for a,b in zip(per_barrel,distances)]
        if not i:
            continue
        previous = samples[i-1]
        dt = stamp-previous[0]
        dx,dy = x-previous[1],y-previous[2]
        distance = math.hypot(dx,dy)
        traveled += distance
        delta_yaw = math.atan2(math.sin(yaw-previous[3]),math.cos(yaw-previous[3]))
        heading = previous[3]+delta_yaw/2
        projected = dx*math.cos(heading)+dy*math.sin(heading)
        event = dict(from_index=i-1,to_index=i,dt_s=dt,displacement_m=distance)
        if dt <= 0:
            nonincreasing.append(event)
            continue
        speed = distance/dt
        if dt > .5:
            gaps.append(event)
            backward_across_gaps += max(0.,-projected)
        else:
            max_speed = max(max_speed,speed)
            backward += max(0.,-projected)
            reverse_intervals += int(projected < -1e-5)
        # A gap alone is not a teleport; excessive displacement rate is separate evidence.
        if speed > 2.5:
            jumps.append(dict(event,implied_speed_mps=speed))
    progress = live.get('audit',{})
    mission_complete = (live.get('status') in ('succeeded','completed','complete')
                        and live.get('completed_waypoints') == 77
                        and live.get('total_waypoints') == 77
                        and progress.get('complete') is True
                        and progress.get('valid') is True
                        and progress.get('ordered_waypoints_visited') == 77)
    sampled_clear = negative_samples == 0
    return dict(status='final' if mission_complete else 'interim_or_incomplete',
                mission_complete=mission_complete, source_status=live.get('status'),
                completed_waypoints=live.get('completed_waypoints'), sample_count=len(samples),
                barrel_count=len(barrels), simulation_time_span_s=samples[-1][0]-samples[0][0],
                footprint=dict(x_min=-1.1,x_max=.6,y_min=-.5,y_max=.5),barrel_radius_m=RADIUS,
                minimum=minimum, negative_clearance_samples=negative_samples,
                negative_clearance_sample_barrel_pairs=negative_pairs,
                per_barrel_minimum_clearance_m=per_barrel,
                sampled_barrel_clearance_passed=sampled_clear,
                observed_chord_distance_m=traveled, backward_projected_distance_m=backward,
                backward_projected_distance_across_gaps_m=backward_across_gaps,
                reverse_intervals=reverse_intervals,
                maximum_speed_between_samples_within_0_5s_mps=max_speed,
                timestamp_gaps_over_0_5s=gaps, nonincreasing_timestamps=nonincreasing,
                displacement_rate_over_2_5mps=jumps,
                final_distance_to_origin_m=math.hypot(samples[-1][1],samples[-1][2]),
                final_yaw_error_rad=math.atan2(math.sin(samples[-1][3]),math.cos(samples[-1][3])),
                full_run_sampled_evidence_passed=(mission_complete and sampled_clear and not gaps
                                                 and not nonincreasing and not jumps),
                limitations='Sampled geometric clearance only, not swept collision detection or contact physics. '
                            'Timestamp gaps leave unobserved motion and are not by themselves evidence of teleportation.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',type=Path,default=ROOT/'artifacts/checks/full-course-live.json')
    parser.add_argument('--route',type=Path,default=ROOT/'artifacts/checks/course-route.json')
    parser.add_argument('--output',type=Path,default=ROOT/'artifacts/checks/full-course-clearance.json')
    args=parser.parse_args()
    raw=args.live.read_bytes()
    report=audit(json.loads(raw),json.loads(args.route.read_text()))
    report['source_sha256']=hashlib.sha256(raw).hexdigest()
    args.output.write_text(json.dumps(report,indent=2))
    print(json.dumps({k:report[k] for k in ('status','completed_waypoints','sample_count','minimum',
         'negative_clearance_samples','backward_projected_distance_m','final_distance_to_origin_m',
         'full_run_sampled_evidence_passed')},indent=2))


if __name__ == '__main__':
    main()
