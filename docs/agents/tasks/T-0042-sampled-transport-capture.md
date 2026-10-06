---
id: T-0042
title: Observe per-frame connector errors and physics-step gaps without changing control
status: accepted
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0042-sampled-transport-capture
base: 8c33100
candidate: 2ca413fbd8b8dacbf72bf9f5cc2af8f3a543eb81
claim: tested
lease: none
updated: 2026-10-05
---

# T0042: Minimal sampled transport capture

## Packet

Dedicated headless Claude CLI worker ONLY. Interactive Claude must not duplicate.
Read README and this packet from PRIMARY, plus existing timing code/tests first.
Worker checkout C:/Users/brand/.codex/worktrees/igvc-t0005-health-capture/IGVC SIM
is clean at8c33100. No live session. Prior branch/evidence preserved.

Implement the narrowed, reviewed T0041 direction. Existing trace is opt-in by
IGVC_TRANSPORT_TIMING_TRACE=1 and defaults off. Add observation-only FixedUpdate
sampling and connection-error counts on every observed Update/FixedUpdate while
coverage is active. Keep constant bounded aggregation and1Hz output/cap1200.

Owned SOURCE paths ONLY:
- unity/IGVCSim/Assets/IGVC/Runtime/TransportTimingTrace.cs
- unity/IGVCSim/Assets/IGVC/Runtime/TransportTimingWindow.cs
- unity/IGVCSim/Assets/IGVC/Editor/TransportTimingChecks.cs
- tools/diagnose_transport_timing.py
- tools/tests/test_transport_timing_diagnostics.py

Use schema v3 for new records; offline tool must continue accepting original v2
logs (new metrics unavailable, never invented zero). Add finite/count/order
validation for v3 and bounded summaries; mixed versions/inconsistent fields are
incomplete. Preserve all existing v2 integrity checks and original fixtures.
Minimal metrics: sampled Update error count; FixedUpdate sample/error count;
largest interval between FixedUpdate observations with end monotonic time;
fixed-window observed SimTime range if useful. Clearly label independent sample
streams and their window attribution. Do not conflate previous-frame boundary
with currentwindow fixed observations. Zero observations => unavailable timing,
not healthy. A gap spanning a reporting boundary must remain visible.

Limits: Bool reads are asynchronous observations, not exact intervals/durations,
not proof of no errors. FixedUpdate gap means no sampled callback in that period,
not unique main-thread causation. SimTime is sampled with unspecified component
ordering; it proves neither publish/enqueue/send/delivery nor cross-hostalignment.
No offline ROS-time join in this slice. No cause classifier or automatic retry.
Keep record cap, default-off zero component behavior, permanent stop/no resume,
terminal tail uncertainty, warning semantics, and existing guards unchanged.
No changes to TransportProbe hook, publishers/cameras, motion, ROS interface,
watchdogs, scenes, packages, audit, course or trajectory. Do not build Unity or
launchROS/player. Root owns Unity compile/build/integration after bothreviews.

Behavior checks: subsecond true samples invisible to old1Hz snapshot now counted;
rollover of each samplingstream withoutlostgap/doublecount; multiplefixedticks per
Update; noFixed samples; final partialwindow; ended/cap no-op; v2 compat; v3 malformed
counts/nonfinite/out-of-order data and mixedschema rejected; real v2 logs remain
valid/incomplete asbefore. Prefer emittedC#v3fixture parsed byPython to avoidmirror
schemas. Do not rewrite parser architecture or remove behavioral tests.

Use installed C:/Program Files/dotnet/dotnet.exe for pure core harness; reference
PRIMARY artifacts/agents/T-0037/harness source/project as example (copy into your
OWN ignored artifacts/T0042, adjust source refs to worker). Do not edit original
harness. Python at C:/Users/brand/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe
(use -X utf8), or WSLpython3. Plain python onWindows isStorealias.

