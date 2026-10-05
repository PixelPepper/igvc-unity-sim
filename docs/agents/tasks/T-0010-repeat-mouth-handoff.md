---
id: T-0010
title: Repeat the reviewed sensor-led mouth-handoff lap
status: integrated
priority: P1
owner: gpt-6-astra
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/transport-probe
base: 417f0ee08dee4270c6de6aab85c4503317d8d5d5
candidate: 70b3566d91dce8b807fee729dbb110c20db3c764
claim: tested
lease: released
updated: 2026-10-05
---

# T-0010: Repeat the reviewed sensor-led mouth-handoff lap

## Packet

- Objective: one additional independent test of unchanged T-0009 runtime sources/profile; no tuning or speed change.
- Managed job: artifacts/iterations/2026-10-05/mouth-repeat-1/config.json via iteration-launch.mjs. Isolated overlay /home/brand/igvc_agent_ws/t0010-repeat. Hidden Unity; no RViz or rebuild.
- Controls: seed2027, exact T0009 profile/player/course/mission, six sparseGPS, no learned scorer, checked-path/RPP,0.6m/s,body clearance3,0.5s search. Verify16source hashes equal T0009. Documentation-only launch SHA differs; do not count as a strict same-commit promotion streak with T0009.
- Grant: ONE trial only, mission600s, build10min/start3min/audit3min monitoring limits; no retry. Shared exclusive10000/domain42 lease. Verify owned shutdown and release.
- Inputs: T0009 frozen completed artifacts and task; use nativePS5 module child environment workaround already verified. Preflight clean Git/process/port required.
- Evidence: exact launchSHA,inputs/hashes,overlay,run/audit/health,ledger including failures. Only coordinator docs may change while live. Do not change source or audit.
- Acceptance: report actual audit,health,progress,time,recovery/return/clearance and compare cautiously; no promotion from one repeat.
- Reviews: Sonnet and Sol, <=10min/$5 each; own run only. Stop at evidence handback. No publication.
- Concurrent activity: T0011 permits only light local reads of finalized frozen evidence plus remote-model reasoning. No replay/tests/builds during lease; external host load remains uncontrolled.

## Handback

Pending.

## Log


### 2026-10-05T02:35:56.6277608-07:00 · gpt-6-astra → all · NOTE
Managed trial started from clean70b3566d91dce8b807fee729dbb110c20db3c764, supervisor43412. Same player/profile hashes as T0009. Pre-launch local guard first refused a newly appended T0011 ACK before any runtime; that coordination change was saved and clean preflight then passed. No failed simulation attempt or fabricated ledger row. T0011 light frozen-file analysis is the only assigned overlapping work; host load uncontrolled. No source edits during the trial.

### 2026-10-05T02:45:37.252504-07:00 · gpt-6-astra → all · LEASE-RELEASE
T0010 completed6/6 in394.558273s but audit19/20, ordered_world_full_loopfailed with exception min() iterable argument is empty after77/77gates andprogress=total. Health3948/0/0,return0.398244m,clearance0.109255m,onebackup0.608m. Original audit/failedledger retained. Source fingerprintsall16identical toT0009. Managed shutdownverified, supervisor43412/player/listenerabsent; exclusiveFileMode.Open lockprobe succeeded. Independent reviewpending. T0012 offlineprobe explicitlydispatched aftercleanup; no liveleaseowner remains.


### 2026-10-05T02:57:16.261724-07:00 · gpt-6-astra → all · REVIEW
relayed-from: artifacts/agents/T-0010/sol-review-r1.md

### 2026-10-05T02:47:33.0349315-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0010   Candidate: 70b3566d91dce8b807fee729dbb110c20db3c764   Scope: evidence
Verdict: approve

Findings (ranked, ≤ 5):
1. [major] tools/course_judge.py:topology_evidence has a terminal projection defect. Recorded sample 17418 has progress=total 155.18610514980062; sample 17419 at 354.80 s has identical XY, hence delta 0 and lo=hi=total. With 622 vertices, bisect_right produces first 621 while clamped last 620. The segment range is empty; min(candidates) raises ValueError, caught as failed topology. This confirms an evaluator exception. Remaining topology samples were unevaluated; 77/77 gates cannot certify the tail.
2. Evidence binding verified: run SHA256 f7be0831c27ec043b160c46f4016bc9608508aeae93b4d3d6463f88e925d9c98 equals audit binding. All 16 runtime fingerprints match T-0009, current bytes and normalized launch blobs. Course/mission/profile match their input manifest and T-0009; actual player assembly matches recorded identity. Learned scorers remain null.

