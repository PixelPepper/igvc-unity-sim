---
id: T-0065
title: Record truthful planning-pose provenance without changing latency behavior
status: integrated
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0065-capture-provenance-opus
base: 980ee1d4196b35d56991a86d0862d4f1f5b74bc6
candidate: 17778b77546639e2308788c324500b2fdeb58ede
claim: tested
lease: none
updated: 2026-10-06
---

# Packet

ONLY INTERACTIVE user-started Claude session interactive-opus-t0065-20261006,
same actual session as T0064. ACK alias and exact claude-opus-5-5 before work.
T0064 assignment ended. One reserved slot, no duplicate headless dispatch.
Worktree C:/Users/brand/.codex/worktrees/igvc-t0065-capture-provenance/IGVC SIM,
branch/base above. Root froze ONLY three current external files into isolated base;
see primary artifacts/agents/T-0065/source-snapshot.json. Primary remains untouched.
Read README intro, this packet, T0064 final decision, source APIs as needed.

Problem: primary sensor_course sends a measured or predicted planning pose but
records no metadata.latency_compensation. New measured-default dataset therefore
classifies even disabled captures as unknown. Fix producer provenance only.

Own ONLY tools/latency_compensation.py, tools/sensor_course.py capture wiring,
NEW tools/tests/test_primary_capture_provenance.py. Do not edit original
test_latency_compensation.py: keep it as independent preservation evidence.
No classifier/dataset/replay/admission/recovery/profile/Unity/CLI edits.

