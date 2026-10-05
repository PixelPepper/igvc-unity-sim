---
id: T-0029
title: Support explicit held-out seeds in the managed trial runner
status: ready
priority: P2
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0029-managed-seed-opus
base: 2ec0c05e3975e6aa2ebec4c5b30c845a0b770ade
candidate: none
claim: none
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

Pending.

## Log

### 2026-10-05T05:45:34.041347-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
Proceed with light authoring now; honor the T0028 test prerequisite above. This
prepares the existing validation plan without changing the running navigation.
