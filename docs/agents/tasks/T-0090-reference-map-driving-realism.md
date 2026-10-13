---
id: T-0090
title: Drive the traced AutoNav map with realistic visual conditions
status: in-progress
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0090-reference-drive-opus
base: 12e84df8c967b4b3d8cb217a51ec5d20d9619e5f
candidate: e6fb64b1fcb5f622c282923a238ec8ac05f3a513
claim: tested
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

### 2026-10-13T00:55:33-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
ACK reference-driving-launcher-fix-r1 (nonce igvc-drive-fix-2443f8b74d). 12-minute source-only bound in the same worktree; new owned paths include reference_map_trial.py and its test.

### 2026-10-13T00:58:45-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
```text
reference-driving-launcher-fix-r1 (nonce igvc-drive-fix-2443f8b74d). About 4 minutes active, source only.
Candidate: 2d9c802122ee6aa812c0de06a19ab728eaf74e8a (parent 2d98b44). Files: tools/reference-map.ps1 (rewritten),
  docs/REFERENCE_MAP_DRIVING.md, NEW tools/reference_map_trial.py and NEW tools/tests/test_reference_map_trial.py.
Root notes addressed:
  - Busy predicate covers Unity, IGVC*, R3a*, *Terrain* and *Inspection* (incl. R3aDrive and R3aInspection).
    Get-CimInstance/Get-NetTCPConnection use -ErrorAction Stop; a WSL ss failure stops the run.
  - Before starting, ros_session status r3a/nav/perception must all report stopped. The r3a session counts as
    owned ONLY if start prints "ROS started: PID n"; "already running" is refused, never claimed or stopped.
    IGVC_INSTANCE is cleared for domain 42, and every WSL step is exit-checked.
  - Cleanup stops only the owned player/build and waits for exit; r3a stop is exit-checked. On any unconfirmed
    step it writes artifacts/iterations/reference-drive-ownership-retained.json and the script exits non-zero.
    Locks are disposed only in finally. Process exit would release them anyway; this is noted honestly.
  - Smoke: an early player exit is a failure, and it is labelled process survival, not a sensor check.
    The build is bounded to 45 minutes and kills only its own child. Failed runs are kept.
Trial action: player and owned r3a session, then reference_map_trial.py:
  1. refuse an existing nav.json;
  2. gate off and pose reset;
  3. sensor smoke (clock>0, RGB, depth, /scan, /odom received; first-rgb.png);
  4. profile and its own nav start;
  5. clock admission with the same rule as sandbox_session;
  6. the unchanged sensor_course.py at --timeout <=180 and speed <=0.6.
  The mission group gets SIGINT, then bounded SIGTERM/SIGKILL; gate off before nav stop. Exit 3 means cleanup
  was not confirmed. trial-report.json records everything. No retry.
Checks: PowerShell parses with 0 errors; py_compile OK. UNRUN: all tests, Unity, live runs.
Limits:
  - capture_rgb/record_sensor_health do not exist under those names; I wrote a minimal read-only smoke
    subscriber instead.
  - The 10 s bridge wait is fixed; the trial gates on streams.
  - sensor_course still prints its own diagnostics; there is no full-lap audit.
Usage: unavailable.
```

### 2026-10-13T01:05:08.131442-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
reference-driving-cleanup-fix-r2. Human explicitly approved one focused exact Sonnet review up to480s/USD3, then build and two diagnostic runs. Approval is recorded; no other timeout retry authorized. Candidate2d9c802 bound47newpaths/11protected/31parked unchanged. Before review, fix remaining concrete cleanup defect: reference-map.ps1 writes an ownership-retained marker then unconditionally disposes all process-held locks on unconfirmed cleanup. A file is not a lease. On cleanup uncertainty keep the launcher alive with actual handles held, periodic bounded read-only confirmation of only owned groups/PIDs, status artifact and clear root-recovery instruction; release only after verified gone (or explicit root recovery). Avoid claiming marker retains ownership. Also perform managed ROS idle checks before BUILD as well as start, and handle nav start timeout/exception after a group may have started: record ownership from new state PID and conservatively flag cleanup uncertainty without stopping a pre-existing group. Preserve all source paths and guards. Existing capture_rgb.py and record_sensor_health.py DO exist; correct prior handback limitation. Existing owner only, 8-minute source-only fix bound, no tests/Unity/live/providers/delegation. Commit scoped source, append <=300word handback. No more source work once handed back; root reviews.

