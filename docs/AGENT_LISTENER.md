# Agent message listener

`tools/agents/wait_message.py` prints task-log messages addressed to one recipient
(exact model id, `user`, or entries addressed to `all`). It reads only
`docs/agents/tasks/T-*.md` and never edits task logs, dispatches work or ACKs.
This page describes the listener only; the canonical message protocol remains
[docs/agents/PROTOCOL.md](agents/PROTOCOL.md).

**A listener does not wake an idle agent.** Printing a message does not start a
session, prove that an agent read it, or count as receipt/ACK. Something that is
already running (a monitor, a person, an agent's own wait step) must consume the
output and act on it.

## Modes

| Mode | Startup behaviour | State written |
| --- | --- | --- |
| no `--cursor` (legacy) | ignores messages present at start; prints only later ones | none |
| `--cursor PATH` | prints every addressed message not recorded in `PATH`, immediately | `PATH`, `PATH.lock`, `PATH.<pid>.tmp` |

Legacy mode misses a dispatch written while no listener was running. Use
`--cursor` when delivery across restarts matters.

Exit codes: `0` message printed, `2` timeout, `1` error (bad cursor, lock held,
output or save failure). `--watch` keeps running and never times out.
`--timeout` and `--poll` must be finite positive seconds.

## Cursor behaviour

- **First run replays.** A missing cursor means nothing has been delivered yet, so
  every existing addressed message is printed at once. The listener never seeds
  the cursor from current messages, which could hide a pending dispatch. Expect a
  large backlog on first use; it is printed once and then recorded.
- **Restart catches up.** With an existing cursor, entries posted while offline are
  printed immediately on start, before any polling.
- **Identity binding.** The cursor stores `version`, `recipient` and the resolved
  task directory. Using it with another recipient or checkout fails with exit 1.
  Message IDs are the log file name plus the exact heading line; editing a heading
  makes it a new message.
- **One consumer per cursor.** `PATH.lock` is held for the life of the process
  (`msvcrt` on Windows, `flock` on POSIX). A second listener on the same cursor
  exits 1 instead of overwriting state. The lock file is kept on purpose; the OS
  releases the lock when the process exits, so no stale-lock cleanup is needed.

## Delivery guarantee: at-least-once

Each batch is printed and stdout is flushed **before** the cursor is atomically
replaced (temp file, `fsync`, `os.replace`). Therefore:

- If printing fails (closed pipe, etc.), nothing is marked delivered; exit 1.
- If saving fails, or the process dies after printing but before saving, the
  previous cursor is intact and the same messages are printed again next run.
- Delivery is **never exactly-once.** Consumers must tolerate duplicates, e.g.
  by keying on `[file] heading`.

## Failure recovery

| Error | Meaning | Recovery |
| --- | --- | --- |
| `corrupt cursor` / `unsupported cursor version` | file is not valid v1 state | inspect it; it is never reset automatically. Move it aside to replay everything. |
| `belongs to recipient ... and tasks ...` | wrong recipient or worktree | use that consumer's own cursor path |
| `is locked by another listener` | another live process holds `PATH.lock` | stop that listener or use a distinct cursor |
| `cannot save cursor` | printed but not recorded | fix the disk/permission issue; the batch will repeat |

## Examples

Use a separate cursor per consumer (recipient × checkout × monitor). Keep cursors
outside `docs/agents/tasks/`.

Windows (PowerShell):

```powershell
python tools/agents/wait_message.py --to claude-opus-5-5 `
  --cursor "$env:LOCALAPPDATA\igvc-agents\opus-monitor.json" --watch --poll 10
python tools/agents/wait_message.py --to gpt-6.1-sol `
  --cursor "$env:LOCALAPPDATA\igvc-agents\sol-oneshot.json" --timeout 1800
```

WSL / Linux:

```bash
mkdir -p ~/.local/state/igvc-agents
python3 tools/agents/wait_message.py --to claude-sonnet-5-5 \
  --cursor ~/.local/state/igvc-agents/sonnet-wsl.json --timeout 3600
```

A Windows listener and a WSL listener reading the same checkout see different
resolved task paths (`C:\...` vs `/mnt/c/...`), so they need different cursors;
reusing one fails the identity check. Do not share a cursor across machines or
synchronised folders: the lock only covers processes on one host.
