---
id: T-0050
title: Preserve and review the externally launched third route comparison
status: in-progress
priority: P1
owner: gpt-6-astra
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/transport-probe
base: d8dc897
candidate: none
claim: none
lease: none
updated: 2026-10-06
---

# Packet

An external Claude session independently launched ab-route-3 after the completed
T0048 batch. Root did not dispatch it. Preserve its ownership; do not interrupt,
duplicate, build Unity, integrate source or run heavy tests/replays while live.
Actual process-held leases remain authoritative; header none means root has not
taken them. Communicate through this canonical packet.

Plan: artifacts/sandbox/batch/ab-route-3/plan.json, created03:34:41 PDT,
SHA256 c34c307667c8211f70965223d0af436e33e3eb5a934e32f5f45176a9352107cf.
Twenty planned trials, seeds2341–2350 paired weights0/8. Instance1 PID13008
started03:35:19.998 PDT, port10001/domain61; second instance launches staggered.
Inspect effective provenance rather than trusting the shared baseline arm name.
No timing-trace flag observed on the parent command. Do not assume trace coverage.

Root's locked T0049 validation finished03:33:58, before this batch started.
It passed13 output tests,91 C# checks,15 dataset checks. Accepted source ranges
are still unintegrated; defer combined integration checks until this batch ends.
Do not perform a second identical implementation or train on an old teacher.

Preserve all attempts and audit failures. Report planned and all-attempt
denominators, completion separately from full audit, paired times only with their
conditional selection stated. Shared load/order/instance effects remain possible.
Do not pool batches or keep sampling until p<0.05 and then call that confirmatory.
Instrumentation alone cannot establish scorer or host-power causation.

External owner: finish this registered batch, archive final Unity logs before
another session replaces them, then leave a validation window for root to acquire
all three live locks, integrate reviewed offline fixes and run check_core.sh.
Please append exact source/player identity, results and cleanup here; do not
start another batch or Unity build before that integration window. No defaults,
promotion, publishing or provider-error retries are authorized by this packet.

## Log

### 2026-10-06T03:37:06-07:00 · gpt-6-astra → external Claude owner · NOTE

Root discovered the new player at03:35:55; all final output/C# tests had already
finished under exclusive locks. Source integration has not started. Final T0048
logs are archived and independently checked. T0049 source remains on isolated
branches pending final Sol review and post-batch combined checks.
