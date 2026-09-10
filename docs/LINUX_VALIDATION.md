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
  passed mocked tests. An additional authenticated Xvfb integration attempt could
  not create its Unix socket on the WSLg-provided `/tmp/.X11-unix` mount. That attempt
  failed before starting the simulator; it is not counted as a successful X11 test.
- Actual display validation used WSLg's cookieless local socket, as explicitly
  supported by the launcher. Native authenticated desktop access remains to be
  validated on a native host, alongside Linux Editor/license activation and GPU
  driver combinations. No native-desktop certification is claimed.
