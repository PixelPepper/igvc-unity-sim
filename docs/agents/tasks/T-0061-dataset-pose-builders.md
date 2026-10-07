---
id: T-0061
title: Add explicit pose provenance to dataset builders and shared policy
status: integrated
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0061-dataset-pose-builder-opus
base: ec0627a
candidate: 9ea5da030d42ec09d41d8eb957b091643fbbe959
claim: tested
lease: none
updated: 2026-10-06
---

# Packet

INTERACTIVE user-started Claude ONLY, session alias interactive-opus-t0061-20261006,
same actual session as completed interactive-opus-dataset-20261006. ACK exact alias
and model claude-opus-5-5 before implementation. Reserve one worker slot; no other
session is assigned. No headless duplicate. Work ONLY in isolated
C:/Users/brand/.codex/worktrees/igvc-t0061-dataset-pose-builder/IGVC SIM,
branch codex/t0061-dataset-pose-builder-opus, base ec0627a. Root prepared a sparse
tools checkout. Primary task log is authoritative, not stale worktree docs.
Read README intro and accepted T0056 final decision in primary task log.

First of three implementation slices. Own only tools/learning/build_dataset.py,
NEW tools/learning/dataset_policy.py, NEW tools/tests/test_dataset_pose_policy.py,
and tools/tests/test_learning_pipeline.py only necessary builder fixture/tests.
Do not edit train_scorer, round_gate, run_round, classifier, recorder, teacher,
runtime, primary source or docs. Later slices wire all readers and cache policy;
THIS SLICE MUST NOT BE INTEGRATED INTO PRIMARY OR USED FOR TRAINING YET.

Implement reusable policy APIs and both route/corridor builder provenance:
- Load full snapshot payload joined by recorded outcome decision index and existing
NNNNN.json.gz identity. Reuse tools/snapshot_pose_provenance.classify_snapshot_pose
unchanged. Add pose_source and pose_reason. Missing/unreadable/invalid snapshot
payload is unavailable, distinct from canonical malformed metadata. No sourcehash
allowlist, CLI-flag absence inference, or numeric planner/feature substitution.
- Default allowed measured. Explicit --allow-predicted and --allow-unknown-legacy
may be combined. malformed/unavailable are never admitted. Historical dataset rows
missing pose_source are unknown_legacy/dataset_row_unlabelled and need unknown
opt-in; do not invent --allow-legacy-dataset or silently relabel measured.
- Shared row admission applies BEFORE existing group cardinality/heuristic filters.
Drop whole groups if any member is excluded or the group's provenance kinds are
mixed, even when individual kinds are allowed. Uniform unknown groups are allowed
only with explicit opt-in. Preserve original groups/candidates/numeric values;
no replenishment of skipped rows/groups. Export a documented compact shared API
for later train/gate reader use; do not wire those readers in this slice.
- Both builder paths enforce the same explicit policy and report pose_policy plus
per-run/per-kind/row/group selected/admitted/excluded counts in summary.json, with
reasons and no omission of failures. Summary is a record, not proof overriding rows.
- Preserve replay schema2 and snapshot schema1; do not modify recorder/replay writer
or historical artifacts. Existing included row values remain identical except the
new provenance fields. Keep group/corridor-label semantics and teacher separation.
- New behavior tests: each kind/flag combination; appliedtrue/equal remains predicted;
route and corridor index joins; missing/bad snapshot; fixed exclusion counts and
whole-group consistency; numeric/feature immutability; old unlabelled rows opt-in.
Use synthetic fixtures only; do not read real captures/labels/course/WORLD geometry.

You may edit and commit the owned files on the assigned branch. No imports/tests,
replay/builds/live sessions/provider calls/delegation: root runs focused validation
under all3simulator locks after handback. No primary integration or publishing.
Suggested bound6minutes/USD5 (interactive usage target, not billing guarantee).
At bound, preserve edits and report incomplete rather than silently extending.
Return actual commit SHA, files, test commands NOT RUN, API contract and remaining
work in <=300words. Append ACK/HANDBACK only to this primary task log. Unknown usage
is acceptable; no fabricated accounting. Stop after handback/blocker. Root handles
Sonnet review and Sol evidence review before any next slice. No routine questions.

## Log

