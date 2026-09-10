# Docker delivery plan

## Scope and architecture

Keep Unity 6000.3.23f1 and rendered sensors on Windows. Build the ROS workspace in
an Ubuntu 24.04 / ROS 2 Jazzy image, with the pinned ROS TCP endpoint. Keep ROS
participants together inside the container; publish only the Unity TCP port on
localhost. Provide terminal entry points and RViz via WSLg. Preserve the existing
WSL workflow. The container must not depend on the host ROS installation.

## Ordered gates

1. Inspect launch commands, package dependencies, external assets, Docker runtime,
   GitHub authentication and repository size. Record missing prerequisites.
2. Add a Dockerfile, bounded build context, Compose configuration, environment
   entrypoint and Windows/WSL commands. Build dependencies from package manifests.
3. Build the image from project source. Check Ubuntu version, Jazzy, all packages,
   description mesh resolution and launch startup within the image.
4. Stop the managed native ROS session before using its port. Start container ROS
   and a Windows Unity player. Verify clock, lidar, RGB/depth, TF, commands and
   watchdog behavior using the existing behavioral verifiers. Open container RViz.
5. Run the seeded course and audit the result; distinguish this live evidence from
   prior native-WSL evidence. Test stop/restart. Diagnose failures before publishing
   a claim of working integration.
6. Document clean download/build/start/RViz/terminal/stop instructions in README,
   including Unity and external-asset preparation, limitations and exact evidence.
7. Inspect the upload set for credentials, generated output, large files and
   external assets. Create a new private GitHub repository, push source, and check
   a clean clone against the documented setup. Report the repository URL and any
   gates that remain incomplete. Never describe a blocked gate as passed.

## Initial inspection

- WSL Ubuntu-24.04 exists and uses systemd; Docker and GitHub CLI are absent.
- No Git remote exists; project files are currently untracked.
- Existing integration uses localhost TCP 10000 and ROS domain 42.
- SoonerRobotics imported assets are ignored; a clean checkout must explicitly
  obtain required reference inputs or build a self-contained procedural player.
- One coordinator owns runtime installation, container files and live testing;
  a bounded read-only worker reviews ROS dependencies and launch requirements.
