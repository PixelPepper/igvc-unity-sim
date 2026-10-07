---
id: T-0066
title: Implement explicit clock-bound latency estimators behind a shared interface
status: ready
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0066-latency-estimators-opus
base: 6e866970f285b6a8602d14eac5e415a8156fa665
candidate: none
claim: none
lease: none
updated: 2026-10-06
---

# Packet

ONLY INTERACTIVE user-started session interactive-opus-t0066-20261006, same
actual Claude session as T0065. ACK alias/exact claude-opus-5-5 before work.
T0065 ended/integrated. Worktree C:/Users/brand/.codex/worktrees/igvc-t0066-latency-estimators/IGVC SIM,
branch/base above. One reserved slot; no headless duplicate.
Read README intro, this packet, T0064 final reviews/decision and T0065 handback.

Implement ONLY NEW tools/latency_estimators.py and NEW
tools/tests/test_latency_estimators.py. Pure standard-library module with no
runtime imports/callers yet. Do NOT edit current latency_compensation, sensor_course,
dataset/classifier, path_entry, profile/Unity, reporting, ROS, original tests or
other worktrees. Root owns later runtime integration. Stop with blocker if larger
scope is needed. No primary integration or live A/B approved by this packet.

Objective: resolve T0064's missing common estimator interface and honest variant
identity, independently of prediction/recovery/safety arithmetic. Existing legacy
implementation remains intact. Reviewed candidate reference f41aeeb (read by
git show f41aeeb:tools/latency_compensation.py) supplies odometry EMA/sample rules;
primary supplies lower-quartile/window arithmetic. Do not copy unrelated helpers.

Provide explicitly selected estimator kind (no silent fallback), with defaults
EMA initial0.6s/alpha0.3 and lower-quartile initial0.3s/window20; max_latency1.2s.
Common observe_admission interface receives BOTH odometry header stamps and local
monotonic submit/admission times, plus admission sample receipt time. Separate
named scalar arguments or immutable record, document units. No pose/course/grid
inputs. EMA uses only (entry_stamp-planning_stamp)*1e-9; quantile uses only
admission_wall-submit_wall. No retiming or converting one clock into the other.

Common admission-sample gate matches candidate: missing/invalid/non-int stamps
(bool excluded), same stamp, backwards stamp, invalid/negative/stale receipt age
reject with explicit reasons and no estimator-value update. Default max_age0.25s,
same allowed constructor limits as candidate. Wall estimator additionally rejects
missing/nonfinite/negative submit-to-admission duration (zero duration allowed).
EMA does not require otherwise-unused wall submit time. Both require finite
admission and receipt clocks. Clamp valid intervals above max_latency, count them.
EMA first sample replaces initial then weighted update; quantile last20 accepted
clamped samples and exact sorted[(n-1)//4]. Preserve rejected/clamped/sample counters
with clear semantics. Strict constructor config/type validation, no malformed
boolean-as-number, unknown selection error. Stateless caller config cannot silently
change rules midway. Return accepted interval or explicit no-action per clear API.

Fresh detached JSON-safe identity/report must distinguish algorithm/timebase,
initial/window/alpha/max settings, clock and sample rules. Name quantile estimator
arithmetic separately from the common gated-sample policy: this is NOT the exact
legacy end-to-end experiment, since legacy admitted any finite wall interval and
used different prediction bounds. Explicit sample_policy/version in identity.
No predictor bound claims in estimator-only module. No ranking/performance claims.

Behavior tests: distinct clocks produce different correct estimates; first EMA
sample and subsequent smoothing; exact small-N quantile/order/window eviction;
clamping/counters; all malformed/reset/same/stale/future-receipt cases and no
value updates; quantile invalid submit clock vs EMA unused submit clock; default
and custom identity, strict config/selection, detached reports. Use numeric
expected outcomes and sequences, not mirrored formulas only. No actual logs or
fitting/teacher/replay/live. Preserve all failed outcomes if any.

Worker source edits + ast.parse only, NO tests/imports/providers/delegation/live.
Target6min/USD5 interactive target not billing guarantee; hand back incomplete
at bound rather than silently extend. Commit only owned files; <=300word handback
SHA/API/files/checks NOT RUN/risks. Stop after handback. Root runs focused checks
under all3locks, exact Sonnet source review and Sol evidence review. Any future
predictor port must also retain T0065 branch-based applied semantics (old candidate
planning_context still infers applied by pose inequality; don't reintroduce that).

## Log

### 2026-10-06T20:29:56.7757221-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

INTERACTIVE interactive-opus-t0066-20261006 ONLY. T0065 integrated/closed, new isolated worktree prepared. Implement only unused shared estimator interface and tests; no runtime/primary/source mutation outside owned paths. ACK exact model/session first. One slot reserved pending actual ACK; do not treat listener visibility as receipt.
