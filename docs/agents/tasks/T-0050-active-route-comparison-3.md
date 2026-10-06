---
id: T-0050
title: Preserve and review the externally launched third route comparison
status: review
priority: P1
owner: gpt-6-astra
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/transport-probe
base: d8dc897
candidate: d3f9f4a0ddfd55f19b82ba3bbb62e339df1e7e14
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
Sixty planned trials, seeds2341–2370 paired weights0/8. Instance1 PID13008
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

### 2026-10-06T03:37:06-07:00 · gpt-6-astra → claude-opus-5-5 · NOTE

Root discovered the new player at03:35:55; all final output/C# tests had already
finished under exclusive locks. Source integration has not started. Final T0048
logs are archived and independently checked. T0049 source remains on isolated
branches pending final Sol review and post-batch combined checks.

### 2026-10-06T03:39:36.4065892-07:00 · gpt-6-astra → claude-opus-5-5 · REVIEW

Correction: root initially inferred20trials from a truncated plan preview. Parsing
all entries confirms60trials/30seeds2341–2370; plan hash unchanged. Previous count
was a reporting error, not an edited plan. Preserve registered60-trial design.
Instance2 PID43468 started03:36:06.340 PDT. Current on-disk player assembly changed:
SHA42afe009a61b2ff9ac1963965398206b374960554d9b6bd0e83a18bed1d3b1a9,
mtime03:34:25.594. This observed disk identity is not launch-bound provenance.

Read external proposal FRESHNESS-machine-wide-bursts.md. Useful hypothesis;
several conclusions exceed its evidence. Simultaneous stale received streams do
not prove the whole simulator paused or exclude transport/scheduling defects.
A non-reproduction does not rule out layout interactions. WSL/Windows clock lag
has not been independently calibrated. Post-hoc selected windows and timestamps
cannot support the claimed one-in-several-thousand chance estimate. No firmware,
charger or battery-care causal diagnosis is established. Do not use these claims
as proof of a fix or relax watchdogs. Root is recording this as review feedback,
not rewriting another author's proposal or erasing its evidence.

Display-awake changes host behavior; it is an intervention, not observe-only.
The new player's build/revision and power-request activation/release must be
bound and reviewed. Current batch changes seeds/player/environment relative to
prior comparison; do not pool as one controlled experiment or attribute lack of
latches to this intervention. Same-batch route weights may still be compared
with instance/order/shared-host limits. No physical charger manipulation or OS
power-setting change requested; no questions for the sleeping user are needed.

### 2026-10-06T06:48:04.1772180-07:00 · gpt-6-astra → claude-opus-5-5 · NOTE

Both players have exited (instances finished06:35:46/06:41:56); each recorded31
attempts for30planned trials. Merged audit report is still being generated; no
success counts claimed yet. Final Unity logs archived at06:44:15 under ignored
artifacts/agents/T-0050/, manifest final-snapshot-20261006T064415.json.
Root holds ALL THREE process-held simulator locks since06:44:43, PID40812;
status artifacts/agents/T-0049/integration-lease.json. Please leave the window
free. Script waits for merged audit report before complete-range cherry-picks,
then output/C# and check_core.sh validation; maximum12minute report wait, release
in finally on success/failure. No source integration or heavy root tests yet.

### 2026-10-06T07:02:28.8994934-07:00 · gpt-6-astra → all · REVIEW

Batch closed; independent Sol review saved artifacts/agents/T-0050/sol-final-review.md.
Baseline28/30 fullaudits; scorer20/30 planned,20/32 strictattempts.19both pass,
9baselineonly,1scoreronly,1neither. Weight8 slower11/19 mutualpasspairs (mean+6.137s).
2359scorer6/6 failed orderedloop39/77gates;2354freshness had freshclock.033s.
No default/promotion, pooling or causal inference. All62 attempts and both failed
startup attempts retained. MergedSHA40f4446dd2a326707e8b236ab183dea1df51287bb3127aacc689f48ae9e4f58b.
Final logs and unreviewed external source snapshot archived; no launch-bound
player identity or v3traces. Root's integrated fixes at74967bf passed checks.
New external corridor experiment now owns instance2; seeT0052. T0051 remains
queued after its lease attempt correctly stopped before Claude/replay.
