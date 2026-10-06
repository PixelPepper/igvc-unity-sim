---
id: T-0043
title: Reconcile the already-running learned-route comparison and preserve its evidence
status: review
priority: P1
owner: gpt-6-astra
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/transport-probe
base: e65214b
candidate: 1097d2d
claim: none
lease: none
updated: 2026-10-06
---

# Packet

The user resumed overnight work with Claude, without routine questions. At
2026-10-06 01:57 PDT, the coordinator found an independently launched batch
`artifacts/sandbox/batch/ab-route-2/` already running on instances 1 and 2.
Parent WSL PID 10236 invokes tools/parallel_batch.py; wrapper PIDs 7748/40772
and player PIDs 36252/43136 were observed. These are observations, not new lease
grants or proof of the provider that launched them. Preserve their ownership.
Do not stop, restart, mutate plans, rebuild Unity, add a third trial, or run heavy
replays while this batch is active. Existing uncommitted scene/.claude/proposal
files are not ours to restore or commit.

First phase: GPT-6.1 Sol read-only audit of the static parent and per-instance
plans and dispatch/settings code. Inspect tools/parallel_batch.py,
tools/sandbox_batch.py (if present), tools/sandbox_supervisor.py, relevant
batch settings methods, and docs/LEARNING_PLAN.md only where needed. Determine
whether intended route weights 0/8 reach runtime, how trials are assigned to
instances and ordered, and what comparison/confounding limits must be reported.
Both arm labels say baseline; verify settings rather than inferring treatment
from labels. Do not read changing raw logs or inspect future course geometry.
At most four focused read commands / six minutes; no tests, source edits,
subagents, network, provider calls or live actions. Output at most 300 words to
artifacts/agents/T-0043/sol-plan-review.md (or return for root relay), with paths,
verified facts, inference limits and next concrete check. Stop after handback.

Second phase, after completion and explicit coordinator dispatch: bind effective
settings, model/source/player hashes, full audit and health for every attempt;
preserve startup retries, failed and latched outcomes. Do not present 6/6 alone
as audit success, exclude failures to improve the headline, or seek a p-value
threshold through repeated optional batches. T0042 capture cannot establish
causation by itself. No additional live grant in this packet.

## Log

### 2026-10-06T02:00:00-07:00 · gpt-6-astra → claude-opus-5-5 · NOTE

I resumed coordination at the user's request and found ab-route-2 in progress.
Please append your batch handback here when finished, including launch source,
player/model identities, treatment settings, complete outcomes and cleanup.
I will avoid competing builds, trials and heavy analysis while it runs. This
message does not transfer your active session or dispatch another batch.

### 2026-10-06T02:00:00-07:00 · gpt-6-astra → gpt-6.1-sol · DISPATCH

Read-only first-phase plan/settings review above. Root checks ownership and
prepares the next bounded task independently. Overnight follow-ups stop at
10:00 AM October 6 America/Los_Angeles; no push or publishing.

### 2026-10-06T02:04:53.7264814-07:00 · gpt-6-astra → all · NOTE

Sol's static four-command review verified the saved 20-trial paired plan (seeds2331–2340), balanced conditions across instances (five weight0 and five weight8 each), and Unity command emission. Both labels baseline are intentional Reference Lab load labels, not treatment identifiers. Deterministic ascending seed order, complementary instance assignment, stagger and shared load remain comparison limits. A narrow follow-up verified supervisor handoff and scorer construction; root closed the remaining mapping: sandbox_profile.py mission_argv includes scorer path/weight only when weight>0; sensor_course.py passes scorer_options at planner.submit. This is source verification, not a completed outcome claim.

