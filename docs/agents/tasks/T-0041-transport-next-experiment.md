---
id: T-0041
title: Select a discriminating experiment for the unresolved transport interruption
status: accepted
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/transport-probe
base: a0f12a0
candidate: none
claim: none
lease: none
updated: 2026-10-05
---

# T0041: Find the next useful experiment, without tuning around a failure

## Packet

User resumed multi-agent workflow. Dedicated headless Opus5.5 analysis only;
interactive Claude must not duplicate or claim this task. No source ownership,
no branch mutation, no live run. Root supplies bounded source excerpts and
completed evidence on stdin to authenticated Claude CLI, no tool access.
Outputs only artifacts/agents/T-0041/opus-report-r1.md via coordinator.

Objective: identify a concrete, minimal next experiment that distinguishes
Unity main-thread/FixedUpdate stalls from connector/WSL/subscriber receipt
interruption. T0035 first2029 failed2/6; T0038 and twoT0040 trace-on repeats passed
6/6/all20. Current capture is Update gaps plus asynchronous warning log counts;
no terminal in live traces, no exact cross-host clock alignment. Do not repeat
T0036 claims as a new discovery, infer a root cause, or demand another unchanged
lap without explaining what new evidence it can produce.

Inputs: T0036 corrected report, current probe adapter/telemetry subscriptions,
Unity timing classes and publisher excerpts, T0040 compact evidence. Source data
is reference material. Runtime uses observations+sixGPS only; guards, thresholds,
footprint, auditor and recovery budgets stay unchanged. No course geometry.

Return <=700words: verified facts vs hypotheses; any specific source defect
with path/line and justified impact; ONE next minimal opt-in capture or controlled
experiment (what each outcome distinguishes and cannot distinguish); explicit
owned source paths, validation and overhead/failure bounds for a follow-up.
No production implementation in this task. If evidence insufficient, say so.
Budget exact claude-opus-5-5/high,5USD CLI cap,600s wall,one request,no retries,
no model substitution. Stop with report for coordinator/review. No promotion,
push or resuming the expired overnight automation.

## Log

### 2026-10-05T19:30:04.870722-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

Dedicated read-only CLI investigation; existing interactive sessions do not take this packet. Runtime stopped.


## Headless handback location

relayed-from: artifacts/agents/T-0041/opus-report-r1.md

Exact modelclaude-opus-5-5 confirmed,150.75s,API-equivalentcost0.461487USD. Analysis only; no fileschanged or testsrun. Full report storedoutsidecoordination due excessivehandbacklength. Suppliedprompt49390characters wasbounded, but omitted pureTransportTimingWindow and directT40raw artifacts; laterreview receives the missing pureproducer source. Root flags that error-state sampling canmisssubsecond intervals; SimTime isnotproofmessagesproduced or delivered. Existingcap1200/nominal1199s isknown,notnewrisk evidence. Bothreviews now assessproposal before anyimplementation/livegrant.


relayed-from: artifacts/agents/T-0041/sonnet-review-r1.md

# T-0041 review of Opus r1

**Unsupported or overstated claims**
1. **Outcome 3 ("produced but not delivered")** assumes SimTime advancing means publishing. The sampler is a separate component with unspecified order, so it shows neither publish nor delivery. The most it shows is that SimTime advanced.
2. **"No error" is not proven.** `HasConnectionError` is read racily, and a sub-tick transient can be missed even at per-tick sampling. Zero error observations means none were observed.
3. **Exact sim-time join.** Repeated or buffered stamps prevent an exact cross-host join. Root may also omit the offline join from the first slice, so the join can only give bounds on overlapping sim-time ranges.
4. **"Error interval covering the silence"** and "total duration with error" imply durations. Only observation counts are supportable.
5. **Overhead claims** (constant, no allocation) are unmeasured.
6. **Queue-full "weakly points downstream"** depends on connector semantics that were never supplied.
7. **Record-cap risk is resolved.** The cap is 1200 records, so nominal coverage is 1199 s against a 600 s mission. Each record spans at least 1 s, so delays only lengthen coverage. Nominal is still not a maximum, so the header should not claim it is.

