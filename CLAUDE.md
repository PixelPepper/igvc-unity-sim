# Claude Code entry point

Read [AGENTS.md](AGENTS.md), [README.md](README.md), then
[the current handoff](docs/CLAUDE_HANDOFF.md) before project work.
Read other documents on demand using the handoff's index; do not ingest all logs,
CAD files, Unity Library, node_modules or historical agent packets.

This is IGVC 2027 AutoNav: Unity on Windows, ROS 2 Jazzy in Ubuntu 24.04 WSL2.
It is an ideal simulation fixture, not a calibrated physical robot.
Canonical +X points toward the front driven wheels; rear wheels are casters.

Optimize sensor-led navigation without supplying the generated course/path to
autonomy. Six broad GPS destinations are allowed; WORLD geometry is reserved
for rendering and independent offline auditing. Preserve collision footprints,
paint/ramp checks, freshness watchdogs and bounded recovery.

The local working tree contains substantial uncommitted and untracked work.
Inspect it before branching; a worktree from HEAD alone omits current features.
Preserve existing edits. Never reset/clean the tree or commit everything blindly.

Inspect active session ownership before running, stopping or rebuilding anything.
Use the shared live lease and separate worker overlays. The sandbox can remain
open after completing a lap and still own the bridge. Do not launch a second
simulator or stop someone else's session to obtain the port.

Multi-agent work follows [docs/agents/](docs/agents/README.md): check the
[board](docs/agents/BOARD.md) first. ASTRA (Codex `gpt-6-astra`) orchestrates and
integrates, Opus implements, and Sonnet (code) and GPT-6.1 Sol (evidence) review.
Work only on a task you were assigned. Append to its log in the
[message format](docs/agents/PROTOCOL.md#message-format) and never edit task headers.

Report implementation, tests, evidence and remaining uncertainty separately.
Reaching 6/6 alone is not passing the independent audit. Start with the prioritized
work in the handoff, not an unmeasured speed increase or wholesale rewrite.
