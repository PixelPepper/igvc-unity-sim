---
id: T-0023
title: Preserve actual failed-backup arguments and bounded rejection stages
status: ready
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0023-recovery-diagnostics-opus
base: 0f76a2ac6090de0cf83c8f57bd471874dbffe552
candidate: none
claim: none
lease: none
updated: 2026-10-05
---

# T-0023: Own recovery failure evidence end to end

## Packet

- ADR011 complete bounded ownership: choose design, implement, test, revise and commit
  without intermediate approval. Existing interactive Opus, own prepared worktree
  C:/Users/brand/.codex/worktrees/igvc-t0005-health-capture/IGVC SIM.
- Read README, knowledge sensor-led-navigation and trial-audit-promotion, task T0022
  accepted diagnosis and artifacts/agents/T-0022/REPORT.md plus comparison.json.
  Exact source inputs: tools/recovery_policy.py select_backup_recovery and
  _accept_continuation; tools/sensor_course.py recovery branch and existing capture
  mechanisms; directly relevant existing tests. Do not load full logs/CAD or WORLD.
- Outcome: a failed legacy backup search must report where and why it returned
  None, and bind those diagnostics to the actual immutable arguments given to the
  worker process. Preserve successful searches' existing motion result.
  Submission-time planner captures are not sufficient recovery provenance.
- Choose a minimal backward-compatible diagnostic transport that works across
  ProcessPoolExecutor. Keep existing select_backup_recovery return contract for
  current callers. Capture actual observed cost grid, pose/frame/stamps, sparse GPS,
  chosen guidance, footprint, forward options, search limits and optional masking/
  trap inputs if applicable; record explicitly unavailable fields rather than infer.
  No course/WORLD geometry. Exact captured arrays/options must match search inputs.
- Bounded diagnostic output: input/validation failure; initial clearance failure;
  blocked rear distance; per-candidate proposal/continuation acceptance or rejection;
  time/expansion exhaustion; actual attempted distances and charged budget.
  Default has five distances. Cap diagnostic payloads, nonfinite-safe JSON and
  bounded capture count; do not log full maps in run.json. Explain costs/overhead.
  Any capture failure must be explicit and must not silently bypass safety gates.
- Owned files: tools/recovery_policy.py; tools/sensor_course.py only recovery
  instrumentation/invocation/report/fingerprints; new tools/recovery_evidence.py
  and tools/tests/test_recovery_evidence.py if useful; directly relevant existing
  recovery tests. No T0021 behavior or recorder changes, ROS interfaces, runner,
  auditor, Unity, profiles, thresholds, planning rules, scoring or motion changes.
- Tests must exercise real branches and transport/serialization where possible,
  comparing original successful/failed return semantics, immutable input binding,
  empty/invalid/unknown/rear-blocked/no-continuation/exhausted cases, diagnostic
  size/nonfinite handling. Do not add source-string tests as evidence of behavior.
  If capture can't prove recovery inputs, state the gap and fix the design.
- T0024 control lap is reserved in DIFFERENT frozen checkout at this same source.
  Light reading/design/source authoring may overlap its exclusive lease; no tests,
  replay or builds until primary
  artifacts/iterations/2026-10-05/replacement-control-1/live.json is finished with
  shutdown_verified=true, OR root explicitly releases this prerequisite.
  Then proceed directly with focused checks without awaiting another permission.
- <=40min active work plus live wait; <=3 focused invocations, no full suite/live/
  Unity build/provider calls/recursive workers. Own-branch commit, bounded report
  and review-inputs.md in primary artifacts/agents/T-0023, <=300word handback with
  exact candidate, tests, overhead and unverified live behavior. No fix/performance
  claim for the failed lap. Stop at handback or genuine boundary.

## Handback

Pending.

## Log

### 2026-10-05T04:51:13.578594-07:00 · gpt-6-astra → all · NOTE
Prepared complete task; await explicit dispatch after branch preparation and
combined integration checks. T0024 is an unchanged-source off-mode control.

### 2026-10-05T04:52:12.506981-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
T0021 is integrated and all610 combined tests pass. Your clean existing worktree
now has codex/t0023-recovery-diagnostics-opus at0f76a2a. Own this entire new
bounded instrumentation slice; choose design and tests without interim approval.
T0024 is starting now in the different frozen checkout. Light authoring permitted;
wait for its verified shutdown before focused tests, then proceed automatically.
Return one completed source candidate or a supported boundary, not a design-only
handoff. Do not weaken behavior/limits or claim to fix the failed lap.

### 2026-10-05T04:52:22-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
T-0023 accepted on codex/t0023-recovery-diagnostics-opus at 0f76a2a. Reading and authoring only until replacement-control-1 live.json is finished with shutdown_verified=true.
