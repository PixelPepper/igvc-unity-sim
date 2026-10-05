# Project Observatory integration

This is a local observation prototype shared with the **Research agent network
visualizer** Codex chat (`01a10ab7-b8b1-7552-bc4e-ac91c3ec1018`). Its owner maintains
the app outside this repository at:

`C:/Users/brand/Documents/Codex/2026-10-04/cre/outputs/project-observatory`

The IGVC coordinator remains this project's orchestrator. The visualizer is a
read-only observer, not a second owner of IGVC source, tasks or simulator leases.
Current integration work and verification are recorded in
[T-0004](tasks/T-0004-observatory-integration.md).

## Data and identity

- Canonical task state: `docs/agents/tasks/T-*.md`; the generated board can lag.
- Bounded snapshot: `artifacts/agents/observatory/coordination.json`.
- Schema version 1 contains `generatedAt`, `projectRoot`, `tasks`, `messages`,
  and `agents`. It carries at most 200 messages and 1,200 characters per summary.
- `sourcePath` and one-based `sourceLine` identify the original task-log entry.
- Message IDs remain stable when preceding Handback content changes line numbers.
- A model/role ID is not a unique process or session. The two ASTRA chats are
  distinct sessions. Task status and owner fields are **declared**; unknown
  activity and unmetered subscription usage remain explicit.
- Git worktree paths are resolved from branch registrations. Candidate commits
  differ from cherry-picked integration commits; use Git's origin trailers.
- `worktreeRole` labels the candidate or assigned checkout; `integrationWorktree`
  and `integratedCommits` separately record verified cherry-pick destinations.
- Message `from` is the author role; `writer` and `relayedFrom` distinguish a
  coordinator-relayed review from a direct entry. Neither establishes a unique
  runtime session without separate evidence.
- Reported usage includes amount, bounded scope and `billingVerified: false`.
  API-equivalent usage is not an invoice or the total cost of all project work.
- The collector labels export events `coordination-export` / `declared`; runtime
  events are a separate observation source with their own coverage limitations.

## Refresh and viewing

The local viewer is at `http://127.0.0.1:4318`, with the read-only state endpoint
at `/api/state`. It was running during the October 5 integration check; the URL
does not imply restart persistence. T-0004 records API and browser verification.

The initial exporter is a coordinator-owned local helper under ignored
`artifacts/agents/observatory/export_coordination.py`. It uses Python's standard
library, reads canonical task files, Git worktree/cherry-pick metadata, and the
three bounded T-0001 Sonnet status files for reported review usage, then replaces
the JSON atomically. It is **not yet a packaged or committed project tool**.
During active coordination, the coordinator refreshes it after relevant messages.
The viewer must display snapshot age. A collector polling an unchanged export
does not make that export current.

From the repository root, with a working Python 3 installation:

```powershell
python -X utf8 artifacts/agents/observatory/export_coordination.py
python -X utf8 tools/agents/wait_message.py --to gpt-6-astra --timeout 180
```

The listener ignores messages already present at startup. Inspect the task tail
when reconnecting; it is not a durable inbox. Windows Python must use UTF-8 output
for the Unicode message arrows; the default cp1252 console failed during this
check, although the canonical Claude reply remained intact.

## Scope and limitations

Public task messages and decision summaries are visible. Private reasoning,
credentials, raw complete chat/tool payloads, CAD, Unity Library and build contents
are outside this integration. Code fences are excluded from exported summaries;
the canonical source link retains review context. Corrections are later messages,
not rewrites of prior history. A public message is a claim, not proof of a test.

This observer does not dispatch agents, stop sessions, grant leases, drive the
robot, approve merges or wake an ended Codex turn. Hooks and agent configuration
are not changed for the demonstration. Continuous refresh, restart persistence
and a durable message cursor require separately tested follow-up work.
