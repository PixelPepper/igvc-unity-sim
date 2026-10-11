---
id: T-0082
title: Define a consistent observation-only finish crossing contract
status: in-progress
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0082-finish-contract-opus
base: 495d4b4fc1342a8b6035b662412a6f254b967f86
candidate: none
claim: none
lease: none
updated: 2026-10-10
---

# T-0082: Finish contract foundation

## Packet

User explicitly requests: "so the robot should only have to cross the line, it
should not have to be on any specific point, please make the change".
This authorizes new finish semantics, superseding the missing authorization in
T0079. External T0079 candidate remains unintegrated; do not edit its worktree or
copy the combined policy/auditor commit. T0070 interactive reservation unchanged.

Named owner opus-t0082-finish-contract-20261010. Isolated worktree
C:/Users/brand/.codex/worktrees/igvc-t0082-finish-contract/IGVC SIM.
Owned paths only: NEW tools/finish_crossing.py, NEW tools/tests/test_finish_crossing.py,
NEW docs/FINISH_CROSSING.md. Source-only; no tests/imports/build/live/providers or
recursive delegation. Current primary live mission must remain untouched.

Implement a small pure, versioned crossing helper and document the exact contract
to support later SEPARATE auditor and runtime-policy tasks (protocol invariant5).
Do not edit auditor, runtime, mission exporter, Unity, or coordination files.
Read tools/sensor_course.py, tools/export_autonomy_mission.py,
tools/generate_course_variant.py, tools/course_judge.py topology_evidence,
tools/audit_sensor_run.py final return and ordered visits, tools/mission_completion.py,
and docs/COURSE_JUDGE.md. These current source files are frozen at the snapshot.

Resolve the T0079 issues: same line center/normal/direction in runtime and audit;
no final 0.4m radius or endpoint-to-origin requirement; final crossing replaces
destination6 only after first5 independently ordered visits; ledger reports the
crossing decision honestly. No startup, stationary, reverse, early or far-off
teleport crossing credit. Preserve full ordered loop, corridor/body/paint/ramp,
identity, continuity, speed, health/freshness and recovery guards.

Runtime must stay observation-only plus existing sanitized broadGPS. No WORLD,
centerline, teacher route or course file consumed by runtime; helper must not
import ROS. Determine from current generator whether the fixture start/finish
line can be specified from public mission origin and fixed ROS+X orientation.
If it cannot, explain precisely instead of silently taking armed heading or
last WORLD tangent as incompatible definitions. The document must identify how
the audit independently establishes the same contract and how old reports retain
legacy semantics. A finish line spans the lane; crossing away from its midpoint
must succeed, while unrelated corridor checks still apply. Define point vs body
reference explicitly using canonical driven-axle base_footprint.

Helper supports deterministic sequential crossing with explicit eligibility,
finite validation, previous/current samples and useful scalar crossing provenance.
Plan-through guidance must not stop at the old goal-radius/min_goal_distance:
document the later runtime slice's observed, guard-preserving strategy.
Tests must exercise offset valid crossing, stationary/reverse/early crossing,
finite invalid inputs, and differing initial/final headings without inventing
live evidence. They are SOURCE ONLY until root runs focused checks under all3
locks after the live session ends. No tests mirroring a formula alone.

Commit only owned3paths. Return <=300words with SHA, changed files, unrun checks,
exact semantics, limitations and next separate slices. Budget exact Opus5.5 high,
USD5,360seconds; no automatic provider retries/substitution. Stop with honest
partial handback if the line identity cannot be established from allowed inputs.

## Log

### 2026-10-10 · gpt-6-astra → claude-opus-5-5 · DISPATCH
Explicit new user authorization recorded. New isolated foundation task, not a
duplicate T0070 or redispatch of T0079. Source snapshot includes9tracked external
edits and DisplayAwake source/meta without primary index changes; .claude and
unrelated untracked proposals excluded. Current interactive mission running;
no heavy tests, process/port checks or integration until leases permit.
