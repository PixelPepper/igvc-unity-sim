# Linux workflow validation — 2026-09-09

## Scope

Native Linux launcher implemented for Ubuntu24.04 x86_64, local X11/XWayland,
Docker Engine, and Unity6000.3.23f1 Mono. No WSL calls in the Linux scripts. Shared
Unity build code selects Linux64/Win64 output; Windows wrappers explicitly select
Win64 to avoid accidentally retaining a previous Linux Editor target.

This machine is Windows with Ubuntu24.04 WSL2/WSLg. Linux runtime tests use an
actual ELF x86_64 player, not a Windows executable. The Linux player was built by
the Windows Editor with Unity's matching Linux Mono module; its official download
checksum and Authenticode publisher were checked before installation.

## Passed checks

- Linux player build exited0; ELF64/x86_64 confirmed and linked dependencies resolve.
  Editor build included3 ground render fixtures,6 depth checks,70 ramp checks and
  12 caster checks. Editor render tests ran on Windows, distinct from live Linux.
- Linux player and non-root ROS container run as UID1000; container mesh/package
  environment verifier passed. Live transport passed all7 checks over20seconds:
  RGB12.69Hz, depth8.59Hz, lidar5.00Hz, odometry47.02Hz; no payload errors, coherent
  camera-info stamp pairs and sensor/robot TF. See [report](evidence/linux/integration.json).
- Full Linux course completed82/82 checkpoints and returned to start. All12 audit
  checks passed: no resets, gaps or line interventions, max2.2m/s, sampled clearance
  0.70154m and swept clearance0.53413m. See [audit](evidence/linux/course-audit.json).
- Terminal command/control test passed4 checks:0.243m commanded travel, timeout
  stop, E-stop overrides fresh commands, clearing E-stop does not rearm.
  See [controls](evidence/linux/controls.json).
- RViz visibly rendered robot, scan, RGB, metric depth and costmaps with Global
  Status OK. Renderer was Mesa llvmpipe/OpenGL4.5. The already documented first-map
  GLSL warning and one startup scan queue drop were observed; zero warnings are
  not claimed. Local screenshot: `artifacts/checks/linux-rviz.png`.
- Fifteen launcher tests passed on Ubuntu Python: process reuse/identity and
  pidfd checks, foreign checkout/container refusal, failed-start cleanup, stopped
  status, seed/difficulty checks, argument forwarding and scoped Xauthority cases.
- Linux stop removed its owned player/container; stopped status exited successfully.

## Final platform checks

- Windows rebuild via `tools/docker.ps1 unity-build` after the Linux target switch
  exited0 and produced the Windows player. Windows wrapper selection remains Win64.
- Scoped-cookie construction and rejection of an unauthenticated native display
  passed mocked tests. The original Xvfb attempt could not create its Unix socket
  on WSLg's read-only socket mount; the isolated test below resolved that fixture
  limitation without changing the host display mount.
- Linux Editor/license activation and physical desktop/GPU driver combinations
  remain untested. No native-desktop certification is claimed.

## Authenticated X11 integration (September 10, 2026)

A private mount namespace provided a writable X11 socket directory to Xvfb
`:90` (2560x1600, TCP disabled, MIT-MAGIC-COOKIE authentication). The Docker bind
source used `IGVC_X11_SOCKET_DIR` to reach that same directory from the daemon.
Unity and the launcher ran as the normal user; root was used only to isolate the
test mount. WSLg's original socket mount remained read-only and unchanged.

- A client with an empty authority file was rejected with `Authorization required`.
- The launcher's scoped cookie admitted RViz in the non-root ROS container.
- All seven live integration checks passed over 20 seconds: RGB 10.79 Hz,
  depth 7.95 Hz, scan 4.50 Hz, odometry 45.52 Hz; no payload errors, 215 RGB
  and 159 depth/CameraInfo pairs. See [report](evidence/linux/xauth-integration.json).
- [RViz capture](evidence/linux/xauth-rviz.png) was visually checked: Global Status
  OK, robot, costmaps, RGB and metric depth rendered. The previously documented
  first-map GLSL warning still occurred. Software rendering was used.
- All 15 launcher tests passed again; session cleanup removed the player,
  container and virtual display. The full course was not repeated for this
  display-only check; the earlier 82/82 result remains the course evidence.

The first isolated capture attempt used a screen smaller than the RViz window and
failed `X_GetImage`; enlarging the virtual screen allowed the capture to succeed.
This verifies authenticated virtual X11 integration, not physical GPU behavior.
