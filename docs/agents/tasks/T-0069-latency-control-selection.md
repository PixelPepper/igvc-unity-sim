---
id: T-0069
title: Carry explicit latency estimator selection through Python sandbox controls and reports
status: ready
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0069-latency-controls-opus
base: f8b1b543cd51f46385b8d5cb5da9795f88be8d62
candidate: none
claim: none
lease: none
updated: 2026-10-06
---

# Packet

ONLY INTERACTIVE user-started Claude session alias interactive-opus-t0069-20261006,
same actual session as T0068. ACK exact alias/model claude-opus-5-5 before edits.
All previous assignments ended. One reserved slot; no headless duplicate.
Worktree C:/Users/brand/.codex/worktrees/igvc-t0069-latency-controls/IGVC SIM,
branch/base above. Read README intro, this packet, accepted T0068 CLI seams and
latency_estimators.KINDS. Primary coordination only in docs/agents/.

The base includes accepted but UNINTEGRATED T0068 runtime8bf08da plus an exact
three-file external checkpoint f8b1b54. Checkpoint is not source acceptance;
hashes recorded artifacts/agents/T-0069/source-pins.json in PRIMARY. Primary
external files remain untouched. Reviewer must assess whole control diff from
8bf08da, including inherited bool/report changes, not just your final commit.

Own ONLY tools/sandbox_profile.py, tools/sandbox_batch_report.py,
tools/tests/test_sandbox_profile.py, NEW tools/tests/test_latency_control_selection.py.
Do not edit runtime, estimator/helpers, Unity, parallel_batch, launchers, presets,
audit logic or historical files. Source edits + ast.parse only: no tests/imports,
providers, delegation, ROS/Unity/build/live. Root runs checks under all three locks.

1. Add latency_estimator setting, default empty string meaning unspecified.
   Exact choices must derive from latency_estimators.KINDS, not copied arithmetic.
   Require a string and either empty or an exact known kind. Keep strict boolean
   latency_compensation. Enabling requires explicit nonempty selector and
   execution=checked-path. Reject old bool-enabled presets with actionable error;
   never silently migrate or choose an estimator. Disabled old presets remain
   valid; explicitly supplied disabled selector remains recorded.
2. mission_argv passes --latency-estimator whenever explicitly selected, alongside
   --latency-compensation only when enabled. Check actual argv with T0068 parser
   for both choices, disabled defaults, explicit disabled, and invalid settings.
   No change to unrelated profile/controller limits or baseline default args.
3. Batch reports must distinguish requested estimator from recorded run identity.
   Preserve absent historical identity as unknown, never infer old bool=true means
   EMA or quantile. Retain detached actual run latency identity/selection where
   available and explicit mismatch/unknown status. Policy grouping/display must
   not silently pool different estimators or known-vs-unknown variants. Do not
   relabel historical records or change denominators, audit decisions, retry
   accounting, or filtering. Full audit/comparability gate remains separate.
   Rows without a run/startup failures still retain requested selector and unknown
   actual identity. BatchTrial Unity field does not exist yet; handle absent field
   honestly and state that this slice cannot complete Unity plumbing.
4. Add small behavior tests for strict setting types/choices/mode, exact argv into
   real parser, old disabled compatibility/old enabled rejection, both explicit
   estimators including disabled, unknown historical report identity, mismatched
   requested/actual, failed/no-run rows, and distinct grouping. Use temp fixtures
   and mock audit when needed; no actual auditing/training/live. Avoid repeating
   estimator math tests. Existing bool-enable fixture must become explicit.

Do not broaden into analysis of external timing correlation or learned models.
Inherited report disturbance annotation is not causal evidence and must not gain
promotion authority. Preserve all attempts and failures. No course/WORLD/teacher
geometry in runtime policy and no relaxed safety/freshness/footprint/recovery gates.

Target6min/USD5 interactive target, not billing guarantee; hand back honest partial
at bound if needed. Commit owned paths only, <=300word handback with SHA/files/API,
checks NOT RUN and risks, then stop. Root Sonnet source/Sol evidence review.
NO PRIMARY INTEGRATION OR REAL TRAINING/LIVE until subsequent Unity selector slice
and combined checks; no publishing/pushing. Root retains Unity/shared interfaces.

## Log

### 2026-10-06T21:04:39.7009824-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

INTERACTIVE interactive-opus-t0069-20261006 ONLY. T0068 accepted isolated TESTED55PASS and both reviews, not integrated. New worktree includes its candidate and exact three-file external checkpoint for whole-range review. Own Python controls/report paths only; source/ast.parse only, ACK model/session first. No Unity edits or primary integration. Read full packet and hand back bounded commit.

