---
id: T-0062
title: Apply one pose policy in training and promotion dataset readers
status: in-progress
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0062-dataset-readers-opus
base: 9ea5da030d42ec09d41d8eb957b091643fbbe959
candidate: 4df0e7334bb1f31cb95ad587ce1df78377a7eb1a
claim: implemented
lease: none
updated: 2026-10-06
---

# Packet

ONLY INTERACTIVE user-started Claude session alias interactive-opus-t0062-20261006,
same actual session as completed T0061. ACK exact alias/model claude-opus-5-5.
One reserved worker slot. No headless duplicate. Isolated worktree
C:/Users/brand/.codex/worktrees/igvc-t0062-dataset-readers/IGVC SIM,
branch codex/t0062-dataset-readers-opus, base9ea5da030d42ec09d41d8eb957b091643fbbe959.
Primary docs/agents/ is canonical. Read README intro and this packet, T0061 accepted
API/code as needed. This base includes accepted dataset-builder slice1 only;
primary source is unchanged. Slice2 of3: NO primary integration, real training,
model generation/promotion, replay or live run. Slice3 must wire run_round/cache
and pass combined end-to-end tests before primary integration/training.

Own ONLY tools/learning/dataset_policy.py (shared reader API extension),
tools/learning/train_scorer.py, tools/learning/round_gate.py,
NEW tools/tests/test_dataset_readers_pose_policy.py,
tools/tests/test_learning_pipeline.py and tools/tests/test_learning_round.py
ONLY necessary synthetic reader/gate fixture compatibility. No run_round source,
build_dataset/classifier/recorder/teacher/runtime changes. Never primary source.

Requirements:
- Replace duplicated JSONL group readers with a shared dataset_policy reader
which uses existing filter_rows BEFORE existing >=2 candidates/exactly one
heuristic-choice filtering. Keep public load_rows wrappers returning lists for
existing callers, with optional explicit policy. Document API returning rows and
admission statistics for reports. Preserve valid input row numeric/features/order,
groups and existing cardinality/heuristic semantics. No replenishment.
- Default measured-only; combinable --allow-predicted and --allow-unknown-legacy
in train CLI and gate CLI. Unknown/unlabelled historical rows require same unknown
opt-in; never infer provenance from flags/source hashes/summary sidecars. Malformed
and unavailable always excluded. Any excluded/mixed member drops whole group,
even if remaining members would form a valid ranking group.
- gate(..., pose_policy=...) must support DIRECT FUNCTION callers as well as CLI;
run_round currently calls it directly and will be wired in next slice. Record
pose_policy and actual admission counts in train/gate reports, including no usable
rows. Distinguish pre-pose, pose-admitted and final usable counts. Do not make an
empty dataset promotable or run fitting when no rows remain. Honor report-out/out
on empty outcomes so exclusions remain reviewable. Keep model schema/features,
CV folds/course grouping, significance thresholds, selection and promotion rule
unchanged. No new trained model metadata schema is needed for this slice.
- Tests synthetic only: same row populations through both public readers/all four
policy combinations, legacy row opt-in, mixed or forbidden member in otherwise
valid group, malformed group field, numerical immutability, CLI flag and direct
gate policy propagation, empty report fail-closed behavior/counters. Use mocks
for fitting/CV where necessary; no real captures/labels/course geometry. Update
only synthetic fixtures that intentionally represent measured poses, never
relabel historical data. Preserve existing tests' intended assertions.
- Scope includes clear reporting of malformed JSON input if reader rejects it;
no silent partial dataset acceptance. Reuse canonical classifier indirectly via
row policy; don't duplicate it.

Edit/commit owned files only. No tests/imports/providers/delegation/live/build;
syntax-only ast.parse is permitted. Root validates after actual handback under
all3simulator locks and obtains Sonnet source/Sol evidence review. Target6min/USD5
interactive usage target, not billing guarantee; report incomplete at bound.
Handback <=300words with commitSHA, API, files, NOT RUN commands, unresolved risks;
append ACK/HANDBACK to this primary task log only. Stop after handback/blocker.

## Log

### 2026-10-06T19:18:32.615981-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

INTERACTIVE interactive-opus-t0062-20261006 ONLY. T0061 assignments ended and accepted candidate remains frozen. Prepared separate worktree/branch above; ACK exact alias/model before editing. No tests/live lease or primary integration. No other session owns this task; posting alone is not ACK.

### 2026-10-06T19:18:45-07:00 · claude-opus-5-5 → gpt-6-astra · ACK

ACK T-0062, alias interactive-opus-t0062-20261006, model claude-opus-5-5. This is the same interactive session that completed T-0061.
- Worktree: .codex/worktrees/igvc-t0062-dataset-readers, branch codex/t0062-dataset-readers-opus, base 9ea5da0.
- Files: owned files only.
- Checks: static ast.parse only. No tests, imports or live work.

### 2026-10-06T19:19:44.092857-07:00 · gpt-6-astra → claude-opus-5-5 · ACK

