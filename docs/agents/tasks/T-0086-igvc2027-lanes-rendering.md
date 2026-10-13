---
id: T-0086
title: Represent variable-width lanes and dashed IGVC 2027 boundaries in Unity
status: blocked
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0086-igvc2027-lanes-opus
base: b517a9924d80750bd19ee1094b95984fe6463b96
candidate: none
claim: none
lease: none
updated: 2026-10-12
---

# T-0086: Represent variable-width lanes and dashed IGVC 2027 boundaries in Unity

## Packet

Written by ASTRA and frozen at `ready`. Any change goes in the Log as a `DECISION`.

- **Hypothesis / objective:** Variable-width sectors and dashed white paint can represent the requested profile without reducing valid obstacle passages, ramp support or the existing finish contract.
- **Why now:** This is the staged narrowing/marking slice from [the proposal](../proposals/IGVC2027-rules-profile.md) and `artifacts/agents/IGVC2027/astra-r1.md`, after T-0085 establishes profile generation and passage validation.
- **Inputs:** `README.md`, this packet, [T-0085](T-0085-igvc2027-course-profile.md), `artifacts/agents/IGVC2027/sol-r1.md`, the proposal, and the owned Unity sources. Read [T-0070](T-0070-unity-latency-selection.md) before any `SandboxDocument.cs` work, `docs/COURSE_RAMP.md` for ramp/support and the T-0083 finish contract sources before changing widths. Preserve the existing dirty `CourseVariant.cs`, `SandboxDocument.cs` and new `RealisticObstacles.cs` in `.claude/worktrees/sim-realism` as identifiable inputs; ASTRA must reconcile these with primary and T-0070 before dispatch.
- **Knowledge context:** `sensor-led-navigation`, `frames-and-sensors`, `trial-audit-promotion`, `agent-handoffs` from [the OKF index](../../knowledge/index.md); check canonical source drift.
- **Owned paths (may edit):** Prospective ownership only, inactive while blocked: `unity/IGVCSim/Assets/IGVC/Runtime/CourseVariant.cs`, `unity/IGVCSim/Assets/IGVC/Runtime/RealisticObstacles.cs` and its new `.meta`, `unity/IGVCSim/Assets/IGVC/Runtime/SandboxDocument.cs` after explicit T-0070 release, plus new `unity/IGVCSim/Assets/IGVC/Editor/RulesProfile2027Validation.cs` and its `.meta`. After explicit T-0085 ownership transfer: `tools/generate_course_variant.py`, `tools/course_passage.py`, `tools/tests/test_course_profile_2027.py` for width/marking support only. Ignored evidence under the assigned worktree's `artifacts/agents/T-0086/`. Everything else is read-only; no active file reservation overrides T-0070/T-0085.
- **Must not change:** No scenes/prefabs, Unity builds/imports, shared interfaces/schema without ASTRA decision, auditors, runtime policy, perception, dependencies, speed ceiling or robot/sensor configuration. Retain six sanitized goals, whole-body and swept checks, health/recovery gates, and the straight +X origin with 3 m half-span / 6 m finish sector required by `finish-crossing/1`. Dashes never grant permission to cross boundaries. Drop decorative barricade work. Mesh containment within colliders alone cannot establish matching RGB/depth/lidar surfaces. Preserve unrelated dirty work and review realism prerequisites separately.
- **Baseline identities:** Planning anchor `b517a9924d80750bd19ee1094b95984fe6463b96`; this is not an executable post-T-0085 base. ASTRA will record the reviewed successor SHA, input hashes and isolated worktree in a DECISION before making ready/dispatching. Legacy byte reference remains `b517a99`. Candidate/player/overlay/course hashes/live run: none yet.
- **Allowed checks:** After unblock, up to 3 focused offline runs: (1) `python -m unittest discover -s tools/tests -p test_course_profile_2027.py`; (2) `python -m unittest discover -s tools/tests -p test_course_variants.py`; (3) ASTRA-run Unity validation entry `IGVC.RulesProfile2027Validation.Run` from the new validation source, using the pinned Editor under the build/lease workflow. Worker may author validation source but must not open/import/build Unity. Actual launch command is recorded by ASTRA at dispatch. Do not run tests while blocked.
- **Live trial:** None for the implementer. Unity import/build, visual/sensor inspection and any live validation belong to T-0088.
- **Acceptance:** Target 3.048 m clear lanes in suitable sectors; widen centered-obstacle sectors for two 1.524 m openings plus the actual obstacle diameter and paint allowance, retaining the 6 m finish sector. Measure clearance to inner paint edges; detect staggered bottlenecks and curved/transition restrictions through the T-0085 validator. White boundary tape is 3-4 in (0.0762-0.1016 m); support continuous/dashed representations with deterministic geometry and an unchanged logical boundary through dashes. Validate below-4 m widths only when geometry is valid. Reconcile ramp width/support and body containment before claiming width conformity; preserve gradient limits. Render 0.6096 m white zero-depth rule potholes and the user-sized drums, and test geometry/collider/sensor representation explicitly. Preserve legacy behavior/bytes for omitted profile and the 12-case profile matrix. Hand back scoped SHA, imported-input provenance, focused results and remaining rendering evidence requirements for both reviewers. No live or compliance claim from source-only checks.
- **Stop condition:** Remain blocked until T-0085 is reviewed, ASTRA transfers generator/test ownership and resolves T-0070's reservation plus dirty-source provenance. Then hand back at completion or 35 minutes / budget; stop for scope/invariant conflict, two refuted hypotheses, ungranted resources or provider errors. No timeout-based reassignment, automatic retries or further delegation.
- **Budget:** `claude-opus-5-5`, high effort, `--max-budget-usd 10`, 35 minutes once dispatched; interactive equivalent is a usage-accounted target, not an enforced cap. One review per handback per reviewer, at most two revision rounds.

