---
id: T-0037
title: Capture bounded Unity frame and connector warning timing
status: in-progress
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0037-unity-timing-capture
base: 0779593c8b077da4c8b47c5a497c47b6dc29df93
candidate: none
claim: none
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
