---
id: T-0039
title: Summarize bounded Unity timing captures without inferring a cause
status: review
priority: P2
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0039-timing-log-diagnosis
base: 20a18f3e7df4da4fa6dce4e5c8e5d16323b4c5ef
candidate: 138386416f884eb834a95fcde8b37afe4715d7af
claim: tested
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


### 2026-10-05T08:08:39-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
T-0039 accepted on codex/t0039-timing-log-diagnosis at 20a18f3. Light authoring only until the T0038 LEASE-RELEASE; no active-log reads.

### 2026-10-05T08:13:28.5543511-07:00 · gpt-6-astra → claude-opus-5-5 · NOTE

T0038 lease released and cleanup independently verified. Your2 focused offline test commands may run now. Completed log available at PRIMARY artifacts/iterations/2026-10-05/timed-2029-diagnostic-1/unity.log. Diagnostic lap completed6/6 with auditexit0; no original freshness failure reproduced, source19 unchanged. Do not infer a fix from this pass. Keep runtime stopped.


### 2026-10-05T08:14:30-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
Candidate 09ad7e9d5203762b6d4131da7c7b016a06185150 (base 20a18f3; new tools/diagnose_transport_timing.py and tools/tests/test_transport_timing_diagnostics.py, +486).
Tool:
- Required --unity-log and --output; refuses overwrite; read-only, single pass. SHA-256 over all bytes.
- Bounded lines (64 KiB) and records (1300). Oversize, malformed, non-finite, excess or embedded-marker lines are
  integrity issues.
- Validates schema v2, header fields, a gap-free seq chain, running frame and warning totals, gap monotonicity,
  mono_s order, UTC brackets, final-record presence and placement, and exhaustion only at cap-1. Any issue makes it
  "incomplete"; a log with no records is "unavailable".
- Report: header config (nominal coverage, not a maximum), kinds, first and last sampled frame, the top 5 window gaps
  with UTC brackets, warning-line totals and locations, the final record with its unsampled tail (last frame to
  final UTC read, not a gap), the covered span, and explicit uncertainty. No cause, verdict, clock alignment or
  performance claim.
Tests (command 1, after the T0038 release): 10/10 OK. Steady; hitch across a boundary; unsampled tail; missing final;
default-off; malformed or NaN; sequence and count contradictions; zero warnings; cap exhaustion; oversize line plus
hash; CLI.
Command 2, applying it to the real T0038 and smoke logs, FAILED because of my shell quoting (the path became "."),
not the tool. No files were written, and it is not re-run (budget). Suggested integrator commands are in
artifacts/agents/T-0039/REPORT.md. No 2029 conclusion. Stopping for review.

### 2026-10-05T08:16:01.5246331-07:00 · gpt-6-astra → claude-opus-5-5 · REVISION

Root found a concrete acceptance defect before independent review: schema=[igvc_transport_timing_v2] and kind=[] both crash summarize with unhashable-list TypeError. Reproducer artifacts/agents/T-0039/check_malformed.py and malformed-result-r0.json. Harden malformed field types throughout validation AND report aggregation so invalid JSON-shaped values become explicit incomplete evidence, not exceptions or healthy defaults. Check string/list/dict seq/previous-seq, kind, schema, numeric fields and large integers; bound error representations/output. Do not hide arbitrary programmer exceptions. Add behavioral regressions and retain the malformed evidence. Up to15min active and2 focused test/application commands; no live session active. Root also applied09ad to reallogs successfully: timed-2029-r0.json,smoke-on-r0.json,smoke-off-r0.json now in primaryartifacts/T0039. Reuse those as read-only references; don't overwrite. Focused revised tests then immutable source commit, updated report, stop for first independent reviews.

### 2026-10-05T08:18:44-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
Revision 1: candidate 138386416f884eb834a95fcde8b37afe4715d7af (parent 09ad7e9; same 2 owned files).
- Every field is type-checked before comparison, hashing or arithmetic. Integers are bounded to int64, numbers to
  |x| < 1e300 (inf from 1e400 rejected).
- UTC brackets: non-negative and ordered, with an ISO "o" utc of at most 64 characters.
- The cumulative warning time must be null or finite >= 0.
- All echoed values are bounded (truncated strings, summarized lists and dicts). No broad try/except.
Tests:
- Command 1: a new regression covering 10 bad types across the header, a window and the final record, plus
  root's list schema/kind cases and 1e400. It exposed a real gap (warning time unvalidated), two test-design
  errors and an unbounded utc.
- Command 2, after the fixes: no exceptions in any case, 3 remaining failures, all test expectations.
- The final two edits (ISO utc format check, valid-null exclusion) are committed but NOT RUN: budget used.
Request: one focused run, cd tools && python3 -B -m unittest tests.test_transport_timing_diagnostics; 11 tests
should pass.
Root's malformed-result-r0.json and real-log *-r0.json are untouched; REPORT-r0.md is preserved. Stopping for review.


### 2026-10-05T08:25:22.831705-07:00 · gpt-6-astra → all · REVIEW-START

Root ran requested11 focused tests on Windows:10pass,1failure oversize byte-count67479 versus expected67467. Likely test fixture write_text newline translation; exact byte hashing needs portable fixture. First independent Sonnet and Sol reviews now active on immutable1383864. Do not revise concurrently; await consolidated findings. Runtime remains stopped. Prior failed test commands and original malformed evidence retained.
