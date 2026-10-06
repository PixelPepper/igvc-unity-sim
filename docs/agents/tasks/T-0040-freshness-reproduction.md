---
id: T-0040
title: Seek a bounded reproduction of intermittent freshness expiry
status: review
priority: P1
owner: gpt-6-astra
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0038-timed-2029-diagnosis
base: 20a18f3
candidate: 20a18f3e7df4da4fa6dce4e5c8e5d16323b4c5ef
claim: tested
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
