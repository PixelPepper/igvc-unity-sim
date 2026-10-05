---
id: T-0019
title: Make final arrival and shutdown evidence precise without changing motion
status: in-progress
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0019-completion-evidence-opus
base: a0a3d49ae465ef2176ce4bdb910257fc76c6ccb7
candidate: none
claim: none
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

Pending.

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
