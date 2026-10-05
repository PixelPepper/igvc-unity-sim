---
type: Reference
title: Frames and sensors
description: Canonical robot frame, forward axis and the authoritative sensor mount configuration.
tags: [frames, urdf, sensors, camera, lidar, footprint]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-05T10:15:00Z }
sources:
  - id: drive
    resource: ../R3A_DRIVE.md
    title: R3-a drive orientation
  - id: camera-mount
    resource: ../../ros2/src/igvc_description/config/camera_mount.json
  - id: lidar-mount
    resource: ../../ros2/src/igvc_description/config/lidar_mount.json
igvc_sources:
  - path: docs/R3A_DRIVE.md
    sha256: ad4804440982790e5340ddc599a66816373fca5ac99db35f512e4fd426e5d29f
  - path: ros2/src/igvc_description/config/camera_mount.json
    sha256: 1f0be7d3acfe7894744a2b04fa7b644f9cc00d3bbec696c68546bacec61322ed
  - path: ros2/src/igvc_description/config/lidar_mount.json
    sha256: fa2c3c135fa982135b53499971db452f3f0e50a9c1d60e418c4e810232b9c3bf
---

# Invariants

- **Front is the big driven wheels; the casters are rear.** Canonical ROS +X points forward.
  - The source CAD/URDF frame was reversed, and description preparation rotates it by Z π.
  - Never restore the source-frame forward assumption.[^drive]
- **`base_footprint` is at the driven axle.** `base_link` is 0.25591 m behind it.
- **Sensor poses** come only from the mount JSON files:
  - The RPLIDAR sits in the front roof housing.[^lidar-mount]
  - The OAK-D Pro sits atop the rear pole, with pitch-only tilt; +Y pitch is positive down.[^camera-mount]
- **Whole-body footprint** is about x = [−1.1, 0.6] and y = [−0.5, 0.5] m about the axle, plus 0.02 m padding.
  Inflation is a cost preference, never a footprint reduction.

# Not claimed

Measured mass, inertia, calibration or physical sensor noise.

[^drive]: R3-a drive orientation
[^camera-mount]: Camera mount configuration
[^lidar-mount]: Lidar mount configuration
