---
id: T-0021
title: Reduce avoidable replacement-path cancellation pauses with fresh observed checks
status: changes-requested
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0021-replacement-continuity-opus
base: 02cea958ccc9cd051241170c58ed1cbcd929a697
candidate: e0829c55e31063baad1323780f4b39fc60b05aac
claim: tested
lease: none
updated: 2026-10-05
---

# T-0021: Own the development slice for replacement-path continuity

## Packet

- User-approved ADR011 ownership: investigate, choose implementation, add meaningful tests, revise and commit without intermediate permissions. Existing interactive Opus5.5. Worktree C:/Users/brand/.codex/worktrees/igvc-t0005-health-capture/IGVC SIM prepared clean at 02cea958 on codex/t0021-replacement-continuity-opus. T0019 recorder already included; do not alter it.
- Read README, knowledge sensor-led-navigation, tools/sensor_course.py replacement admission/cancel/send path, tools/path_entry.py and relevant existing action-cancellation/recovery contracts. Primary T0018 evidence and artifacts/agents/T-0021/inputs are bounded context. No full logs/CAD/network.
- Problem: current direct-path replacement rejection cancels the existing FollowPath action. T0018 has31 admission rejections,26 start_pose_departed_checked_path; T0016 has41; priorT0010 has57. This does not prove every cancellation was avoidable. Frozen examples pair prior sends with rejections, but DO NOT prove the prior action was still active. Planner captures are submission-time observations, not exact latest admission grids. No exaggerated replay claims.
- Objective: implement an OPT-IN, behavior-tested way to avoid an unnecessary stop when a replacement is rejected but a previously admitted path remains usable under current observations. You choose the design; a freshly validated/resubmitted suffix may be safer than blindly retaining an existing action. It is acceptable to reject the hypothesis if you cannot satisfy the invariants.
- Hard conditions: only an actually accepted active path for the same destination/action identity; latest checked pose and current observed costmap; unchanged full-footprint connector/suffix sweeps, cross-track .10, heading .15, turn radius .65, connector limits, unknown blocking and freshness/health gates. No widening, no stale-map reuse, no simply ignoring admission failure. Invalid/missing/consumed/blocked/old-destination/cancelled/completed paths follow the current fail-closed cancellation behavior. One bounded fallback attempt per replacement, no recursive retry or unbounded planning. Validate freshness again after any work as needed.
- Keep default behavior unchanged behind an explicit CLI option (name chosen by you). Record configured mode, fallback decisions/reasons and source fingerprints so a live experiment can distinguish enabled behavior. No new ROS message/interface or Nav2/profile/speed changes. Command/action identity, outcomes and destination advancement must remain coherent.
- Owned paths: tools/sensor_course.py; new tools/replacement_path.py if useful; tools/tests/test_replacement_path.py; directly relevant existing Python tests if essential; tools/agents/iteration-live.ps1 ONLY to pass this explicit opt-in boolean from job config safely (absent defaults off; reject malformed nonboolean values). No other runner redesign. Source/docs report in primary artifacts/agents/T-0021/REPORT.md and review-inputs.md; task log append-only.
- Acceptance tests must execute actual admission/sweep behavior, not string assertions: rejected replacement plus valid active path; active path now blocked/unknown; excessive pose error or consumed suffix; wrong destination/action/inactive path; stale data; cancellation failure behavior where applicable; successful replacement bypasses fallback; fallback mode off preserves behavior; coherent selected plan/goal metadata. Use meaningful synthetic observations and bounded frozen replay only where provenance supports it. Test CLI/runner wiring to the extent possible; disclose live gaps.
- T0020 third repeat is running in DIFFERENT frozen checkout. Light inspection/design/source edits allowed now; no tests/replay/builds until primary artifacts/iterations/2026-10-05/connector-repeat-3/live.json stage finished AND shutdown_verified true. Then proceed directly with focused checks without new dispatch. Do not launch/stop a simulator or acquire its lease.
- <=40min active work plus lease wait; <=3 focused test invocations; no recursive agents/provider retries/fullsuite/Unitybuild/live run. Own-branch commits only. Exact candidate and <=300word handback with tests/limits, source range and knowledge concepts. Independent Sonnet/Sol review and integrator live A/B decide acceptance; no speed or performance claim from offline tests.

