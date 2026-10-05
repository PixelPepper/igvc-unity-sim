---
id: T-0022
title: Explain observed recovery refusal in failed connector repeat
status: ready
priority: P1
owner: gpt-6.1-sol
reviewers: claude-sonnet-5-5
orchestrator: gpt-6-astra
branch: none
base: a0a3d49ae465ef2176ce4bdb910257fc76c6ccb7
candidate: none
claim: none
lease: none
updated: 2026-10-05
---

# T-0022: Observed recovery diagnosis

## Packet

- Read README, knowledge sensor-led-navigation and exact relevant functions only.
- Read-only diagnosis, not implementation. T0020 stopped at 2/6 after 226.30s,
  no observed safe backup with useful forward clearance; health complete and passed.
  Explain which observed prerequisites/candidate gates failed and what we can and
  cannot infer. Compare T0018's successful backup; do not assume same location or causality.
- Inputs: primary artifacts/iterations/2026-10-05/connector-repeat-3/run.json and
  bounded final planner-input captures; connector-repeat-2/run.json and relevant
  backup-associated captures; compact evidence and task T0020.
  Runtime source is frozen worktree
  C:/Users/brand/.codex/worktrees/igvc-t0008-mouth-handoff/IGVC SIM at a0a3d49,
  especially tools/sensor_course.py, observed_navigation.py, and actual recovery
  chooser reached by that call. Follow precise symbols, not a repository-wide review.
- NO course.json, WORLD, audit/reference geometry or exact route inputs in
  diagnosis/replay. Observed sensor costs, sparse GPS and pose only.
  Submission-time captures are not necessarily latest recovery snapshots.
  Distinguish missing telemetry from absent observation and unsafe geometry.
- At most 10 minutes and 4 focused read/analysis commands. No source edits, tests,
  live sessions, replays, builds, provider calls or delegation. Write only
  artifacts/agents/T-0022/REPORT.md and a compact diagnostic JSON if useful.
  Do not update task log/header; return one handback of at most 300 words to root.
- Acceptance: exact decision indices/reasons/evidence pointers; code branch that
  raises; whether refusal happens before or after sweeps; smallest next bounded
  instrumentation or improvement without weakening unknown, footprint, health,
  clearance or freshness gates. Support numerical claims. Stop after diagnosis.
  This task grants no fix/promotion authority.

## Handback

Pending.

## Log

### 2026-10-05T04:38:00-07:00 · gpt-6-astra → gpt-6.1-sol · DISPATCH
Investigate this bounded observed-only failure while Opus revises T0021.
Return a supported diagnosis and smallest next step, no speculative rewrite.
