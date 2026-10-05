# Interactive IGVC sandbox

The sandbox is a separate Unity player for changing the course and experimenting
with navigation. The existing `IGVC Latest Run + RViz` shortcut and compiled course
player remain separate. This is the ideal simulation fixture, not a calibrated
physical robot or a promise that arbitrary obstacle layouts can be completed.

## Open it

On the development Windows computer, double-click **IGVC Sandbox + RViz** on the
desktop. It starts Unity, native ROS 2 Jazzy in Ubuntu 24.04 WSL2, and RViz. Close
the previous managed simulation first: both use ROS domain 42 and TCP port 10000.

From PowerShell at the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/sandbox.ps1
```

The launcher opens a 1600 × 1000 window. `-Width 1280 -Height 800` selects a smaller
window. The menu uses 18-pixel body text, large buttons and scrolling panels.
Close Unity to shut down its supervisor, RViz and managed ROS session. Keep the
launcher terminal open so it can perform that cleanup.

## Edit the course

1. Wait for **IDLE** in the footer. Editing is disabled while a trial is running
   or the session is disconnected.
2. Open **Course editor**. Select **+ barrel**, **+ barricade** or **+ pothole**,
   then click the ground. Placement snaps to 0.25 m.
3. Use **Select** and click an obstacle. Its editable position, rotation and
   dimensions appear in the panel. Barrel color and pothole depth are available
   for those obstacle types. Select **Apply changes** to commit numeric edits.
4. **Move selected** moves it to the next ground click. **Delete**, **Undo edit**
   and **Reset course** support experimentation. Reset restores the baseline
   obstacle course; navigation settings have a separate reset button.
5. Give the experiment a preset name and select **Save preset**. To reload it,
   select its name from **Saved presets** or type the name, then **Load preset**.
   Saving an existing name overwrites that preset. Presets contain both the
   course geometry and navigation settings. Numeric fields commit on Enter or
   focus loss; apply obstacle values before saving.

The editor rebuilds colliders and the ground when needed, including actual
pothole cutouts and supporting rims. It rejects invalid dimensions, overlapping
pothole rims, potholes through the ramp, and obstacles covering the starting
area. It does not guarantee a traversable lane or prevent deliberately difficult
layouts. Lane topology, ramp geometry and the six broad GPS destinations remain
the baseline; obstacle editing does not create additional guidance waypoints.

Camera controls: **Whole course**, **Follow robot**, right-drag orbit,
middle-drag pan, wheel zoom. **F1** hides/shows the editor panel. UI interactions
and text entry suppress spectator controls. Selection markers belong only to
the screen UI and are not painted into camera/depth sensor images.

## Tune and run

Open **Navigation lab** and change the desired settings while stopped. They are
applied together on the next **Start from beginning**, including a managed Nav2
restart and fresh mission observations. No algorithm change is applied halfway
through a controller action.

| Control | Allowed range / choices | Effect |
| --- | --- | --- |
| Controller | RPP or MPPI | Pure-pursuit path tracking or sampled trajectory control |
| Path execution | Checked path or Nav2 goal | Follow the custom observed-space path directly, or let Nav2 plan toward the selected local target |
| Speed ceiling | 0.1–2.2 m/s | Maximum requested forward speed, also bounded by the sanitized GPS mission |
| Inflation radius | 0.1–1.5 m | Nav2 obstacle inflation in both costmaps |
| Clearance preference | 0–10 | Soft preference for space around the whole body; does not shrink its collision footprint |
| Planning budget | 0.1–5 s | Custom local search time budget; processing overhead is additional |
| RPP lookahead | 0.2–2 m | RPP tracking lookahead distance; not an MPPI parameter |

**Restore successful 6/6 settings** chooses RPP, checked-path execution, 0.6 m/s,
0.30 m inflation, clearance weight 3, 0.5 s planning budget and 0.65 m lookahead.
Other combinations are experiments. A new course and a visible UI can also change
timing and results; the earlier single successful seed is not a guarantee here.

**Start from beginning** resets the robot to its original pose, clears navigation
observations and begins the six-destination mission. **Stop trial** immediately
holds simulated motion and requests confirmed mission/Nav2 shutdown. Editing
unlocks only after that shutdown is acknowledged. On a failed trial, use Stop
to return to editing. Missing session heartbeat prevents editing and holds motion.

## Saved files and implementation

Local files live under `artifacts/sandbox/` and are excluded from Git:

- `baseline-course.json`: reset template from seed 2027.
- `course.json`: currently applied layout; matches the geometry hash reported by Unity.
- `presets/<name>.json`: named course/settings presets, preserved between launches.
- `runs/<timestamp-id>/`: immutable course, sanitized six-GPS mission, generated
  Nav2 profile, provenance, mission logs, decisions and run report.
- `status.json`, `command.json`: local supervisor communication; not a public
  network API. Unity does not launch shell commands from user-entered text.
- `unity.log`, `rviz.log`, `supervisor.log`, `supervisor-error.log`: diagnostics.

The launcher starts a fresh baseline on each launch. Save a preset before closing
to retain edits, and load it after reopening.

| Source | Responsibility |
| --- | --- |
| [SandboxPanel.cs](../unity/IGVCSim/Assets/IGVC/Runtime/SandboxPanel.cs) | Interactive editor, selection, parameter controls and command/status handshake |
| [SandboxDocument.cs](../unity/IGVCSim/Assets/IGVC/Runtime/SandboxDocument.cs) | Versioned presets, input validation and atomic saves |
| [SandboxPanel.uxml](../unity/IGVCSim/Assets/Resources/SandboxPanel.uxml) / [styles](../unity/IGVCSim/Assets/Resources/SandboxPanel.uss) | Large Unity UI Toolkit layout and appearance |
| [CourseVariant.cs](../unity/IGVCSim/Assets/IGVC/Runtime/CourseVariant.cs) | Staged environment generation, obstacle colliders and pothole ground rebuild |
| [sandbox_profile.py](../tools/sandbox_profile.py) | Allowed parameters, Nav2 YAML generation and mission options |
| [sandbox_session.py](../tools/sandbox_session.py) | ROS mission ownership, heartbeat, restart and confirmed cleanup |
| [sandbox.ps1](../tools/sandbox.ps1) | Windows/WSL startup, separate player and desktop shortcut |

Build using Unity 6000.3.23f1 after preparing the main project's assets/dependencies:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/sandbox.ps1 build
powershell -NoProfile -ExecutionPolicy Bypass -File tools/sandbox.ps1 shortcut
```