## Handback

Revision 1 by claude-opus-5-5. Candidate e0829c55e31063baad1323780f4b39fc60b05aac (base 02cea95).
Report: artifacts/agents/T-0021/REPORT.md; review-inputs.md staged.

```text
Design: opt-in --revalidate-active-path (default off). On a rejected checked-path replacement, keep the running
  FollowPath only if: an ActivePathRecord exists (the admitted plan actually sent and accepted); the action is still
  running; the goal ID taken from the running handle equals the record (a BackUp cannot match); the destination is
  unchanged; ONE unchanged prepare_controller_plan call on the running plan from the latest pose and latest grid
  admits it (same 0.10/0.15/0.65 limits, connector and suffix full-footprint sweeps, unknown blocking, consumed
  check); and check_live passes afterwards (stale raises, so the mission stops as today). Kept means no new goal, no
  modification and no resubmission; target stays the running goal; outcome not_sent with retained_active_goal_id.
  Everything else uses the existing cancel. Off mode is identical apart from a recorded mode summary.
Paths: tools/replacement_path.py (new), tools/tests/test_replacement_path.py (new), tools/sensor_course.py (+44/-1),
  tools/agents/iteration-live.ps1 (+8: optional JSON boolean revalidate_active_path; non-boolean or combined with
  record_episode is rejected before any runtime work).
Evidence recorded: state.replacement_fallback {mode, evaluated, retained, reasons}; per-decision replacement_fallback
  events (on only); replacement_path.py fingerprinted.
Tests (after T-0020's verified shutdown): 64 OK (2 existing skips) using real admission: kept; lethal/unknown suffix;
  cross-track, heading and consumed; identity, destination and activity fail closed without recheck; stale;
  successful replacement and disabled mode never run the fallback; revalidates the running plan. The launcher parses
  with 0 errors.
Untested offline: CLI parsing and ROS wiring; launcher execution; any stop or time benefit (needs a live A/B). Not
  related to T-0020's 2/6 backup failure. Knowledge: sensor-led-navigation (path entry). 2 invocations. UNMETERED.
```

## Log

### 2026-10-05T04:28:10.342989-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
You own this complete development task under ADR011. Choose and implement the
smallest safe opt-in continuity improvement, including its tests and bounded
launcher flag, without pausing for design approval. Source base/worktree prepared.
T0020 owns runtime; author lightly now, run focused checks after its verified
shutdown. Preserve all admission/sweep/freshness/action-identity boundaries.
Return completed immutable slice or a supported rejection, not merely a plan.

### 2026-10-05T04:28:25-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
DISPATCH received (ADR-011 slice ownership). Worktree igvc-t0005-health-capture on codex/t0021-replacement-continuity-opus at 02cea95.
Opt-in only, default unchanged. Light authoring now; focused tests only after T-0020 connector-repeat-3 live.json shows finished and
shutdown_verified. No lease.


### 2026-10-05T04:32:30.365979-07:00 · gpt-6-astra → claude-opus-5-5 · NOTE
T0020 finished and shutdown_verified=true; focused tests may proceed under your existing assignment. Third frozen-version run FAILED at2/6 in226.30s, reason no observed collision-free backup with useful forward clearance. No promotion; failure evidence being analyzed. Preserve task scope and safety; do not assume this failure is caused or fixed by replacement fallback. Updated evidence will be linked once compact summary is ready.

### 2026-10-05T04:33:07-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
Candidate e0829c55e31063baad1323780f4b39fc60b05aac (4 owned files, +229/-1). Opt-in --revalidate-active-path keeps a running
FollowPath only after its own plan re-passes unchanged admission at the latest pose and grid, for the same handle and destination,
with freshness re-checked; otherwise the existing cancel. Default off is unchanged. 64 focused tests OK (after T-0020's verified
shutdown); the launcher parses. No live or performance claim; does not address the T-0020 failure. See the Handback section. Stopping.

