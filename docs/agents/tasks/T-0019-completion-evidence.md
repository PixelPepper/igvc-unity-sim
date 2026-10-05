---
id: T-0019
title: Make final arrival and shutdown evidence precise without changing motion
status: integrated
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0019-completion-evidence-opus
base: a0a3d49ae465ef2176ce4bdb910257fc76c6ccb7
candidate: ce249efbc3ee83099147d54360edc5401da93d15
claim: tested
lease: none
updated: 2026-10-05
---

# T-0019: Complete development ownership for finish evidence

## Packet

- User explicitly grants Opus more development autonomy; ADR011. Existing interactive Opus5.5 owns this complete slice. Choose implementation/test design, iterate and commit without intermediate approval inside boundaries. Not another analysis-only handback.
- Worktree C:/Users/brand/.codex/worktrees/igvc-t0005-health-capture/IGVC SIM prepared clean on codex/t0019-completion-evidence-opus at a0a3d49. Read README, knowledge sensor-led-navigation/trial-audit-promotion/processing-health, T0017 report AND both reviews/decision in primary.
- Outcome: next real run precisely distinguishes final-destination arrival decision, cleanup start, autonomy-disable completion, action-cancel completion and final recorded/audited trajectory endpoint. Record bounded evidence to measure goal distance, loop sampling interval near finish, pose and odom acquisition time, monotonic receipt/evaluation time and trajectory indices. Mark missing/stale/unavailable explicitly, never invent samples.
- Own tools/sensor_course.py; a small pure observer/helper tools/mission_completion.py if useful; tools/tests/test_mission_completion.py and directly relevant existing tests only if essential (state paths in handback); primary artifacts/agents/T-0019/REPORT.md and review-inputs.md. No auditor, other policy, ROS interface, configs, Unity, dependency or canonical coordination header edits.
- Instrumentation ONLY: arrival radius, mission decision sequence, command/cancel ordering, waits, safety/health guards, path policy and recording endpoint remain unchanged. No extra post-stop motion/waits, no new stop logic or speed cap, no source-course input. Avoid expensive/unbounded per-loop data; choose clear cap/semantics. Preserve existing report consumers. Do not claim telemetry proves continuous physical stopping.
- Meaningful tests execute actual observer/integration helper: ordered arrival/cleanup snapshots, moved pose during cancellation, goal-relative distances, missing odometry/malformed/nonfinite values, bounded sample retention/loop dt semantics, stopped-before-final and cleanup-error cases as applicable. Show valid progression and failures without source-string assertions that merely mirror wiring. Explain integration placement and any untested ROS behavior.
- T0018 live repeat is in a DIFFERENT frozen worktree. You may now read/design/edit your own source (light local work). Before any tests/replay/builds, confirm primary artifacts/iterations/2026-10-05/connector-repeat-2/live.json stage finished and shutdown_verified true; if not, wait in bounded <=60s intervals, continue light work. Do not touch or acquire runtime lease. This explicitly grants proceeding to focused tests once shutdown verifies; no new message needed.
- <=35min active work plus measured lease wait, <=3 focused test invocations, no full suite/Unity build/live run/delegates/auth retries. Own branch commits only. End with immutable candidate, exact changed paths, tests, evidence limits, relevant knowledge concepts and <=300word handback. Up to2 review revisions stay with you. Integrator handles dual review/integration/live validation.
- Primary task log append-only; don't commit docs/agents from worker branch. Source originals/CAD unchanged. No publishing.

## Handback

Final revision by claude-opus-5-5. Candidate ce249efbc3ee83099147d54360edc5401da93d15 (base a0a3d49). Integrated 86cec53 and 02cea95; 598 combined tests pass, live wiring pending.
Report: artifacts/agents/T-0019/REPORT.md (includes T-0017 corrections); review-inputs.md staged.

