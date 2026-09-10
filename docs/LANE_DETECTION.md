# Camera lane detection

`igvc_perception` consumes RGB8 `/camera/color/image_raw` and CameraInfo with identical acquisition stamps and optical frame IDs. It resolves `odom <- camera_color_optical_frame` at that exact time, including camera tilt, then intersects calibrated pixel rays with a fresh depth-estimated ground plane. It never reads the course mesh, simulator lane guard or ground-truth line labels.

The normal `nav-start` workflow starts the detector automatically through `local_navigation.launch.py`. Do not launch a second detector alongside it. An isolated detector also requires the depth processor and its ground estimates; the old `ground_plane_z` parameter is removed. Use the normal launch to start both once.

The plane comes from the newest preceding depth fit within 0.35 acquisition seconds and 0.5 receipt seconds. No fixed-Z fallback is used. See [terrain projection](TERRAIN_LANES.md) for geometry, temporal checks and limits. A single locally stationary plane cannot represent arbitrary slope transitions. An incorrect plane, slope or calibration produces incorrect projected points. Processing targets 5 Hz using a steady timer. The image ROI starts at 40% of image height so downward camera tilt does not crop away distant paint. Bright low-saturation pixels (HSV value at least 220, saturation at most 50) receive a 3×3 closing operation and no opening: even a 2×2 opening erased real one-pixel distant markings. Component area, shape and orange context provide the remaining noise rejection. Accepted pixels must form thin components; curved and transverse paint is accepted without a global vertical-orientation requirement. White pixels with orange above and below within 24 pixels are removed before component filtering, so touching lane paint survives while the barrel stripe is rejected. This corrected a real first-turn image where the former orientation filter rejected both visible boundaries. Ten lane geometry checks pass, but other white objects, faint paint, occlusion and non-orange obstacles remain limitations.

Outputs are `/perception/lanes/debug` (mono8 acceptance mask), `/perception/lanes/points` (XYZ PointCloud2 in odom), `/perception/lanes/valid` (Bool) and `/perception/lanes/status` (JSON String counts/reason). Points are range-limited to 1–10 m, voxelized at .075 m, capped at 8,000 and expire after eight wall seconds. Cloud headers use the current image stamp; retained points include observations up to TTL old. Validity requires current detected/projected paint, not merely cached points. Missing/new/stale pairs, unavailable TF or missing fresh depth ground publish false. The course command gate requires fresh valid observations to enable autonomy; .75 seconds without a valid update stops forwarding and latches manual mode. Recovery requires explicitly enabling navigation again.

Clock regression and a changed run ID in `/sim/status` clear observations. A monotonic-time simulator pose reset should also call `ros2 service call /perception/lanes/reset std_srvs/srv/Trigger '{}'` synchronously; relying on the later status message leaves a short detection delay. Reset/run metadata is not used for detecting paint.

Nav2 uses the custom `igvc_lane_layer`, independently of lidar. Every incoming cloud replaces the previous active lane set. The layer revisits previous bounds so the master costmap rebuild removes superseded marks; if no cloud arrives for .75 wall seconds, the lane set expires and those bounds are revisited. Lidar cannot erase current lane observations. Other obstacle layers can still keep a cell occupied. The detector's eight-second point history and the layer's .75-second cloud timeout are distinct.

The independent Unity ground-truth line guard prevents crossing the fixture's painted boundaries. It supplies no input to camera perception or Nav2. Live testing stopped lateral motion at approximately odom (-.0873, 1.931) m without crossing; reversing away worked. This is simulator enforcement evidence, not proof that perception alone prevents crossing.

Run synthetic checks from WSL with package source on PYTHONPATH:

```bash
PYTHONPATH="$PWD/ros2/src/igvc_perception" python3 -m unittest discover -s ros2/src/igvc_perception/test -v
```

Ten lane checks cover gray-road/barrel-band rejection, curved and converging lines, elevated thin paint with downward pitch, one-pixel paint versus isolated speckles, known 3 m/8 m projection and sky/horizon rejection. Six separate hazard checks cover the synthetic dark-bowl detector. General lighting, range accuracy and object-confusion cases remain validation tasks.

