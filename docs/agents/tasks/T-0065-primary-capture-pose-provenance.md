---
id: T-0065
title: Record truthful planning-pose provenance without changing latency behavior
status: in-progress
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0065-capture-provenance-opus
base: 980ee1d4196b35d56991a86d0862d4f1f5b74bc6
candidate: none
claim: none
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
