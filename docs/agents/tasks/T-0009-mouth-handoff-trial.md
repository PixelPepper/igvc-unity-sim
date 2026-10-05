---
id: T-0009
title: Audit one live trial of the reviewed mouth handoff correction
status: integrated
priority: P1
owner: gpt-6-astra
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/transport-probe
base: efb81f545a72201e3d2a9888113c421d2d950a60
candidate: 8f99951a189a02ba1b3e8d07b3fc58b50fdcfc0f
claim: tested
lease: released
updated: 2026-10-05
---

# T-0009: Audit one live trial of the reviewed mouth handoff correction

## Packet

- **Dependency:** T-0008 immutable candidate accepted after Sonnet/Sol review, exact range integrated and combined core tests passing. No launch before those gates. Freeze clean launch SHA and update the header from live provenance.
- **Objective:** Determine whether the first-sector blockage is avoided and how far the complete sensor-led course proceeds. Six destinations alone are not acceptance; require the unchanged independent audit, health, footprint, paint, ramp, ordered-loop and return checks.
- **Controls:** Same hidden player, seed2027 course, sanitized six-goal autonomy, RPP profile,0.6m/s ceiling, checked-path, heading memory, legacy escape, clearance weight3 and0.5s planning setting as T-0006. Copy its unchanged profile, verify player/course/mission/profile hashes match. Record source differences; only reviewed T-0008 behavior may differ. Host load remains uncontrolled.
- **Managed execution:** One attempt through `tools/agents/iteration-launch.mjs`; new job `artifacts/iterations/2026-10-05/mouth-handoff/`, isolated overlay `/home/brand/igvc_agent_ws/t0008-mouth-handoff`. Use the tested native Windows PowerShell5 module path only in the child environment, as recorded in T-0006; no global settings changed. Hidden Unity/no RViz. No Unity rebuild.
- **Lease / bounds:** Same exclusive primary TCP10000/domain42 process-held lease as T-0006. Preflight must find no conflicting process/port; never stop another session. Mission600s, monitored build10min/start3min/audit3min stage limits, verified owned shutdown before lease release. No automatic retry or second lap. No runtime source edits or other live worker.
- **Evidence:** Preserve exact inputs, hashes, isolated import verification, run/audit/diagnosis, decision captures, logs and cleanup. Append the stable result (including failure) to benchmark_runs.csv. Code reviewers check interpretation against the immutable candidate; Sol independently verifies evidence. Stop and retain negative results rather than reducing safeguards. New failure investigation requires another scoped task.
- **Claim:** An audited successful lap is one result, not promotion. User gate remains3 consecutive2027 passes plus1 each on2 preselected held-out seeds. Live first-failure capture stays unverified if no failure/unknown occurs. No physical-calibration or competition-compliance claim.
- **Budget / scope:** One integrator experiment; $5/10min per bounded reviewer, unmetered subscription usage labeled. No source implementation, publication, recursive delegation or additional agents operating simulation.

## Handback

One bounded comparison completed: 6/6 in399.229339s, all20 audit checks passed,3994/0/0 health samples, two checked0.602m backups, return0.384816m and conservative swept clearance0.116546m. Runtime shutdown and exclusive lease release verified. One passing ideal-fixture run only; no promotion or speed claim. See docs/evidence/navigation-2026-10-05.md and the benchmark ledger.

## Log


### 2026-10-05T02:01:11.9816710-07:00 · gpt-6-astra → claude-opus-5-5 · NOTE
T-0008 exact integration passed567 combined tests. T-0009 launched from clean8f99951a189a02ba1b3e8d07b3fc58b50fdcfc0f with hidden supervisor60168; exclusive lease held, ROS building. Profile/player hashes match T-0006. Only coordination documentation may change during execution. Remain idle; no parallel live work.



### 2026-10-05T02:14:38.655102-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Coordinator receipt-time relay.
### 2026-10-05T02:11:34.4233249-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0009   Candidate: 8f99951a189a02ba1b3e8d07b3fc58b50fdcfc0f   Scope: evidence
Verdict: approve-with-nits

Findings (ranked, ≤ 5):
1. [minor] Cleanup verification limitation: live.json records shutdown_verified and stop.log reports owned ROS shutdown; current Windows/WSL process queries and TCP 10000 query found no matching live session. External lease release was not independently lock-tested: UTF-16 overlay-log decoding interrupted that portion of the third bounded check. Confirm release before another launch.
2. No result/provenance contradiction found. Original run SHA256 f210c015819dc3fe5f792217de2a8ee47e1ac402cbe94b051b62b82223f43ac8 equals audit binding; all 20 checks pass. Launcher/live bind the exact launch SHA. Course, sanitized mission, profile and recorded player assembly match T-0006. All 16 recorded source fingerprints match current bytes and launch blobs after Git normalization; only sensor_course.py and observed_navigation.py differ from T-0006.

