---
id: T-0036
title: Explain the first2029 perception and clock freshness interruption
status: integrated
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0036-freshness-interruption
base: d6519e1ee323db0e66fd5953959f07cc56508cc5
candidate: 0779593c8b077da4c8b47c5a497c47b6dc29df93
claim: tested
lease: none
updated: 2026-10-05
---

# T-0036: Bounded diagnosis and evidence-supported repair

## Packet

- Interactive Opus owns this bounded slice through diagnosis and any justified
  scoped correction, tests and handback. Read README, this packet, processing-health
  concept and relevant T0005 first-failure capture semantics; no complete history.
  Clean worker C:/Users/brand/.codex/worktrees/igvc-t0005-health-capture/IGVC SIM,
  assigned branch at d6519e1. No live session active or authorized here.
- PRIMARY artifacts/iterations/2026-10-05/nearer-gate-2029-1 is the first2029
  attempt: stopped2/6 at121.428575356s,12/20 audit, health1209pass7fail0unknown,
  maxgap0.123985376s, complete interval. Autonomy latch says perception receipt
  ages0.772s and clock age0.907s exceeded0.750s. No backup charged.
- Inputs: run.json (first-verdict snapshot, health recent events, timestamps,
  trajectory tail and decisions78..81 only), health-diagnosis.json, bounded relevant
  ros-session/nav-session/unity/mission logs. No course/mission/WORLD/reference
  geometry; no need to load full grid/camera files unless a specific evidence need.
  Inspect exact publishers/callbacks/timeout functions only when implicated.
- Establish a timeline across monotonic, ROS/wall and acquisition clocks without
  equating incompatible timestamps. Distinguish upstream sensor/clock silence,
  processing backlog, callback starvation, transport, shutdown and host stalls.
  ROS endpoint disconnect at1791210188.635 follows the autonomy latch at
 1791210178.563 by10.072s; do not mistake cleanup disconnect for original cause.
  Unity log lacks uniform event timestamps. Absence of a log is not proof of health.
- The old frozen source passed three2027 laps and one2028 regression; source19,
  profile and player are unchanged. This does not rule out a sporadic defect or
  prove CPU load caused it. Coordinator ran only light doc/metadata work during
  this trial, no local tests/builds/replays; unmeasured other-host load remains unknown.
- If exact evidence demonstrates a LOCAL diagnostic parsing/reporting defect,
  you may correct tools/diagnose_processing_health.py and focused diagnostic tests.
  These are the only owned production paths. A real runtime repair outside them
  requires a handback with precise source ownership and acceptance proposal; do
  not invent a fix without timing evidence. You own choosing the best supported
  diagnosis, not a mandatory code change. This is a meaningful complete handback.
- Preserve ALL thresholds, freshness latch, health sampling/audit semantics,
  footprint, navigation and recovery. No auto-enable, timeout increase, failed-run
  exclusion, artificial timestamp updates, course knowledge or quiet rerun.
  No Unity build, new interfaces, dependencies, ROS/source edits beyond scope.
- <=20min active work, <=3 focused analysis/test commands, two revisions; no
  provider/delegation/live sessions. Usage UNMETERED. Stop with actual evidence,
  uncertainty, smallest targeted next capture/repair (if required), changed paths,
  tests and clean commit only if source changes. Preserve original failed evidence.
- Write bounded artifacts/agents/T-0036/REPORT.md and compact timeline JSON in
  PRIMARY; <=300word handback in this canonical task log. No task commits inworker.
  Knowledge: processing-health; ros-unity-transport; trial-audit-promotion.

## Handback

Current: revision 1, candidate 0779593c8b077da4c8b47c5a497c47b6dc29df93 (additive diagnostic reporting; see REPORT.md "Revision 1" and the latest HANDBACK). Original: claude-opus-5-5. Diagnosis only: no source change, no commit. Report: artifacts/agents/T-0036/REPORT.md and timeline.json.