The build menu is **IGVC > Build Sandbox Player**. Output is
`artifacts/build-sandbox/IGVCSandbox.exe` with its accompanying data directory.
The sandbox currently targets this Windows/native-WSL setup; a Docker or native
Linux sandbox launcher has not been validated.

## Validation — October 1, 2026

### RViz icon appears but its window is invisible

On this development host, RViz's title contained `[WARN:COPY MODE]` and
`/mnt/wslg/weston.log` reported `rdp_allocate_shared_memory: Failed to open`
with an input/output error. RViz was running and receiving ROS data, but WSLg
displayed a transparent window. Restarting RViz and switching to software OpenGL
did not fix it. Restarting the WSLg Weston compositor, then reopening RViz with
normal rendering, restored the visible robot, RGB/depth images and costmaps.
The active Unity/ROS mission continued during that recovery.

This matches the symptoms in [Microsoft's WSL issue](https://github.com/microsoft/WSL/issues/40618).
Check the current log and window title before attributing another failure to it.
Restarting the compositor disconnects **all WSL GUI apps**, so it should be an
explicit recovery action after checking other open Linux applications, not an
automatic sandbox startup step. A full `wsl --shutdown` also stops ROS and should
not be used during a lap. In this recovery, the reopened RViz watches the sandbox
supervisor and closes when the sandbox ends.

### Build, editor and integration checks

Later user trial `20261002T035715-45c98a0f` reached 6/6 and passed geometry,
but failed aggregate acceptance with four processing-health samples failing.
See the [current handoff and preserved audit](CLAUDE_HANDOFF.md#current-state-and-evidence).
The UI's `completed` status reports mission completion, not independent audit acceptance.

- Unity 6000.3.23f1 Windows player build passed. This produces a separate player;
  the course build is not the sandbox build target.
- The rendered 1280 × 800 interface was inspected for readable text, scrolling,
  separated course viewport and always-visible Start/Stop controls.
- Runtime editor smoke checks passed: add all three obstacle types, rotate/edit,
  undo, named save/load, raycast through a rebuilt pothole cutout, and reject
  invalid geometry while retaining the previous world and saved course.
- Fourteen offline supervisor/profile tests passed, covering parameter limits,
  mission input boundaries, stale commands, heartbeat, shutdown, missing inputs,
  atomic file replacement and confirmed child exit.
- Isolated live ROS domain 43/TCP 10001 tests launched Unity and RViz, then started
  and stopped RPP and MPPI using checked-path execution. ROS parameter services
  confirmed each controller plugin, 0.4 m inflation and RPP's 0.8 m lookahead.
  At a requested 0.4 m/s ceiling, the robot moved 2.31 m with RPP and 2.90 m with
  MPPI before operator stop. Both wrote final reports without cleanup errors and
  returned editable idle. Temporary isolated processes were cleaned up.

The live tests exercised the supervisor through the same command files used by
the panel. They did not automate mouse clicks through every control. The normal
domain-42 shortcut uses the same components; the isolated ports avoided disrupting
the existing managed session during validation. Nav2-goal mode was verified in
profile/argument tests, not a new live trial. Arbitrarily edited courses and other
parameter combinations have not passed a full-lap acceptance test.

Testing corrected invalid-edit rollback, UI sizing/focus handling, transient
Windows/WSL atomic-file sharing failures and interrupted mission finalization.
Mission cancellation now preserves the ROS context while it cancels actions and
saves evidence; planner workers are closed by their coordinator first.

Evidence: [editor checks](evidence/sandbox-2026-10-01/ui-smoke.json),
[integration summary](evidence/sandbox-2026-10-01/integration.json),
[trial measurements](evidence/sandbox-2026-10-01/live-trials.json),
[course editor image](evidence/sandbox-2026-10-01/sandbox-editor.png), and
[navigation menu image](evidence/sandbox-2026-10-01/sandbox-navigation.png).

Offline checks from the repository root:

```powershell
wsl -d Ubuntu-24.04 -- python3 -m unittest discover -s tools/tests -p test_sandbox_profile.py
```

After closing the previous managed simulation, `tools/sandbox.ps1 -SmokeTest`
runs the editor checks, captures both tabs and closes the sandbox. Keep its window
visible for screen capture. For a live parameter check, start a trial from the
panel, inspect `/controller_server` and both costmap parameter services, then Stop
and check the saved `run.json` and editable status.
