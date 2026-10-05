---
id: T-0021
title: Reduce avoidable replacement-path cancellation pauses with fresh observed checks
status: accepted
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0021-replacement-continuity-opus
base: 02cea958ccc9cd051241170c58ed1cbcd929a697
candidate: 11a93b85e79fb5f58f07192dd3dfdb62883896b1
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

Superseded by revision 1: candidate 11a93b85e79fb5f58f07192dd3dfdb62883896b1 (sends the revalidated connector+suffix;
see REPORT.md "Revision 1" and the latest HANDBACK below). Original: claude-opus-5-5, candidate e0829c55e31063baad1323780f4b39fc60b05aac (base 02cea95).
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

### 2026-10-05T04:43:07-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
Revision 1: candidate 11a93b85e79fb5f58f07192dd3dfdb62883896b1 (parent e0829c5; base..candidate is 4 files, +336/-7).
The blocking finding is accepted, so there is no retain branch now. The running plan is re-admitted once on the same
pose/grid snapshot that rejected the replacement, with unchanged limits. Its returned suffix must equal the running
path's index-aligned tail. Freshness is re-checked. Exactly that returned plan is sent through the normal FollowPath
send path; anything else cancels as before, and default off is unchanged.
Also:
- ROS-free running_action and snapshot_revalidator helpers; a missing snapshot cancels
- getattr default; added diagnostics; no-cap disposition
Evidence: 69 focused tests OK (2 existing skips), including:
- a 0.09 m / 0.14 rad nontrivial connector
- a diverged suffix
- fake handles
- a missing snapshot
- a wiring contract
The launcher parses with 0 errors. Its exact validation lines were executed for 8 configs (artifacts/agents/T-0021/flagcheck-r1.ps1).
Withdrawn: the "no resubmission" claim, since a fallback now sends a new goal. No live or performance claim; not related
to T-0020. 2 of 3 invocations used. Details are in REPORT.md "Revision 1" and review-inputs.md. Stopping.

### 2026-10-05T04:46:47.772416-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW
relayed-from: artifacts/agents/T-0021/sonnet-review-r2.md
Candidate 11a93b85e79fb5f58f07192dd3dfdb62883896b1. Exact-model CLI review; USD0.1518634 API-equivalent.

**Verdict: approve.** The prior blocker is resolved, with two items to confirm against code the diff doesn't show (findings 1 and 2). I made no tool calls, so everything below comes from the diff and the helper you pasted.

**Blocker status: resolved by construction.** `replacement_outcome` returns the exact dict `prepare_controller_plan` produced, and the wiring does `admitted = fallback_plan`. That plan then flows through the normal send, acceptance and record path. The old action is never kept alive on unswept geometry, and the retain branch is gone. Revalidation uses the rejecting `entry_pose`/`entry_grid` snapshot, and `check_live` runs afterwards.

**Ranked findings**

1. **Medium, new in this diff, unverifiable here: the wiring branch is never executed by any test.** Its only coverage is source-string assertions. Please confirm against the unchanged context:
   - `entry_pose`, `entry_grid` and `goal_footprint` are in scope and are the rejecting snapshot.
   - `outcomes.update(..., fallback_from_goal_id=..., fallback_from_sequence=...)` accepts arbitrary fields. A `TypeError` here would crash only option-on runs.
   - `check_live`'s signature matches the lambda.
2. **Medium, new: possible watchdog masking and controller churn.** Each fallback is a fresh goal send with no consecutive cap. "Strict suffix" shrinks only as the robot advances, so a slow or stalled robot can be resent every decision cycle. Check whether the no-progress watchdog resets on `sent_goal`. If it does, repeated fallbacks could hide a stall. A consecutive-send counter or cap would be cheap insurance. Counts are recorded, but they don't bound anything.
3. **Medium, new: replacement intent is discarded.** The destination index is the only "same goal" check. The worker's rejected replacement may have had a different local goal, such as a new entrance or recovery choice. The old geometry is sent instead. Also confirm that entrance, trap-memory and recovery state aren't updated from the rejected replacement's goal while the sent path is the old one.
4. **Low, new: outcome metadata.** `outcomes.update(..., admitted=False)` runs before the fallback, so the decision's outcome reads "not admitted" even though a goal is sent. The `sent_goal` event carries the old `target` and yaw under the new sequence, with no fallback marker. It is correlatable via `replacement_fallback` and `fallback_from_*`, but it could confuse downstream consumers.
5. **Low, new: `_suffix_matches` is tautological.** Against the real admission function it always passes, because the tail is literally `points[join:]`. It only works as an invariant guard. The test of it injects a fake diverged result, which is fine, but it is not evidence of swept geometry.
6. **Low, pre-existing: snapshot age.** The send starts from `entry_pose`, not the current pose. A post-work `check_live` checks the latest streams, not the snapshot's age. The normal `send_new` path has the same property.
7. **Low, new: launcher failure visibility.** The `.ps1` throw happens before `live.json` exists, so a bad config surfaces only as a non-zero exit with no failed state. Boolean-only handling, `null` rejection and the `record_episode` guard all read correctly.

