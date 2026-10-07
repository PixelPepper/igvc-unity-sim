---
id: T-0066
title: Implement explicit clock-bound latency estimators behind a shared interface
status: integrated
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0066-latency-estimators-opus
base: 6e866970f285b6a8602d14eac5e415a8156fa665
candidate: fa65b1a73eb0e9a3c97bb92acc03b764a77b0c17
claim: tested
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

### 2026-10-06T20:30:30-07:00 · claude-opus-5-5 → gpt-6-astra · ACK

ACK T-0066, alias interactive-opus-t0066-20261006, model claude-opus-5-5. This is the same interactive session that completed T-0065.
- Worktree: igvc-t0066-latency-estimators, branch codex/t0066-latency-estimators-opus, base 6e86697.
- Files: only NEW tools/latency_estimators.py and NEW tools/tests/test_latency_estimators.py.
- Checks: static ast.parse only.

### 2026-10-06T20:31:49.9393243-07:00 · gpt-6-astra → claude-opus-5-5 · ACK

Actual20:30:30 exactmodel/session ACK received. Sole implementation owner active; no duplicate. Root all3lock inspection completed/released; no simulator session observed. Preparing validation/review wrappers, no execution before committed handback.

### 2026-10-06T20:32:23-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK

Alias interactive-opus-t0066-20261006, model claude-opus-5-5. Commit **4365314** on codex/t0066-latency-estimators-opus, parent 6e86697.

Files:
- NEW tools/latency_estimators.py (stdlib only; nothing imports it)
- NEW tools/tests/test_latency_estimators.py

Only static `ast.parse` was run.

API:
- **`AdmissionSample`** (frozen): `planning_stamp_ns` and `admission_stamp_ns` (int ns, odometry header), plus `submit_wall_s`, `admission_wall_s` and `admission_receipt_wall_s` (local monotonic s).
- **`make_estimator(kind, **config)`**: `kind` must be exactly one of `KINDS`; there is no default or fallback. Unknown kinds raise ValueError; settings the kind doesn't take raise TypeError.
  - `odometry_header_interval_ema`: initial 0.6, alpha 0.3.
  - `wall_submit_admission_lower_quartile`: initial 0.3, window 20.
- **Shared limits:** max_latency 1.2 in (0,5]; initial in [0,max]; max_sample_age 0.25 in (0,1]; alpha in (0,1]; window an int in [1,1000]. Bools and non-finite values are rejected.
- **`observe_admission(sample)` → `Observation(accepted, interval_s, clamped, reason)`.**
  - The shared gate (`gated_admission_sample` v1) rejects, with a counted reason and no value change: missing, non-int or bool stamps; equal stamps; backward stamps; non-finite admission or receipt clocks; future receipts; receipts older than max age.
  - The wall estimator also rejects a missing, invalid or negative submit interval. Zero is accepted.
  - The EMA ignores `submit_wall_s`.
  - Intervals above max are clamped and counted.
  - EMA: the first accepted sample replaces the initial value; later ones are weighted. Quartile: last-window `sorted[(n-1)//4]`.
- **State and reports:** `latency`, `samples`, `clamped_samples`, `rejected_samples`, `rejected`. `identity()` and `report()` return fresh JSON-safe dicts covering kind, timebase, rules, sample policy and the frozen config (`EstimatorConfig`). The quartile identity states it is not the legacy end-to-end experiment. No predictor bounds; no ranking.

NOT RUN:
- `python3 -m unittest tools.tests.test_latency_estimators`

Risks:
- Unused until runtime wiring. Any future predictor port must keep T0065's branch-based `applied`.
- The reason names are new and not yet consumed.
- Float wall subtraction is used as-is, with no rounding.

Stopping.

### 2026-10-06T20:33:16.5109299-07:00 · gpt-6-astra → claude-opus-5-5 · ACK

Actual committed handback received, candidate4365314b4fabc5e5c92ac56b5b5d11d4430a77c7 bound. Assignment ended; read-only now. Root starts focused checks under all3locks and exact Sonnet source review. No runtime callers or integration approved.

### 2026-10-06T20:34:29.7439415-07:00 · gpt-6-astra → claude-opus-5-5 · REVIEW

Firstcandidate4365314:13focusedPASS underall3locks, Sol review/sol-evidence-review.md accepts recorded evidence only. Sonnet review/review.md source PASS with risks,40.5s/USD0.16121. Root source acceptance BLOCKED by packet-contract gaps: finite wall operands can yield inf duration then be clamped/accepted, huge int finite-check/stamp conversion can throw OverflowError, and public config attribute can be replaced despite immutable-config contract. Raw passing record retained; no source integration. Scope/newmodule/clock separation otherwise supported. Identity lists wall-only rejection reasons for EMA, correct alongside revision.

### 2026-10-06T20:34:29.7448863-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

REVISION r1 ONLY INTERACTIVE interactive-opus-t0066-20261006-r1, same actual session. Prior assignment ended. ACK exactmodel/alias. Same isolatedworktree/base, firstcandidate4365314 parent for revision; same TWO owned files only. Fix bounded contract gaps: make constructor config exposed through read-only property/frozen value (normal public config reassignment rejected; not asking to defend deliberate private mutation). Finite-number validation handles huge Python ints without OverflowError; constructors return documented ValueError for invalid/unrepresentable numeric config. Check derived interval and receipt-age arithmetic for finite representability: invalid/nonfinite/overflow intervals rejected with explicit reason/counter BEFORE clamp or estimator updates. EMA ignores unused submit time as before. Preserve legitimate finite above-max clamping and ordinary exact arithmetic. Split common rejection-policy identity from algorithm-specific reasons so EMA does not claim rejecting unused wall submit values. Add focused behavior cases: 1e308 minus -1e308 wall interval, huge integer stamp delta/config/clock, read-only config reassignment, correct per-kind identity reasons, unchanged accepted-after-rejection behavior. Do not silently adjust thresholds/window/timebases or runtime. Existing identity shape kind rather than id is retained for explicit later adapter; no generic oldshape compatibility claim.

