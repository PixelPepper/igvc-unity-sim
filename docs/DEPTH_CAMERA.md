# Ideal metric depth camera

Latest integration: RGB lane and dark-bowl projection now use this estimated plane through a bounded causal join; see [terrain-aware lane projection](TERRAIN_LANES.md). All 42 perception tests and the new full-course regression passed. Earlier depth-only evidence below remains separate.

The terrain-relative ground estimator is implemented. The earlier 32-test perception suite (including eight ground tests), three actual GPU-rendered ground fixtures, Windows Unity build and seven ROS package builds passed. A [30-second live depth check](../artifacts/checks/ground-depth-live.json) passed all 12 checks at 9.77 Hz images / 4.88 Hz clouds, with 283 exact-stamp image/CameraInfo/TF observations and 141 independently checked cloud projections. This stationary view contained no positive obstacles; the rendered cube fixtures below verify positive obstacle retention separately. The [depth-loss watchdog check](../artifacts/checks/depth-watchdog-live.json) passed enable, loss-stop and no-automatic-rearm checks.

The earlier fixed-ground [30-second live check](../artifacts/checks/depth-live.json) passed all 12 checks at 10.11 Hz images / 5.00 Hz clouds, with 290 positive obstacle-point observations. Its seed-2027 [archived audit](../artifacts/courses/seed-2027/previous-20260909T155117598034Z/validation.json) passed 78/78 checkpoints with no recovery or paint-guard interventions, 0.723 m minimum sampled clearance and 2.2 m/s maximum. A first terrain-estimator run also completed all 78 with [0.708 m sampled / 0.547 m swept clearance](../artifacts/courses/seed-2027/previous-20260909T155710805753Z/validation.json). That run exposed brief acquisition-TF timing errors, preserved in [the failure report](../artifacts/checks/ground-depth-tf-race.json); the final selector now uses the newest fresh exact-TF-ready pair. The depth verifier does not isolate costmap-layer causality.

The preceding terrain-depth [full-course run](../artifacts/courses/seed-2027/previous-20260909T164059627191Z/run.json) **completed 78/78 with no pauses, recoveries or line-guard blocks**. Its [audit](../artifacts/courses/seed-2027/previous-20260909T164059627191Z/validation.json) passed: 0.75552 m minimum sampled clearance, 0.58410 m conservative swept clearance, 0.29262 m final error and 2.2 m/s maximum observed chord speed. The [120-second health observation](../artifacts/checks/steady-course-health.json) received 581 depth-health updates, all true, with a 0.2092 s maximum gap. Lane updates had a 0.2318 s maximum gap; the 8.40 s interval without positive paint detections occurred in the declared unmarked connector. Two transient lane TF misses left the maximum positive camera-health gap at 0.4016 s. Three autonomy falling edges corresponded to planned zone stops and completion, with fresh perception at each; the mission recorded no pause events.

An earlier regression stopped at 17/78 after three watchdog stops and two explicit resumes. Its [health diagnostics](../artifacts/checks/ground-course-health-resumed.json) preserve approximately 1.15 s shared update gaps despite valid depth statuses. Subsequent paired-clock observations identified backward system-time corrections delaying default timers while monotonic freshness expiry continued. All three relevant nodes now use explicit steady timers; the 0.75 s gate is unchanged. See [ROS timing cause, fix and evidence](ROS_TIMING.md). Earlier completed loops and failed attempts remain historical evidence rather than substitutes for the latest run.

## Image contract

| Topic | Data |
|---|---|
| `/camera/depth/image_raw` | `sensor_msgs/Image`, 320×240, `32FC1`, nominal 10 Hz |
| `/camera/depth/camera_info` | Matching dimensions, intrinsics, frame and acquisition stamp |
| `/camera/depth/points` | Sampled optical-frame XYZ `PointCloud2`, nominal 5 Hz |
| `/perception/depth/obstacles` | Height-filtered XYZ `PointCloud2` in `odom`, nominal 5 Hz |
| `/perception/depth/status` | JSON String with validity, stamp and point counts or failure reason |
| `/perception/depth/healthy` | Bool; successful fresh acquisition and confident observed ground fit |

