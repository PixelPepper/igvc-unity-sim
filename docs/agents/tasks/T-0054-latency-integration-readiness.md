---
id: T-0054
title: Resolve latency candidate integration and recorded-pose compatibility
status: changes-requested
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: none
base: 646845e25af6c0b58cd20131addfdbfacdcc6562
candidate: none
claim: none
lease: none
updated: 2026-10-06
---

# Packet

Prepared, NOT DISPATCHED. Read README and this packet. T0053 reached focused
validation after two revision rounds; do not reopen its implementation assignment.
Root must check latest primary task logs and actual ownership before dispatch.

Objective: identify the smallest safe integration slice for candidate646845e
without overwriting the external rolling-percentile experiment or mislabeling
predicted poses as measured observations in downstream datasets/reports.

Inputs, read only:
- T0053 canonical log, final validation-646845e-fixtures and review-646845e.
- Candidate worktree igvc-t0053-reconcile-1703, full range e38deca..646845e.
- Preserved primary-observation-1707 hashes/copies and current primary hashes;
  record drift rather than assuming the saved copies are current.
- Relevant pose-input consumption in tools/learning/build_dataset.py (locate
  exact file if renamed), recovery/decision capture readers and batch reporter.
- T0051 accepted narrow diagnosis only if discussing recovery; no new probe.

Initial assignment is a bounded read-only compatibility analysis. Root must name
the actual session and permitted output artifact before launch. No source edits,
tests, imports, dependency installs, Unity, ROS, providers or recursive delegation.
Return exact affected paths, source identities, concrete compatibility defects,
and a minimal implementation/test proposal. Distinguish existing concerns from
new regressions. Read no course/WORLD/teacher geometry. Do not merge estimators
or select one based on confounded T0052 results. No new live latency batch.

Acceptance: Sonnet reviews proposed invariants and Sol verifies identity/evidence
claims; root writes a separate implementation scope with a fresh isolated
worktree if changes are justified. Existing tests do not prove live improvement.
Stop after one analysis. Exact Opus5.5/high,6minutes/USD5 task bound; no provider
error retries or silent model substitution. Findings <=300words plus concise
artifact. All previous failed checks and alternate source variants remain intact.

## Log


### 2026-10-06T17:28:41-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

You are exact Opus5.5 read-only analyst opus-t0054-readiness-20261006T1729. Read README intro and docs/agents/tasks/T-0054-latency-integration-readiness.md in primary cwd. Latest dispatch: this is now an actual bounded read-only assignment; no implementation worktree or write ownership. T0053 all workers completed, candidate646845e frozen,55 focused tests pass after preserving earlier failures. You may read candidate C:/Users/brand/.codex/worktrees/igvc-t0053-reconcile-1703/IGVC SIM/tools and primary source/relevant task artifacts. No edits, imports/tests, simulation, providers/delegation or commits. Analyze candidate/primary estimator differences and downstream predicted-vs-measured pose provenance. Follow packet acceptance/limits. Do not read full logs, binary files, credentials, course/WORLD/teacher geometry. Return <=300words with exact file lines, minimal followup implementation scope and unresolved evidence; root saves artifact and posts handback. No new mission or probe. Stop once analysis complete.

### 2026-10-06T17:30:06-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK

relayed-from: artifacts/agents/T-0054/analysis-20261006T1729/review.md

I compared the two estimators and traced every reader of the captured pose. I did not hash any files, so the primary-observation-1707 drift is not recorded.

**Estimator differences (primary working tree vs candidate 646845e)**
- **Latency estimate:** primary keeps the 25th percentile of the last 20 samples, starting at 0.3 s and timed by the wall clock (`tools/latency_compensation.py:24-35`, `sensor_course.py:792`). The candidate uses an exponential average starting at 0.6 s, timed by odometry header stamps, and counts rejected samples by reason (`candidate latency_compensation.py:85-99,172-195`).
- **Limits:** primary scales the result down to 1 m after predicting (`:51-55`). The candidate shortens the prediction time itself, limits yaw too, and skips stale or mismatched samples (`:101-109,130-165`).
- **Primary-only defects the candidate fixes:**
  - The heading hint isn't moved with the predicted start (`sensor_course.py:511,543`; the candidate fixes this with `rebase_heading_hint`).
  - Compensation isn't restricted to checked-path mode (candidate `:1020-1022`).
  - Snapshots carry no record that compensation was on.
- These are different algorithms. Integrating the candidate would overwrite the rolling-percentile experiment, so it needs its own name or file, not a merge.

**Predicted vs measured pose in recorded data (a problem in both versions)**
- With compensation on, the snapshot's `robot_xy`/`robot_yaw` hold the **predicted** pose (primary `:509`; candidate `latency_compensation.py:215`). The candidate adds `metadata.latency_compensation.{applied,measured_pose,planning_pose}` (`sensor_course.py:531`), but nothing downstream reads it:
  - `tools/learning/build_dataset.py:82` replays the planner from the predicted pose. That is correct for exact-input replay but isn't labelled as such.
  - `build_dataset.py:323-332` computes corridor features from the predicted pose without saying so.
  - `tools/replay_recovery.py:151-157` starts recovery from the predicted pose but uses the measured trajectory up to the odometry stamp. This mismatch is a real defect.
  - `tools/sandbox_batch_report.py:26,55` records only a true/false flag, so it can't tell which estimator ran.

