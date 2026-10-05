# Reference Lab — port plan (HPA*/accelerated pathfinding, racing line, AI drivers)

Prepared 2026-10-01. Source: the Mechanics Sandbox Unity project
(`AI/HierarchicalPathfinding`, `Vehicles/RacingLine`, `Vehicles/AiDrivers`), which
lives in a temporary Claude scratch folder (also mapped as `M:\MechanicsSandbox`).
Copy what is needed now; do not reference that path from this repository.

## 1. What this adds and the boundary it must respect

The Reference Lab is an **oracle / audit-side** toolset. It reads the WORLD
course (`course.json` → `CourseVariant.Manifest`), which CLAUDE.md reserves for
rendering and independent offline auditing. It must therefore:

- never publish anything to ROS, never write `autonomy.json`, never feed the
  mission, planner, costmaps or controller;
- render only on a dedicated layer (`ReferenceLayer`, index 30) that has **no
  colliders** (lidar raycasts use layer 0) and is **removed from the sensor RGB
  and depth camera culling masks**;
- be off by default and never compute while a trial is running unless the user
  asks (it costs CPU/GPU, and processing-health is the open priority-1 issue);
- label every result "reference (full course knowledge) — not autonomy".

Uses: (a) see what an ideal planner does on an edited course (HPA*, JPS, A*,
…, with the abstraction visualised); (b) a lap-time lower bound for the robot's
limits on the actual corridor (priority 4: speed vs the 360 s budget);
(c) ghost drivers (pure pursuit ≈ Nav2 RPP, Stanley, sampling MPC ≈ MPPI/DWA,
and a range-sensor neural driver) driving that line with the R3-a's
differential-drive limits, compared against the recorded sensor-led trajectory.

## 2. Pipeline

```
course.json ─► CourseGeometry (pure C#) ─► Rasterizer ─► GridMap (0.10 m, C-space inflated by half-width+pad)
                                   │                          │
                                   │                          ▼
                                   │                 Pathfinding: Dijkstra/A*/WA*/BiA*/JPS/HPA*(+smooth)/FlowField
                                   │                          │  homotopy (which side of each obstacle)
                                   ▼                          ▼
                           Corridor stations ──► per-station free interval [lo,hi] chosen by the HPA* path
                                                              │
                                                              ▼
                     Racing line: centre / shortest / min-curvature / compromise QP / GA / lap-time gradient
                     LapSim: point mass + diff-drive wheel-speed limit  v ≤ vmax / (1 + |κ|·b/2)
                                                              │
                                                              ▼
                     AI drivers (unicycle, wheel accel/speed limits) → ghosts, metrics, collisions vs footprint
```

## 3. Code layout and ownership (one owner per file)

All runtime code lives in the existing `Assembly-CSharp` (no asmdefs in this project).

| Path (under `unity/IGVCSim/Assets/IGVC/`) | Owner | Rules |
| --- | --- | --- |
| `Runtime/Reference/Model/Geometry.cs` (V2, CourseGeometry, Corridor, Rasterizer, RobotLimits) | integrator | Shared API; workers request changes, don't edit |
| `Runtime/Reference/Model/Pathfinding/*.cs` | worker A | namespace `IGVC.Reference.Pathfinding` |
| `Runtime/Reference/Model/RacingLine/*.cs` | worker B | namespace `IGVC.Reference.RacingLine` |
| `Runtime/Reference/Model/Drivers/*.cs` | worker B | namespace `IGVC.Reference.Drivers` |
| `Runtime/Reference/Model/<Area>/<Area>Checks.cs` | owner of the area | `public static void Run(CheckContext c)`; `Model/Checks/` (context, registry, geometry checks) is integrator-owned |
| `Runtime/Reference/View/ReferenceOverlay.cs`, `ReferenceLab.cs`, `ReferenceLayer.cs` | integrator | Unity drawing + orchestration |
| `Runtime/Reference/View/PathfindingView.cs` | worker A | Uses `ReferenceOverlay` API only |
| `Runtime/Reference/View/RacingLineView.cs`, `DriversView.cs` | worker B | Uses `ReferenceOverlay` API only |
| `Runtime/SandboxPanel.cs`, `Runtime/TransportProbe.cs` (culling-mask line), `Editor/ReferenceLabChecks.cs` | integrator | Minimal edits; preserve existing uncommitted work |
| `tools/reference_lab/` (dotnet harness + CLI report) | integrator | Compiles `Model/**` only |
| `docs/REFERENCE_LAB.md`, handoff/index updates | integrator | |

