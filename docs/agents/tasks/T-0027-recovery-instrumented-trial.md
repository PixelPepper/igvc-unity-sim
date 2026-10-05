---
id: T-0027
title: Exercise reviewed recovery evidence in one unchanged-policy live trial
status: in-progress
priority: P1
owner: gpt-6-astra
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0027-recovery-instrumented
base: f1a6ae4ceb0a146b53b5ea7d9e83da472ceb391f
candidate: f1a6ae4ceb0a146b53b5ea7d9e83da472ceb391f
claim: none
lease: requested
updated: 2026-10-05
---

# T-0027: One instrumented live trial

## Packet

- Frozen runtime checkout C:/Users/brand/.codex/worktrees/igvc-t0008-mouth-handoff/IGVC SIM
  at f1a6ae4ceb0a146b53b5ea7d9e83da472ceb391f. Integrator owns it and the reused t0024-control ROS overlay.
  No edits during live. Same player/profile/course/mission as T0024/T0025.
- Wait for the one combined integration check to pass and explicit dispatch.
  Managed hidden rendered Unity + native WSL ROS 2 Jazzy/Nav2, exclusive port
  10000/domain42 lease. No RViz, Docker, Unity build, replay or heavy local tests
  while live. No interrupting other sessions.
- One attempt, no retry: seed2027, requested speed0.6, planning budget0.5,
  clearance weight3, checked-path RPP, six broad GPS goals, learned scorers off,
  replacement revalidation OFF. Mission600s/build10min/start3min/audit3min bounds.
- This is instrumentation, not a recovery policy fix. Preserve any failure.
  If recovery refusal recurs, inspect recovery_failures, submitted/worker/capture
  digests, bounded stage/terminal records and the exact captured inputs. Check
  deferred writer timing and cleanup phase/health interval; no live-wire or
  successful capture claim if that branch never executes.
- If capture is unavailable or mismatched, say so. No retrospective attribution
  of T0020/T0025 from this different run. A timed replay need not return identically.
- Full independent audit, health coverage, source hashes, charged backups and
  cleanup verification remain required. Runtime may read observations plus
  sanitized autonomy.json only; course geometry belongs solely to rendering/audit.
- Append ledger with all outcomes. One Sonnet interpretation and one Sol raw
  evidence review <=10min/$5 each. Stop after this one attempt; no publishing,
  promotion, threshold relaxation or implicit second trial.
- Artifacts: artifacts/iterations/2026-10-05/recovery-instrumented-1.
- Knowledge: sensor-led-navigation; trial-audit-promotion; processing-health.

## Handback

Pending.

## Log

### 2026-10-05T05:30:52.955151-07:00 · gpt-6-astra → all · NOTE
Prepared only. Combined integration checks are still running; no live launch yet.

### 2026-10-05T05:33:30.385245-07:00 · gpt-6-astra → all · DISPATCH
Integrated source at f1a6ae4ceb0a146b53b5ea7d9e83da472ceb391f.
Validation covers 630 distinct tests: 541 tools +85 perception +4 GPS.
The initial tools run passed 540 and failed only generated-board freshness after
the coordinator added T0027. Regenerated board; its5-test suite passed. No source
test failed. Two manually assembled remaining-suite commands lost ROS Python
imports; preserved remaining-checks.log/-r2.log. A saved helper based on check_core
preserved the environment and passed board5/perception85/GPS4.
Knowledge check then caught a malformed new log heading; corrected it and the
strict check passed8concepts/0errors/0warnings. These are staged validation results,
not one uninterrupted clean check_core invocation. Original failures are retained.
No live validation yet. All motion/audit parameters are unchanged.

Grant the single trial now after this final board refresh/check. No other tests,
replay or source edits in its checkout while live. Opus is idle after handback.