Budget20minutes active,4focusedcheckcommands, atmost1selfrevision aftertests.
No recursiveagents/provider/networkcalls/credentialreads. Edit and commit ONLY
fivepaths onassignedbranch afterfocusedchecks; artifactsnevercommitted. Do not
amend reportedcommits, reset, clean or push. Do not editprimarysource orcoordination.
Write compact report + changed-path/sourcehash manifest in PRIMARY
artifacts/agents/T-0042/REPORT.md (onlyownedprimaryartifact); all earlier evidence
unchanged. Handback<=300words with SHA,tests,limitations; stop forreview. No claim
of runtimefix/overhead benefit orqualification; originalT0035 preserved.

## Log

### 2026-10-05T19:36:04.870971-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

Bounded implementation after narrowed T0041 review. HeadlessCLIonly; no livelease.

### 2026-10-05T19:44:30-07:00 · gpt-6-astra → all · HANDBACK

relayed-from: artifacts/agents/T-0042/opus-report-r1.md

Opus committed d9c71a862ff886f8ca49f674a6a1a0ec0263796f; five owned paths only, clean worker tree. Exact claude-opus-5-5 confirmed, 435.58 seconds, 2.107092 USD API-equivalent usage. Worker reports 29 C# core checks and 24 Python checks passing, emitted C# v3 fixtures accepted, and four real v2 reports unchanged except unavailable new metrics. Root has not yet independently verified those tests. Unity compile/build and live behavior remain unverified. No control or safety change, root-cause claim, or promotion.

Worker file tools could not write outside its checkout. Root copied the original worker artifacts/T0042/REPORT.md into primary artifacts/agents/T-0042/REPORT.md without changing its contents. Longer original handback remains in artifacts; this is its bounded relay.

### 2026-10-05T19:44:31-07:00 · gpt-6-astra → claude-sonnet-5-5, gpt-6.1-sol · DISPATCH

One code review and one evidence review run in parallel against d9c71a8. Read-only, bounded offline scope. Root prepares integration validation while reviewers work. No live lease or Unity build granted to either reviewer.


### 2026-10-05T19:47:00-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION

Sonnet r1 accepts the implementation with explicit review limits (68.92 seconds, exact model confirmed, 0.2386302 USD). Sol r1 independently verifies scope, hashes, clean candidate, 29 C# and 24 Python checks, emitted v3 fixtures and four v2 comparisons, but requests revision based on root's counterexample. Reports: artifacts/agents/T-0042/{sonnet,sol}-review-r1.md.

Root reproduces two impossible records accepted by the parser: one fixed sample with distinct first/last times, and a new sample older than the previous record's UTC bracket. Evidence and reproducer: artifacts/agents/T-0042/single-sample-integrity.json and check_single_sample_integrity.py. These are offline validation gaps, not demonstrated runtime faults.

Grant one narrow Opus revision of the two Python paths, plus its ignored harness artifacts if synthetic observation chronology needs correction. Eight minutes, three focused checks, 5 USD CLI bound; no C# production edits, live lease, Unity build or provider retry. Preserve r1 evidence. Exact instructions are captured in artifacts/agents/T-0042/opus-request-r2.txt. Re-review only changed behavior before integration.


### 2026-10-05T19:49:13.7080390-07:00 · gpt-6-astra → all · HANDBACK

relayed-from: artifacts/agents/T-0042/opus-report-r2.md

New candidate 2ca413f fixes single-sample endpoints, single-gap span, and prior-record ordering in the two Python files only. Exact Opus model confirmed, 122.23 seconds, 0.6062404 USD. Reports 25 Python and 29 C# checks passing plus corrected actual-producer fixtures and four v2 comparisons. Earlier synthetic harness had an impossible observation timestamp; r1 evidence is preserved and r2 fixture chronology is corrected rather than weakening validation. Root copied REPORT-r2.md unchanged. Sonnet and Sol now review the delta; Unity integration remains pending.



relayed-from: artifacts/agents/T-0042/sonnet-review-r2.md

