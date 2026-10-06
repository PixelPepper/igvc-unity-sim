---
type: Architecture
title: ROS-Unity transport
description: How the Unity player and ROS 2 Jazzy exchange clock, sensors and commands, and who owns the bridge.
tags: [unity, ros2, transport, lease, simulation]
status: stable
generated: { by: codex/gpt-6-astra, at: 2026-10-06T02:53:00Z }
sources:
  - id: ros-interface
    resource: ../ROS_INTERFACE.md
    title: ROS interface contract
  - id: runbook
    resource: ../RUNBOOK.md
    title: Runbook
  - id: timing-capture
    resource: ../../unity/IGVCSim/Assets/IGVC/Runtime/TransportTimingTrace.cs
    title: Optional Unity transport timing capture
  - id: timing-window
    resource: ../../unity/IGVCSim/Assets/IGVC/Runtime/TransportTimingWindow.cs
    title: Bounded timing aggregation and schema
  - id: timing-analysis
    resource: ../../tools/diagnose_transport_timing.py
    title: Offline timing integrity checks and summary
igvc_sources:
  - path: docs/ROS_INTERFACE.md
    sha256: d5b996b2f611062ac96451b2f160b868da167f0b4bd1a0ee15233335d9a38787
  - path: docs/RUNBOOK.md
    sha256: c56c73f2d0d9c315d54b48be97097213cdce20985459b3e779170934d7bb7546
  - path: unity/IGVCSim/Assets/IGVC/Runtime/TransportTimingTrace.cs
    sha256: 689fb6dee35bf7a82aa0dc8f87ab3021d5d2fe3295b597198c07681f7eccaf0e
  - path: unity/IGVCSim/Assets/IGVC/Runtime/TransportTimingWindow.cs
    sha256: bf2d4e5d49ff16c86cbfe9406ae06926da67090ee8789205dcaeebca7454b49a
  - path: tools/diagnose_transport_timing.py
    sha256: 55b80f4fe466deb6766070f2b1d1fe930fa790220d6f7e344ce7243a85b867ab
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

# Optional timing capture

Set `IGVC_TRANSPORT_TIMING_TRACE=1` before starting a compatible player to enable the
observation-only component. It defaults off. The bounded schema-v3 trace reports
once per wall second, up to 1200 records including the header. It samples connection
error flags in both Update and FixedUpdate and preserves gaps across reporting
boundaries. Disabling the component or exhausting the cap ends capture permanently.[^timing-capture][^timing-window]

Use `tools/diagnose_transport_timing.py --unity-log <log> --output <new-report.json>`
offline. It accepts v2 and v3 separately, checks record consistency and hashes the
input. Old v2 logs have no per-sample error or physics timing evidence. Missing
terminal records leave final coverage unknown; absent samples are not healthy
samples. Boolean counts are not error durations, warning lines are not drop counts,
and neither SimTime nor callback gaps prove message delivery or a root cause.
No alignment with ROS/WSL clocks is assumed.[^timing-analysis]

[^ros-interface]: ROS interface contract
[^runbook]: Runbook
[^timing-capture]: Optional Unity transport timing capture
[^timing-window]: Bounded timing aggregation and schema
[^timing-analysis]: Offline timing integrity checks and summary