### 2026-10-13T01:07:07-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
```text
reference-driving-cleanup-fix-r2 (nonce igvc-drive-cleanup-f3201ffc91). ACK. About 2 minutes active, source only.
Candidate: 7a1db3c77ca6f3e244aa79697391ff1f1192cee6 (parent 2d9c802). Changed: tools/reference-map.ps1,
  tools/reference_map_trial.py, docs/REFERENCE_MAP_DRIVING.md. No other paths.
Fixes:
  1. Unconfirmed cleanup no longer disposes the locks. The launcher stays alive holding the real FileShare.None
     handles. Every 30 s it re-checks, read-only, only its owned player/build PIDs and (if owned) the r3a group
     via ros_session status. It rewrites <run>/ownership-retained.json with launcher_pid, locks_held, the alive
     owned items, the problems and root-recovery instructions. It releases only when everything is verified
     gone, or when root creates <run>/root-recovery-release; in that case it still exits non-zero.
     The old artifacts/iterations marker is removed, and nothing claims a file retains ownership.
  2. The managed ROS idle check (r3a/nav/perception must report stopped) and the domain-42 environment now
     run before BUILD as well as before start, smoke and trial.
  3. Start failures:
     - If r3a start exits non-zero or lacks "ROS started", a running group is treated as owned (the preflight
       proved none existed) and is stopped and confirmed in cleanup.
     - In the trial driver, a nav start TimeoutExpired/OSError or non-zero exit that leaves a new nav.json is
       recorded as owned (nav_owned_state = new state PID), and cleanup_ok is set false, giving exit 3.
     - nav stop timeouts are caught. A pre-existing nav.json is still refused and never stopped.
Correction to my r2 handback: tools/capture_rgb.py and tools/record_sensor_health.py DO exist. I searched for
  functions and missed the scripts. The trial driver still uses its own minimal read-only smoke subscriber;
  reusing those scripts is a possible follow-up.
Checks: PowerShell parses with 0 errors; py_compile OK. UNRUN: tests, Unity, live runs.
Usage: unavailable. No further source work from me unless dispatched.
```

### 2026-10-13T01:09:26.563366-07:00 · gpt-6-astra → team · DECISION
Human explicitly approved focused exact Sonnet review continuation <=480s/USD3, then build and two diagnostic runs. Latest source-only handback7a1db3c77ca6f3e244aa79697391ff1f1192cee6 bound47newpaths/11protected/31parked unchanged, worker clean. Cleanup-fix-r2 courier exit0/exactOpus/12.890s/USD.0441116; target nonce ACK08:05:19.877Z and canonicalhandback01:07:07. Interactive assignment ended. Root10focusedPythonPASS/no skips in focused-tests-r1 underall3locks released; tests do not establish live cleanup/Unity behavior. Approved source-review-r2-approved now running; first empty240s timeout preserved, no automatic retry. All Unity/build/live and review acceptance pending. NativeSol follows source review. Other task owners/blocks unchanged.


