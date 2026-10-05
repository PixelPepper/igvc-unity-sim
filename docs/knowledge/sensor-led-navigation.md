---
type: Architecture
title: Sensor-led navigation
description: The observed-only planning pipeline and its hard safety checks.
tags: [navigation, planning, guidance, path-entry, safety]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-05T10:15:00Z }
sources:
  - id: sensor-autonomy
    resource: ../SENSOR_AUTONOMY.md
    title: Sensor-led autonomy design
  - id: guidance
    resource: ../../tools/observed_navigation.py
  - id: path-entry
    resource: ../../tools/path_entry.py
# path_entry.py is linked but not pinned until its pending T-0014 change integrates.
igvc_sources:
  - path: docs/SENSOR_AUTONOMY.md
    sha256: 1dd11e27fafbce6866bebc09943c8d2a76d5890cc7bf702803035a091ecf995c
  - path: tools/observed_navigation.py
    sha256: 1bd13088c92dfacc5dd5a5aa93d56eafba344e52edc8ceb989fd0196fa569c1f
---

# Inputs allowed at run time

Observations (paint, hazards, depth, lidar, odometry) plus six broad GPS destinations in a sanitized `autonomy.json`.
The policy never reads `course.json`, WORLD geometry, Reference Lab output or teacher labels. Those are for rendering
and the independent audit only.[^sensor-autonomy]

# Pipeline

1. **Guidance.** Observed corridor guidance proposes intent from lane pairs. An entered visible mouth hands off into
   the shared observed span.[^guidance]
2. **Search.** The search admits only full-footprint, forward, curvature-bounded paths under a wall and expansion budget.
3. **Path entry.** Path entry joins the latest pose with a checked forward biarc and re-sweeps the connector and the
   remaining path. It rejects stale poses, lethal cells and unknown cells.[^path-entry]
4. **Recovery.** Recovery uses checked backups within a bounded budget.

# Not claimed

A bounded search that finds no route is not proof that no route exists. Replay of a saved decision is not a live result.

[^sensor-autonomy]: Sensor-led autonomy design
[^guidance]: Observed navigation guidance
[^path-entry]: Path-entry admission