### 2026-10-05T04:39:54.183617-07:00 · claude-sonnet-5-5 → claude-opus-5-5 · REVIEW
relayed-from: artifacts/agents/T-0021/sonnet-review-r1.md
Candidate e0829c55e31063baad1323780f4b39fc60b05aac. Exact-model CLI review, cost USD0.0932214 API-equivalent.

**Verdict: request changes.** Default-off behavior and the launcher validation look sound. The core retain rule isn't justified by what it checks. I reviewed the diff only, and I haven't seen `path_entry.py`.

**Ranked findings**

1. **High: the check validates a path the controller never follows.** `revalidate` returns a new connector+suffix from the latest pose, and `replacement_outcome` keeps only `admitted is None`. The old FollowPath keeps running its own geometry, so the controller's own rejoin motion is never swept. A non-null return from `prepare_controller_plan` does not show that the executing command path matches what was checked.
   - **Strong geometric evidence could close this gap:** the cross-track (0.10) and heading (0.15) gates bound the divergence, so the old path may be nearly identical to the checked suffix. The code never asserts that, though.
   - **Fix:** require the returned plan's suffix to be an index-aligned slice of `active.plan['path']` within grid resolution, with connector length bounded, and log both. Otherwise cancel, or send the returned plan.
   - **Test gap:** the keep test puts the pose exactly on the path (2.8, 3.0, 0), so the connector is trivial. Add a keep case at roughly 0.09 m and 0.14 rad, plus a case where the suffix diverges.

2. **Medium: API compatibility.** `run()` reads `args.revalidate_active_path` unconditionally. Any caller that builds its own Namespace, such as a record-episode path or tests, would raise `AttributeError`. Use `getattr(args, 'revalidate_active_path', False)`, or grep for callers. Also confirm that `direct_path` is bound on every path through `run()`, including nav2-goal mode.

3. **Medium: the runtime wiring is untested.** Nothing exercises these:
   - `bytes(handle.goal_id.uuid).hex()`
   - `result.done()`
   - the closure reading `latest['grid'][1]` and `latest['pose']`
   - the record being created only after the server accepts the goal. Claim 1 says "accepted", but the diff doesn't show that ordering.

   A missing grid raises `KeyError` and crashes the mission instead of cancelling. Extract the identity and running-state derivation into a ROS-free helper and test it with fake handles.

4. **Low: freshness and coherence.** `check_live` after the work covers staleness only. It doesn't confirm that pose and grid come from one snapshot. Read both once. Also add the connector length and divergence to the admission diagnostics so retained decisions are auditable. There is also no cap on consecutive retentions.

5. **Low: the runner flag is only syntax-parsed.** Execute the config-validation branch with a stub for `true`, `"true"`, `null`, and `true` plus `record_episode`.

**Confirmed fine:** identity comes from the live handle, and a BackUp action can't match. Destination and activity gates fail closed. The `target` and `not_sent` metadata are coherent. `source_sha256` is updated. The T-0020 2/6 failure is correctly left separate, with no fix claimed.
### 2026-10-05T04:39:54.183617-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION
Revision round 1: proceed autonomously within T0021 ownership; no new permission
needed. Root agrees with the blocking geometry finding: prepare_controller_plan
returns a new connector plus suffix but the implementation retains execution of
the OLD path. Passing a check of unused geometry is insufficient. Select and
implement a safe design that executes the geometry actually validated, or reject
the hypothesis. A freshly admitted fallback submission is a reasonable option;
simply bounding divergence does not demonstrate that controller rejoin is swept.
Do not widen admission or footprint thresholds.

Address each remaining review item by a fix, behavior check, or source-supported
disposition. Add nontrivial offset/heading cases, fake live-handle/running-result
and missing-grid behavior checks, exact selected-plan/action metadata, and bounded
runner flag validation. Preserve default-off behavior. Read relevant path_entry
implementation, not only the review (reviewer did not inspect that helper).
At most 3 focused invocations and 25 minutes this revision; no live, full suite,
Unity build or provider calls. Return exact new candidate plus concise evidence.
Runtime is shut down, so tests may proceed. T0020 is a separate failed trial;
no claim this fixes its missing useful-backup failure. Sol will review corrected
candidate rather than duplicate review of known-blocked code.
