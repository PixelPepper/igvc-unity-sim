---
id: T-0096
title: Compare two fixed recovery search budgets on one frozen observed state
status: ready
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/transport-probe
base: 64316d5222a534aad41ae431a821a8c124130f12
candidate: none
claim: none
lease: none
updated: 2026-10-13
---

# T0096 frozen recovery time-budget comparison

T0095 diagnosis accepted by exactSonnet and nativeSol; human explicitly requested continued Claude collaboration. One new offline experiment, not another live attempt. Same linked Opus owner prepares a small standard-library driver under artifacts/agents/T-0096/probe.py; root alone executes under all three simulator locks after source review. No project source modifications, tests, providers, delegation, replay execution by worker, or T84 retry.

Use the frozen 20 modules under T0095/input and the original recovery-00160.json.gz from run20261013T210631-5fc7543a. Verify input-pins-v2/source-pins and capture hash from T0095/run-pins before importing; sys.path explicitly prioritizes frozen modules, dont_write_bytecode true. Only load_capture_inputs from frozen recovery_evidence; require planner function observed_navigation.plan_observed_navigation. Verify loaded module paths and exact canonical describe_search_inputs digest equals capture digest and saved worker submission digest. Record Python/NumPy versions and interpreter identity, no environment secrets.

Predeclare EXACTLY TWO calls, sequential in fixed order, independent fresh decoded inputs: original max_search_seconds=5 and counterfactual20. Keep max_expansions50000, all candidate distances, planner function/options, lane inputs, grids, body footprint, unknown/freshness/progress/continuation gates unchanged. Use existing diagnose_backup_recovery unmodified, no monkeypatches, no diagnostic wrapper. Verify only max_search_seconds differs via canonical input descriptions/digests. Case20 is counterfactual, never live-equivalent. Do not select additional cases or repeat for determinism/success. Run both declared cases even if first returns a proposal, except stop on error/outer timeout.

Save each full returned escape/evidence immediately using exclusive new-file writes into output directory supplied as positional argument. Record elapsed wall times and output SHA; separate root outer90second watchdog. Save before/after source/capture hashes, all input bindings and numerical settings, exit/error receipts. No ROS, Unity, network, course/WORLD/teacher data, ground-truth lane classification or commands. Original-case timing-dependent result need not match saved live failure. Proposals are observed-grid local planner results, not traversed safety or course finish.

Stop after helper handback (<=300words, exact SHA, explicit no-execution statement). Source Sonnet checks frozen imports, exact two-call design, invariant parameter equality and persistence. Root runs once only if source review passes; native Sol binds receipts and interpretation. Max90seconds root child; no automatic retry. Hypothesis: more search time may produce an admissible escape on this one frozen state without changing geometry or safety gates; failure to do so is bounded negative evidence only.


## Ownership and acceptance
Analysis-only driver stays isolated in ignored artifacts/agents/T-0096; no source branch edits needed. Opus owns probe.py, HANDOFF.md and its append-only task log. Root owns execution wrapper, summaries and receipts. Exact linked Opus5.5 target6minutes for helper handback; no providers or retries. This task is not a runtime budget change; diagnostic duration20s cannot be promoted from this evidence. Do not change timestamps/freshness checks or control sources. Source Sonnet review4min/USD3; nativeSol final evidence. Candidate header is coordination anchor plus exact helper/input hashes, not a runtime code candidate. Root executes only after reviewed helper. Stop on source pin mismatch, model/provider failure, unexpected output collision, import failure or watchdog expiration; preserve failure and do not rerun automatically.

## Log

### 2026-10-13T14:25:41.960128-07:00 · gpt-6-astra → team · DECISION
Assign a fresh bounded experiment justified by accepted T95 time-limited forward search evidence. Original5s and counterfactual20s cases are fixed before execution; max50000 expansions and all safety checks unchanged. Root owns all3locked execution. No live work or source implementation authorized.

### 2026-10-13T14:25:42.502542-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
frozen-recovery-budget-r1. T0095 accepted: corrected report passed exactSonnet and nativeSol. Your diagnosis assignment ended. New T0096: read primary docs/agents/tasks/T-0096-frozen-recovery-budget-comparison.md. Prepare only the bounded probe.py and HANDOFF.md in artifacts/agents/T-0096. Two fixed original5s/counterfactual20s calls on recovery-00160, unchanged50000expansion/geometry/safety limits, fresh decoded inputs, exact frozen imports and hashes, immediate per-case persistence. Root alone executes after source review under all3locks. No execution/tests/project edits/live/providers/delegation/T84 retry. Handback helper SHA and stop. No human relay.
