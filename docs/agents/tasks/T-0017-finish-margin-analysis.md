---
id: T-0017
title: Explain finish margin and propose bounded observed-only completion improvement
status: rejected
priority: P2
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/transport-probe
base: a0a3d49ae465ef2176ce4bdb910257fc76c6ccb7
candidate: a0a3d49ae465ef2176ce4bdb910257fc76c6ccb7
claim: tested
lease: none
updated: 2026-10-05
---

# T-0017: Finish margin analysis

## Packet

- Existing interactive Claude Opus5.5 session owns this bounded read-only analysis. No source worktree/implementation assignment yet. User authorizes overnight improvements; integrator is running T0016 with unchanged profile.
- Read README, knowledge sensor-led-navigation and trial-audit-promotion, this packet. Inputs frozen under primary artifacts/agents/T-0017/inputs with manifest hashes. Source read-only primary at a0a3d49: sensor_course.py and directly relevant observed_navigation/mission destination logic; inspect limited portions as necessary. No other full logs/binary inputs.
- Problem: T0009 return0.384816m and T0010 return0.398244m leave little room under unchanged independent0.4m audit threshold. Identify exact operational completion condition, cancellation/stop sequence and evidence limits. Distinguish coordinate/localization basis and overshoot from mere threshold choice. Frozen compact evidence is summaries, not full trajectory; do not infer unsupported causality.
- Deliver concise diagnosis and smallest behavior-testable candidate proposal; no runtime course/world inputs, no threshold weakening, no reverse/turnaround promotion or safety change. If simplest approach is an internal stricter arrival margin, justify how it can terminate under forward-only geometry and distinguish final destination from other GPS handoffs. Do not implement yet.
- During live lease: only light read-only file inspection and remote reasoning. NO replay, tests, shell loops, builds, source edits, model delegates or heavy local computation. Primary artifact report plus append-only task messages allowed. Source hash checks only after lease release if needed.
- Owned outputs artifacts/agents/T-0017/REPORT.md, review-inputs.md and append-only this task log. <=20min, max3focused reads. Return <=300word handback with findings and evidence limits; stop. No recursive delegation, provider retries, live launch or Git source commits.

## Handback

Read-only analysis by claude-opus-5-5. Report: artifacts/agents/T-0017/REPORT.md.

```text
Diagnosis: the mission's stop line IS the audit's pass line. sensor_course.py (a0a3d49, ~L433) completes a destination
  on the first ~0.05 s loop iteration where hypot(goal-pose) <= radius. The final return goal radius_m is 0.4 (others
  2.0; the loader forbids <0.4), and the final destination breaks to completed and cancels. At 0.6 m/s the stop lands
  in ~(0.34, 0.40] m: T-0009 pose (-0.339,0.182) gives 0.3848; T-0010 (0.398,-0.017) gives 0.3982 (both equal the audit).
  The sim's mission and auditor use the same ideal odom basis, so this is not a localization error.
Both laps were still approaching. Straight-line closest approach from the final pose is ~0.163 m (T-0009) and ~0.017 m
  (T-0010). This is an inference; the planned path may curve.
Proposal (not implemented, sensor_course.py only, final destination only): on entering 0.4 m, if
  along=dot(goal-pos, heading) <= eps, stop now (today's behavior). Else continue on the existing checked forward path
  until d <= 0.25 m, or d stops decreasing, or a min(along+0.1, 0.6) m / time cap. Forward-only termination is
  guaranteed by the caps. No reverse/turnaround, threshold, radius, audit or world-input change; intermediate 2.0 m
  handoffs unchanged. Optional separate experiment: a final-approach speed cap. Behavior tests: straight approach,
  heading away (unchanged), curving (first increase), long tangent (caps), intermediate unchanged.
Limits: no full trajectory or measured loop period in inputs; post-cancel motion unrecorded; worst case on a sharply
  curving path is about one step beyond the entry distance unless tests bound it; manifest hashes deferred until after
  the lease. 3 reads. No source edits or live work. UNMETERED.
```

## Log

### 2026-10-05T03:57:58.626286-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
Explicit bounded light-analysis assignment, no source changes. Existing interactive session only; T0016 currently owns live simulator. Read frozen packet and report within20min; finish margin analysis may proceed alongside measured lap, no replay/tests/builds. Await separate assignment before implementation.

### 2026-10-05T03:58:14-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
DISPATCH received. claude-opus-5-5, the same interactive session. Read-only light inspection only while T-0016 holds the lease (no replay,
tests, loops or builds; hash checks deferred until after release). Max 3 focused reads, 20 min. Owned: T-0017 REPORT and review-inputs.

### 2026-10-05T04:00:09-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
Analysis complete; see the Handback section and artifacts/agents/T-0017/REPORT.md. Root cause: the final destination radius_m 0.4
equals the audit threshold, and the mission stops on the first ~0.05 s check inside it, so returns land in ~(0.34, 0.40].
Both laps were still approaching. Proposal: final-destination-only closest-approach arrival with caps (not implemented).
3 reads. No compute during the lease. Manifest hashes deferred. Stopping.

### 2026-10-05T04:05:37-07:00 · claude-opus-5-5 → gpt-6-astra · NOTE
After the T-0016 lease release, the deferred input verification is done: t0009-evidence.json (cad62cd0...) and t0010-evidence.json (695e0725...)
both match manifest.json. No change to findings.


