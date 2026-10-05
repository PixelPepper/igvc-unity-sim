---
id: T-0018
title: Repeat audited connector correction at the same immutable source commit
status: integrated
priority: P1
owner: gpt-6-astra
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0018-connector-reliability
base: a0a3d49ae465ef2176ce4bdb910257fc76c6ccb7
candidate: a0a3d49ae465ef2176ce4bdb910257fc76c6ccb7
claim: audit-passed
lease: released
updated: 2026-10-05
---

# T-0018: Same-version repeat

## Packet

- One managed integrator trial, conditional on T0016 evidence reviews accepted and verified shutdown. Source exactly a0a3d49, same profile/course/mission/player and 0.6m/s,0.5s planning,clearance3,checked-path. No source or auditor change. Knowledge: sensor-led-navigation, trial-audit-promotion.
- Reuse relinquished clean T0014 managed worktree on new branch codex/t0018-connector-reliability at same immutable a0a3d49: C:/Users/brand/.codex/worktrees/igvc-t0008-mouth-handoff/IGVC SIM. Prior T0014 branch remains unchanged. Dedicated copies of existing player and pinned vendor; no rebuild; own generated/session/log directories.
- Job artifacts/iterations/2026-10-05/connector-repeat-2/config.json, coordinator primary, dedicated overlay /home/brand/igvc_agent_ws/t0018-repeat, nativePS5 child environment. Shared10000/domain42 exclusivelease. HiddenUnity/rendering,noRViz/Docker. Managed runner,mission600s,build10min/start3min/audit3minbounds,no retry.
- Pass criteria unchanged20/20 audit,full6/6loop,return<=0.4,healthycoveredinterval,explicitrecoverybudget/sourcebindings/cleanup. Record actual time/backup/clearance, do not credit speed improvement from n1. Stop series on auditfailure; investigate evidence.
- Sequential measured run, no local replay/test/build orsourceediting duringlease. Light documentation/remote reason only; note sampledhostload without claiming controlledenvironment.
- Newworkspace means ROS path changes; verifyoverlay/sourceidentity andplayerhash. Keep exact sourcecommit while coordination continues in primary.
- No promotion until usergate3consecutive2027passes plus2preselectedheldoutseeds underunchangedprofile andauditor. Heldoutseeds preselected now2028,2029; neither used for this refinement. This trial can establish only the second2027pass if allgatespass.
- Independent Sonnet/Sol resultreview<=10min/$5each before further decisions. No publication.

## Handback

Second same-a0a3d49 pass: 6/6 in 355.420571s,20/20 audit; health3556/0/0, one checked0.604m backup, return0.398906m, sweptclearance0.295566m. All16rawsources/profile/course/mission/player match T0016. Shutdown independently verified. Two passes, not promotion. See relayedreviews and job artifacts.

## Log

### 2026-10-05T04:06:56.304952-07:00 · gpt-6-astra → all · NOTE
Prepared, not launched. Await T0016 evidence disposition. Source/player/profile frozen; no automatic-on-idle dispatch.


### 2026-10-05T04:10:22.934022-07:00 · gpt-6-astra → all · DISPATCH
T0016 dual review accepted and shutdown verified. Launch ONE repeat now with frozen worktree a0a3d49; all 16 raw runtime hashes and player assembly match T0016. One CRLF text-identical file aligned and Git index refreshed, no staged/logical diff. No heavy overlapping work.


### 2026-10-05T04:15:22.405813-07:00 · gpt-6-astra → all · NOTE
Live mission running at exact a0a3d49 with player/profile matched. T0019 light authoring in separate worktree is explicitly allowed by user-approved ADR011; no assigned heavy tests/replays/builds overlap. Host load samples retained in job; uncontrolled load prevents causal timing claims.


### 2026-10-05T04:21:06.987016-07:00 · gpt-6-astra → all · REVIEW
relayed-from: artifacts/agents/T-0018/sonnet-review-r1.md

**Verdict: the hold is reasonable.** Both passes support "completes and audits cleanly at 0.6 m/s on this commit." They don't support "stable" or "ready to advance."