### 2026-10-06T19:00:07.535497-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

INTERACTIVE interactive-opus-t0061-20261006 ONLY. Existing T0056 assignments completed and revoked for implementation purposes; this is the sole dataset implementation owner in its isolated worktree. Please ACK exact alias/model before editing. No live lease granted. T0060 metadata branch is accepted separately and unchanged; no source overlap. Root will not count a posted dispatch as delivery.

### 2026-10-06T19:00:26-07:00 · claude-opus-5-5 → gpt-6-astra · ACK

ACK T-0061, alias interactive-opus-t0061-20261006: same interactive Claude Code session as interactive-opus-dataset-20261006,
exact model claude-opus-5-5. Working only in .codex/worktrees/igvc-t0061-dataset-pose-builder on branch
codex/t0061-dataset-pose-builder-opus (base ec0627a), on the owned files only. No tests, imports, replays, builds or
live work; at most a syntax-only `ast.parse` of my own edited files. Handback here with the commit SHA. No questions.

### 2026-10-06T19:00:48.685158-07:00 · gpt-6-astra → claude-opus-5-5 · ACK

Received actual19:00:26 ACK from INTERACTIVE interactive-opus-t0061-20261006 with exact model confirmation. Sole ownership is active; no duplicate/headless dispatch. Static ast.parse of owned source text is allowed; do not import project modules or execute tests/planners. Root handles lock-gated validation after handback. No integration/training or live lease.

### 2026-10-06T19:05:53-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK

Alias interactive-opus-t0061-20261006, model claude-opus-5-5. Commit **25605a2** on codex/t0061-dataset-pose-builder-opus (parent ec0627a).

Files changed:
- tools/learning/build_dataset.py
- new tools/learning/dataset_policy.py
- new tools/tests/test_dataset_pose_policy.py
- tools/tests/test_learning_pipeline.py (measured snapshot fixture and a pose assertion)

Only a static `ast.parse` was run. These commands were NOT run:
- `python3 -m unittest tools.tests.test_dataset_pose_policy tools.tests.test_learning_pipeline tools.tests.test_corridor_scorer`
- `python3 -m unittest discover -s tools/tests -p "test_*.py"`

API (`dataset_policy`):
- `PosePolicy(allow_predicted=False, allow_unknown_legacy=False)`: `.allowed` and `.to_dict()`.
- `load_snapshot_provenance(path)` returns `(snapshot|None, {kind, reason})`. Missing, unreadable, non-schema-1 or non-dict input is `unavailable`. Otherwise `classify_snapshot_pose` is used unchanged.
- `row_provenance(row)`: rows without fields are `unknown_legacy/dataset_row_unlabelled`; a bad `pose_source` is malformed.
- `admit_group(provenances, policy)` returns `(bool, reason)`, with reasons `kind_not_allowed:<kind>` or `mixed_provenance`.
- `filter_rows(rows, policy)` returns `(kept, counts)`: whole groups, order kept, no replenishment.
- `PoseCounts` and `merge_counts`.

Builders:
- `build_rows` and `build_corridor_rows` take `pose_policy=` (default measured-only). The snapshot is loaded by the outcome index.
- Admission runs right after the join, before the cardinality, guidance and target filters.
- `stats['pose']` holds `members_by_kind/reason`, `admitted_groups/rows` and `excluded_groups/rows` by reason.
- Rows add `pose_source` and `pose_reason`; their other values are unchanged.
- The corridor builder reuses the same loaded snapshot. `missing_snapshot` now counts only input KeyError.
- CLI flags: `--allow-predicted` and `--allow-unknown-legacy`. summary.json carries `pose_policy` and the merged `pose` counts.

Expected breakage outside my ownership: the tools/tests/test_corridor_scorer.py fixtures write `metadata={}` (unknown_legacy). Under the measured-only default, `test_dataset_rows_match_runtime_features` and CorridorLabelModeTests will produce no rows. The fix is to pass `pose_policy=PosePolicy(allow_unknown_legacy=True)` or write measured metadata there. That needs your assignment.

Remaining work:
- The above fixture fix.
- run_round does not pass the flags yet, so a default rebuild of historical data now yields zero rows until it opts in.
- Train and gate readers using `filter_rows`.
- Validation.
Stopping.

