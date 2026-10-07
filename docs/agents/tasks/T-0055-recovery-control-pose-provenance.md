---
id: T-0055
title: Reject ambiguous pose inputs in offline recovery control comparisons
status: accepted
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0055-pose-provenance-opus
base: 646845e25af6c0b58cd20131addfdbfacdcc6562
candidate: 8a8ab433db7ca925dc68968d7b6466f6e13e9c3d
claim: tested
lease: none
updated: 2026-10-06
---

# Packet

Read README introduction and this packet. Implement only the concrete offline
control-comparison defect confirmed in T0054. Navigation snapshot inputs may be
predicted; replay_controls currently pairs them with measured trajectory history.
Actual recovery selection_pose and captured recovery args remain measured.

Named HEADLESS owner: opus-t0055-controls-20261006T1738, no other writer.
Worktree: C:/Users/brand/.codex/worktrees/igvc-t0055-pose-provenance/IGVC SIM.
Interactive sessions and earlier T0053/T0054 workers have no edit ownership here.
Root holds artifacts/agents/T-0055/implementation.lock for dispatch.

Own only tools/snapshot_pose_provenance.py (new), tools/replay_recovery.py,
tools/tests/test_recovery_control_pose.py (new). Do not edit docs/agents or primary.
Initial candidate includes T0053 source for reading; this slice must not import
latency_compensation or depend on its integration at runtime.

Implement a pure reader-side classifier for snapshot pose provenance and guard
replay_controls BEFORE any numerical planner invocation. Require finite three-
element measured/planning poses, strict boolean enabled/applied metadata,
consistency with recorded input XY/yaw, and logically consistent flags. Predicted
poses can equal measured poses when velocity is zero: do NOT reject solely for
equality. Not-applied requires equal measured/planning/input poses. Applied
requires enabled true, and matching planning/input poses.

Distinguish measured, predicted, unknown_legacy (absent metadata/key) and malformed
(present wrong shape/type, contradictory/nonfinite/mismatched content). Never
silently infer measured from a missing flag. Existing snapshot numerical inputs
are never replaced. Controls execute only measured snapshots; selected predicted,
unknown or malformed snapshots produce explicit skipped rows/reasons and visible
counts in the CLI output. Preserve deterministic sample/count selection; do not
search extra snapshots until enough eligible controls are found. Do not claim
unknown means unsafe, or predicted means a navigation failure.

No legacy override in this slice: document in CLI help that legacy control
snapshots without provenance are skipped. This does not alter dataset admission,
ordinary navigation replay or runtime. A provenance-bound legacy opt-in may be
designed separately; arbitrary source-hash trust or silent relabeling is forbidden.
Keep replay_event unchanged, with no claim that its older costmap matches captured
recovery evidence. No course/WORLD/teacher reads in tests. Do not execute the CLI
against historical runs (it may load offline teacher labels).

Behavior tests must call the actual replay_controls with mocked planning functions:
skipped inputs invoke no planners; measured input arguments/history stay unchanged;
zero-motion applied remains predicted; malformed flags/NaN/poses reject; missing
metadata is visibly unknown; result and selection bounds remain deterministic.
Tests must not just repeat implementation. No production policy or audit edits,
metadata rewrite, estimator merge, dataset schema migration, dependency installs,
Unity build, ROS/live run, provider/delegation or source integration.

No tests/imports during implementation: root runs focused synthetic checks once
the committed handback exists, under all three process-held live locks. Provider
may edit and commit owned files only. Return <=300words SHA, files, test command
NOT RUN and limits. Bound6minutes/USD5, exactOpus5.5/high, no provider-error retries.
One Sonnet code review and Sol evidence review follow. Stop at committed slice or
actual blocker; preserve any partial work. No push/publish.

## Log


### 2026-10-06T17:37:15-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

Dispatch exact named owner above through implementation-1738/dispatch.ps1. Three owned files only, no tests until root validation. Existing replay_recovery.py and build_dataset.py match candidate/primary byte hashes; source consumers can be fixed independently without importing the unintegrated compensator. No prior owner for new task.

### 2026-10-06T17:40:02-07:00 · gpt-6-astra → all · HANDBACK

Opus completed128.41s/USD0.5671772 exactmodel. Candidate4d01fd0e2d797f48f412d1a1afffda0034a8d447 owns only three scoped files; tests NOT RUN by worker. Implementation assignment ended and worktree frozen. Root will run new behavior tests plus navigation replay/recovery evidence regressions under all3locks. ExactSonnet source review dispatched4min/USD3, Sol evidence review after results. No live run or historical teacher replay.

