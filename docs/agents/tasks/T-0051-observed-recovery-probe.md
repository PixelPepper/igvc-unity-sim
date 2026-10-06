---
id: T-0051
title: Reconstruct rejected forward recovery proposals from observed inputs
status: backlog
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/transport-probe
base: 7cad33b
candidate: none
claim: none
lease: none
updated: 2026-10-06
---

# Packet

Prepared, NOT DISPATCHED. Read README and this packet. Run only after T0050 ends,
root archives live evidence and completes the accepted teacher integration/checks.
Root must acquire all three process-held live locks and hold them for the entire
diagnostic, then verify no player/editor/ports before dispatching heavy work.
This is an offline diagnosis; no runtime source edits, model training or live run.

Read T0046's accepted diagnosis and relevant recovery source at7cad33b. Inputs:
artifacts/sandbox-instance-1/runs/20261006T091734-d7a917a2/run.json and
decisions/recovery-00049.json.gz in that same run. Only saved observed costmap,
robot pose, captured planner settings and selected broad guidance are allowed.
Never read course.json, WORLD, teacher/trap labels, oracle paths or new courses.
Do not use replay_recovery.py blindly: its existing grading can load teacher data.

Before execution, bind the captured arguments with recovery_evidence's digest
round trip and verify planner source identities against provenance. If source
differs, root prepares an isolated frozen-source checkout first; do not silently
run current changed logic. Never change a shared checkout or load unknown code.

Perform ONE bounded diagnostic invocation of the full five-distance straight
backup search using the captured nominal5s/50000 expansion settings. A temporary
in-memory wrapper may record each forward call's actual settings, complete
returned proposal (endpoint/path/local goal/diagnostics), and call duration.
Accumulate records in memory and write after search to avoid logging inside the
timed loop. Preserve every safety, progress, unknown-space and budget setting.
Verify the original input digest before wrapping; record that instrumentation
changes callable identity and timing. Do not call this a bit-exact replay.

Compare the1.8m proposal and other candidates with recorded allowances/progress.
Return termination information only if the planner actually reports it; do not
infer timeout from elapsed time alone. If absent, identify the minimal future
diagnostic change needed, without implementing runtime instrumentation here.
Do not select only1.8m and give it the full5s: that changes allocation. Do not
repeat, increase budgets or sweep settings until a proposal passes. One Python
process, hard parent timeout20s; stop and retain partial/error evidence if it fails.

Owned output only: ignored artifacts/agents/T-0051/ (small script, bounded result,
source/input hashes and <=300word handback). No source/coordination edits, commits,
dependencies, providers, recursive delegation, credentials, network or user asks.
Root dispatches exact Opus once with6minute/USD5 task bounds, no provider-error
retries. These are task bounds, not guarantees of provider billing. Root obtains
Sonnet interpretation review and Sol evidence review before accepting any claim.

Acceptance is a clearer diagnosis: finite search exhaustion versus proposal
selection versus actually observed geometric blockage. It is not a navigation
improvement or permission to weaken any gate. Implementation needs a later packet.

## Log

### 2026-10-06T06:58:27.2006828-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

Now dispatched: T0050 players/audits closed and T0049 full integration checks
passed at74967bf. Root wrapper must acquire all3locks and verify idle before CLI.
Root preflight matched all19 captured source_sha256 entries from run.json to
current tools files; artifact source-preflight.json. Recheck before executing.
Do not read reference-teacher output or any WORLD data. Only saved observation
capture and planner code. One instrumented diagnostic; no reruns/tuning. Root
owns unrelated external dirty files and leaves them untouched. Bound6min/USD5.

### 2026-10-06T07:00:52.4162753-07:00 · gpt-6-astra → all · NOTE

Dispatch wrapper stopped before Claude invocation: instance2 lease occupied by
new external ab-corridor-v2 session (T0052). No provider cost, no replay, no source
changes; partial locks released. Prepared dispatch scripts are not execution
proof. Return backlog until T0052 closes; do not bypass its lease or retry live.

### 2026-10-06T07:42:47.9321155-07:00 · gpt-6-astra → all · NOTE

Previous source-preflight.json is historical: external latency changes now make
current sensor_course differ from the capture. Before T0051 dispatch, prepare an
isolated frozen-source checkout matching all captured hashes; never revert the
external author's primary edits. Source mismatch must stop the probe before any
planner call. No test or replay was run during this heartbeat.
