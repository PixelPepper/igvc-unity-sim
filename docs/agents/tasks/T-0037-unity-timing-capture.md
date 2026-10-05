---
id: T-0037
title: Capture bounded Unity frame and connector warning timing
status: integrated
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0037-unity-timing-capture
base: 0779593c8b077da4c8b47c5a497c47b6dc29df93
candidate: ccee5bccba857d6f0046f4085d110cee18889061
claim: tested
lease: none
updated: 2026-10-05
---

# T-0037: Observe production cadence before changing runtime behavior

## Packet

- Read README, this packet and revised PRIMARY artifacts/agents/T-0036/REPORT.md.
  First2029 failed2/6 on freshness; producer versus delivery versus subscriber
  scheduling cause remains unknown. Original failure remains authoritative.
- Your clean worker is C:/Users/brand/.codex/worktrees/igvc-t0005-health-capture/IGVC SIM,
  now branch codex/t0037-unity-timing-capture at0779593. T0036 diagnostic commit is
  independently reviewed; do not alter it or its files. No live session or lease.
- Implement a small OPT-IN Unity companion that logs bounded, timestamped frame
  cadence and connector queue-warning observations. Purpose: establish whether
  a future ROS freshness failure coincides with a Unity frame gap; do not claim
  it establishes every transport cause. No navigation/publisher/physics changes.
- Owned paths only: new unity/IGVCSim/Assets/IGVC/Runtime/TransportTimingTrace.cs,
  TransportTimingWindow.cs if a small pure helper is justified, their .meta files,
  new Editor/TransportTimingChecks.cs plus .meta. No package/dependency edits,
  reflection into connector internals, scene/prefab edits, or shared ROS interfaces.
  Integrator owns the eventual explicit one-line TransportProbe hookup and builds.
  Return the proposed hookup in PRIMARY artifacts/agents/T-0037/integration.md.
- Suggested contract: explicit Initialize(TransportProbe, ROSConnection) on a
  component created ONLY when opt-in enabled. Cache references, no searches per
  frame, no static mutable state or automatic scene injection. Balanced callback
  subscribe/unsubscribe; idempotent init/enable handling. No new ROS topics.
- Every Update sample a monotonic wall clock, frame gap, cumulative/window max,
  frame count and probe SimTime. Emit at most one compact JSON Debug.Log record
  per wall second, including UTC timestamp and monotonic source/frequency/origin
  so clocks can be correlated with stated uncertainty. Do not emit per-frame
  logs or allocate/serialize every frame. Preserve max frame gaps across reporting
  boundaries; cap total records (e.g.1200), label exhaustion, cleanly stop tracing.
- Application.logMessageReceivedThreaded can observe the existing exact queue-full
  warning. Callback may ONLY update bounded thread-safe counters/timestamps; never
  call Unity APIs, log recursively, allocate unbounded lists or mutate motion.
  Aggregate into next bounded record. Label warning observation time, not the time
  a particular message dropped. Connector warnings occur while dequeuing overflow
  counters, and prior runs have untimestamped startup warnings even when passing.
- Pinned package local reference: Library/PackageCache/com.unity.robotics.ros-tcp-connector@bdad6c87bd9e
  (read-only if available). Actual queue depth is not public; QueueSize is CAPACITY.
  LastMessageSentRealtime is updated on enqueue, not proof of socket delivery.
  Do not report either as wire send time or actual backlog. Queue depth unavailable
  is acceptable. Record connection status descriptively, without altering it.
- Use repository Editor *Checks.Run style for meaningful deterministic cadence,
  frame-hitch retention, zero/paused sim time, bounded warning aggregation,
  record-cap and lifecycle behavior where testable. Worker may run <=3 focused
  offline commands with installed tools, NO Unity editor/player/build. Integrator
  performs Unity compilation/checks then later separately grants a live capture.
  Missing Unity execution must be reported, not replaced by fabricated success.
- Follow Unity feature implementation lifecycle/performance/test guidance:
  explicit initialization, cache references, bounded hot-path allocations,
  balanced events and disable/cleanup, pure deterministic tests where useful.
- Budget25min active, at most2 revisions, no other models/provider/live tasks.
  Choose implementation details autonomously inside this scope. No safety/audit
  threshold changes, no course/mission geometry, no seed generation, no publishing.
  Hand back clean source-only commit, files, evidence and limitations <=300words
  in this canonical task, artifacts in PRIMARY artifacts/agents/T-0037/. Stop for
  review. Measured overhead and actual cause remain unverified until a live trial.

