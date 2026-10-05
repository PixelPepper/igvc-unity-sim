---
id: T-0020
title: Third same-version seed-2027 connector repeat
status: integrated
priority: P1
owner: gpt-6-astra
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0018-connector-reliability
base: a0a3d49ae465ef2176ce4bdb910257fc76c6ccb7
candidate: a0a3d49ae465ef2176ce4bdb910257fc76c6ccb7
claim: tested
lease: released
updated: 2026-10-05
---

# T-0020: Third repeat

## Packet

- One attempt after T0018 accepted evidence and T0019 focused revision checks finish. Exact same immutable a0a3d49 workspace, dedicated overlay and profile/player/course/mission as T0018. No instrumentation integration into the running checkout. Knowledge: trial-audit-promotion, sensor-led-navigation.
- Job artifacts/iterations/2026-10-05/connector-repeat-3/config.json; managed iteration-launch.mjs, native PS5 child module environment; exclusive10000/domain42, hidden rendered Unity, no RViz/Docker/rebuild.
- Mission600s, build10min/start3min/audit3min bounds; no retry. Same0.6m/s,0.5s planning,clearance3,checked-path/RPP, six sparseGPS, no scorer/coursegeometry runtime inputs.
- Keep all footprint/sweep/health/return/paint/ramp/speed gates. Record every result and verifiedshutdown. Goal third consecutive seed2027 fullauditpass; backups remainallowedandreported. Any failure breaks streak; no cherry-picking.
- Light source work in OTHER checkout and remote reviews permitted under ADR011; no heavy local tests/builds/replay while running. Record load samples, no controlled timing claim.
- No promotion: preselected2028/2029 still required and not run. Userapprovedgate needs fullpasses across those variants as well. Thirdpass alone is reliability evidence for thisseed/version, not generalization/hardwarefidelity.
- Independent Sonnet/Sol evidence review <=10min/$5each after cleanup. Stopafteroneattempt; no publication.

## Handback

FAILED trial evidence accepted; no promotion. Immutable launch a0a3d49, job
artifacts/iterations/2026-10-05/connector-repeat-3. Stopped at 2/6 after
226.295129231 s: no observed collision-free backup with useful forward clearance.
Audit 14/20; completion, return, ramp and ordered-loop checks fail. Footprint,
paint, obstacle and speed checks pass. Health 2265 pass/0 fail/0 unknown,
max gap 0.130315273 s. Zero charged recoveries; missing recoveries list is not
inferred to be an empty array. All 16 runtime hashes and profile/player/course/
mission match T0018. T0019 recorder is absent. Verified shutdown and lease release.
Run SHA256 6959f6278a7dc1a5e93175db9d66fb3791a94dbb178c62147c45aecb5e7569bb.
The failed row is recorded in benchmark_runs.csv. Two previous passes followed
by this failure do not satisfy the consecutive-pass gate. Review artifacts are
under artifacts/agents/T-0020. No causal or speed-improvement claim.

## Log

### 2026-10-05T04:21:46.919929-07:00 · gpt-6-astra → all · NOTE
Prepared third-repeat packet. T0018 dual-review accepted; wait for T0019 revision
tests to finish before explicit launch. The source checkout stays at a0a3d49.


### 2026-10-05T04:27:20.466401-07:00 · gpt-6-astra → all · DISPATCH
Launch ONE third frozen-version repeat now. T0018 evidence accepted, T0019 focused and combined checks finished. No more heavy checks during live lease. T0021 isolated light development may overlap under ADR011; its tests must wait for this trial shutdown. Same a0a3d49 runtime/profile, no recorder change in running source.

### 2026-10-05T04:39:54.183617-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW
relayed-from: artifacts/agents/T-0020/sonnet-review-r1.md

**REVIEW verdict: T0020 is an honest failure, not a regression we can explain yet.**

