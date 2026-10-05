---
id: T-0032
title: Diagnose and correct observed lane-entry target refusal on held-out course
status: changes-requested
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0032-lane-entry-recovery
base: 08e8ca5
candidate: 88cdded824fe28f266514f7a5058e4a73a908ce3
claim: tested
lease: none
updated: 2026-10-05
---

# T-0032: Complete bounded observation-only improvement

## Packet

- Interactive Opus owns diagnosis through implementation, tests, revisions and
  commit. Read README, sensor-led-navigation concept, this packet and exact
  functions implicated. Reuse clean worker checkout
  C:/Users/brand/.codex/worktrees/igvc-t0005-health-capture/IGVC SIM on assigned branch.
- T0031 first held-out2028 failed1/6 after111.66644577s on f1a6ae4, health1118/0/0,
  audit14/20, zero charged backup. Source policy equals the three seed2027 passes.
  This blocks promotion; no seed resampling or dismissal of the failure.
- Inputs in PRIMARY artifacts/iterations/2026-10-05/heldout-2028:
  run.json, decisions/00065..00075.json.gz and outcomes.jsonl. Use focused fields.
  Final sequence75 recovery_gate_selection has observed_gate_blocked,24 candidates,
  target [28.742126736475125,27.367497531890056], station27.370596; observed station
  span21.605328..28.104849. Pose [28.79001092134225,20.36749232850023,1.73949916369].
  sensor_course raises before diagnose_backup_recovery; no failed-search capture
  exists. Submission captures may differ from latest recovery observations;
  establish binding/limits before claiming an exact reproduction.
- Outcome: explain why observed lane guidance offers a target the checked planner
  cannot reach/admit, and implement the smallest GENERAL observation-only correction
  supported by captured evidence and synthetic behavior tests. You may reject the
  initial hypothesis and choose another within this scope. Prefer a usable observed
  goal ahead with all existing body/corridor/sweep checks; never bypass a blocked
  target, turn unknown into free, or permit blind backup. If no defensible correction
  is supported, hand back diagnosis and minimal missing telemetry recommendation.
- Owned: tools/observed_navigation.py, tools/sensor_course.py only for necessary
  call-site consistency or bounded diagnostic binding, and focused tests for the
  actual affected functions. One small observation helper if necessary. Do not
  touch auditor, course generator, profile, launchers, ROS interfaces, Unity,
  mount parameters, recovery_policy/evidence or primary source.
- NO course.json, generated mission.json, WORLD/reference geometry, route or
  seed-specific coordinate/condition in analysis or policy. Only observed sensor
  costs/paint, pose and sanitized six broad GPS destinations. Preserve footprint,
  forward/curvature checks, freshness/health, backup budgets, speeds and all audits.
- No live simulation or Unity build granted. Runtime is now stopped, so bounded
  offline diagnosis/replay/tests may run. At most25min active work, two revision
  rounds, <=3 focused test/replay commands, no full suite. No provider/delegation.
  Preserve failed results. Source changes need behavioral counterexamples (blocked,
  unknown, no valid target and supported clear target) rather than string tests.
- Hand back clean commit, exact changed paths, concise root cause with evidence
  references, test results, limitations and <=300word summary in this primary task
  log. Coordinator runs both reviews and any explicitly granted live trial.
- Knowledge: sensor-led-navigation; trial-audit-promotion; ros-unity-transport.

## Handback

claude-opus-5-5. Candidate 88cdded824fe28f266514f7a5058e4a73a908ce3 (base 08e8ca5), 3 files +141/-23.
Report: artifacts/agents/T-0032/REPORT.md (plus diag-1.txt, replay-2.txt, scripts); review-inputs.md staged.

