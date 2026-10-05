---
id: T-0027
title: Exercise reviewed recovery evidence in one unchanged-policy live trial
status: integrated
priority: P1
owner: gpt-6-astra
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0027-recovery-instrumented
base: f1a6ae4ceb0a146b53b5ea7d9e83da472ceb391f
candidate: f1a6ae4ceb0a146b53b5ea7d9e83da472ceb391f
claim: audit-passed
lease: released
updated: 2026-10-05
---

# T-0027: One instrumented live trial

## Packet

- Frozen runtime checkout C:/Users/brand/.codex/worktrees/igvc-t0008-mouth-handoff/IGVC SIM
  at f1a6ae4ceb0a146b53b5ea7d9e83da472ceb391f. Integrator owns it and the reused t0024-control ROS overlay.
  No edits during live. Same player/profile/course/mission as T0024/T0025.
- Wait for the one combined integration check to pass and explicit dispatch.
  Managed hidden rendered Unity + native WSL ROS 2 Jazzy/Nav2, exclusive port
  10000/domain42 lease. No RViz, Docker, Unity build, replay or heavy local tests
  while live. No interrupting other sessions.
- One attempt, no retry: seed2027, requested speed0.6, planning budget0.5,
  clearance weight3, checked-path RPP, six broad GPS goals, learned scorers off,
  replacement revalidation OFF. Mission600s/build10min/start3min/audit3min bounds.
- This is instrumentation, not a recovery policy fix. Preserve any failure.
  If recovery refusal recurs, inspect recovery_failures, submitted/worker/capture
  digests, bounded stage/terminal records and the exact captured inputs. Check
  deferred writer timing and cleanup phase/health interval; no live-wire or
  successful capture claim if that branch never executes.
- If capture is unavailable or mismatched, say so. No retrospective attribution
  of T0020/T0025 from this different run. A timed replay need not return identically.
- Full independent audit, health coverage, source hashes, charged backups and
  cleanup verification remain required. Runtime may read observations plus
  sanitized autonomy.json only; course geometry belongs solely to rendering/audit.
- Append ledger with all outcomes. One Sonnet interpretation and one Sol raw
  evidence review <=10min/$5 each. Stop after this one attempt; no publishing,
  promotion, threshold relaxation or implicit second trial.
- Artifacts: artifacts/iterations/2026-10-05/recovery-instrumented-1.
- Knowledge: sensor-led-navigation; trial-audit-promotion; processing-health.

## Handback

Accepted first audited pass at this source; see evidence and reviews below.

## Log

### 2026-10-05T05:30:52.955151-07:00 · gpt-6-astra → all · NOTE
Prepared only. Combined integration checks are still running; no live launch yet.

### 2026-10-05T05:33:30.385245-07:00 · gpt-6-astra → all · DISPATCH
Integrated source at f1a6ae4ceb0a146b53b5ea7d9e83da472ceb391f.
Validation covers 630 distinct tests: 541 tools +85 perception +4 GPS.
The initial tools run passed 540 and failed only generated-board freshness after
the coordinator added T0027. Regenerated board; its5-test suite passed. No source
test failed. Two manually assembled remaining-suite commands lost ROS Python
imports; preserved remaining-checks.log/-r2.log. A saved helper based on check_core
preserved the environment and passed board5/perception85/GPS4.
Knowledge check then caught a malformed new log heading; corrected it and the
strict check passed8concepts/0errors/0warnings. These are staged validation results,
not one uninterrupted clean check_core invocation. Original failures are retained.
No live validation yet. All motion/audit parameters are unchanged.

Grant the single trial now after this final board refresh/check. No other tests,
replay or source edits in its checkout while live. Opus is idle after handback.

### 2026-10-05T05:41:50.947425-07:00 · gpt-6-astra → all · HANDBACK
6/6 and20/20 audit checks in364.386478s; zero charged backups. Health3646/0/0,
complete coverage, maxgap0.154392s. All19source hashes match frozencheckout.
Same player/profile/course/mission asT0024/T0025. Fallback off. No recovery failure
record, so failed-input capture/deferred-write live branch remains unexercised.
Return0.394471883m; first same-version pass only, no speed/fix/promotion claim.
Runner shutdown verified; root independently found no player/listener and acquired/
released the lease. Ledger appended. Independent reviews pending.

### 2026-10-05T05:44:46.509854-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW
relayed-from: artifacts/agents/T-0027/sonnet-review-r1.md

**Verdict:** the evidence supports a narrow claim: one clean, first-pass completion on f1a6ae4 under ideal-fixture conditions. It supports nothing broader.

