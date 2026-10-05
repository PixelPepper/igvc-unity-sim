# Draft ADR-009: Less idle time without weaker gates

**Status: PROPOSED, under review.** Not adopted. PROTOCOL.md is unchanged until ASTRA records a `DECISION` and the
user approves. Drafted 2026-10-05 by claude-opus-5-5 at the user's request ("send this off to be reviewed first").

## Context: measured from the task logs

The protocol's gates caught real defects in every cycle, so they are worth keeping:

- Sol found that an empty snapshot identity validated as evidence (T-0005).
- Sol found that my handback claimed documentation that did not exist (T-0002).
- ASTRA's T-0007 Q1 replaced my "retry more targets" proposal with a 0.153 m fix to an existing gate. That fix,
  T-0008, then passed a full 20-check audit in T-0009.

The cost is serial idle time. Approximate cycle times from the log timestamps:

| Task | Dispatch → integrated | Implementer active (approx.) | Main waits |
| --- | --- | --- | --- |
| T-0001 | 23:26 → 23:44 (3 revisions) | ~10 min | review relay, decision per round |
| T-0002 | 00:12 → 00:27 (2 revisions) | ~10 min | same |
| T-0005 | 00:57 → 01:17 (2 revisions) | ~12 min | same |
| T-0008 | 01:40 → 02:00 (1 revision) | ~12 min | same |
| T-0006 / T-0009 live laps | ~15–20 min each | 0 | single lease; all implementers idle |

These are coarse estimates from message timestamps, not instrumented measurements. Other friction:

- A per-task cap on *invocations*, rather than on time, pushes workers to bundle checks into one command; a typo
  burned an invocation in T-0002, and a stale edit burned one in T-0005.
- `wait_message.py` has no durable cursor, and the Claude watcher expires every 30 minutes.
- A Codex turn cannot wake itself, so the user sometimes has to nudge ASTRA.
- ASTRA relays every review request and every review result. That is routing work, not judgement.

## Proposal

Adopt items 1–3 now. Items 4–5 are follow-ups.

1. **Standing offline backlog (pull model).** ASTRA keeps a list of pre-approved, offline-only tasks (`status: ready`,
   `class: offline`). An idle implementer may claim one with an `ACK` without waiting for a `DISPATCH`.
   - Allowed: read-only analysis, decision and recovery replays, diagnostic tooling, and test hardening. Output goes
     only under `artifacts/agents/<task>/`, or to source on a task branch.
   - Not allowed: simulator, lease, Unity, shared interfaces, profiles, the auditor or dependencies.
   - Integration, acceptance and promotion stay with ASTRA.
   - Example: while a live lap runs, the implementer replays the decisions that lap has already saved.
2. **Worker-launched reviews.** On `HANDBACK` the implementer launches the Sonnet code review and the Sol evidence
   review itself. It uses the existing read-only dispatch commands and checks the exact model ID, then relays each
   `REVIEW` block verbatim with `relayed-from`. ASTRA still writes every `DECISION` and still enforces the
   reviewer-independence rule.
   - Optional fast path: when every finding is `minor` or `nit`, the worker may make one fix-and-rehandback round
     before ASTRA's decision. That round needs a new SHA and both reviews again. Any `major` or `blocking` finding goes
     straight to ASTRA.
3. **Two-instance A/B trials.** For outcome comparisons, run the baseline and the candidate concurrently on the two
   isolated instances that LEARNING_PLAN already calibrated (`tools/sandbox.ps1 -Instance n`, own port, domain,
   session and lease). Both get the same course, profile and player, and the independent audit. Both rows go to the
   benchmark ledger automatically. Each comparison yields twice the data in the same wait, and machine load is
   comparable across the pair. The 3+1+1 promotion gate needs many laps, so this matters.
4. **(Follow-up) Bounded worker-run trials.** With ASTRA's per-task grant, a worker may run one trial through the
   existing `iteration-live.ps1` lease path, which already holds the lease through verified shutdown. Independent
   audit, verified shutdown and no automatic retry stay mandatory. ASTRA keeps integration of the result.
5. **(Follow-up) Plumbing (fold into T-0003).**
   - A durable message cursor, so `wait_message` never misses an entry.
   - Launchers driven by the task file.
   - Offline budgets set in minutes rather than invocation counts. Live trials keep a strict count.

## Unchanged (hard)

- ASTRA-only integration and promotion.
- One owner per file, and reviewer independence: no self-review, and no same-model review within a task.
- The independent auditor and every invariant in PROTOCOL.md.
- The exclusive lease per instance.
- User approval for push, publish, invariant or threshold changes, and new providers.
- No automatic retries or model substitution.
- The live-trial count stays capped. A two-instance A/B counts as two trials against the user's budget.

## Risks

- **More concurrent spend:** reviews and A/B trials. Mitigated by keeping the existing per-task allowances, and by
  having ASTRA report aggregate usage per cycle.
- **Workers drifting into scope:** the backlog's `offline` class is fail-closed. Anything outside the allowed list
  needs a `DISPATCH`.
- **Thinner orchestrator visibility:** every claim, review and result still lands in the canonical task log, which
  the board and the Observatory already show.
- **A/B instance interference:** keep to the calibrated two instances only. LEARNING_PLAN reports perception latches
  at four instances under machine load.

## Questions for reviewers

1. Does any proposal weaken an invariant, the reviewer-independence rule or ASTRA's authority?
2. Is the fast path in item 2 safe, given that it requires a new SHA and both re-reviews?
3. Are the timing estimates and the defect examples accurately supported by the task logs?
4. What is missing, for example the claim-conflict rules when two implementers pull from the backlog?