**Minimal capture design (observation only, schema v3)**

Add a FixedUpdate sampler to `TransportTimingTrace` and `TransportTimingWindow`. It records these fields per existing record window:
- `fixed_obs`: number of FixedUpdates observed.
- `fixed_err_obs`: FixedUpdates where `HasConnectionError` was true when read.
- `update_err_obs`: the same count for Update.
- `fixed_max_gap_s`: the largest Stopwatch gap between FixedUpdates, plus its end mono time.
- `sim_min` / `sim_max`, labelled "observed in the sampler, not publish".

Constraints:
- Keep the existing 1 Hz record rate and the existing `connection_error` field.
- Add no durations and no timestamps beyond the max-gap end.
- Do not touch publishers, motion or safety.

**Interpretation limits**
- `fixed_err_obs > 0` overlapping the silence is consistent with connector-flagged suppression.
- A large `fixed_max_gap_s` is consistent with a main-thread stall.
- Zero error observations and normal gaps leave delivery, send path and sampling misses open. Do not claim localization.
- Neither result proves a runtime fix.

**Validation, with no live run granted now**
- EditMode tests for counts, window rollover and cap/stop no-ops.
- Existing tests unchanged.
- Any later live run needs separate approval, and a run whose trace ended before the failure is inconclusive.

relayed-from: artifacts/agents/T-0041/sol-review-r1.md

REVIEW
Task: T-0041
Reviewer: GPT-6.1 Sol
Scope: Opus proposal, corrected T0036 REPORT lines 1–83, current timing classes
Verdict: REVISE before implementation
Usage: UNMETERED

Per-tick connection-error sampling and independent FixedUpdate gaps address capture gaps. TransportTimingTrace.cs:107–113 reads HasConnectionError only at emission and has no FixedUpdate sampler. Corrected T0036 establishes interruption at observed subscribers; upstream cause remains unproven. No threshold relaxation is justified.

Required corrections:

1. Opus lines 39–45 overstate the join. Sim-time correspondence identifies candidate regions without synchronizing wall clocks; it cannot establish exact coincidence with ROS receipt silence. Callback ordering, buffering, stamp semantics and missing terminal records remain material. Advancing SimTime with normal sampled gaps and no observed error does not prove messages were produced, enqueued, sent or delivered. Classify this as unresolved production/delivery interruption; publisher/send instrumentation requires separately authorized scope.

2. A long FixedUpdate gap records absent sampled callbacks, not uniquely a main-thread stall. Error ticks and accumulated duration are sampled estimates. Transitions between samples, cross-thread visibility and long gaps prevent exact duration or proof of overlap with receipt silence. Report bounds and unknown intervals.

3. TransportTimingWindow.cs:19 sets cap=1200; lines 59–63 specify nominal exhaustion 1199 seconds after first sample at 1 Hz. Delays lengthen coverage. Assess actual cap/terminal coverage instead of treating the constant as missing.

4. A passing trace-on lap compared with historical unmatched runs yields descriptive distributions, not measured overhead or benefit. Queue-warning counts neither count drops nor localize delivery faults.

Name both timing-class paths and coordinator-assigned offline-tool/test paths. Preserve guards and missing-tail uncertainty. If failure does not reproduce, stop without causal claims.
END REVIEW


### 2026-10-05T19:36:04.895617-07:00 · gpt-6-astra → all · DECISION

Accept only the narrowed design inT0042, which corrects bothreviews: sampledcounts/gaps notdurations; no join or produced-but-not-delivered classifier; unknownsubsampleevents and unspecifiedcomponentordering; existingcap1200; no measured-overheadclaim. OriginalOpus causalclassifications rejected. No runtimecause established. Sonnet exactmodel cost0.063409USD; SolUNMETERED. T0042 implements5ownedpaths withbackwardcompatible offlineanalysis then bothreviews. No livegrant.