## Log

### 2026-10-05T07:46:00-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

Start the bounded opt-in capture companion. Runtime is stopped; offline work can
proceed. No package/library modifications or Unity builds. Existing diagnostic
review runs independently against immutable0779593 and must not be disturbed.

### 2026-10-05T07:45:42-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
T-0037 accepted on codex/t0037-unity-timing-capture at 0779593. Opt-in Unity timing companion plus pure checks; no Unity execution available to me.

### 2026-10-05T07:47:09.9132265-07:00 · gpt-6-astra → all · NOTE

Dispatch timestamp was rounded ahead by about20seconds; ACK07:45:42 confirms actual start. T0036 integrated asb1aada7 with36 focused checks; workerbase0779593 is its equivalent source. T0037 remains offline-only; no lease granted.

### 2026-10-05T07:49:01-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
Candidate f9f80be5a8fccf6413892e4a62f31f86b2385750 (base 0779593; 6 files +321: TransportTimingWindow.cs, TransportTimingTrace.cs, Editor/TransportTimingChecks.cs plus 3 .meta files with unique GUIDs).
- Opt-in, observe-only. Explicit idempotent Initialize(TransportProbe, ROSConnection), cached references, balanced
  OnEnable/OnDisable/OnDestroy log-callback subscription.
- The threaded callback only counts the exact queue-full warning prefix (Interlocked, no Unity API, no allocation,
  no logging).
- Update: one Stopwatch read and one pure-window sample; at most one compact JSON Debug.Log per wall second.
- Records: a header with Stopwatch source, frequency, origin and semantics. Then window records: frames, window and
  cumulative max frame gap (a hitch is kept across boundaries), sim span, warning delta, total and observation time,
  connection_error.
- Cap of 1200 with a labelled exhausted record, then it stops and unsubscribes. Queue depth is reported unavailable.
- No navigation, publisher, physics, topic, scene, package or connection change, and no hookup.
Proposed one-line hookup and verification steps: artifacts/agents/T-0037/integration.md.
Evidence: 2 offline commands. The real pure helper and Checks compiled with .NET SDK 10 and a Debug stub:
15/15 checks passed, and all records parse as single-line JSON (artifacts/agents/T-0037/harness).
Unverified, needs Unity: TransportTimingTrace compile and lifecycle, the Editor Run, the player on/off smoke test,
overhead, and any 2029 cause. Report: artifacts/agents/T-0037/REPORT.md. Stopping for review.

### 2026-10-05T07:51:38.7441385-07:00 · gpt-6-astra → all · VALIDATION

Candidatef9f80be source applied provisionally to primary for validation, not accepted/committed yet. Root added explicit IGVC_TRANSPORT_TIMING_TRACE=1 environment opt-in in TransportProbe.Start; default creates no component. Hidden Unity6000.3.23f1 compile and15 pure Editor checks launched under exclusive simulator lease, ten-minute bound, no player/build/mission. Evidence artifacts/agents/T-0037/unity-check*. Source/hook will receive independent review before integration.


### 2026-10-05T07:53:43.4673875-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0037/sonnet-review-r1.md

**Verdict: accept with changes.** The default-off design is safe: no component unless `IGVC_TRANSPORT_TIMING_TRACE=1`, with no scene, publisher, physics or policy changes. Fix items 1-3 before logs are treated as evidence. I reviewed the pasted diffs only and could not confirm that `f9f80be` matches them.

**Ranked findings**

1. **Disable/enable gaps are misreported (medium-high).**
   - A disabled interval has no `Update`, so re-enabling records it as a frame gap and pollutes `cumulative_max_frame_gap_s` permanently.
   - `OnDisable` also unsubscribes, so warnings during that interval are never counted, yet records still show `0`.
   - Fix: keep the subscription until destroy or exhaustion, add a `Discontinuity()` that resets `lastFrame`, and emit a `resumed` flag.

2. **Clock correlation uncertainty is claimed but not recorded (medium).**
   - The header's `DateTime.UtcNow` is read after `originTicks`, in a separate expression.
   - `UtcNow` can be coarse on Mono/Windows and can step.
   - Fix: bracket each `UtcNow` read with two Stopwatch reads and log both, in the header and per record.
   - `"R"` prints 17 digits, which implies false precision.
   - Cross-machine offset to ROS-side logs is not covered, so say so in the header.

