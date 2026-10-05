---
id: T-0034
title: Qualify the new recovery build with three fixed-version seed2027 laps
status: in-progress
priority: P1
owner: gpt-6-astra
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0033-nearer-gate-trial
base: d6519e1ee323db0e66fd5953959f07cc56508cc5
candidate: d6519e1ee323db0e66fd5953959f07cc56508cc5
claim: none
lease: held
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

Pending.

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

