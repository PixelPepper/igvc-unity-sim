---
id: T-0071
title: Preserve agent message delivery across listener restarts
status: ready
priority: P2
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0071-durable-listener-opus
base: 1b56bed
candidate: none
claim: none
lease: none
updated: 2026-10-07
---

# Packet

Explicit HEADLESS owner opus-t0071-listener-20261007 only. Independent of reserved
interactive T0070; no ownership transfer. Worktree
C:/Users/brand/.codex/worktrees/igvc-t0071-durable-listener/IGVC SIM.
Base is a scoped clean-source snapshot: root checked wait_message.py equals HEAD;
external navigation/Unity working edits are deliberately excluded and untouched.

Read README intro, this packet, tools/agents/wait_message.py. The listener currently
ignores entries present at startup and has no durable cursor. A dispatch written
between listener runs can therefore be missed. Fix this delivery gap, without
claiming that printed messages start agents or prove receipt/ACK.

Own ONLY tools/agents/wait_message.py, NEW tools/tests/test_wait_message.py,
NEW docs/AGENT_LISTENER.md. All other files read-only. SOURCE ONLY: no tests/imports,
providers, delegation, live simulations, Unity, installs or primary changes.
Static ast.parse is allowed. Root will run focused tests separately.

Acceptance:
- Add opt-in --cursor PATH; unchanged no-cursor mode keeps startup-ignore behavior.
  Cursor identity binds exact recipient and resolved task directory. Versioned,
  strictly validated JSON state stores delivered message IDs (filename + heading).
- Missing cursor replays all addressed existing messages immediately; existing
  cursor immediately emits unseen entries including messages posted while offline.
  Do not silently seed from current messages and lose a pending dispatch.
- Flush stdout before persisting delivery; document at-least-once crash semantics,
  never exactly-once. Failure to print/save must not silently mark entries consumed.
  Atomic replacement and process-held cross-platform cursor lock prevent two
  consumers from overwriting state. Keep lock file; no stale-file deletion heuristics.
  Corrupt state, wrong identity, or concurrent lock fails clearly without resetting.
- --watch and one-shot work; timeout/poll values reject nonfinite/nonpositive values
  as appropriate. Preserve current timeout exit2 and success0, use nonzero error.
  Don't busy-loop or depend on WSL/provider. Reads still only canonical task logs;
  writes only selected cursor/temp/lock files. No automatic dispatch or task edits.
- Behavioral standard-library tests use temporary directories and controlled
  clock/sleep or subprocesses: offline messages survive restart, one-shot and watch,
  recipient/all filtering, legacy no-cursor behavior, malformed/wrong-identity state,
  interrupted output/save, exclusive lock release/contention. No mirror-only tests.
- Document Windows/WSL examples with distinct cursor paths per consumer, first-run
  replay, path/recipient binding, failure recovery, duplicate-delivery limitations,
  and that listeners do not wake idle agents. No edits to canonical protocol.

Budget exact claude-opus-5-5 high, 6 minutes / requested USD5, no retry/substitution.
Commit only owned source paths. Return <=300 words with candidate SHA, changed files,
tests NOT RUN, remaining risks, then a protocol HANDBACK. Stop on bound, honest partial
is acceptable. Do not edit canonical task logs from headless worker.

## Log

### 2026-10-07T17:06:17.0080845-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

HEADLESS opus-t0071-listener-20261007 only, compact packet above. Source-only isolated
task; T0070 interactive assignment remains reserved. Root will bind actual returned
commit, run focused checks with all three simulator locks, request Sonnet source
review and Sol evidence review. No Unity or live work.
