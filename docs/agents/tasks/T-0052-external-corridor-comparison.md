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
