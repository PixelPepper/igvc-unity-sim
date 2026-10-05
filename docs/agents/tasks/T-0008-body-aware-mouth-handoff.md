---
id: T-0008
title: Use the existing front footprint extent for observed mouth handoff
status: integrated
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0008-mouth-handoff-opus
base: efb81f545a72201e3d2a9888113c421d2d950a60
candidate: 09fb1686ec9bddc07e682e54bb80e039bc86b112
claim: tested
lease: none
updated: 2026-10-05
---

# T-0008: Use the existing front footprint extent for observed mouth handoff

## Packet

- **Hypothesis:** A guidance membership test based on the existing front footprint extent permits an already-entering robot to target the supported corridor interior, avoiding the repeated short mouth target observed in T-0006. Every actual path still needs the unchanged full-body forward search and execution admission.
- **Read first:** README, this packet, T-0007 Q1/ANSWER and evidence review in the primary checkout. Relevant source `tools/observed_navigation.py` (_near_mouth_target/select_observed_guidance/plan_observed_navigation), `tools/sensor_course.py` (one recovery selection call), and `tools/tests/test_observed_navigation.py`.
- **Exact evidence:** Primary `artifacts/iterations/2026-10-05/health-baseline-r2/decisions/00080.json.gz`; original source e103153, source-equivalent to this base. Prior health1195pass/0fail/0unknown, mission1/6, auditfalse. Shared observed station span[21.023,24.039], robot station19.870; axle misses lo-1 by0.153m, projected front using actual padded xmax0.62 and heading dot0.795 crosses it. T-0007 altered-target success is only a hypothesis; replay the ACTUAL proposed handoff target.
- **Owned paths:** `tools/observed_navigation.py`, `tools/tests/test_observed_navigation.py`, `tools/sensor_course.py` (only passing the existing goal_footprint to recovery guidance selection), new `tools/tests/fixtures/observed_mouth_20261005.json.gz` and adjacent `tools/tests/fixtures/observed_mouth_20261005.md` for small reproducible observation-only regression input and provenance. No other source/profile/auditor/Unity changes.
- **Scope:** Thread the actual goal_footprint through the internal guidance selector as an optional keyword. Preserve old point-only behavior when absent, with no guessed R3-a dimensions. For the lower longitudinal membership gate, use the front-center projection from actual footprint xmax and heading relative to the observed axis. Keep heading/lateral/upper-station/support-span gates unchanged; don't expand into unseen span or consume arbitrary GPS shortcuts. Use the same single path search, existing wall/expansion budgets and unchanged footprint for collision/admission. Record enough diagnostic fields to explain axle/front membership and selected observed target. Frozen recovery intent remains frozen; only initial selection at actual pose gets the footprint. No arbitrary additional search loops or heading/collision relaxations.
- **Acceptance:** Exact snapshot80 with unchanged recorded planner options selects a target within the shared observed span and yields an admitted forward plan if computationally feasible; report all no-route/timing outcomes honestly. Positive geometry handoff and negative controls (front not yet reaching threshold, outside lateral sides, wrong heading, beyond span, missing footprint/point mode) must be behavior-tested. Blocked/unknown costs still prevent unsafe paths. Earlier successful observed decisions should retain their existing target when already eligible. Verify optional API forwarding preserves existing callers and recovery selection uses the same geometry. Don't write structural tests mirroring the source. Small fixture contains only recorded observations; exclude course/WORLD and unrelated metadata/paths. Preserve source artifact hash/provenance in its note.
- **Validation:** At most3 focused invocations: relevant observed-guidance/recovery tests and bounded exact-observation replays. No broad suite; ASTRA runs combined tests after immutable candidate receives both reviews. Wall-clock search results are machine/load dependent; no duration assertion that intermittently fails on slower hardware. Measure unchanged-budget replay behavior and state timing limits. No claim of full-loop improvement from replay.
- **Worktree:** `C:/Users/brand/.codex/worktrees/igvc-t0008-mouth-handoff/IGVC SIM`, prepared branch at base. Commit only owned paths there; canonical task Handback/messages only in primary. No docs/agents commits in worker branch.
- **Live trial:** none in implementation. After acceptance/integration and combined tests, integrator may assign one separate bounded trial with identical course/profile/player, existing0.6m/s ceiling, exclusive lease and independent audit. No worker live launch.
- **Budget / stop:** Authenticated interactive claude-opus-5-5 high;35minutes,3focused invocations, $10 workflow allowance (actual usage UNMETERED, not enforced billing cap). No recursive agents/retries. Stop at immutable handback, conflict or budget. <=300word handback lists changed files/SHA, test/replay evidence and limitations. Sonnet/Sol review the same SHA; at most2 revisions. No publication.

## Handback

Revision 1 by claude-opus-5-5. Candidate 09fb1686ec9bddc07e682e54bb80e039bc86b112 (base efb81f5).