Root snapshot artifacts/agents/T-0043/initial-live-observation.json records two CLOSED initial result rows and continuing missions at09:00:57UTC. Player assembly on disk equals T0042's809c280c... build, but this alone does not prove tracing was enabled. Initial completed rows report route weights0/8; both run.progress.json files preserve perception/clock freshness latches (1/6 and0/6 respectively). Sol is granted a bounded read of these two closed reports/provenance only, not heavy audits or active raw logs, to examine timing and model binding. No safety gates changed and no failed rows excluded.

### 2026-10-06T02:06:35.2159362-07:00 · gpt-6-astra → all · REVIEW

relayed-from: artifacts/agents/T-0043/sol-initial-pair.md

Sol verified both closed initial attempts latched freshness, effective route weights0/8 and loaded model d9b3935081e65be9acfe806fd0521cbfcf3682a104d8d72df60f282bb0afc9c6 in the weight8 arm. Course/mission and sensor_course source hashes match. Health intervals end0.106331s apart on shared WSL monotonic time, but endpoints follow cleanup and first recorded health failures occurred at different times. Root's coarse start-plus-duration arithmetic is not an exact latch timestamp; do not use it as one. Mean-frame disturbance flags cannot rule out rare stalls. A shared interruption remains a hypothesis only. The batch continues unchanged; preserve these failures in all outcome summaries.

### 2026-10-06T02:06:35.2159362-07:00 · gpt-6-astra → all · NOTE

User-authorized overnight follow-ups are active hourly through October6 10:00AM America/Los_Angeles, resuming the existing automation rather than duplicating it. Next wake must inspect current batch/agent state first, preserve external ownership and avoid heavy overlap. Finish the complete batch review before deciding whether additional controlled capture is justified. No new simulation is authorized merely because the heartbeat fires. Do not begin a new live mission in the final20minutes or a provider task whose bound exceeds the remaining time. At cutoff pause the heartbeat and report verified results; do not stop sessions owned by another agent without coordinating. No publishing or pushing, no provider-error retries.

### 2026-10-06T02:57:38.9883297-07:00 · gpt-6-astra → all · NOTE

Root extracted pre-cleanup evidence to artifacts/agents/T-0043/initial-pair-completion-phases.json; Sol independently verified against both closed run.json files and mission_completion.py. Inferred last odometry receipt times 189.445073789/189.459392880 (14.319 ms apart), cleanup starts 190.366072262/190.238445497 with ages already 0.921/0.779 s. Mission loops continued while receipt timestamps stayed unchanged. This supports stalled receipt updates before cleanup; callbacks are not wire arrivals, and this does not identify Unity/transport/ROS/host cause or scorer causation. Root generic igvc_transport_timing search found no records in finished instance1 log; v3 capture coverage cannot be assumed. Instance1 has finished ten planned trials; instance2 remains active after retaining an infrastructure retry. No new trial granted.


### 2026-10-06T03:07:04.6853386-07:00 · gpt-6-astra → all · HANDBACK

Merged report complete: both wrappers exit0, 21 attempts/20 planned trials, 17 reached6/6,16 full audits. Root verified both players absent and TCP10000-10002 free; no session was interrupted. Weight0=7/10 audits (8/10 completed); weight8=9/10 planned or9/11 attempts including failed startup retry. All failure reasons retained in docs/evidence/navigation-2026-10-06.md. Sol independently verified all21 treatment settings/CLI weights, matching profiles, source/model spotchecks, and counts; launch-time player identity remains unbound. Report SHA256 0b64d29bfb480303b2fdefd577a446aa6a0c9b4e3c36b88b1badc173ad04b752. Relayed evidence: artifacts/agents/T-0043/sol-final-batch-review.md. Seven mutually audit-passing pairs: scorer slower on6; simulation time +6.56% aggregate (root), elapsed wall +6.67% (Sol). These are different clocks and conditional subsets. No default change, promotion, significance or causality claim. Freshness failures, unavailable backup on2335, and health-audit failure despite6/6 on2336 remain actionable. No new live batch granted.


Candidate identifies the documented analysis/source baseline, not a runtime code change.
