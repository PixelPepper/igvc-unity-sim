"""Named, bounded review checks; no arbitrary command or source edits accepted."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
GROUPS={
 'navigation':['tools.tests.test_observed_navigation','tools.tests.test_path_entry',
               'tools.tests.test_recovery_policy','tools.tests.test_recovery_intent'],
 'perception':['ros2.src.igvc_perception.test.test_surface_projection',
               'ros2.src.igvc_perception.test.test_recorded_lane_projection',
               'ros2.src.igvc_perception.test.test_point_evidence'],
 'integration':['tools.tests.test_sensor_mission_contract','tools.tests.test_sensor_run_audit',
                'tools.tests.test_sensor_telemetry','tools.tests.test_navigation_decisions']}
REPLAYS={'replay-oriented':'oriented-entry-decisions/00131.json.gz',
         'replay-directed':'directed-sweep-decisions/00089.json.gz'}

def main():
    name=sys.argv[1] if len(sys.argv)==2 else ''
    if name not in GROUPS and name not in REPLAYS:raise SystemExit('Unknown bounded check')
    manifest=ROOT/'manifest.json'
    if not manifest.exists():raise SystemExit('Run checks in the frozen baseline, not the live checkout')
    contents=json.loads(manifest.read_text())
    for relative,digest in contents['files'].items():
        if hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=digest:
            raise SystemExit('Baseline drift: '+relative)
    started=time.monotonic()
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    env['PYTHONPATH']=':'.join(str(ROOT/'ros2/src'/p) for p in
        ('igvc_perception','igvc_gps','igvc_sim_bridge'))+':'+str(ROOT/'tools')+':'+env.get('PYTHONPATH','')
    if name in GROUPS:
        r=subprocess.run([sys.executable,'-m','unittest',*GROUPS[name]],cwd=ROOT,env=env,
            text=True,capture_output=True,timeout=120)
        result={'exit_code':r.returncode,'command':['python3','-m','unittest',*GROUPS[name]],
                'output_tail':(r.stdout+r.stderr)[-14000:]}
    else:
        sys.path.insert(0,str(ROOT/'tools'))
        from replay_navigation_decision import load_snapshot,replay
        data,_=load_snapshot(ROOT/'artifacts/checks'/REPLAYS[name])
        r=replay(data)
        plan=r.get('plan')
        result={'exit_code':0,'status':r.get('status'),
            'guidance':r.get('diagnostics',{}).get('guidance'),
            'plan_diagnostics':plan.get('diagnostics') if plan else None,
            'note':'Old recorded observations evaluated with frozen review code; not a live run or necessarily original source revision.'}
    result.update(check=name,wall_seconds=time.monotonic()-started,
        manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest())
    print(json.dumps(result));return result['exit_code']

if __name__=='__main__':sys.exit(main())
