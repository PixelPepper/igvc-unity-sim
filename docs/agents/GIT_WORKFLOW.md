# Git workflow for agents

Adopted 2026-10-04 ([ADR-003](DECISIONS.md#adr-003-snapshot-based-worker-branches)).
The goals are to keep the history reviewable and every claim traceable to a commit, and to never
lose anyone's uncommitted work.

## Current repository state (read before branching)

- Remote: `origin` → [PixelPepper/igvc-unity-sim](https://github.com/PixelPepper/igvc-unity-sim), default branch `main`.
- **Integration branch: `codex/transport-probe`** in the primary checkout
  `C:\Users\brand\Documents\ChatGPT\IGVC SIM`. HEAD is `01709fe`.
- The primary checkout has **a large uncommitted and untracked working set**
  (navigation, sandbox, perception, evidence, docs). HEAD alone is missing
  current features. A worktree made from HEAD is **not** the current project.
- Existing agent branches and worktrees (historical, keep them):
  `codex/agent-baseline-20261001` (snapshot `00a3e70`),
  `codex/sonnet-surface-projection`, `codex/navigation-cancellation-20261001`,
  `codex/opus-path-entry`, under `C:\Users\brand\.codex\worktrees\`.

Always run `git status --short`, `git worktree list` and `git branch -vv` before you branch.

## Branches

| Branch | Purpose | Who commits |
| --- | --- | --- |
| `main` | Published history | Only through user-approved push/PR |
| `codex/transport-probe` (current integration) | Accepted, integrated work and coordination commits | ASTRA only |
| `codex/snapshot-YYYYMMDD[-n]` | Immutable base made from the dirty integration tree | ASTRA, via `snapshot.sh` |
| `codex/tNNNN-<slug>-<role>` | One task, one implementer, for example `codex/t0001-processing-health-opus` | The task owner only |

Keep the `codex/` prefix. The Codex app and existing tooling expect it. Never
rename or delete another agent's branch. Rejected branches stay as records.

## Snapshot before dispatch

Workers start from a **snapshot commit** of the primary working tree, not from HEAD.
Make one with:

```bash
bash tools/agents/snapshot.sh                         # dry run: lists what would be captured
bash tools/agents/snapshot.sh --create codex/snapshot-20261004
```

The helper stages through a **temporary index**, so the primary checkout's index,
files and branch stay untouched. It respects `.gitignore` (artifacts, Unity
`Library/`, credentials) and refuses files over 5 MB unless you pass `--allow-large`.
It creates only a local branch, never pushes it, and prints the snapshot SHA.
Record that SHA as `base:` in the task header.

Review the dry-run list before you use `--create`. If anything secret, generated
or unrelated is listed, fix `.gitignore` or move the file first.

## Worktrees

```powershell
git worktree add "C:\Users\brand\.codex\worktrees\igvc-t0001-opus\IGVC SIM" -b codex/t0001-processing-health-opus <base-sha>
```

- One worktree per active task. Never edit inside another task's worktree.
- Each worktree uses its own ROS build overlay (`IGVC_ROS_WORKSPACE`). Unity
  player builds happen only in the primary checkout, by ASTRA.
- When a task is `integrated` or `rejected`, ASTRA may run `git worktree remove`
  once the branch holds every commit. Never use `--force` on a worktree that has
  uncommitted changes.

## Commits

Workers commit **only their task's owned paths**, staging them explicitly by path
(`git add <path>…`). Never use `git add -A`, `git add .` or `git commit -a`.

```text
<area>: <imperative summary, ≤ 72 chars>

<why, what changed, how it was tested; wrap at 72>

Task: T-0001
Agent: claude-opus-5-5
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

`<area>` is one of `perception`, `planning`, `recovery`, `audit`, `sim-bridge`,
`unity`, `sandbox`, `tools`, `docs`, `agents`, `ci`. Codex/ASTRA commits use
`Agent: gpt-6-astra` and the Codex attribution line its configuration adds.

Rules:

- Commit after the focused tests pass and before you request a live trial. A live trial
  always runs on a clean committed candidate.
- One logical change per commit. Keep test changes with the behavior they test.
- Never amend or rebase a commit after it has been reported as a `candidate`. Add a new commit
  instead, so reviews stay bound to the SHAs they reviewed.
- Large evidence (runs, bags, logs, builds) stays under ignored `artifacts/`. Commit
  only compact summaries under `docs/evidence/<topic>-<date>/`.

## Coordination commits

Changes to `docs/agents/` (board, tasks, decisions) are made and committed **only
in the primary checkout**, in their own commits:

```text
agents: dispatch T-0001; T-0000 accepted
```

Never mix coordination files with source changes in one commit. Workers never
commit `docs/agents/` on task branches.

## Review and integration

1. The handback names `candidate: <sha>`. Reviewers run `git diff <base>..<sha>`
   (scoped to owned paths) and review exactly that SHA.
2. On acceptance, ASTRA integrates **exactly the reviewed range** on `codex/transport-probe`:
   `git cherry-pick -x <base>..<candidate>`. **Never `git merge` a task branch.**
   Its base is a dirty-tree snapshot commit, and merging would import that whole
   snapshot, which nobody reviewed. Never cherry-pick only the tip, because that drops
   earlier task commits.
   - If the integration tree has uncommitted edits to the same files, **stop**.
     Checkpoint those edits first (see below). Do not stash or overwrite them.
   - After T-0000 lands and snapshots equal committed history, the same range rule still applies.
3. Run the combined relevant checks (`wsl -d Ubuntu-24.04 -- bash tools/check_core.sh`
   at minimum, the same suite CI runs) and any live trial on the integrated tree.
4. **Post-integration evidence gate.** New live/audit evidence invalidates earlier
   reviews. Before `claim: promoted`, Sol reviews the integrated commit's run, audit and
   ledger evidence (one evidence-only `REVIEW`). Then ASTRA records the `DECISION`.
5. Tag only promoted baselines: `git tag -a baseline/YYYY-MM-DD-<name> -m "<run id, audit>"`.
6. Update the task (`integrated`), the board and, if the baseline changed, the
   [handoff](../CLAUDE_HANDOFF.md) result table.

## Checkpointing the dirty integration tree

The uncommitted working set is the project's real state, and it is at risk while
it stays uncommitted. Converting it into reviewed, scoped commits is task
[T-0000](tasks/T-0000-checkpoint-working-tree.md). It is owned by ASTRA and requires
user approval of the grouping before the first commit. Group by area (navigation tools,
perception package, Unity runtime, sandbox, docs, evidence), stage explicitly by
path, and run `tools/check_core.sh` once before the first commit and once after the
last. Never reset, clean, or bulk-add.

## Never without explicit user approval

`git push` (any branch), PRs, tags pushed to the remote, `reset --hard`, `clean`,
`checkout -- <path>` or `restore` on someone else's edits, `stash` in the primary
checkout, `rebase` of shared branches, `branch -D` of another agent's branch, or
`worktree remove --force`.

## CI

[`.github/workflows/checks.yml`](../../.github/workflows/checks.yml) runs
`tools/check_core.sh` in `ros:jazzy-ros-base-noble` on push/PR, plus a whitespace
check. That suite includes `tools/tests/test_agent_board.py`, which fails if
[BOARD.md](BOARD.md) is stale or a task header is malformed. Regenerate the board with
`wsl -d Ubuntu-24.04 -- python3 tools/agents/board.py` after you edit tasks. CI cannot run Unity or live trials,
so a green CI run is not a live-trial or audit claim.