Historical stationary live validation on 2026-09-09 passed with the earlier brightness/opening configuration and a short wait for acquisition-time TF. Opening has since been removed for thin paint; the following measurements are not a fresh validation of that change. Two clean paint components produced points/debug at 4.80 Hz. The cloud contained 727 accumulated points, 543 at camera range 3–8 m. All 455 corresponding unique global costmap cells were lethal. Exact-time camera TF and finite odom points passed. Evidence: `artifacts/checks/lanes-live.json` and `lanes-live.png`; reproduce read-only with `bash tools/run_ros.sh python3 tools/verify_lanes.py` from WSL. These stationary results do not establish full-course detection reliability.

The dedicated loss-of-perception integration check passed: briefly suspending the owned detector disabled autonomy; restoring it did not rearm or move the robot. Evidence: `artifacts/checks/lane-watchdog-live.json`. The 2/4/6 m GPS sequence subsequently documented in GPS_WAYPOINTS.md completed with camera lanes active. The later imported-course full run completed under its documented configuration; see [FULL_COURSE.md](FULL_COURSE.md). Neither result establishes reliability on all generated variants.


## Downward camera and procedural validation

The camera now defaults to 10° downward about ROS +Y. Actual procedural-course frames exposed both ROI cropping and erosion of thin paint. After the current ROI/closing changes, two saved frames yielded 849 and 99 accepted pixels; the latter is only a short partial boundary, not a recovered complete line. The earlier ROI adjustment also produced 378 ground points from 401 accepted pixels using a fresh synchronized camera/TF acquisition.

**Seed 2027 / normal now completed 78/78 checkpoints with no line-guard blocks.** Lane generation uses shared joins to eliminate independently offset segment gaps, and barrel-band pixels are removed before component filtering so connected lane paint survives. The ten lane tests and six hazard tests pass. This completed run supersedes the earlier checkpoint-8 pauses for this seed/configuration; seed 2028 / easy and seed 2029 / hard also passed complete loops (78 and 81 checkpoints respectively). See [the procedural guide](PROCEDURAL_COURSES.md).

## Camera hazard observations

`hazards.py` detects the procedural fixture's compact dark bowl regions in RGB. Its ROI remains the lower 45% of the image (starting at 55% height), independently of the lane ROI. It uses dark/low-saturation thresholds, bounded area and aspect, convexity, border rejection and orange-context rejection; at most 1,500 pixels are passed to the same acquisition-time ground projection. It is an appearance heuristic, not stereo depth or general pothole reconstruction. Shadows and non-fixture dark objects can confuse it.

The node publishes `/perception/hazards/debug` (mono8) and `/perception/hazards/points` (odom PointCloud2). Fresh hazard component/projected-point counts are included in `/perception/lanes/status`. Hazard history is capped at 4,000 voxels and eight wall seconds. A separate Nav2 hazard layer replaces active observations and expires stale clouds after .75 wall seconds, independently of lidar clearing. The projected ground plane cannot represent a bowl's actual depressed surface accurately.

`/perception/lanes/healthy` distinguishes successful fresh RGB/CameraInfo/TF processing from finding paint. Declared unmarked sections use processing health while painted sections still require valid current lane observations. Hazard detections do not substitute for lane validity. Manifest pothole coordinates are used only by verification, GPS guide construction and offline scoring, not by the image detector.

See [PROCEDURAL_COURSES.md](PROCEDURAL_COURSES.md) for variant commands and sensor evidence, and [2026_WINNER_LESSONS.md](2026_WINNER_LESSONS.md) for the reference report's limited pothole claims.


Seed-2027 sensor verification passed with three fresh positive hazard frames, up to 139 projected points matching manifest pothole neighborhoods, and 1,461 matched costmap-cell observations at occupancy values at least 99. Manifest matching is verifier-only; observations can revisit the same cells and do not prove exclusive layer causality. The [sensor report](../artifacts/courses/seed-2027/previous-20260909T141807592352Z/sensors.json) records the evidence and limitations. Fifty-three camera checks passed with the 10° downward default. These results do not establish general pothole detection on real terrain.
