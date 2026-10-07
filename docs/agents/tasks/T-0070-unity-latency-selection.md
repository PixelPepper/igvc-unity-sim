---
id: T-0070
title: Expose explicit latency estimator selection in Unity sandbox settings and batch records
status: ready
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0070-unity-latency-opus
base: 6fdecdb5c04c90b0902ce6ff5f368899641c4da5
candidate: none
claim: none
lease: none
updated: 2026-10-06
---

# Packet

ONLY INTERACTIVE user-started Claude alias interactive-opus-t0070-20261006,
same session as T0069. ACK exact alias/model claude-opus-5-5 before edits.
Previous assignments ended. One reserved slot; no headless duplicate.
Worktree C:/Users/brand/.codex/worktrees/igvc-t0070-unity-latency/IGVC SIM.
Read README intro, this packet, docs/SANDBOX.md relevant settings, accepted
tools/sandbox_profile.py and latency_estimators.KINDS. Read primary artifact
artifacts/agents/T-0069/unity-next-slice-preflight.md for build hazards.

Base contains accepted UNINTEGRATED T0068/T0069 chain, plus isolated exact external
checkpoint of SandboxDocument.cs, SandboxPanel.cs and DisplayAwake.cs/.meta.
Pins: artifacts/agents/T-0070/source-pins.json in PRIMARY. Checkpoint is not source
acceptance; whole range7cab2b5..candidate requires review. Primary files and scene
are untouched. Preserve unrelated display-awake code; no claim it fixes freshness.

Own ONLY:
- unity/IGVCSim/Assets/IGVC/Runtime/SandboxDocument.cs
- unity/IGVCSim/Assets/IGVC/Runtime/SandboxPanel.cs
- NEW unity/IGVCSim/Assets/IGVC/Editor/SandboxLatencyValidation.cs and its NEW .meta
- docs/SANDBOX.md (selector usage and validation command only)

No scene/prefab/package/project settings/DisplayAwake/other files. Root owns Unity
import/build/integration and live validation. Author SOURCE ONLY; no Unity opening,
compilation/tests/imports/providers/delegation/live. Static source checks permitted.
Use established UI Toolkit controls/JsonUtility DTOs; no new dependencies/framework.

Requirements:
1. SandboxSettings.latency_estimator string defaults to empty (unspecified).
   Match exact Python kinds: odometry_header_interval_ema and
   wall_submit_admission_lower_quartile. Put C# identifiers in one clear source
   location; root combined validation checks parity with Python, not copied math.
   Validate empty-or-known string, enabled requires explicit nonempty choice and
   execution=checked-path. Handle JsonUtility old missing field deliberately:
   only absent/default disabled compatibility is allowed; never choose an enabled
   fallback. Reject unknown/null malformed fields unless missing-field handling
   is required by actual JsonUtility behavior; explain that distinction.
2. Navigation panel exposes a readable selector with 'Choose estimator' or other
   clearly unspecified label. Existing 18px/control sizing, edit gating and
   save/load/start validation remain. Display useful explanations for odometry
   interval EMA vs submit-to-admission wall-clock quartile, and experimental status.
   Selecting must explicitly persist the exact id, including when disabled.
   Enabling without selection should show actionable validation feedback; no
   auto-select, silent mode change, or resetting a saved id when checkbox changes.
   Restore successful settings keeps compensation disabled and selector empty.
   Preserve an invalid loaded id for rejection/feedback, not silent dropdown repair.
3. BatchTrial retains requested latency_estimator copied from spec.settings when
   constructing each trial, before start/failure handling, plus existing boolean.
   Ensure clone/save/load/start command and batch JSON carry exact same string.
   A narrow pure factory used by production batch construction is acceptable for
   behavioral testing; no new navigation or batch execution behavior.
