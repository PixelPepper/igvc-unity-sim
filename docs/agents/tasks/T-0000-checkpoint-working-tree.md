---
id: T-0000
title: Checkpoint the dirty integration tree into reviewed scoped commits
status: backlog
priority: P1
owner: gpt-6-astra
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/transport-probe
base: 01709fe
candidate: none
claim: none
lease: none
updated: 2026-10-04
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
