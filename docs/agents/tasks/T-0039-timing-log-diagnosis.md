---
id: T-0039
title: Summarize bounded Unity timing captures without inferring a cause
status: ready
priority: P2
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0039-timing-log-diagnosis
base: 20a18f3e7df4da4fa6dce4e5c8e5d16323b4c5ef
candidate: none
claim: none
lease: none
updated: 2026-10-05
---

# T-0039: Reusable offline timing evidence

## Packet

- Read README, this packet, accepted T0037 source/header semantics. Same worker
  directory now clean branch codex/t0039-timing-log-diagnosis at20a18f3. Root's
  integration renamed nominal coverage to(cap-1)*interval and clarified unsampled
  tail/frame ambiguity. Do not restore r0/r1 weaker semantics.
- Implement a small read-only tools/diagnose_transport_timing.py with focused
  tools/tests/test_transport_timing_diagnostics.py. Only these source paths owned.
  Follow existing diagnosis CLI style: explicit --unity-log and --output, refuse
  overwrite, preserve original log; no ROS/Unity process launches, no dependencies.
- Input is a Unity player log containing schema igvc_transport_timing_v2 single-line
  JSON records among ordinary lines. Stream bounded input; cap trace records/line
  size with explicit unavailable/integrity diagnostics rather than silently claiming
  coverage from truncated data. Hash original log bytes for binding. No geometry,
  course, mission, images, external models or ROS callback modifications.
- Summarize header configuration, record count/kinds, actual frame-sample range,
  UTC read brackets, worst frame gap/window, observed connector-warning log lines,
  final stopped/exhausted versus missing terminal record. Preserve raw floats but
  make clock-resolution/UTC-step/cross-host uncertainty explicit. Final mono_s is
  LAST FRAME, not stop time: expose final bracket separately and mark unsampled tail.
  Nominal coverage is not a maximum. Zero warning lines never prove zero drops.
- Validate schema/version, monotonic sequence and relevant finite/types/order
  fields enough to avoid false claims; missing/malformed/conflicting records mean
  incomplete evidence, not zero gaps/healthy. No automatic upstream cause,
  performance benefit, ROS gate verdict, or invented clock alignment. A frame gap
  does not distinguish focus/GC/OS/scheduling/render/network. Unknown stays unknown.
- Keep report concise/bounded; do not reproduce whole log. Avoid building an
  event platform or modifying auditors/health gates. Support default-off log with
  no records as unavailable (not failed simulator); abrupt trace termination as
  incomplete. Any optional threshold is diagnostic-only and must not affect runtime.
- Behavioral tests: steady cadence, hitch across reporting boundary, terminal
  unsampled tail, missing terminal, default-off/no data, malformed/nonfinite JSON,
  sequence contradiction, zero warnings and cap exhaustion with finite coverage.
  Prefer synthetic records consistent with actual producer plus existing smoke logs.
- IMPORTANT: T0038 live trial is ACTIVE under exclusive lease. LIGHT source edits
  only while active. No test/replay/large-log parsing until canonical T0038
  LEASE-RELEASE. Do not read changing active trial logs. Existing completed smoke
  snippets in PRIMARY artifacts/agents/T-0037 are enough for design. Root will
  notify lease release. Do not wait for approval on implementation choices.
- Budget20min active,2 focused test commands after release, at most2 revisions.
  No provider calls/delegation/live sessions. Clean source-only commit, compact
  primary artifacts/agents/T-0039/REPORT.md and <=300word canonical handback with
  tests/unverified areas. Stop for independent review. No push/promotion.

## Log

Light implementation dispatched; tests wait for T0038 lease release.

### 2026-10-05T08:08:22.6604254-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

Implement the bounded offline report while the live mission runs; defer tests until T0038 lease release. No active-log parsing or runtime changes. Exact branch already prepared at20a18f3; current Unityplayer unaffected.

