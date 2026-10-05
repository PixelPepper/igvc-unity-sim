---
id: T-NNNN
title: <imperative, specific outcome>
status: backlog
priority: P2
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/tNNNN-<slug>-<role>
base: <snapshot sha>
candidate: none
claim: none
lease: none
updated: YYYY-MM-DD
---

# T-NNNN: <title>

## Packet

Written by ASTRA and frozen at `ready`. Any change goes in the Log as a `DECISION`.

- **Hypothesis / objective:** one falsifiable sentence.
- **Why now:** link to the handoff priority or [COMPETITION_CONTEXT](../COMPETITION_CONTEXT.md) row.
- **Inputs:** exact files, run ids and evidence paths to read first. Keep this to the minimum needed.
- **Owned paths (may edit):** list them. Everything else is read-only.
- **Must not change:** invariants specific to this task, in addition to the
  [protocol invariants](../PROTOCOL.md#invariants-every-reviewer-checks).
- **Baseline identities:** commit, profile, player, overlay, course/mission hashes, run id.
- **Allowed checks:** the named test commands, up to 3 focused runs.
- **Live trial:** none, or 1 via `LEASE-REQUEST` (state the instance and profile).
- **Acceptance:** what evidence would make ASTRA accept this.
- **Stop condition:** when to hand back, even if partial.
- **Budget:** model, effort, `--max-budget-usd`, wall limit.

## Handback

Filled in by the owner. 300 words maximum, not counting the identities.

```text
Hypothesis and outcome:
Changed files / scoped commit (candidate SHA):
Baseline and candidate identities:
Tests and replay evidence (commands + results):
Live result: destinations, time, backups, clearance, health, audit status:
Shutdown/lease verification:
Claim level reached: implemented | tested | audit-passed
Remaining risks and next experiment:
```

## Log

<!-- Append entries below. Never edit or delete earlier ones. Format:
### 2026-10-04T21:40-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
body
-->
