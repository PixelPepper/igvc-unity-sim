---
id: T-0090
title: Drive the traced AutoNav map with realistic visual conditions
status: changes-requested
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0090-reference-drive-opus
base: 12e84df8c967b4b3d8cb217a51ec5d20d9619e5f
candidate: 2d98b4476371eeec93e99fd94537d0f4cd648f42
claim: implemented
lease: none
updated: 2026-10-13
---

# T-0090: Traced-map driving and realistic conditions

## Packet

Human requests robot on the newly accepted image-traced map, bounded runs, better barrels and lighting/shadows, reusing Claude's existing realism work. Preserve the T0089 diagram geometry. Runtime policy remains sensor-led with only sanitized broad destinations. No geometry leakage, guard weakening, unreviewed whole-branch imports, or blocked T0084 retry. T70/T86/T85/T88 ownership unchanged.

First slice is READ-ONLY integration discovery: five minutes active. Read T0089 final log/source; relevant R3aDriveBuild, TransportProbe, SoonerCourseBuild, and sim-realism branch SimConditions/RealisticObstacles and their integration. Identify minimal nonconflicting owned paths, scene/launch/mission interface and exact existing source commits. Propose practical robot placement and first test protocol on this map, acknowledging incomplete auditor compatibility and possible impassable traced gaps. Return plan <=300 words plus evidence path. No source edits/tests/builds/live/providers/delegation. Root independently examines managed launch and validation. After plan root will dispatch a concrete implementation slice.

## Log

### 2026-10-13T00:36:49.879326-07:00 · gpt-6-astra → team · ANSWER
Direct user authorizes bot running on the new map, test runs, and realistic conditions/lighting/shadows/barrel visuals. This is new scope after T0089 completion; prior no-live restriction superseded for bounded trials here. It does not authorize retrying T0084 or changing autonomy/auditor guards.

### 2026-10-13T00:36:49.879326-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
reference-driving-discovery-r1: existing linked interactive session only. Read packet and append ACK, then bounded plan to artifacts/agents/T-0090/discovery-plan.md and this log. Five-minute read-only task. No source/Unity/provider/new worker actions. Preserve all existing owners.

### 2026-10-13T00:37:20-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
ACK reference-driving-discovery-r1 (nonce igvc-drive-43437c0e83). Read-only, five-minute discovery plan, no source edits, tests, Unity runs, providers or delegation.

### 2026-10-13T00:37:45-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
```text
reference-driving-discovery-r1 is done (read-only). Plan: artifacts/agents/T-0090/discovery-plan.md.
Facts:
  - The sandbox player (SandboxBuild -> R3aDriveBuild, SoonerAutoNav.unity) loads courses at runtime through
    --course-manifest -> CourseVariant.Load (TransportProbe.cs:107-112).
  - The mission is a sanitized autonomy.json from export_autonomy_mission.
  - The T-0089 map is a separate editor scene with no robot or manifest.
Recommendation: export, do not fork scenes.
  A: tools/reference_map_course.py emits course.json and autonomy.json from the literal trace. Origin at the
     North Start/Finish line heading south. 95 drums become barrels (black drums need BarrelColor). The ramp
     goes in ramps[]. About 6 broad destinations include the 4 stars.
  B: an optional manifest paint_polylines field, so CourseVariant renders and guards two independent
     variable-width boundaries. World-only data.
  C: realism reuse after scoped reviews: e8a5f02 (SimConditions, lighting, shadows, --conditions) plus the
     parked RealisticObstacles.cs (uncommitted; record hashes first). The perception commits b4054a0 and
     5931c61 are excluded unless reviewed.
Test protocol: one ideal visual-check lap under the live lease, then 3 single laps (ideal, clear-noon,
  evening) with the audit and the T-0087 report.
Risks:
  - Some corridors may be impassable for the 1.0 x 1.7 m robot (drums within 0.15 m of the tape, a ~3.05 m
    lane): report failures, never move geometry.
  - The auditor and judge expect a generator centreline, so verdicts may be unknown.
  - Ownership overlaps: CourseVariant.cs (parked T-0086 inputs), SandboxDocument.cs (T-0070 reservation),
    sandbox.ps1 (T-0088).
Usage: unavailable.
```