### 2026-10-06T19:06:50-07:00 · gpt-6-astra → claude-opus-5-5 · ACK

Actual handback received, clean candidate25605a2769c3d1e6c7a9c5ea42a3377803716b1e bound. Implementation assignment ends; please remain read-only until consolidated review. Root will preserve reported corridor fixture incompatibility, run focused validation under all3locks, and obtain Sonnet source review before revision. No primary integration/training.

### 2026-10-06T19:08:14.237577-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0061/review-25605a2/sonnet-static-review.md

Static review of 25605a2 against ec0627a. I ran no tests and executed no code.

**Blockers**
1. **Old corridor fixtures break.** `tools/tests/test_corridor_scorer.py:154` and `:183` build snapshots with `metadata={}`, which the classifier calls `unknown_legacy`/`latency_compensation_absent`. Default admission now excludes them. That affects the `build_corridor_rows` tests in `test_corridor_scorer.py`, which expect rows from them: the `:157` test and every `CorridorLabelModeTests` case that reaches row building.
   - **Required fix:** migrate both fixtures to measured metadata. Use the `write_measured_snapshots` shape: `latency_compensation` with `enabled=False`, `applied=False`, and `measured_pose` equal to `planning_pose` equal to the `input` robot pose. Do not relax the default.
   - **Scope:** `test_corridor_scorer.py` is not in the packet's owned list, so the packet needs an amendment, or the root must do this migration.
2. **`filter_rows` crashes on a malformed `group`.** An unhashable `group` value (list or dict) hits `key not in groups` and the `in kept` check (`dataset_policy.py`, `filter_rows`) and raises `TypeError`. The code that maps non-string keys to `group_absent` never runs. Check `isinstance(key, str)` before any hashing.

**Risks**
- **`admitted_rows` and `excluded_rows` are candidate counts, not built rows.** They are the pre-filter member count, and `admitted_rows` can exceed emitted `rows`. The packet's own single-option test shows this (admitted 1, emitted 0). Rename them, e.g. `*_candidates`, or document this in `summary.json`. As written, the counts can mislead.
- **Pose counts include non-members.** Decisions with zero route/corridor members and non-corridor guidance are counted as admitted or excluded groups with 0 rows. Unlabelled and mismatched decisions are never counted.
- **Corridor validation ordering changed.** Pose admission now runs before `_corridor_target`. Incompatible or malformed label rows in pose-excluded groups are skipped silently instead of raising `ValueError`. The label-mode check at `build_dataset.py:314` still runs first.
- **`missing_snapshot` changed meaning.** It now counts only a schema-1 snapshot lacking costmap keys. Missing files appear under `pose` as `unavailable/snapshot_missing`.
- **Mixed-provenance is never exercised in the builders.** Each group has one snapshot, so it only matters in `filter_rows`. The test coverage there is adequate.
- **No test pins the corridor summary.** The corridor path isn't exercised through the `main` summary.
- **Formatting nit:** `group =[(` in `build_rows`.

**Checked and fine**
- The classifier is reused unchanged.
- No numeric values are mutated, and the test compares included rows with `assertEqual`.
- Predicted stays predicted when `applied` is true and the poses are equal.
- Both builder paths and the CLI use the same `PosePolicy`.
- Unlabelled rows are `unknown_legacy`/`dataset_row_unlabelled` and need the unknown opt-in.
- The API is compact and suitable for the later readers.

### 2026-10-06T19:08:14.237577-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

Revision r1 assigned ONLY INTERACTIVE interactive-opus-t0061-20261006-r1, same user-started session. Prior implementation assignment ended at handback; do not duplicate. ACK exact alias/model. Same isolated worktree/branch, start25605a2769c3d1e6c7a9c5ea42a3377803716b1e. Ownership extended ONLY to necessary builder fixture/assertion migration in tools/tests/test_corridor_scorer.py; all original owned files remain allowed. No primary edits beyond ACK/HANDBACK.

Root lock-gated validation selected19tests and ended FAILED with12failure entries (including subtests); full preserved log/result/hashes at artifacts/agents/T-0061/validation-25605a2. Source review is above; Sol evidence review pending. Do not rerun tests/imports yourself.

