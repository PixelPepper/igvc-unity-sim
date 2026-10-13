---
id: T-0097
title: Account for time and motion in the saved six-minute course run
status: in-progress
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/transport-probe
base: b5b0b65074d282f9bc3f015b65d16dd9a8459de6
candidate: none
claim: none
lease: none
updated: 2026-10-13
---

## Packet
Direct user request: "ok lets do the saved run time breakdown". Analyze ONLY T0094 run20261013T184458-b140dccf (360.02655 wall seconds,5/6 harness arrivals). Separate new descriptive analysis, no repeat of prior reviews/trials. T0095's244s recovery failure is a DIFFERENT run; do not pool. T0096 remains resource-blocked, no execution/retry assigned here.

Read README, this packet and artifacts/agents/T-0097/input-pins.json first. Frozen input/run.json is25MB: parse locally with standard-library Python; never dump it into model context. Source-only frozen sensor_course.py, sensor_route_policy.py and mission_completion.py match this run's recorded hashes. T94 accepted RESULTS/run-summary/manifest preserved. Root verifies prior run pin independently. Provenance remains posthoc; no new full pre-run manifest or hardware/rules claim.

Owned outputs ONLY artifacts/agents/T-0097/analysis.py, metrics.json, breakdown.md (<=300 words), optional compact CSV; append-only ACK/HANDBACK here. Artifact-only diagnostic; no project-source branch/edit/integration. Implement and execute ONE bounded lightweight standard-library JSON/arithmetic pass; no project imports, tests, replay, capture decompression, NumPy/plotting, provider calls, delegation, simulator/process/port checks, locks, live trials or builds. This descriptive file analysis is safe while Unity is active; heavy computation remains prohibited. Stop on error and report, no auto retry. Target6minutes, actualmodel/usage if known otherwise unknown.

Required outputs:
1. Wall-time per destination leg from mission_health_interval.start.monotonic_s, five arrival monotonic_s, mission_health_interval.end.monotonic_s. Identify sixth leg incomplete. Reconcile sum to elapsed_wall_s. Startup and cleanup must be labelled/excluded where identifiable; elapsed interval includes any recorded cleanup tail, report its size.
2. Odometry trajectory rows [sim seconds,x,y,yaw]. Clip to recorded health trajectory indices and stamp bounds; validate finite values, positive dt, gaps and endpoints. Sum observed XY displacement, wrapped absolute yaw, simulation duration per leg using arrival trajectory indices/stamps; include sample-gap/invalid accounting. Distances are odometry estimates, not judge course distance or excess detour proof.
3. Mutually exclusive simulation-time categories from each adjacent interval: near-stationary speed<0.03m/s AND abs angular speed<0.10rad/s; turning-in-place speed<0.03 and angular>=0.10; moving-turn speed>=0.03/angular>=0.10; moving-straighter otherwise. Invalid/nonpositive dt or gap>0.25s unknown, do not bridge. State analyst thresholds; sensitivity near-stationary thresholds0.02/0.05m/s (same angular threshold) in same analysis pass. Do not convert SIM categories into exact wall-time totals or infer commands/causes. Include ten longest contiguous near-stationary bouts and per-leg categories.
4. Planning is OVERLAPPING activity, not an additive fifth motion bucket. Match requested/evaluated events by sequence, counts/missing/duplicates, sum and union of clipped request-to-evaluation wall intervals, recorded search_wall_s distribution/sum, successful versus null plans, time-budget flags where present, sent-goal counts. Inspect frozen source to correctly describe search_wall_s vs end-to-end response; these are not necessarily CPU time or stationary waiting. Do not assign all stopped time to planning. Report unobservable wall-time motion/planning causality explicitly.
5. Rank at most three evidence-supported next investigations. No promise that changing speed/budgets/thresholds fixes navigation. Preserve 5/6 radius-arrival vs finish distinction. No full audit, geometry lookup, route optimality or calibrated hardware claim.

Save input/output hashes, method definitions and all exclusion counts in metrics.json; handback exact paths/hashes and <=300-word summary. Root independent arithmetic proceeds in parallel; Sonnet source/interpretation then native Sol evidence review before acceptance. No changes to other tasks or source guards.

## Log

### 2026-10-13T14:45:33.674425-07:00 · gpt-6-astra → team · DECISION
Assigned independent, lightweight saved-file time accounting under direct user request. Linked session idle at dispatch preparation, T96 helper assignment ended. All inputs copied and pinned; source hashes match recorded runtime. No simulator resource checks or heavy work needed for bounded JSON arithmetic. Root will verify independent totals and prior manifest while Claude implements artifact-only analysis.

### 2026-10-13T14:45:33.860128-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
saved-time-breakdown-r1. Read docs/agents/tasks/T-0097-saved-run-time-breakdown.md and execute its bounded artifact-only saved-run analysis. Inputs frozen in artifacts/agents/T-0097/input, source pins match run. Own analysis.py/metrics.json/breakdown.md only and append task ACK/HANDBACK. One lightweight standard-library JSON pass, no project imports/replay/tests/simulator/process checks/providers/delegation. Separate wall leg durations, SIM odometry motion classes and overlapping planner response intervals. No live authority or T96 execution. Stop on error or handback. Confirm nonce in BOTH canonical task log and assistant text. Root independently verifies arithmetic while you work; source/evidence reviews follow.