### 2026-10-13T00:40:43.564144-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION
Accept discovery as design input; select separate drivable scene to avoid altering the accepted diagram through the old symmetric loader and colliding with T70/T86/T88 owners. Implement bounded complete source slice in assigned snapshot worktree. Existing interactive exact Opus owns this task, no other implementer.

Owned paths ONLY (all NEW): unity/IGVCSim/Assets/IGVC/Editor/ReferenceDriveBuild.cs(.meta), ReferenceDriveChecks.cs(.meta), RealismAssets.cs(.meta); Runtime/ReferenceDriveConditions.cs(.meta), SimConditions.cs(.meta), RealisticObstacles.cs(.meta); Assets/IGVC/Realism/ and Realism.meta (exact local licensed source assets from e8a5f02); tools/reference_map_mission.py, tools/reference-map.ps1, tools/tests/test_reference_map_mission.py, docs/REFERENCE_MAP_DRIVING.md. Do not change any existing source, project settings, T0089 geometry, CourseVariant, TransportProbe, robot/sensor mounts, SandboxDocument/Panel, sandbox.ps1, autonomy policy or auditor. If truly needed, hand back exact blocker instead of expanding.

Source design/acceptance:
- Build a NEW ReferenceAutoNav2027Drive scene and separate artifacts/build-reference-drive/IGVCReferenceDrive.exe with existing R3aDriveBuild robot/ROS/sensors, importing the accepted ReferenceAutoNav2027 scene additively. Runtime uses baked geometry (NO --course-manifest replacing it); source/reference assets stay unchanged. Reuse generated R3aDrive scene if valid or generate it with existing code. Existing generators may save TransportProbe.unity: protect and restore exact preexisting scene bytes in finally, and report this. Root will independently bind protected preimages.
- Align the entire environment so spawn is the center of NORTH start line (pixel960.5,439) at odom0, heading NORTH/up image (Unity+z, ROS+X). This traverses top->left four stars->bottom->south finish. Do not reverse orientation. Big drive wheels FRONT. Robot stays at odomorigin; never export course geometry into navigation. Use original ground/ramp support colliders with ConfigureTerrain. Derive simulator-only LaneBoundaryGuard segments from the actual two saved tape meshes (same coordinate transform); preserve footprint/guards. Scoring mode remains explicit, as existing sensor-led launches. Strip all EditorOnly diagram annotations and duplicate cameras/lights from drivable scene so no labels/stars in sensors. Keep spectator follow/orbit.
- Reuse bounded parked SimConditions/RealismAssets/RealisticObstacles implementation and CC0 textures (originals read-only, pinned at artifacts/agents/T-0090/parked-preimages.json). Do NOT cherry-pick whole e8a5f02 or other unreviewed branch edits. Adapt under owned paths. Higher quality barrel visual meshes with ribs, top, base and reflective bands while retaining all 95 positions/colors and existing collision envelopes; ensure saved mesh/material assets survive reopen/build. World-metre UV asphalt/ground textures. Lit white tape and ramp, sky, real soft shadows. New scene-local ReferenceDriveConditions component applies explicit clear-noon, overcast, low-sun presets from --reference-conditions before TransportProbe sensor setup, logs selected settings into unique run directory. No rain/physics/sensor realism claims, no random settings. No project-wide graphics changes; ensure selected shader variants available safely in this new player. Avoid depth-camera sky/fog contamination.
- New Python mission exporter emits ONLY sanitized GPS origin/goals/max_speed schema (existing sensor_course.destinations) to autonomy.json: top-right broad gate, four pictured waypoint stars, south-finish broad destination = six, with sensible broad radii; no route/heading/WORLD data. Exact transform is independent easy to inspect. Mission/trial not full-lap audited: existing centerline auditor incompatible; never fabricate course.json/guide route or weaken gates. First sensor-led runs diagnostic progress/health only, not competition success.
- New managed tools/reference-map.ps1 is distinct from sandbox: build/start or bounded trial(s), default visible when human invokes. Hold all three exclusive simulator locks before process/ports/checks/build/runtime; refuse ANY Unity/editor/player/occupied port including own newname; only cleanup processes this invocation owns. Use existing managed ros_session.py and run_ros.sh, overlay verifier, nav profile/clock admission before motion, unique immutable run dir, preserve failed runs. Start with bounded sensor smoke and later root-authorized two diagnostic attempts clear-noon and low-sun, speed ceiling0.6, max180seconds each, no retry. Avoid claiming full independent audit compatibility. No automatic reset/retry, no external stop ownership, no live/build by worker. Root can use a small separate harness for actual trial if launcher not ready.
- Provide editor validation and captures for saved scene (robot/mounts/support/spawn/guard/95drums/no sensor-visible annotations, actual rendered lighting and barrel detail). Behaviour tests for GPS transform/schema reject/finite bounds if applicable. Root compiles/generates/builds/renders only after Sonnet+Sol source acceptance; tests unrun until rootlocked checks.