Actual19:18:45 ACK and exactmodel confirmed; sole interactive-opus-t0062-20261006 ownership active. No duplicate dispatch. T0061 frozen accepted23test candidate remains unintegrated. Root validates only after actual committed T0062 handback; no live lease.

### 2026-10-06T19:22:01-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK

Alias interactive-opus-t0062-20261006, model claude-opus-5-5. Commit **4df0e73** on codex/t0062-dataset-readers-opus, parent 9ea5da0.

Files:
- tools/learning/dataset_policy.py
- tools/learning/train_scorer.py
- tools/learning/round_gate.py
- NEW tools/tests/test_dataset_readers_pose_policy.py
- tools/tests/test_learning_round.py: its synthetic rows are now explicitly measured; no other change.

API:
- `read_dataset_rows(path, policy=None)` → `(usable rows, stats)`.
  - It runs `filter_rows` first (default measured-only), then the unchanged ranking rule: ≥2 members and exactly one truthy `heuristic_choice`.
  - Stats: `semantics`, `pose_policy`, `pre_pose`, `pose` (filter counts), `pose_admitted`, `ranking_excluded` and `usable` (rows and groups each).
  - Malformed JSON or a non-object line raises `ValueError` naming `path:line`; nothing is partially accepted.
  - Row values and the previous group-major order are kept.
- `add_pose_policy_arguments(parser)` and `policy_from_args(args)` add the shared flags.
- `train_scorer.load_rows(path, pose_policy=None)` and `round_gate.load_rows(path, pose_policy=None)` still return lists.

Callers:
- `gate(..., pose_policy=None)` works for direct callers. Its reports gain `pose_policy` and `dataset_admission`. An empty report has `rows=0` and promote=False.
- Both CLIs take `--allow-predicted` and `--allow-unknown-legacy`. `--report-out` and `--out` are written for empty datasets (train exit 1) and rejected ones (exit 2); nothing is fitted or promoted.
- Model schema, features, CV, thresholds and the promotion rule are unchanged.

NOT RUN:
- `python3 -m unittest tools.tests.test_dataset_readers_pose_policy tools.tests.test_learning_round tools.tests.test_learning_pipeline tools.tests.test_dataset_pose_policy tools.tests.test_corridor_scorer`
- the full `discover`

Risks:
- A missing `heuristic_choice` now counts as false. The old train reader raised KeyError; the gate reader did the same through `bool()` of a lookup.
- `run_round` passes no policy and no flags, so real rounds become measured-only. Unlabelled historical datasets now produce no usable rows until slice 3 wires an explicit policy and cache key.
- The gate CLI previously crashed on malformed JSON; it now exits 2 with a report.

Stopping.

### 2026-10-06T19:32:51.677907-07:00 · gpt-6-astra → claude-opus-5-5 · ACK

Actual committed handback received, clean HEAD 4df0e7334bb1f31cb95ad587ce1df78377a7eb1a bound. T0062 implementation assignment ended; remain read-only during root validation/Sonnet review. No integration/training/live lease.

### 2026-10-06T19:34:38.958801-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0062/review-4df0e73/sonnet-static-review.md

**Verdict: ACCEPT, with one should-fix.** I found no blocker for pose admission. This is static review only; I ran nothing.

**What checks out**
- **Shared reader:** both `load_rows` wrappers delegate to `read_dataset_rows`, which runs `filter_rows` before the ≥2-members and exactly-one-heuristic rule. Group-major order and row values are kept. Nothing is replenished.
- **Whole-group drop:** `admit_group` drops a group on any disallowed or mixed member, including measured+predicted under `--allow-predicted`. A group in which only one row lacks pose fields is dropped as mixed. Unlabelled rows need the unknown opt-in. Malformed and unavailable rows are never admitted.
- **Propagation:** both CLIs take the same two flags. Direct `gate(pose_policy=...)` defaults to measured-only, and a mocked test pins the CLI→`gate` kwarg. `run_round` passes no policy, so it is measured-only until slice 3.
- **Reports:** reports carry `pose_policy` plus pre-pose, pose-admitted and usable counts. The empty paths skip fitting and CV, set `promote=False`, and still write `--out`/`--report-out`.
- **No drift:** model schema, CV, thresholds and the promotion rule are untouched.

**Should-fix: `heuristic_choice` handling**
- The new `bool(m.get(...))` matches the old gate reader, but it is looser than old train, which used a raw `sum()`.
  - A value of `2` is now one heuristic choice.
  - Strings such as `"false"`, `"0"` or `"no"` are now admitted as the heuristic choice.
  - Old train excluded the first or raised on the others.
- Missing-as-false admits a group where one member lacks the key and another is `True`. Downstream, `_pick` and `heuristic_picks` index `['heuristic_choice']` directly (`train_scorer.py:85,100`, `round_gate.py:83,102`). The result is an uncaught `KeyError` after admission, with no report.
- Suggested fix: require `type(v) is bool` on every member. Otherwise drop the group, counted under `ranking_excluded` or a malformed bucket. Builders only emit bools, so real data is unaffected.

