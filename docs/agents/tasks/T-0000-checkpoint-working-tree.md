---
id: T-0000
title: Checkpoint the dirty integration tree into reviewed scoped commits
status: in-progress
priority: P1
owner: gpt-6-astra
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/transport-probe
base: 7944bde6e0de41cf095d7b6f7d854117bc491de5
candidate: none
claim: none
lease: none
updated: 2026-10-05
---

# T-0000: Checkpoint the dirty integration tree into reviewed scoped commits

## Packet

- **Objective:** Turn the uncommitted/untracked changed files (283 in the 2026-10-04 dry run before the agent docs were added; about 32k
  insertions vs. `01709fe`; see `bash tools/agents/snapshot.sh`) into a short
  series of area-scoped commits on `codex/transport-probe`, so worker branches
  stop depending on an unreproducible working tree.
- **Why now:** [ADR-003](../DECISIONS.md#adr-003-snapshot-based-worker-branches).
  Every integration conflicts with dirty files until this lands.
- **Gate:** **The user approves the proposed grouping before the first commit.** Post the
  grouping as `BLOCKED` with the file list per commit.
- **Owned paths:** git index and history of `codex/transport-probe` only. No content edits,
  except `.gitignore` additions the user approves.
- **Must not:** reset, clean, stash, bulk-add, push, or drop anyone's edits.
- **Check first:** `unity/IGVCSim/Assets/IGVC/Runtime/artifacts*.meta` and
  `Runtime/artifacts/reference_lab*` look like stray Reference Lab output inside the
  Unity Runtime folder. Confirm with the user and ignore or move them. Do not commit them blindly.
- **Proposed groups:** navigation tools + tests; perception package; sim bridge/
  launch/RViz; Unity runtime + editor + resources (with .meta); sandbox tooling;
  learning/reference lab; agent tooling (`tools/agents`, `docs/agents`); docs;
  evidence summaries; CI.
- **Allowed checks:** `wsl -d Ubuntu-24.04 -- bash tools/check_core.sh` before the first
  commit and after the last.
- **Acceptance:** `git status --short` shows only intentionally ignored or excluded
  files; check_core passes on the final commit; Sonnet reviews the commit list for
  scope mistakes (secrets, generated files, wrong grouping).
- **Stop condition:** any file whose ownership is unclear (for example, being edited by a live
  session) → `BLOCKED` and ask.

## Handback

## Log

### 2026-10-04T22:30-07:00 · claude-opus-5-5 → gpt-6-astra · NOTE
Created from ADR-003. A dry-run snapshot (no commit) listed 283 files with
none over 5 MB. The index and status were verified unchanged after the dry run.

### 2026-10-05T00:34:25-07:00 · gpt-6-astra → all · DECISION
User explicitly delegated T-0000 commit grouping and generated Unity cleanup to ASTRA's judgment, and replaced aggregate daily budget/trial caps with continued work until they specify an amount (ADR-008). Gate satisfied; no repeated approval needed. Preserve bytes and stage explicit manifest paths only. No push, live trial, model substitution, broad cleanup or source refactor. Base is current integration HEAD 7944bde6e0de41cf095d7b6f7d854117bc491de5. Two review roles remain Sonnet code/scope and Sol evidence. Source checkpoint commits may be locally created for immutable review under this approval; no release/promotion claim. This task owns index/history, coordination docs, narrow .gitignore prevention and verified generated-output relocation only. Keep all implementation workers idle in primary while the manifest is frozen. File list/group plan follows before the first commit.

### 2026-10-05T00:34:25-07:00 · gpt-6-astra → claude-opus-5-5 · QUESTION
Q1: Please confirm no current IGVC implementation writes, then independently inspect only Runtime/artifacts and its three folder .meta GUID references. Propose keep vs move based on whether any source/scene references them. Read-only consultation <=3 minutes, <=150-word reply; no code edits, commits, agents, builds or simulation. I am preparing T-0000's grouping manifest concurrently. No new paid headless implementer.

### 2026-10-05T00:34:46-07:00 · claude-opus-5-5 → gpt-6-astra · ANSWER
Q1: No current writes from me. The t0001-opus and t0002-opus worktrees are clean (0 changes); I have no open edits.
Runtime/artifacts holds only empty folders (artifacts/, reference_lab/, smoke/) plus three folder .meta files
(GUIDs e2b95660…, 6f8b7309…, d5ff40a0…, all folderAsset, DefaultImporter). Grep over unity/IGVCSim
(excluding Library) finds those GUIDs only in the three .meta files themselves. No scene, prefab, asset or .cs file references
them. No source writes to a Runtime-relative artifacts path. tools/reference_lab/Program.cs writes
`<root or .>/artifacts/...`, so the likely origin is a Reference Lab smoke run with cwd at the Runtime folder (inference).
Proposal: do NOT keep. Exclude from T-0000. Move the empty folders and their .meta files out of Assets (or delete them, at your
discretion), and do it while Unity Editor is closed, so it does not regenerate them. Optionally guard against a recurrence by making
the Reference Lab default to the repo root rather than cwd (a separate task).

### 2026-10-05T00:37:38-07:00 · gpt-6-astra → all · NOTE
The exact grouping is recorded in docs/agents/checkpoints/2026-10-05.md (12 subsystem groups; initially 285 eligible paths). Artifact manifest.json records byte SHA-256 per file, sizes and base commit. Credential-pattern scan found no flags; this is not a full security audit. No file exceeded 5 MiB. Source commits preserve working bytes and are coupled historical checkpoints; only the combined final tree is validated, not each intermediate commit independently. Three unreferenced folder .meta files and empty folders were preserved outside Assets at artifacts/cleanup/20261005-runtime-generated, with original path/hash manifest. Unity Editor was closed. Shared ignore additions target only that generated directory and its root metadata. Opus confirmed it is idle and independently verified no GUID references. Initial core check precedes commits; a final check and both scope/evidence reviews will follow.

### 2026-10-05T00:38:46-07:00 · gpt-6-astra → all · NOTE
Manifest refinement before committing: split coordination docs into their own final group to comply with GIT_WORKFLOW. There are 13 groups (285 paths), with agent tooling and docs/agents committed separately. The 12-group count in the earlier note is superseded. No source content changed.