3. **Zero warnings is ambiguous, and the cap limits coverage (medium).**
   - A connector text change makes the prefix match silently count zero. Record the prefix in the header and state that zero does not prove no drops.
   - The counts are log lines, not drops.
   - The hook uses the default cap, about 20 minutes at 1 s. A later failure would be missed, so document the capture window or add an env override.

4. **Threaded counter coherence (low).**
   - The count and the timestamp are separate atomics, so a delta can pair with a timestamp that is one warning off. That is acceptable at ms scale, but document it.
   - `last_queue_full_observed_mono_s` is cumulative, so it repeats in windows with a delta of 0. Rename it or null it out for those windows.

5. **Sim time and mono time (low).**
   - `Update` order against `TransportProbe` is undefined, so `SimTime` may lag by a frame. Document it.
   - A record is emitted only after a hitch ends, and its own `Debug.Log` can cause a hitch.

6. **Hook (low).**
   - It is correct as written. Guard against a duplicate `AddComponent` with `GetComponent`.
   - Confirm that Initialize really runs before Connect.
   - `TransportProbe.cs` is already modified in the working tree, so check that the change is only this hook.

7. **Callback safety, CPU and allocations: fine.** The callback uses an ordinal prefix check and `Interlocked` only, with no Unity API and no allocation. Per frame there is no allocation, and per second there are only a few small strings.

8. **Tests (low).** The `"0.91"` substring checks are loose. Nothing covers disable/enable or the `TransportTimingTrace` class, and Unity compile and lifecycle checks are still pending.

No causal claim is made, and the prior 2029 failure (2/6 freshness) is preserved.

relayed-from: artifacts/agents/T-0037/sol-review-r1.md

### 2026-10-05T14:51:50+00:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0037   Candidate: f9f80be5a8fccf6413892e4a62f31f86b2385750   Scope: evidence
Verdict: approve-with-nits

Findings (ranked, ≤ 5):
1. [minor] unity/IGVCSim/Assets/IGVC/Runtime/TransportTimingTrace.cs:68: Warning count and timestamp updates, and their reads, are separate. A callback between reads can associate a newer count with an older timestamp; observation time can also exceed the preceding frame sample's mono_s. Qualify their association as asynchronous, not an atomic window snapshot. No drop-time or wire-delivery inference follows.
2. [nit] artifacts/agents/T-0037/integration.md:11: Proposed CLI opt-in differs from the coordinator's env-only IGVC_TRANSPORT_TIMING_TRACE=1 plan. Update instructions when integrating; this candidate contains no hookup.

Evidence: Clean exact candidate; base-to-candidate range adds only three owned sources and their .meta files (+321). Harness project directly includes candidate helper/check sources and its Debug stub, excluding the Unity wrapper. Inspected 14 meaningful helper checks plus harness JSON parsing, consistent with the reported 15; execution was not independently repeated. Header records Stopwatch origin/frequency and UTC emission semantics; frame gaps survive reporting boundaries, and the 1200-record cap includes header/exhaustion. Queue warnings are labeled observation counts, queue depth unavailable, enqueue distinct from wire delivery. Independently inspected the pinned connector warning prefix/public connection status. No policy, course geometry, publisher or audit changes.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓.
Tests run: none (read-only source, harness and provenance inspection).
Missing acceptance coverage: Unity wrapper compilation, lifecycle/threaded callback behavior, Editor checks, integrated default-off/on smoke, overhead and clock-correlation uncertainty remain pending. Helper tests establish no live timing, 2029 cause, runtime benefit or promotion.
Usage: UNMETERED.


### 2026-10-05T07:53:43.4673875-07:00 · gpt-6-astra → claude-opus-5-5 · REVISION

Revise your owned source on current branch; root's primary copies are provisional only, no integration yet. Address Sonnet1-3 before logs become evidence: handle disable/re-enable coverage explicitly so suspension is never classified as a frame hitch; bracket UTC reads with monotonic samples and state remaining wall-clock resolution/steps plus no cross-host synchronization guarantee; record exact warning prefix, count/log-observation semantics, zero-not-proof and cap coverage. Choose minimal lifecycle behavior yourself (permanent tracing stop on disable is also valid if explicit, rather than complex resume). No need to count callbacks while disabled if unavailable coverage is stated. Document asynchronous count/timestamp association and cumulative last-warning time; no implied exact-window attribution. Keep bounded allocation/no recursive logs/no Unity API on background callback. Raw floating precision is encoding, not measurement accuracy: document, no need arbitrary rounding. Hook runs once in Start so duplicate guard is optional, not required. Root hookup is ENV-ONLY IGVC_TRANSPORT_TIMING_TRACE=1; synchronize integration.md. Source15 claim actually14 core checks +1 JSONparse; correct labels. Add focused tests for lifecycle discontinuity model and UTC bracket fields/clock semantics. Up to15min active/3 focused offline commands, no Unity/live/build. Clean new commit and updated report. Preserve r0 report/review/harness evidence. No policy change.

