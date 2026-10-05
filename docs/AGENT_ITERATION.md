# Independent implementation and simulation iterations

User authorization (2026-10-01): Claude models may implement, commit and run their
own simulations. Opus/Sonnet use Claude CLI; Cursor is for separate tasks.

Measured candidate outcomes, usage and remaining gates are recorded in
[October 1 integration evidence](evidence/navigation-2026-10-01.md).

## First implementation round

- Sonnet 5.5 owns observed surface projection and its regression tests. Correct
  the demonstrated 0.387 m synthetic ground-paint displacement while retaining
  valid paint on ramps and rejecting occluders/unsupported creases. No WORLD data.
- Opus 5.5 owns path admission and its regression tests. Eliminate sideways/
  backward connectors while retaining a useful forward path. No footprint
  reduction or collision-check bypass. Recovery redesign is a separate experiment.
- The integrator owns infrastructure, immutable experiment profiles, the acceptance
  audit, review and final combined trials. Maximum two implementation workers.

## Isolation and evidence

Each worker starts from the same local snapshot commit of the current dirty tree,
on its own `codex/` branch and worktree. The primary checkout and index are preserved.
Workers may edit only assigned files and commit only those paths. No pushes,
resets, force operations, package installs, credentials or unrelated files.

Offline checks can run in parallel. Live trials serialize on an exclusive lease
because the existing Unity bridge uses TCP 10000 and the launchers share domain42.
The lease is held through build, start, readiness, bounded sensor-led mission,
independent audit and shutdown. Each worktree uses a separate ROS build overlay.
The same existing Unity binary and seed2027 course are used; workers cannot alter
the map, sparse destinations, footprint, .30m inflation or .6m/s trial ceiling.
Neither worker receives the other's implementation during its independent trial.

On Windows, `tools/agents/iteration-launch.mjs` holds the background PowerShell
process independently of the agent's MCP connection. The Node supervisor is
detached; PowerShell itself is hidden and attached to that supervisor. Directly
detaching PowerShell failed before script execution on the tested host. A
no-ROS/no-Unity fixture checks startup and survival after the MCP process exits.
`iteration-live.ps1` retains simulator ownership through shutdown. Optional
`record_episode: true` in an integrator trial configuration enables the read-only
paired acquisition recorder through `iteration-mission.py`; recording load must
be measured and cannot justify weakening the freshness watchdog.

Live trials preserve command logs, source/profile/player hashes, mission result
and independent geometric audit. Geometry passing is not aggregate sensor-led
acceptance; the review's health/provenance findings still apply. A failed or partial
run must be reported as such. No report is promoted based on progress count alone.

Each worker may request at most one live trial in this initial round and up to
three focused offline checks while fixing failures. Only the integrator can grant
another iteration after new evidence. Shared runtime ownership never expires while
a process could still command motion; stale leases require inspection.

## Integration

Review each commit once, compare live evidence with the recorded baseline, then
apply only accepted diffs to the current checkout. Preserve rejected candidates
and their evidence on their branches. Run the combined relevant tests and a fresh
live trial before claiming improvement. Full 6/6 requires interval sensor health,
continuous trajectory, ordered return, full-body paint/obstacle/ramp checks and
speed evidence. Physical calibration and competition compliance remain separate.
