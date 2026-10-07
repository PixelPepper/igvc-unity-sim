---
id: T-0061
title: Add explicit pose provenance to dataset builders and shared policy
status: in-progress
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0061-dataset-pose-builder-opus
base: ec0627a
candidate: none
claim: none
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