**Model code rules** (so it compiles under both Unity and `dotnet`):
no `UnityEngine`/`UnityEditor` references, C# 9 (`LangVersion 9`: no file-scoped
namespaces, global usings, `required`, raw strings), `double` maths, our `V2`
struct, seeded RNG only, no static mutable state, no threads. Match repository
style: compact code, short comments only where the reason is not obvious.

## 4. Verification

1. `dotnet run --project tools/reference_lab -- check` (set `REFLAB_ONLY=pathfinding|vehicles` to build one worker's folders with separate obj dirs) runs every `*Checks.Run`
   against synthetic maps **and** the frozen course
   `artifacts/sandbox/runs/20261002T035715-45c98a0f/course.json` (falls back to
   synthetic only if absent). Fast loop for workers; no Unity needed.
2. Unity batch `-executeMethod ReferenceLabChecks.Run` calls the same checks
   inside Unity (integrator only; one Unity process per project).
3. Checks must test behaviour, not mirror code: optimality vs Dijkstra, JPS cost
   = A* cost, HPA* completeness + stated suboptimality bound + incremental
   update = full rebuild, rasteriser keeps start cell free and blocks every
   obstacle centre, QP KKT ≤ tolerance, line inside bounds, lap-sim respects every
   limit, min-curvature ≤ centre-line lap time, each tracker completes the seed
   course without footprint contact, deterministic results for a fixed seed.
4. Integrator: sandbox build, `--sandbox-smoke` still passes, visual check of
   the tab/overlays, sensor camera culling masks exclude layer 30.

## 5. Worker briefs (summary — full text in the Agent prompts)

- **Worker A — pathfinding**: port `GridMap`, `Searchers` (Dijkstra, A*, WA*,
  bidirectional A*, JPS, flow field), `Hpa` (build, incremental update, query,
  smoothing), `PathBenchmark`; add `PathfindingView` drawing grid/clusters/
  entrances/abstract graph/expansion order/path; `PathfindingChecks`.
- **Worker B — racing line + drivers**: build a `RaceTrack` from corridor
  stations (not Catmull-Rom control points); port `BoxQP`, geometric lines,
  `KnotLine`, `LineGA`, gradient lap-time optimiser, `LapSim` with a robot
  vehicle; port drivers to a unicycle/diff-drive model (pure pursuit, Stanley,
  sampling MPC, neural + NeuroGA with a seeded quick-train), `RaceSim`; views;
  `RacingLineChecks`, `DriversChecks`.

Each worker: own files only, stop after checks pass or after reporting a
blocker, hand back ≤300 words (files, check output summary, risks). No Unity
launches, no ROS, no git commits, no edits outside owned paths.

## 6. Integrator sequence

1. Foundation: `Geometry.cs`, `ReferenceLayer`, `ReferenceOverlay` API, dotnet harness.
2. Launch workers A and B in parallel (background).
3. Meanwhile: `ReferenceLab` orchestrator + Sandbox "Reference lab" tab, culling masks, editor check entry.
4. Integrate worker output, run dotnet checks, Unity batch checks, sandbox build + smoke.
5. Docs (`docs/REFERENCE_LAB.md`, handoff/file index), report implemented / tested / pending separately.