Fix both blocking findings: migrate the two synthetic corridor snapshot fixtures to explicit measured metadata; guard malformed/non-string/unhashable group values before any hash/set membership, count exclusion without crashing or admitting them. Add behavior tests for list/dict/null group fields and preservation of valid neighboring rows.

Address source-review risks within the same bounded revision: explicitly describe in summary/count metadata that pose admitted/excluded row counts are PRE-FILTER CANDIDATES, groups are joined decisions (including zero-member decisions), and show original decisions/joined/mismatched alongside them. Include a corridor CLI summary test so both builder outputs carry policy/count semantics. Clarify legacy missing_snapshot counter versus pose unavailable counts. Preserve existing hard rejection of incompatible/malformed corridor target records even when pose-excluded: validation is allowed before pose admission, cardinality/guidance/group selection must remain after pose admission. Add a targeted excluded-pose invalid-target check; do not weaken teacher validation. Mixed provenance need only be exercised by shared filter_rows, since builders use one snapshot per group. Cosmetic spacing fix optional.

No train/gate/run_round wiring yet, no tests/imports/providers/live/build/integration. Syntax ast.parse allowed. Target6min/USD5, report incomplete at bound. Commit owned source/tests; handback <=300words with SHA and NOT RUN checks. Stop after handback. No primary integration or training.

### 2026-10-06T19:08:23-07:00 · claude-opus-5-5 → gpt-6-astra · ACK

ACK r1, alias interactive-opus-t0061-20261006-r1, model claude-opus-5-5. Same session and worktree; branch codex/t0061-dataset-pose-builder-opus starting at 25605a2. Scope: the original owned files plus the corridor fixture/assertion migration in test_corridor_scorer.py only. Static ast.parse only; no tests or imports.

### 2026-10-06T19:08:41.091997-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0061/validation-25605a2/sol-evidence-review.md

# T0061 first candidate evidence review

Validation fails; no test or integration acceptance for `25605a2769c3d1e6c7a9c5ea42a3377803716b1e`. Worker HEAD matches and is clean. All four source/test hashes match `result.json`; verified log SHA-256 is `eddfa75c475eb6845240187af06108552b9ad1e699e9be06294dce558bc802a1`.

The command ran 19 test methods in 1.328 seconds, with 12 failure entries across seven distinct methods. Subtest failures account for the difference; this is not 12 failing methods or a seven-pass result. Parent exit is 1, no timeout, elapsed 2.250 seconds. No failure entry names the nine new policy methods or the selected route-join test. Expected argparse refusal messages are not recorded test errors.

Every failure belongs to the existing corridor fixture tests. Both fixture writers explicitly use `metadata={}` (`test_corridor_scorer.py:153–154,182–183`), so canonical classification is unknown legacy and the measured-only default excludes them. Observed consequences include empty rows, omission counters staying zero, and two expected label exceptions not raised. This is consistent with early pose admission masking subsequent label checks; it does not prove that changing fixtures alone resolves every source defect or preserves those checks. Source review remains pending.

Matching PID 2412 lease records bracket validation, 19:07:03.286–19:07:05.688 PDT. Preserve this failed run unchanged. A revised candidate needs explicit fixture/source ownership, review and new focused evidence. Reader wiring, training, primary integration and live behavior remain outside this slice.


### 2026-10-06T19:08:41.091997-07:00 · gpt-6-astra → claude-opus-5-5 · ACK

Received actual19:08:23 exact-model r1 ACK; sole revision owner interactive-opus-t0061-20261006-r1 is active. Both first-candidate reviews complete. Preserve all19test results/12failure entries; no acceptance for25605a2. Original implementation assignment expired; no headless duplicate. Sonnet review costUSD0.1943454/35.70s, interactive implementation and nativeSol billing unavailable. All validation locks released; no live lease. Await committed r1 handback before fresh review/lock-gated validation.

### 2026-10-06T19:11:18-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK

r1, alias interactive-opus-t0061-20261006-r1, model claude-opus-5-5. Commit **9ea5da0** on codex/t0061-dataset-pose-builder-opus, parent 25605a2.

Files: build_dataset.py, dataset_policy.py, test_dataset_pose_policy.py, test_corridor_scorer.py (fixtures only). Only static `ast.parse` was run, on all five owned files.

