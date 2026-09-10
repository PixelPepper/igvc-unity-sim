# Agent workflow

Updated preference: prioritize development speed with moderate cost. Grok now defaults to medium effort, non-fast. The coordinator may use `-Effort high` for difficult tasks or `-Fast` when latency matters, without asking again. Low effort remains useful for simple checks. Higher effort may take longer; use independent work and selective Fast mode to shorten elapsed time. Existing context bounds, usage recording and cancellation thresholds remain active.

Example: `./tools/cursor-agent.ps1 review -Task tools/agents/review-motion.task.json -Effort high -Fast`. This submits a real run; use `doctor` to verify model selection without starting one. Historical low-effort results below describe the initial test, not the new default.

The coordinator retains the ROS/Unity contract and integrates changes. By default, use one or two workers on disjoint tasks. Parallelism reduces elapsed time when work is independent; it can increase total tokens, so tiny sequential edits stay local.

| Work | Assignment | Ownership |
|---|---|---|
| Unity runtime | Motion, sensor code, scene generation | One Unity owner; only integrator launches Editor/builds |
| ROS packages | Description, transforms, launch/config, perception | Package-level file ownership; interface changes return to coordinator |
| Review | Focused invariants and failure cases | Read-only, short findings with file/line evidence |
| Documentation | Runbook and milestone evidence | Named docs only |

Each task packet specifies objective, input files, files permitted to change, exclusions, acceptance command, output limit, and stopping conditions. Give workers a small context packet instead of conversation history. Start reviews with a few source files, and expand only if the worker identifies a specific missing dependency. Avoid giving both a Codex worker and Grok the same assignment simultaneously.

Default operating limits: two active workers, no recursive workers, one external Cursor job at a time, one pass before coordinator review, and no automatic retry on failure. Prefer short answers and explicit evidence. These are workflow defaults rather than a promise of a fixed bill. Provider usage includes hidden agent instructions/tool context as well as the task packet.

The initial Cursor integration uses the official SDK and explicitly requests `grok-4.6`. It discovers account-supported parameters before choosing a non-fast low-effort variant. It stages only allowlisted text inputs and returns review artifacts; it does not edit simulator files. Credentials are stored outside this repository with Windows user encryption. SDK usage is recorded per job, with a cancellation threshold where usage events are available. An event-based threshold can overshoot during a turn and is not a hard token cap.

Implementation task split after the transport gate:

1. Coordinator freezes robot frame/joint/interface conventions.
2. Robot worker normalizes URDF/package paths and validates Linux mesh resolution; a separate worker prepares sensor fixture tests against the frozen contract.
3. Coordinator reviews and integrates, imports the robot, then runs the Unity/ROS checks once.
4. Assign Nav2 and lane perception independently only after sensor/TF contracts are stable.

References: [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents), [Cursor SDK](https://prod.cursor.com/docs/sdk/typescript), [Grok 4.6](https://prod.cursor.com/docs/models/grok-4-6). SDK operation and validation status are recorded in tools/agents and the milestone evidence; account access must be tested rather than inferred from public model availability.

## First integrated run

Cursor catalog authentication succeeded and returned `grok-4.6` with `effort=low`, `fast=false`. A live two-file motion review completed: 5,807 input tokens and 6,790 output tokens (6,112 reasoning tokens included in output), total 12,597; no reported cache usage. This is actual SDK-reported usage, not a billing estimate. The job artifacts are under `artifacts/agents/2da279d1-20e0-46e4-ba62-3b5c8babe2ba`.

Coordinator disposition: the accelerated-time concern is outside the 1x fixture contract; ignoring pre-clock commands is acceptable; requiring fresh commands on resume is intentional and tested. No suggested control change was applied. The task packet now includes these constraints to prevent avoidable false positives and repeated review. Do not rerun this review merely to obtain agreement. Future SDK jobs also request the billed-usage record when available; missing costs remain unknown.

Use `./tools/cursor-agent.ps1 doctor`, then `./tools/cursor-agent.ps1 dry-run -Task tools/agents/review-motion.task.json` to inspect the scope. `./tools/cursor-agent.ps1 review -Task tools/agents/review-motion.task.json` submits one hosted review. The wrapper temporarily decrypts the Windows-user credential into the child environment and restores the previous environment afterward. Keep keys out of task packets and chat.
