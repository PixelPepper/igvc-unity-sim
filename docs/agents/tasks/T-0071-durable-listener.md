---
id: T-0071
title: Preserve agent message delivery across listener restarts
status: integrated
priority: P2
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0071-durable-listener-opus
base: 1b56bed
candidate: 18665c6c14dca44eaaf5a5fe11705a6514249ff2
claim: tested
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

### 2026-10-07T17:09:15.5671888-07:00 · gpt-6-astra → all · HANDBACK

Received actual headless Opus handback, artifacts/agents/T-0071/implementation/handback.md (SHA256 c993d1cb5bb28dd7d596c9d0ab7e8a5f1b387c7b6b707b1c6e187df85b482fd5), raw result.json and status.json retained. Exact model claude-opus-5-5 verified; 134.92 seconds, reported USD0.5249918. Candidate18665c6c14dca44eaaf5a5fe11705a6514249ff2, clean, three owned files only. Worker reports no tests/imports/syntax checks run; cursor implementation and behavioral tests are source only. Implementation assignment ended. Sonnet whole-range review dispatched separately. Root tests/integration deferred behind the interactive seed2370 demo reservation and actual busy simulator lock. No live/runtime benefit claimed.

### 2026-10-07T17:10:03.5880694-07:00 · gpt-6-astra → all · REVIEW

Exact Sonnet source review PASS for18665c6c14dca44eaaf5a5fe11705a6514249ff2, whole1b56bed..candidate. artifacts/agents/T-0071/review/review.md SHA256 3a83852e7ddec7202c7cbca1095395cbb92143cad6b3ddc78cf178e39dca107b; raw result.json/status.json retained. Actual model claude-sonnet-5-5,56.42seconds,USD0.173321. No blocking source findings. Nonblocking test limitations: watch-output duplicate check and explicit flush-failure case absent; Windows/Linux locking unexecuted. Both reviews' prose exceeded compact requested length and are preserved as artifacts rather than pasted. Source-only acceptance is NOT task acceptance. Root validation and Sol evidence review remain pending the demo release; no primary integration. Total recorded Claude task usage USD0.6983128; this is reported usage, not billing guarantee.

### 2026-10-07T17:16:37.0049240-07:00 · gpt-6-astra → all · DECISION

Accept candidate18665c6c14dca44eaaf5a5fe11705a6514249ff2 for integration: Sonnet source PASS and Sol evidence acceptance in artifacts/agents/T-0071/sol-evidence-review.md; 18 distinct tests PASS on each of Windows and WSL, no skips, hashes and leases verified. Demo release17:11:53 precedes validation. No DrvFs cursor-file locking guarantee, automatic wake/ACK or live-navigation claim. Known limitations retained: at-least-once duplicates, identical-heading IDs, partial writes outside atomic log protocol, absent flush-failure injection and pre-created Windows cursor parent directory. Root will integrate only three owned paths under all locks and check primary behavior/external preimages. No old validation or provider calls repeated.

### 2026-10-07T17:17:54.6048874-07:00 · gpt-6-astra → all · DECISION

COMPLETE integrated8dc6d378b14162270d7f2f7e3ddb4d42f70b3726. Three source hashes match accepted candidate18665c6;18 primary Windows checks PASS, no skips, final Sol binding accepted in sol-integration-review.md. All14 protected preimages unchanged during validation; later T0070 coordination NOTE is outside that window. Artifacts integration/result.json,tests.log,lease-held/released.json preserve full result; all locks released17:16:41. Root initialized its own durable cursor artifacts/agents/listeners/astra-windows.json; initial historical delivery saved locally, not an ACK or authorization to repeat ended work. No primary navigation/Unity source changed and no live benefit claimed. Windows/WSL candidate checks and primary check are complete; do not repeat absent new cause. Sonnet/Opus recorded totalUSD0.6983128, native Sol usage unavailable. All T0071 assignments ended.
