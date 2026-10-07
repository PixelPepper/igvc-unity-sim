---
id: T-0060
title: Bind latency estimator identity to candidate reports and pose provenance
status: accepted
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0060-latency-identity-opus
base: 646845e25af6c0b58cd20131addfdbfacdcc6562
candidate: f41aeeb8cc067f6f14e7c6dfee136d75fba06082
claim: tested
lease: none
updated: 2026-10-06
---

# Packet

Sole HEADLESS owner opus-t0060-latency-identity-20261006T1830.
Worktree C:/Users/brand/.codex/worktrees/igvc-t0060-latency-identity/IGVC SIM,
based on reviewed T0053 candidate646845e, NOT current primary. Deliberately extend
candidate only; preserve primary externally authored rolling percentile untouched.
This branch is not ready for primary integration or live promotion. T0056 reserved
interactive session owns only dataset migration design and must not be duplicated.
Read README intro and this embedded packet. Root holds implementation.lock.

Own only tools/latency_compensation.py and new
 tools/tests/test_latency_estimator_identity.py. Do not edit sensor_course,
existing tests, dataset/readers, batch reporter or primary files.

Problem: reports and pose metadata lack explicit estimator identity; the preserved
primary wall-clock 25th-percentile experiment differs from this candidate's
odometry-interval EMA. Naming the difference must not imply either is superior.

Add a stable, JSON-safe estimator identity/configuration description to report(),
planning_context() metadata and admit_from_measured_pose() returned provenance.
Name odometry-header interval EMA explicitly; document EMA alpha, initial horizon,
first accepted sample replacing the initial value, maximum interval/clamping, and
existing prediction model/horizon/yaw/receipt-age bounds. Configuration must reflect
constructor values actually used; clearly separate running estimates/sample counts
from initial configuration. A schema/version or algorithm ID can define fixed
semantics. Choose compact consistent names; preserve every existing field/value.
No algorithm selection toggle, changed defaults, arithmetic, clock, gates, counters,
stationary threshold, sample admission, pose mutation or bound changes. New metadata
must also exist when disabled/skipped so off/on run identities remain inspectable.
Do not infer legacy identity, normalize recorded values, edit historical rows or
silently map the external percentile experiment to EMA. Keep all payloads detached:
mutating an emitted metadata dict must not alter later predictions or metadata.

Tests must exercise public flow: constructor nondefault config, known odometry
interval sequence and first-sample/EMA behavior, rejected/stale input unaffected,
planning/admission/report identity consistency, disabled/skipped cases, JSON roundtrip
and caller-mutation isolation. Assert actual prediction/admission arguments remain
as previously defined. Tests should check behavior, not source strings or constants
alone. Use synthetic sample data only. No course/WORLD/teacher/captured inputs.

No tests/imports/replays/benchmarks/live or providers/delegation during implementation.
Root runs new suite plus existing latency_compensation/sensor_course_latency tests
under all3simulator locks after committed handback; no rerun of unrelated passing
suites. Root supplies fixture files already tracked in base. Sonnet reviews code,
Sol reviews evidence. Return SHA/files/NOT RUN commands and risks <=300words.
Commit only owned files; no docs/primary integration/push.6min/USD5 exactOpus5.5/high,
no automatic provider-error retries or substitution. Stop at handback/blocker.

## Log

### 2026-10-06T18:52:24.789877-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

HEADLESS named session only. Root acquired all3 simulator locks before process/port inspection18:29, found no active Unity/listeners, released. Primary external ownership unchanged. This metadata-only extension starts from646845e to avoid overwriting external primary source; it does not inherit primary T0055/T0057/T0059 integration and must not be promoted as the current runtime.

### 2026-10-06T18:55:27.642888-07:00 · gpt-6-astra → all · HANDBACK

Exact Opus completed150.80s/USD0.6417434, candidatef41aeeb, only two owned files, no tests/imports. Assignment ended. Source adds fresh estimator identity/config dict to reports/planning/admission metadata, copies emitted pose lists, stores initial latency; no estimator selection or runtime arithmetic changes claimed. Primary percentile preserved. Root runs three focused suites underall3locks; Sonnet reviews scope/identity semantics/mutation isolation. This branch remains separate and is not authorized for primary integration.

### 2026-10-06T18:56:47.699681-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0060/review-f41aeeb/sonnet-static-review.md

I read the diff and source only. I ran no tests or imports and made no edits.

**Blockers:** none found.

