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

### 2026-10-06T17:35:03-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

You are sole read-only analyst opus-t0054-followup-20261006T1735, not an implementation session. All previous T0054 assignments expired. Read README intro, primary docs/agents/tasks/T-0054-latency-integration-readiness.md latest decision and review-20261006T1730/review.md plus primary-hashes.json and primary-drift-comparison.json. Complete missing trace, not another general summary. Candidate646845e is at C:/Users/brand/.codex/worktrees/igvc-t0053-reconcile-1703/IGVC SIM. Trace candidate sensor_course.py snapshot creation, actual recovery selection_pose and recovery_evidence caller to prove measured/predicted provenance at each. Check source in tools/replay_recovery.py and tools/learning/build_dataset.py only as needed. DO NOT read course/WORLD/teacher geometry, logs or credentials. No source edits, tests/imports, providers/delegation or simulations. Design minimal backward-compatible provenance handling: exact navigation replay retains all recorded numeric inputs; actual recovery uses captured actual selection_pose unchanged; controls may skip predicted/unknown with explicit counts. Legacy missing metadata is unknown unless explicit source/run binding proves semantics; distinguish malformed new metadata. Propose how dataset consumers retain usable legacy workflow via explicit opt-in versus silent relabeling. Adding metadata cannot preserve byte-identical full rows: specify unchanged numerical inputs and schema migration instead. State concrete smallest implementation scope, invariants, behavior tests and actual confirmed line references. Do not choose/merge primary percentile versus candidateEMA based on T0052. Root already verified two primary percentile hashes match1707; no need claim you hashed. Return <=300words plus concise design if needed, explicitly missing traces. Task6min/USD5; no retries. Root posts output; no edits or commits.

### 2026-10-06T17:39:29-07:00 · claude-opus-5-5 → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0054/followup-20261006T1735/handback.md

**T-0054 provenance follow-up (candidate 646845e, static read only; nothing run or edited)**

**Traces now proven**
1. **Navigation snapshot is the planning pose, with provenance stored alongside.** `sensor_course.py:509-511` gets `planning_pose` from `planning_context`. `latency_compensation.py:208-215` puts only that pose into `robot_xy`/`robot_yaw`. `sensor_course.py:525-531,541` stores `metadata.latency_compensation`, which holds `enabled`, `applied`, `measured_pose`, `planning_pose` and `reason` (`latency_compensation.py:138-165`). When compensation is not applied, `planning_pose == measured_pose` (`:141,165`). `navigation_decisions.py:59` writes `{schema_version:1, input, metadata}`.
2. **Recovery `selection_pose` is measured.** `sensor_course.py:607` re-reads `latest['pose']`, which only the odometry callback sets (`:294`). It does not reuse the planning pose. `:632` records it unchanged, and `:639` passes the same pose into `recovery_args`.
3. **The `recovery_evidence` caller is measured too.** `describe_search_inputs(recovery_args)` (`:667`), the worker (`recovery_evidence.py:213`) and `recovery_captures.defer(recovery_args…)` (`sensor_course.py:724`; `recovery_evidence.py:252-272`) all receive the measured pose. Nothing on this path calls the compensator.
4. **The control-replay problem is confirmed.** `replay_controls` (`replay_recovery.py:151-153`) reads the snapshot's `robot_xy`, which can be the planning pose. `replay_event` (`:81`) uses `selection_pose`, which is measured.

**Traces still missing**
- I did not check whether `compact_event_metadata` keeps `latency_compensation` in the "requested" event in `run.json`.
- `replay_event` uses the grid saved with that decision's navigation snapshot (`:75-78`). The live search used the grid from `:606`, which can be newer. That is a grid-provenance gap, separate from pose, and I haven't checked it.
- I did not read the `build_dataset.py:323` corridor path past the line reference.
- I did not open the README, `primary-hashes.json` or `primary-drift-comparison.json`.

**Proposed design**
- **`pose_source(snapshot)`, reader only:**
  - `measured`: `latency_compensation` is a dict, `applied is False`, and `planning_pose == measured_pose == input` pose.
  - `predicted`: `applied is True`, `planning_pose == input` pose, and `planning_pose != measured_pose`.
  - `unknown_legacy`: metadata or the `latency_compensation` key is missing.
  - `malformed`: the key is present but the wrong type, or any of the checks above fail.
  - `unknown_legacy` can become measured only through an explicit opt-in such as `--legacy-pose-binding` against a listed set of pre-compensation `metadata.source_sha256` values. The output records that binding was used; nothing is relabelled silently.
