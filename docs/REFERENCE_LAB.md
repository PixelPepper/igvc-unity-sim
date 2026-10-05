# Reference Lab — planner, racing line and AI driver ghosts

Added 2026-10-01, ported from the Mechanics Sandbox (Hierarchical Pathfinding,
Racing Line, AI Drivers) and adapted to the R3-a and IGVC courses. Design and
worker ownership: [REFERENCE_LAB_PLAN.md](REFERENCE_LAB_PLAN.md).

## What it is — and is not

A **reference/audit tool** in the sandbox player's third tab, **Reference lab**.
It reads the WORLD course (`course.json`) that Unity renders, so it answers
"what would an ideal planner/driver with full course knowledge do?". It is
**not autonomy**: nothing is published to ROS, written to `autonomy.json`, or
given to the mission, planner, costmaps or controller.

- Drawings use layer 30 with no colliders (lidar raycasts use layer 0).
  `TransportProbe` removes layer 30 from the RGB camera before the depth camera
  copies it. The smoke run asserts both sensor cameras exclude it.
- Compute buttons follow the sandbox edit lock, so studies run only while the
  session is stopped. Ghost playback and the robot trail may run during a trial;
  they cost a little main-thread time, so leave them off for health-sensitive or
  accepted-baseline trials (processing health is the open priority-1 issue).
- Robot limits: footprint, track width and the 2.2 m/s ceiling are canonical.
  Acceleration 0.8, braking 1.2, lateral 1.0 m/s² and yaw 2 rad/s are
  **assumptions**. Lap times are lower bounds under those assumptions, not
  calibrated drivetrain predictions or competition evidence.

## Pipeline

1. **Geometry** (`Model/Geometry.cs`): course → 0.5 m corridor stations; every
   obstacle → a conservative capsule. Rasterised to a 0.1 m C-space grid grown
   by the inscribed half-width (0.52 m). A one-cell seam at the start line makes
   start→goal one full lap. Whole-body checks use the full 1.7 × 1.0 m footprint.
2. **Grid planner** (`Model/Pathfinding/`): Dijkstra, A*, weighted A*,
   bidirectional A*, JPS, flow field and HPA* (clusters 8–64, incremental
   update after course edits, smoothing), plus a seeded benchmark with
   optimality gap. Drawings show grid, clusters, entrances, abstract graph,
   animated expansions and raw/refined/smoothed paths.
3. **Racing line** (`Model/RacingLine/`): the planner route fixes which side of
   each obstacle to pass. Per-station bounds come from `Corridor.BoundsFromRoute`.
   Methods: centre, shortest, minimum curvature, compromise (box QP, projected
   Newton), GA and lap-time gradient descent. The lap simulator adds the
   differential-drive wheel cap v ≤ vmax / (1 + |κ|·b/2).
4. **AI driver ghosts** (`Model/Drivers/`): unicycle model with wheel speed and
   acceleration limits. Drivers: pure pursuit (RPP-like regulation), Stanley,
   sampling MPC with whole-body costs, and a neural range-sensor driver trained
   by seeded NeuroGA. Ghosts drive alone; metrics are lap time, contacts,
   minimum body clearance, cross-track error and µs per call.
5. **Robot trail**: optional recording of the real robot's axle path, with its
   deviation from the reference line and reference footprint contacts.

## Results on the frozen seed-2027 course (`3e653e4fc893`)

Recorded from `dotnet run -c Release --project tools/reference_lab -- check`:

| Item | Result |
| --- | --- |
| Grid | 463×525 cells, lap 149.8 m (corridor 155.2 m) |
| Planner, one lap | Dijkstra 67,408 expansions / 14 ms; JPS 595 / 8 ms; HPA* (16²) 1,350 / 0.8 ms at +1.33% cost |
| Line lap bound at 2.2 m/s | centre 86.5 s; min-curvature 70.9 s; compromise 67.9 s; lap-time descent 70.6 s |
| Ghosts at 0.6 m/s (bound 255.4 s) | pure pursuit 261.1 s; Stanley 256.1 s; MPC 258.9 s; 0 contacts |
| Ghosts at 1.2 m/s (bound 128.1 s) | pure pursuit 133.7 s; Stanley 128.4 s; MPC 128.6 s; 0 contacts |

Ghost body clearance on this course is only 0.02–0.05 m, and 2.2 m/s ghost runs
are untested. The real sensor-led robot's accepted lap was 363 s at 0.6 m/s,
with stops and recovery. The gap to a ~255 s ideal tracker shows how much time
perception, planning and recovery cost; it is not a target the robot can reach
without course knowledge.

## Use

Sandbox: open **Reference lab** → *Plan route* (pick algorithm/cluster size;
toggle drawing layers) → *Optimise line* or *Compare all methods* → *Start
ghosts* (1×/4×/16×). *Train neural driver* runs 20 seeded generations. *Record
robot trail* compares a real trial with the line. *Show reference drawings*
hides everything.

