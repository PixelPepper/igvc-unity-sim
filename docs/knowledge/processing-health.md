---
type: Architecture
title: Processing health evidence
description: How lane/depth processing health is sampled, latched and diagnosed.
tags: [health, telemetry, perception, diagnostics]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-05T10:15:00Z }
sources:
  - id: ledger
    resource: ../../tools/mission_health.py
  - id: telemetry
    resource: ../../tools/sensor_telemetry.py
igvc_sources:
  - path: tools/mission_health.py
    sha256: 2373c48ee06504208d5157798315a0501cd59a37377d0216e3de38662781b8ac
  - path: tools/sensor_telemetry.py
    sha256: 92f60e4ec8d1393d71d9b4e26ed2d64901e6b405a885bdd15a9e4ce9da2281c2
---

# Mechanism

- **Sampling.** The mission samples lane and depth processing health at about 10 Hz over the armed interval. The ledger
  latches any fail or unknown.[^ledger]
- **Verdict.** The audit's sensor-led acceptance needs complete interval coverage, with gaps of at most 0.25 s, and
  zero failing samples.
- **Snapshots.** Telemetry keeps bounded, immutable first-fail and first-unknown snapshots, bound to the exact ledger
  sample, and exports its clock origin.[^telemetry]

# Interpretation

- A node reporting unhealthy says *that* processing failed, not *why*.
- Snapshots separate node-reported status from subscriber-observed ages and infer no cause.
- Health is not perception accuracy or physical reliability.

[^ledger]: Mission health ledger
[^telemetry]: Sensor telemetry
