---
id: T-0026
title: Skip deferred recovery capture when command-stop cleanup failed
status: review
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0026-capture-stop-guard-opus
base: 52fdd9d192accecb02d952ca73bc1e55116694eb
candidate: 9cdfd99131548ec22181da229f37edf8fc30ed25
claim: tested
lease: none
updated: 2026-10-05
---

# T-0026: Bound the remaining capture guard

## Packet

- Read README and the final Sonnet review/decision in T0023. Existing interactive
  Opus owns implementation, focused tests and commit. Same isolated worktree
  C:/Users/brand/.codex/worktrees/igvc-t0005-health-capture/IGVC SIM, now on the
  prepared branch above at clean 52fdd9d.
- Owned files: tools/recovery_evidence.py, tools/sensor_course.py only deferred
  flush call/comments/import, tools/tests/test_recovery_evidence.py.
- If command-stop cleanup reports errors, do not invoke the heavy capture writer.
  Mark each pending report record explicitly skipped with the cleanup reason.
  Preserve map-free failure diagnostics, original cleanup/error/health semantics
  and normal successful-cleanup capture. Describe calls as attempted unless
  successful cleanup is actually known. Do not redesign preexisting snapshot I/O.
- Behavior tests must prove a failing cleanup prevents writer invocation and
  keeps the skip reason in the saved report; successful cleanup still writes and
  binds the exact frozen worker inputs. No source-string/order tests.
- No motion, policy, timeout, health, footprint, unknown, audit, runner or Unity
  changes. No live trial. T0025 is fully shut down; focused tests are allowed.
- Bound: 10 minutes active work, one focused test invocation, no full suite,
  providers, subagents or retries. If this exposes a new issue, hand back partial.
  Write REPORT.md and review-inputs.md under primary artifacts/agents/T-0026,
  append <=300-word handback here, and stop. No publishing.
- This is a new narrow task after the T0023 revision budget, not an extension of
  the original feature scope. Review the resulting full stack once in Sol and
  the guard delta once in Sonnet before integration.
- Knowledge: sensor-led-navigation; trial-audit-promotion.

## Handback

claude-opus-5-5. Candidate 9cdfd99131548ec22181da229f37edf8fc30ed25 (base 52fdd9d), 3 files +66/-8.
Report: artifacts/agents/T-0026/REPORT.md; review-inputs.md staged.

```text
Change: DeferredCapture.flush(cleanup_errors=()) receives state['cleanup_errors'], which the existing
  cleanup loop appends when disabling autonomy, cancelling the action or resetting the mode raises.
  Any error: the writer is never invoked; each pending record is marked "skipped: command-stop cleanup
  reported errors: <label: error>"; pending is cleared. No error: the capture is written and bound as
  before. sensor_course changes only the flush call and its comment (cleanup "attempted"). Map-free
  failure diagnostics, cleanup/error/health semantics and preexisting snapshot I/O are unchanged.
Tests: one invocation, 58 OK. New behavior tests use the real search and writer through a mission-style
  cleanup harness. Failing cancel: the guarded writer is never called, no file exists, and the serialized
  report keeps the reason and the evidence. Successful cleanup: written, matches_worker_digest, and the
  rebuilt file reproduces the worker digest.
Limits: the mission wiring is source-reviewed, not executed. Non-RuntimeError cleanup failures are not
  recorded by the existing loop (unchanged, out of scope). No live trial, no fix claim. UNMETERED.
```

## Log

### 2026-10-05T05:24:53.085387-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
Proceed with this guard now. One owner, exact paths and bounds above.


### 2026-10-05T05:26:07-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
Candidate 9cdfd99131548ec22181da229f37edf8fc30ed25 (base 52fdd9d, 3 files). If command-stop cleanup recorded any error, the deferred capture writer is never invoked and each record keeps the skip reason; successful cleanup still writes and binds the capture. 58 focused tests OK in one invocation. Mission wiring is source-reviewed only. See the Handback section. Stopping.

### 2026-10-05T05:28:32.948463-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW
relayed-from: artifacts/agents/T-0026/sonnet-review-r1.md
Actual model confirmed; USD 0.0360934 API-equivalent.

**Accept.** The T0023 cleanup-error blocker is closed, with the caveats below.

This review is from the diff and report only. I used no tools and did not run the 58 tests, so that result is the worker's reported one.

**Requirements against the diff**
- **No writer call on cleanup errors:** `flush` checks `cleanup_errors` before `started = clock()` and the `self.writer(...)` call, then `continue`s. The failing-cleanup test uses a writer that raises if called, asserts `assert_not_called`, and checks that no file exists.
- **Explicit skip reason on pending records:** each record gets `capture = 'skipped: command-stop cleanup reported errors: <joined errors>'`, bounded by `MAX_STRING`. The test confirms the string survives the `allow_nan=False` JSON round trip and that the map-free `evidence` is untouched. `self.pending` is cleared either way.
- **Successful cleanup still writes and binds:** with an empty list the original path runs unchanged. The test checks `matches_worker_digest`, then rebuilds the inputs from the file and reproduces the worker digest.
- **Health, cleanup and policy unchanged:** the `sensor_course.py` change is only the flush argument and its comment. The "attempted, not confirmed" wording is accurate.

**Non-blocking notes**
1. **Wiring is not executed.** The tests use a mirror harness. If `state['cleanup_errors']` were renamed, the mission would silently go back to writing captures. This is source-reviewed only, as the report states, so it makes no live claim.
2. **`flush` signature change:** `clock` moved from the first to the second positional parameter. Any caller passing it positionally would break. The reported 58 tests passing suggests none exist, but I did not grep for callers.
3. **Gap in the `RuntimeError`-only cleanup loop:** a non-`RuntimeError` cleanup failure is not recorded, so `flush` would still write. The report correctly marks this as pre-existing and out of scope. It limits how far this guard can be trusted.

**Remaining blocker:** none.

### 2026-10-05T05:28:32.948463-07:00 · gpt-6-astra → all · NOTE
Disposition: source confirms the same failure dict reaches state and the deferred
writer, so updates are retained. No positional clock callers were introduced.
Sonnet's non-RuntimeError observation is partly incorrect: an uncaught exception
exits the existing finally block before flush, rather than continuing to write.
It remains a preexisting evidence-loss/cleanup limitation, not a bypass of this
guard. Simulated cleanup tests are not live mission wiring evidence.

### 2026-10-05T05:28:43-07:00 · claude-opus-5-5 → gpt-6-astra · NOTE
Correction accepted. A non-RuntimeError cleanup failure is not "unrecorded but continuing": it escapes the cleanup loop and exits the existing finally block before flush, so no capture is written and the later report write is also skipped. That is a preexisting evidence-loss limitation, not a bypass of this guard. My REPORT.md "Limits" wording was imprecise; this note supersedes it.
