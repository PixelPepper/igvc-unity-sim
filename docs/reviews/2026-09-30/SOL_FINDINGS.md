# GPT-6.1 Sol integration review

Model/provider/effort: GPT-6.1 Sol / OpenAI Codex worker / high. Frozen dirty-tree baseline manifest SHA-256: `77f2ebe7ceaa71cb58f9d014a1e3965936ca616b823c8f2485268da79319b1fa` (186 files); all allowlisted hashes verified by both test calls. HEAD alone is not this baseline.

Scope: README, HANDOFF/SOL packets, mission orchestration, recovery intent, decision recording/replay, episode and stopped-costmap capture, geometry judge, integration tests, relevant recovery/replay tests, investigation notes and trial summary. No source changes, sessions, builds or networking. Full historical trajectories, controller-local grids and activation traces are unavailable in this snapshot. Source reads are not tests.

## Ranked findings

1. **P1 — Proven acceptance gap: geometric certification omits sensor health and mission identity.** `tools/audit_sensor_run.py:196,206` sets `passed`/`full_loop_certified` without reading `sensor_health` or comparing `mission_sha256` with the evaluated mission bytes. A valid geometric fixture still certifies with missing health, explicitly failed processing plus a clock reset, or a conflicting mission hash. These are synthetic counterexamples, not live success. Independent destination visits do not establish that the audited mission was the commanded one. Smallest correction: an explicit final acceptance aggregator requiring mission-byte identity and adequate sensor-health evidence over the motion interval; retain geometric evidence separately. Falsifier: all three controls must refuse final acceptance while a fixture carrying valid matching evidence passes. An endpoint health snapshot alone would not prove interval health.

2. **P1 — Supported historical evidence: short-lookahead cannot count as a clean audited trial.** `trial-summary.json:448` records `trajectory_continuous=false`, 1/6 and intent expiry. `tools/audit_sensor_run.py:128,152,177` rejects intervals above 0.5 simulation seconds or nonincreasing timestamps and withholds paint/topology certification. Clear sampled obstacles and interpolated paint do not prove the unobserved motion; interpolation cannot recover a missing trajectory. The compact summary omits offending indices/timestamps, so dropout, clock behavior or another cause remains unproved. Preserve this failure; acquire the exact trajectory and corresponding odometry/event interval before diagnosis. Falsifier: the original bytes reveal no prohibited interval, or a complete separately captured trajectory resolves it under the existing threshold. Do not relax continuity.

3. **P2 — Hypothesis: checked-path admission can age before activation.** `tools/sensor_course.py:533–557` checks the latest pose/grid, then constructs and asynchronously sends the path while the prior action can continue. `wait()` spins for up to five seconds; no second admission binds the checked pose to controller activation. The 0.10 m/0.15 rad thresholds can therefore be exceeded after admission. This is a residual integration risk, not proof of the historical RPP failure. Smallest correction if reproduced: a bounded handoff protocol linking admission, pose and activation, with rejection/replanning after excessive movement. Proposed falsifier: a fake action server varies only acceptance delay while odometry advances; assert that an obsolete connector is withheld. Separately, backup cancellation already waits for the cancel response and terminal result (`:219–227,432`); the integration suite has no behavioral test of rejected cancellation or delayed termination.

4. **P2 — Supported reproducibility limitation: profile provenance is external to mission evidence.** `tools/sensor_course.py:107–117,383` records mission and selected Python hashes, but no effective Nav2 controller/profile hash or installed perception/build identity. The oriented snapshot's recorded mission-orchestrator/planner hashes inspected match this baseline; older trials differ, and wall-limited replay cannot establish original execution. Experimental YAML files are preserved but not cryptographically bound to the running server. Smallest correction: record effective configuration and installed-source identities alongside each run. Falsifier: changing the launch profile produces a distinct bound runtime identity. The preserved-guidance schema correctly limits target/yaw/kind; its offline replay does not replay recovery age, expiry, action ordering or Nav2 motion.

## Actual tests

1. `wsl -d Ubuntu-24.04 -- bash artifacts/reviews/2026-09-30/baseline/tools/agents/review-check.sh integration` — exit 0; 37 tests passed in 17.123 s. Tests cover sparse mission admission, geometric scoring, telemetry and recording, not the asynchronous ROS action lifecycle.

2. Exact targeted negative-control command below — exit **1**, intentionally exposing unmet rejection assertions; all three cases returned `audit_passed=true, full_loop_certified=true`. Evidence is this command and its recorded JSON tool output. No production or baseline files were written.

```powershell
$reviewPython = @'
import copy, hashlib, json
from pathlib import Path
root=Path.cwd()
manifest=json.loads((root/'manifest.json').read_text())
assert all(hashlib.sha256((root/p).read_bytes()).hexdigest()==h for p,h in manifest['files'].items())
from tools.tests.test_sensor_run_audit import SensorRunAuditTests
from tools.audit_sensor_run import audit
fixture=SensorRunAuditTests(); fixture.setUp()
results=[]
for name in ('missing_sensor_health','failed_sensor_health','mismatched_mission_hash'):
    run=copy.deepcopy(fixture.run)
    if name=='failed_sensor_health':
        run['sensor_health']={'processing_health_summary':{'status':'fail','fresh_successful_processing':False},'clock_resets':1}
    if name=='mismatched_mission_hash':
        run['mission_sha256']='b'*64
    report=audit(run,fixture.course,fixture.mission,course_sha256=fixture.hash)
    results.append({'case':name,'expected_full_acceptance':False,'audit_passed':report['passed'],'full_loop_certified':report['full_loop_certified'],'checks':list(report['checks'])})
print(json.dumps({'manifest_sha256':hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest(),'results':results}))
raise SystemExit(1 if any(r['full_loop_certified'] for r in results) else 0)
'@
$reviewPython | wsl -d Ubuntu-24.04 -- bash -c 'source /opt/ros/jazzy/setup.bash; export PYTHONDONTWRITEBYTECODE=1; cd artifacts/reviews/2026-09-30/baseline; python3 -'
```

Next integration step: close the acceptance gap and resolve the missing continuity interval before promoting any trial. The delayed-acceptance test above is the sole proposed additional experiment; no live trial is requested. All six destinations, ordered return, continuous motion, body clearance, speed and sensor evidence remain unmet together. No autonomy, calibration or 2027-compliance claim follows from these tests.
