---
id: T-0064
title: Reconcile latency candidate with the current measured-pose data pipeline
status: in-progress
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: none
base: b41e63b418764fbbfada02cf7487e25ba613d85a
candidate: none
claim: none
lease: none
updated: 2026-10-06
---

# Packet

READ-ONLY analysis ONLY by INTERACTIVE user-started session
interactive-opus-t0064-20261006, same actual user session as completed T0063.
ACK alias/model claude-opus-5-5. No headless duplicate; one reserved worker slot.
T0061/62/63 integratedb41e63b, all assignments ended. T0054 dataset questions are
resolved by those slices, do not repeat that design. Read README intro, this
packet and T0054 latest notes; source pins artifacts/agents/T-0064/primary-source-pins.json.

Objective: smallest concrete source-reconciliation plan for reviewed latency
candidate646845e plus estimatoridentity f41aeeb against CURRENT primary, preserving
externally authored rolling-percentile source and newer integrated fixes.
No source edits, commits, tests/imports/replay/build/provider/delegation/live work.
Only write artifacts/agents/T-0064/readiness.md and optional exact source-pins.json;
append ACK/HANDBACK in primary task log. Do not edit task headers/board.

Read relevant source only:
- primary tools/sensor_course.py, latency_compensation.py, sandbox_batch_report.py,
  targeted tests and newest dataset_policy/replay_recovery guards as needed.
- clean candidate worktree C:/Users/brand/.codex/worktrees/igvc-t0060-latency-identity/IGVC SIM
  HEADf41aeeb8cc067f6f14e7c6dfee136d75fba06082 (T0053base646845e). This lacks newer
  primary changes: NEVER propose replacing primary wholesale with that worktree.
- T0053/T0060 final acceptance log/code differences; T0048 external inventory.
  Record exact hashes, detect current-primary drift from root pins, don't overwrite.

Deliver compact static plan with exact functions/paths and minimal test criteria:
1. Enumerate current-vs-candidate differences in estimator/timebase, bounds,
   measured/planning pose consumers, safety admission and reporting. Identify
   patches safe to port versus external changes that must stay preserved.
2. Propose an explicit estimator-selection strategy with identities and unchanged
   disabled/default behavior, keeping percentile and EMA distinct. No claims that
   one is faster/better; confoundedT0052 and odometry timing do not prove causality.
   Root chooses implementation scope after review. Do not silently drop the
   external experiment or use enum/metadata changes as proof of safety.
3. Confirm data pipeline's measureddefault/explicit optins remain compatible with
   proposed live payloads. Missing metadata stays unknown; no inferred measured.
   Old recovery costmap equality remains unproven even matchingstamps; keep
   counterfactual gates. Propose smallest genuinely missing runtime/capture or
   reporter compatibility correction only, avoid redoing resolved work.
4. List blockers before any bounded live A/B: sourceidentity/frozenplayer/profile,
   tests, lease, preregistered seeds/attempts and auditgates. Do not design or launch
   new batch now; do not widen freshness/body/unknown/recovery/safety bounds.

Output <=1000words artifact + <=250word handback, exact checked source identities,
remaining uncertainties and one actionable next implementation slice. Bound6min/
USD5 interactive target, not billing guarantee; report incomplete at bound.
No course/WORLD/teacher geometry or historical bulk logs. Stop after handback.
Root Sonnet plan review/Sol source-evidence check; new implementation owner needs
separate explicit assignment and isolated frozen worktree. No primary latency
integration, realtraining/modelpromotion, pushing/publishing or live lease.

## Log

### 2026-10-06T20:07:20.246154-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

INTERACTIVE interactive-opus-t0064-20261006 ONLY, read-only new reconciliation after integrateddataset changes. ACK model/session before analysis. Prior T0063 implementation ended. No source edits or execution authorized; artifacts and canonical ACK/HANDBACK only. Posting is not assumed receipt.

### 2026-10-06T20:07:39-07:00 · claude-opus-5-5 → gpt-6-astra · ACK

ACK T-0064, alias interactive-opus-t0064-20261006, model claude-opus-5-5. This is the same interactive session that completed T-0063.
- Read-only analysis.
- Outputs: only artifacts/agents/T-0064/readiness.md, plus optional source-pins.json, and this ACK/HANDBACK.
- No source edits, commits, tests, imports or live work.

### 2026-10-06T20:08:11.740274-07:00 · gpt-6-astra → claude-opus-5-5 · ACK

Actual20:07:39 exactmodel/session ACK received; sole read-only interactive-opus-t0064-20261006 active. Prior source assignments ended. Root waits actual artifact handback then Sonnet/Sol; no latency integration or live lease.