Observation: 6/6 in 394.558273 s; audit 19/20, only ordered_world_full_loop false. Complete sampled health 3948 pass / 0 fail / 0 unknown, max gap 0.139617 s. One backup traveled 0.608 m against requested 0.6 m; exact rear sweep and blocked unknown recorded. Return 0.398244 m independently recalculated; swept clearance lower bound 0.109255 m, collision poses 0. Shutdown logs/live flag agree; no session/process/listener found, read-only lease open succeeded.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓
Tests run: none; three focused static/hash/cleanup checks. Original audit unchanged; no altered audit recomputation.
Missing acceptance coverage: separate auditor repair/review. Regression: valid square-loop fixture plus duplicate terminal poses; require all remaining samples evaluated. Retain stationary-origin, reverse/shortcut, unfinished-loop and post-finish corridor-departure negatives. Preserve this run for a separately labeled corrected audit. Current result remains failed, not promotion. Usage: UNMETERED.




### 2026-10-05T02:57:16.261724-07:00 · gpt-6-astra → all · REVIEW
relayed-from: artifacts/agents/T-0010/sonnet-review-r1.md

**REVIEW: T-0010, launch SHA 70b3566d91dce8b807fee729dbb110c20db3c764**

**Verdict:** The trial is recorded as **audit FAILED (19/20), not promoted**. The evidence record is sound. Sol's "approve" covers the evidence binding, not the trial outcome.

**Interpretation**
- The mission reached 6/6 in 394.558 s. The only failing check is `ordered_world_full_loop`.
- That failure is an evaluator exception (`min() iterable argument is empty`) at the repeated terminal pose, not a measured topology violation. The topology result is therefore **unassessed**, neither pass nor demonstrated fail.
- 77/77 gates and progress equal to total arc cover samples only through index 17418. The tail is unevaluated, so these figures cannot certify the loop.
- Sol's bisect/clamp diagnosis comes from static analysis. No test reproduced it.

**Supporting evidence (bounded)**
- Sampled lane/depth health: 3948 pass, 0 fail, 0 unknown, max gap 0.1396 s. This covers processing health only, not perception accuracy or motion authorization.
- Return distance is 0.398244 m against the 0.4 m limit, a margin of only about 1.8 mm.
- Swept clearance lower bound is 0.109255 m, with 0 collision poses and max speed 0.6 m/s.
- One checked backup traveled 0.608 m against 0.6 m requested. Recovery used 1 of 12 attempts.
- The run SHA matches the audit binding. Coordinator and Sol independently verified shutdown, port and lock release.

**Limitations**
- All 16 runtime sources, the profile, player and course/mission match T-0009. The launch SHA differs, though (docs-only), so this does **not** extend a strict same-commit promotion streak.
- This is a single run with no corrected audit. T-0013's auditor fix is in progress, and no changed-judge acceptance is claimed.
- The elapsed-time difference from T-0009 is live wall-clock and not causal evidence.
- There are no hardware or competition-compliance claims.

**Next steps**
- Retain the original failed audit and ledger unchanged.
- After the T-0013 fix, run a separately labeled re-audit of this preserved run. Require the regression coverage Sol listed: terminal duplicate poses, all remaining samples evaluated, and the retained negatives.
- Any promotion streak needs fresh same-commit runs.


### 2026-10-05T02:57:16.261724-07:00 · gpt-6-astra → all · DECISION
Accept experiment evidence; original trial remains audit FAILED19/20 with topology unassessed after evaluator exception. This is not a promotion or passing streak. Sonnet report only had T0010 review packet; subsequent T0013 independently reproduces the endpoint exception in regression tests. Original run/audit/failedledger remain unchanged. A separately labeled full re-audit may follow reviewed auditor integration. Actual Sonnet model verified, API-equivalent cost $0.0382534; Sol usage UNMETERED.
