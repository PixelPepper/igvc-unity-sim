# Native Linux delivery

Target Ubuntu 24.04 x86_64 with a graphical X11/XWayland session, Docker Engine,
and Unity 6000.3.23f1 with Linux Mono build support. Keep the same ROS container,
TCP interface, robot and course. No Windows executable or WSL command is required
by the Linux launcher.

1. Add Linux output selection to the shared Unity build helper, preserving Windows
   output selection. Reject unsupported build targets explicitly.
2. Add a Linux launcher with scoped process ownership, cleanup, terminal commands
   and non-root container UID/GID mapping. Configure scoped Xauthority access for
   RViz without disabling host X server access control.
3. Obtain Linux build support and build an actual x86_64 player. Run that Linux
   executable against Docker, verify sensors/TF/controls and a full course audit.
4. Test launcher lifecycle failures, ownership and command construction; verify
   Windows build compatibility. Document native setup and exact validation limits.
5. Commit and push the Linux workflow and README to the existing GitHub repository.

Available hardware is Windows with WSL2/WSLg. A Linux ELF player running there is
useful Linux-runtime evidence, but not a native Linux desktop/GPU certification.
Linux Editor/license validation and a second physical host must be identified
separately if unavailable. Do not claim those checks passed based on cross-builds.