**What validates**
- **Completion:** 6/6 destinations, 364.386 s, and all 20 audit checks pass. The audit has independent course and mission hash matches, swept and paint clearance, ordered visits, and ramp containment.
- **Return:** 0.394472 m against the 0.4 m bound, a 5.528 mm margin. It passes, but barely, so call it "inside bound" rather than "good return."
- **Health:** 3646 pass, 0 fail, 0 unknown. The max gap including bounds is 0.1544 s, and the interval covers armed motion (sim 7.0 to 371.4 s).
- **Recovery:** the budget shows 0 attempts and 0 episodes, so zero charged backups is affirmative. Fallback is off, with 0 evaluated and 0 sent.
- **Cleanup:** all five phases report ok, and `capture_analysis` has no failures.
- **Code identity:** 19/19 runtime hashes match the launch.

**What does not validate**
- **Deferred capture:** the live branch was never exercised. The new f1a6ae4 failure-diagnostics and cleanup-guard path is therefore untested live. Cleanup success only corroborates ordering. The limitations say deferred-after-health ordering is source-reviewed, not scheduler-traced.
- **Causality:** no speed, fix, or promotion claim. The control run (0f76a2a, 368.77 s) is a different commit, and a 4.4 s difference from a single pair is not evidence. Three source files changed from T0024, so "same source" is only approximately true.
- **Health scope:** these are sampled lane/depth Bool checks. They do not show perception accuracy, raw-stream quality, or continuous physical health.
- **Hardware:** this is an ideal fixture, not calibrated hardware.
- **Independence:** `shutdown_verified` is runner-reported. Only root's separate player/port/lease checks make it independent, and the compact input does not.

**Discrepancies to resolve**
- `recoveries` and `recovery_failures` are `null`, not empty. That means absent, not zero. Rely on `recovery_budget` for the zero count.
- `health.max_gap_s` reads 0.25, while the observed gap is 0.1544 s. Verify that 0.25 is the configured limit and not a measurement.
- The capture limitations say "No attribution of this failure," but there was no failure. Reword it, since it looks like boilerplate left over from a failure template.

**Recommendation:** record it as "first pass on this commit, earlier failures retained." Exercising the deferred-capture branch needs a separate trial that induces a failed backup.

### 2026-10-05T05:44:46.509854-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
relayed-from: artifacts/agents/T-0027/sol-review-r1.md

### 2026-10-05T05:42:29-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0027   Candidate: f1a6ae4ceb0a146b53b5ea7d9e83da472ceb391f   Scope: evidence
Verdict: approve

Findings (ranked, ≤ 5):
1. No material evidence blocker. This is the first passing trial on this source; the failed-recovery instrumentation remains unexercised live. Neither recovery_failures nor recoveries exists; there are no recovery-search/guidance/failure events or recovery capture files. Zero charged backups is independently supported by recovery_budget.total_attempts = 0, not inferred solely from missing lists.
2. Return margin is narrow: final recorded pose independently yields 0.394471883m, approximately 5.53mm inside the unchanged 0.4m bound. This is an audited sampled endpoint, not proof of continuous physical stopping precision.

Run SHA256 057b7662370e2ebe320c697295bfd478b62300ecfbc60e68009cf942eb6c7843 matches audit.run_sha256. Audit passes all 20 checks over all 18,221 recorded samples; completion is 6/6 in 364.386478s. No collision poses; conservative swept clearance lower bound 0.163087777m.

Health ledger, diagnosis and audit agree: 3,646 pass/0 fail/0 unknown, complete coverage, maximum gap including interval boundaries 0.154391915s < 0.25s, no integrity errors.

All 19 raw source hashes match the clean frozen workspace; normalized bytes match exact launch blobs. Versus T0024/T0025, only sensor_course/recovery_policy fingerprints changed and recovery_evidence was added. Profile/course/mission bytes and actual player assembly match both controls. Fallback is off with zero evaluated/sent; learned scorers are absent.

Successful cleanup phases, runner shutdown_verified and stop log are corroborated by no player/10000 listener and available exclusive lease.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓.
Tests run: none (read-only JSON/hash checks).
Missing acceptance coverage: live failed-input binding/deferred writing, repeatability and controlled-load comparison. No speed-causality, fix or promotion claim. Usage: UNMETERED.


### 2026-10-05T05:44:46.509854-07:00 · gpt-6-astra → all · DECISION
Accept one audited passing run on f1a6ae4. Sonnet USD0.1409254 API-equivalent;
Sol UNMETERED. The0.25s max_gap_s is the configured limit (mission_health.py),
not the observed0.154392s gap. Absent recovery lists are not asserted empty;
zero charged attempts comes from the budget and no recovery events were found.
Corrected failure-specific boilerplate in the derived capture-analysis template;
raw run/audit unchanged. No failed capture branch executed. No fix, speed or
promotion claim. Return margin remains5.53mm. Proceed to the separately bounded
same-version repeat T0028; do not count earlier source versions toward its streak.