### 2026-10-06T17:40:58-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0055/review-4d01fd0/sonnet-static-review.md

**T0055 4d01fd0 vs 646845e: one blocker. This is a read-only review. I ran nothing, so the blocker comes from reading the code and the documented behaviour of `math.isfinite`.**

**Blocker**
- `tools/snapshot_pose_provenance.py:28-30` (`_finite_number`, called at `:37`): `math.isfinite(int)` raises `OverflowError` for ints too large for a float, such as a `1` followed by 400 zeros.
  - `json.load` accepts such literals, up to Python's int-digit limit, which is 4300 digits by default.
  - The classifier is therefore not fail-closed for very large JSON integers in `measured_pose`, `planning_pose`, `robot_xy` or `robot_yaw`. The exception escapes `classify_snapshot_pose`, called at `tools/replay_recovery.py:154`. It aborts the whole `replay_controls` run instead of producing a `malformed` skipped row.
  - Suggested fix: catch `OverflowError` and return False, or check `isinstance(value, float)` first.
  - No test covers huge ints. The tests only use nan and inf, in `test_recovery_control_pose.py:78` and `:89`.

**Verified, no blocker**
- The guard at `replay_recovery.py:154-162` runs after the fixed `requests[::step][:count]` selection and before any planner call. Skipped rows are never replaced. Test `:196` asserts `loaded == [0, 3, 6]`.
- Only a strict `MEASURED` result executes. A missing `metadata` or `latency_compensation` key is `unknown_legacy` (`provenance.py:58-65`), and there is no override.
- Flags must be real booleans. Poses must be finite 3-element numbers, and bool is rejected. Planning pose must equal input pose.
- Numerical equality is only used for consistency checks. It never changes the recorded label, so `applied=true` with equal poses stays `predicted`. The test at `:52` covers this.
- Skipped rows carry only `sequence`, `skipped`, `pose_provenance` and `skip_reason`. `control_counts` excludes them from executed counts. Nothing else in the repo consumes the `controls` rows.
- Measured-path arguments and history are unchanged, and the test at `:176` asserts exact argument equality.
- The diff touches only the three scoped files. `replay_event`, runtime, navigation and datasets are untouched.

**Limitations**
- Planners are mocked, so real planner behaviour is unexercised.
- `main()` and the `control_counts` output are not tested through the CLI.
- Measured rows still raise `KeyError` on missing grid fields. That behaviour predates this change.
- `-0.0` equals `0.0` in the pose comparison. It is harmless.
- No performance or runtime-promotion claim is made.

### 2026-10-06T17:40:58-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

Sole HEADLESS worker opus-t0055-controls-20261006T1738-r1, previous session completed. Root holds same T0055 implementation.lock. Same isolated worktree igvc-t0055-pose-provenance, branch codex/t0055-pose-provenance-opus starting clean4d01fd0e2d797f48f412d1a1afffda0034a8d447. Only edit tools/snapshot_pose_provenance.py and tools/tests/test_recovery_control_pose.py. Sonnet blocker: _finite_number math.isfinite huge Python int raises OverflowError for valid JSON integer such as10**400, so classifier crashes instead of malformed skip. Fix robustly without accepting nonfinite/bool/contradictory inputs or changing ordinary numeric values. Add meaningful regression through actual replay_controls with mocked planners for huge int in measured,planning,inputXY,yaw ensuring malformed skip/no planner and no abort; finite normal integer still valid. No other scope. Root first47tests passed but didn't cover this; preserve evidence. No tests/imports/providers/delegation/live/CLI historicalreplay. Commit only ownedfiles and return SHA, NOT RUN tests <=300words.6min/USD5 exactOpus5.5/high once, no retries. README and canonicalpacket prior scope stillapply; promptembeddednewdispatchoverridesoldowner. Stop after committed correction.

### 2026-10-06T17:42:15-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

Revision1 committedb0af326,34.16s/USD0.197456 exactmodel; tests NOT RUN, preserved. Root static numeric identity finding requires correction before validation.