Blockers:
1. The two `test_corridor_scorer.py` snapshot fixtures now use a `MEASURED` constant: `latency_compensation` with enabled/applied False, and measured_pose == planning_pose == `[*ROBOT, YAW]`. The default stays measured-only.
2. `filter_rows` checks `isinstance(group, str)` before any dict or set use. Missing, null, number, list or dict groups and non-dict rows are each excluded as `group_invalid` and never admitted. Valid neighbouring rows keep their order. New test: `test_non_string_groups_are_excluded_without_crashing`.

Risks:
- **Count semantics.** `stats['pose']`/`summary['pose']` now carry `semantics` (`BUILDER_SEMANTICS`: groups = joined decisions, including zero-member ones; members = PRE-FILTER candidates, NOT emitted rows), `join` {decisions, joined, mismatched, unlabelled}, `provenance_by_kind`/`_reason`, `admitted_/excluded_groups` and `admitted_/excluded_members`. `filter_rows` uses `ROW_SEMANTICS`. `merge_counts` refuses parts with different semantics. Route stats now always include `unlabelled`.
- **Corridor validation before pose admission.** `_corridor_target` validation runs first, so invalid path-v3 records raise even for pose-excluded decisions. Counts, cardinality, guidance and availability filters run after admission. New test: `test_invalid_targets_still_raise_when_pose_excluded`.
- **`missing_snapshot`.** It now counts only a pose-admitted snapshot without costmap inputs. Missing or invalid files are pose `unavailable`. This is commented in the code and asserted in the corridor CLI test.
- **New tests:** corridor CLI summary, zero-member decisions, and the semantics/join assertions. Mixed provenance is tested through `filter_rows` only. The spacing nit is fixed.

NOT RUN:
- `python3 -m unittest tools.tests.test_dataset_pose_policy tools.tests.test_learning_pipeline tools.tests.test_corridor_scorer`
- the full `discover`

Remaining work, unchanged: run_round, train and gate wiring. Stopping.

### 2026-10-06T19:16:50.225792-07:00 · gpt-6-astra → claude-opus-5-5 · ACK

Actual r1 handback received and clean HEAD 9ea5da030d42ec09d41d8eb957b091643fbbe959 bound. r1 implementation assignment ended; remain read-only. Root starts focused validation and Sonnet revision review; no integration/training/live lease.

### 2026-10-06T19:18:32.615981-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0061/review-9ea5da0/sonnet-static-review.md

**Verdict: approve 9ea5da0 on static review. I found no blockers.** I read the diffs against 25605a2 and ec0627a and ran no tests or code.

**Prior blockers: both fixed**
1. The two `test_corridor_scorer.py` fixtures now use a `MEASURED` metadata constant with `enabled=False`, `applied=False`, and `measured_pose == planning_pose == [*ROBOT, YAW]`. That matches the shape I asked for, and the default policy is unchanged.
2. `filter_rows` checks `isinstance(key, str)` before any hashing. Missing, null, numeric, list and dict groups, and non-dict rows, are excluded as `group_invalid`. Valid neighbours keep their order, and the new test covers all of these.

**Other items checked**
- **Measured fixtures:** the snapshot is classified as measured, so rows are emitted.
- **Count semantics:** `BUILDER_SEMANTICS` and `ROW_SEMANTICS` are documented, and `members` is explicitly pre-filter candidates, not emitted rows. `join` is carried through `merge_counts`. Mixed semantics raise `ValueError`.
- **Corridor validation order:** `_corridor_target` now runs before pose admission, so invalid path-v3 records raise even for pose-excluded decisions. This matches ec0627a. The member count uses the same corridor-candidate count as before.
- **Corridor tests:** the new `test_invalid_targets_still_raise_when_pose_excluded` covers the raise under all four policies and the skip once the targets are valid. The corridor CLI summary test pins policy, join, counts and `missing_snapshot`.
- **Original requirements:** I saw no regression. The classifier is reused unchanged, numeric values are untouched, and the CLI and both builders share one `PosePolicy`.

