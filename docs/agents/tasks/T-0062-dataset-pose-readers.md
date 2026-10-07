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
candidate: none
claim: none
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
