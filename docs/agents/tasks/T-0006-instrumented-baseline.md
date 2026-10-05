---
id: T-0006
title: Run one hidden instrumented baseline with independent audit
status: ready
priority: P1
owner: gpt-6-astra
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/transport-probe
base: 6db872fa8c01e6670bdcb4c4a527b536423ba218
candidate: 2002dada9c1b7c3b39d56c545d8a6de03855dbde
claim: none
lease: none
updated: 2026-10-05
---

# T-0006: Run one hidden instrumented baseline with independent audit

## Packet

- **Objective:** After reviewed T-0005 integration and combined checks, record one fresh sensor-led baseline, including failed or partial outcomes, to establish current behavior and exercise the new diagnostics if a health failure occurs.
- **Type / ownership:** Integrator-operated experiment, no source implementation. Only task/board coordination, an evidence summary and one benchmark-ledger row may be added. No policy, perception, profile, auditor or Unity edits during the trial.
- **Dependency:** T-0005 accepted, integrated, combined checks passing. Freeze and record the actual clean launch commit in the dispatch and live provenance before motion. The header base is the pre-instrumentation reference, not a claim about code that ran.
- **Inputs:** README, docs/AGENT_ITERATION.md, T-0005 handback/reviews, `artifacts/agents/T-0005/baseline-preflight-sol.md`, and historical `artifacts/iterations/2026-10-01/admissible-endpoints/{config.json,live.json,profile.yaml}`. No full logs/CAD in agent context.
- **Trial identity:** `artifacts/iterations/2026-10-05/health-baseline/`. Preserved RPP profile SHA-256 `14245726680bb2f4e36aef73ae32de7fb3395d2e38b01dd6d7fbe7c869edbef4`; current course player assembly `6564e85476866ef0b2d1b0a8954af7ae81280b177cb7cef8b5da50d906b429c7`. Separate ROS overlay `/home/brand/igvc_agent_ws/t0005-baseline`. Record freshly generated course/autonomy hashes and six broad GPS destinations. Different source/layout/host load forbids a controlled historical improvement claim.
- **Command:** From the primary checkout, hidden host launch of `node tools/agents/iteration-launch.mjs artifacts/iterations/2026-10-05/health-baseline/config.json`. It uses exclusive primary live.lock, TCP10000/domain42, hidden variant-start seed2027 normal, checked-path, body-clearance weight3, speed ceiling0.6m/s, planning budget0.5s, 600-second mission timeout, independent audit and verified shutdown. No RViz or visible Unity launch. Rendering remains active for sensors.
- **Runtime controls:** One trial only. Check simulator processes and port before dispatch. Do not stop another session or acquire a parallel instance. Let the process acquire and retain its exclusive lease through shutdown. Monitor build/start/audit stage durations; build at most10minutes, startup/readiness at most3minutes, audit at most3minutes, mission at most600seconds plus its controlled-stop allowance. Escalate a stalled stage to safe owned-session cleanup while preserving lease ownership; never kill a lease holder while command authority may remain. No automatic retry.
- **Evidence:** Preserve config/profile, full run/audit/logs, source/player/overlay/course/autonomy hashes, diagnostic JSON, runner exit and shutdown verification. Append the completed stable artifact set to the benchmark CSV, including failure. Classify 6/6 separately from the independent audit and armed-interval health. Do not force a failure merely to populate a snapshot. A clean run validates normal capture wiring but leaves live failure capture unexercised.
- **Acceptance:** Truthful complete result and cleanup evidence, with evidence review; a failed lap can complete this diagnostic experiment but is never promoted. Policy promotion remains 3 consecutive full audit passes on seed2027 plus one pass on each of2 preselected held-out seeds. This single trial does not meet that gate.
- **Budget / stop:** One integrator trial; no additional paid implementer, no agents running simulation concurrently. Review allowances $5 each with10minute bounded read-only tasks; native Sol usage unmetered. ADR-008 has no aggregate daily cap. Stop after recording/auditing the one result and cleanup; use a new task for an evidence-driven algorithm change or additional laps. No publication.

## Handback

Pending T-0005 integration.

## Log


### 2026-10-05T01:17:00-07:00 · gpt-6-astra → all · DISPATCH
T-0005 is integrated with562 combined tests passing. Run the one bounded baseline from the clean primary checkout after this coordination commit; live.json records the exact launch HEAD (source-equivalent to candidate2002dada). Task candidate records source integration; the subsequent coordination-only commit is separately recorded runtime provenance. Simulator processes and TCP10000 are clear at preflight, with no IGVC environment overrides. Config/profile already prepared at artifacts/iterations/2026-10-05/health-baseline. Request exclusive primary lease; only the managed process may acquire/release it. No other live work authorized during this experiment. Operator checks stage deadlines and preserved shutdown evidence. No source edits until it finishes.