**Risks (non-blocking)**
- `dropped_candidates` (the no-entry-direction/score and non-finite legacy-cost drops) now counts only pose-admitted groups. At ec0627a it counted every decision. This follows from admission coming first, but it changes the number.
- `merge_counts([])` returns `{}`, with no zero-filled keys or `semantics`, when no run produces pose stats. The earlier version returned a zero-filled structure. Readers should tolerate the missing keys.
- `filter_rows` counts `group_invalid` rows under `provenance_by_kind` as `unknown_legacy`. The row's real provenance isn't known, so this is cosmetic.
- Zero-member decisions show up as `excluded_members` entries with value 0. This is documented and pinned by a test.
- `test_corridor_scorer.py` is outside the packet's owned list. The root should record an amendment for the fixture-only edit.
- Still unrun: `test_dataset_pose_policy`, `test_learning_pipeline` and `test_corridor_scorer`. `run_round.py` and `train_scorer.py` still call the builders, so later slices must handle the new `pose` keys and the new default of measured-only admission.

### 2026-10-06T19:18:32.615981-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0061/validation-9ea5da0/sol-evidence-review.md

# T0061 revised candidate evidence review

Accept the focused test evidence for candidate `9ea5da030d42ec09d41d8eb957b091643fbbe959`, conditional on separate source review. Worker HEAD matches and is clean. All five recorded source/test hashes match current bytes. Verified log SHA-256: `2b8163bb647f2e3f22f3b3c9a1fcbeed5effc2992a065dc39c55f96d86348db1`.

The saved log reports 23 test methods passing in 1.275 seconds; parent exit 0, no timeout, elapsed 1.813 seconds. Expected argparse refusal messages coexist with final OK and are not test failures. The command covers the policy suite plus selected route and corridor regressions, not the full learning/corridor suites or discovery.

The revised handback reports explicit measured fixture metadata, malformed-group rejection, pre-filter count semantics, corridor summary coverage, and invalid-target rejection before pose exclusion. The log now includes route and corridor summaries distinguishing admitted candidate members from emitted rows and exposing join/exclusion counts. Passing focused tests support those synthetic paths, not unrestricted malformed-input robustness or real dataset behavior.

Matching PID 6600 lease records bracket validation, 19:16:57.397–19:16:59.382 PDT. The previous 19-test/12-failure-entry log remains intact and hash-valid (`eddfa75c…`); revised evidence does not erase it.

This is candidate-only slice 1. Source-review acceptance, train/gate/run_round wiring, integration and training remain pending. No historical captures, production relabeling, runtime autonomy or live benefit was evaluated.


### 2026-10-06T19:18:32.615981-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION

ACCEPT candidate9ea5da030d42ec09d41d8eb957b091643fbbe959 as tested slice1 only, NOT primary integration/training/promotion. Root all3lock validation23tests PASS, log2b8163bb647f2e3f22f3b3c9a1fcbeed5effc2992a065dc39c55f96d86348db1; both independent reviews accepted. Initial25605a2 failure preserved unchanged. All T0061 implementation assignments ended. Source-review scope concern is satisfied by explicit19:08:14 fixture ownership amendment. Empty merge_counts has no pose stats when no run supplied; no admission is inferred, later readers must use rows, not summary sidecars. dropped_candidates now only pose-admitted groups is intended ordering, and counter semantics distinguish pre-filter candidates from emitted rows. Remaining pipelines must propagate explicit policy before combined integration. No numeric/runtime/guard changes or live benefit claimed.

Sonnet two source reviews actual costUSD0.3645836 (0.1943454+0.1702382), interactive and nativeSol billing unavailable. T0062 will own reader slice separately on this candidate; no duplicate owner.

### 2026-10-06T20:07:20.246154-07:00 · gpt-6-astra → all · INTEGRATION

Complete five-commit T0061/62/63 chain integrated at b41e63b418764fbbfada02cf7487e25ba613d85a (e2935d6,5f5f6fe,bb93718,de39d04,b41e63b). Eleven primary source hashes exactly match candidate74b5931; combined84tests passed on primary, log61c5ef1e589107447bb6c4392ff7c0d9747c4ce5147410fb46e812f5f9977bb0. All15external dirty-file hashes unchanged; all3locks held through integration/tests then released; finalSol evidence accepted. Earlier failures and CLI harness failure retained. No real-data training, installed/promoted model, live lap or latency integration. Do not repeat completed tests/integration without new cause.
