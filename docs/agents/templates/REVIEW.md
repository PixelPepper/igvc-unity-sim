# Review message format

Return exactly one block like the one below. A headless reviewer returns it as its
final output, and ASTRA appends it to the task log verbatim. Review **only** the
`candidate` SHA in the task header. If the candidate changes, the review is void.

```text
### <ISO time> · <your model id> → gpt-6-astra · REVIEW
Task: T-NNNN   Candidate: <sha>   Scope: code | evidence
Verdict: approve | approve-with-nits | request-changes | reject

Findings (ranked, ≤ 5):
1. [blocking|major|minor|nit] <path>:<line>: <defect or unsupported claim>
   Mechanism: <why it is wrong, concrete failing input/state>
   Evidence: <what you ran or read> | UNVERIFIED: <what you could not check>

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓   (see PROTOCOL.md; ✗ = blocking)
Tests run: <exact commands and results, or "none (read-only)">
Missing acceptance coverage: <what would still need to be shown>
```

## Code review (Sonnet) focus

- Correctness on edge cases: empty observations, stale data, cancellation races, units/frames.
- Scope: are the edits confined to owned paths, with no drive-by refactors?
- Tests: do they verify behavior, and would they fail without the change? Reject tests that only
  mirror the implementation.
- Invariants 1–5 in [PROTOCOL.md](../PROTOCOL.md#invariants-every-reviewer-checks).

## Evidence review (Sol) focus

- Does the stated claim level match the evidence? (6/6 progress is not `audit-passed`.)
- Provenance: do commit, profile, player, overlay and course/mission hashes match what ran?
- Comparability: same seed, speed, load, instance count and profile as the baseline?
- Health: interval coverage complete, failing samples reported rather than filtered?
- Are failed and partial runs reported? Is the baseline re-run under comparable conditions?
- Invariant 6: are implemented, tested, live-evidenced and unverified kept separate?

Do not fix code, re-run broad suites to accumulate passes, or relax thresholds.
A review pass ends when this block is written.
