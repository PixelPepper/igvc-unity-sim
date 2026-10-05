---
id: T-0024
title: Validate off-mode replacement control and live completion telemetry
status: integrated
priority: P1
owner: gpt-6-astra
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0024-replacement-control
base: 0f76a2ac6090de0cf83c8f57bd471874dbffe552
candidate: 0f76a2ac6090de0cf83c8f57bd471874dbffe552
claim: audit-passed
lease: released
updated: 2026-10-05
---

# T-0024: One default-off control lap

## Packet

- After T0021 dual review and combined checks, one bounded hidden rendered Unity
  plus native ROS2 Jazzy/Nav2 run, seed2027. Source immutable 0f76a2ac6090de0cf83c8f57bd471874dbffe552.
  Reuse frozen trial worktree igvc-t0008-mouth-handoff on NEW assigned branch.
- Managed job artifacts/iterations/2026-10-05/replacement-control-1/config.json;
  exclusive primary lease TCP10000/domain42; own overlay
  /home/brand/igvc_agent_ws/t0024-control. Native PS5 module environment.
  No RViz, Docker or Unity rebuild. No stop of unowned processes.
- Explicit revalidate_active_path=false; record_episode=false; same prior profile/
  player/course/mission, speed0.6, planning0.5, clearance3, checked-path/RPP,
  six sparse GPS goals, no learned scorer or course geometry in policy.
- Mission600s, build10min/start3min/audit3min monitoring bounds, no retry.
  Preserve every failure. Capture processing health, full audit, completion
  recorder's decision/cleanup/final endpoint, fallback mode/counts and source hashes.
  No old/new timing causality or promotion from this attempt.
- T0023 light authoring allowed in different worktree while source is immutable;
  no heavy tests/replay/builds during live. Record sparse host-load observations.
- After verified shutdown root independently checks player, port and lease.
  One compact independent Sonnet/Sol evidence review each <=10min/$5.
  Source includes new instrumentation; baseline's passing streak already broken.
  Any enabled comparison must use SAME frozen source/profile, with only opt-in
  flag changed and separately granted after this attempt. No publication.

## Handback

6/6, 20/20 full audit in 368.772596037s. Zero charged backup attempts.
Processing health3690 pass/0fail/0unknown, maximum gap0.119757825s.
Explicit fallback mode off. New completion telemetry present, interpretation
review pending. Source hashes match the frozen runtime checkout. Profile/player/
course/mission unchanged. Shutdown, port/player absence and exclusive lease probe
verified. Raw artifacts: artifacts/iterations/2026-10-05/replacement-control-1.
Sonnet/Sol evidence reviews accepted. One control pass, no promotion/speed claim.

## Log

### 2026-10-05T04:51:13.578594-07:00 · gpt-6-astra → all · NOTE
Prepared only. Launch after combined checks pass and explicit grant recorded.

### 2026-10-05T04:52:12.506981-07:00 · gpt-6-astra → all · DISPATCH
Grant ONE default-off managed trial now. Frozen worktree clean at0f76a2a,
player assembly6564e85476866ef0b2d1b0a8954af7ae81280b177cb7cef8b5da50d906b429c7.
Combined checks complete; T0023 isolated light edits may overlap, no heavy tests.
Keep source/profile fixed; record cleanup and every outcome without retry.

### 2026-10-05T05:00:22.398239-07:00 · gpt-6-astra → all · HANDBACK
Managed control lap and audit passed; telemetry collected. Keep source at0f76a2a
for a separately granted enabled comparison after T0023 tests finish. No enabled
fallback performance evidence from this OFF run. Independent evidence review now.

### 2026-10-05T05:04:45.641208-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW
relayed-from: artifacts/agents/T-0024/sonnet-review-r1.md

**Verdict: Approve**, as a single OFF-mode control run with the scope below. Everything here comes from the compact summary, not raw logs, so none of it is independent raw verification.

**What the data supports**
- Status is completed, 6/6 destinations, 368.77 s, mission and audit exit 0. All 20 audit checks are present and true, and course and mission hashes match their expected values.
- Health: 3690 pass, 0 fail, 0 unknown, max gap 0.1198 s. This covers lane/depth processing booleans over the armed interval only, not perception quality.
- All 18 listed runtime hashes match the launch snapshot. The commit field is 0f76a2a. Only `sensor_course.py`, `mission_completion.py` and `replacement_path.py` differ from T0020, and the latter two are new.
- Fallback OFF: evaluated 0, sent 0, with `recovery_budget` at 0 attempts and 0 episodes cleared.

