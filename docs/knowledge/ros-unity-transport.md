---
type: Architecture
title: ROS-Unity transport
description: How the Unity player and ROS 2 Jazzy exchange clock, sensors and commands, and who owns the bridge.
tags: [unity, ros2, transport, lease, simulation]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-05T10:15:00Z }
sources:
  - id: ros-interface
    resource: ../ROS_INTERFACE.md
    title: ROS interface contract
  - id: runbook
    resource: ../RUNBOOK.md
    title: Runbook
igvc_sources:
  - path: docs/ROS_INTERFACE.md
    sha256: d5b996b2f611062ac96451b2f160b868da167f0b4bd1a0ee15233335d9a38787
  - path: docs/RUNBOOK.md
    sha256: c56c73f2d0d9c315d54b48be97097213cdce20985459b3e779170934d7bb7546
---

# Summary

Unity runs on Windows and renders the course, an idealized robot, RGB and metric depth, and a simulated lidar. ROS 2
Jazzy runs in Ubuntu 24.04 under WSL2. They connect over the ROS TCP bridge, by default on TCP port 10000 with ROS
domain 42. Topic and frame contracts are defined in the [ROS interface](../ROS_INTERFACE.md).[^ros-interface]

# Ownership rules

- **One owner at a time.** One live simulator owns the bridge per instance. A finished sandbox lap can still hold the
  port, so inspect ownership before starting anything.
- **Isolated instances.** These use their own port and domain (`10000+n`, `60+n`). See the
  [runbook](../RUNBOOK.md).[^runbook]
- **Lease authority.** The process-held lease (`artifacts/iterations/live.lock`, or a per-instance lease) is
  authoritative. A file existing does not prove the lease is held.
- **Builds lag source.** Source edits do not update a built Unity player or an installed ROS overlay, so check hashes.

# Not claimed

Idealized physics and sensors. This is not a calibrated R3-a robot or hardware timing.

[^ros-interface]: ROS interface contract
[^runbook]: Runbook