20-minute active implementation bound, no provider/delegation/Unity/heavy tests/live. Static checks and source edits/commit allowed. Commit ONLY owned source/meta/texture/license paths; no docs/agents commit. Append ACK and final <=300-word handback with commit, exact files and entry commands plus risks. User already authorizes these implementation/build/trial actions; do not request manual relay. On genuine scope blocker stop and report exact needed change. Preserve T84 block and other owners.

### 2026-10-13T00:40:43.564144-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
reference-driving-implementation-r1. Worktree C:/Users/brand/.codex/worktrees/igvc-t0090-reference-drive/IGVC SIM, clean snapshot 12e84df8c967b4b3d8cb217a51ec5d20d9619e5f. Discovery assignment ended. Scope/acceptance in preceding DECISION; implementation with existing linked session, no duplicate.

### 2026-10-13T00:41:17-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
ACK reference-driving-implementation-r1 (nonce igvc-drive-impl-595dd6e8e4). New-only owned paths in worktree igvc-t0090-reference-drive at 12e84df, with a 20-minute active bound. Source only: no Unity runs, live runs or providers. I will hand back a complete or partial scoped commit, or the exact blocker.

### 2026-10-13T00:45:13.699053-07:00 · gpt-6-astra → team · NOTE
Actual linked exact-Opus implementation ACK at07:41:02.336Z and canonical00:41:17 collected; no duplicate. Discovery courier exit0/11.640s/USD.036141; implementation courier exit0/23.016s/USD.0438198; target-session usage unavailable. Root prepared immutable source/parked preimages and new-only binding/review harness. Initial availability all3locks found no Unity/player/ROS but overlay command had shell-space quoting error; preserved initial-availability failure, not evidence of stale overlay. Corrected invocation with script path verified three installed perception modules exactly match source, all3locks released00:41:53.722. No Unity/build/live attempted yet.