Sole HEADLESS session opus-t0055-controls-20261006T1738-r2, prior r1 ended. Same isolated worktree/branch, root implementation.lock. Startingb0af326d9fed1e2d1dcd5d6a6560d1690eef7b0d. Root static finding before validation: converting all values to float before equality comparison collapses distinct valid JSON integers above2**53 (e.g.2**53 vs2**53+1). Metadata/input inconsistencies can therefore be accepted as measured. This existed initially and remains after r1. Fix comparison to preserve original numeric identities while checking float finiteness/overflow safely; no widening metadata trust and no mutation of snapshot values. Only helper and existing newtestfile owned. Add actual replay_controls regression where distinct finite large integers in planning/input or measured/planning would collapse under float conversion, requiring malformed skip and no planner. Keep normal int/float equivalents valid, huge10**400 skip and zero-motion predicted behavior. No tests/imports/live/replay/provider/delegation; root validates after commit. Return SHA/files/NOT RUN <=300words. This is second revision,6min/USD5 exactOpus5.5/high once. No policy/dataset/replay_event edits. Stop after commit or blocker.

### 2026-10-06T17:43:24-07:00 · gpt-6-astra → all · HANDBACK

Revision2 committed8a8ab433db7ca925dc68968d7b6466f6e13e9c3d,44.56s/USD0.2492478 exactmodel. Preserves original numeric identity while rejecting float-overflow/nonfinite shapes. Two new actual-control regressions for huge integer rejection and distinct finite integer mismatch; tests NOT RUN by worker. T0055 implementation assignments ended; candidate frozen. Root validates same3suites and dispatches focused Sonnet review. Interactive T0056 has separately reserved read-only slot; no extra worker beyond two.

### 2026-10-06T17:45:39-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0055/validation-4d01fd0/sol-evidence-review.md

# T0055 initial candidate evidence review

Verified the focused test record for immutable candidate `4d01fd0e2d797f48f412d1a1afffda0034a8d447`:47 tests, OK, exit0, no timeout;1.614s suite time/2.0s parent elapsed. Candidate HEAD matched and worktree was clean at review. All three changed-source SHA256 values and raw log hash match result.json. An authorized subsequent revision does not alter this candidate-bound evidence.

The wrapper acquires all three exclusive simulator locks, checks processes and WSL/Windows listeners, refuses changed/dirty candidates and existing results, then releases in finally. Held/released artifacts record PID49632,17:40:03.289–17:40:05.492 PDT. One validation directory was present when reviewed.

The new tests call actual replay_controls with synthetic snapshots/history and mocked planner functions. Covered behavior includes no planner invocation for skipped inputs; visible classifications/counts; zero-motion applied classified predicted; measured input/grid/history preservation; fixed sample selection without replacement; and exclusion of recovery sequences. Classifier cases cover strict flags, NaN/infinity, shape/type mismatches and contradictory poses. Navigation-replay/recovery-evidence regression suites also passed in the recorded command.

These passes do not prove every malformed-number case. Static spotcheck found `_finite_number` calls math.isfinite on arbitrary Python integers without catching overflow; oversized JSON integers can raise rather than produce a malformed row. Float coercion also deserves source review. Root reports Sonnet independently confirmed the huge-integer blocker and authorized a separate revision. No revised code or validation was reviewed here.

This is covered synthetic behavior, not historical replay, actual numerical escape efficacy, live safety or CLI execution evidence. replay_event's older-grid gap and primary-estimator reconciliation remain separate. Do not integrate or promote this blocked candidate on the47-test pass alone.

Raw log SHA256: `1985cbeeda6950db41b75652b2c2a14703cbec8879c26ad5155295e93c2ee6b2`.


### 2026-10-06T17:45:39-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0055/review-8a8ab43/sonnet-static-review.md

**No remaining blockers in 8a8ab43 for the scoped T0055 behavior.** I read the diff and code only. I ran no tests, imports or edits, so everything below is from reading.

**Fix 1: huge JSON integer.** `_finite_number` (`tools/snapshot_pose_provenance.py:28`) now checks `math.isfinite(float(value))` and catches `OverflowError`, so a `10**400` pose value returns False. Measured, planning and input poses all go through this check. The result is `measured_pose_invalid`, `planning_pose_invalid` or `input_pose_invalid`, which `replay_controls` turns into a malformed skipped row. A single unreachable dead-code edge is not an issue here.

**Fix 2: float collapse.** `_pose` now returns the original values (`tuple(value)`) and no longer builds floats. The comparisons `planning != recorded` and `measured != planning` therefore use Python's exact int/float comparison. `2**53` and `2**53+1` stay distinct, while `1`, `1.0` and `1` still compare equal.

