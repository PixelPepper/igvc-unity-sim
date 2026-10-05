---
id: T-0022
title: Explain observed recovery refusal in failed connector repeat
status: accepted
priority: P1
owner: gpt-6.1-sol
reviewers: claude-sonnet-5-5
orchestrator: gpt-6-astra
branch: none
base: a0a3d49ae465ef2176ce4bdb910257fc76c6ccb7
candidate: a0a3d49ae465ef2176ce4bdb910257fc76c6ccb7
claim: none
lease: none
updated: 2026-10-05
---

# T-0022: Observed recovery diagnosis

## Packet

- Read README, knowledge sensor-led-navigation and exact relevant functions only.
- Read-only diagnosis, not implementation. T0020 stopped at 2/6 after 226.30s,
  no observed safe backup with useful forward clearance; health complete and passed.
  Explain which observed prerequisites/candidate gates failed and what we can and
  cannot infer. Compare T0018's successful backup; do not assume same location or causality.
- Inputs: primary artifacts/iterations/2026-10-05/connector-repeat-3/run.json and
  bounded final planner-input captures; connector-repeat-2/run.json and relevant
  backup-associated captures; compact evidence and task T0020.
  Runtime source is frozen worktree
  C:/Users/brand/.codex/worktrees/igvc-t0008-mouth-handoff/IGVC SIM at a0a3d49,
  especially tools/sensor_course.py, observed_navigation.py, and actual recovery
  chooser reached by that call. Follow precise symbols, not a repository-wide review.
- NO course.json, WORLD, audit/reference geometry or exact route inputs in
  diagnosis/replay. Observed sensor costs, sparse GPS and pose only.
  Submission-time captures are not necessarily latest recovery snapshots.
  Distinguish missing telemetry from absent observation and unsafe geometry.
- At most 10 minutes and 4 focused read/analysis commands. No source edits, tests,
  live sessions, replays, builds, provider calls or delegation. Write only
  artifacts/agents/T-0022/REPORT.md and a compact diagnostic JSON if useful.
  Do not update task log/header; return one handback of at most 300 words to root.
- Acceptance: exact decision indices/reasons/evidence pointers; code branch that
  raises; whether refusal happens before or after sweeps; smallest next bounded
  instrumentation or improvement without weakening unknown, footprint, health,
  clearance or freshness gates. Support numerical claims. Stop after diagnosis.
  This task grants no fix/promotion authority.

## Handback

Report: artifacts/agents/T-0022/REPORT.md and comparison.json. T0020 sequence149
uses broad GPS after all lane-pair candidates were rejected. The corridor
refinement early exit is not evidence of stale sensors or failed rear sweeps.
The actual null-return stage inside select_backup_recovery is UNDETERMINED
because failed search diagnostics are discarded. T0018 success occurs 26.363m
away, not a controlled same-location comparison. Next bounded instrumentation
should preserve actual recovery inputs and per-candidate rejection stages.
Four read-only commands; no source changes/tests/replay/live. Usage UNMETERED.

## Log

### 2026-10-05T04:38:00-07:00 · gpt-6-astra → gpt-6.1-sol · DISPATCH
Investigate this bounded observed-only failure while Opus revises T0021.
Return a supported diagnosis and smallest next step, no speculative rewrite.

### 2026-10-05T04:46:47.772416-07:00 · gpt-6.1-sol → gpt-6-astra · HANDBACK
relayed-from: artifacts/agents/T-0022/REPORT.md
Observed-only diagnosis complete; exact failure stage is undetermined.
See report and comparison.json for bounded evidence and numerical provenance.

### 2026-10-05T04:46:47.772416-07:00 · gpt-6-astra → all · NOTE
Accept the uncertainty correction for current handoff prose. Earlier T0020 review
shorthand around no_fresh_corridor_or_footprint must not be interpreted as sensor
staleness or the reason select_backup_recovery failed. Separate review pending.

### 2026-10-05T04:48:38.404428-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW
relayed-from: artifacts/agents/T-0022/sonnet-review-r1.md
Exact model verified; USD0.0813274 API-equivalent.

**Verdict: Approve.** I found no material errors, only non-blocking edits. The report keeps what the logs establish apart from what they don't. Lane detection returned `all_pairs_rejected`, so recovery selected `broad_gps`. The refinement fields are labeled as skip artifacts, and the cause of the null return is marked UNDETERMINED. It makes no route-impossibility or stale-sensor claim. I did not independently verify the comparison figures. The pose distance (26.363 m) agrees with the pose values in the JSON, but the JSON is worker-produced.

**Edits requested:**
1. `no_fresh_corridor_or_footprint` is emitted for three conditions: corridor `None`, non-corridor guidance, and footprint `None`. Selecting `broad_gps` satisfies the second, so the skip is explained. The logged string itself doesn't say which condition fired, and the report should say so. I also can't confirm the cited lines 38–41 from the excerpt.
2. `planning_route_found=false` appears in both observations, including the successful recovery. It doesn't discriminate between them, and the report should say that explicitly.
3. The 306 surviving lane points and the rejection counts (`entry_not_forward:2`, etc.) are not in `comparison.json`. Cite the decision file or mark them as not independently checked.
4. Reword "before versus after rear sweeps" to list the possible None branches: validation, initial clearance, rear sweep, planner `None`, continuation rejection, and time/expansion exhaustion.
5. Add to the limitations that `trap_regions`, the `continuation_costs` mask, `forward_options` and the search limits may not be in the submission captures.

**Next task:** The instrumentation-only scope is right. Add a requirement that the `None` return contract stays unchanged, with diagnostics carried on a side channel. The diagnostics should record:
- the exit branch
- the blocked rear distance
- the per-candidate rejection clause in `_accept_continuation`
- the budget consumed

The report should make no replay claims.
### 2026-10-05T04:48:38.404428-07:00 · gpt-6-astra → all · DECISION
Accept read-only diagnosis and instrumentation-only next step, with these
qualifications: broad_gps suffices to explain refinement skip, but the generic
reason string does not distinguish its three conditions. planning_route_found
is false in both compared observations and is not a discriminant. Lane candidate
counts are reported from decisions/00149.json.gz, not independently reproduced by
Sonnet. Recovery arguments, options, continuation mask and search limits need
their own exact snapshot; submission capture does not prove those values.
Null may arise from validation, initial clearance, rear sweep, proposal absence,
continuation rejection or time/expansion exhaustion. Actual stage remains unknown.
Keep select_backup_recovery's return contract and safety checks unchanged in the
next task; diagnostic transport must work across the existing worker process.
No replay, navigation improvement, speed or repeatability claim.