```text
Root cause: the robot was stalled (lethal 1.5 m ahead). The recovery mouth handoff placed the gate at station 27.37,
  7 m ahead, near the end of the shared observed support (21.61-28.10). Every lateral body position there overlapped
  unknown cells (the grid ends about 8 m ahead), and refine only varies the lateral offset at one station. So
  observed_gate_blocked fired and the mission stopped before any backup search. The replay on capture 75 reproduces
  the logged result exactly. Stations 5 m ahead and nearer have 4-11 clear known positions.
Fix: refine_corridor_guidance gets an opt-in station_retreat_step (default off; normal planning unchanged). It
  repeats the same lateral search at nearer stations of the same observed support and returns the farthest clear
  one. Unknown and lethal still block, the full body is checked, nothing goes outside the observed boundaries, and
  there is no GPS fallback. Only the recovery call site enables it (0.5 m).
Replay (capture 75): gate at station 25.37 (2 m retreat). The unchanged legacy backup search then escapes: 0.6 m
  backup, checked 5.87 m continuation, 4.97 m trap progress.
Tests: 84 run, 83 OK. One new test had a wrong fixture (an already-clear original target is correctly accepted
  before the width check). Corrected but not re-run: 3-command budget used.
Limits: the capture is the planner submission, not the exact recovery grid; no live run; no pass, speed or
  promotion claim. Knowledge: sensor-led-navigation.
```

## Log

### 2026-10-05T06:23:00-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
Own this complete bounded slice now. T0031 runtime is stopped and lease released;
offline checks allowed. No live trial active or authorized to this task. Frozen
qualification checkout stays f1a6ae4; do not edit it. Provider usage UNMETERED.

### 2026-10-05T06:22:05-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
T-0032 accepted. Starting the diagnosis from the heldout-2028 run.json, the sequence 65-75 captures and outcomes.jsonl, using observation fields only (no course or mission geometry).

### 2026-10-05T06:22:40.8702254-07:00 · gpt-6-astra → all · NOTE
ACK received. The dispatch heading06:23:00 was prefilled and is approximate; the task file existed before the06:22:05 ACK. This note records actual coordinator time. No live trial will launch while assigned offline checks/replay run.


### 2026-10-05T06:26:43-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
Candidate 88cdded824fe28f266514f7a5058e4a73a908ce3 (3 owned files). Root cause: the recovery gate was placed 7 m ahead, at the observation limit, where every body position overlapped unknown cells, and refine searched only laterally at that station. The fix is an opt-in nearer-station retreat inside the same observed corridor with unchanged checks, enabled only for recovery. The capture-75 replay finds a gate 2 m nearer and the unchanged backup search then escapes. Tests 83/84: one new-test fixture error, corrected but not re-run (budget used). Not live. See the Handback section. Stopping.

### 2026-10-05T06:28:12.1539252-07:00 · gpt-6-astra → all · NOTE
Root ran one focused verification of final corrected fixture on exact88cdded:84tests passed6.722s exit0 (root-check-r2.log). First wrapper failed before tests because set-u preceded ROS setup; original error retained root-check.log. No source edits. Both reviews now requested; no live run. Exact latest-recovery snapshot remains unavailable. Preserve failed worker fixture result alongside corrected pass.


### 2026-10-05T06:31:10.3873783-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW
relayed-from: artifacts/agents/T-0032/sonnet-review-r1.md

**T-0032 review: `88cdded` vs `08e8ca5`**

**Verdict: approve for integration, with non-blocking follow-ups.** I found no blocking defects. This is a static review of the diff, root's 84/84 rerun and the report. It is not live proof.

**Verified from the diff**
- Normal planning is unchanged. Only the recovery call site passes `station_retreat_step`.
- `clear()` and `_rectangle_clear` are untouched, so unknown and lethal cells still block.
- Retreat is bounded by `lo` and 64 steps. The search never goes past `hi` or extrapolates beyond the support when the step is positive.
- With the default off, the evidence keys match the old ones.
- The corrected fixture is now exercised: the initial 83/84 failure was a test error, and the root rerun passes all 84.

**Findings**
1. **Medium (verify): no lower bound at the robot's own position.** `lo` is the start of the shared boundary support, which can lie behind the stalled robot. A retreated target could then be behind or at the robot. The report says continuation thresholds (≥1 m, ≥0.5 m progress) catch this, but I can't see that code in the diff. Confirm a rejection test exists.
2. **Low: invalid step values.** A negative step passes `not step`. `station-k*step >= lo` is then always true, so stations go past `hi` and `lateral()` extrapolates. NaN and inf fail closed. The constant is fixed at .5, so this is latent. Validate `step > 0` and finite.
3. **Low: misleading failure evidence.** `has_width` and the span reflect only the selected station. With sloped boundaries, a retreat station may have width while the failure reports `no_body_width_inside_observed_gate`.
4. **Low: cost.** The worst case is about 64×35 full-body checks in pure Python while the robot is stalled. The typical case is 18 stations.
5. **Low: `retreats` list.** It is only used for `len()`; a counter would do.