**Wording to tighten**
- **Zero charged backups:** state that it rests on `recovery_budget` (0 attempts, 0 episodes), not on `recoveries`. That field is `null`, meaning absent, and must not be read as an empty list.
- **Shutdown:** `shutdown_verified: true` is all the summary shows. The independent players/port/lease check is the root's own statement and isn't in this data. Attribute it as such.
- **Identical profile/player/course/mission vs T0020:** this summary has no T0020 profile or player hashes. Course and mission matches are shown against expected values only.
- **Final arrival:** 0.3924 m against a 0.4 m radius leaves a 7.6 mm margin. Say "arrived within radius", not "comfortably".
- **Zero movement after arrival:** the odom stamp never advances (376.76) across the ~40.5 ms cleanup. Zero new samples is therefore expected, and `moved_m: 0.0` is not evidence of stationarity. The 64 retained loop samples are only the tail of 75,979.
- **Environment:** the rendered Unity / WSL ROS Jazzy / Nav2 claims are not in this data. Attribute them to the root.

**Remains unknown**
- Run-to-run variance (n=1) and the effect of uncontrolled load.
- Any speed causality or promotion effect.
- Whether the replacement fallback works when enabled. This run never exercised `replacement_path`, so it validates only that the new code is inert in OFF mode.
- Physical stopping, and perception accuracy beyond the health booleans.
### 2026-10-05T05:04:45.641208-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
relayed-from: artifacts/agents/T-0024/sol-review-r1.md

### 2026-10-05T05:03:05.8287142-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0024. Candidate/launch: 0f76a2ac6090de0cf83c8f57bd471874dbffe552. Scope: evidence.
Verdict: approve.

Findings: none within this bounded review.

Bindings: clean frozen HEAD matches launcher/live. Run SHA256 d31e3a1ad4489895cae341be6707961c02b689647edde1c008add72d4d29e2a4 matches audit/compact report. All 18 raw runtime fingerprints match running checkout; profile/course/mission hashes match manifests and prior trial bytes. Actual player assembly matches recorded 6564e854…; dedicated t0024-control overlay record reports matching installed perception sources.

Results: 6/6 in 368.772596 s under 600 s; full audit 20/20 over 18,438 samples. Return 0.392415454 m leaves 7.585 mm margin; conservative swept clearance 0.109986430 m, zero collision poses. Sampled processing-health coverage is complete: 3,690 pass, zero fail/unknown, maximum gap 0.119758 s below 0.25 s. Recovery budget records zero charged attempts; absent recovery list remains unavailable. Learned scorers disabled.

Completion: six arrivals, 64 retained loop evaluations, five successful cleanup phases, no recorder errors/dropped phases. Final arrival and endpoint both reference index 18437, stamp 376.76 and distance 0.392415454 m; endpoint matches audit and last trajectory row. Cleanup receipt age grows to 40.55 ms with no new odometry/index. Reported zero movement/extra samples describes recorded endpoints only. Retained loop evaluations span 0.207271 s and 14 odometry stamps; loop_dt is not sensor sampling period or a universal arrival bound.

Control boundary: explicit config false, fallback mode off, evaluated 0, sent 0, no fallback events. This validates off-mode normal-path telemetry, not enabled continuity benefit.

Cleanup independently confirmed: no player/listener; exclusive lease read-open available. Invariants retained; no speed, physical-stopping or promotion claim. Checks: bounded read/hash/cleanup only. Missing coverage: enabled execution, failure instrumentation, repeatability/held-out gates. Usage: UNMETERED.

### 2026-10-05T05:04:45.641208-07:00 · gpt-6-astra → all · DECISION
Both reviews accept the passing control evidence. Source0f76a2a, one run, no
promotion. Sol independently verified raw bindings and cleanup; Sonnet reviewed
only compact interpretation (USD0.0491774 API-equivalent). Sol UNMETERED.
All numerical limits unchanged; the zero charged backup figure comes from budget.
Completion recorder's live normal path is validated. No subsequent odometry sample
during40.55ms cleanup means endpoint equality, not proof of physical stopping.
Return margin7.585mm. Enabled fallback remains untested. Ledger row appended.
