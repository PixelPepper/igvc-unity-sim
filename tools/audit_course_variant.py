"""Read-only saved-run audit for generated courses; sampled ideal geometry only."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re

from generate_course_variant import body_clearance


def audit(course, run):
    if course.get('schema_version') != 1 or course.get('frame') != 'odom':
        raise ValueError('Expected generated schema 1 course in odom')
    objects = course['obstacles']
    if len({o['id'] for o in objects}) != len(objects):
        raise ValueError('Duplicate obstacle IDs')
    for obj in objects:
        if obj['kind'] not in ('barrel','barricade','pothole'):
            raise ValueError('Unknown obstacle kind')
        if not all(math.isfinite(obj[k]) for k in ('x','y','yaw','length','width','height','depth')):
            raise ValueError('Nonfinite object geometry')
        if obj['width'] <= 0 or obj['length'] <= 0:
            raise ValueError('Positive obstacle extent required')
    samples = run.get('trajectory', [])
    minimum = None
    previous_clearances = None
    swept_minimum = None
    sampled_failures = Counter()
    failed_sample_count = 0
    gaps = []; nonincreasing = []; speed_violations = []
    maximum_dt = maximum_speed = 0.
    for i, sample in enumerate(samples):
        if len(sample) != 4 or not all(math.isfinite(v) for v in sample):
            raise ValueError('Expected finite [simulation seconds,x,y,yaw] trajectory')
        stamp, x, y, yaw = sample
        clearances = [body_clearance((x,y),yaw,obj) for obj in objects]
        hit = False
        for j, distance in enumerate(clearances):
            if minimum is None or distance < minimum['clearance_m']:
                minimum = dict(clearance_m=distance,sample_index=i,stamp=stamp,
                               object_id=objects[j]['id'],kind=objects[j]['kind'])
            # Rectangle intersection returns zero; circles may have negative clearance.
            if distance <= 0:
                hit = True; sampled_failures[objects[j]['kind']] += 1
        failed_sample_count += int(hit)
        if i:
            before = samples[i-1]
            dt = stamp-before[0]; displacement = math.hypot(x-before[1],y-before[2])
            angle = abs(math.atan2(math.sin(yaw-before[3]),math.cos(yaw-before[3])))
            maximum_dt = max(maximum_dt,dt)
            event = dict(from_sample=i-1,to_sample=i,dt_s=dt,displacement_m=displacement)
            if dt <= 0:
                nonincreasing.append(event)
            else:
                speed = displacement/dt; maximum_speed = max(maximum_speed,speed)
                if speed > 2.2+1e-5:
                    speed_violations.append(dict(event,chord_speed_mps=speed))
                if dt > .5:
                    gaps.append(event)
                else:
                    # Nearest endpoint is at most half a segment away when position
                    # and shortest-angle yaw interpolate linearly; 1.3 m bounds body radius.
                    pad = (displacement+1.3*angle)/2
                    for j, distance in enumerate(clearances):
                        bound = min(distance,previous_clearances[j])-pad
                        if swept_minimum is None or bound < swept_minimum['clearance_m']:
                            swept_minimum = dict(clearance_m=bound,from_sample=i-1,to_sample=i,
                                                 object_id=objects[j]['id'],kind=objects[j]['kind'])
        previous_clearances = clearances
    progress = run.get('audit',{})
    total = run.get('total_waypoints')
    complete = run.get('status') == 'completed'
    all_physical = (isinstance(total,int) and total>0 and run.get('completed_waypoints')==total
                    and progress.get('ordered_waypoints_visited')==total
                    and progress.get('ordered_waypoints_required')==total
                    and progress.get('complete') is True)
    audit_valid = progress.get('valid') is True and not progress.get('errors') and not run.get('audit_error')
    status = run.get('sim_status','')
    blocks = re.search(r'\bline_blocks=(\d+)',status)
    run_match = re.search(r'\brun=(\d+)',status)
    line_blocks = int(blocks[1]) if blocks else None
    no_reset = (run.get('run_id') is not None and run.get('run_id')==progress.get('run_id')
                and run_match is not None and int(run_match[1])==run['run_id']
                and not nonincreasing and audit_valid)
    return_distance = math.hypot(*samples[-1][1:3]) if samples else None
    checks = dict(run_completed=complete,all_physical_checkpoints=all_physical,audit_valid=audit_valid,
                  trajectory_present=len(samples)>=2,objects_present=bool(objects),
                  sampled_hazard_clearance=failed_sample_count==0,
                  speed_within_2_2mps=not speed_violations,
                  no_reset_evidence=no_reset,no_audit_gaps=not gaps and not nonincreasing and audit_valid,
                  returned_within_0_35m=return_distance is not None and return_distance<=.35,
                  no_line_guard_interventions=line_blocks==0)
    sampled_passed = all(checks.values())
    swept_passed = swept_minimum is not None and swept_minimum['clearance_m']>0 and not gaps and not nonincreasing
    recovery_events = [e for e in run.get('events',[]) if 'recover' in e.get('message','').lower()
                       or 'backed up' in e.get('message','').lower()]
    return dict(schema_version=1,seed=course.get('seed'),difficulty=course.get('difficulty'),
                passed=sampled_passed and swept_passed,sampled_checks_passed=sampled_passed,checks=checks,
                run_status=run.get('status'),run_id=run.get('run_id'),
                completed_waypoints=run.get('completed_waypoints'),total_waypoints=total,
                object_count=len(objects),object_counts=dict(Counter(o['kind'] for o in objects)),
                sample_count=len(samples),minimum_sampled_clearance=minimum,
                nonpositive_clearance_samples=failed_sample_count,
                nonpositive_sample_object_pairs_by_kind=dict(sampled_failures),
                minimum_conservative_swept_clearance=swept_minimum,
                conservative_swept_clearance_passed=swept_passed,
                conservative_swept_warning=swept_minimum is not None and swept_minimum['clearance_m']<=0,
                maximum_chord_speed_mps=maximum_speed,speed_tolerance_mps=1e-5,
                speed_violations=speed_violations,maximum_sample_dt_s=maximum_dt,
                timestamp_gaps=gaps,nonincreasing_timestamps=nonincreasing,
                final_distance_to_origin_m=return_distance,line_blocks=line_blocks,
                recovery_event_count=len(recovery_events),recovery_events=recovery_events,
                limitations='Ideal sampled geometry, not contact physics or measured instantaneous peak speed. '
                    'Potholes are planar hazards. Box overlaps return zero, circle overlaps can be negative. '
                    'Swept bounds assume linear translation and shortest-angle interpolation between samples; '
                    'negative bounds are conservative warnings, not proof of contact. Gaps leave motion unobserved. '
                    'Reset evidence uses reported run IDs, timestamps and the independent route audit; '
                    'paint compliance uses the last simulator line_blocks counter, not a separate geometric paint audit.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--course',required=True,type=Path)
    parser.add_argument('--run',required=True,type=Path)
    args=parser.parse_args()
    course_bytes=args.course.read_bytes();run_bytes=args.run.read_bytes()
    report=audit(json.loads(course_bytes),json.loads(run_bytes))
    saved_run=json.loads(run_bytes)
    expected_hash=hashlib.sha256(course_bytes).hexdigest()
    runtime_hash=re.search(r'\bcourse_hash=([a-f0-9]{64})\b',saved_run.get('sim_status',''))
    report['checks']['runtime_course_hash_matches'] = bool(runtime_hash and runtime_hash[1]==expected_hash)
    report['passed'] = report['passed'] and report['checks']['runtime_course_hash_matches']
    report.update(course_file=str(args.course.resolve()),run_file=str(args.run.resolve()),
                  course_sha256=hashlib.sha256(course_bytes).hexdigest(),
                  run_sha256=hashlib.sha256(run_bytes).hexdigest())
    output=args.run.parent/'validation.json'
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('passed','checks','minimum_sampled_clearance',
         'minimum_conservative_swept_clearance','maximum_chord_speed_mps','line_blocks')},indent=2))


if __name__=='__main__':main()