### 2026-10-13T00:48:47-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
```text
reference-driving-implementation-r1 (nonce igvc-drive-impl-595dd6e8e4). About 8 minutes active, source only.
Candidate: 2d98b4476371eeec93e99fd94537d0f4cd648f42 on the worktree branch (base 12e84df). 45 NEW files; no
  existing file changed. Worktree clean.
Files:
  - Editor: ReferenceDriveBuild, ReferenceDriveChecks, RealismAssets (.cs + .meta)
  - Runtime: ReferenceDriveConditions, RealisticObstacles (.cs + .meta)
  - Assets/IGVC/Realism/** and Realism.meta: exact git-archive copy of e8a5f02's CC0 textures and LICENSE
  - tools/reference_map_mission.py, tools/tests/test_reference_map_mission.py, tools/reference-map.ps1
  - docs/REFERENCE_MAP_DRIVING.md
Entry points:
  - Unity: -executeMethod ReferenceDriveBuild.Build (scene, checks, player) or .CreateSceneOnly
  - tools/reference-map.ps1 -Action build|start|smoke [-Conditions clear-noon|overcast|low-sun] [-Seconds <=180]
Design:
  - R3aDriveBuild.CreateScene, then the probe props are removed and ReferenceAutoNav2027 is merged in
    additively, with geometry unchanged and the map root translated by -World(960.5, 439).
  - Robot at odom 0 heading north (Unity +z). Annotations, TextMesh, the map camera and the map lights are
    stripped.
  - Lane guard from both edges of the saved tape meshes (odom = (z, -x)), with CanOccupy(0,0,0) asserted.
    Terrain support is the ground plus 3 ramp colliders, serialized via ConfigureLaneGuard/ConfigureTerrain.
  - Drums keep their colliders. The primitive renderer is hidden, and a persistent 3-submesh drum visual sits
    inside the envelope.
  - One soft sun plus a procedural sky; presets are applied in Awake, with no fog.
  - Protected files (TransportProbe.unity; EditorBuildSettings, ProjectSettings, Editor, Quality and Graphics
    settings; R3aDrive.unity; lidar evidence) are byte-restored in a finally block and reported in
    protected-restore.json.
  - Mission: six sanitized goals (gate, 4 stars, south finish), validated against sensor_course.destinations.
Checks: static only. Balanced C#; py_compile OK; PowerShell parses with 0 errors. UNRUN: Unity compile,
  generation, checks, captures, the build, the Python tests and any trial.
Risks:
  - MergeScenes/Find path assumptions and robot.forward orientation are untested.
  - Editor captures use Apply() and modify RenderSettings, but the scene is not resaved.
  - The launcher drives no mission (the trial is your root harness).
  - SimConditions.cs is not created; the presets live in ReferenceDriveConditions.
  - Possibly impassable traced passages.
Usage: unavailable.
```

### 2026-10-13T00:55:11.471347-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION
Collected candidate2d98b4476371eeec93e99fd94537d0f4cd648f42, clean45newpaths/11protected/31parkedpreimages bound in source-binding-r1.json. Exact requested Sonnet review source-review-r1 hit240s localtimeout with EMPTYstdout/stderr: no result/modelUsage/cost/provider-exit confirmation. Review assignment ended; no automatic retry/substitution. No review acceptance or Unity/build/live yet. Preserve failure. Separate actionable root source findings in artifacts/agents/T-0090/root-source-notes-r1.md require revision. Source fixes are authorized independently; further Sonnet call awaits direct approval, not inferred from this fix.

### 2026-10-13T00:55:11.471347-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
reference-driving-launcher-fix-r1, existing linked owner/worktree only, 12-minute active source bound. Read root-source-notes-r1.md and fix launcher ownership/bounded cleanup before handback. No other files/owners/providers/Unity/live/tests. User wants runs, so complete a reusable `trial` action as part of launcher instead of leaving it entirely to an unreviewed root harness. Additional owned NEW paths tools/reference_map_trial.py and tools/tests/test_reference_map_trial.py. This Python trial driver may reuse sandbox_session.RosControl.verify_sim_time (strict GetParameters/cleanup), capture_rgb and record_sensor_health, then the UNCHANGED sensor_course.py with sanitized mission and known profile. Save clock admission, sensor smoke (RGB, depth, lidar, odom actually received), first RGB PNG, applied conditions, run report/capture paths. Refuse motion without positive clocks and streams. Fixed speed<=.6 and timeout<=180. No automatic retry. Launcher starts its own managed nav session only after confirmed idle all managed ROS groups; verifies WSL checks exit0, clears IGVC_INSTANCE for domain42, refuses R3aDrive/R3aInspection/IGVC/Unity. Cleanup only recorded newly-owned sessions/PIDs; confirm exits, don't quietly release on cleanup failure. Trial mission child should be reaped/cancelled with SIGINT and bounded escalation only ownedgroup; always gate autonomy off before nav stop. Root will independently inspect and approve source after required reviews; no actual trial by worker. Tests source only until root locks. Root notes include earlyplayerexitsmustfail, finitebuilddeadline, preserveallfailedruns. Hand back <=300words with newcommit and limitations. Do not request provider review yourself or retry timed-out review.
