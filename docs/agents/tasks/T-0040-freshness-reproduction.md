---
id: T-0040
title: Seek a bounded reproduction of intermittent freshness expiry
status: integrated
priority: P1
owner: gpt-6-astra
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0038-timed-2029-diagnosis
base: 20a18f3
candidate: 20a18f3e7df4da4fa6dce4e5c8e5d16323b4c5ef
claim: audit-passed
lease: released
updated: 2026-10-05
---

# T-0040: Reproduction evidence before runtime changes

## Packet

Read T0035 original failure, T0036 first-failure scope, T0037 timing semantics,
and T0038 reviewed non-reproduction. T0039 parser must finish its tests before
any live grant. No new runtime fix has been identified. Keep the first2029
failure and all diagnostic passes; none replaces held-out qualification.

Proposed bounded batch: at most TWO additional diagnostic2029 laps with the same
frozen20a18f3 checkout, cf8f4a64... player,19 policy hashes, profile and all inputs
as T0038; trace opt-in1, all watchdogs/auditors/budgets unchanged. Do not generate
or inspect2030. Six broad GPS targets only; no runtime course geometry.

Do not start from this packet alone: a separate explicit root LEASE-GRANT with
clean-source/player/input/preflight checks is required per attempt. At most one
hidden rendered Unity/native WSL Jazzy session. Use existing managed supervisor,
600s mission bound and standard startup/build/audit bounds, exclusive live.lock,
no other local heavy tests/builds/replay during mission. Reserve cleanup time
before10AM PDT cutoff; do not begin a mission after09:40. No visible Unity/RViz.
Stop the batch at the first reproduced freshness expiry or infrastructure error;
no automatic retries. Preserve failed outcome and first-failure health snapshot.

After verified cleanup, append every result to benchmark ledger and compare:
full audit/6 goals/health coverage and gaps, source and input bindings, raw Unity
trace windows and warning observations, bound first-failure subscriber snapshot.
Report missing terminal or unsynchronized timing as unknown. A sampled frame gap
is not a causal attribution; warnings count log observations, not message drops.
No timeout relaxation, automatic re-enable, new seed selection, speed increase,
policy tuning, package change, publishing or promotion.

Both reviewers inspect the whole completed batch once. If failure is not
reproduced, report that honestly and leave diagnosis unresolved; do not keep
running until a desired result appears. Choose a subsequent capture/repair only
from evidence. One source version; no effect-size claim without matched control.

## Log

Prepared follow-up only. No live grant, no session or job created.


### 2026-10-05T08:44:10.840441-07:00 · gpt-6-astra → all · LEASE-GRANT

Grant ONLY attempt1 job timed-2029-reproduction-1. T0039 integrated/tested, workers stopped. Runtimeclean20a18f3, actualplayercf8f4a64...426c3,19policyhashes and profile/course/mission/autonomy matchT0035/T0038. No player/port listener, exclusiveleasepreflightfree. Managedsupervisorholdslease throughshutdown; traceenv1 recorded/inherited explicitly, coordinatorenvrestored. Hidden renderedUnity/nativeWSLJazzy; noRViz.600smission; preserveanyfailure, stopbatchiffreshnessexpiry/infrastructureerror. No2030/promotion/push. Secondattemptrequiresfreshgrant.

### 2026-10-05T08:46:17.6329387-07:00 · gpt-6-astra → all · NOTE

Attempt1 reached mission. Actual generated seed/course/mission/autonomy hashes and profile/player match prepared identity. Schema2 header confirmed in runtime startup log (cap1200 interval1s). T0039 source unchanged runtime remains20a18f3. No local tests/builds/replay during mission.



### 2026-10-05T08:52:18.256312-07:00 · gpt-6-astra → all · LEASE-RELEASE

Attempt1 complete6/6 in368.395837434s,20/20audit,health3685/0/0 fullcoverage maxgap0.154945539. Mission/auditexit0, shutdown_verified; root independently no players/listener and exclusiveleaseavailable. Freshness failure not reproduced. Batch result still pending bothreviews. OriginalT0035 remains unchanged.


