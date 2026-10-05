---
type: Process
title: Trial, audit and promotion
description: What a live trial must record, what the independent audit decides, and how promotion is gated.
tags: [evidence, audit, trial, ledger, promotion]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-05T10:19:28Z }
sources:
  - id: auditor
    resource: ../../tools/audit_sensor_run.py
  - id: judge
    resource: ../../tools/course_judge.py
  - id: ledger
    resource: ../../tools/benchmark_ledger.py
  - id: decisions
    resource: ../agents/DECISIONS.md
igvc_sources:
  - path: tools/audit_sensor_run.py
    sha256: f15ffa1b0c49c1b4012752a9a2afe91acbfaabe7bdaf003ee3539e9b3f72031a
  - path: tools/course_judge.py
    sha256: 783afab8cbc230cf321c98d7805bf37030ec958da1fa6a6d5a114d7c1db8e825
  - path: tools/benchmark_ledger.py
    sha256: cee367381fd959a64f7bbc492d602658bb6c576f3f235241453e67cf8111533f
---

# Trial

- **Ownership.** One bounded trial per grant, under the exclusive lease, held until shutdown is verified.
- **What gets recorded.** Commit, profile, player, overlay and course/mission identities, plus the run, decisions and
  health ledger.

# Audit

The independent auditor judges the same saved course and mission bytes, offline.[^auditor] Reaching 6/6 destinations is
**not** a pass. Acceptance needs every check: ordered full loop, return, swept obstacle and paint clearance, ramp,
continuity, speed and processing health.[^judge]

- **The auditor stays independent.** It is never changed in the same task as the policy it judges.
- **Re-audits are separate.** A corrected re-audit is a separately labeled artifact; the original failed audit and
  ledger row stay.

# Evidence ledger

[`docs/evidence/benchmark_runs.csv`](../evidence/benchmark_runs.csv) holds one row per run, with values copied from
artifacts and failed runs kept.[^ledger]

# Promotion

The current gate is set by the user and recorded in [DECISIONS](../agents/DECISIONS.md).[^decisions] It requires
repeated passes on the same commit plus held-out seeds. Current results live in the ledger and the task logs, not in
this concept.

[^auditor]: Independent run auditor
[^judge]: Course judge
[^ledger]: Benchmark ledger
[^decisions]: Decision log