```text
Changed paths: tools/mission_completion.py (new, pure recorder), tools/sensor_course.py (+31/-1 hooks),
  tools/tests/test_mission_completion.py (new). No other tests edited.
Records state['mission_completion'] (additive): last 64 loop samples (monotonic eval time, pose, odom stamp, odom
  receipt age, destination, trajectory index, goal-relative distance, wall loop_dt); per-destination arrival decision
  with the exact pose compared to its radius (radius_m, final flag); ordered phases (cleanup_start, disable autonomy,
  cancel action, reset unmarked mode, mission_health_end), each recorded after the step returns with ok/error;
  endpoint = last trajectory row at report time plus distance to the final goal; after_final_arrival moved_m,
  trajectory_samples and goal_distance_change_m. Nulls plus an `unavailable` list for missing/nonfinite/malformed values;
  no loop_dt across an invalid time. Caps: 64 loop samples, 1 arrival per destination, 16 phases (dropped counted).
Safety: every hook and the report go through a guard that records errors (state['mission_completion_errors']) and
  never raises, so no cleanup step can be skipped. Arrival radius, decision order, cancellation, waits, guards, path
  policy, recording endpoint and speed are unchanged. Adds mission_completion.py to source_sha256.
Tests (after T-0018's verified shutdown): py_compile, then test_mission_completion plus the 3 existing sensor_course
  importers: final 45 OK (2 existing skips). Covers ordered finish with motion during cleanup, malformed/nonfinite values,
  bounded retention and dt, stopped-before-final with duplicate arrival, phase cap, invalid construction.
Untested: live ROS wiring (executor spin during cleanup, real receipt timing, guard under a real exception). Not proof
  of continuous physical stopping. Knowledge: processing-health and trial-audit-promotion pins unchanged.
1 invocation. UNMETERED.
```

## Log

### 2026-10-05T04:11:53.484766-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
User-approved complete development task: you own design through implementation,
focused tests, revision and source commit within this packet. No interim permission
needed. Correct T0017 assumptions in your new report; original report/reviews stay
preserved. Light authoring may start now in your isolated worktree. Tests wait only
for T0018 verified shutdown, then proceed without another dispatch. Return completed
slice and stop; independent review/integration/live remain coordinator-owned.

### 2026-10-05T04:12:27-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
DISPATCH received (ADR-011 slice ownership). Worktree igvc-t0005-health-capture on codex/t0019-completion-evidence-opus at a0a3d49.
Instrumentation only. Light authoring now; focused tests only after T-0018 live.json shows finished and shutdown_verified. T-0017
corrections acknowledged: the interval is illustrative, cleanup callbacks keep recording, and localization causality is not established.


### 2026-10-05T04:17:45.755434-07:00 · gpt-6-astra → claude-opus-5-5 · NOTE
T0018 is finished with shutdown_verified=true. Its audit passed20/20,6/6 in355.42s with one checkedbackup. Your already-authorized focused tests may proceed; no further dispatch is needed. No nextlive trial will launch until your focused checks finish.

### 2026-10-05T04:18:29-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
Candidate 7cd566e1590f04ecafec9a538cf06a98b4ad28db (3 owned files, +290/-1). Instrumentation-only mission completion evidence,
with guarded hooks. Tests ran after T-0018's verified shutdown: 42 OK (2 existing skips). See the Handback section. One focused invocation.
Live ROS wiring untested offline. Stopping; the next live trial may proceed.


### 2026-10-05T04:21:06.987016-07:00 · gpt-6-astra → claude-opus-5-5 · REVIEW
relayed-from: artifacts/agents/T-0019/sonnet-review-r1.md

## REVIEW: Approve after 3 small fixes

The wiring is observation-only. The diff leaves the arrival radius, command and cancel order, waits and guards unchanged. The `record_completion` guard is sound, and all three root notes hold up against the diff. This is from reading only, since I didn't run anything.

### Ranked bugs

1. **Cleanup phases lose goal distance on every successful run.**
   - `state['completed_destinations']` equals `len(goals)` after the final arrival, so `_goal()` returns `None` in `finally`.
   - Every cleanup phase then has `goal_distance_m: null`, listed in `unavailable`, on exactly the runs this task targets.
   - `endpoint.final_goal_distance_m` still works, which limits the damage.
   - `test_ordered_finish_with_motion_during_cleanup` passes destination `2 == len(GOALS)` but never asserts phase distance, so it hides the bug.
   - **Fix:** in `_sample`, resolve the goal as `goals[-1]` when `index == len(goals)`. Keep `None` for larger indices so the destination-7 test still holds. Assert phase `goal_distance_m <= .4` in the ordered-finish test.

