---
id: T-0032
title: Diagnose and correct observed lane-entry target refusal on held-out course
status: in-progress
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0032-lane-entry-recovery
base: 08e8ca5
candidate: none
claim: none
lease: none
updated: 2026-10-05
---

# T-0032: Complete bounded observation-only improvement

## Packet

- Interactive Opus owns diagnosis through implementation, tests, revisions and
  commit. Read README, sensor-led-navigation concept, this packet and exact
  functions implicated. Reuse clean worker checkout
  C:/Users/brand/.codex/worktrees/igvc-t0005-health-capture/IGVC SIM on assigned branch.
- T0031 first held-out2028 failed1/6 after111.66644577s on f1a6ae4, health1118/0/0,
  audit14/20, zero charged backup. Source policy equals the three seed2027 passes.
  This blocks promotion; no seed resampling or dismissal of the failure.
- Inputs in PRIMARY artifacts/iterations/2026-10-05/heldout-2028:
  run.json, decisions/00065..00075.json.gz and outcomes.jsonl. Use focused fields.
  Final sequence75 recovery_gate_selection has observed_gate_blocked,24 candidates,
  target [28.742126736475125,27.367497531890056], station27.370596; observed station
  span21.605328..28.104849. Pose [28.79001092134225,20.36749232850023,1.73949916369].
  sensor_course raises before diagnose_backup_recovery; no failed-search capture
  exists. Submission captures may differ from latest recovery observations;
  establish binding/limits before claiming an exact reproduction.
- Outcome: explain why observed lane guidance offers a target the checked planner
  cannot reach/admit, and implement the smallest GENERAL observation-only correction
  supported by captured evidence and synthetic behavior tests. You may reject the
  initial hypothesis and choose another within this scope. Prefer a usable observed
  goal ahead with all existing body/corridor/sweep checks; never bypass a blocked
  target, turn unknown into free, or permit blind backup. If no defensible correction
  is supported, hand back diagnosis and minimal missing telemetry recommendation.
- Owned: tools/observed_navigation.py, tools/sensor_course.py only for necessary
  call-site consistency or bounded diagnostic binding, and focused tests for the
  actual affected functions. One small observation helper if necessary. Do not
  touch auditor, course generator, profile, launchers, ROS interfaces, Unity,
  mount parameters, recovery_policy/evidence or primary source.
- NO course.json, generated mission.json, WORLD/reference geometry, route or
  seed-specific coordinate/condition in analysis or policy. Only observed sensor
  costs/paint, pose and sanitized six broad GPS destinations. Preserve footprint,
  forward/curvature checks, freshness/health, backup budgets, speeds and all audits.
- No live simulation or Unity build granted. Runtime is now stopped, so bounded
  offline diagnosis/replay/tests may run. At most25min active work, two revision
  rounds, <=3 focused test/replay commands, no full suite. No provider/delegation.
  Preserve failed results. Source changes need behavioral counterexamples (blocked,
  unknown, no valid target and supported clear target) rather than string tests.
- Hand back clean commit, exact changed paths, concise root cause with evidence
  references, test results, limitations and <=300word summary in this primary task
  log. Coordinator runs both reviews and any explicitly granted live trial.
- Knowledge: sensor-led-navigation; trial-audit-promotion; ros-unity-transport.

## Handback

Pending.

## Log

### 2026-10-05T06:23:00-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
Own this complete bounded slice now. T0031 runtime is stopped and lease released;
offline checks allowed. No live trial active or authorized to this task. Frozen
qualification checkout stays f1a6ae4; do not edit it. Provider usage UNMETERED.

### 2026-10-05T06:22:05-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
T-0032 accepted. Starting the diagnosis from the heldout-2028 run.json, the sequence 65-75 captures and outcomes.jsonl, using observation fields only (no course or mission geometry).

### 2026-10-05T06:22:40.8702254-07:00 · gpt-6-astra → all · NOTE
ACK received. The dispatch heading06:23:00 was prefilled and is approximate; the task file existed before the06:22:05 ACK. This note records actual coordinator time. No live trial will launch while assigned offline checks/replay run.