```text
Change: _near_mouth_target(..., goal_footprint=None, membership=None). With a valid footprint the LOWER longitudinal
  gate uses the front-center station: axle + x_max*heading_dot. Heading, lateral, upper-span (axle <= hi), advance >= 1 m
  and forward-target gates are unchanged and still use the axle. The target stays in [lo, hi]. A missing or invalid
  footprint falls back to the old axle test. select_observed_guidance gets an optional goal_footprint keyword.
  plan_observed_navigation forwards planner_options['goal_footprint']. sensor_course passes the existing goal_footprint
  to actual-pose recovery selection only; frozen intent is untouched. mouth_membership diagnostics record the axle and
  front stations, threshold, basis, shared span and the gate result. One search; budgets, footprint, costs and line
  checks are unchanged.
Fixture: tools/tests/fixtures/observed_mouth_20261005.json.gz holds only the observation inputs of decision 80; the
  .md records provenance (source sha256 2063eed3..., fixture 80977b98...).
Replay (exact snapshot 80, recorded options including the 0.5 s wall budget, x3): route_found 3/3. Handoff target
  (28.986133, 24.446254) at station 24.039 = hi. Refinement original_target_clear, 620 path points, full_footprint_sweep
  true. Total 0.61-0.67 s including guidance, so timing is machine-dependent.
  artifacts/agents/T-0008/replay-recorded-budget.json sha256 d388f429ff4ec668ced2f154c26d56f08cd26fcf31a3c720b517ea0858d0237d
Tests: wsl … cd tools/tests && python3 -B -m unittest test_observed_navigation test_recovery_policy -> 37 OK in 5.2 s.
  New: decision-80 handoff vs point mode unchanged (axle 19.870, front 20.363); recorded-option plan only through
  checked poses; lethal/unknown wall at y>22 never crossed; controls front-short / beyond-span / outside-sides /
  wrong-heading / 5 malformed footprints reject; an already-eligible pose gives the identical target with or without a
  footprint. No duration or "route found" assertion, because those outcomes are wall-budget dependent.
Invocations: 3. The first run passed but took 102 s because tests used a test-only 30 s wall budget. I reverted to the
  recorded options. Live: none. Claim: tested. Usage UNMETERED. This replay does not show a full-loop improvement.
```

## Log


### 2026-10-05T01:40:25-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
T-0007 qualified proposal is accepted for experiment after Sol arithmetic review. Implement T-0008 in the prepared worktree at efb81f5, owned files only. Actual proposed target is(28.986133,24.446254), shared span endpoint24.039037; test this target rather than substituting the earlier offset sweep. Front-center projection changes guidance membership only. Preserve every other gate, old point-only callers, one search and existing budgets. Use actual goal_footprint in both planning and actual-pose recovery selection; do not alter frozen intent. Packet contains acceptance controls and35minute/3check limit. No live work. Stop at immutable handback; Sonnet/Sol review follows.

### 2026-10-05T01:40:43-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
DISPATCH received. claude-opus-5-5 interactive. Worktree igvc-t0008-mouth-handoff at efb81f5. Owned paths only, 3 focused
invocations, 35 min from now. Front-center projection for the lower membership gate only; optional goal_footprint keyword.

### 2026-10-05T01:47:34-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
Candidate 09fb1686ec9bddc07e682e54bb80e039bc86b112. Owned paths only. Exact snapshot-80 replay under the recorded options hands off
to (28.986133, 24.446254) with route_found 3/3 (0.61-0.67 s total, machine-dependent). 37 focused tests pass in 5.2 s.
See the Handback section. Three invocations used. No live work. Stopping edits for review.

### 2026-10-05T01:54:21-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW
Coordinator receipt-time relay; original timestamp line retained in source artifact, not asserted as model clock time. Review body follows unchanged.
Task: T-0008   Candidate: 09fb1686ec9bddc07e682e54bb80e039bc86b112   Scope: code
Verdict: approve-with-nits

Findings (ranked, ≤ 5):
1. [minor] tools/observed_navigation.py:149-172: No `hi >= lo` guard before target selection.
   Mechanism: if the shared span is inverted, `min(hi, max(lo, ...))` returns `hi`, which is outside any shared span. The lower gate now accepts an axle up to about 0.5 m further back, which slightly widens this degenerate window. `refine_corridor_guidance` returns early when the original target is clear, so it does not always catch the case.
   Evidence: read-only. UNVERIFIED: whether `propose_lane_corridor` guarantees an overlap for `visible_mouth`.
2. [minor] tools/tests/test_observed_navigation.py:362,377: Both planner tests assert only inside `if plan is not None`.
   Mechanism: a slow machine misses the 0.5 s wall budget, so the clear-path and wall/unknown assertions never run. The admitted-forward-plan claim then rests entirely on the external replay artifact. This is a documented trade-off, but it is a vacuous-pass risk.
   Evidence: read. UNVERIFIED: the artifact `d388f429…`.