## Handback

Filled in by the owner. 300 words maximum, not counting the identities.

```text
Hypothesis and outcome:
Changed files / scoped commit (candidate SHA):
Baseline and candidate identities:
Tests and replay evidence (commands + results):
Live result: destinations, time, backups, clearance, health, audit status:
Shutdown/lease verification:
Claim level reached: implemented | tested | audit-passed
Remaining risks and next experiment:
Knowledge concepts affected (IDs, source changes or none):
```

## Log

### 2026-10-12T18:03:00-07:00 · gpt-6-astra → all · DECISION

Blocked pending reviewed T-0085 and explicit generator/test ownership transfer, plus resolution of T-0070's `SandboxDocument.cs` reservation and preservation of dirty Unity inputs.
No implementation, worker launch, test, Unity import/build or ownership transfer is authorized by this packet while blocked. ASTRA must bind the successor base/worktree and dispatch after those gates.
Staged width decision: 3.048 m clear sectors where suitable, wider centered-obstacle sectors with 5 ft on both sides measured to inner paint edges, connected-passage checks for staggered obstacles, and the unchanged 6 m finish sector. Ramp conformity remains pending validation.

### 2026-10-12T19:41:10-07:00 · gpt-6-astra → all · DECISION

Keep **blocked**; do not dispatch the interactive `claude-opus-5-5` session yet. T-0085 is accepted at `937a7e60a3557ab403b688404bf1205ebd1f8a10`, but neither its inherited prerequisites nor these parked Unity edits have been accepted for integration.
Resolve the current ownership collision by **retaining T-0070's exclusive `SandboxDocument.cs` reservation**; T-0086 has no write authority to that file in any checkout. T-0070's simulator releases are not source releases. No timeout-based reassignment, split hunk ownership or implicit transfer is made; T-0070's log remains untouched this turn.
The parked SandboxDocument change permits depth-zero potholes; primary independently adds `SandboxSettings.latency_compensation`. Although these observed hunks differ, they are not a reconciled baseline and do not override one-owner-per-file. Before dispatch, obtain the reserved owner's explicit release/handback, or record an explicit scoped reassignment with preserved inputs; reconcile primary, the T-0070 checkpoint/candidate and the parked patch in an isolated successor with both reviews as applicable.
Preserve the parked inputs in `.claude/worktrees/sim-realism` unchanged. SHA-256 at this decision: `CourseVariant.cs` = `90a48b2e4ef9ce79c6f6094130f81d7a470e501f70de51cb58d8f39fa986f462`; `SandboxDocument.cs` = `e14f91459cd2aded4add2390eedb1e0a3c177c6d12ed41ef3a72660bc4eac770`; untracked `RealisticObstacles.cs` = `e2ef81a98eaa98d4a0e22f6d346efc6bee59dba571052592e261b0fdff963aa9`. These are input identities, not accepted source.
ASTRA must first establish the separately reviewed generator prerequisite and choose either reviewed realism dependencies or a separately reviewed port onto the ideal renderer (T-0088 plan). Then pin an isolated worktree/base and provenance-preserving import of only owned Unity inputs, excluding decorative barricades and unrelated realism behavior. Do not commit or discard the parked files merely to clean the source worktree.
Generator, passage helper and profile-test ownership stays with ASTRA pending that successor decision; T-0085 acceptance alone is not a T-0086 ownership transfer. A future DISPATCH must enumerate exact active paths, source-only worker checks, the actual ASTRA Unity validation command and the unchanged 3-run/35-minute/USD 10 bounds. No worker tests, Unity import/build, live session or new worker launch is authorized now.

### 2026-10-12T23:15:50.0748456-07:00 · gpt-6-astra → all · DECISION

T-0086 remains `blocked`, with no implementer dispatch or active file ownership. The user's approval is now disposed in T-0070 and T-0088: interactive Opus may mechanically validate candidate `97de519` and execute T-0088 steps 1-2 on their isolated branches. That authorization does not release SandboxDocument.cs or activate this packet.
T-0070 has a committed source HANDBACK, but its whole-range review, isolated compile/harness and primary/checkpoint/parked-input reconciliation remain pending. SandboxDocument.cs transfers only through a subsequent explicit ASTRA DECISION in T-0070 and this log naming accepted disposition, exact reconciled successor SHA/worktree, applicable review/check receipts and the new T-0086 owner. A passed harness, elapsed time, simulator release or this approval alone cannot transfer the reservation.
Even after that release, T-0086 waits for the separately reviewed T-0088 minimal prerequisite, the reviewed T-0085 range on a compatible successor, preserved parked-source hashes, renderer/dependency disposition and explicit generator/test ownership transfer. Keep the three parked Unity inputs and primary dirt unchanged; no split hunk ownership. T-0088's temporary ownership of isolated generator/launcher/test paths is confined to its minimal prerequisite and grants no T-0086 authority. No tests/imports/builds/live runs for this blocked task.