Implement a minimal API to obtain detached metadata for the SAME actual predict
call used to build planner inputs. Required enabled/applied strict booleans,
measured_pose and planning_pose matching the recorded input, plus truthful
versioned legacy estimator identity: wall monotonic submit-to-admission,
last20 clamped samples, lower order statistic sorted[(n-1)//4], initial0.3s,
max latency1.2s default, legacy end-pose shift scaling. Reflect custom constructor
settings honestly; unused alpha must not be called EMA. Identity is not safety proof.

Instrument actual prediction branch outcome, not pose equality. Disabled, missing
twist, nonfinite twist and existing stationary early returns are applied=False.
Reaching extrapolation is applied=True even if output equals input (e.g. t=0).
Do not infer measured from equality or missing historical flags. Reset per-call
state so prior prediction cannot leak to a later skipped call. Return metadata
copies that later calls and caller mutations cannot change. Preserve predict's
existing return shape/values, latency sample math, thresholds, counters, report
fields, bounds and all runtime decisions. No candidate EMA/horizon/staleness port.

Wire metadata into captured snapshots and compact requested-event metadata from
the same measured tuple, exact planning pose and call. Keep existing inputs,
heading hints and measured recovery/admission unchanged. Metadata attests pose
provenance only, not coherent pose/twist timestamps or freshness.

Behavior tests using real predictor and canonical classifier after JSON roundtrip:
disabled, missing/nonfinite/stationary twist, straight/turn/clamped prediction,
zero-latency applied prediction with equal poses, skip after applied/reset,
detached prior metadata. Verify estimator identity and unchanged representative
numeric outputs/counters. Exercise actual sensor_course capture wiring via a
focused synthetic harness/extracted pure capture helper if needed; AST-only key
presence is insufficient. Prove a captured disabled/measured row is admitted by
default dataset policy and predicted capture excluded unless explicit opt-in;
historical missing metadata remains unknown. No heavy real training/teacher/logs.

Source edits and ast.parse only by worker; NO tests/imports/providers/delegation/
live/builds/primary integration. Root runs focused tests under all3locks after
committed handback, then Sonnet source and Sol evidence review. Bound6min/USD5
interactive target, not billing guarantee; report incomplete at bound. Commit
owned files only. Handback <=300words with SHA/files/API, checks NOT RUN, risks.
Stop after handback/blocker. No dual-estimator or live A/B approval in this task.

## Log

### 2026-10-06T20:23:00-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

INTERACTIVE interactive-opus-t0065-20261006 ONLY. T0064 complete as reviewed analysis; its broad dual-estimator proposal is deferred. New isolated frozen base prepared without changing primary. ACK exact model/session before editing. Sonnet's equality-based applied suggestion is explicitly rejected: record actual branch execution. No tests/live/integration authorized. Posting is pending until actual ACK.

### 2026-10-06T20:21:37.9315806-07:00 · gpt-6-astra → claude-opus-5-5 · NOTE

Timestamp correction: preceding DISPATCH was written20:21 Pacific; its20:23 timestamp was a clerical error. Ownership and exact packet unchanged. T0064 final decision now recorded; read before implementation.

### 2026-10-06T20:21:38-07:00 · claude-opus-5-5 → gpt-6-astra · ACK

ACK T-0065, alias interactive-opus-t0065-20261006, model claude-opus-5-5, same interactive session as T-0064. Worktree igvc-t0065-capture-provenance, branch codex/t0065-capture-provenance-opus, base 980ee1d. Owned: latency_compensation.py, sensor_course.py capture wiring, new test_primary_capture_provenance.py. ast.parse only.

### 2026-10-06T20:21:58.4349041-07:00 · gpt-6-astra → claude-opus-5-5 · ACK

Actual20:21:38 exact-model/session ACK received. Sole active implementation owner interactive-opus-t0065-20261006; one slot reserved. Root prepares validation without running it until committed handback.

### 2026-10-06T20:24:55-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK

Alias interactive-opus-t0065-20261006, model claude-opus-5-5. Commit **17778b7** on codex/t0065-capture-provenance-opus, parent 980ee1d.

Files:
- tools/latency_compensation.py
- tools/sensor_course.py (capture block, import and requested event only)
- NEW tools/tests/test_primary_capture_provenance.py

test_latency_compensation.py is untouched. Only static `ast.parse` was run.

API:
- `predict_with_provenance(pose, twist)` → `(planning_pose, metadata)`.
  - The pose is exactly one unchanged `predict()` return.
  - Metadata fields: `enabled`, `applied`, `reason`, `measured_pose`, `planning_pose`, `latency_s` (None unless applied) and `estimator`.
  - `applied` is True only when the extrapolation branch ran (`extrapolated` or `extrapolated_shift_scaled`). Early returns are False: `disabled`, `no_twist`, `nonfinite_twist`, `stationary`.
  - Zero latency with equal poses is still applied, so it classifies as predicted.
  - Branch state resets on every call, and the returned metadata is a deep copy.
- `estimator_identity()`: `wallclock_submit_admission_lower_quartile` v1.
  - Rules: local monotonic submit→admission-attempt interval, window 20, `sorted[(n-1)//4]`, clamp to max, first sample replaces the initial value, latest twist with no age check, end pose scaled to `max_shift_m`.
  - It includes the constructor config with `alpha_used=False`.
- `capture_planning_inputs(...)` → `(planning_pose, inputs, metadata)`. sensor_course's one capture call; `inputs` has the identical shape to before.
- sensor_course writes `metadata.latency_compensation` and gives the requested event a JSON-detached copy.
- Unchanged: predict arithmetic, checks and order, latency math, counters, report fields, heading hint, admission and recovery.

NOT RUN:
- `python3 -m unittest tools.tests.test_primary_capture_provenance tools.tests.test_latency_compensation tools.tests.test_dataset_pose_policy tools.tests.test_navigation_decisions`

Risks:
- The sensor_course wiring is tested through the shared pure helper plus an AST check. No ROS harness runs the loop itself.
- The metadata attests pose provenance only; the twist/pose timing stays unverified.
- `reason` is a new optional field that the classifier ignores.
- Historical captures stay unknown.

Stopping.

### 2026-10-06T20:26:02.1095989-07:00 · gpt-6-astra → claude-opus-5-5 · ACK

Actual20:24:55 handback received; assignment ended. Candidate 17778b77546639e2308788c324500b2fdeb58ede bound; clean isolatedtree verified. Starting exact Sonnet source review and root focused tests under all3locks. No primary integration/live readiness yet.

### 2026-10-06T20:26:37.7100760-07:00 · gpt-6-astra → claude-opus-5-5 · NOTE

Root validation candidate17778b7:25methods passed, then test_navigation_decisions module failed import because sparse checkout omitted ros2/src/igvc_gps. Command exit1,26entries includes loaderfailure, raw evidence preserved artifacts/agents/T-0065/validation. This is not fullpass. Root materialized unchanged GPS package from same candidate and will rerun ONLY failed-to-load navigation suite underall3locks; no repeat25passingchecks. Source review still running. No new worker assignment.

### 2026-10-06T20:28:01.8478402-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION

Accept candidate17778b7 focused TESTED claim. Sonnet review/review.md no blockers,24.55s/USD0.134234; Sol review/sol-evidence-review.md accepts38 executed passes across preserved failedloader command and corrected navigation-only command;2historical fixture checks skipped. Code tests execute shared capture helper/classifier/admission, loop linkage AST only, no ROS loop/live safety claim. Sonnet nonblocking note incorrectly says skipped reason is None: source sets disabled/no_twist/nonfinite_twist/stationary; latency_s alone is None. Malformed classifier behavior is unchanged and covered by existing dataset checks. Loose AST/wiring limit retained, no blanket dynamic loop claim.

Authorize root metadata integration underall3locks. First checkpoint ONLY exact three pre-existing external frozen bytes sensor_course/latency_compensation/originaltest after hash verification, with no workingtree rewrite; then cherry-pick full one-commit candidate. This checkpoints the existing experimental variant, does not accept it for live promotion or adopt T0053/60. Preserve all other external files. Validate38 synthetic checks onprimary; omit2historical replay tests explicitly, do not manufacture fixtures or rerun historical records. All interactive assignments remain ended.

### 2026-10-06T20:29:16.4429638-07:00 · gpt-6-astra → claude-opus-5-5 · INTEGRATION

Integrated metadata candidate at6e866970f285b6a8602d14eac5e415a8156fa665 after exact external checkpoint2b18333. Primary38synthetic tests PASS, no skips in selected scope;2historical replay checks explicitly omitted. Three sourcehashes matchcandidate, originaltest and12externalfilehashes unchanged. Final Sol integration/sol-evidence-review.md independently accepted source/checkpoint/log/lease binding. LogSHA61b554e709376821a32e58a84105378074273799fc42871448c509a049cf0da3. All3locks released. No livebenefit/latencyvariantpromotion; T0053/60 remain unintegrated. Do not repeat completed tests without newcause. All T0065 ownership ended.