3. [nit] tools/sensor_course.py:571: The recovery call-site change has no behavioral test.
   Mechanism: the diff only shows `goal_footprint=goal_footprint` being passed. I could not confirm that the name is in scope at that call. Only the planner path is covered.
   Evidence: diff only. UNVERIFIED: scope of `goal_footprint` there.
4. [nit] tools/tests/test_observed_navigation.py:401: The "already eligible" test is weak.
   Mechanism: lookahead 7 clamps the target to `hi` either way, so equal targets are nearly guaranteed. The test also calls the private `_near_mouth_target` directly.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓
- The relaxation only lowers the lower-gate station by `x_max·heading_dot`, which is ≥ 0, so it never narrows eligibility.
- Heading, lateral, upper (`axle <= hi`) and advance ≥ 1 m gates still use the axle.
- Missing or invalid footprints fall back to the axle test, and the tests cover this.
- Frozen guidance bypasses selection.
- No search, budget, footprint or auditor change.
- Diff stays within owned paths.

Tests run: none (read-only). The handback's "37 OK" is unverified by me.

Missing acceptance coverage:
- Sol's fixture provenance and replay-artifact check.
- ASTRA's combined run, including that the new `mouth_membership` diagnostic key does not break strict telemetry or snapshot validation (UNVERIFIED).
- Offline replay is not a live-lap improvement.
relayed-from: artifacts/agents/T-0008/sonnet-review-r1.md

### 2026-10-05T01:53:11.8684280-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0008   Candidate: 09fb1686ec9bddc07e682e54bb80e039bc86b112   Scope: evidence
Verdict: approve

Findings (ranked, ≤ 5):
1. No blocking evidence defect found. Source and fixture SHA256 match the provenance note; all eleven retained input fields equal original decision 80, including observed costs, broad destination and recorded planner options. Fixture adds only schema_version outside input.
2. Timing limitation: the unchanged 0.5-second setting governs the bounded search phase, checked periodically; continuation and surrounding planning work add time. Recorded 0.606–0.668-second totals establish neither an end-to-end 0.5-second deadline nor live success.

Observation: clean worktree HEAD matched candidate. Actual [-1.12,0.62,-0.52,0.52] footprint reaches both selectors. Only lower longitudinal membership changes; axle upper limit, heading/lateral/advance gates, target construction and independent collision/health/audit budgets remain. Front station 20.363395 crosses lower threshold 20.022706; proposed target [28.986133,24.446254] lies at shared-span upper station 24.039037.

Tests run: one read-only WSL Python replay of the byte-verified fixture with unchanged recorded options: route_found, 0.653 seconds total, 620 path points, full_footprint_sweep true; every returned pose independently rectangle-clear. Worker 37-test result inspected, not repeated. Initial verification assertion incorrectly assumed no schema_version wrapper; corrected before replay. Worker’s earlier test-only 30-second invocation is disclosed and absent from candidate.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓
Missing acceptance coverage: live execution, reaching the handoff, subsequent progress, recovery behavior and audited full-loop outcome. Local execution goal precedes the handoff; replay supports planning toward it, not arrival or a solved stall root cause. Usage: UNMETERED.
relayed-from: artifacts/agents/T-0008/sol-review-r1.md

### 2026-10-05T01:54:21-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION
Accept09fb168 for integration: Sonnet approves with nits and Sol independently verifies fixture/source hashes and observed-input replay. Integrate the single exact base..candidate commit, run combined core checks, then T-0009 may own one controlled live attempt. No new source edits after review; please remain idle during integration/trial.
Sonnet nits: detector rejects overlap below3m before returning a visible_mouth corridor (lane_corridor_policy339-342), so inverted shared spans cannot arrive through the current production selector. Actual goal_footprint is initialized from the existing local footprint at sensor_course382 and is in scope at recovery571. The conditional planner assertions certify safety only if a plan is found; timing-independent handoff assertions are unconditional, and successful route output is supported separately by worker3/3 plus Sol's independent recorded-input replay. The existing-axis eligible case intentionally confirms no target change; other controls exercise ineligible geometry. Internal front-coordinate parsing is not a general footprint validator; live inputs retain the existing measured-model footprint path. Combined checks will cover added diagnostics. Search setting remains0.5s, not an end-to-end deadline; measured totals0.606-0.668s include surrounding work. None of this proves arrival, backup recovery or a full lap. Sonnet exact model verified, API-equivalent USD0.1989434; Opus/Sol UNMETERED.

### 2026-10-05T01:59:59.1276186-07:00 · gpt-6-astra → claude-opus-5-5 · NOTE
Integrated exact candidate range as8f5e87766d5a7dffcba68da3917a7f101853d80d. Combined checks passed:478 tools +85 perception +4 GPS =567 tests. Log artifacts/agents/T-0008/integration-checks.log. Candidate/source equality checked. Live efficacy remains pending T-0009; stay idle during the exclusive trial.
