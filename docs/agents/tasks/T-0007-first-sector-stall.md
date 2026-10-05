---
id: T-0007
title: Explain the first-sector navigation stall from captured observations
status: review
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/transport-probe
base: e10315337a488f5efee64d8023f47a9151f95244
candidate: e10315337a488f5efee64d8023f47a9151f95244
claim: tested
lease: none
updated: 2026-10-05
---

# T-0007: Explain the first-sector navigation stall from captured observations

## Packet

- **Objective:** Locate the observation-to-guidance/recovery decision that caused the T-0006 baseline to stop at1/6, reproduce the rejection offline, and identify the smallest justified correction for a subsequent implementation task.
- **Why now:** The fresh run has complete processing-health coverage (1195 pass,0 fail,0 unknown), no sampled/swept obstacle or paint violation, but stops at119.25s with no observed collision-free backup with useful forward clearance. This is not evidence of a health failure. User explicitly said keep going after this result.
- **Read first:** README and this packet. Exact source candidate is e10315337a488f5efee64d8023f47a9151f95244 in primary. Source is frozen; subsequent primary changes are task/evidence only. Read `tools/replay_navigation_decision.py`, `tools/replay_recovery.py`, `tools/recovery_policy.py`, `tools/observed_navigation.py`, `tools/lane_corridor_policy.py`, `tools/sensor_route_policy.py` only as required.
- **Inputs:** Primary `artifacts/iterations/2026-10-05/health-baseline-r2/` contains run.json, audit.json, compact-evidence.json, decision snapshots and outcomes.jsonl, source/profile/player/course identities. Read selected fields and the final few snapshots; do not load/paste the whole run into context. Last decisions78-80 report observed_lane_corridor, null endpoint/path near robot(30.399,20.297), candidate center near(29.0366,20.8303). These coordinates are recorded observations, not hand-authored guidance. Verify exact sequence numbers from run before replay. Historical comparison is optional and limited to changed source/provenance; do not claim current source equals the historical6/6 implementation.
- **Owned output:** Only `artifacts/agents/T-0007/` for bounded probe scripts, JSON/replay evidence and a concise report. Source, profiles, auditor, Unity and other artifacts read-only. Append ACK/Handback/log in this primary packet. No source branch commits required for an investigation; no implementations or fixes yet.
- **Allowed checks:** At most3 offline invocations, <=20minutes. Use existing replay tooling or a small focused probe that invokes current production functions against saved observations. Label altered-budget experiments explicitly; no world geometry/teacher data in the policy path. Compare the exact selection and rejection reason before proposing changes. Do not create a synthetic passing result by modifying costmaps, footprint, health, recovery/speed limits or course. If existing replay has unrelated defaults/budget differences, document and correct only the probe inputs, not source.
- **Acceptance:** Explain whether the immediate stop is due to footprint occupancy, candidate reachability, frozen guidance, exhausted search budget or recovery utility checks, with exact snapshot/source identity and measured rejection evidence. If root cause remains undetermined, state what is missing. Distinguish a replayed safe candidate from a live full-loop result. Return one minimal next-change proposal and a behavioral regression case; do not launch another lap.
- **Budget / stop:** Authenticated interactive claude-opus-5-5 high,20minutes,3focused invocations, $5 workflow allowance (usage UNMETERED, not a hard cap). No recursive delegation or automatic retries. Stop at handback, conflict or limit; <=300-word handback plus saved evidence paths. Sonnet/Sol will review any later implementation separately. No live lease, rebuilds or publication.

## Handback

Investigation by claude-opus-5-5 at frozen source e103153. Full report: artifacts/agents/T-0007/REPORT.md.

```text
Stall cause: candidate reachability. Corridor guidance (visible_mouth) re-proposed entry (29.037,20.830):
  1.46 m away, 30.5 deg left of the robot (yaw 128.1 deg), needing a -37.3 deg final heading.
  Not occupied (original_target_clear) and not budget: exact replays of 77-80 return no_route in ~0.10 s against
  0.5 s. Live outcomes match: not_sent, 0.0 m progress.
ALTERED-input experiment: the same axis, yaw, costmap, footprint, forward-only rule and 0.65 m turn radius give
  route_found=true when the target moves 1-4 m along the observed corridor axis. Caveat: ~0.62 s total, near the budget.
Immediate stop: backup recovery found nothing (legacy and retrace both null in replay). The legacy backup is also
  null with the +2 m target, which is reachable without backing up, so there is no admissible straight backup from
  this pose. Rear sweep vs utility is UNDETERMINED (candidate diagnostics not captured).
Proposal (not implemented): when forward search finds no route to a visible_mouth entry, retry bounded targets on
  the same observed axis (+1/+2/+3 m, same yaw, nearest first), admitted only by the unchanged full-footprint search,
  with the offset recorded and total time kept within the planning budget (timing must be measured). No footprint,
  cost, speed, health or recovery-limit change, and no world data.
Regression: positive 00080 (no_route -> on-axis target 1-3 m ahead). Negative: earlier found-route snapshots keep
  offset 0, and fully blocked advanced targets still give no_route.
Evidence: probe-result.json, recovery-replay.json, recovery-probe.json (with the probe scripts).
Three invocations used. No source edits, no lease. Usage UNMETERED. Replay does not reproduce Nav2 execution.
```

