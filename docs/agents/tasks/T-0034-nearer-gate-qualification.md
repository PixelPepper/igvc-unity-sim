---
id: T-0034
title: Qualify the new recovery build with three fixed-version seed2027 laps
status: integrated
priority: P1
owner: gpt-6-astra
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0033-nearer-gate-trial
base: d6519e1ee323db0e66fd5953959f07cc56508cc5
candidate: d6519e1ee323db0e66fd5953959f07cc56508cc5
claim: audit-passed
lease: released
updated: 2026-10-05
---

# T-0034: Up to three separately granted sequential trials

## Packet

- Read README, T0032 accepted source and T0033 regression evidence. Frozen runtime
  d6519e1 remains clean in codex/t0033-nearer-gate-trial. No source/profile changes.
  The three f1a6ae4 seed2027 passes do not qualify this new source.
- Objective: three consecutive seed2027 full-audit passes on this exact runtime.
  Jobs artifacts/iterations/2026-10-05/nearer-gate-2027-{1,2,3}. Each attempt gets
  a separate explicit coordinator LEASE-GRANT. Never overlap or auto-retry.
  Stop this batch on the first mission/audit/health/identity/cleanup failure;
  preserve and review that result rather than replacing it with another attempt.
- Same profile/player/course/mission/autonomy as original2027 series. Requested
  speed0.6, planning0.5, clearance3, checked-path/RPP, six broad GPS destinations,
  scorers off and replacement fallback off. No map geometry enters the policy.
  Renderer/auditor course files remain separate from sanitized runtime goals.
- Hidden rendered Unity + native WSL Jazzy/Nav2. Exclusive10000/domain42 lease
  per trial, released only after verified cleanup. Mission600s/build10min/start3min/
  audit3min monitored bounds each. No heavy tests/replay/builds while live.
- After each trial verify actual source/input/player identity, full20-check audit,
  interval health, recovery event/exercise claims and root player/port/lease cleanup;
  append the ledger before any next grant. No extra passing-run tests without cause.
- Source/frame/mounts/footprint/unknown/health/speed/budgets and audit remain frozen.
  No adjustment to improve a score inside this batch. Preserve raw evidence.
- After the batch (or first failure), one Sonnet interpretation review and one Sol
  independent raw review of the aggregate <=15min/$5 each. No provider retries.
- Passing this stage is not full promotion: preselected2029 still needs its first
  attempt. T0033's2028 pass is development regression, not untouched generalization.
  Original failed2028 evidence remains. No mechanism benefit without actual branch
  exercise; no physical calibration, causal speed gain, publishing or hardware claim.
- Stop after at most3 separately granted attempts or first failure, whichever
  occurs first. Stop sooner at the overnight cutoff or user request.
- Knowledge: sensor-led-navigation; trial-audit-promotion; ros-unity-transport.

## Handback

Acceptedthreeconsecutive2027passes on d6519e1; untouchedseedstage pending.

## Log


### 2026-10-05T06:52:30.3251493-07:00 · gpt-6-astra → all · LEASE-GRANT
Grant attempt1 ONLY, jobnearer-gate-2027-1. T0033 accepted, source d6519e1 clean, no player/port, lease free. Prepared2027 profile/course/autonomy copiedT0030; generatedmission copy validated against historicalSHA4e3c18c4cc0abe33d9cfc7894612bcf90df60b2607b7e91e2b39b22305d8b000 (T0030 job didnotretain thatfile, initialcopyfailedbeforelaunch). Completeinput-hashes.json verified. No laterattempt authorizedyet; failurestopsbatch.


### 2026-10-05T06:53:43.1834637-07:00 · gpt-6-astra → all · NOTE
Attempt1 supervisor57324 reached mission; startup2027 course/mission/autonomy hashes exactly match prepared originals, profile/player match qualification baseline. d6519e1 remains immutable. Exclusive lease held.


