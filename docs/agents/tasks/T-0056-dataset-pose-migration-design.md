---
id: T-0056
title: Design explicit pose provenance for dataset readers without changing replay inputs
status: ready
priority: P2
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: none
base: 646845e25af6c0b58cd20131addfdbfacdcc6562
candidate: none
claim: none
lease: none
updated: 2026-10-06
---

# Packet

INTERACTIVE CLAUDE CODE SESSION ONLY, the user-started session that posted the
17:36 T0048 inventory. Named assignment alias interactive-opus-dataset-20261006.
This is not for a headless worker. Reply ACK here with that alias and the exact
selected model before acting. Root reserves one of two worker slots for this
assignment until handback/revocation; a posted message alone is not an ACK.

Read README introduction and T0054's latest trace and review. Read-only design:
trace tools/learning/build_dataset.py snapshot, corridor and route output paths,
and their direct training/dataset readers plus relevant tests (locate with focused
search). Candidate646845e is frozen in igvc-t0053-reconcile-1703; primary
build_dataset.py bytes match that candidate as last checked17:36. Record observed
hashes if available; stop on changed ownership/source uncertainty, don't restore.

Deliver a minimal schema/consumer migration proposal preserving exact numeric
planner inputs while making measured/predicted/unknown-legacy/malformed provenance
explicit. Determine all affected consumers and compatibility gates; do not simply
change one writer to version3 while readers discard it. Separate exact navigation
replay (recorded planning pose) from recovery controls (T0055 owns that fix).
Explain how existing legacy data remains inspectable and usable only with an
explicit recorded opt-in or verifiable binding; absent metadata must never silently
mean measured. Specify a matrix of behavior tests, no execution. Exact output rows
cannot remain byte-identical when adding metadata: preserve numerical fields and
document schema changes. Do not propose automatic historical rewrites or arbitrary
trusted source hashes. No estimator selection based on the confounded batch.

Owned write surface: append ACK/HANDBACK to THIS primary task log only, <=300word
handback plus a concise optional table. Everything else read-only. No code edits,
commits, builds, tests/imports, historical replay, live sessions, provider calls or
delegation. No course/WORLD/teacher geometry, credentials, CAD, complete logs or
unrelated files. Do not duplicate T0055 implementation or act on its headless
dispatches. Stop after one design pass or a blocker. Suggested bound6minutes/USD5;
for an interactive session these are task targets, not enforced billing caps.
Report attributable usage if available, otherwise unknown; no invented accounting.
Exact Claude Opus5.5 only; report model mismatch without substitution or retry.
Sonnet and Sol reviews follow actual handback. No integration or live A/B granted.

## Log


### 2026-10-06T17:42:56.8603662-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

INTERACTIVE USER-STARTED SESSION ONLY, alias interactive-opus-dataset-20261006. Please ACK this exact assignment/model before beginning the bounded read-only packet above. Root reserves one worker slot; no implementation or live lease. Headless T0055 owns different files and remains separate. Do not start a provider subprocess or delegate. Return here when complete; posting is not presumed delivery.

### 2026-10-06T18:25:10.191571-07:00 · gpt-6-astra → claude-opus-5-5 · NOTE

INTERACTIVE alias interactive-opus-dataset-20261006: the existing17:42 T0056 read-only dataset design assignment remains yours; no duplicate worker or reassignment. No ACK has appeared yet. This refresh is for a listener that began after the original message: please ACK the exact session/model and read the existing packet when received, then return your bounded design here. T0057 is integrated; T0059 headless handles only recovery replay reporting and is in final evidence review. Do not edit its files or start a live latency A/B. Posting this note is not proof of delivery or activity.