Root validation before revision: Unity6000.3.23f1 compiled wrapper and root hook; TransportTimingChecks.Run14 PASS, exit0, no C# error/warning or exception. artifacts/agents/T-0037/unity-check-status.json and unity-check.log. No lifecycle/player test yet. Editor process ended and exclusive lease independently available. Sonnet usage0.1156714USD API-equivalent; Sol UNMETERED.

### 2026-10-05T07:56:25-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
Revision 1: candidate ccee5bccba857d6f0046f4085d110cee18889061 (parent f9f80be; 3 owned sources, +176/-77; .meta unchanged).
- Lifecycle: disable or destroy ends coverage permanently. It unsubscribes, then logs one "stopped" record with the
  partial window; nothing is sampled after, so a suspension is never a frame gap.
- Clock: every UTC read is bracketed by monotonic reads. The header states that UtcNow can be coarse and step,
  that there is no cross-host synchronization, and that raw digits are not accuracy.
- Warnings: the header records the exact queue_full_prefix and states: log lines, not drops; zero is not proof;
  asynchronous count/time association; cumulative last-observation time; cap coverage approx_max_coverage_s
  (about 1198 s). Schema v2, with renamed fields.
- Frame semantics documented (record after a hitch; SimTime read order).
integration.md synchronized to root's env-only IGVC_TRANSPORT_TIMING_TRACE=1. Originals preserved:
REPORT-r0.md, integration-r0.md, harness-r0. The r0 count label is corrected to 14 core + 1 JSON.
Evidence: 1 offline command; 19 core checks + 1 JSON check passed (lifecycle stop, UTC bracket and header
semantics, exact hitch values). Unity recompile of r1, player lifecycle and overhead are unverified (no Unity
available to me). Stopping for review.

### 2026-10-05T08:00:31.6296533-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW

relayed-from: artifacts/agents/T-0037/sonnet-review-r2.md

**Verdict: accept with conditions.** I found no code blockers, but items 1-3 need fixing or confirming before live capture. The four prior blockers are resolved: permanent stop, bracketed UTC, schema-2 caveats, and the offline checks. Only the pure window is tested. The Trace lifecycle, log callback and hook default-off are unverified in a player.

**Ranked findings**

1. **Coverage vs the 2029 failure.** The hook uses the defaults, so 1200 records cover about 1198 s. If "2029" means elapsed seconds, the trace exhausts before it. `approx_max_coverage_s` is also mislabeled. Records are at least one interval apart, so exhaustion happens at or after that time, never before, and sparse frames lengthen it. Rename it to nominal or minimum. Consider an env-supplied cap, or state that "exhausted" is not "no event".

2. **Frame gap over-reads as transport.** It is wall time between Updates. That is indistinguishable from focus loss, Editor pause, GC, OS suspension or vsync stalls, so add this to `frame_semantics`. Also, `mono_s` is the last frame, not the emission time. In the `stopped` record, the time from the last frame to disable is unmeasured. Say so.

3. **Warning LogType is unconfirmed.** `OnLog` counts only `LogType.Warning`. The survey confirmed the text and the thread, not the type. A mismatch gives a silent zero, which the caveat covers. Confirm the type in the pinned source before the player run.

4. **Count/timestamp coherence (low).** The writer increments the count and then sets the ticks, and the reader reads in the same order. A record can therefore show delta>0 with last-observed null or stale. Setting ticks first and then the count removes that case. It stays non-atomic, as documented.

5. **Minor.**
   - `ReadUtc` runs `ToString("o")` inside the bracket, which widens it. Take the second timestamp before formatting.
   - `Update` dereferences `ros` and `probe` without Unity-null checks. `End` guards `ros`, but `Update` does not.

**Sound as written**
- **Threading:** the callback does only `Interlocked` work, with no Unity API and no allocation. The taken-count is touched only on the main thread.
- **Disable/enable:** the stop is permanent and idempotent. The exhaustion path through `OnDisable` is safe, and `Stop` cannot exceed the cap.
- **Cadence and allocations:** at most one record per second, and allocations happen only when a record is due.
- **Claims:** the clock caveats are honest, and there is no wire-time or queue-depth claim.

