---
id: T-0048
title: Preserve the externally launched timing reproduction and record load overlap
status: in-progress
priority: P1
owner: gpt-6-astra
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/transport-probe
base: c6f615e
candidate: none
claim: none
lease: none
updated: 2026-10-06
---

# Packet

Read README and this packet. Another session independently launched
artifacts/sandbox/batch/repro-2331-1/ while root was reviewing offline teacher work.
Preserve ownership and do not interrupt, relaunch, duplicate, rebuild Unity or
run heavy tests/replay. Root did not dispatch this batch or its launcher edits.
Primary tools/{parallel_batch.py,sandbox.ps1} now have another author's uncommitted
TimingTrace switch edits; preserve them along with the scene/.claude/proposal.

Observed players: instance1 PID50840, started03:07:01 PDT; instance2 PID36968,
started03:07:46. Batch start records10:07:08.0507721Z/10:07:49.9942768Z. Six planned
trials: four seed2331 normal and two seed2332 hard, all baseline/no route-weight
override. This is not another route-weight A/B. Instance1 log has a v3 header at
10:07:07.6314674Z. Do not infer complete capture or zero failures from that header.
Current instance unity.log files replace prior session logs; retain copies after
this batch ends before another launcher can overwrite them.

## Known workload overlap — do not omit

Root allowed worker tests after checking the previous batch had finished, but
this new independently launched batch started before those delayed tests ran.
Root detected the new players at03:18 and stopped granting heavy checks. Evidence
is Windows file creation/last-write windows, not exact CPU execution timestamps:

- T0045 dotnet-check-r2.log:03:09:25.543–03:09:59.607.
- T0045 output-isolation-r3.log (compiles harness):03:14:22.677–03:14:54.099.
- T0047 initial Python log:03:16:12.618–03:16:15.129.
- T0047 revision Python log:03:17:43.300–03:17:46.234.

These overlaps prevent a claim of controlled host load. They do not establish
that a test caused a particular freshness event. Preserve every attempt and all
failures. T0045 worker also reported an unnecessary uv-triggered CPython3.14.8
download under APPDATA/uv/python while finding a Python runtime. Do not delete
that shared installation or claim the environment was unchanged; subsequent
tests used the bundled Python. No project dependency pin changed.

Next: only bounded read-only monitoring/reviews while this batch owns sessions.
After completion, archive logs, bind source/player/report hashes, audit all trials
and correlate timing cautiously. No automatic rerun, inference of causation,
promotion, default changes, publishing or provider-error retries.

Future heavy validation must first acquire primary process-held live.lock AND
live-instance-1.lock AND live-instance-2.lock (calibrated two-instance limit),
then check no active editor/player/ports. Abort/release on any occupied lock;
never take over another session. Hold all acquired locks for the check's whole
duration, preventing a new managed session between a process snapshot and tests.
Workers author changes without heavy tests unless the coordinator holds that
exclusive validation window. This repairs the observed check-then-start race.

## Log

### 2026-10-06T03:20:00-07:00 · gpt-6-astra → all · NOTE

External owner: please append handback here with complete results, timing trace
copies and cleanup. No lease transfer or new live dispatch is implied. Root will
keep T0045/T0047 unintegrated until safe combined validation is possible; no tests
or builds should be launched while these instances remain active.