**Tests.** Both new tests call the real `replay_controls`, with only the planners and `load_snapshot` mocked.
- **Overflow test:** it covers the huge value in measured x, planning y, input x, input y and input yaw. It checks the skip reasons and provenance, and that one ordinary integer snapshot still executes. Reverting to an unguarded `math.isfinite` would raise `OverflowError` and fail it.
- **Collapse test:** it covers planning/input mismatch, input mismatch, and measured mismatch (`not_applied_pose_mismatch`). It also covers an applied `big+1` predicted case and an int/float-equivalent measured case. Reverting to float coercion would turn the three mismatch rows into non-malformed rows and fail it.
- **Weak point (non-blocking):** `{(1,2)}` equals `{(1.,2.)}` in Python, so the planner-argument assertions can't tell an int pose from a float one. That doesn't affect the two fixes.

**Scope limits.**
- Three files changed relative to 4d01fd0^ (`tools/replay_recovery.py`, `tools/snapshot_pose_provenance.py`, `tools/tests/test_recovery_control_pose.py`). I did not diff against `main`, because that ref doesn't resolve in this worktree.
- Validation covers only the three pose fields: measured, planning and input `robot_xy`/`robot_yaw`. Other snapshot fields (origin, resolution, costs, destination, planner options) are unchecked.
- A finite but very large integer pose on a measured snapshot is passed to the planner unchanged.
- There is no live run or real-recording evidence. Behavior under the three-suite run with locks is unverified, since I didn't run it.
- Legacy snapshots are skipped explicitly with no override. Recorded numeric inputs are passed through unchanged. The reader accepts `applied=true` at the same pose by design.

### 2026-10-06T17:45:39-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0055/validation-8a8ab43/sol-evidence-review.md

# T0055 final focused evidence review

Accept the focused tested claim for candidate `8a8ab433db7ca925dc68968d7b6466f6e13e9c3d`; no remaining evidence blocker for the reviewed offline-control slice. Integration has not been executed and requires root's separate decision.

Raw log confirms49 tests, OK, exit0, no timeout;1.621s suite time/1.875s parent elapsed. Candidate HEAD matches and worktree is clean. Independently verified all three recorded source hashes and log SHA256. Held/released records cover PID52924,17:43:25.554–17:43:27.597 PDT.

Both revisions remain in history: b0af326d9fed1e2d1dcd5d6a6560d1690eef7b0d catches float-range overflow;8a8ab43 preserves original numbers for exact pose comparison. Each changes only classifier/tests. The original47-pass log remains hash-identical; the only saved validation directories are original/final. No validation pass is claimed separately for the intermediate revision.

The added behavior tests call real replay_controls with mocked numerical planners: oversized integers in measured/planning/input poses produce malformed skipped rows without planner calls, while an ordinary integer control executes. Precision regressions distinguish2**53 from2**53+1, retain int/float-equivalent measured values, and skip applied predictions. Sonnet independently reports no scoped source blockers.

Limits: synthetic input/history and mock planning do not establish numerical escape efficacy, historical-recording compatibility, live safety or CLI execution. Only pose provenance fields are validated; grid origin/resolution/costs/destination/options remain outside this classifier. Finite huge poses may pass unchanged to planners; no physical range guarantee is added. Legacy snapshots remain skipped without override; applied/equal poses are accepted as predicted by reader contract. replay_event's older-grid gap, dataset admission and primary-estimator reconciliation remain separate. No runtime promotion follows.

Log SHA256: `7e111062c6102c52b2a0d982754b8f5404230a6a82309bcad23c22426a364254`.


### 2026-10-06T17:45:39-07:00 · gpt-6-astra → all · DECISION

Accept scoped offline-control fix8a8ab43 for integration. Sonnet28.83s/USD0.0957236 found no remaining blockers; Sol verified49 tests and source/log hashes, both prior revisions preserved. No policy/planner/replay_event/dataset edits or live benefit claim. Root will acquire all3locks before process/port checks, integrate complete scoped range646845e..8a8ab43 (three source commits), and rerun same49 checks on primary. Guard primary replay baseline and clean owned paths/index; preserve unrelated changes. Identical Git content with only checkout line-ending differences may be restored to reviewed exact bytes and recorded before validation. Do NOT integrate unreviewed T0053 estimator range. No pushing.
