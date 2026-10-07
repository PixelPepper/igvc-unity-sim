---
id: T-0059
title: Label and guard reconstructed recovery comparisons
status: in-progress
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0059-replay-provenance-opus
base: 2e1e6b8
candidate: none
claim: none
lease: none
updated: 2026-10-06
---

# Packet

Sole HEADLESS owner opus-t0059-replay-provenance-20261006T1811.
Worktree C:/Users/brand/.codex/worktrees/igvc-t0059-replay-provenance/IGVC SIM.
Root holds artifacts/agents/T-0059/implementation.lock during dispatch.
Only own tools/replay_recovery.py and NEW tools/tests/test_replay_recovery_provenance.py.
Root verified owned existing paths clean at base; external sensor_course.py/latency
edits remain outside scope. Read README intro and embedded packet; primary task
log is authoritative. No primary edits, docs edits or recursive delegation.

Implement reviewed T0058 narrow design for recovery-event reconstruction only:
* Preserve fixed one row per selected recovery_guidance_selected event. Add event
index identity because sequences can repeat; never replace a skipped event.
* Every executed row says replay_kind=counterfactual_reconstructed and
input_binding=not_evaluated, including equal stamps. Never call it live-exact.
* Strict positive int (not bool) event.grid_stamp_ns and snapshot.metadata.grid_stamp_ns.
Equal allows reconstruction with reason grid_stamp_match; differing skips with
reason grid_stamp_mismatch; missing/malformed stamps skip grid_stamp_unknown.
* Explicit --allow-grid-mismatch enables available valid snapshots with mismatch/
unknown stamps as labelled counterfactuals. Missing/unreadable/malformed snapshots
always remain skipped even with opt-in. Preserve raw stamps or explanatory safe
metadata, budget scale, status/reason, no numeric substitution/coercion.
* Snapshot acquisition/validation errors become per-event skipped rows; validate
necessary shape before planner use. Avoid a broad catch around planner execution:
unexpected planner/runtime errors must stay visible, never become missing data.
* stall_counts includes selected,executed,skipped,skipped_by_reason,by_status with
selected=executed+skipped. Existing successful legacy/retrace numerical fields stay
unchanged when admitted; document schema additions/skip semantics in module help.
* Document reconstructed options/guidance/continuation/fresh TrapMemory; matching
stamp proves neither full inputs nor equivalent live state. No digest pairing,
exactness enum, automatic capture selection or type normalization to force hashes.
* T0055 replay_controls and classifier remain unchanged. recovery_evidence exact
capture loader/producer and all runtime policy/safety inputs remain untouched.

Behavior tests use synthetic snapshots/events and mocked planners to observe
admission and exact forwarded values: equal/mismatch/missing/malformed stamps
(bool,float,zero,negative); opt-in; snapshot absent,badgzip,badJSON,badshape;
repeated sequence unique eventindices; skip counts/no replenishment; successful
legacy/retrace output unchanged and inputs unmutated; no planner calls on skipped
rows; planner exception visible. CLI test fixed selection and JSON/help fields.
Don't test mere source strings or replicate implementation predicates.

No tests/imports/benchmarks/replays during implementation: root runs focused new
suite plus test_recovery_control_pose.py and test_recovery_evidence.py under all3
simulator locks after actual commit handback. No historical files, teacher/course/
WORLD geometry, Unity/ROS/live sessions or provider calls. Preserve all failures.
Commit only two owned paths, return SHA/files/NOT RUN checks and risks <=300words.
ExactOpus5.5/high6min/USD5 taskbound, no provider-error retry/substitution.
Stop at committed handback or blocker. Sonnet source review, Sol evidence review;
root integrates only after both and tests. No publishing/pushing.

## Log

### 2026-10-06T18:13:00.915445-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

Sole HEADLESS opus-t0059-replay-provenance-20261006T1811, isolated branch/worktree and implementation.lock. T0058 narrowed contract accepted by both reviewers. Worker slot now released by Sol; interactiveT0056 remains reserved without ACK. Own only two packet files, no execution.