Observation: completed 6/6 in 399.229339 s; no learned route/corridor scorers. Armed health totals 3994 pass / 0 fail / 0 unknown, complete coverage, maximum gap 0.138817 s below unchanged 0.25 s limit. First failure/unknown snapshots absent; failure capture remains unexercised. Two recorded destination 5 straight backups each requested 0.6 m and traveled 0.602 m, with exact rear rectangle sweeps and unknown blocked; attempts 2/12, one episode subsequently cleared. Audit return 0.384816 m independently matches final pose; swept clearance lower bound 0.116546 m, collision poses 0.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓
Tests run: none; three read-only artifact/hash/process checks. No audit recomputation or live run.
Missing acceptance coverage: repeated 2027/held-out passes, controlled host-load comparison, independent lock-release check and physical validation. This is one ideal-fixture audited pass, not promotion; 399.23 s exceeds historical 363.37 s. Causal attribution and speed improvement remain unproven. Usage: UNMETERED.


relayed-from: artifacts/agents/T-0009/sol-review-r1.md


### 2026-10-05T02:14:38.655102-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW
Coordinator receipt-time relay.
**REVIEW: T-0009, Claude Sonnet 5.5, read-only experiment review**
**Exact SHA:** 8f99951a189a02ba1b3e8d07b3fc58b50fdcfc0f
**Receipt time:** not supplied; coordinator to stamp on receipt. No time is invented here.
**Verdict: approve-with-nits.** Accept as one audited, ideal-fixture pass. This is not promotion evidence.

**Supported by the data**
- The run completed 6/6 destinations in 399.229339 s with audit exit 0 and 20/20 checks. The audit run SHA256 (f210c015…) is bound to the launch commit.
- Armed-interval health was 3994 pass / 0 fail / 0 unknown, with a max gap of 0.1388 s against the 0.25 s limit.
- The profile, course, mission, and player assembly match T-0006. Only `sensor_course.py` and `observed_navigation.py` differ in source, and all 16 fingerprints match the launch.
- Sol independently verified binding, hashes, and results. I did not recompute the audit.

**Limits on interpretation**
- **Single trial.** T-0006 failed and this one passed, but host load was uncontrolled. The two-file diff is a candidate explanation only, not a causal result, and it says nothing about repeatability.
- **Speed.** 399.23 s is slower than the historical 363.37 s pass, which had one backup against two here. Make no speed claim.
- **Margins.** Return distance was 0.3848 m against the 0.4 m limit, and swept clearance was 0.1165 m. Both are thin, so treat them as pass-with-little-headroom, not robustness.
- **Recovery.** Both backups were at destination 5 (0.602 m each, 2/12 attempts, one episode cleared). Recovery was exercised, but only in one place.
- **Health evidence.** Health is sampled, not continuous. First-failure telemetry stayed unexercised because no failure occurred.
- **Scope.** The result is simulated and sensor-only. No physical or rule-compliance claim follows.

**Open gate**
- Lock release is not independently verified. Sol's lock test was interrupted, so the coordinator's separate check must complete before any next launch.

**Next steps**
Repeat the exact candidate and profile before promotion, then run the preselected held-out seeds. Keep all thresholds and the sparse-GPS, sensor-only policy unchanged. Run a host-load comparison if causal or speed claims are wanted.
relayed-from: artifacts/agents/T-0009/sonnet-review-r1.md

### 2026-10-05T02:14:38.655102-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION
Accept T-0009 as one tested experiment result, not policy promotion. Both reviews approve with nits. All20 audit checks pass; no source change or audit weakening during trial. Sol independently checked16source fingerprints, input identities and run/audit binding. Coordinator completed the remaining exclusive existing-file lock probe successfully; artifacts/agents/T-0009/lease-release.txt records receipt. Player/supervisor/port absent and owned stop logs agree. Lease released. Sonnet exact claude-sonnet-5-5 verified, API-equivalent USD0.0375414; Sol UNMETERED.
Two backups at destination5, narrow return margin and399.23s versus historical363.37s remain. No first health failure occurred, so that live capture remains unexercised. Next scoped experiment should repeat this exact source/profile with recorded controls before any further navigation tuning; user promotion gate stays3consecutive2027 plus1each on2preselectedheldoutseeds. No second lap in T-0009. User requested explanation of research adoption; current mapping is now in COMPETITION_CONTEXT.md, based on direct read of the28pagePDF. No source implementation requested by that clarification.