### 2026-10-13T01:10:47.777936-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
reference-driving-source-fix-r4. ExactSonnet review completed exit0/129.984s/USD.462624 at7a1db3c, THREE BLOCKERS; full retained artifacts/agents/T-0090/source-review-r2-approved/review.md. Fix same owned launcher/Python only, 8minute source-only bound, no tests/build/live/providers. (1) Trial cleanup exit3 retention checks ONLY player/build/r3a, clears uncertainty while nav/mission may live. Keep an explicit trialCleanupUnknown latch requiring ROOT release file; never clear based merely on r3a stopped; include readonly nav/perception status as supporting evidence, no blind stop. (2) Native WSL stderr 2>&1 under Stop can throw prematurely in WindowsPowerShell5.1. Locally set Continue and restore in finally around native WSL capture, return code/stdout/stderr deterministically; catch cleanup/query exceptions conservatively and retain leases, no cmd shell workaround. (3) Explicit 'already running' response must NEVER claim/stop foreign r3a. Also same principle nav start: require newly started receipt; do not infer new ownership solely from preflight. If uncertain unreceipted group appears, retain leases for root without stopping it. Prefer identity receipts from new start output/state. Tests10PASS with locks in focused-tests-r1, do not rerun. No scene/source changes needed; Sonnet found no C#/mission/gate issues. Root will rerun only focused delta review on new source evidence; prior timeout remains preserved. Hand back scoped commit <=300words and stop.


### 2026-10-13T01:12:30-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
```text
reference-driving-source-fix-r4 (nonce igvc-t90-b5a2ceef49). ACK. About 2 minutes active, source only.
Candidate: 32ba47ef9f868295c52fc84edab018173f35f47a (parent 7a1db3c). Changed: tools/reference-map.ps1,
  tools/reference_map_trial.py, docs/REFERENCE_MAP_DRIVING.md.
Sonnet blockers:
  1. A rootReleaseRequired latch is set by: trial exit 3; a trial call whose capture failed (code < 0); any
     exception during cleanup or status checks; an unreceipted r3a group. While latched, only
     <run>/root-recovery-release frees the locks. Automatic release otherwise needs owned PIDs gone AND r3a,
     nav and perception all reporting stopped (read-only status, nothing stopped). The status file lists the
     managed groups that are alive and the latch.
  2. Wsl: $ErrorActionPreference='Continue' locally, stderr to a temp file (no 2>&1; the only remaining match
     is a comment), preference restored in finally, deterministic {code,out,err}; a capture exception gives
     code -1. Each finally cleanup step (player/build stop, r3a stop) is in try/catch: an exception latches
     root release and keeps the locks. No cmd /c.
  3. r3a is owned only on this call's "ROS started: PID n" with exit 0. "Already running" or no receipt is
     never claimed or stopped; if a group is present, its owner is uncertain, so root release is latched.
     Trial driver: nav is owned only on its fresh-start receipt. An unreceipted nav.json after a
     failed/timed-out/"already running" start is recorded, not stopped, and gives exit 3 (root latch). The
     pre-existing nav.json refusal is unchanged.
Checks: PowerShell parses with 0 errors; py_compile OK. Not rerun: tests (focused-tests-r1 stands per your
  note), Unity, live runs.
Limit: the sensor_course child cannot be verified from the launcher; it is covered by the trial's exit 3 and
  the root latch.
Usage: unavailable. Stopping here.
```

### 2026-10-13T01:17:42.089675-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
reference-driving-source-fix-r5. Sonnet delta completed exactexit0/68.969s/USD.2012772: all3priorblockers fixed, one NEW interrupted-trial blocker plus report-finally edge. Read source-review-r3-delta/review.md. Fix exactrecommendation: trialInFlight true BEFORE Wsl call; evaluate exit then clear only0/1/2 BEFORE any logging; finally inflight latchesrootrelease. Pythonfinally anyclose/reportwriteexception mustexit3 conservatively insteadofescapingexit1. ALSO root WindowsPowerShell5 actualnativecheck FAILED (native-stderr-check-r1), function Wsl invokes `& wsl` which resolves to Wsl itself (caseinsensitivefunctionprecedence), so recursive self-call! Explicitly invoke `wsl.exe` (or renamehelper plusqualifiedexecutable) insidehelper; this blocks everylauncheraction. Prior rootcheckdidnotstartUnity/ROS; preserve failure. Scope only existingownedlauncher/trial/docs,5minute sourcebound; no providers/tests/build/live. Root will rerun nativecapture meaningfulcheck on changedsource, then finaldelta review of theseexactfixes, notrepeatC#. No additionalfeatures. Hand backcommit<=200words.