### 2026-10-05T08:52:53.606466-07:00 · gpt-6-astra → all · LEASE-GRANT

Grant final attempt2 job timed-2029-reproduction-2, no attempts after this batch. Attempt1 no health/infrastructure failure; ledger appended and offline reports completed while stopped. Recheckedruntimeclean20a18f3,cf8f4a64player and19source/inputhashes unchanged. Previous shutdown independently verified; no intervening runtime. Same traceenv1/profile/seed and600smission. No heavytests/replays/buildswhilelive. Preserveallresults; stopbatchonfailure. No2030/promotion/push.


### 2026-10-05T09:00:21.105756-07:00 · gpt-6-astra → all · LEASE-RELEASE

Attempt2 finished with mission/auditexit0, shutdown_verified. Root independently no players/listener and leaseavailable. Maximum2attempt batch is now finished; no more retries authorized byT0040. Full evidence and timing now reviewed offline, reviewers next. Both attempts remainedsame source/player/inputs. No freshness failure reproduced; no cause/fix/promotion claim.


relayed-from: artifacts/agents/T-0040/sonnet-review-r1.md

**Verdict: the claims are sound and appropriately conservative. Accept as diagnostic-only, with no promotion, no causal claim, and no further trials.** There are two gaps in the packet, listed below.

**What the evidence supports**
- Each run has all 20 audit checks true, with health at 3685/0/0 and 3498/0/0 and coverage complete.
- Profile, player (`cf8f…`), inputs, commit and `source19_equal_T0035` match across both runs.
- Both traces have `missing_final_record`, so the tail is unknown. Warning counts are labeled as log observations, and UTC is not aligned across hosts.

**Issues, ranked**
1. **The comparison is confounded and the sample is tiny.** The player is `cf8f` here versus `6564` at T0035, and two passes cannot bound a failure rate. T0035's 2/6 failure stays unexplained, and the passes show only that it did not recur under this player.
2. **Run 1 and run 2 differ, and the packet doesn't say so.** Run 1 used one recovery attempt (`episodes_cleared: 1`) while run 2 used none. Swept clearance was 0.126 m versus 0.270 m, and wall time was 368 s versus 350 s. Same inputs gave visibly different behavior, which weakens any "stable" reading. Add this to the packet.
3. **A summary field contradicts the trace status.** `raw_timing.final_kind: "window"` conflicts with `timing.final.kind: "missing"` and `status: "incomplete"`. A reader skimming `raw_timing` could take the trace as complete. Relabel or drop it.
4. **The startup warnings need careful wording.** All 95 and 110 lines landed at seq 1 (under 0.84 s), and the matched prefix is literally "Queue full! Messages are getting dropped!". "Observations, not drops" is correct, but don't turn it into "no drops" either. The lack of later warnings only covers the traced span, not the unknown tail.
5. **Some claims can't be checked from this data.**
   - I could only verify that profile, player and inputs match across the two runs. Equality with T0038 is asserted but not shown.
   - Root cleanup and Sol's raw source/hash/audit checks are not visible here. `shutdown_verified: true` is the runner's self-report.
6. **Minor:** the frame gaps are small (at most 51 ms), but they are 1 s window maxima from a trace that stops short of the end, so they can't show the absence of stalls.

No other objections. Batch limit and "no 2030" are consistent with two jobs and one seed.

### 2026-10-05T19:26:46.585533-07:00 · gpt-6-astra → all · CUTOFF

Late heartbeat arrived after10AM PDT cutoff. Automation igvc-overnight-improvement nowPAUSED (tool confirmed). No new experiment/provider call or implementation. Both batch attempts ended before09:00PDT and shutdown is again independently verified: no players, TCP10000free, exclusiveleaseavailable. Sonnet reviewed diagnostic interpretation, exactmodel confirmed, API-equivalentcost0.0598334USD. Sol final artifact is absent and no worker remains active; leaveT0040 in review rather than claim bothreviews complete. No further trialgrant. Runtime/source remainsunchanged.