Image values are metres along optical **Z**, not Euclidean distance along a ray. Rows run from top to bottom; optical axes are right, down and forward. Valid rendered depths span 0.2–10 m inclusive. No-return and out-of-range pixels become NaN. The floating-point axial-depth representation follows [REP 118](https://reps.openrobotics.org/rep-0118/); this project's topic retains the `/image_raw` suffix despite carrying floating-point metres.

Depth has half the RGB width and height and shares the pose and `camera_color_optical_frame` of the RGB camera, including its commanded pitch. Depth captures have their own schedule: RGB and depth acquisition stamps are **not synchronized**. Consumers must use each stream's own CameraInfo and TF rather than assume paired RGB/depth exposures. Depth intrinsics use principal point (159.5,119.5) and the copied camera vertical field of view, with zero simulated distortion.

This is an ideal rendered geometry sensor. It does not simulate a physical stereo baseline, disparity estimation, texture failures, occlusion-related matching errors or OAK-D calibration uncertainty.

## Rendering and projection

`ProbeDepthCamera.cs` creates a co-located camera and a linear `RFloat` render texture. The resource shader `Assets/Resources/IGVCMetricDepth.shader` outputs positive camera-view Z depth. Async GPU readback publishes float values with the declared byte order and 1,280-byte row stride. A pending readback prevents overlapping captures; paused/disconnected operation suppresses new captures, and a changed simulation run invalidates an in-flight result.

The renderer requires a supported shader, `RFloat` render targets and GPU readback support. Its render camera and texture are released when the component is destroyed. `depth completed=... errors=...` diagnostics report transport-side progress.

`depth_node.py` joins depth and CameraInfo by exact acquisition stamp, checks encoding/buffer/frame consistency and handles image byte order and row padding. It waits briefly for acquisition-time TF and rejects pairs older than 0.5 wall seconds. Its wall-time processing timer targets 5 Hz. `depth_points` samples every fourth row and column, producing at most 4,800 optical points per processed frame. Non-finite and out-of-range samples are removed.

The node resolves `odom <- camera_color_optical_frame` at acquisition time and transforms sampled depth points into odom. Ground candidates come only from image rows 160–239 at stride four. `estimate_ground` fits an upward plane directly to those returns, without consulting course geometry or assuming world Z=0. A deterministic RANSAC uses at most 64 hypotheses and 1,600 candidates, followed by two SVD refinements.

Confidence requires at least 100 inliers and 60% support within 35 mm of the plane, slope at most 20°, and signed camera-to-plane clearance of 0.4–2 m. The fit also requires two-dimensional horizontal support: minor-axis RMS at least 0.15 m and central-90% spans of at least 1 m and 0.5 m. Refinement rechecks these requirements. Insufficient consensus, including the tested equally supported separated levels, is rejected. Sparse, narrow, wall-like or steep observations can also fail these checks; there is no fallback to a guessed flat plane.

`terrain_obstacles` retains points with signed normal height 0.12–1.8 m above the fitted plane and Euclidean camera range at most 10 m. The full optical cloud still includes ground. One fitted plane cannot represent steps, discontinuities or curved terrain generally. A broad flat obstacle top can satisfy the geometric ground heuristic; confidence is not semantic proof of traversability. It does not detect negative obstacles: the existing RGB dark-bowl hazard detector remains separate. RGB lane/hazard projection now uses the observed plane; neither this single-plane model nor the ideal planar body motion implements complete ramp navigation or physical contact/attitude.

`/perception/depth/healthy` reports a successful fresh depth/CameraInfo/TF observation **and** confident ground fit. Missing/stale pairs, unavailable TF and low-confidence terrain publish false; uncertain frames do not publish a replacement obstacle cloud. Existing depth marks expire through the layer timeout. When the bridge's `require_depth` parameter is enabled, 0.75 wall seconds without a successful depth-health update prevents enabling autonomy or latches active autonomy off. Valid depth returning does not rearm the gate automatically.

Both Nav2 costmaps consume `/perception/depth/obstacles` through a separate `igvc_lane_layer::LaneLayer` instance. Each cloud replaces that layer's active observations; stale clouds expire after 0.75 wall seconds and previous bounds are revisited. Lidar clearing does not erase active depth marks. Other layers can keep the same cell occupied. The depth node retains only bounded image/CameraInfo caches, not a multi-second point history.

## Build, launch and inspect

The normal `nav-start` launch starts `depth_processor` automatically. Do not start a second instance. For a rebuild from project-root PowerShell, stop the existing simulator first:

```powershell
.\tools\igvc.ps1 stop
wsl -d Ubuntu-24.04 -- bash '/mnt/c/Users/brand/Documents/ChatGPT/IGVC SIM/tools/build_ros.sh'
.\tools\igvc.ps1 course-build
.\tools\igvc.ps1 variant-start -Seed 2027 -Difficulty normal -Visible
.\tools\igvc.ps1 nav-start
.\tools\igvc.ps1 rviz
```

`variant-start` regenerates its variant and archives prior evidence; use `course-start -Visible` instead for the imported reference course. Building and starting alone do not issue motion commands.

The navigation RViz configuration includes **Depth obstacle points** and **Metric depth**, enabled by default, plus **Full depth cloud**, disabled by default to reduce clutter. Use fixed frame `odom` and Best Effort/Volatile subscriptions. The image display's normalized brightness is a visualization, not metres; inspect pixel values or point coordinates for quantitative checks.

Raw depth payload is computed as 320×240×4 = **307,200 bytes/frame**, or **3.072 MB/s** at 10 Hz before ROS/TCP overhead. A maximum-size stride-four XYZ cloud is 4,800×12 = 57,600 bytes, or 0.288 MB/s at 5 Hz; the filtered obstacle cloud adds up to the same amount. These are arithmetic payload bounds, not measured throughput or frame-rate results.

Math tests cover axial-versus-radial depth, row orientation, NaN/Inf/range handling, dimensions/intrinsics, stride, proper transforms and pitched-camera ground rejection. Reproduce the bounded sensor check through `tools/run_ros.sh` with `python3 tools/verify_depth.py --duration 30 --report artifacts/checks/depth-live.json`. The sibling PNG uses magenta for NaN, unlike RViz's grayscale display.

The course regressions use flat procedural terrain and do not validate moving slope transitions. Full raw depth remains geometric; stereo noise, disparity, sensor confidence, material-dependent returns and suspension/contact dynamics are not simulated.

## Rendered terrain fixtures

`tools/verify_ground_fixtures.py` reads the actual `flat`, `raised` and `inclined` GPU depth buffers and metadata under `artifacts/checks/ground-fixtures/`. It applies the same lower-image candidate selection and pure ground helpers, then independently compares with each fixture's analytic normal/offset and cube bounds. Run from WSL:

```bash
python3 tools/verify_ground_fixtures.py
```

All three fixtures passed: flat Z=0, raised Z=0.195 m and a 10° inclined plane. Maximum normal error was 0.000335° and maximum offset error 0.00000107 m. Cube observations were respectively 116, 109 and 119; none of the 2,348 / 2,504 / 3,344 independently identified ground points were classified as obstacles. The [fixture report](../artifacts/checks/ground-render-live.json) records checks and input hashes. Despite that historical filename, this is saved GPU-render plus math evidence, **not live ROS transport, watchdog or moving-terrain validation**.