**Verified against the code**
- The identity matches the actual behavior:
  - The first accepted sample replaces the initial value (`samples == 0`).
  - Later samples use `(1-alpha)*latency + alpha*sample`.
  - Intervals above `max_latency_s` are clamped and counted, not dropped.
  - The interval is the odometry header stamp delta.
  - The horizon formula matches `horizon()`.
- `config` holds the stored floats (`self.initial_latency` is new, `float()`-coerced). It is separate from the running `latency`, `samples` and counters.
- All three surfaces carry `estimator`: `report()`, `planning_context()` and `admit_from_measured_pose()`. The `planning_context` key is built before any skip branch, and provenance sets it unconditionally. Off and skipped runs therefore carry it.
- The diff changes no arithmetic, gates, counters, stationary threshold or admit arguments. `estimator_identity()` returns a fresh dict each call and has no side effects.
- The existing tests I grepped don't compare whole dicts, and `sensor_course.py` only forwards these payloads.

**Risks (low)**
1. The identity doesn't state the `|v|,|w|<.02` no-predict threshold. It also leaves out the rejection rules for equal, backward, invalid and stale stamps. `observe_admission` documents those rules, but the machine-readable v1 identity doesn't.
2. `receipt_age_clock='local_monotonic'` is a claim. The caller supplies `now`, and nothing enforces which clock it is.
3. Provenance `measured_pose` and `planning_pose` are now `list()` copies. For compensator-built contexts the values are unchanged. A hand-built context holding tuples would now come out as lists. A `None` pose would raise `TypeError`. No test covers `planning_pose` aliasing; only `measured_pose` isolation is checked.
4. `provenance['estimator']` comes from the admitting compensator, not from `planning_context['estimator']`. A context from a different compensator would not be flagged.
5. The tests have gaps:
   - They check field presence, not the full pre-existing field values.
   - They don't assert that `predictions`, `skipped` or `max_applied_*` are unchanged around identity calls.
   - The mutation test mostly proves fresh dicts, because provenance never reads `context['estimator']`.
   - I hand-checked the arithmetic (.3, .4, .65, horizon .4, pose 1.24) and it is consistent.

### 2026-10-06T18:56:47.699681-07:00 · gpt-6-astra → gpt-6.1-sol · DISPATCH

Sonnet review complete45.95s/USD0.1581022 exactmodel. Candidate f41aeeb passed31focusedtests, 0.088s suite, exit0 underall3locks; log2e549d8b85ee9f07853d5dc522a8fc8aa1d7ddd5e4f140689f96dfd42f8f4c61. Sol now checks bounded recorded evidence and untouched primary external hashes; no execution. Low-risk limitations recorded: identity v1 leaves some fixed rejection/threshold semantics implicit, callerclock/config consistency relies on existing same-compensator production wiring, no support claim for arbitrary handcrafted contexts. No primary integration or live promotion.

### 2026-10-06T18:57:33.859947-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0060/validation-f41aeeb/sol-evidence-review.md

# T0060 candidate evidence review

Accept focused candidate evidence for `f41aeeb8cc067f6f14e7c6dfee136d75fba06082`, not primary integration or live promotion. Worker HEAD matches and is clean; both recorded source/test hashes match current bytes. All three preserved primary hashes remain unchanged, including the external latency variant and sensor-course source.

The saved log reports 31 tests passing in 0.088 seconds; parent records exit 0, no timeout, 0.344 seconds. Verified log SHA-256: `2e549d8b85ee9f07853d5dc522a8fc8aa1d7ddd5e4f140689f96dfd42f8f4c61`. The command runs the new identity suite plus existing latency and sensor-course helper suites; it does not establish a full 55-test run.

The wrapper takes all three exclusive simulator locks and checks Unity processes plus Windows/WSL listeners. Matching PID 52596 lease records bracket validation, 18:55:38.717–18:55:39.217 PDT.

Sonnet reports no source blockers and metadata-only scope. Remaining limits include identity omissions, an unenforced caller-clock convention, cross-compensator contexts, and incomplete alias/state-preservation coverage. These tests do not establish historical source attribution, runtime fidelity or live benefit. The branch intentionally lacks newer primary T0055/T0057/T0059 changes; integration needs its own validation. Earlier T0053 failures remain separate evidence, not superseded by this run.


### 2026-10-06T18:57:33.859947-07:00 · gpt-6-astra → all · DECISION

Accept f41aeeb as a tested candidate-only metadata extension of646845e. All31 focused tests and both reviews pass; primary external hashes remain unchanged. No primary integration, estimator choice by performance, historical attribution or live promotion follows. Future integration must include the complete T0053 source range plus this metadata commit and separately reconcile the primary changes; this isolated branch is not current primary. All T0060 assignments ended.