**Proposed minimal follow-up (separate worktree)**
1. Name the estimator variant in `report()` and the batch-report row.
2. Have `build_dataset` and `replay_recovery` read `metadata.latency_compensation`. Recovery replay should use `measured_pose`. Dataset rows should carry a `pose_source` of predicted or measured, or be excluded.
3. Tests: compensation off gives identical snapshots; a snapshot with compensation applied must not feed the predicted pose into recovery replay.

**Still unresolved**
- No hash comparison of the 1707 copies against current primary.
- Not checked: the T0053 log, the 646845e validation and review files, the full e38deca..646845e diff, or `recovery_evidence.py:181`'s live caller.
- No evidence yet that compensation improves live runs, and T0052 remains confounded.

### 2026-10-06T17:30:06-07:00 · gpt-6-astra → claude-sonnet-5-5 · DISPATCH

Opus completed58.74s/USD0.4117786 exactmodel; scope incomplete, no acceptance. Review concrete consumer findings and proposed compatibility handling per embedded prompt. Root recorded primary hashes under review-20261006T1730. No blanket replacement of planner inputs, new probe, source edit or source integration. Bound4min/USD3 exactSonnet5.5. Opus analysis assignment ended.

### 2026-10-06T17:31:04-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0054/review-20261006T1730/review.md

**Source review of the Opus T-0054 analysis (static; nothing run or edited)**

**Hash check:** I only read `primary-hashes.json`. I did not recompute any hashes, and it records no comparison against the 1707 copies.

**Corrected finding: the recovery-replay defect is narrower than Opus said.**
- `replay_recovery.py:151-157` is inside `replay_controls`. It uses `grid['robot_xy']` and `grid['robot_yaw']` from non-stall "requested" snapshots, which may be predicted poses. It then pairs that pose with the measured trajectory up to `odom_stamp_ns` (`:156`).
- Controls only compare retrace-with-no-memory against legacy backup. They don't grade actual failures. A start pose that is off by the latency shift can mislead them. I have not shown it changes the `same_goal` and `same_distance` verdicts.
- Actual captured failures go through `replay_event`. It takes the pose from `event['selection_pose']` (`:81`). `sensor_course.py:607,632` sets that pose from `latest['pose']`, which the recovery path does not appear to predict-shift. I did not trace whether compensation touches it. I did not check line 509 either, so this is likely but unproven.
- `replay_event` uses the grid only for the costmap, so it is probably unaffected.

**Blanket measured-pose replacement is wrong for exact-input replay.**
- `build_dataset._replay_one` (`:77-84`) is exact-input navigation. It feeds `inputs['robot_xy']`, `inputs['robot_yaw']` and `heading_hint` to the planner. Swapping in the measured pose would stop it reproducing what the planner actually saw.
- Corridor features at `:323-332` have the same issue. They are labelled from the grid and planner, so the predicted pose is consistent with them. The gap is that nothing says which pose was used.

**Proven offline issue:** no reader branches on `metadata.latency_compensation`. I only searched `build_dataset.py` for it, and `replay_recovery.py` has no such branch.

**Fail-closed proposal (readers and reports only):**
1. Define `pose_source` as `measured` (compensation off), `predicted` (`applied` true and the metadata complete), or `unknown`. `unknown` covers a missing key, a legacy capture with no metadata, or malformed or contradictory metadata. Do not default `unknown` to `measured`.
2. Leave exact-input replay on the recorded pose. Stamp `pose_source` on the output rows.
3. In `replay_controls`, skip `predicted` and `unknown` snapshots and count each skip with its reason. Don't substitute a pose.
4. Corridor and route training exclude `unknown` rows by default. Predicted rows are included only if an explicit flag allows them.
5. Historical files are never rewritten.

**Tests needed:**
- compensation off gives byte-identical rows
- legacy snapshots with no metadata resolve to `unknown`
- `unknown` and `predicted` snapshots are skipped by controls
- exact-input replay of a predicted snapshot still reproduces the recorded plan
- `replay_event` ignores the metadata

**Limits:** I did not read `sensor_course.py:509` or `recovery_evidence.py:181`. There is also no live-improvement evidence.

### 2026-10-06T17:31:04-07:00 · gpt-6-astra → all · DECISION

Sonnet26.41s/USD0.1140564 exactmodel narrows Opus claim: predicted/measured mismatch is in offline replay_controls, not established for actual-failure replay_event. Exact-input navigation and corridor features must retain recorded planner pose. No change accepted yet. Root compared freshly recorded primary hashes with1707 manifest: both percentile-module/test hashes match; other current files have recorded hashes but no claimed1707 comparison. Source-level remaining traces and legacy semantics are incomplete.

Next bounded Opus follow-up must trace sensor_course snapshot construction, recovery selection_pose and recovery_evidence caller, then provide a concrete provenance design. Keep metadata-absent historical captures distinct from malformed new metadata; do not silently relabel them measured, rewrite historical files or make all historical datasets unusable without documenting compatibility. Sonnet proposal to add pose_source conflicts literally with byte-identical full output rows; clarify preserved numerical/planner inputs versus new metadata before implementation. Read-only analysis first, no new source edits or tests until explicit scope. Previous analysis session ended; no active T0054 worker. T0053 remains focused-tested only and isolated.
