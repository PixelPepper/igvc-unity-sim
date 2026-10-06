---
id: T-0053
title: Review the external latency-compensation change before acceptance
status: changes-requested
priority: P1
owner: gpt-6-astra
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/transport-probe
base: 74967bfa0a579f74be2d70c94c7dfc56274d778a
candidate: none
claim: none
lease: none
updated: 2026-10-06
---

# Packet

Read README introduction and this packet. Read-only static review of another
Claude session's uncommitted change; no source edits, tests, builds, simulation,
replay, provider calls or delegation. Current T0052 players own both instances.
Review immutable copies under artifacts/agents/T-0053/source/; manifest.json
binds copies to observed source hashes. tracked.diff captures tracked changes.
This is not a reviewed Git candidate or permission to integrate that working set.

Scope: latency_compensation.py and sensor_course.py integration, relevant
sandbox_profile.py settings and the two copied tests. Check disabled identity,
state/pose timing, predictions versus actually frozen observations, continued
actual-pose admission/body/unknown checks, pathological velocities/configs,
and whether tests support the advertised behavior. Inspect original checked
admission helpers read-only if necessary, with exact source/path references.
No WORLD/course/teacher geometry, raw run logs or private configuration needed.

Return <=250words: blockers versus hypotheses/limits, precise file/line and one
bounded correction/validation recommendation. Do not call a partial static
review a safety certification or accept claimed test counts without artifacts.
Exact Claude Sonnet5.5, high, once, maximum4minutes/USD3, <=8focused reads.
No automatic provider-error retry. Root relays findings through canonical logs;
external implementer retains file ownership. Sol evidence review follows only
when a committed candidate and actual bound test results are provided.

## Log

### 2026-10-06T07:42:00-07:00 · gpt-6-astra → claude-sonnet-5-5 · DISPATCH

Source snapshot only, no executable validation while simulations run. Root will
independently bind current model/plan metadata alongside this code review.

### 2026-10-06T07:47:19-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0053/sonnet-static-review.md

**T-0053 static review: not accepted.** There is no committed candidate and no bound test artifacts. This is a partial static read of the 5 copies plus `tracked.diff`. It is not a safety certification, and I accept no test counts. I did not read the admission helper `prepare_controller_plan`, so continued actual-pose admission, body and unknown checks are unverified from source. I only saw it called with the actual pose (`sensor_course.py:786-791`).

**Blockers (source-visible)**
1. **Frozen record mixes poses.** `sensor_course.py:509` puts the predicted pose in the snapshot inputs, which are saved at `:532`. `outcomes.begin` (`:533`) and `requested.input_pose` (`:537`) still use the actual pose. The predicted pose is first logged at `:795`. Replay and audit therefore can't see from the snapshot or request event alone that the plan started from a prediction.
   - **Fix:** log `planning_pose`, the twist and the latency in the `requested` metadata, and keep the actual pose in the snapshot.
2. **No integration test.** The two copied tests cover only the pure predictor (`test_latency_compensation.py:12-37`) and the CLI flag and bool validation (`tracked.diff:113-119`). Nothing covers the disabled-mode inputs at `sensor_course.py:504-509`, or the `observe_latency` and `planned_from` wiring.

**Hypotheses and limits**
- **Disabled mode isn't byte-identical.** The inputs are identical, but `:795-796` add `planned_from` and a `latency_compensation` state key, and the source-hash list at `tracked.diff:56` changes.
- **Rotation is uncapped.** `latency_compensation.py:37-44`: with v≈0 and large w, the yaw shift is up to w·1.2 s with no bound. The cap at `:46-49` limits only distance and scales the arc as a chord.
- **Config is unvalidated.** `:15-18` don't reject NaN, a negative `max_shift_m` or an `alpha` outside 0–1. The initial latency isn't clamped, and the 1.2 s clamp (`:27`) sits below the 5 s planning budget.
- **Pose/twist timing.** The line that sets `(x,y,yaw)` is outside my reads. `latest['twist']` is read at `:504` with no age check.

**Smallest validation:** add an offline test that stubs the frozen-input construction at `sensor_course.py:504-509` and asserts disabled equals actual, enabled equals predicted, and the actual pose is still logged. Then provide a committed candidate and run artifacts for Sol.

### 2026-10-06T07:47:19-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION

Changes requested before acceptance or a root-granted latency trial. Review
completed once: exact claude-sonnet-5-5, 51.72seconds, USD0.1431538, exit0,
no provider error/retry. Snapshot hashes are in T0053/source/manifest.json.
No bound candidate or executed integration-test evidence exists in this packet.
Sol evidence review waits for those artifacts; no broad checks ran during T0052.

Root verified the relevant snapshot lines. Clarification to the suggested fix:
keep the serialized planner inputs EXACTLY as sent (predicted when enabled).
Do not replace those inputs with the measured pose merely to satisfy logging.
Add separately named measured_pose, planning_pose, twist sample identity/age,
and latency estimate to submission metadata and the requested event, including
paths that never reach path_entry. This preserves replay fidelity while making
prediction versus measurement explicit. Current captures do contain predicted
inputs; their limitation is missing explicit prediction provenance, not absence
of a replayable planner pose. Actual-pose admission is still called, but this
limited review did not certify its complete safety chain.

Implement in an isolated owned branch after acknowledging this packet; do not
edit primary policy/model files during active comparisons. Provide behavior
checks for disabled actual-input identity, enabled frozen inputs plus metadata,
and admission against a changed actual pose/grid with unchanged body/unknown/
freshness rejection. Validate nonfinite/invalid predictor configuration and
bound rotation, or justify operational bounds with code/tests. Preserve all
rejected attempts and retain actual-pose gates. No WORLD/teacher data in runtime.
Do not launch ab-latency-1 before reviewed candidate/evidence and the queued
T0051 diagnostic window. No automatic retries, pushing or publishing. No new
missions after09:40; overnight work ends10:00AM Pacific.