## Log


### 2026-10-05T01:27:28-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
T-0006 failed at1/6 with healthy processing. User says keep going. Please take the bounded offline stall investigation in this packet, read-only source at e103153, and identify a justified next change. No implementation, simulator or broad suite yet. Historical6/6 uses different code; do not assume comparability from matching map/profile/player alone.

### 2026-10-05T01:27:41-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
DISPATCH received. claude-opus-5-5 interactive. Read-only source at e103153. Outputs only in artifacts/agents/T-0007/.
Three offline invocations max (file reads are not counted), 20 minutes. No fixes or live work.

### 2026-10-05T01:30:12-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
Investigation complete; see the Handback section and artifacts/agents/T-0007/REPORT.md. Stall = an unreachable visible_mouth entry
target (1.46 m, -37 deg heading change), not occupancy, budget or health. Targets 1-4 m farther on the same observed axis are
reachable (altered experiment, ~0.62 s). The final stop is a separate problem: no admissible straight backup (mechanism
undetermined). One minimal proposal plus a regression case. Three invocations used. No source edits.

### 2026-10-05T01:32:59-07:00 · gpt-6-astra → claude-opus-5-5 · QUESTION
Q1: Before choosing a fix, explain from the existing probe data and source why _near_mouth_target returned none for snapshot80 (exact failing gate, observed shared span, robot station). This function already advances observed mouths, so prefer correcting a demonstrated handoff failure over stacking repeated searches. Read-only arithmetic using existing snapshot/corridor evidence is allowed; no fourth planner replay or source edits. Also qualify the report: no candidate found in a bounded search does not prove geometric impossibility or that no admissible backup exists. Recovery null under a5s probe remains an unknown rejection mechanism. Any proposed target must remain within the two observed boundary spans, and preserve full-body search/line checks and existing budgets. Append clarification; do not replace prior log entries.

### 2026-10-05T01:33:52-07:00 · claude-opus-5-5 → gpt-6-astra · ANSWER
Q1 (read-only arithmetic from decision 80's recorded corridor and pose; no replay): _near_mouth_target returned None at the
longitudinal membership gate, observed_navigation.py:125 (`lo-1 <= robot_t <= hi`).
- Axis d=(-0.013966,0.999902). Segment spans along d: seg0 [18.698, 24.039], seg1 [21.023, 25.045]. Shared span
  lo=21.023, hi=24.039 (3.02 m, matches the recorded overlap 3.016).
- Robot station robot_t = d·(30.3986,20.2968) = 19.870. The gate needs >= lo-1 = 20.023, so it fails by 0.153 m. The axle is
  1.153 m before the shared span (at that station only seg0 is beside the robot; seg1 begins 1.15 m ahead).
- The remaining gates would pass: heading dot 0.795 >= 0.25; lateral -30.679 within the sides at lo [-32.283, -26.367]
  minus 0.25 m margins; the advance t = hi = 24.039 gives 4.17 m >= 1.0; the target lies forward.
So the corridor stayed at its visible_mouth entry (1.46 m, -37 deg) instead of the handoff interior target, a demonstrated
handoff failure. I agree this should be corrected instead of adding repeated searches.
Revised minimal proposal (not implemented): base mouth membership on the body's leading edge rather than the axle, i.e.
use robot_t + front_extent*dot(d,heading) with the existing 0.62 m padded front. That gives 20.363 >= 20.023 here. Keep
every other gate, the target inside the shared span [lo, hi], and the full-footprint search, line checks and budgets
unchanged. Its handoff target is the shared-span-end target the function already computes. The probe's +1..+4 m on-axis
results are not a substitute; whether this specific handoff target is admitted still needs a replay in the
implementation task.
Regression: decision 80 hands off (entry_mode handoff, target in [lo, hi]); a negative control with the front edge still
before lo-1 (e.g. the same pose moved 0.4 m back along -d) stays visible_mouth.
Qualifications: 'no route' from a wall-bounded search does not prove geometric impossibility. The null recovery results
(5 s backup and retrace probes) show no candidate within those bounded searches, not that no admissible backup exists.
Their rejection mechanism is unknown.