**Accept the r2 correction. I found no blocking defects.** This is a static diff review. I did not run the tests or the harness, and I relied on your reported results (25/25 Python, 29/29 C#, compare-r2 all OK).

The two root counterexamples are closed in `tools/diagnose_transport_timing.py`:
- **Single sample with a range:** line 208 adds `n == 1 and first != last`, which reports `fixed_range_invalid`.
- **Sample older than the previous record:** line 214 compares `first < prior_after`. `last_after` is seeded from the header bracket (line 315) and advanced to each record's `bracket[1]` (line 395). If a record's bracket is invalid it isn't advanced, so the check stays conservative.
- **Single-gap equality (line 231):** when exactly one gap exists, it must equal `last - start` within the existing 1e-9 relative tolerance, and `gap_end` must equal `last`. The first record with n=2 and a later record with n=1 both fit this. A boundary-crossing gap from the carried sample is still accepted.

The regression test (`test_v3_fixed_range_and_order_must_be_observable`) covers both reproducers. It also covers a legitimate case with a carried gap across a boundary, a no-fixed window and a gap of 2.05.

**Other invariants:**
- v2 records still go through the `elif any(key in record for key in V3_FIELDS)` path.
- Validation is `O(1)` state per record, and the summaries stay capped by `MAX_LISTED`.
- The correction doesn't touch the C# cap, permanent-stop or default-off behavior.

**Limits:**
- Multi-gap windows (two or more gaps) are only lower-bounded. Their `gap_end` is constrained only to lie within `[first, last]`.
- The harness change is evidence-only. The r2 synthetic scheduler gives every callback in a frame that frame's observation time. The real producer isn't exercised any further than before.
- No Unity compile, live run or overhead result exists. The checks are offline plausibility checks on timestamps and counts. They don't establish root cause, error durations, or publisher or delivery behavior.

relayed-from: artifacts/agents/T-0042/sol-review-r2.md

REVIEW
Task: T-0042
Reviewer: GPT-6.1 Sol
Verdict: ACCEPT narrow r2 offline evidence; Unity integration remains pending
Usage: UNMETERED

Independently verified: Candidate 2ca413fbd8b8dacbf72bf9f5cc2af8f3a543eb81 changes only the diagnostic Python file and its tests after d9c71a8. Both new manifest SHA256 values match committed bytes and working files. The candidate checkout is clean. All three C# production/check files are byte-identical to r1.

The delta rejects unequal endpoints for one fixed sample, observations before the previous record's UTC bracket, and a single gap inconsistent with its endpoint span/end. The 25 Python tests pass. Rebuilding the actual unchanged C# helper/check harness passes 29 core checks plus JSON parsing and freshly emits corrected r2 fixtures.

The r2 stopped/exhausted fixtures parse complete; independently checked sequences are contiguous and fixed observations follow prior UTC brackets. The comparison also rejects the count-corrupted fixture. R1 fixture hashes remained unchanged during validation; the preserved impossible r1 stopped chronology is now incomplete at sequence 5, while its exhausted fixture remains complete. This explains the fixture correction without weakening validation.

Four real v2 comparisons pass: original status, issues, SHA and structured report content remain compatible, with new sample metrics unavailable. The comparison deliberately normalizes uncertainty prose, so it is not proof of byte-identical reports.

Limits: These are synthetic emitted-fixture and pure-core/parser checks. TransportTimingTrace compilation/scheduling inside Unity, live capture, runtime overhead and failure discrimination remain unverified. Sampled counts are not exact error durations; callback gaps and SimTime do not prove delivery or cause. No threshold relaxation, runtime fix or promotion is established.

Three focused offline commands; no delegation, live session or source edits.
END REVIEW


### 2026-10-05T19:50:35.2535555-07:00 · gpt-6-astra → all · DECISION

Accept 2ca413f for its reviewed offline capture/analyzer scope. Sonnet r2 exact model confirmed, 20.09 seconds and 0.0785114 USD; Sol independently rechecked changed hashes, 25 Python tests, 29 unchanged C# checks, corrected producer fixtures and four v2 comparisons. Comparison normalizes uncertainty prose; it is not a byte-identical report claim. Root reviewed the complete five-file change and two-file correction. Authorize integrator-only Unity compile, Win64 build and two stopped-player 12-second off/on smoke checks under the exclusive process-held lease; no ROS/autonomy mission in this grant. Preserve cf8f player and earlier failed evidence.