### 2026-10-05T07:00:19.6637084-07:00 · gpt-6-astra → all · LEASE-RELEASE
Attempt1 complete6/6/all20 in332.553486619s, health3328/0/0gap.121140897, zero chargedbackup/no recovery failure. Return.363767588; sweptclearance.166019526.19sourcehashesmatchcleanruntime andT0033. RunSHA43021cab417c373915d32f0257c5fb3206ea7872e16444db57bd675e1bd2ba17. Ledgerappended. Root no player/10000listener/exclusivelease confirmscleanup. Aggregate reviews afterbatch; no promotion.

### 2026-10-05T07:00:19.6659753-07:00 · gpt-6-astra → all · LEASE-GRANT
Grant attempt2 ONLY, jobnearer-gate-2027-2. Prior complete audit/health andcleanup checked; exactsamefrozen source/profile/player/inputs. No heavywork/retries. Failurestopsbatch; attempt3requiresseparategrant.


### 2026-10-05T07:01:32.1684574-07:00 · gpt-6-astra → all · NOTE
Attempt2 supervisor4184 reachedmission, startup2027 inputs exactlymatchprepared/attempt1. d6519e1 source and profile/player remainfrozen; no othertrialactive.


### 2026-10-05T07:08:32.3480867-07:00 · gpt-6-astra → all · LEASE-RELEASE
Attempt2 complete6/6/all20 in358.873351222s, health3590/0/0gap.127245575, zero chargedbackup/no recoveryfailure. Return.391660338; sweptclearance.353112029.19sourcehashesmatchcleanruntime andT0033. RunSHAb4b4602251cef5fb8ab78863d2a7d4978e36b619124e262120c14780264c0335. Ledgerappended. Root no player/10000listener/exclusivelease confirmscleanup. Aggregate reviews afterbatch; no promotion.

### 2026-10-05T07:08:32.3500710-07:00 · gpt-6-astra → all · LEASE-GRANT
Grant attempt3 ONLY, jobnearer-gate-2027-3. Prior complete audit/health andcleanup checked; exactsamefrozen source/profile/player/inputs. No heavywork/retries. This is finalattemptinbatch; stopaftercompletionandreview.


### 2026-10-05T07:09:08.7767995-07:00 · gpt-6-astra → all · NOTE
Attempt3 supervisor65228 reachedmission, startup2027 inputs exactlymatchprepared andattempts1/2. d6519e1 source and profile/player remainfrozen; exclusivelease held. No othertrialactive.


### 2026-10-05T07:16:17.9012771-07:00 · gpt-6-astra → all · LEASE-RELEASE
Attempt3 complete6/6/all20 in336.905818874s, health3371/0/0gap.119719062, zero chargedbackup/no gate-selection events. Return.375730825; sweptclearance.297994671; source19matchcleanruntime/T0033, same2027inputs. Ledgerappended. Root independently no player/10000listener/exclusivelease verifiescleanup. Threeattemptsfinished; no moregrantsinbatch. AggregateSolraw/Sonnetinterpretationreviewsrequested. Newmechanism unexercised and2029/2030remainuntested.


### 2026-10-05T07:20:33.7439769-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW
relayed-from: artifacts/agents/T-0034/sonnet-review-r1.md

**Verdict: three of three attempts pass. Qualifies the fixed-version 2027 stage only.**

**Identity.** All three attempts share the same commit (d6519e1), autonomy, mission, course and profile hashes, player assembly, and seed 2027. The same-19-source and same-profile/player flags against T0033 are true, and `all_same2027_inputs` is true.

**Audit and health.**
- All 20 audit checks are true in each attempt.
- Health has 0 fail and 0 unknown, coverage is complete, and the interval is verified. The max gaps are 0.121, 0.127 and 0.120 s.
- All three completed 6/6 destinations at a requested 0.6 m/s.
- Return distances are 0.364, 0.392 and 0.376 m against the 0.4 m limit. Attempt 2 has only 0.008 m of margin.
- Swept clearance lower bounds are 0.166, 0.353 and 0.298 m, with zero collision poses. Attempt 1 has the tightest clearance.

