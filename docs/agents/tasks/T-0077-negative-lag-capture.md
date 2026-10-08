---
id: T-0077
title: Preserve bounded first-negative raw sensor timestamp observations
status: integrated
priority: P2
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0077-negative-lag-capture-opus
base: 264ace5
candidate: 87d8970fd76b1279fb54dd8826a355a10e26cb97
claim: tested
lease: released
updated: 2026-10-08
---

# T-0077: Bounded negative-lag event capture

## Packet

Only session opus-t0077-negative-lag-20261007 owns implementation in isolated
C:/Users/brand/.codex/worktrees/igvc-t0077-negative-lag/IGVC SIM.
Own ONLY tools/sensor_telemetry.py and NEW tools/tests/test_negative_lag_capture.py.
Base264ace5 has the exact current owned-file preimage; unrelated external dirty
files remain in primary and are out of scope. T0070 interactive ownership unchanged.
Read README.md and this packet, then primary artifacts/agents/T-0076/accepted-summary.md
for interpretation, existing telemetry and focused behavior tests as needed.

Implement one additive, observation-only bounded capture in SensorTelemetry for
the existing five raw streams rgb,rgb_info,depth,depth_info,scan. On a negative
lag already counted by observe(), retain the FIRST64 eligible events across those
five streams; never evict early events. Fixed allowlist, fixed global capacity,
no new dynamic stream identifiers. Record stream, sensor stamp_ns, last received
clock stamp_ns and the SAME monotonic callback time already read by observe().
Strict finite/JSON-safe scalars only; malformed diagnostic-only values must be
counted as capture skips without changing legacy counters or causing new errors.
Use exact bounded integer stamp ranges for diagnostic serialization (0 <= ns <2**63,
strict int, no bool); record no NaN/Inf. No new clock reads or upstream calls.

Expose a detached report section with capacity, captured count, overflow count,
invalid-value skip count and events. Overflow explicitly counts eligible valid
events beyond capacity. Counts cover only allowlisted negative events. Document
exact accounting and whole-telemetry-lifetime scope, no mission interval tagging.
Explain callback-local evidence cannot identify transport/executor/drop/CPU causes
or explain past runs. Do not add histograms, clock-step assumptions or new settings.

Preserve ALL existing health predicates, first-health snapshots, lag percentiles,
negative counters, regression counters, schema version, subscription/QoS, guards
and audit behavior exactly. Do not alter unknown input's legacy behavior; if legacy
code itself already rejects an input that is outside this instrumentation contract.
No catch-all wrapper around pre-existing calculations. No course/teacher inputs.

New behavior tests must cover exact first-event values and same callback time;
positive/zero/unclocked/unknown-stream exclusion; mixed-stream global first64 and
exact overflow accounting; malformed diagnostic skip behavior for legacy-accepted
inputs; detached nested report copies; legacy health and counter invariance under
capture saturation. Avoid implementation-mirroring assertions. Root will run new
tests plus existing test_sensor_telemetry, test_health_failure_capture and
test_mission_health under all3locks. No benchmarks or live runs in this slice.

Source edits and static ast.parse only. NO tests/imports/simulations/builds/providers,
recursive delegation or other-file edits. Commit the two owned paths on assigned
branch. Hand back SHA, paths, unrun checks and risks in <=300words. Bound6min/USD5,
not billing guarantee. Root integrates only after exact Sonnet source review,
focused candidate checks, Sol evidence review and primary binding checks. No push.

## Log

### 2026-10-07T20:09:38.7672681-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

Assign only headless opus-t0077-negative-lag-20261007 to the isolated worktree, source/ast.parse and committed handback only. Base264ace56655b124f6e399bd87ea603beffc016d0; owned telemetry preimage equals primary. Provisioning acquired all3locks before actual Windows/WSL process/port checks, no live IGVC session; nine external tracked preimages pinned and unrelated Unity left alone. Provision locks released. T0070 retains the other reserved slot. Actual provider model/handback must be verified, not inferred from this note.