```text
Evidence:
- At the first health failure (telemetry 128.06 s, sim 127.54 s), every simulator-origin stream was silent: clock
  0.394 s (normally about every 1 ms), rgb 0.395, depth 0.480, scan 0.591 s. Lane and depth processing still
  published (0.07 s) and reported no_new_pair. Their last sim stamps stop within about 0.2 s of each other.
- Near the failure the sim-to-wall ratio was 0.868 (0.992 for the whole run); odom sim stamps stayed continuous.
- The latch at epoch 178.563 (0.772/0.907 s vs 0.750 s) behaved as designed. The endpoint disconnect at 188.635
  follows the shutdown SIGINT at 188.571, so it is a cleanup consequence.
- Unity "Queue full" warnings appear in every run from startup (58-162 per run, passing runs included) and are
  untimestamped, so not distinctive. I rejected my initial hypothesis.
Diagnosis: a roughly 0.9 s Unity-side or Unity-to-ROS delivery stall. Unity hitch vs connector send stall vs host
  contention vs WSL networking is undetermined. Not navigation, recovery or perception logic; no gate change indicated.
Reporting gap: health-diagnosis reports clock max gap 0.104 s although it was silent for at least 0.907 s, because
  only closed intervals are counted. Smallest owned repair: add per-stream open trailing gap plus an "all sim-origin
  silent while processing alive" flag in diagnose_processing_health.py with tests. Proposed, not done (3 commands used).
Next capture (outside owned paths): Unity per-frame wall stamp and outgoing-queue depth at 1 Hz and on queue-full,
  endpoint receive stamps, host CPU at 1 Hz.
Limits: no monotonic/epoch mapping; untimestamped Unity log; host load unknown; one event.
```

## Log


### 2026-10-05T07:26:13.3646332-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
Startnow, runtime stopped and exclusivelease released. Offlineboundedanalysis allowed. Do not repeat2029/launch2030 or alter safetygates. Diagnoseactual firstfailure before proposingbehaviorchanges. RawSoltrialreview runsindependently; no overlapping ownedsource.


### 2026-10-05T07:26:27-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
T-0036 accepted. Offline diagnosis of nearer-gate-2029-1, from the first-failure snapshot, health diagnosis, bounded logs and decisions 78-81. No live run, gate change or course data.

### 2026-10-05T07:28:11-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
Diagnosis-only handback (no source change). Every simulator-origin stream (clock, rgb, depth, scan) went silent together while ROS processing stayed alive, with the sim slowed to 0.868x near the failure: a roughly 0.9 s Unity-side or Unity-to-ROS delivery stall; the finer cause is undetermined. The latch worked as designed; the disconnect is cleanup. Queue-full warnings are chronic in all runs, so not causal evidence. A health-diagnosis reporting gap (open trailing gaps uncounted) has an owned repair proposed for revision. See the Handback section and REPORT.md. Stopping.

### 2026-10-05T07:34:00-07:00 · gpt-6-astra → claude-opus-5-5 · REVISION

Proceed with the proposed additive diagnostic reporting repair in your same owned paths and branch. New bounded allowance: 20 minutes active, up to three focused test/analysis commands, no live runs or provider calls. Report verified first-failure snapshot receipt ages separately from closed interarrival maxima, with exact clock/snapshot provenance; never substitute the later adapter's 0.907s for the snapshot's 0.394s. Missing, invalid or unbound ages must remain unavailable. Preserve report fields and all audit/runtime behavior. Any correlated stream-silence indicator must expose its assumptions and thresholds as diagnostic-only, treat absent data as unknown, and never assert Unity, transport or host causality. Do not add a flag unless its semantics can be defensibly tested.

Preserve REPORT-r0.md and timeline-r0.json before revision. Soften categorical exclusions of perception/navigation/callback causes: fresh processing reports demonstrate those callbacks ran, not that every upstream subscriber/executor was healthy. The evidence shows delivery interruption at observed subscribers; location and mechanism remain unproven. Sol is reviewing the original diagnosis independently and findings will follow. Add behavioral tests for trailing silence larger than closed maximum, missing/invalid/mismatched snapshots, and a normal fresh snapshot. Commit owned source only; hand back exact commit, test evidence and revised report. No task docs in worker commits. Stop after this revision for independent code/evidence review.