4. Add an Editor-only validation entry point callable by root with -executeMethod
   IGVC.EditorValidation.SandboxLatencyValidation.Run (or document exact actual).
   It must use ACTUAL SandboxDocument validation and JsonUtility round trips,
   and actual batch-record factory/production seam (reflection permitted for a
   private nested type). Assertions cover old disabled JSON, old enabled rejection,
   both exact kinds enabled/disabled, unknown choice/wrong execution rejection,
   clone/command/preset persistence, and batch requested field copied before a run.
   No ROS, physics, scene generation, player build, live trial or Editor asset saves.
   Emit a clear deterministic PASS marker and test count; throw on failure so
   batchmode fails. Pure harness, no NUnit/package change. A test that merely
   checks source strings is insufficient. Add unique .meta in existing convention.
   Root will run actual Unity compile/harness under all3locks after source review;
   worker must not claim it ran or fabricate results.
5. Document old bool-enabled preset rejection and how to choose a selector. Mark
   experimental/not calibrated. No speed/guard/rule/autonomy claims. Do not edit
   historical experiment presets or plans to make them silently pass.

Unity skill principles: preserve existing serialization names and GUIDs, narrow
UI/lifecycle change, no scene re-save, no copied .meta GUID, meaningful behavioral
checks. New field default is safe; schema_version need not change because old
disabled data stays valid and enabled legacy data is explicitly rejected.

Target6min/USD5 interactive target, not billing guarantee. Commit only owned paths;
if incomplete at bound hand back honest partial. <=300word SHA/files/seams/checks
NOT RUN/risks thenstop. No primary integration or live launch. Root exact Sonnet
whole-range code review, locked Unity compile/harness and combined Python checks,
then Sol evidence and explicit integration decision. No publishing/pushing.

## Log

### 2026-10-06T22:51:26.2667523-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

INTERACTIVE interactive-opus-t0070-20261006 ONLY. T0069 r2 accepted isolated40PASS and bothreviews; all earlier assignments ended. Newworktree/checkpoint prepared with full Unity tree and current external sandbox sources preserved. SOURCE ONLY owned paths; root runs Unity compile/harness later. Read exactpacket, ACK model/session before edits. No Unity opening/build/scene mutation or primary integration.


### 2026-10-06T23:04:25.9970884-07:00 · gpt-6-astra → claude-opus-5-5 · NOTE

INTERACTIVE interactive-opus-t0070-20261006 only: refresh for listener reconnection. Assignment22:51:26 remains RESERVED, no actual ACK or committed handback as of23:04. Worktree remains clean at checkpoint6fdecdb. Read existing packet; ACK exact model/session before edits. This is not a second dispatch or assignment transfer. Root all3lock read-only readiness found no simulator processes/ports; installed Editor exists; locks released. Evidence artifacts/agents/T-0070/readiness-20261006T2304. Several Claude processes exist, but they do not prove this assignment was received. No provider/tests/build/integration launched, ownership preserved.


### 2026-10-06T23:49:20.2247615-07:00 · gpt-6-astra → claude-opus-5-5 · NOTE

INTERACTIVE interactive-opus-t0070-20261006: no ACK/handback or worktree change observed since22:51 dispatch, including four heartbeat checks. Please explicitly ACK the reserved packet if able to take it, or state relinquishment if this session cannot continue. This asks for delivery/ownership status, not a duplicate implementation. Root will not infer receipt or transfer ownership from elapsed time. No pending provider error was retried. All3locks idle check recorded state-20261006T2349.json and released; no simulator running, several unbound Claude processes remain. Existing candidate/source/evidence unchanged.



### 2026-10-07T16:44:54.5376526-07:00 · gpt-6-astra → claude-opus-5-5 · NOTE

Reserved session interactive-opus-t0070-20261006 still has no ACK or handback; worktree is clean at 6fdecdb5c04c90b0902ce6ff5f368899641c4da5. Latest all-three-lock inspection at 2026-10-07T16:44:31-07:00 detected zero local Claude processes (previous checks detected twelve), no Windows simulator processes or bridge listeners. WSL state remains unconfirmed after the earlier timed-out read-only probe; no WSL restart was attempted. All locks released. This is a process-state observation, not a handback or reassignment. Owner must ACK the existing packet when resumed or explicitly relinquish it. Root will not launch a duplicate implementation, tests, Unity build, integration or live trial. User notified of the coordination interruption under PROTOCOL live-mode guidance; completed source/evidence stays preserved.
