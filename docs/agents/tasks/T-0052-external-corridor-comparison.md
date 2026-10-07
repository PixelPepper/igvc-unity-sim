---
id: T-0052
title: Preserve the externally launched corridor comparison and its failed dispatch
status: in-progress
priority: P1
owner: gpt-6-astra
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/transport-probe
base: 74967bfa0a579f74be2d70c94c7dfc56274d778a
candidate: none
claim: none
lease: none
updated: 2026-10-06
---

# Packet

Root discovered another externally launched batch immediately after the T0049
integration window. Preserve its live ownership and do not duplicate, stop,
rebuild Unity or run heavy checks/probes. Header lease none means root does not
own the externally held instance2 lock. No new root live grant is implied.

Plan artifacts/sandbox/batch/ab-corridor-v2/plan.json has40 trials across
seeds2371–2390, fixed route_weight8, corridor_weight0/8 pairs. Plan SHA256:
13d85d10c7afe1c7e286f0989df384fbf8a10b66558b9b34b0d3ac005731b12a.
The name v2 alone does not establish the model's label mode or training source.
No model/relabel/training promotion has been accepted by root. Verify actual
loaded model hashes, training/admission evidence and provenance before claims.

Instance1's launcher failed opening live-instance-1.lock while root legitimately
held all three locks for combined validation. Preserve launcher.log as a failed
dispatch, not a navigation trial. Instance2 player PID41980 began06:57:31.437 PDT,
port10002/domain62, after root released locks at06:57:18.502. Thus no known root
test/live overlap. Parent WSL804 runs parallel_batch.py with instances2.

Only instance2 is observed live. Do not pretend an incomplete assignment forms
20 paired comparisons. Preserve missing-arm data and failed launcher evidence;
do not fill the absent arm through an unregistered automatic retry. Archive logs
before reuse, record all attempts and independent audits, and retain provenance.
Route8 itself regressed in T0050, so this is a conditional corridor experiment
on that experimental route scorer, not a comparison with the baseline default.

T0051 attempted to reserve all three locks at06:58:27 but correctly refused the
busy instance2 lease. No Claude invocation or replay occurred; partial locks
released. It remains backlog until the live instance closes. Root integrated
offline teacher/dataset fixes at74967bf and all checks passed before this player.

## Log

### 2026-10-06T06:59:58-07:00 · gpt-6-astra → claude-opus-5-5 · NOTE

Please finish the owned session and provide its handback here, then leave all
leases free for the one bounded observed-recovery diagnostic T0051. Do not start
another batch before that diagnostic window. No provider retries, pushing,
publishing, safety relaxation, default change or model promotion is requested.
The overnight cutoff is10:00AM Pacific; do not start missions after09:40.

### 2026-10-06T07:42:47.9321155-07:00 · gpt-6-astra → claude-opus-5-5 · REVIEW

Root found an external restart, not a continuation of the original plan. The
original directory is now ab-corridor-v2-aborted: report rows[], exits1/0 and
no per-instance results; preserve this incomplete evidence. Current v2b has40
trials2371–2390, route0 by defaults, corridor0/8 (planSHA9bcb766cf9c975c0908b96a940b3ecf7dafb9a0e2d34a02b686eb8fea68da881).
Players6132/51876 started07:03:24/07:04:10. Root did not stop or relaunch anything.

Blocking promotion issue: manifest confirms candidateSHA
bbfc93f7085266a22854faa44d524aa4268469cf43821f557c59a3b5e09b4308,
label_version='corridor_cost path-v2', source artifacts/learning/corridor-v2/.
LEARNING_PLAN explicitly names rejected95b0baf teacher. T0044/T0045 rejected its
endpoint/cap/penalty/label semantics; accepted path-v3 is now integrated74967bf.
These v2 runs cannot validate the corrected teacher or justify root accepting
this model. Keep both vetoes, preserve experimental evidence and avoid promotion.
Manifest still carries round0 gate_report/promoted timestamp for replaced model;
that is not bound evidence for this new candidate. Request corrected provenance
and fresh-version workflow after the live session, not mutation mid-run.

Policy identity also changed mid-batch: firstruns140335-aa1d1402/140420-4405e113
record sensor_course c3c93114231b0b5748540b366262fd11e27510fc4a42a37a968504684ccb0a66;
later142855-cccd83af/143524-6314927a record ad1bfb9cd3fcbedf569164c6d37701b915da9b6fccc06d056792734b6f7d578b,
new latency modulec3b7fec3dec5b56b7b4b6a85b85ae9bace090101e06f9fef4f8537371db7dcb3.
Later samples show enabled=false,predictions0; that does not establish identical
code behavior. Stratify by actual source identity; do not claim a frozen-policy
comparison. Root's earlier combined test pass covers74967bf, not these dirty edits.

ab-latency-1 has a40trial2391–2410 plan, no observed player yet. Root requests
no next launch before T0053 independent review and T0051 diagnostic window.
No further code/model/manifest edits during live comparisons. Never pool the
changed-player/changed-policy batches or infer power causation from emptyquery.
Preserve actual admission thresholds, body/unknown/freshness gates and cutoff.

### 2026-10-06T16:35:45-07:00 · gpt-6-astra → all · NOTE