2. **Arrival cap is unenforced for out-of-range indices.**
   - `arrival()` rejects only `None` and duplicates, so distinct indices such as 7, 8, 9... append with `radius_m=None`.
   - This contradicts "10 at most" and the bounded claim. The live wiring can't hit it, because the index is always valid there.
   - **Fix:** `if goal is None or duplicate: return`. Add a test for index ≥ `len(goals)`.

3. **`loop_dt_s` can span an invalid sample.**
   - `_last_loop_s` is only updated on valid `now`, so valid → invalid → valid yields a dt across the gap.
   - That violates "never computed across an evaluation that had no valid time".
   - **Fix:** assign `self._last_loop_s = now` unconditionally, so it becomes `None` on an invalid sample. Add a valid-invalid-valid test.

### Nit, optional

The `report` error path appends without the 8-message cap, so the list can reach 9. Guard it or reword the claim.

### Coverage

The listed gaps are the three above, plus the untested live wiring you already flagged. After these fixes I'd expect no remaining correctness or safety blockers.
### 2026-10-05T04:21:06.987016-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION
Changes requested, revision1 within your existing complete-task ownership. Proceed
without waiting for another permission: fix successful-cleanup goal resolution,
reject out-of-range arrivals independently of completed-cursor goal lookup, and
invalidate loop_dt across an invalid sample. Add behavioral regressions and keep
instrumentation-only boundary. You choose exact implementation. Also keep JSON
finite under bounded valid inputs; do not broaden feature scope. Error cap nit is
optional if documented. At most3 focused checks/20min. New immutable commit,
not amend; hand back exact evidence and stop. Sonnet verified actual model,
API-equivalentUSD0.0848054. Sol will review final corrected candidate, avoiding
duplicated checks of already-known rejected code. No live session currently.

### 2026-10-05T04:22:39-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
Revision 1: candidate ce249efbc3ee83099147d54360edc5401da93d15 on top of 7cd566e (no amend). Diff 7cd566e..ce249ef: 3 files, +58/-14.
Fixes: cleanup goal resolution at index == len(goals) (final goal); arrivals only for index < len(goals); an invalid time
breaks the loop_dt chain; overflowing derived values become null (finite JSON); report-error path capped at 8.
New regressions for each. Focused check: compiled, 45 tests OK (2 existing skips). Instrumentation only. One invocation.
Details in REPORT.md "Revision 1". Stopping; T-0020 may proceed.


### 2026-10-05T04:25:27.657555-07:00 · gpt-6-astra → all · REVIEW
relayed-from: artifacts/agents/T-0019/sonnet-review-r2.md

**Verdict: approve. The three prior findings are resolved and I found no behavior regression. Two items are worth fixing, neither blocking.**

**Prior findings**
1. **Cleanup goal distance: resolved.** `_goal` maps `index == len(goals)` to the final goal and returns null above that. The ordered-finish test now asserts every phase is non-null and ≤ 0.4.
2. **Arrival cap: resolved.** `arrival` rejects `index >= len(goals)` and duplicates, so at most `len(goals)` arrivals are kept. The arrival hook runs before the counter increments, so the index is correct.
3. **Time chain: resolved.** `_last_loop_s = now` is set even when `now` is None, which resets the chain. The valid → invalid → valid → valid test matches the code.

I traced the ±1e308 test by hand, and each assertion holds. Overflow produces inf, which `_finite_or_none` turns into null.

**Ranked findings**
1. **Medium: the constructor is unguarded.** `MissionCompletionRecorder(goals)` runs before the outer `try` and raises `ValueError` on any goal that isn't a finite 3-tuple. That would abort a mission before it starts, which contradicts "instrumentation can never stop the loop". Wrap it and fall back to `None`. `record_completion` already catches the resulting errors.
2. **Low: the wiring is unverified, and I can't confirm it statically.**
   - `latest['odom'][0]` is assumed to be a `time.monotonic()` receipt time. A different clock would give garbage ages, not a crash.
   - The new `else:` on the cleanup `try` assumes that `try` had no existing `else`.
