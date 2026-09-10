# Moving terrain perception baseline

Historical baseline, 2026-09-09: this experiment showed the then-current perception was **not ready for autonomous ramp traversal**. Suspension and transforms passed while depth misclassified visible ground and RGB reported lanes on an unpainted bench. No perception thresholds or navigation algorithms changed in this slice.

The subsequent [ramp-edge perception integration](RAMP_EDGE_PERCEPTION.md) replaces infinite-plane extrapolation with observed depth normals/connectivity and depth-supported RGB projection. Its seed-2027 autonomous loop completed 82/82 with the 12-check audit passing. The retained failure measurements below describe the earlier implementation, not the current result. The same captured fixture now produces zero obstacle points versus 335 under the legacy plane method; this single replay is not general semantic-ground proof.

## Implemented

- `perception-start` / `perception-stop` manage camera processors without Nav2. Managed navigation and perception sessions are mutually exclusive, with a shared process lock. Stop confirms group termination before discarding ownership. Unmanaged manual launches remain the operator's responsibility.
- `tools/observe_terrain_perception.py` records health, fit status, gaps and obstacle geometry without commands. Surveyed ramp geometry is test-only, never an autonomy input.
- `tools/capture_depth_fixture.py` saves one recently received depth/CameraInfo pair and exact acquisition-time optical-to-odom TF. Receipt age is bounded; acquisition age relative to current simulation time is not independently checked. NPZ output contains no object arrays and cannot overwrite an existing fixture.
- `tools/replay_depth_fixture.py` replays spatial filtering offline. It does not test transport or freshness behavior.

## Evidence

`artifacts/checks/terrain-perception-motion.json`: manual 0.6 m/s traversal reached x=11.1243 m; all 10 suspension/TF checks passed with 1,029 matched pairs. This is motion evidence only.

`artifacts/checks/terrain-perception-baseline.json`: 45 seconds, all six observed topics present, no decode errors. Depth reported 224 valid fits and one rejected fit. Among published obstacles, **39,773 repeated observations** matched surveyed ground within 35 mm, excluding edges, transitions and the caster bump. These are repeated pixel observations, not distinct obstacles. Phase bins use latest received odometry and are approximate. Example plane metadata is receipt context, not an exact-stamp causal join.

RGB reported 96 valid current lane detections despite no intentional lane paint. Their visual source remains unidentified because this observer does not capture RGB masks. No paint is expected; an invalid lane status alone is not a processing failure.

`artifacts/checks/terrain-depth-origin.npz` and `terrain-depth-origin-replay.json`: one captured frame replays to 2,667 depth points, 1,600 lower-image fit candidates, 100% inlier fraction, 11.15 mm fit RMS and 335 obstacle points in the visible ramp region. The fitted 0.88-degree plane describes near support, not every visible surface. High consensus does not validate infinite-plane extrapolation.

The perception package built. Live lifecycle checks verified startup, idempotent startup, rejection of Nav2 while perception is managed, stop and restart. `terrain-perception-managed.json` observed all topics after restart with no decode errors. Unity assets/source did not change; no player rebuild was needed.

After adding the shared lock and confirmed process-group cleanup, stop/restart passed again. `perception-session-lifecycle.json` records two simultaneous starts sharing PID 1783 and a rejected navigation start. A follow-up review found no remaining material lifecycle issues; syntax checks passed for the four Python tools.

## Repeat

From the repository root, with no other command publisher:

```powershell
.\tools\igvc.ps1 stop
.\tools\igvc.ps1 terrain-start -Visible
.\tools\igvc.ps1 perception-start
```

Run the observer in one terminal and the bounded manual traversal in another. Choose new report names to preserve evidence:

```powershell
wsl -d Ubuntu-24.04 -- bash tools/run_ros.sh python3 tools/observe_terrain_perception.py --duration 45 --report artifacts/checks/terrain-perception-new.json
wsl -d Ubuntu-24.04 -- bash tools/run_ros.sh python3 tools/verify_caster_suspension.py --speed 0.6 --report artifacts/checks/terrain-motion-new.json
```

Capture while stopped at an interesting view, using an existing output directory:

```powershell
wsl -d Ubuntu-24.04 -- bash tools/run_ros.sh python3 tools/capture_depth_fixture.py --output artifacts/checks/depth-new.npz --timeout 10
wsl -d Ubuntu-24.04 -- bash tools/run_ros.sh python3 tools/replay_depth_fixture.py artifacts/checks/depth-new.npz --report artifacts/checks/depth-new-replay.json
.\tools\igvc.ps1 perception-stop
```

## Remaining acceptance work

The new spatially supported classifier and depth-supported RGB projection passed the documented fixture and loop. Broaden recorded-acquisition coverage beyond those observations. Preserve positive obstacles and negative hazards; raising height thresholds alone can hide real obstacles. Test approach, crest, descent, raised obstacle tops and missing depth. RGB projections need depth/surface agreement; capture masks to diagnose unpainted-bench detections. Preserve freshness/watchdogs, then repeat moving-bench and flat-course regressions before claiming autonomous ramp support.
