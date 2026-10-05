# Draft ADR-009 (revision 2): Less idle time without weaker gates

**ASTRA disposition, October 5:** revision 2 is not adopted as a package. See
[ADR-009 decision](../DECISIONS.md#adr-009-reduce-preparation-overhead-within-existing-authority).
Worker-staged manifests with independent verification and the stdin documentation
fix are retained within existing authority. Automatic pickup, timeout reassignment,
uncapped checks and parallel live comparisons are not enabled. The original
proposal and its review history below are preserved as submitted.

**Status: PROPOSED. Reviews complete; awaiting ASTRA's DECISION.** Both reviewers requested changes on revision 1
and revision 2. The user chose to stop revising (2026-10-05) and leave the decision to ASTRA. Not adopted. PROTOCOL.md is unchanged until ASTRA records a `DECISION` and the
user approves.

- Revision 1 is kept at [ADR-009-autonomy-draft-r1.md](ADR-009-autonomy-draft-r1.md).
- Its reviews are relayed in [T-0003](../tasks/T-0003-parameterize-launchers.md): Sonnet and Sol both requested
  changes.
- Author: claude-opus-5-5, the implementer that would gain autonomy. Reviewers should keep scrutinizing self-interest.

## What changed from revision 1

| Revision 1 item | Revision 2 | Reason (review finding) |
| --- | --- | --- |
| Worker-launched reviews and the minor-only fast path | **Dropped.** Replaced by worker-staged review inputs that ASTRA launches | It conflicts with PROTOCOL.md "Recursive delegation: none (workers do not spawn agents)", which only the user can change. The author would control the review framing, and the fast path bypassed the revision-cap transition (Sonnet 1, 5; Sol 2) |
| Two-instance A/B trials | **Deferred** behind explicit T-0003 prerequisites | Shared `igvc_ws` overlay (`sandbox.ps1:50`). The lease is disposed after an unverified shutdown (`sandbox.ps1:117-122`). No automatic ledger ingestion. Latches are reported at two instances too (Sonnet 2-3; Sol 1, 4) |
| Worker-run trials | **Dropped** for now | `iteration-live.ps1` has no instance support. Trial ownership stays with ASTRA (Sonnet 2) |
| ACK-claimed backlog | **Kept, redesigned:** ASTRA pre-assigns the owner and freezes the scope, with no open claiming | Racing ACKs, no frozen paths or base, and reads of lease-owned artifacts (Sonnet 6; Sol 3) |
| Timing table | **Corrected** from ACK→HANDBACK intervals | Active time was overstated, revisions were miscounted, and the idle claim contradicted T-0007 (Sonnet 4; Sol 5) |

## Context, from the task logs

Gates caught real defects:

- T-0005: the validator accepted snapshots that were missing identity fields.
- T-0002: my handback claimed documentation that did not exist.
- T-0007 Q1: led to the 0.153 m membership fix (T-0008), which then passed a 20-check audit (T-0009).

Measured from message headings (seconds-resolution timestamps):

| Task | Handbacks | Implementer active (ACK→HANDBACK summed) | Dispatch → integrated |
| --- | --- | --- | --- |
| T-0001 | 3 (2 revisions) | 6.0 min | 23:26 → 23:44 |
| T-0002 | 2 (1 revision) | 4.7 min | 00:12 → 00:27 |
| T-0005 | 2 (1 revision) | 6.7 min | 00:57 → 01:17 |
| T-0008 | 1 (0 revisions) | 6.8 min | 01:40 → 02:00 |

- A HANDBACK→DECISION hop takes about 4.5 minutes, and that is mostly reviewer runtime, so relay overhead is small.
- The T-0006 lease lasted about 14 minutes.
- The implementer was **not** idle for that whole lap: T-0007 was dispatched while the T-0006 lease was still held,
  so offline work can already overlap a lap.
- The remaining idle time comes from **having no assigned work queued** between decisions, not from review latency.

Other friction:

- **Prompt swallowed by a flag.** PROTOCOL's Sonnet example passes the prompt after variadic
  `--allowedTools`/`--disallowedTools` flags, which swallow it. The first ADR-009 review launch failed this way, before
  any model ran.
- **Missed messages.** `wait_message.py` has no durable cursor.
- **Invocation counts.** Counting invocations instead of time penalizes typos: T-0002 lost one to a path typo and
  T-0005 to a stale edit.

## Proposal

### 1. Pre-assigned offline queue

ASTRA may write offline tasks with `status: ready` and an extra header key, `start: on-idle`.

- **Fully frozen packet.** Each one has a single pre-assigned `owner`, a `base` SHA, owned paths, a budget, acceptance
  checks and a stop condition. These are written exactly like a DISPATCH packet.
- **Scope.** The class is restricted to read-only analysis, replay of **finished runs** (whose `live.json` reports
  `shutdown_verified: true`), diagnostic tooling and tests.
- **Excluded.** Lease-owned artifacts of a running trial, the simulator, Unity, shared interfaces, profiles, the
  auditor and dependencies.

Starting work:

- The pre-assigned owner, and only that owner, may start the task when it has no active task, by appending
  `ACK (on-idle start)`.
- Owner pre-assignment removes claim races. ASTRA does not assign more than the existing two-implementer limit.
- ASTRA sets `in-progress` on its next pass, and keeps the right to cancel with a `DECISION`.

Ends:

- Handback, review, decision, integration and acceptance are unchanged.
- An on-idle task with no HANDBACK within its wall budget is treated as abandoned. ASTRA may then reassign it.

This allows the implementer to pick up queued offline work during a live lap without waiting for a fresh dispatch.
ASTRA's control is unchanged, because ASTRA authors every queued packet.

### 2. Worker-staged review inputs (ASTRA still launches)

At HANDBACK the implementer writes `artifacts/agents/<task>/review-inputs.md`. It lists:

- the exact `git diff <base>..<candidate>` range
- owned paths
- the focused test commands with their results
- evidence paths and their hashes

It contains **no review instructions or framing**. ASTRA launches the reviewers it assigns, using fixed prompt
templates kept in `docs/agents/templates/`, which ASTRA owns, and verifies the actual model. The reviewer-independence
rule, the revision-round cap and ASTRA-written decisions are unchanged.

This saves ASTRA's input-gathering time without the implementer controlling the review.

### 3. Protocol hygiene (no authority change)

- **Fix the dispatch example.** Correct PROTOCOL.md's Sonnet dispatch example to pass the prompt on stdin.
- **Time-based offline budget.** Replace "Focused offline checks per revision: 3" with "Offline compute per
  revision: a wall budget set in the packet, default 20 minutes; invocations are logged, not capped."
  Live-trial limits are unchanged.

### 4. Deferred, with prerequisites tracked in T-0003

Two-instance A/B trials stay deferred until all of these hold:

- **(a) Isolated builds.** A separate ROS overlay per instance and per source identity.
- **(b) Lease retention.** Each instance keeps its lease while shutdown is unverified, matching `iteration-live.ps1`.
- **(c) Ledger ingestion.** An implemented ledger ingestion step for batch and instance runs.
- **(d) Bias control.** Balanced arm-to-instance assignment, with recorded load and every failed, latched or partial
  attempt kept and never auto-retried.
- **(e) Trial counting.** ASTRA grants each arm as a separate trial.

Also in T-0003: a durable `wait_message` cursor.

## Unchanged (explicitly)

All user approval gates in PROTOCOL.md "Escalation to the user" are unchanged:

- push, publish or PR
- stopping sessions that are not owned
- invariant, threshold, footprint or speed changes
- budget increases or new providers
- installs and version pins

The following are also unchanged:

- ASTRA-only header edits, integration, acceptance and promotion
- one owner per file
- reviewer independence
- the independent auditor and every invariant
- per-instance lease exclusivity
- no recursive delegation, and no automatic retries or model substitution
- live trials stay at one per task revision unless ASTRA grants more

ADR-008 removed the aggregate daily cap; this proposal does not add or remove any budget.

## PROTOCOL.md lines that would change if adopted

- **Task file format:** document the optional `start: on-idle` header key and its eligibility rules (item 1).
- **Message format:** add the `ACK (on-idle start)` meaning (item 1).
- **Dispatch commands:** add the stdin form for Sonnet; add the `review-inputs.md` description and the ASTRA-owned
  template path (items 2, 3).
- **Limits table:** replace the "Focused offline checks" row (item 3).

## Questions for reviewers

1. Does any remaining item weaken an invariant, reviewer independence, ASTRA's authority or an approval gate?
2. Is pre-assignment with an ASTRA-written frozen packet enough to prevent claim conflicts?
3. Is "finished runs only" a sufficient boundary against lease-owned reads?
4. Are the corrected measurements now supported by the task logs?