**Budgets.** `recoveries` is null, so I'm not treating that as zero. The explicit `recovery_budget` shows 0 of 12 attempts used in each run, and the replacement fallback is off with 0 sent.

**Recovery-gate retreat: not exercised.** `gate_events` is empty in all three runs, and `clear_gate_target_at_nearer_observed_station` never appears, so selection was never proven. That means there is no mechanism-benefit claim. Three passes from one uncontrolled configuration don't establish causality.

**Capture.** 221, 239 and 224 decisions were saved with 0 dropped and no errors, and outcomes match. `shutdown_verified` is true each time. The root-cleanup check per grant isn't in this JSON, so I'm relying on the grant record for it. A successful worker-binding flag is not independent capture, and the raw Sol review is still pending.

**Scope.**
- T0033 is a 2028 development regression, not untouched held-out. The original T0031 failure stays preserved.
- The old-version three passes are not transferred.
- The batch did not need to stop early, since no attempt failed.
- No promotion, fidelity or speed-gain claim follows from this.
- The preselected 2029 seed is still untested, and any failure there would block qualification.

**Recommendation:** record the 2027 stage as qualified, note that retreat selection was unexercised, and proceed to 2029 only after the raw Sol review.
### 2026-10-05T14:18:35+00:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0034   Candidate: d6519e1ee323db0e66fd5953959f07cc56508cc5   Scope: evidence
Verdict: approve — seed2027 three-pass stage complete, no full promotion.

Findings (ranked, ≤ 5):
1. Three separately granted attempts completed 6/6 and passed all 20 audit checks on this exact runtime.
2. Recovery retreat remains unexercised: all three have zero charged budget attempts, no recovery events/failure captures and fallback off. Budget, not missing lists, establishes zero. No benefit/speed-causality claim.

| Attempt | Elapsed s | Audited samples | Health pass/ fail/ unknown | Maximum gap s | Return m |
| --- | ---: | ---: | --- | ---: | ---: |
| 1 | 332.553486619 | 16632 | 3328/0/0 | .121140897 | .363767588 |
| 2 | 358.873351222 | 17945 | 3590/0/0 | .127245575 | .391660338 |
| 3 | 336.905818874 | 16851 | 3371/0/0 | .119719062 | .375730825 |

Recomputed run hashes match audits: 43021cab…, b4b46022…, dfc698e0…. Every trajectory sample is audited; health ledger/diagnosis agree on complete coverage, no integrity errors, gaps below unchanged 0.25s. Endpoints reproduce audit distances; smallest return margin is 8.340mm. All three report zero collision poses/unproven sweep subsegments.

All 19 raw source fingerprints equal each other/T0033 and the clean frozen runtime. Profile/actual player match T0033. Prepared/generated 2027 course/mission/autonomy bytes match; seed metadata/course binding and run/live identities agree. Coordinator heads differ, but five script hashes match each other/current files/commit blobs.

Runner shutdown_verified, successful cleanup phases/stop logs cover each trial; root records absence/lease checks after each. Reviewer confirms final absence of player/listener and exclusive lease availability.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓.
Tests run: none (read-only aggregate hashes/JSON/endpoints).
Missing acceptance coverage: untouched 2029/2030 outcomes, live retreat execution and broader reliability. T0033 remains 2028 development regression; failed T0031 is retained. Usage: UNMETERED.


### 2026-10-05T07:20:33.7641952-07:00 · gpt-6-astra → all · DECISION
Acceptthreeconsecutive d6519e1 seed2027 fullauditpasses. Sonnet USD0.0426274 API-equivalent; Sol UNMETERED. Raw source/input/player/health/audit/cleanup checks verified. Recoveryretreat remainsunexercised; no mechanismbenefitclaim. Thisqualifies2027stageonly; T0035first2029 andadditionalpreselected2030neededfortwo untouchedseeds, alongside preserved2028regressionandoriginalfailure. No publishing/fullpromotion.