### 2026-10-05T04:11:53.484766-07:00 · gpt-6-astra → all · REVIEW
relayed-from: artifacts/agents/T-0017/sonnet-review-r1.md

**Verdict: request-changes.** The diagnosis is mostly supported. The proposal is not defensible as written.

**Ranked findings**

1. **The proposal can turn a pass into a fail.** Today the stop fires on the first sample at or under 0.4 m, and the audit presumably sees that same pose, so a pass is guaranteed by construction. Continuing after entry adds a path to failure. The recorded margins are only ~0.015 m (T-0009) and ~0.002 m (T-0010). Under curvature, one non-decreasing step, or cancel latency, can push the end above 0.4 m. `along > 0` at entry doesn't prevent that, and forward-only motion can't undo it. "Tests must bound this" is not enough. Both laps already pass, so the proposal fixes no demonstrated failure.

2. **Illustration versus bound.** The "(0.34, 0.40]" window and the 0.05 s period are illustrations. `spin(.05)` plus per-iteration work gives an unmeasured period, and the report concedes this. The 0.6 m/s figure is assumed, since the source caps speed only at `min(args.speed, max_speed, 2.2)`. Faster runs, which the user wants, enlarge the step. The straight-line closest approaches are inference only. I recomputed 0.163 m, but T-0010 comes to ~0.020 m, not 0.017 m, which is immaterial.

3. **Audit-recorded end versus physical stop.** After the `break`, cleanup disables autonomy and cancels the action, so the robot keeps moving. `health_trajectory_end_index` is set after cleanup. It's unclear whether the audited pose is the break pose or a later one. This is unresolved, and the whole case depends on it.

4. **Unresolved failure cases:**
   - Curved paths that increase distance after entry.
   - Cancel and decel latency.
   - Whether Nav2's goal already sits at the destination, which would make the extension redundant.
   - Early stop from odom noise.
   - Higher speeds.
   - The `len(goals)-1` gating.
   - The 0.4 radius and loader L68 aren't in the supplied source, so I treat them as the report's claim.

**Smallest next experiment (instrumentation only, no behavior change)**

After the lease is released, on the next lap(s) at the target speed, log:
- Loop dt.
- Per-iteration distance to the final goal from 1 m out.
- The break pose.
- Poses through ~2 s after cancel.
- Which pose the audit judges.

Propose a behavior change only if the data show the audited distance exceeds 0.4 m, or that the overshoot grows with speed. Otherwise leave the stop line alone.

### 2026-10-05T04:11:53.484766-07:00 · gpt-6-astra → all · REVIEW
relayed-from: artifacts/agents/T-0017/sol-review-r1.md

### 2026-10-05T04:08:56.3913341-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0017. Source: a0a3d49ae465ef2176ce4bdb910257fc76c6ccb7. Scope: evidence; no implementation candidate.
Verdict: request-changes.

Findings:
1. Major: REPORT's assertion that post-cancel motion is unrecorded is too broad. Source emits mission_end, disables autonomy and waits for cancellation before setting health_trajectory_end_index. Frozen cancellation records contain later poses. The audited endpoint is the last recorded pose, not proven identical to the radius-check/break pose. Qualify this ordering and retain uncertainty about motion after recording ends.
2. Major: proposed forward continuation can leave the passing 0.4 m region before a non-decreasing sample or cancellation is observed. Positive heading projection and travel/time caps guarantee bounded termination, not a passing endpoint. Do not implement this proposal from current evidence.
3. Minor: the stated (0.34,0.40] stopping window is not an observed or derived bound. spin(.05) plus work/cancellation has unmeasured timing; straight closest-approach estimates assume future constant heading.

Observations: both frozen evidence hashes match their manifest. Source verifies radius completion via hypot(goal-pose), final-destination break, loader minimum 0.4 m, and cleanup ordering. Mission radii are five 2.0 m goals plus final 0.4 m. Recorded audit distances 0.384816084 and 0.398243889 support narrow margins, not a demonstrated completion failure or exclusive causal/localization diagnosis.

Invariants: no source, threshold, audit, policy, sensor or lease change. Original T0010 failed audit remains preserved; subsequent auditor correction is separate evidence.

Checks: light source/frozen-hash and recorded endpoint inspection, Sonnet critique; no replay/tests/live. Missing acceptance coverage: break pose, measured loop timing, cancellation/deceleration poses and final audited sample correspondence. Close with qualified diagnosis; instrumentation is justified, behavior change deferred. Usage: UNMETERED.

### 2026-10-05T04:11:53.484766-07:00 · gpt-6-astra → all · DECISION
Reject the proposed forward-continuation behavior. Retain qualified finding that
mission radius equals the audit radius, leaving narrow recorded margins. The
(.34,.40] interval is illustrative, not a measured bound; localization causality is
not established. Cleanup callbacks continue recording before the final health
index, so the claim that all post-cancel motion is unrecorded is incorrect.
Original report is retained with this correction. Sonnet actual model verified,
API-equivalent USD0.0804394; Sol UNMETERED. T0019 is the separate instrument-only
development task. No further report-only revision or behavior change requested.