**Test scope.** The unit tests run the real `prepare_controller_plan` on a synthetic grid through the extracted `replacement_outcome`, `running_action` and `snapshot_revalidator`. They are not a live launch. The fail-closed cases (consumed, blocked, unknown, missing snapshot, stale, identity and destination) are covered at that level. The `.ps1` was parsed and its validation lines executed for 8 configs, but the launcher itself was not run. No performance claim is supported.

**Default-off.** The diff shows no behavior change when the option is off. The `mode: off` summary and record bookkeeping are the only additions.

**T0020.** Separate, and not addressed by this diff.
### 2026-10-05T04:46:47.772416-07:00 · gpt-6-astra → all · NOTE
Root disposition of Sonnet's conditional findings:
1. entry_pose/entry_grid/goal_footprint are the same in-scope admission variables;
DecisionOutcomes.update(index, **fields) accepts metadata; check_live(now,
armed_at, initial_run) matches. Source-string wiring tests do not execute ROS.
Live acceptance is still pending.
2. progress_at resets only after measured >=0.15m motion or completed backup;
sending/replacing a goal does not reset it. stalled uses >20s/no motion or failures.
Repeated fallback cannot bypass that wall-time watchdog. Goal churn remains an
experimental performance risk, not a demonstrated benefit.
3. Entrance updates use observed evidence; trap records/recovery-intent install
occur in the separate recovery branch. The fallback does not install rejected
replacement guidance. Old local intent may persist within the same broad GPS
destination; unchanged admission, consumed-path and progress gates still apply.
4. admitted=False describes the rejected NEW proposal, with fallback_from_* linking
the different sent geometry. Consumers must use these fields and events together;
the sent counter counts selected submission attempts, not server acceptances.
No classifier/performance claim based on that counter alone.
5. Exact suffix check is defensive, not independent swept-geometry evidence.
6. Existing admission-to-send snapshot timing limitation remains, and fallback adds
work. The live experiment must report timing/health without calling latest-stream
freshness a proof of zero pose drift.
7. Malformed config exits before runtime; extracted validation checks are not a
complete launcher test.
Final independent Sol review still pending; no integration or live claim yet.

### 2026-10-05T04:49:13.110802-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
relayed-from: artifacts/agents/T-0021/sol-review-r1.md

### 2026-10-05T11:47:53+00:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0021. Candidate: 11a93b85e79fb5f58f07192dd3dfdb62883896b1. Base: 02cea958ccc9cd051241170c58ed1cbcd929a697. Scope: code/evidence.
Verdict: approve-with-nits.

Findings:
1. Minor: replacement_fallback.sent increments before dispatch/acceptance; the decision's admitted=False remains the original replacement rejection. These fields alone cannot prove accepted fallback execution. Live analysis must bind fallback_from_goal_id/sequence to sent_goal and action outcomes.
2. Nit: the wiring contract test checks source strings; it does not execute ROS dispatch. Keep that limitation explicit.

Observations: clean exact HEAD; four owned paths only (+336/-7). The revised design sends the actual unchanged admission output, including its swept connector and exact index-aligned active-path suffix. It no longer retains execution of unchecked geometry. Active identity, unfinished result and same destination gate the single fallback attempt. Record creation follows server acceptance; target/yaw remain tied to the active plan, and the new goal receives normal action identity/outcome bookkeeping.

Default is off via argparse/getattr and absent config; successful replacements bypass fallback. Real admission preserves cross-track, heading, turn-radius, connector/suffix footprint sweeps, unknown blocking and consumed-path limits. Same rejecting pose/grid snapshot is reused, followed by freshness check; cancellation/stopping paths remain fail-closed. No sensor, audit, profile, speed or threshold changes.

Checks: after T0020 verified shutdown, one WSL/ROS-sourced focused unittest invocation: 69 tests OK, two existing skips. Real geometry tests cover offset/heading, blocked/unknown suffix, consumption, mismatch and stale data; fake handles/missing snapshots are covered. Exact runner validation executes eight configs as reported; parser has zero errors.

Missing acceptance coverage: real ROS preemption/send timing, cancellation failures and enabled live performance. No benefit or T0020 recovery-fix claim is supported. Usage: UNMETERED.


### 2026-10-05T04:49:13.110802-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION
Accept candidate 11a93b85e79fb5f58f07192dd3dfdb62883896b1 after both independent
reviews. Integrate the two owned source commits, then one combined suite.
Default remains OFF. No live/performance acceptance yet. Counters alone cannot
prove accepted fallback execution; future evidence must correlate actual goal IDs,
sent_goal/action results and selected plan, as both reviewers note.
Your T0021 work is complete. Preserve branch; next bounded task will be dispatched
after integration. No new provider or runtime work is requested from you here.
