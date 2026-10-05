---
id: T-0016
title: Measure reviewed connector numerical correction in a live lap
status: integrated
priority: P1
owner: gpt-6-astra
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/transport-probe
base: a57d4bfe001793b7bac27894448fe74df36d1282
candidate: a0a3d49ae465ef2176ce4bdb910257fc76c6ccb7
claim: audit-passed
lease: released
updated: 2026-10-05
---

# T-0016: Connector live comparison

## Packet

- User asks for continued background simulation progress while asleep. One bounded live attempt now; further trials require a new explicit task/decision after evidence review. No publication.
- Knowledge context: sensor-led-navigation, trial-audit-promotion, processing-health; README, RUNBOOK, T0014 reviewed correction and T0010 original/reaudit comparison.
- Managed job artifacts/iterations/2026-10-05/connector-numerics-1/config.json, iteration-launch.mjs with tested native Windows PowerShell5 child module environment. Source primary; isolated ROS overlay /home/brand/igvc_agent_ws/t0016-connector; hidden Unity with rendering, no RViz/Docker/Unity rebuild.
- Exact T0010 profile/player/course/mission; seed2027, six broad GPS, speed0.6m/s, body clearance3,0.5s planning, checked-path/RPP; no learned scorer. Only expected runtime source difference is reviewed tools/path_entry.py arithmetic allowance. Separately reviewed T0013 auditor now evaluates terminal tails. No threshold or audit alteration in this task.
- Shared TCP10000/domain42 exclusive process-held lease. Preflight clean Git, no existing simulator/listener. Mission600s; build10min/start3min/audit3min monitoring bounds; no automatic retries. Verify owned shutdown and exclusive lease release.
- Preserve failed results, source/profile/player hashes, health, all audit checks, recovery, stop intervals and return/clearance. Compare against preserved T0010/T0009 without claiming controlled host load or causality from one lap.
- During live trial no source edits, tests/replays/builds or other assigned substantial local compute. Light read-only preparation allowed. No world geometry in runtime policy.
- Sonnet result interpretation and Sol evidence review after shutdown; <=10min/$5 per review, no retries on provider failure. Integrator updates ledger/status; worker not assigned runtime.

## Handback

Live 6/6, 20/20 audit in 380.348777s at unchanged 0.6m/s; recorded recovery budget 0, health 3806/0/0, return 0.392594m, clearance 0.263685m. Both reviews accepted with limits. Same profile/player/course/mission, only runtime change reviewed path_entry comparison. Not causal speed proof or promotion.

## Log

### 2026-10-05T03:56:23.830200-07:00 · gpt-6-astra → all · DISPATCH
One managed integrator trial authorized by user continuation; exact launch SHA recorded by runner after this packet commit. All health, geometry and recovery gates retained. No parallel live session.


### 2026-10-05T04:05:26.588757-07:00 · gpt-6-astra → all · LEASE-RELEASE
Completed6/6 in380.348777s, audit20/20,health3806pass0fail0unknown,maxgap0.130448s. Recoverybudget0,progressrecoveriesempty; runhasnorecoverieskey. Managedshutdownverified; coordinator independentlychecked absentplayer/TCP10000 andexclusiveFileMode.Open lockprobe. Profile/player/course/mission matchT10; runtimehashdifferenceonlypath_entry.py. Ledgerappended includingfullrunbinding. Sonnet andSol evidence reviewassigned; no promotion. T0017lightreadonlyanalysis/remoteSonnet overlapped, no assignedlocaltests/replay/build.


### 2026-10-05T04:10:22.934022-07:00 · gpt-6-astra → all · REVIEW
relayed-from: artifacts/agents/T-0016/sonnet-review-r1.md

**REVIEW: T0016 @ a0a3d49 (connector-numerics-1)**

**Verdict: ACCEPT as a single clean observation. A same-source/profile repeat is justified before any higher-speed work.**

