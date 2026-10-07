---
id: T-0067
title: Connect explicit estimators to guarded prediction and measured admission helpers
status: ready
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0067-guarded-prediction-opus
base: 472a7f917534c870b7cb96ba620d151094859a28
candidate: none
claim: none
lease: none
updated: 2026-10-06
---

# Packet

ONLY INTERACTIVE user-started session interactive-opus-t0067-20261006,
same actual Claude session as T0066. ACK alias/exact claude-opus-5-5 first.
Previous assignments ended. Isolated worktree
C:/Users/brand/.codex/worktrees/igvc-t0067-guarded-prediction/IGVC SIM,
branch/base above. One reservedslot; no headlessduplicate.
Read README intro, this packet, T0066 API/handback and T0065 provenance contract.

Own ONLY NEW tools/guarded_latency_compensation.py and NEW
tools/tests/test_guarded_latency_compensation.py. Do not edit estimator module,
legacy latency_compensation, sensor_course or existing tests. This is a pure
adapter/predictor slice with NO runtime callers, CLI/profile/Unity changes or
integration authorized yet. Root assigns runtime wiring separately after review.

Use reviewed candidate f41aeeb:tools/latency_compensation.py as reference for
OdometrySample, checked-path mode gate, horizon/prediction, planning context,
frozen inputs, heading rebase and measured admission helpers. Port relevant pure
logic deliberately, not the older checkout wholesale. Compose accepted current
latency_estimators.make_estimator/AdmissionSample; no copied estimator arithmetic.

Implement guarded compensator with explicit estimator_kind (required argument;
no default/fallback), strict bool enabled, validated provisional bounds matching
f41aeeb: shift1m (0,2], yaw0.6rad (0,pi/2], sample-age0.25s (0,1]. Estimator
config is passed explicitly; preserve per-kind defaults via factory. Sharing
receipt-age setting must not allow predictor vs estimator freshness divergence.
Use immutable whole-message OdometrySample holding pose, twist, headerstamp and
local receipt. No course/grid geometry in prediction. No wall/header conversion.

planning_context(sample, measured_pose, now) returns planning pose and detached
metadata. Disabled always returns the identical measured pose. Enabled prediction
requires a valid finite whole sample, pose exactly matches measured pose, and
finite receipt age within the unchanged bound. Missing/malformed/stale/future
sample yields measured pose and counted explicit no-action reason; never retime.
Reject malformed measured pose explicitly rather than fabricate finite values.
Nonzero valid twist predicts constant unicycle motion with horizon
min(estimate, max_shift/abs(v), max_yaw/abs(w)), preserving candidate thresholds
and stable small-turn handling. No end-pose scaling in this new variant. Zero
twist returns measured; nonzero twist at zero horizon is still applied=True.
Set applied from actual branch execution, NEVER pose equality (fix known older
candidate flaw). Context fields enabled/applied/measured_pose/planning_pose must
pass canonical classifier after JSON roundtrip. Identity names estimator AND
new guarded prediction/sample policy, not legacy equivalence or safety proof.

Observe admission through the new explicit BOTH-clock AdmissionSample interface:
planning and entry stamps, entry receipt, now and submitted_at. Keep entry sample
freshness rejection and estimator counters. Require the caller to supply submit
time explicitly; EMA may ignore it per estimator API. Do not substitute receipt
time or odometry interval for missing wall submit time. Preserve rejected/no-action
outcomes in reports. Reports/context fresh copies, and config not publicly mutable.

Pure admission wrapper must call injected existing admit function exactly once
with ACTUAL entry pose, latest observed grid and original footprint. Return its
admitted result/diagnostics unchanged. Prediction may appear in provenance only,
never replace admission, recovery, costmap or memory pose. Sample after every
admission attempt, including rejection. If entry pose does not match its sample,
skip sampling with explicit provenance; do not claim a coherent timing sample.
Copy/report actual arguments honestly, not reconstruct them from predicted data.

Port frozen_planner_inputs and rebase_heading_hint semantics as needed: preserve
all observed arrays/fields and only predicted robot_xy/yaw; rebase pose-relative
heading-only hint entry, leave world-anchored hint and underlying memory untouched.
Keep execution_mode_error requiring checked-path when enabled. No runtime input
schema or admission/collision logic changes. Never loosen guards to pass tests.

Behavior tests with both estimator kinds: distinct-clock estimate into correct
bounded prediction; stale/future/mismatched/malformed sample skip; disabled identity;
zero-horizon applied semantics; JSON classifier/detachment; translation/yaw caps
including fast rotation; spy admission sees actual pose/grid/footprint once with
identical returned result, including rejected admission; correct submit/receipt
clock forwarding and mismatch no-sample; frozen field pass-through and heading
rebase without mutating input. Use real estimator, injected admission spy, numeric
expected outcomes. No live ROS, historical replay, teacher or training.

Source edits + ast.parse only, NO tests/imports/providers/delegation/live/builds.
Target6min/USD5 interactive target not billing guarantee. If incomplete at bound,
hand back partial honestly, no hidden extension. Commit owned files only; handback
<=300words SHA/API/files/NOTRUN/risks. Stop at handback/blocker. Root focused
checks underall3locks, exact Sonnet source review and Sol evidence review follow.

## Log

### 2026-10-06T20:39:54.8829899-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

INTERACTIVE interactive-opus-t0067-20261006 ONLY. New isolated base includes accepted estimator revision and root19PASS integration; final integration evidence review pending independently. Previous T0066 assignments ended. Own only new pure adapter/predictor and tests, no runtime caller or live work. ACK exact model/session first; posting is not assumed delivery.