Disposition of Sonnet findings: last raw record kind window is NOT a terminalrecord; final.kind missing is consistent, not contradictory. Future wording should say last_record_kind toavoidambiguity. Attempt1 usedone0.6m checkedbackup (actual0.6000000089m), sequence217 recovery_gate_selection original_target_clear,0candidates; nearer-station retreat remainsunexercised. Attempt2 usedzero. Differentelapsedtimes/clearances do not establishstablebehavior orcausalbenefit. Missingterminal meansunknownfinaltail; recordedwarningcounts95/110 areobservations, notdrops/no-dropproof. OriginalT0035failurepreserved;2030unexamined; promotionblocked. Rootretained bothledgerrows, no push/publishing.


relayed-from: artifacts/agents/T-0040/sol-review-r1.md

REVIEW
Task: T-0040
Reviewer: GPT-6.1 Sol
Scope: Saved evidence; read-only, no live runs or tests
Verdict: QUALIFIED — two successful repetitions; freshness cause and promotion unresolved
Usage: UNMETERED

Checked: Recomputed raw run.json SHA256 matches audit.run_sha256 for both T0040 repetitions, T0038 diagnostic and preserved T0035 failure. Both T0040 audits report passed with 20 checks; completed_destinations=6, elapsed=368.395837434/349.597993597 seconds. Complete sampled mission-health coverage reports 3685/3498 passing samples, zero failures/unknowns; maximum gaps 0.154945539/0.123447752 seconds. This is bounded lane/depth processing-health coverage, not continuous physical or all-stream health.

All four runs contain identical 19-file policy-source dictionaries. T0040 helper live records agree on profile, course, mission, autonomy and cf8f player hashes. Attempt 1 contains one requested 0.6 m backup, actual 0.6000000088954682 m; helper gate event sequence 217 reports original_target_clear. Attempt 2 contains zero backups. The new retreat selection remains unexercised.

Missing coverage: This reviewer did not independently complete T0038 live-input comparison, frozen-runtime attestation, or raw timing sequence/terminal verification. The helper reports 393/373 timing records and maximum sampled frame gaps 0.0512366/0.0484108 seconds; diagnosis tail is null. The raw parser matched no records, so these remain helper-derived, not independently verified. Missing terminal records leave terminal-tail coverage unknown.

The original T0035 2/6 freshness failure remains preserved. The timing player differs from its original player. Two passes do not establish causal benefit, freshness resolution, recovery benefit, promotion, calibrated hardware autonomy or 2027 compliance. Seed 2030 remains unexamined.

Execution limits: Initial Python alias failed before reading; authorized replacement output was truncated. A final authorized bounded probe supplied the checks above. No source edits, provider calls or simulations.
END REVIEW


### 2026-10-05T19:31:34.366629-07:00 · gpt-6-astra → all · DECISION

User explicitly resumed interactive multi-agent workflow. AcceptT0040 individual diagnostic results with qualifications; no promotion. Sol independently verified raw run/audit bindings, health, policy dictionaries and recovery evidence; its timing parser usedwrongmarker and additionalclaims remain helper-only in thatreview. Root filled remaining checks with explicit bounded assertions saved artifacts/agents/T-0040/coordinator-verification.json: raw schema2 sequences393/373; last_record_kind window (not terminal); maxgaps0.0512366/0.0484108; warnings95/110 allseq1; rawlogSHA matchesreport; all4inputfiles andlivefields matchT0038; frozen clean20a18f3/player/source19 independently matchcurrentfiles. Do notdescribe those rootchecks as Solchecks. Both reviews complete with namedlimitations, notblanketvalidationofallhealth/physicalbehavior. No sourcefixornewtrial/push. Overnightautomationremainspaused.
