---
id: T-0083
title: Audit a completed lap by ordered finish-line crossing rather than a final point
status: backlog
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0083-finish-auditor-opus
base: 495d4b4fc1342a8b6035b662412a6f254b967f86
candidate: none
claim: none
lease: none
updated: 2026-10-10
---

# T-0083: Independent finish crossing audit

## Packet

Dependent on accepted T0082 foundation, frozen before dispatch. User asks final
line crossing anywhere across the lane, with no final-point arrival requirement.
Separate auditor slice; DO NOT modify runtime or policy in this task.
Isolated worktree C:/Users/brand/.codex/worktrees/igvc-t0083-finish-auditor/IGVC SIM.
Named owner opus-t0083-finish-auditor-20261010.

Owned paths ONLY tools/course_judge.py, tools/audit_sensor_run.py,
tools/tests/test_sensor_run_audit.py, NEW tools/tests/test_finish_crossing_audit.py,
docs/COURSE_JUDGE.md. All other files read-only, especially finish_crossing.py.
Read docs/FINISH_CROSSING.md, helper and existing audit tests first.

Adopt finish-crossing/1 explicitly for new run reports carrying a finish_crossing
block whose contract_version matches. Absence retains legacy point/radius grading;
unsupported/malformed version fails closed, never silently downgrade. Do not
re-audit old live records. New grader independently reconstructs five ordered
GPS radius visits and uses actual trajectory samples after fifth-visit index
as crossing eligibility. Do not trust runtime count, claimed crossing or sample
indices as proof. Validate same fixed origin/+X/3m half-span against WORLD course
and mission frames. Unsupported rotated/narrow/origin-incompatible fixture fails.

For new contract remove final point-distance conditions, replace radius visit6
with a forward crossing after all ordered topology cross-sections and first5
visits. No requirement on final endpoint proximity to origin. Keep start origin
admission, reachable local projection, no branch jumps, all ordered gates and
corridor checks, body/paint/ramp/obstacle sweeps, health, timestamps/identity,
speed and all remaining checks. Topology must require accepted crossing AFTER
the final ordered gate; cannot latch an early crossing then complete gates later.
Document any terminal samples beyond the closed arc safely: stopping after
crossing must not fail solely because the axle moves past the origin, while
all remaining corridor/paint/body checks still apply. Do not add unconditional
projection or skip lateral checks. Final distance retained descriptive only.

Tests: valid complete offset crossing >0.4m away with all required synthetic
evidence and full audit pass; same trajectory failing legacy point semantics;
early/reverse/no crossing, wrong unsupported/malformed version, fixed-line
orientation mismatch, outside-span, skipped ordered gates and first5 destination
miss. Full synthetic audit fixture must actually meet interval-health evidence;
do not repeat old T79 fixture's misleading health claim. Preserve existing
legacy test behavior. No ROS/import/tests/live/build/provider/delegation by worker;
write test source only. Root runs focused checks under all3 locks.

Commit only owned paths and hand back <=300words, SHA, test command UNRUN, risk.
Budget exact Opus5.5 high USD5/360s. No automatic retry/substitution. Stop honest
partial if guard-preserving terminal projection cannot be established.

## Log

### 2026-10-10 · gpt-6-astra → claude-opus-5-5 · NOTE
Prepared dependent auditor packet. Not yet dispatched; T0082 review required.
T0070 reservation and external T0079 candidate untouched.

### 2026-10-10 · gpt-6-astra → team · NOTE
Initial placeholder base failed board validation; replaced with actual current
snapshot identity. Packet remains backlog and will be rebased/frozen on accepted
T0082 candidate before dispatch. No implementation assignment issued.
