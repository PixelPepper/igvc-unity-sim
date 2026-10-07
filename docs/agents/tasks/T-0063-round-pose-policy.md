---
id: T-0063
title: Propagate dataset pose policy through learning rounds and cache reuse
status: in-progress
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0063-round-policy-opus
base: f9594e6c3e462bb6d223fed3b57edc5661eebd34
candidate: none
claim: none
lease: none
updated: 2026-10-06
---

# Packet

ONLY INTERACTIVE user-started Claude session interactive-opus-t0063-20261006,
same actual session as completed T0062. ACK alias/model claude-opus-5-5. One reserved
worker slot, no headless duplicate. Isolated worktree
C:/Users/brand/.codex/worktrees/igvc-t0063-round-policy/IGVC SIM,
branch codex/t0063-round-policy-opus, base f9594e6c3e462bb6d223fed3b57edc5661eebd34.
Read README intro, this packet and source APIs. Primary task log authoritative.
T0061+T0062 accepted candidates are on this branch; primary not integrated.
Slice3: runtime/teacher/model algorithms untouched. No real training, labels,
replay, model promotion, live or primary integration. Root runs combined checks
and reviews before integrating complete candidate range.

Own ONLY tools/learning/run_round.py, NEW tools/tests/test_round_pose_policy.py,
and tools/tests/test_learning_round.py necessary orchestration fixture/assertion
compatibility. Do not edit sharedreader/build_dataset/train/gate/classifier or
teacher/runtime, primary source. Report blocker if scope is insufficient.

Implement:
1. Reuse dataset_policy.PosePolicy/shared flags. measured-only default and explicit
combinable predicted/unknown optins; no implicit historical optin. Pass selected
flags into BOTH build/train command argv for route/corridor. Pass pose_policy
object to DIRECT round_gate.gate. Record canonical policy in round reports and
build/train/gate step results, including empty/error outcomes where available.
2. Include canonical policy + policy-cache version in build/train/gate cache
inputs. Old caches with absent policy cannot stand in for new-policy validation.
Round.step's imported status must not bypass input identity for these steps;
preserve legitimate imported collection/replay and plan freezing. Gate's early
same-current/new-model SHA shortcut also needs bound policy/data identity, not
just a model hash. Changing policy must reevaluate even if resulting dataset or
model bytes happen to be equal. Unchanged policy with same inputs may resume.
3. Builder now reads snapshots: include deterministic snapshot input identity in
build dependency cache along with outcomes/labels. Detect additions/removals and
content changes even equal-size/restored-mtime fixtures (content digest required,
not timestamps alone). Do not materialize full decompressed snapshots/geometry.
Validate cached output content identity before reusing dataset/model steps;
do not blindly accept file existence after mutation. Keep checks offline.
4. Narrow existing CLI compatibility prerequisite: old run_round teacher command
implicitly uses straight-v1, but builder now requires explicit corridor-label.
Preserve that CURRENT legacy mode in this slice by passing --corridor-label
straight-v1 explicitly to teacher label command and corridor builder only. Bind
mode in label/build cache identity. Do NOT introduce path-v3 default or automatic
conversion. Existing path-v2/mismatched labels must fail validation, not be
silently accepted because a cached/imported label exists. Reuse builder label_mode
validation as needed; never overwrite/delete existing teacher outputs. If an
incompatible/partial immutable output prevents labeling, fail with fresh-output
instruction rather than replace it. A later task may select path-v3 with isolated
output roots; not this slice. No actual teacher execution now.
5. Preserve no-promote semantics, seed registry/collection settings, runtime
inputs, model schema/CV/significance/thresholds and immutable historical artifacts.
No sampling/training/replay hidden inside tests or implementation.

Synthetic tests (mock command runner and gate/fitting): both kinds/all4policies
propagate exactflags and directgatekwarg; default no widening; same-policy resume
skips work, changed-policy invalidates build/train/gate including imported and
already-promoted shortcuts; altered snapshot bytes same size/mtime invalidates;
changed output content invalidates reuse; malformed/mismatched corridor labels
fail closed, explicit straight-v1 validmode, no immutable output overwritten;
empty/excluded gate not promoted; dry-run writes nothing. Preserve expected
valid row values. Full end-to-end synthetic pipeline checks by root after handback.

No tests/imports/providers/delegation/build/live by worker; syntax ast.parse only.
Target6min/USD5 interactive target, not billing guarantee. Report incomplete at
bound; no silent extension. Commit owned files only. Handback <=300words SHA/API,
files, commandsNOTRUN/risks. Stop after handback/blocker. Root Sonnet source review,
all3lock focused/combined tests, Sol evidence; no user questions needed.

## Log

### 2026-10-06T19:48:50.437273-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

INTERACTIVE interactive-opus-t0063-20261006 ONLY. T0062 assignments ended; new isolated branch/worktree prepared from acceptedcandidate. ACK exactalias/model before editing. No livelease/primaryintegration/realtraining. Root treats posted dispatch as pending until actualACK.

### 2026-10-06T19:49:04-07:00 · claude-opus-5-5 → gpt-6-astra · ACK

ACK T-0063, alias interactive-opus-t0063-20261006, model claude-opus-5-5. This is the same interactive session that completed T-0062.
- Worktree: .codex/worktrees/igvc-t0063-round-policy, branch codex/t0063-round-policy-opus, base f9594e6.
- Owned files: run_round.py, new test_round_pose_policy.py, and the test_learning_round.py fixtures only.
- Checks: static ast.parse only. No tests, imports or teacher runs.

### 2026-10-06T19:49:49.814208-07:00 · gpt-6-astra → claude-opus-5-5 · ACK

Actual19:49:04 ACK/exactmodel received. Sole interactive-opus-t0063-20261006 implementation active; no duplicate owner or livelease. T0062 source/evidence accepted candidate-only, source assignments ended. Await actual committed handback for review/combined validation; no primary integration until full chain accepted.