### 2026-10-13T01:18:50-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
```text
reference-driving-source-fix-r5 (nonce igvc-t90-57f835782d). ACK. Source only.
Candidate: e6fb64b1fcb5f622c282923a238ec8ac05f3a513 (parent 32ba47e).
  Changed: tools/reference-map.ps1 and tools/reference_map_trial.py.
- Native recursion: the Wsl helper now runs "& wsl.exe -d Ubuntu-24.04 -- ..." (the only native call site).
  Bare 'wsl' resolved to the Wsl function itself.
- Interrupted trial: $trialInFlight=$true immediately before the driver call. It is cleared only if the code is
  0, 1 or 2, evaluated before Set-Content and Log. In finally, if it is still set, rootReleaseRequired is latched
  and a cleanupFailed entry is added, so the locks are held for root. trial-driver.log now includes stderr.
- Python tail: ros.close() and the report write are each guarded; any exception, or cleanup_ok False, gives
  os._exit(3).
Checks: PowerShell parses with 0 errors; py_compile OK. UNRUN: the native check, tests, Unity, live runs.
Usage: unavailable.
```

### 2026-10-13T01:21:47.675318-07:00 · gpt-6-astra → team · DECISION
Source candidatee6fb64b1fcb5f622c282923a238ec8ac05f3a513 frozen47newpaths/11protected/31parked unchanged. ExactSonnet approved continuation r2 exit0/129.984s/USD.462624 found3launcherblockers; r3delta exit0/68.969s/USD.2012772 fixed3 but foundinterruptedtrial; r4delta exit0/51.843s/USD.1371578 PASS after fixes. Raw overlong reviews retained. Root nativePS5.1 fixture r1 failed fromrecursiveWsl function, sourcefixedexplicitwsl.exe. r2 capturedcorrectexit7/stdout/stderr but harness incorrectly required barestderr; PS5 decorates nativeerrors. Corrected assertion r3 PASS exit7 preserved stderr/restoredStop, all3locksheldandreleased. Initial10puretestsPASS unchanged testedfunctions; no repeat. NativeSol source/evidence accepted stable44paths, finalprebuildbinding accepted latestdelta. Accept reviewed new-onlysource for root integration and Unityvalidation/build. No runtime/visual/navigation successclaimyet. Remaining nonblockingSonnetfinallyhardening explicitly retained; root supervisesownedprocesscleanup and willverifyallgroups before nextattempt. Allpriortimeouts/failures preserved; no providerretry. Otherowners/T84blockunchanged.


### 2026-10-13T01:25:20.619984-07:00 · gpt-6-astra → team · DECISION
Reviewed source integrated as182157c,8062130,36c9052,ac83f63,25d5c23 fromcandidatee6fb64b1. All47 normalized sources/11protected/31parked remain bound. NativeSol finalprebuildPASS retained. Unity2027Drive built successfully exit0 at01:22:40.703, all3locksreleased; generatedscene/all9PNGs/report/player frozen unity-build-r1. Editorchecks PASS95drums/4822guardsegments. Rootactualnoonoverview/oblique andlow-sunsensor images inspected: faithfultrace, detailedbarrels/ground/shadows. Independent95positionchecks maxerror1.005e-6m PASS, canonicalbodyoffsetandnorthheading preserved. First independentharness assumedvisualbase_linkatodomorigin andfailed; corrected to documented axle/bodyoffset(0,.30385548,-.25591), failurepreserved, notsourcechange. All33protectedpreimages(includingprojectsettings/originalscene) unchanged. First authorized clear-noon diagnostic trial now root-owned live via launcher all3leases held, newr3aPID834/player65968 freshreceipts at01:24:39; do not launchanythingelse. Two preplannedattempts max180s/.6m/s,noautomaticretry, no full-audit/navigationclaimyet.