Source/ast.parse only, no tests/imports/providers/live/delegation. Target6min/USD5 not billing guarantee. Commit own files, handback <=300words actualSHA/API/risks/NOTRUN, stop at handback/bound. Root then revised focusedchecks/newsource review/Sol. No integration/training/live.

### 2026-10-06T20:34:57-07:00 · claude-opus-5-5 → gpt-6-astra · ACK

ACK r1, alias interactive-opus-t0066-20261006-r1, model claude-opus-5-5. Same session and worktree, parent 4365314. Only the two owned files; ast.parse only.

### 2026-10-06T20:35:55.3081477-07:00 · gpt-6-astra → claude-opus-5-5 · ACK

Actual20:34:57 r1 exact-model ACK received. Sole active implementation owner interactive-opus-t0066-20261006-r1. Firstcandidate evidence preserved; do not integrate or use its source before revised handback/review.

### 2026-10-06T20:36:32-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK

r1, alias interactive-opus-t0066-20261006-r1, model claude-opus-5-5. Commit **fa65b1a** on codex/t0066-latency-estimators-opus, parent 4365314. Same two owned files. Only static `ast.parse` was run.

Fixes:
- **Number validation.** `_real()` catches OverflowError, so ints too large for a float count as non-finite.
  - Constructors raise ValueError for huge or invalid config (initial, max, age, alpha, window).
  - Huge int clocks are `invalid_receipt_clock`; a huge submit clock is `invalid_submit_clock`.
- **Arithmetic checked before clamping or updates.** Each new rejection is counted:
  - `invalid_receipt_age` (shared gate): the age is not a finite float, e.g. 1e308 − −1e308 or 10**308 − −10**308.
  - `invalid_odometry_interval` (EMA only): the exact int stamp delta overflows when multiplied by 1e-9.
  - `invalid_wall_interval` (lower quartile only): the wall difference is not finite. inf is now rejected, never clamped.
- **Behaviour preserved.** Legitimate finite above-max clamping and exact arithmetic are unchanged. The EMA still never reads `submit_wall_s`.
- **Read-only config.** `config` is a property over the frozen `EstimatorConfig`. Assigning `est.config = …` raises AttributeError, and field mutation still raises FrozenInstanceError.
- **Identity.** `sample_policy.rejects` = `COMMON_REJECTS` (shared). The new top-level `rejects` lists each kind's own reasons: `EMA_REJECTS` = (`invalid_odometry_interval`,), and the quartile's submit/wall reasons. The EMA identity names no submit or wall reasons. The `kind` key shape is kept; no compatibility claim with the old shape.
- **`REASONS` replaced** by `COMMON_REJECTS`, `EMA_REJECTS` and `LOWER_QUARTILE_REJECTS`.

New tests:
- 1e308 − −1e308 wall interval rejected (the EMA still accepts the same sample);
- overflowing receipt age, both float and int forms;
- huge int clocks, stamp delta, submit and config;
- per-kind identity rejects;
- public config reassignment refused;
- accepted-after-overflow-rejection behaviour, with clamping still counted.

NOT RUN:
- `python3 -m unittest tools.tests.test_latency_estimators`

Risk: `SAMPLE_POLICY_VERSION` stays 1 although the gate gained `invalid_receipt_age`. The version was never released; ASTRA may bump it.

Stopping.

### 2026-10-06T20:37:34.1768132-07:00 · gpt-6-astra → claude-opus-5-5 · ACK

Actual20:36:32 r1 committed handback received; assignment ended. Boundfa65b1a73eb0e9a3c97bb92acc03b764a77b0c17, checks and source review starting. Version1 remains acceptable for unreleased draft with separate immutablecandidateSHA provenance; no historical published identity is overwritten. No source integration yet.

### 2026-10-06T20:39:07.7699488-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION

Accept revisedfa65b1a scoped TESTED claim.19focusedPASS and verified Sol evidence; Sonnetr1 PASS no blockers70.25s/USD0.2275952 (taskSonnettotalUSD0.3888052). First13PASS record retained as insufficient before sourcefix. Config immutable through public API; telemetry counters remain mutable convention, no adversarial-object guarantee. Extra windowcap1000 documented constructor bound, not algorithmqualityclaim. Typed non-AdmissionSample raises TypeError; malformed fields use counted no-action. Identity timebase/units documented even interval string terse. Nonblocking test/description limits retained; do not repeat revision for them.

Root may integrate complete two-commit range6e86697..fa65b1a underall3locks, preserving external/currentruntimehashes, then focusedprimarychecks and finalSolbinding. Module is UNUSED by runtime: integration does not select an estimator, port a predictor, alter live navigation or promote a model. All interactive assignments ended.

### 2026-10-06T20:40:06.2578728-07:00 · gpt-6-astra → claude-opus-5-5 · INTEGRATION

Complete two-commit candidate range integrated aeefe85 then472a7f917534c870b7cb96ba620d151094859a28. Primary19focusedPASS, bothsourcehashes matchfa65b1a,15runtime/externalhashes preserved. FinalSol integration/sol-evidence-review.md accepted fullrange/hash/log/lease binding. Module remains unused; no runtimeestimatorselection, predictionchange, livebenefit orpromotion. Alllocks released, all T0066 assignments ended. First13PASS candidate insufficient before revision retained. No repeatcompletedimplementation/tests/integration withoutnewcause.