### 2026-10-08T12:13:57.0514837-07:00 · gpt-6-astra → claude-sonnet-5-5 · HANDBACK

Implementation wrapper reported TimeoutExpired360s after host time advanced fromOct7evening toOct8noon. Preserve original status.json/partial.stdout/stderr, no provider retry. Partial stdout contains a COMPLETE valid JSON result: exact claude-opus-5-5,is_errorfalse,stop_reasonend_turn,costUSD0.8188716,duration_ms57779963. Root recovered handback.md/recovered-status.json without invoking provider again. Normal provider exit code is NOT verified. Clean worktree has committed candidate87d8970fd76b1279fb54dd8826a355a10e26cb97, exactly two owned paths. Assignment ended. Worker reports no tests/imports/ast.parse (tool denied) and unable to read external T76summary; packet/source still available. No causation inferred for the long elapsed interval. Root now performs fresh independent lease checks/tests and source review on the actual committed result; timeout alone is not evidence of missing handback when preserved output contains it. T0070 slot unaffected.

### 2026-10-08T12:16:24.3717453-07:00 · gpt-6-astra → gpt-6.1-sol · REVIEW

Exact Sonnet PASS54.48s/USD0.1560372,no source blockers; root focused WSL validation53PASS/no skips, tests0.058s, source hashes and nine protected preimages unchanged, all3locks held before process/portchecks and released. Source review shorthand lag<0 means legacy else after lag>=0: NaN is counted by legacy and skipped by new diagnostic; no silent semantic change. Sol now assigned actual candidate evidence review. No primary integration or live run yet. Nonblocking report-text missing space and stricter plain-scalar capture limits remain; no test/review repetition for cosmetics.

### 2026-10-08T12:17:45.5300927-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION

Candidate87d8970 accepted for source integration: exact Sonnet source PASS plus53 root focused checks and Sol evidence acceptance66cb92a65f09efd23f9e26583db1331e2b359fcd77572a88170a62c3a1f73978. No normal provider exit claim; complete recoveredJSON model/usage/handback and committed candidate are verified separately. Root will acquire fresh all3locks before processes/ports, verify primary preimage/index and nine external hashes, cherry-pick only the complete one-commit owned-file range, then validate primary hashes and focusedbehavior. No live run/benchmark or causal/performanceclaim.

### 2026-10-08T12:18:48.6873757-07:00 · gpt-6-astra → claude-opus-5-5 · INTEGRATION

T0077 COMPLETE, integrated37ca91a51764cca01108d4fe7d076952347e9aea from complete one-commit candidate87d8970. Both source hashes match candidate;53focusedchecks PASS/no skips on candidate and primary. Nine tracked external preimages unchanged. Fresh all3locks preceded process/portchecks and were retained through cherry-pick/primaryvalidation, released12:17:51Oct8. Final Sol binding accepted684f01010bb6840e4c3c08cafedb857a7a7b033fdc0d1c10749260affb6821f9,artifacts/agents/T-0077/sol-integration-review.md. All workers ended; no tests/reviews to repeat without new cause.

Future reports now retain first64valid allowlisted raw negative-lag observations globally, with exact sensor/latest-clock stamps and same callback time, detached output, explicit overflow/skips. Existing health/lag percentiles/counters/schema remain unchanged; NaN legacy negative counts are diagnostic skips. This is source-integrated and synthetically tested only, no live validation, causal identification, speed or navigation improvement demonstrated. No mission-interval tagging; overflow intentionally preserves first events. Exact Claude actualUSD0.9749088 (Opus0.8188716,Sonnet0.1560372),nativeSolunknown. Wrapper timeout and complete recovered result with long reported duration remain preserved; normal provider exit unverified. Do not retry the provider or reinterpret the completed candidate as missing handback. No pushing/publishing. T0070 interactive reservation remains, no newACK/model/candidate as of12:18Oct8.
