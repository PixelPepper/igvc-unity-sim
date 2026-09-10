# Transport milestone evidence

Test host: Windows with Intel Core Ultra 9 275HX, RTX 5080 Laptop GPU; Unity player uses Direct3D 12. Unity 6000.3.23f1, built-in rendering pipeline, Windows x64 Development player. ROS 2 Jazzy runs in Ubuntu 24.04 WSL2 with Fast DDS and WSLg RViz2/OpenGL 4.5. Local domain is 42.

Pinned transport dependencies:

- ROS-TCP-Connector `c27f00c6cf750d2d0564349b3039d19aa3925e7c`.
- ROS-TCP-Endpoint `54c1a64b6d5ef6ffa0a0431570bb74329b79b15b`.
- Cursor SDK `1.0.31` is optional development tooling, not a simulator runtime dependency.

The Unity checks now pass 12 behavior assertions. Batch build logs end with successful Editor exit, and the Windows player was launched and connected to Jazzy. The actual ROS RGB image was captured and inspected: upright, orange fixture on the left. `artifacts/checks/rviz.png` shows RGB, scan, TF and odometry with Global Status OK. This establishes the fixture visualization, not calibrated OAK-D Pro behavior.

## Performance diagnosis

The first 600-second run passed 11 live behavior checks plus image encoding and monotonic time. It measured RGB 6.31 Hz, lidar 5.24 Hz, odometry 49.77 Hz and real-time factor 0.9993. It failed the RGB minimum of 10 Hz. The failed baseline is retained at `artifacts/checks/live-probe-baseline.json`.

State queues of 1 dropped bursts between Unity fixed updates; increasing clock/odometry/joint queues to 10 removed ordinary burst pressure while retaining small bounded memory. RGB remains queue 1. Camera diagnostics measured approximately 13 captures per simulation second and 33 ms mean GPU readback, with no readback errors. A ROS comparison received roughly 12.5 Hz using reliable QoS but only 5.5 Hz using best effort, locating the dominant loss downstream of capture.

The WSL participant profile now gives SHM an 8 MiB segment and retains UDP transport for discovery. An isolated best-effort check then received 171 images over 15 seconds including initial discovery; acquisition stamps spanned 12.9 seconds. This supports the buffer correction; the final full-load test is the acceptance evidence. Fast DDS documents a default 512 KiB segment and warns about insufficient space relative to sample sizes; each RGB payload here is 900 KiB. [Fast DDS SHM](https://fast-dds.docs.eprosima.com/en/2.14.x/fastdds/transport/shared_memory/shared_memory.html).

## Final acceptance

The final 600-second run passed all 15 checks, with RViz connected and best-effort verifier subscriptions. Measured rates: clock 98.66 Hz, odometry 50.00 Hz, RGB 13.34 Hz, lidar 5.26 Hz and joints 49.99 Hz. Real-time factor was 0.999966. The assertions verified forward motion, yaw sign, known wall distance, scan geometry, pause/resume, reset, stop override, stale-command rejection, timeout, image encoding, monotonic clock and sustained load.

All 8 reconnect checks passed after restarting only the owned ROS process group while Unity remained alive. The verifier waited for fresh odometry rather than evaluating cached samples. Clock continued, odometry/images/services recovered, motion did not replay, and additional travel was 0.036 m from a 0.3 m/s command (acceptance bound 0.2 m). Reports: `artifacts/checks/live-probe.json`, `reconnect.json`, `unity-checks.json`; runtime source hashes: `source-hashes.json`. Intentional endpoint restart produces connection/drop messages in the player log and is distinguished from normal sustained operation.

PowerShell wrapper build, doctor, start, status, test, stop and RViz were exercised. Start/stop uses process ownership and rejects duplicate players from this workspace. The package includes a screenshot helper for the Linux RViz window and a ROS RGB capture utility. The first transport gate is complete; these tests do not qualify the future full-sensor robot simulation.

## Scope boundaries

This is a manual, ideal transport fixture. `/odom` uses ground truth, joint payloads are synthetic, and the body has no wheel contact physics. No real robot import, calibrated lidar/depth, CameraInfo, point cloud, Nav2 execution or IGVC course has been implemented. The prototype reset preserves clock and stop/pause latches; it is not the future estimator/Nav2 reset sequence. Per-topic publisher QoS, full sensor throughput and command latency percentiles remain later qualification work.

The original URDF audit (`artifacts/checks/robot-audit.json`) found a connected five-link/four-joint tree, resolving five STL files with 888,264 triangles and 96.86 kg exported mass. Numeric inertia checks passed; this does not validate physical parameters. The invalid package name with spaces, mesh budget, caster approximation and sensor mounts must be resolved in the robot milestone. Source CAD and URDF remain unchanged.

Agent integration evidence and token accounting are in [AGENT_WORKFLOW.md](AGENT_WORKFLOW.md). Local test logs/build outputs stay ignored; source and reproducible commands remain in the repository.
