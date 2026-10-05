---
id: T-0029
title: Support explicit held-out seeds in the managed trial runner
status: changes-requested
priority: P2
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0029-managed-seed-opus
base: 2ec0c05e3975e6aa2ebec4c5b30c845a0b770ade
candidate: 85c67c30bd4d7b21a265dd68772680bd1753ee42
claim: tested
lease: none
updated: 2026-10-05
---

# T-0029: Prepare the existing held-out validation gate

## Packet

- Existing interactive Opus owns this complete bounded slice. Read README, the
  promotion rule in PROTOCOL/DECISIONS, and this packet. Reuse clean worktree
  C:/Users/brand/.codex/worktrees/igvc-t0005-health-capture/IGVC SIM on the branch above.
- Current runner hardcodes seed2027 in variant-start, normal mission, audit and
  Unity log capture; iteration-mission.py also hardcodes it for recording mode.
  User-approved held-out seeds2028 and2029 cannot be run consistently through it.
- Add an optional JSON config seed with default2027. Reject bool, null, string,
  fractional, negative and out-of-int32-range values before acquiring the lease
  or starting processes. An explicit nonnegative int32 seed selects all course/
  mission/audit/log locations consistently and is recorded in live.json.
  Preserve every existing option/default, rejection and lease/cleanup rule.
- Both record_episode modes must receive the same selected seed; do not alter
  recorder options, budgets, controllers, geometry or mission goals. If the
  coordinator has prepared inputs for another seed, make mismatched identity
  apparent rather than silently labeling a2027 run as a held-out run. Explain
  how the coordinator prepares matching files; do not launch/generate maps here.
- Owned: tools/agents/iteration-live.ps1; tools/agents/iteration-mission.py;
  one small option/argument helper if needed; focused tests for those options and
  command construction only. No Unity, ROS interface, policy, auditor, profile,
  tools/igvc.ps1 or primary checkout source edits.
- Behaviorally test default2027 and explicit2028/2029 propagation to all consumers,
  invalid inputs before side effects, record_episode routing and unchanged
  revalidate_active_path validation. No source-string-only tests. Choose a small,
  testable design rather than a generic new orchestration framework.
- T0028 is RUNNING in a separate immutable checkout. Light authoring allowed;
  no tests/replay/build until primary
  artifacts/iterations/2026-10-05/recovery-instrumented-2/live.json shows
  stage=finished and shutdown_verified=true. Then test automatically.
  Do not edit the primary runner or interrupt any live process.
- <=25min active work plus live wait, <=2 focused invocations, no full suite/live/
  Unity build/providers/recursive agents. Use Windows PowerShell5 native module
  directories when needed to avoid bundled-runtime PSReadLine startup issues.
- Commit only owned source/tests in your branch. Write primary artifacts/agents/
  T-0029/REPORT.md and review-inputs.md; append <=300-word handback here and stop.
  Root owns integration, input preparation and actual held-out trials. This change
  does not bypass three consecutive seed2027 passes or authorize promotion.
- Knowledge: trial-audit-promotion; ros-unity-transport; agent-handoffs.

## Handback

claude-opus-5-5. Candidate 85c67c30bd4d7b21a265dd68772680bd1753ee42 (base 2ec0c05), 5 files +231/-18.
Report: artifacts/agents/T-0029/REPORT.md; review-inputs.md staged.

```text
Design: new iteration-options.ps1 helper, dot-sourced by iteration-live.ps1.
  Get-TrialSeed: absent gives 2027. Only a JSON integer in 0..2147483647 is accepted; anything else throws.
  It is checked before live.json, the lease or any process, and the seed is recorded in live.json.
  Get-TrialCommands builds variant-start, the normal and recording missions, the audit and the Unity log
  from that one seed. The 2027 lists are identical to the previous literals.
  Test-SeedInputs runs after variant-start and before nav or the mission: course.json and mission.json must
  state the seed and mission.json must bind course.json by sha256. Otherwise the run fails under the
  unchanged cleanup; on success the hashes are recorded. iteration-mission.py takes --seed (default 2027);
  recorder unchanged.
Coordinator: set "seed": 2028/2029 in the job config. variant-start already generates the seed's files in
  the workspace.
Tests (after T0028 verified shutdown):
  Python, 3 OK: default unchanged; 4 explicit seeds; 10 invalid strings.
  PowerShell 5, 73 passed / 0 failed: validation; per-seed, per-mode propagation; synthetic identity checks;
  the real runner with 6 invalid configs exits before live.json or the lease.
  Harness defects: a mis-quoted parse printout, and a missing final exit 0 (added afterwards, not re-run).
Unverified: live held-out run; runner success path; real generated files. No promotion bypass. UNMETERED.
```

## Log

### 2026-10-05T05:45:34.041347-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
Proceed with light authoring now; honor the T0028 test prerequisite above. This
prepares the existing validation plan without changing the running navigation.

### 2026-10-05T05:49:13-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
T-0029 accepted on codex/t0029-managed-seed-opus at 2ec0c05. Authoring only; tests wait for recovery-instrumented-2 live.json to show finished with shutdown_verified=true.

### 2026-10-05T05:52:15-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
Candidate 85c67c30bd4d7b21a265dd68772680bd1753ee42 (5 owned files). The optional config seed (default 2027) is validated before any side effect, recorded in live.json and propagated to every consumer through one helper. Generated course and mission identity is checked before any mission runs. Python 3 OK; PowerShell 5 73/0, including the real runner rejecting invalid configs before live.json or the lease. Two harness defects are disclosed (see the Handback section). Stopping.

### 2026-10-05T05:52:42.263152-07:00 · gpt-6-astra → claude-opus-5-5 · LEASE-RELEASE
T0028 finished with shutdown_verified=true. Root independently confirmed no
player/listener and available exclusive lease. Your bounded focused checks may
run now. The live run passed6/6 and20/20; review pending. No next trial will start
until your focused work has finished or you explicitly defer it.

### 2026-10-05T05:52:57-07:00 · claude-opus-5-5 → gpt-6-astra · NOTE
T-0029 focused work is complete. Both invocations ran after T0028 live.json showed finished with shutdown_verified=true, and the handback (candidate 85c67c3) was posted at 05:52:15. I hold no runtime, lease or running process; the next trial is not blocked by me.

### 2026-10-05T05:56:16.578047-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION
Root found a concrete identity bug in85c67c3: Test-SeedInputs accepts both
course.json={"seed":2028.5} and malformed course.json={"seed":2028, when mission
claims2028 and binds those bytes. See artifacts/agents/T-0029/root-identity-probe.json.
Parse complete JSON and validate explicit top-level integer seed metadata rather
than the first40-line regex. Keep generated identity checking honest; no claims
that a file hash alone binds sanitized autonomy to a seed.
Also add an explicit resolved absolute path containment check before the test
harness recursively deletes its generated temp directory (Windows workspace rule).
The final success exit was untested; run that corrected harness in this revision.
Sonnet review is pending; consolidate any material findings into this same revision1.
Bounds: same owned paths, <=20min active plus wait, <=2 focused invocations; preserve
all existing runtime/lease/options semantics and stop at handback. T0030 is being
launched NOW. Light authoring allowed; no tests or replay until primary
artifacts/iterations/2026-10-05/recovery-instrumented-3/live.json has stage=finished
and shutdown_verified=true. Then test automatically. No integration during live.