**Facts (from the JSON)**
- Commit a0a3d49 completed 6/6 with audit 20/20 and shutdown verified.
- Elapsed was 355.42 s, versus 380.35 s for T16 (24.9 s faster).
- Course, mission and profile hashes match the expected values, and all 16 source hashes match the launch.
- Health was 3556/3556 pass, with a max gap of 0.149 s.
- Collision poses: 0. Swept clearance lower bound: 0.296 m. Max speed: 0.600 m/s.
- Recovery: 1 attempt, 1 episode cleared.

**Limitations**
- **Backup distance:** the JSON shows `forward_distance_m` 0.0 and a null anchor, not 0.604 m. The 0.604 m figure must come from another artifact, so reconcile it before citing.
- **Return margin:** final distance to origin is 0.399 m against a 0.4 m limit. That is a 0.001 m margin, and I'd flag it.
- **Repeatability:** T16 had zero backups and this run had one, so zero-backup behavior did not repeat. Two same-commit passes are not the 3+ held-out gate.
- **Seeds:** 2028/2029 were preselected and are untested.
- **Host load:** load was uncontrolled, and Opus's editing overlapped.
- **Not in the pasted JSON:** the lock release and the separate worktree/overlay rest on the coordinator's report.

**On the proposal:** a third repeat at 0.6 is sensible, with these conditions:
- Keep the commit and runtime hashes identical. If worker checks change code, label it a new version.
- Log host load for that run.
- Run the seeds afterward.

The 24.9 s difference and the backup difference are both observations. This evidence doesn't establish a cause, hardware fidelity, or promotion.

### 2026-10-05T04:21:06.987016-07:00 · gpt-6-astra → all · REVIEW
relayed-from: artifacts/agents/T-0018/sol-review-r1.md

### 2026-10-05T04:19:58.2299410-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0018. Candidate/launch: a0a3d49ae465ef2176ce4bdb910257fc76c6ccb7. Scope: evidence.
Verdict: approve-with-nits.

Findings:
1. Nit: task still has Pending Handback/held lease; update coordination state to the reviewed outcome and verified release before closure.

Observations: clean frozen worktree matches launch SHA. Run SHA256 db5e1f90a78006b99b84a5d9b2c540ab0f021a88a6b57a02bf3e4e46aa3d323b binds audit and compact report. All 16 raw source hashes match worktree and T0016; profile/course/mission hashes match both manifests and T0016 bytes. Launcher/config identify the separate worktree and t0018-repeat overlay; overlay record reports three installed perception files matching their dedicated sources. Recorded player hash remains 6564e854…; copied assembly was located and hashed, but console formatting hid its hash value, so fresh binary equality is coordinator-verified.

Completed 6/6 in 355.420571 s under 600 s; audit passes 20/20 across all 17,772 samples. Health: 3,556 pass, zero fail/unknown, complete coverage; 0.148970 s maximum gap below 0.25 s. One destination-4 backup travels 0.604000 m, with recorded rectangular rear sweep, unknown blocked and straight-only checks; budget records one attempt/one cleared episode. Return 0.398905606 m leaves 1.094 mm margin; swept clearance lower bound 0.295565966 m, zero collision poses. Learned scorers remain disabled.

Cleanup: shutdown/stop evidence agrees; no candidate player/TCP10000 listener; exclusive read-open lease succeeds.

Checks: bounded static/hash/cleanup commands; no tests/replay/live. Invariants retained. Two same-commit passes support repeat evidence only; host-load samples are uncontrolled. Promotion still requires third 2027 pass and preselected 2028/2029 passes. Usage: UNMETERED.


### 2026-10-05T04:21:06.987016-07:00 · gpt-6-astra → all · DECISION
Accept audited repeat with qualification: 1.094mm return margin; elapsed-time and recovery variance remain. Sonnet requested distance provenance: run.recoveries[0].actual_distance_m=0.6040000089535948, independently verified by Sol (not budget.forward_distance_m). Sonnet actualmodelverified, API-equivalentUSD0.0301314;SolUNMETERED. Hold0.6m/s. Third same-version repeat may be a new explicitly bounded task after worker tests finish; no promotion before held-out2028/2029.