**Hook:** it is acceptable, and the default creates no component. From the 3-line context I can't confirm it precedes Connect. I also can't tell whether a later init throw leaves the trace running against a broken probe.

**Next:** recompile in Unity and run the 19 checks. Then do one player smoke test with the flag off and on, including a forced disable. Make no causal claim and no promotion.

relayed-from: artifacts/agents/T-0037/sol-review-r2.md

### 2026-10-05T14:58:57+00:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0037   Candidate: ccee5bccba857d6f0046f4085d110cee18889061   Scope: evidence
Verdict: approve-with-nits

Findings (ranked, ≤ 5):
1. [minor] unity/IGVCSim/Assets/IGVC/Runtime/TransportTimingWindow.cs:60: approx_max_coverage_s is nominal, not a maximum. Header plus 1199 periodic records exhausts the default cap after approximately 1199 intervals, whereas this field reports 1198. Frame delays can lengthen coverage arbitrarily. Use actual header/final clocks to establish coverage; do not interpret this estimate as a cutoff.

Evidence: Clean exact candidate; revision changes only the three owned source files (+176/−77). Primary copies of all three match candidate raw hashes. Earlier asynchronous-pair and opt-in-document findings are addressed. Schema v2 distinguishes observed warning lines from drops, enqueue from wire delivery, and zero observations from proof of no drops. UTC reads are bracketed with Stopwatch reads; UTC accuracy, steps, precision and cross-host synchronization remain explicitly qualified. Stop retains the partial window and permanently prevents resumption; terminal mono_s remains the last sampled frame, not stop time.

Inspected 19 core checks and harness JSON parsing; pure stop/idempotence checks do not execute MonoBehaviour lifecycle. Independently read revision-1 Unity status/log: Unity 6000.3.23f1 batchmode TransportTimingChecks.Run exited 0 at 14:57:55Z, with 19 PASS and no C# warning/error/Exception matches. This supports actual compilation and Editor helper execution, beyond the reported offline 19+1; update report's pending compilation wording accordingly.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓.
Tests run: none by reviewer (read-only evidence inspection).
Missing acceptance coverage: Player default-off/on, lifecycle, threaded callback capture and overhead remain unverified. Account for the unsampled final tail when interpreting gaps. No 2029 cause, runtime fix, new lap or promotion established.
Usage: UNMETERED.


### 2026-10-05T08:00:31.6296533-07:00 · gpt-6-astra → all · DECISION

Accept ccee5bc capture-only source with root integration corrections requested by reviews: rename misleading approximate max to nominal_exhaustion_after_first_sample_s=(cap-1)*interval, update corresponding check, and state Update gap alternatives plus last-frame/unsampled-tail semantics. No new behavior or runtime motion change. 2029 is COURSE SEED, not elapsed seconds; failed trial121s and mission bound600s are within nominal1199s coverage. No cap increase needed. Pinned ROSConnection.cs line833 explicitly uses Debug.LogWarning, confirming LogType.Warning. Hook precedes ros.Connect (TransportProbe.Start), creates component only with env=1. Async count/time caveat retained. Runtime/null/callback effects and overhead require live evidence. Revision1 actual Unity compile+19checks passed; targeted retest of corrected header plus primary player build and stopped on/off smoke are granted under exclusive lease, hidden rendered player, no ROS mission or other-session interruption. Source promotion is unrelated and remains blocked. Sonnet0.1674194USD API-equivalent; Sol UNMETERED.


### 2026-10-05T08:05:16.3186176-07:00 · gpt-6-astra → all · INTEGRATION

Integrated20a18f3e7df4da4fa6dce4e5c8e5d16323b4c5ef. Final19 Editor checks and rendered Win64 build exit0; Assembly-CSharp SHA cf8f4a64b4847bd1d6156d679c0af19ea8f7219b7b4d53458b0f87bf9fa426c3. Stopped player off/on smoke exit0/0:off0records,on11 (header+9windows+stopped), terminal component-disabled event confirms shutdown lifecycle, UTCbrackets ordered. Logs/verdict in artifacts/agents/T-0037/player-smoke-*. No ROS endpoint by design; expected SocketException connection-refused logs retained. Warningcallback not exercised and overhead unmeasured. Root no player,port10000free,lease available after smoke. Build-generated TransportProbe scene fileID churn archived then restored from cleanprebuildHEAD; no scene source change integrated. Ordinary launches remain unchanged/default-off. T0038 permits one separately granted diagnostic repeat; no promotion.