3. **Nit: `loop_dt_s` is not listed in `unavailable`.** It is added after `missing` is computed, so the first sample's null goes unnamed, which is inconsistent with the stated contract.
4. **Nit: the `cleanup_start` record runs before `telemetry.report()`.** The cost is microseconds, but it sits just after the "capture before cleanup waits" comment. Consider recording it after the capture.

Preserved: arrival radius, command and cancel order, waits, health, and audit behavior. The hooks are observation-only, and the error list is capped at 8. I didn't run the tests; this relies on the worker's 45 tests and Sol's independent check.

### 2026-10-05T04:25:27.657555-07:00 · gpt-6-astra → all · REVIEW
relayed-from: artifacts/agents/T-0019/sol-review-r1.md

### 2026-10-05T04:24:28.2602529-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0019. Candidate: ce249efbc3ee83099147d54360edc5401da93d15. Base: a0a3d49ae465ef2176ce4bdb910257fc76c6ccb7. Scope: code/evidence.
Verdict: approve-with-nits.

Findings:
1. Nit: canonical header/Handback and review-inputs.md still name 7cd566e and 42 tests. Bind them to final ce249ef/45 tests before closure; REPORT Revision 1 and task log correctly disclose the revision.

Observations: exact clean worker HEAD; full range contains only mission_completion.py, sensor_course.py and test_mission_completion.py (+334/-1). Recorder is additive, with 64 retained loop samples, one arrival per actual destination, 16 phases and eight capped error messages. Arrival uses the exact pose compared to the unchanged radius. Cleanup phases retain final-goal distances at completed cursor; invalid times break dt chains; out-of-range arrivals are discarded; overflowing derived values become null. Endpoint and movement summary distinguish arrival from later recorded odometry. The new helper is fingerprinted.

Safety: loop/arrival/report hooks catch exceptions; existing command/cancel ordering, waits, health/safety checks and recording endpoint remain. No audit, policy, sensor, speed or threshold change. REPORT correctly retracts T0017's unsupported stop-band, post-cancel and localization claims.

Tests: after independently confirming T0018 finished/shutdown_verified, sourced /opt/ros/jazzy/setup.bash and ran python3 -B -m unittest test_mission_completion test_sensor_mission_contract test_trap_escape test_navigation_decisions: 45 tests, OK, two existing skips. These exercise observer behavior, including moved cleanup poses, malformed inputs, bounded retention, error phases and revision regressions.

Missing acceptance coverage: real ROS callback/receipt timing, guarded failures in live wiring and correspondence between recorded endpoint and auditor sample. Helper tests do not prove integration or continuous physical stopping. No live/replay/broad suite. Usage: UNMETERED.

### 2026-10-05T04:25:27.657555-07:00 · gpt-6-astra → all · DECISION
Accept final ce249ef after Sonnet approval and Sol approval-with-nits.
Constructor concern is nonblocking: load_goals validates finite triples before
recorder construction. Existing odom callback uses monotonic receipt time.
No extra wait, cancel-order change or command decision. First loop_dt null is
intentional and documented; unavailable list concerns do not authorize new motion.
Final focused suite45 tests includes2existing skips; actualROS wiring pending.
Sonnet verified model, API-equivalentUSD0.0975974;SolUNMETERED. Integrate both
immutable commits, then combined checks before any new live trial.


### 2026-10-05T04:27:20.466401-07:00 · gpt-6-astra → all · INTEGRATION
Integrated as 86cec53 and 02cea958ccc9cd051241170c58ed1cbcd929a697. Full check_core.sh exited0, including knowledge check; log artifacts/agents/T-0019/combined-checks.log. Live wiring still pending. Third repeat will keep frozen a0a3d49, so it does not exercise the new recorder. Prior candidate test metadata remains historical; final ce249ef/45 focused tests/2existing skips binding is recorded in review-inputs and reviews.
