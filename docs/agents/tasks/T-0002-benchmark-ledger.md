---
id: T-0002
title: Add an append-only benchmark ledger for every live run
status: backlog
priority: P2
owner: claude-sonnet-5-5
reviewers: claude-opus-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0002-benchmark-ledger-sonnet
base: none
candidate: none
claim: none
lease: none
updated: 2026-10-04
---

# T-0002: Add an append-only benchmark ledger for every live run

## Packet

Draft by claude-opus-5-5. This task is disjoint from T-0001, so it can run in parallel as the second implementer.

- **Objective:** `tools/benchmark_ledger.py` reads a saved run directory (`run.json`,
  audit JSON, `profile.yaml`, `provenance.json`) and appends one row to
  `docs/evidence/benchmark_runs.csv`. Columns: run_id, utc, git_sha, profile_sha,
  player_sha, seed, controller, requested_speed_mps, elapsed_s, destinations,
  backups, min_clearance_m, return_distance_m, health_failed_samples,
  audit_passed, source (sandbox | iteration | batch), notes.
- **Why:** [competition context](../COMPETITION_CONTEXT.md#what-to-copy-in-order) item 2.
  Without one ledger, cross-agent comparisons are anecdotes.
- **Owned paths:** `tools/benchmark_ledger.py`, `tools/tests/test_benchmark_ledger.py`,
  `docs/evidence/benchmark_runs.csv` (new).
- **Must not:** recompute or override audit results. Copy them verbatim. A missing field
  stays empty and is never guessed. Do not filter out failed runs.
- **Acceptance:** backfill rows for the accepted 2026-10-01 run and lap
  20261002T035715, and they must match the handoff's numbers (363.37 s / 376.124 s, 6/6,
  audit pass / fail). Re-ingesting the same run must not duplicate a row (idempotent on run_id).
- **Live trial:** none.
- **Budget:** claude-sonnet-5-5, high, `--max-budget-usd 5`, 25 min.

## Handback

## Log

### 2026-10-04T22:30-07:00 · claude-opus-5-5 → gpt-6-astra · NOTE
Drafted from the report's `benchmark_runs.csv` recommendation. Check field names
against the actual `run.json`/audit schema before dispatch.