**Supported by the record**
- 6/6 destinations, 20/20 audit checks, `shutdown_verified` true, 380.348777 s.
- The `recovery_budget` block records 0 of 12 attempts, no anchor, and 0 episodes cleared. That is a positive record, not an inference from the missing `recoveries` key.
- Course, mission and profile hashes match. 16/16 source hashes match the launch commit.
- Versus T10 (394.558 s, one backup) the run is 14.21 s (3.6%) faster. Versus T9 (399.229 s, two backups) it is 18.88 s (4.7%) faster.
- Max speed is 0.6000 m/s, so there is no speed-ceiling change.

**Limitations**
- Each configuration has n=1. The time delta is not separable from host load, which was uncontrolled.
- Recovery counts differ across T9, T10 and T16 (2, 1, 0). Fewer backups may explain the time gain, so the `path_entry.py` change (1 of 16 hashes vs T9) is confounded with it. Neither can be credited.
- The auditor changed (T13 terminal-index clamp). Audit equivalence rests on the reviewed claim that no thresholds were weakened. I did not inspect the code.
- Return distance is 0.392594 m against the 0.4 m limit, a 7.4 mm margin (1.9%). It is the thinnest check, and a single sample cannot show whether it is stable.
- Swept clearance lower bound is 0.264 m. This is a lower-bound figure, not a distribution.
- The coordinator's no-player/port and lease checks, and the Sol review, are unverified here.
- No claims on causality, hardware, fidelity or promotion.

**Recommendation**
Run one repeat at the same commit, profile and speed.
- Pre-state the pass criteria: 20/20, return <0.4 m, and recovery budget recorded explicitly.
- Log host load.
- If the repeat shows any recovery or a return above 0.4 m, treat it as a variance finding and do not advance speed.

### 2026-10-05T04:10:22.934022-07:00 · gpt-6-astra → all · REVIEW
relayed-from: artifacts/agents/T-0016/sol-review-r1.md

### 2026-10-05T04:08:56.3913341-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0016. Candidate/launch: a0a3d49ae465ef2176ce4bdb910257fc76c6ccb7. Scope: evidence.
Verdict: approve-with-nits.

Findings:
1. Nit: canonical Handback remains Pending; fill it with the bounded tested result and comparison limits before closure.

Observations: original run SHA256 f05a5f07593f7d1739189905e4a9525b35d2d5560fc69c43289efbd0149ea772 matches audit binding. Launcher/live agree on launch SHA. Profile/course/mission bytes equal T-0009; recorded player assembly hash also equals that baseline (no fresh binary rehash here). Sixteen runtime fingerprints reconcile launch/current code; sensor_route_policy uses raw CRLF hashing, with normalized current bytes identical to the launch blob. Only path_entry differs from T-0009.

Run completes 6/6 in 380.348777 s under 600 s mission limit; audit passes 20/20 across 19,018 samples. Return distance 0.392594134 m leaves 7.406 mm under the unchanged 0.4 m limit. Conservative swept clearance is 0.263685259 m; maximum sampled speed approximately 0.6 m/s. Health covers the armed interval: 3,806 pass, zero fail/unknown, maximum gap 0.130448 s under 0.25 s coverage limit. Missing recoveries remains null; separately recorded recovery-budget attempts are zero. Learned scorers are disabled.

Cleanup: shutdown_verified and stop log agree; read-only inspection finds no candidate player/listener, and exclusive read-open of the external lease succeeds.

Invariants: observed-only policy and thresholds retained; geometry remains audit-only. This is one passing trial, faster than T0009/T0010 but slower than historical 363.37 s; uncontrolled host load prevents a causal speed claim or promotion.

Checks: three focused static/hash summaries plus explicitly authorized CRLF clarification; no tests/replay/live. Missing coverage: repeatability, continuous physical health, failure-snapshot path. Usage: UNMETERED.


### 2026-10-05T04:10:22.934022-07:00 · gpt-6-astra → all · DECISION
Accept evidence as one audit-passed same-profile comparison; no baseline promotion. Return margin 7.4mm and uncontrolled host load remain limits. Raw CRLF vs normalized Git blob mismatch resolved without logical code change. Sonnet actual model verified, API-equivalent cost USD0.0368974; Sol UNMETERED. T0018 one immutable a0a3d49 repeat now explicitly granted.
