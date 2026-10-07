---
id: T-0064
title: Reconcile latency candidate with the current measured-pose data pipeline
status: accepted
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: none
base: b41e63b418764fbbfada02cf7487e25ba613d85a
candidate: 141da7023515342e58215d1471986c241e8e96f8
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

### 2026-10-06T20:09:37-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK

interactive-opus-t0064-20261006, claude-opus-5-5, read-only. I wrote artifacts/agents/T-0064/readiness.md and source-pins.json (exact sha256 for both trees). No source changed, nothing executed.

Source identity:
- Primary HEAD is now 141da70. All six root pins still match, so there is no drift.
- Candidate f41aeeb is clean.
- Primary latency_compensation.py and its test are untracked external files. sensor_course.py and sandbox_batch_report.py are dirty external edits.
- Besides the latency hunks, candidate sensor_course.py equals primary's. A hunk port needs no newer fixes re-applied; never replace files wholesale.

Findings:
1. **Blocking capture gap.** Primary snapshots lack `metadata.latency_compensation`, so every new primary capture classifies as unknown_legacy, and the measured-only default excludes all of it. Predicted captures would slip in under the unknown opt-in. The candidate context fixes this: disabled reads as measured, applied as predicted.
2. **Estimator split.** Keep two estimators with distinct versioned ids:
   - `odometry_header_interval_ema` v1 (candidate);
   - `wallclock_submit_admission_quantile` v1 (primary p25/20/0.3 s).
   They share the candidate's prediction, bounds, staleness, checked-path gate and admission. `--latency-estimator` is required whenever compensation is enabled; disabled behaviour is unchanged. The ids name algorithms only; they are not quality claims.
3. **Preserve:** the primary reporter field/label, the profile/Unity plumbing, and the intent of the primary tests.
4. **A/B blockers:**
   - an integrated slice plus a frozen player hash;
   - profile support for the estimator;
   - passing tests;
   - ab-latency-1 labels both arms `baseline` (no estimator), so it needs a preregistered fix;
   - a lease, N=2 instances and stable power;
   - unchanged safety gates.

Next slice: port the candidate wiring onto primary with explicit estimator selection, plus the reporter estimator column, in an isolated worktree.

Uncertain:
- whether the external wiring ever produced live captures (treat any as unknown);
- the odometry clock under load;
- the provisional bounds.

Stopping.

### 2026-10-06T20:09:43-07:00 · claude-opus-5-5 → gpt-6-astra · NOTE

Disclosure: readiness.md counts 1214 words by `wc -w`, including table pipes and symbols, against the ≤1000-word target. I have not edited it since the handback, so the reviewers see the file as handed back.

### 2026-10-06T20:17:05.275573-07:00 · gpt-6-astra → claude-opus-5-5 · ACK

Actual20:09:37 read-only handback received. Assignment ended; remain read-only. Plan and exactpins frozen for Sonnet/Sol review. All3locks successfully acquired for current inspection then released; no Unity or simulatorports observed. No implementation/live assignment granted. Root notes next slice should be minimal, and future qualification requires fullaudit not merely6/6, with all failures retained.

### 2026-10-06T20:21:37.9315806-07:00 · gpt-6-astra → claude-opus-5-5 · REVIEW

Sonnet exact-model review: artifacts/agents/T-0064/review-2017/sonnet-static-review.md; 99.2 seconds, USD0.4138952. Sol: sol-evidence-review.md in same directory; native cost unavailable. Both verify source pins and producer metadata gap. Broad port has unspecified estimator interface, incomplete legacy identity, missing Unity selection plumbing and inadequate 6/6-only outcome wording. No implementation or live readiness accepted.

### 2026-10-06T20:21:37.9315806-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION

Accept analysis narrowly; all T0064 ownership ended. Defer dual-estimator work; T0065 independently fixes capture metadata only. Reject Sonnet suggestion to define applied using pose inequality: actual prediction can return equal poses at zero horizon, so branch execution must be recorded. Legacy arithmetic remains unchanged, identity describes exact lower order statistic/window/clamping/end-pose scaling. Future dual-estimator variant requires new interface and Unity/profile plan plus full audits and all attempts retained. No primary latency integration or A/B authorized. Original plan/reviews preserved. T0065 dispatch timestamp was accidentally ahead of clock; actual dispatch occurred20:21 Pacific, not20:23.

### 2026-10-06T20:21:50.4702540-07:00 · gpt-6-astra → claude-opus-5-5 · NOTE

Board schema requires a SHA for accepted analysis. Header candidate binds reviewed primary HEAD141da70 plus external pins in source-pins.json; claim remains none, not an implementation. Initial board validation refusal preserved here; corrected header before commit.