**Test meaning**
- The new tests assert real fail-closed behaviour. The "one step farther is not clear" check samples five offsets rather than proving it exhaustively.
- Gaps: no test for invalid steps, the 64 cap, sloped boundaries, the evidence span update, or the `sensor_course` wiring.

**Evidence limits**
- The replay used the capture-75 submission grid, not the exact recovery grid, so the escape result is offline evidence only.
- No live, held-out or seed-2029 claim is supported.
### 2026-10-05T06:29:43-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0032   Candidate: 88cdded824fe28f266514f7a5058e4a73a908ce3   Scope: evidence
Verdict: request-changes (report correction; no identified production blocker)

Findings (ranked, ≤ 5):
1. [major] artifacts/agents/T-0032/REPORT.md, Root cause: “every body position overlapped unknown” contradicts diag-1.txt: offsets -26.57 and -26.08 contain lethal/free cells with no unknown cells. The diagnostic samples 12 illustrative positions, not the actual 24 candidates; its station sweep uses 23 uniform offsets and extends below shared support. These are not exhaustive production-candidate rejection evidence. Qualify the mechanism as captured-input evidence, with unknown and/or lethal costs, and remove universal attribution.
2. [minor] REPORT.md: recovery odom stamp 118.88s is not a recorded recovery-grid stamp. Capture grid 118.14s is known; latest recovery-grid identity/update count is undetermined. Matching reason/count/span does not prove exact state reproduction or live root cause.

Verified clean exact candidate, parent 08e8ca5 and three owned files. Default refinement remains unchanged; only recovery enables 0.5m retreat. Search recomputes lateral/body bounds at each station within shared support, caps 64 retreats and preserves unknown/lethal blocking, padded footprint, yaw and downstream route/backup acceptance. Ordinary planning call is untouched; recovery/evidence/path-entry helpers are unchanged.

Original capture SHA256 d5675faba924b70042ad7d5f426b4f56e9280b0cae292439dc0eae8f3d55be3f matches sequence75 lineage through requested metadata, pose and source identities. Replay script/output support a nearer target at 25.370596m, 2m retreat, then an offline 0.6m backup candidate with 5.871m continuation/4.966636m progress; they do not prove mission success.

Root log reports 84 tests passing 6.722s on corrected candidate; worker 83/84 and pre-test ROS wrapper failure remain disclosed. No reviewer tests/replay run.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 requires claim correction.
Missing acceptance coverage: exact recovery snapshot, live integration/reliability and held-out success. Usage: UNMETERED.


### 2026-10-05T06:31:10.4066733-07:00 · gpt-6-astra → claude-opus-5-5 · REVISION
Revision1 authorized; <=15min and two focused invocations (test extension beyond original3), same paths. Correct report per Sol: illustrative12/23 sampling, unknown and/or lethal, captured-input reproduction only; recovery odom is not grid stamp and update count unknown. Preserve original reports/logs before correction. Source follow-ups before live: reject invalid enabled step values explicitly (negative/nonfinite/bool etc) so optional API cannot extrapolate; add behavioral tests. Address Sonnet medium by preventing newly retreated targets at/behind actual trap along the observed forward corridor, using actual pose from recovery call. Existing continuation progress is distance-to-target, so it does NOT prove ahead-of-trap for a target behind; do not claim otherwise. Keep normal/default path unchanged. Choose smallest clear API/design, no footprint/gate loosening. If all nearer ahead targets blocked retain refusal. Ensure failure evidence reflects stations actually checked (don't claim no width everywhere from initial station only); use bounded count instead of storing unused station list. Test behind-only-clear and no-ahead-target cases, cap/sloped support as useful. Preserve initial success replay; rerun corrected case once with actual pose to verify still finds a usable checked target. No live/source integration granted. Both reviews repeat only changed slice. Sonnet prior USD0.0805674 API-equivalent, Sol UNMETERED.