**Interpretation**
- Attempt 3 stopped at 2/6 after 226.3s with "No observed collision-free backup with useful forward clearance."
- It was a conservative refusal by the legacy escape logic, not a collision or a health fault. Collision poses were 0, swept clearance was 0.335 m, and health was 2265/0/0.
- No recovery was charged: 0 attempts, no anchor, 0 episodes cleared. The stop came before any backup was attempted.
- The 6 audit failures (six destinations, return, two ramp checks, ordered loop, in-order visits) all follow from the early stop. They are not independent defects.
- With passes at 380.35s and 355.42s, the result is 2 of 3 on identical frozen inputs. That is marginal and variable, so the 3-consecutive streak is broken. No promotion or speed increase.
- The `path_entry.py` drift from T0009 is identical across T16/T18/T20, so it can't explain the variance.
- The corrected source-hash comparison didn't change the run or audit.

**Next bounded investigation (read-only)**
Use the 746 decisions and telemetry to answer three questions:
1. Where was the robot at the stop?
2. Which backup candidates were rejected, and for what reason: rear unobserved, forward clearance too small, or a threshold?
3. Does the stop match the location of the one backup in the 355s pass?

This yields a hypothesis only. It does not justify a fix.

**Constraints:** no loosening of checks or world inputs, and no retrying until a pass. T21 stays independent, and this failure can't be credited to it or claimed fixed by it.
### 2026-10-05T04:39:54.183617-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
relayed-from: artifacts/agents/T-0020/sol-review-r1.md

### 2026-10-05T04:34:51.4025644-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0020. Candidate/launch: a0a3d49ae465ef2176ce4bdb910257fc76c6ccb7. Scope: evidence.
Verdict: approve-with-nits (failed trial evidence accepted).

Findings:
1. Nit: Handback/lease state is still pending/requested; record failure and verified release before closure.

Observations: clean frozen checkout and launcher match launch SHA. Run SHA256 6959f6278a7dc1a5e93175db9d66fb3791a94dbb178c62147c45aecb5e7569bb binds audit/compact report. All 16 raw fingerprints match running workspace and T0018; profile/course/mission bytes also match. Actual copied player assembly hashes to 6564e854… as recorded. T0019 recorder is absent. Preserved primary-check mismatch concerns sensor_course.py; corrected report's workspace comparison independently passes.

Mission stops at 2/6 after 226.295129 s. Audit fails six completion/return/ramp/full-loop checks (14/20 pass) over all 11,316 samples; collision, footprint paint and speed checks pass. Conservative swept clearance is 0.335262922 m; zero collision poses. Sampled processing health is complete: 2,265 pass, zero fail/unknown, maximum gap 0.130315 s below 0.25 s. Recovery budget records zero attempts; absent recoveries remains unavailable, not an inferred list count.

Final observed recovery gate reports no_fresh_corridor_or_footprint, zero candidates/collision checks; broad GPS fallback is selected before the recorded useful-backup failure. This describes selection outcome, not impossible routing, node causality or a demonstrated fix. Insufficient lane visibility is distinct from processing-health failure.

Cleanup: shutdown/stop evidence agrees; no player/listener; exclusive lease read-open succeeds. Invariants/thresholds retained; learned scorers disabled. Failure breaks the consecutive-pass streak; no promotion.

Checks: bounded static/hash/cleanup inspection only. Missing coverage: causal diagnosis and held-out validation. Usage: UNMETERED.

### 2026-10-05T04:39:54.183617-07:00 · gpt-6-astra → all · DECISION
Both evidence reviews accepted. Close the experiment as a FAILED, tested result;
'integrated' refers to evidence recording only, not successful navigation.
Header and handback now reflect verified release. Sonnet cost USD0.0297554
API-equivalent; Sol UNMETERED. Preserved primary-check report was corrected to
compare against the actual frozen runtime workspace; original run/audit untouched.
Streak is broken. Next investigate observed recovery prerequisites rather than
weakening audit/health/sweeps or increasing speed.