**Risks**
- `round_gate.main` catches every `ValueError` from `gate` and labels it "rejected dataset". That includes `Course-held-out CV needs at least two courses` and a `JSONDecodeError` from a bad `--new` model file. It still fails closed, but the label is misleading. Narrow the try to the dataset read.
- `PosePolicy(allow_predicted="false")` passed directly would be truthy and admit predicted rows. `policy_from_args` coerces to `bool`, so only direct callers are exposed.
- An explicit `measured` row is trusted without checking its reason string. That is existing T0061 behavior.
- Test gaps: nothing covers non-bool or missing `heuristic_choice`, a ValueError from CV inside the gate CLI, or empty or all-excluded runs through the gate CLI.
- Gate output keys are only added, never removed. The old train error text changed.

### 2026-10-06T19:34:38.958801-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0062/validation-4df0e73/sol-evidence-review.md

# T0062 candidate evidence review

Accept focused validation evidence for candidate `4df0e7334bb1f31cb95ad587ce1df78377a7eb1a`, pending independent source acceptance. Worker HEAD matches and is clean; all five recorded source/test hashes match current bytes. Verified log SHA-256: `52d7d658fba5cd2710cf0577fcc65edb32c0ade3bf32f220f6f8789e0e141f6c`.

The saved log reports 26 tests passing in 0.025 seconds; parent exit 0, no timeout, elapsed 0.359 seconds. Its command selects only the dataset-reader and dataset-policy suites. The modified `test_learning_round.py` is hash-bound but not exercised by that command; full learning/corridor suites and orchestration remain unvalidated here.

The reader tests use synthetic rows and mocked model/CV paths. Their covered cases include public-reader policy agreement, unknown opt-in, whole-group exclusion, malformed groups/JSON, numerical/order preservation, CLI and direct-gate policy propagation, and empty/rejected reports without fitting or promotion. Reaching mocked fitting proves admission/dispatch, not successful real training, model quality or promotion correctness on historical data.

Matching PID 11624 held/released records bracket validation, 19:33:06.929–19:33:07.442 PDT. No tests or imports were rerun for this review.

This is unintegrated slice 2. Source review must assess the disclosed missing-heuristic behavior change and remaining compatibility risks. `run_round` policy/cache propagation and combined acceptance are still pending. No historical captures, production dataset rebuild, real training, live benefit or runtime promotion was evaluated.


### 2026-10-06T19:34:38.958801-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

Revision r1 ONLY to INTERACTIVE interactive-opus-t0062-20261006-r1, same actual session. Prior implementation ended; ACK exact alias/model. Same worktree/branch start4df0e7334bb1f31cb95ad587ce1df78377a7eb1a. Original owned files only; no tests/imports/providers/live. Root all3lock validation26PASS (mocked fitting), Sol bindings accepted. These passes do not cover missing/nonboolean heuristic_choice; retain them unchanged. Root treats the review's should-fix as acceptance-blocking because it broadens malformed admission and can crash after admission.

Require a present strict boolean heuristic_choice on EVERY member before ranking cardinality; otherwise reject the WHOLE group with a distinct counted reason. Do not coerce2/string/None/missing, and never drop just the invalid row to rescue a group. Synthetic tests must cover these malformed values through both public readers; valid bool groups unchanged, forbidden/mixed pose guard still first. Document strictboolean policy; canonical builders emit bool so validdata unchanged.

Also address related direct-call ambiguity: PosePolicy must reject non-bool constructor optins, not treat stringfalse as permission. Add constructor tests without changing validdefault/explicitbools. Distinguish dataset-read rejection from model/CV evaluation errors in gate CLI reports; use narrow/typed dataset exception or honest distinct classification, keep errors failclosed and --out written, and test CV/modelfailure not mislabeled dataset rejection. Do not change CV/model mathematics or promotion thresholds.

Bound6min/USD5 target; static ast.parse only, no execution. Commit corrections and handback <=300words SHA/API/testsNOTRUN. Root fresh focused checks/review then candidate-only acceptance. No run_round wiring/integration/training yet. Stop after handback/blocker.

### 2026-10-06T19:35:01-07:00 · claude-opus-5-5 → gpt-6-astra · ACK

ACK r1, alias interactive-opus-t0062-20261006-r1, model claude-opus-5-5. Same session, worktree and branch, starting at 4df0e73. Original owned files only. Static ast.parse only.

### 2026-10-06T19:35:38.627695-07:00 · gpt-6-astra → claude-opus-5-5 · ACK

Actual19:35:01 r1 ACK exactmodel received; sole revision owner interactive-opus-t0062-20261006-r1 active. Initial candidate26tests passed but source acceptance blocked as described, preserved unchanged. Source reviewUSD0.2006082/48.33s; interactive/nativeSol cost unavailable. Locks released after root validation. Future slice3 static preflight at artifacts/agents/T-0062/next-slice-preflight/notes.txt records policy/cache bypass paths and corridor-label prerequisite; not an assignment. No integration/training/live lease.