Checks (no Unity; separate build slots for parallel work):

```powershell
dotnet run -c Release --project tools/reference_lab -- check            # all, uses the frozen course if present
$env:REFLAB_ONLY='pathfinding'; dotnet run --project tools/reference_lab -- check
```

In Unity: menu **IGVC / Run Reference Lab Checks**, or batch
`-executeMethod ReferenceLabChecks.Run` (88 checks; the same model checks plus
shader and layer checks). The `--sandbox-smoke` run writes
`ui-smoke-reference.json` (route, line, ghosts, sensor-camera exclusion) and the
screenshots `sandbox-reference.png` and `sandbox-reference-results.png`.

## Validation, 2026-10-01

- dotnet: `REFERENCE_LAB_CHECKS passed=86 failed=0` (Release, 7.3 s).
- Unity 6000.3.23f1 batch: `IGVC_REFERENCE_CHECKS_OK passed=88`, no compiler
  warnings in the new files.
- Sandbox player rebuilt. An isolated smoke run used port 10001 and a copy of the
  frozen course in `artifacts/reference_lab/smoke/`. No ROS, and the TCP 10000
  lease was not touched. Results: existing editor smoke passed;
  reference smoke `{"passed":true,"route":true,"line":true,"ghosts":true,
  "sensor_cameras_exclude_reference":true,"sensor_cameras":2}`.
- Not done: mouse-level UI automation beyond the smoke and batch entry points.

## Live A/B, 2026-10-02 (`artifacts/sandbox/batch/ab-reference-load-1/`)

Six alternating real-time sandbox trials, seed 2027 normal, accepted settings
(RPP, checked path, 0.6 m/s), RViz open. The "reference-load" arm ran looping ghosts
(4 laps per trial), trail recording and all drawings during the trial. Run with
`tools/sandbox.ps1 -Batch <plan.json>`; summary from `tools/sandbox_batch_report.py`.
Ghost runs at 1.8 and 2.2 m/s are in the dotnet checks: all trackers finished
with 0 contacts, but body clearance was only 0.01–0.03 m.

| Arm | 6/6 | Health samples failed | Frame mean / p99 | Endings |
| --- | --- | --- | --- | --- |
| baseline | 2 / 3 | 5 of 10,798 (all in trial 1) | 16.68 / 16.99 ms | 6/6, stall at 4/6, 6/6 |
| reference-load | 0 / 3 | 0 of 6,096 | 16.68 / 17.04 ms | stall at 4/6, Nav2 goal rejected at start (12 s), recovery budget at 4/6 |

Interpretation, bounded by n = 3 per arm:
- **No measured cost.** The Reference lab's load showed no effect on processing health or
  Unity frame time.
- **The success-rate difference is not attributable to the lab.**
  - The same stall ("no observed collision-free backup") also hit the baseline.
  - Three of the four navigation failures ended near (−7.3, 21.2) on the west leg (barrels 017/011/005,
    barricade 007). Two of them, one per arm, ended at the identical pose.
  - The 12 s failure is a startup race: a single Nav2 goal rejection ends the mission.
  - The mechanism by which the lab could affect navigation is CPU timing, and neither health nor frame time moved.
- **No run passed the strict audit.**
  - Baseline trial 1 had 5 processing-health failures with no lab load, the open priority-1 issue.
  - Baseline trial 5 failed `ordered_world_full_loop` with a 0.3998 m return.
- **The accepted 6/6 baseline is not repeatable on this machine today**: 2 of 3 baseline trials.

## Source map

| Path (under `unity/IGVCSim/Assets/IGVC/`) | Content |
| --- | --- |
| `Runtime/Reference/Model/Geometry.cs` | V2, Capsule, CourseGeometry, RobotLimits, Corridor, OccupancyGrid, Rasterizer |
| `Runtime/Reference/Model/Pathfinding/` | GridMap, Searchers, Hpa, PathBenchmark, MapPresets, PathfindingStudy, checks |
| `Runtime/Reference/Model/RacingLine/` | RaceTrack, LapSim, LineOptimisers, RacingLineStudy, checks |
| `Runtime/Reference/Model/Drivers/` | DiffDrive, Drivers, Evolution, DriversStudy, checks |
| `Runtime/Reference/Model/Checks/` | CheckContext, registry, synthetic courses, geometry checks |
| `Runtime/Reference/View/` | ReferenceOverlay (+ layer), ReferenceLab orchestrator, per-study views |
| `Runtime/SandboxPanel.cs`, `Resources/SandboxPanel.uxml/.uss` | Reference lab tab and smoke pass |
| `Runtime/TransportProbe.cs` | sensor culling-mask exclusion; read-only axle pose |
| `Resources/IGVCReferenceOverlay.shader`, `Editor/ReferenceLabChecks.cs` | overlay shader; Unity check entry |
| `tools/reference_lab/` | dotnet harness compiling only `Model/` |
