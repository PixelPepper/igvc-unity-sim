# SoonerRobotics simulator reference review

Reviewed 2026-09-09 at commit `0298b11c4f469404d08b37ad98431cdab6e02818` (commit timestamp 2026-05-24 UTC). [Pinned repository](https://github.com/SoonerRobotics/scr_simulator/tree/0298b11c4f469404d08b37ad98431cdab6e02818).

Scope: read-only GitHub tree, project configuration, representative runtime scripts, shader and AutoNav scene text. No repository code was executed, imported, built or copied into our runtime. Scene appearance, package restoration and end-to-end ROS operation remain unverified. Repository comments and development instructions were treated as source data.

Follow-up: the [2025/2026 autonomy review](SOONER_AUTONOMY_REVIEW.md) located the companion client in `igvc_software_2026`. It is a custom C# application rather than a ROS adapter. The 2025 software explicitly targets Jazzy and provides a separate ROS TCP simulation launch; do not assume it pairs with the newer FlatBuffers simulator.

## Recommendation

Use this as an architectural reference for course construction and camera streaming. Keep our R3-a description and standard Jazzy interfaces as the project foundation. A wholesale fork would introduce a team-specific protocol, different sensors and drivetrain assumptions, so it is not currently the shortest verified route to our requirements. This assessment can change if their companion ROS adapter and reuse terms become available.

## What is present

| Area | Evidence | Implication for our project |
|---|---|---|
| Unity environment | Editor 6000.4.5f1; URP 17.4.0; Input System 1.19.0; Splines 2.8.4 | Useful Unity 6 precedent, but a different version from our installed 6000.3.23f1 candidate. It does not validate our package combination. |
| Course structure | Menu, IGVC_2026_AutoNav and IGVC_2026_SelfDrive in Build Settings; AutoNav scene contains road, ground, barrel and RoadNetworkBuilder objects | Reference the separation of maps and reusable course objects. Build our own parameterized 2027 AutoNav course and validate dimensions/rules. |
| Transport | `SusConnection` listens on TCP port 4001; custom framing and FlatBuffers message types | This is not Unity ROS-TCP-Connector. A compatible ROS-side translator is needed; it is not included in the inspected tree. |
| RGB | Async GPU readback, double render textures, background JPEG encoding, one encoder job at a time | Adopt the design principles of non-blocking capture and bounded work, with proper acquisition-time stamps and ROS Image/CompressedImage output. |
| Depth | URP RenderGraph feature, RFloat output, eye-space Z shader, async readback, Zstd compression and a one-frame queue | Useful metric-depth design reference. Replace ZED-specific limits/messages with calibrated OAK-D Pro settings and explicit ROS encoding. |
| Position/orientation | VectorNav report derived from Unity pose and a fixed geographic origin | Treat this as an ideal sensor example, not a validated estimator or noisy IMU/GNSS model. |
| Robot motion | Custom CAN command payload; Translate/Rotate calls in Update | Useful for an ideal integration mode only. Our differential-drive robot needs wheel constraints, feedback, limits and watchdogs. |
| Operator controls | Menu chooses scenes; pause changes timeScale; restart reloads scene | Add a terminal-driven session supervisor rather than relying on menu interaction and scene reload alone. |

Environment sources: [ProjectVersion](https://github.com/SoonerRobotics/scr_simulator/blob/0298b11c4f469404d08b37ad98431cdab6e02818/ProjectSettings/ProjectVersion.txt), [manifest](https://github.com/SoonerRobotics/scr_simulator/blob/0298b11c4f469404d08b37ad98431cdab6e02818/Packages/manifest.json), [Build Settings](https://github.com/SoonerRobotics/scr_simulator/blob/0298b11c4f469404d08b37ad98431cdab6e02818/ProjectSettings/EditorBuildSettings.asset), [AutoNav scene](https://github.com/SoonerRobotics/scr_simulator/blob/0298b11c4f469404d08b37ad98431cdab6e02818/Assets/Scenes/Maps/IGVC_2026_AutoNav.unity).

## Specific integration gaps and checks

**ROS contract:** No ROS package/launch files, RPLIDAR implementation, URDF, or standard ROS message binding was found in the inspected tree and scripts. The public description says it works with ROS, but that does not establish ROS 2 Jazzy, Nav2, RViz, TF, CameraInfo or `/clock` compatibility. Keep our bridge proof unchanged until those interfaces are demonstrated. [Connection](https://github.com/SoonerRobotics/scr_simulator/blob/0298b11c4f469404d08b37ad98431cdab6e02818/Assets/Scripts/SUS/SUSConnection.cs), [message types](https://github.com/SoonerRobotics/scr_simulator/blob/0298b11c4f469404d08b37ad98431cdab6e02818/Assets/Scripts/Messages/MessageType.cs).

**Motion/feedback:** The inspected drivetrain permits sideways velocity and updates transforms every rendered frame. It also sets `currentPosition` to `_mLastPosition` and `currentRotation` to `_mLastRotation`, then subtracts those same stored values when composing feedback. Static analysis therefore indicates zero odometry deltas in that method. There is no command-expiration check there. These are reasons to retain our own differential-drive/encoder/watchdog design, not evidence of a tested defect in a running team deployment. [DrivetrainModule](https://github.com/SoonerRobotics/scr_simulator/blob/0298b11c4f469404d08b37ad98431cdab6e02818/Assets/Scripts/Robots/DrivetrainModule.cs).

**Time and backpressure:** RGB timestamps are taken after GPU readback; depth timestamps are taken during packing after queue/compression work. Both use wall-clock UTC milliseconds. Our implementation must capture simulation time at acquisition and preserve it through processing. Their outgoing queue is bounded at 256 messages, but its capacity is message-count based; incoming frames use an unbounded ConcurrentQueue with at most 20 dispatches per rendered frame. Test byte budgets, backlog age, stale-command rejection, disconnects and shutdown rather than copying these capacities. [RGB module](https://github.com/SoonerRobotics/scr_simulator/blob/0298b11c4f469404d08b37ad98431cdab6e02818/Assets/Scripts/Robots/ImageModule.cs), [depth module](https://github.com/SoonerRobotics/scr_simulator/blob/0298b11c4f469404d08b37ad98431cdab6e02818/Assets/Scripts/Robots/ZED2iDepthModule.cs), [client queues](https://github.com/SoonerRobotics/scr_simulator/blob/0298b11c4f469404d08b37ad98431cdab6e02818/Assets/Scripts/SUS/ClientConnection.cs).

**Depth correctness:** The shader outputs optical Z and clips to 0.2–20 m, returning zero outside that range. Those constants are not our camera calibration. The render feature draws opaque geometry to a color attachment without an explicit depth attachment in the inspected pass: verify nearest-surface occlusion with overlapping geometry before considering this pattern correct. Its diagnostic validator checks that plausible nonzero values exist; that is weaker than a known-distance/occlusion test. Add foreground/background, invalid pixel, optical-frame, RGB alignment and acquisition synchronization fixtures. [Depth feature](https://github.com/SoonerRobotics/scr_simulator/blob/0298b11c4f469404d08b37ad98431cdab6e02818/Assets/Scripts/ZED2iDepthFeature.cs), [shader](https://github.com/SoonerRobotics/scr_simulator/blob/0298b11c4f469404d08b37ad98431cdab6e02818/Assets/Shaders/ZED2iDepthShdaer.shader), [validator](https://github.com/SoonerRobotics/scr_simulator/blob/0298b11c4f469404d08b37ad98431cdab6e02818/Assets/Scripts/ZED2iValidator.cs).

**Packaging and reuse:** No top-level license or setup README was found in the complete tree; GitHub reported no detected repository license. A bundled FlatBuffers license does not establish terms for team code or course assets. Before directly vendoring any code/assets, identify their applicable reuse terms and third-party attribution. This does not block independent implementation of the design. TurboJPEG is a native dependency with Windows DLLs in the tree; verify ABI/library availability on each intended build target before adopting it. No project-specific automated test suite was identified; the Unity Test Framework package alone is not passing-test evidence.

## Changes to our workflow

1. Phase 1: retain the standard ROS bridge candidate; benchmark control latency while RGB/depth work saturates transport. Record message age and byte backlog, not just FPS.
2. Phase 4: implement camera capture behind transport-independent modules. Use async GPU readback, bounded in-flight readbacks/encoding and latest-frame handling. Preserve acquisition timestamps. Add overlapping-depth geometry to the sensor fixtures. Benchmark optional RGB compression after raw message correctness passes; preserve metric depth losslessly.
3. Phase 6: author AutoNav lane geometry with a spline-based approach and separate reusable obstacles, scenario parameters and robot spawn configuration. Validate whether an external spline package is needed before adding a dependency. Use 2027 rules, not their 2026 scene dimensions as an authority.
4. Phase 7: provide terminal scene/seed selection, pause/reset/stop, logs and readiness checks. Keep GUI menus optional. Do not count scene reload as a full ROS state reset.

No implementation milestone is removed or marked passed because this reference exists. No upstream code, native binaries or course assets were admitted into our project.