### 2026-10-05T07:35:26-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
Revision 1: candidate 0779593c8b077da4c8b47c5a497c47b6dc29df93 (base d6519e1; owned
tools/diagnose_processing_health.py and tools/tests/test_health_failure_capture.py; +122/-3).
- New first_failure_stream_receipt, from a valid bound fail snapshot only: per-stream receipt age at that instant
  beside the closed inter-arrival max, an exceeds flag and list, and exact snapshot clock provenance.
- Invalid or missing values are unavailable; an invalid snapshot makes the section unavailable with its reason.
- Never uses the latch's 0.907 s. No threshold, cause or correlated-silence flag (not defensibly testable).
- Whole-run fields are kept, plus max_gap_scope (closed intervals only).
Tests: 36 OK.
- New: trailing silence beyond the closed max; silence that closes later; normal fresh snapshot;
  absent and mismatched snapshots; invalid ages.
- My first run had one wrong assertion (the fixture's silence closed); fixture fixed, both cases now covered.
On the 2029 run: all 7 input streams exceed their closed max (clock 0.394 vs 0.104 s); the 4 processing streams
do not (about 0.07 s).
Report revised (originals preserved as REPORT-r0.md and timeline-r0.json): the categorical exclusions are softened
to a delivery interruption at the observed subscribers, with location and mechanism unproven. Stopping for
independent review.


relayed-from: artifacts/agents/T-0036/sol-review-r1.md

### 2026-10-05T07:33:29-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0036   Candidate: none; diagnosis bound to runtime d6519e1ee323db0e66fd5953959f07cc56508cc5   Scope: evidence
Verdict: request-changes (diagnostic reporting; no runtime repair justified)

Findings (ranked, ≤ 5):
1. [major] REPORT.md, Diagnosis: categorical “not navigation/recovery/perception” and exclusion of callback starvation/backlog are unsupported. Fresh timer/status publications prove some processing activity, not service of every subscription or absence of a sporadic defect. Ages locate missing receipt at these subscribers; Unity production, connector/network delivery and subscriber scheduling remain alternatives. Prior passes do not exclude defects.
2. [minor] Reporting gap: at first failure, mission clock open age is 0.394s versus closed maximum 0.104s; final telemetry exports age/tail maximum 0.926s. Adapter's 0.907s is another observer at an unmapped epoch time. Do not merge these into one precisely timed 0.9s stall. The 0.868 ratio measures received odometry-stamp advancement between decisions, not Unity throughput.
3. [minor] timeline.json: disconnect after SIGINT is consistent with cleanup, not a proven causal consequence. Untimestamped queue-warning counts reproduce across passing runs; this rejects their discriminatory value, not every queue-pressure hypothesis.

Verified bound first-failure snapshot, false processing flags/no-new-pair reasons, receipt ages, health totals and ROS-log ordering. Cancellation follows latch by 16.8ms; disconnect follows it by 10.072s. Closed-gap versus open-age omission in diagnose_processing_health.py is real; telemetry retains both.

Minimal acceptance repair: qualify REPORT/timeline observations versus hypotheses; retain subscriber-starvation uncertainty. An optional diagnostic change should label closed maximum, first-snapshot open age and final tail maximum with observer/clock/scope; missing data stays unknown. Any “upstream silence” flag must describe subscriber observations without identifying a producer cause. If implemented, test trailing silence, closed intervals, absent snapshots and distinct clocks; preserve thresholds/original evidence.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 requires claim correction.
Tests run: none (read-only source/JSON/log checks). Missing coverage: producer/endpoint timing, scheduling and host-load evidence. Usage: UNMETERED.


### 2026-10-05T07:35:35.4556403-07:00 · gpt-6-astra → claude-opus-5-5 · NOTE

Apply these evidence corrections with the already authorized revision. Include final telemetry age/tail maximum if retained; label all three scopes separately. Treat SIGINT/disconnect ordering as consistent with cleanup, not causal proof. The ratio measures received odometry stamp advancement, not measured Unity throughput. No runtime fix justified yet. No additional command allowance is needed for reading this review.


### 2026-10-05T07:36:07-07:00 · claude-opus-5-5 → gpt-6-astra · NOTE
Root 07:35 corrections applied to REPORT.md (no source change):
- Three scopes labelled separately: snapshot age (clock 0.394), closed max (0.104), final telemetry age and tail max (0.926).
- Correction: raw telemetry already retained max_gap_including_tail_s. Only the diagnostic summary omitted it; surfacing it is proposed, untested.
- The ratio is received odom-stamp advancement, not Unity throughput.
- The SIGINT/disconnect ordering is consistent with cleanup, not proof.
- No runtime fix is justified.
Candidate unchanged at 0779593. All 3 revision commands used. Stopping.

### 2026-10-05T07:37:29.9141516-07:00 · gpt-6-astra → claude-opus-5-5 · NOTE

Before evidence re-review, consolidate REPORT.md and timeline.json into coherent current documents. Original -r0 files preserve history; do not leave contradictory stale headings/claims in current files with corrections appended far below. Current report still starts 'no source change', says simulation throughput and proven cleanup consequence, and labels the repaired gap unfixed. Current timeline still labels cleanup causal. Apply already requested corrections in place, document source0779593 and36 passing focused tests, distinguish proposed final-tail reporting from implemented snapshot reporting. Documentation-only authorization, no more code/test commands. Append brief done note; then stop. Sonnet will review immutable source while this clarification finishes.


### 2026-10-05T07:38:23-07:00 · claude-opus-5-5 → gpt-6-astra · NOTE
Done: REPORT.md and timeline.json rewritten as coherent current documents, with -r0 files preserving history. Corrections applied in place:
- source 0779593 documented with 36 passing tests
- implemented snapshot reporting separated from the proposed final-tail reporting
- four silence scopes labelled
- the ratio is odom-stamp advancement
- cleanup ordering is consistent, not proof
- no runtime fix
Documentation only; no code or test commands. Stopping.

### 2026-10-05T07:46:20.8960285-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0036/sonnet-review-r1.md

**Verdict:** Acceptable as additive offline reporting; I found no blocking defect. Two hardening gaps are worth closing before the report prose cites this section. Nothing here addresses the runtime interruption, and the root cause stays undetermined.

**What holds up**
- **Snapshot binding:** The section is gated on `_validate_snapshot` (ledger identity, clock binding, section types). It reads only `fail.subscriber_observations`, and the code never touches latch-message ages or whole-run tail ages.
- **Closed vs open:** The clock-binding mismatch test and the `resume=True` test show the open age (.4) and the later-closed whole-run maximum (.5) staying separate.
- **Bad values:** Missing, bool, string, list, NaN, inf and negative ages all come out as `unavailable`.

**Findings, ranked**
1. **Medium: no physical-consistency bound.** A finite age or closed max larger than `clocks.telemetry_elapsed_s` is impossible, yet it passes and can flag "exceeding". Binding covers the snapshot clocks, not the per-stream values, so the producer's computation at the same instant is trusted, not verified. I'd mark such values unavailable and test it.
2. **Medium: degenerate closed max.** A stream with zero or one message can report `max_gap = 0.0`, so any positive age gives `exceeds=True`. Latched or low-rate streams (`*_info`, for example) are exposed to this. Require a nonzero closed max, or surface the interval count if telemetry has it.
3. **Low: the exceeding list hides gaps.** Streams with unavailable values are silently omitted, so the list reads as complete when it isn't. Add an `unavailable_streams` list or count. Non-dict observation entries also appear as stream rows.
4. **Low: weak test assertions.**
   - `assertNotIn('cause', semantics.split('does not')[0])` only checks a constant string.
   - The bad-value loop covers `receipt_age_wall_s` only, not `max_gap_wall_s_so_far`.
   - There are no tests for age == closed max (strict `>`), closed max 0, an empty observations dict, or that a later-age field is ignored. The no-conflation property is currently true by construction, not by test.
5. **Note: telemetry-side claims.** The `max_gap_scope` wording ("closed intervals only") is supported empirically by the `resume=False` test (.1 < .4). The diff doesn't show the telemetry source, so I can't confirm it independently.

**Real-data output:** Seven input streams exceed their closed maxima while the status streams are fresh (~0.07 s). The code correctly draws no correlation or cause. Final-tail age is still pending, as you stated.

relayed-from: artifacts/agents/T-0036/sol-review-r2.md

### 2026-10-05T14:44:20+00:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0036   Candidate: 0779593c8b077da4c8b47c5a497c47b6dc29df93   Scope: evidence
Verdict: approve-with-nits

Findings (ranked, ≤ 5):
1. [minor] artifacts/agents/T-0036/REPORT.md:46: Untimestamped, nondistinctive queue warnings do not reject their contribution to this interruption. Replace “rejected” with “unsupported”; retain connector pressure among unresolved mechanisms. Line 17 also groups derived ROS lidar_processing status with simulator-originated inputs; distinguish these origins.
2. [nit] tools/diagnose_processing_health.py:120: Optional hardening: an age exceeding telemetry elapsed remains accepted, and a one-message stream's zero maximum denotes no completed interval. Preserve unknown comparisons for these cases. Neither affects this snapshot: every stream count exceeds one, and every age is within elapsed time.

Evidence: Windows Git exact-range inspection found only the diagnostic and focused tests changed, with clean candidate HEAD. Independently read the original 2029 snapshot: its ledger identity exactly matches first_fail; origin subtraction gives 128.06340082 s. Seven streams have open receipt ages exceeding their completed-interval maxima. Clock receipt age 0.394011062 s and closed maximum 0.104247074 s support the new descriptive summary. Final tail 0.926 s and later adapter age 0.907 s remain separate observations. Revised report/timeline leave upstream mechanism, subscriber starvation and node cause undetermined.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓.
Tests run: none (read-only). Inspected producer-backed silence/resumption, fresh, missing/mismatched snapshot and malformed-value tests; revision1-check.txt records 36 passing tests, not independently rerun. A Windows Python lookup failed before execution; PowerShell performed the raw JSON read.
Missing acceptance coverage: Final-tail summary fields remain expressly unimplemented/untested. No runtime fix, new trial, causal attribution or promotion established; original failed run/audit preserved.
Usage: UNMETERED.


### 2026-10-05T07:46:20.8960285-07:00 · gpt-6-astra → all · DECISION

Accept additive diagnostic candidate0779593 with nits. Root corrected current report origin wording (lidar_processing is derived ROS status) and unsupported-versus-rejected queue hypothesis. Both reviewers have no code blocker. Optional malformed/one-message hardening is deferred: the actual snapshot has multiple messages per stream and values within elapsed time; this descriptive report is not a gate or causal classifier. Original evidence and reports preserved. Final-tail summary fields remain pending. Sonnet exact-model usage0.1000494USD API-equivalent; Sol UNMETERED. No runtime repair or promotion. Integrating source and focused tests next; T0037 captures missing producer timing before another trial.

### 2026-10-05T07:46:50.5790187-07:00 · gpt-6-astra → all · INTEGRATION

Integrated as b1aada7. Primary targeted integration check:36 tests passed in0.043s, artifacts/agents/T-0036/integration-check.log. No runtime/player/policy change, no live trial, no promotion. New summary is offline and descriptive; source19 runtime remains frozen atd6519e1. All original failure/audit bytes unchanged. T0037 owns new opt-in capture code; integrator retains explicit hookup/build/launch authority.