- **Navigation replay (`_replay_one`):** inputs stay as recorded. Output rows go to `schema_version=3` with a new `pose_provenance` field. Readers accept versions 2 and 3, and historical files are never rewritten.
- **`replay_controls`:** keep only `measured` snapshots (plus legacy ones under the opt-in), and report `skipped: {predicted, unknown_legacy, malformed}` counts.
- **`replay_event`:** no change.
- **Corridor/route training:** excludes `unknown_legacy` and `malformed` by default. Explicit flags admit `predicted` or bound legacy rows.

**Smallest scope:** one helper module plus edits to `replay_recovery.replay_controls` and `build_dataset._replay_one`/`:323`.

**Invariants:** recorded numbers are never replaced, the live code is unchanged, and legacy data is never treated as measured by default.

**Behaviour tests:**
- Compensation off: a v3 row's numbers equal the v2 row's.
- A predicted snapshot still replays to the recorded plan.
- Missing metadata gives `unknown_legacy`; contradictory metadata gives `malformed`.
- Controls skip and count predicted, legacy and malformed snapshots.
- `replay_event` output is the same with and without the metadata.
- The legacy opt-in needs a matching source hash.

I make no claim about primary percentile versus candidate EMA.

### 2026-10-06T17:39:29-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0054/followup-20261006T1735/sol-trace-review.md

# T0054 static trace evidence review

Confirmed against clean candidate646845e25af6c0b58cd20131addfdbfacdcc6562 and primary replay_recovery.py. No execution or T0055 implementation review performed.

Navigation captures the planning pose: sensor_course.py:509–531 passes planning_pose into frozen_planner_inputs; latency_compensation.py:214–215 stores it as robot_xy/robot_yaw. Metadata retains enabled/applied and measured/planning poses. DecisionRecorder writes input and metadata together (navigation_decisions.py:59). compact_event_metadata:28–35 removes only memory_refresh_input, so requested-event input_metadata retains latency_compensation; sensor_course.py:545–547 separately records both poses.

Live recovery is measured: odom callback:294 sets latest.pose and:299 appends measured trajectory. Recovery:606–639 rereads current grid and latest.pose, records selection_pose and constructs recovery_args from the same measured pose. Recovery evidence diagnosis:213–217 and deferred capture preserve those supplied arguments; this path does not invoke the compensator.

Controls replay:145–157 reads the navigation snapshot's robot_xy/yaw and pairs it with history_until(measured trajectory, event odometry stamp). Therefore predicted-start/measured-history pairing is possible. This is a source-confirmed defect mechanism, not an observed numerical failure from an executed replay.

replay_event:75–85 instead uses measured selection_pose but takes the earlier navigation snapshot's grid. Live recovery rereads latest.grid at:606; equality is not established. That separate old-costmap provenance gap must not be conflated with predicted control pose or described as fixed by T0055.

Qualification: candidate planning_context:155–160 marks unchanged predicted output applied=False. Zero-motion applied=True/equal poses are not emitted by this producer branch. T0055's requirement to admit that metadata shape as predicted is a permissive reader contract/synthetic test, not evidence of current producer behavior. Equality alone must not infer measured provenance across producers.

T0055 appropriately narrows work to classifier/control guards, preserving recorded numbers and deterministic selection. Follow-up proposals for dataset admission, schema migration or legacy overrides are outside that packet. No primary-percentile reconciliation, runtime safety or implementation acceptance follows.


### 2026-10-06T17:39:29-07:00 · gpt-6-astra → gpt-6-astra · DECISION

Opus follow-up66.27s/USD0.4612754 exactmodel and Sol trace confirm control comparison mechanism; compact_event_metadata preserves latency metadata. T0055 implements only classifier/control guard on isolated branch, no predicted-pose substitution or runtime edits. Zero-motion applied=true is permitted reader shape, not emitted by candidate646845e. Actual recovery measured-pose path remains unchanged. Older recovery replay costmap provenance, dataset/schema compatibility and estimator identity remain unresolved; T0054 stays changes-requested for those integration-readiness questions. Headless analysis session ended. Interactive Claude inventory was acknowledged inT0048; no ownership collision or live A/B grant.

### 2026-10-06T18:26:19.686616-07:00 · gpt-6-astra → all · NOTE

T0058 design accepted and T0059 integrated atdaecdaa: recovery-event reconstruction now reports counterfactual/not-evaluated input binding, defaults to skipping mismatched/unknown gridstamps and unusable snapshots, keeps explicit opt-in for available approximate inputs.53focusedtests and both reviews accepted. This prevents overstating reconstruction provenance; it does NOT recover missing live costmaps or prove exact input equivalence from matching stamps. Exact-capture loader remains unchanged. Dataset migration(T0056) and estimator reconciliation remain unresolved; no T0053 integration/live grant.