Cutoff handling: this heartbeat arrived after the October6 10:00AM Pacific
limit. Automation igvc-overnight-improvement is now PAUSED (app confirmed).
No new trial, provider task, source integration or heavy validation started.
At16:35–16:36, external player51876 still exists for ab-corridor-v2b instance2;
its process-held lock is unavailable. Primary and instance1 locks were available
at a brief probe and immediately released. No sessions were stopped or changed.
Per-instance batch-results files exist, but no merged batch-report.json was
present. No final rate or completed-batch claim is accepted without review.
T0053 remains changes-requested with no new canonical handback; T0051 remains
queued, never dispatched past its busy-lease refusal. Preserve external work.
Further development requires resumed user authorization beyond this cutoff.

### 2026-10-06T16:50:30-07:00 · gpt-6-astra → all · NOTE

User resumed interactive coordination at16:46; heartbeat stays paused. Snapshot
artifacts/agents/T-0052/snapshot-20261006T1652/ preserves six batch files with
hashes and read-stability flags. Instance1 reports finished with13 rows:
11 completed,1 mission error,1 offline pre-start failure; planned20 remains
incomplete. Instance2 is still running; observed17 rows include a missing-grid
startup failure and its repeated attempt at seed2385. These are launcher states,
NOT independently checked full-audit successes. No final rate accepted and no
retry issued by root. Player51876 and port10002 remain active. Source/model
caveats above still apply. External primary files remain untouched.

### 2026-10-06T17:24:51-07:00 · gpt-6-astra → all · DECISION

External instance2 finished2026-10-07T00:18:55Z; instance1 already ended incomplete. Root then acquired all three locks, confirmed no Unity/ports and archived both instance results/launcher logs, plan/driver and Unity logs under closed-20261006T1720/ with hash manifest. No merged final batch report was present. Final per-run audit accounting remains pending. Preserve aborted predecessor, incomplete assignment, all attempts and source-version strata. Rejected path-v2 model and mid-batch source changes still block promotion or pooled controlled claims. Root did not stop external sessions or start ab-latency-1.

### 2026-10-06T17:29:32-07:00 · gpt-6-astra → gpt-6.1-sol · DISPATCH

Review closed archive existing-evidence-summary.json without recomputing audits. Root descriptive counts: instance1 13 attempts/20 planned,11 completed and11 existing audittrue, one missionerror and one offline prestart; instance2 22 attempts/20 distinct seeds,15 six-destination completions but13 existing audittrue,6 error and1 offline. Each successful file is preserved by hash. Three source maps occur across recorded runs; no controlled pooling. Output closed-20261006T1720/sol-final-evidence-review.md. No new trials to fill missing arm. No active simulator ownership remains from this batch. Keep task in-progress until final evidence review/closure, rather than assigning fictitious unified candidateSHA.

### 2026-10-06T17:31:36-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0052/closed-20261006T1720/sol-final-evidence-review.md

# T0052 closed existing-evidence review

Recommend closure as an incomplete, changed-source experiment with preserved existing evidence, not model acceptance or promotion. Do not launch trials to fill missing assignments.

Verified archived plan:40 trials,20 seeds2371–2390, one corridor0/8 pair per seed. All eight archived file hashes match the stable manifest. Recounted summary rows:

| Instance | Actual attempts | Planned slots | 6/6 | Existing audit true |
|---|---:|---:|---:|---:|
| 1 | 13 | 20 | 11 | 11/13 attempts;11/20 planned |
| 2 | 22 | 20 | 15 | 13/22 attempts;13/20 planned |

Instance1 lacks rows for2384–2390;2383 has a pre-start offline row. Instance2 retains an offline2382 row and both missing-grid startup retries2375/2385. Combined:35 rows covering33 planned slots,26 completions,24 existing audit-true records. Missing audits are unknown, not passes or independently demonstrated failures.

All33 existing audit file hashes/statuses match the summary; all24 passing files identify the corresponding summarized run SHA. Three raw run spotchecks also match. Completed scorer2387/2389 fail sampled processing-health verification (5/4 failed samples); they must not count as full-audit passes. Other failures include three backup refusals and two freshness latches, with fresh clock at2382 but stale clock at2383; no causal conclusion follows.

All34 available provenance settings match corridor assignment, route0. Source strata are4 original rows,22 latency-module revision1 rows,7 revision2 rows,2 missing identities. Disabled prediction does not establish identical policy. Three scorer spotchecks identify rejected path-v2 model SHA bbfc93f7…; this cannot validate corrected path-v3 labels.

The summarizer hardcodes20 planned slots and accepts any existing audit passed flag; independent plan/count checks resolve the denominator, not auditor trust. Auditor implementation/version and launch-bound player identity remain unbound; run/audit records live outside the batch archive. Preserve aborted predecessor evidence separately. No controlled pooling, paired efficacy, significance, calibrated autonomy or promotion claim.

Summary SHA256: `d475f51df5bbbf046b380061ceb2f18c7c155d3758eb192fa04939c255265c3b`.


### 2026-10-06T17:31:36-07:00 · gpt-6-astra → all · DECISION

Data collection is closed, no batch owns a simulator lease. Sol verified descriptive existing-evidence totals, including failed health audits despite6/6 completion. Preserve all35 attempts, seven absent planned assignments and three source strata. No makeup trials, pooling or model promotion. Task remains in-progress only for bounded final record/provenance review; this does NOT authorize an active trial. Do not invent a single experiment candidateSHA for changed sources. No current worker is assigned to this task. Next root may obtain remaining Sonnet record review and close with an explicitly bound ledger commit.
