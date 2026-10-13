---
id: T-0088
title: Integrate and validate the reviewed IGVC 2027 profile and offline report
status: blocked
priority: P1
owner: gpt-6-astra
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/transport-probe
base: f87b89cc34996e7a346f5eb48337baf53125b29e
candidate: none
claim: none
lease: none
updated: 2026-10-12
---

# T-0088: Integrate and validate the reviewed IGVC 2027 profile and offline report

## Packet

Written by ASTRA and frozen at `ready`. Any change goes in the Log as a `DECISION`.

- **Hypothesis / objective:** Reviewed profile generation, Unity representation and offline reporting can be integrated with reproducible identities and bounded checks without changing autonomy contracts or overstating rule conformity.
- **Why now:** This is ASTRA's integration/evidence gate for [the proposal](../proposals/IGVC2027-rules-profile.md) and the accepted-with-modifications decomposition in `artifacts/agents/IGVC2027/astra-r1.md`; [PLAN.md](../../PLAN.md) gates remain authoritative.
- **Inputs:** `README.md`, this packet, T-0085/T-0086/T-0087 packets and immutable handbacks with Sonnet/Sol reviews, both IGVC2027 consultation outputs, `docs/PLAN.md`, `docs/IGVC_2027_PROFILE.md`, `docs/RUNBOOK.md`, `docs/agents/GIT_WORKFLOW.md`, `tools/igvc.ps1`, and `tools/sandbox.ps1`. Read current T-0070/T-0079/T-0083/T-0084 status and real process-held lease before planning any build/trial. Earlier realism/perception candidates need separate scoped prerequisite review before inclusion.
- **Knowledge context:** `trial-audit-promotion`, `processing-health`, `sensor-led-navigation`, `frames-and-sensors`, `agent-handoffs` from [the OKF index](../../knowledge/index.md); refresh affected canonical links only after acceptance.
- **Owned paths (may edit):** Future integration ownership: primary coordination records for T-0085 through T-0088 and `docs/agents/BOARD.md`; `docs/IGVC_2027_PROFILE.md`; new `docs/evidence/igvc2027-profile-2026-10-12.md`; ignored integration receipts/reviews under `artifacts/agents/T-0088/`. Apply only the exact reviewed source ranges from predecessor tasks after owners release them; no independent edits to worker-owned files. ASTRA retains shared schema/interface, Unity scene/prefab generation/build and lease authority, but changes outside these concrete paths need an explicit scope DECISION. This recording-only turn permits just the four new task files and BOARD.md; no implementation, evidence/doc edits or commits now.
- **Must not change:** Preserve unrelated primary dirt, source SolidWorks originals, generated URDF provenance, pinned dependencies, physical orientation/sensor mounts, whole-body footprint/sweeps, audit/health gates, recovery limits, current approved speed ceiling and six sanitized goals. No WORLD geometry in runtime policy. Preserve straight +X finish origin and 3 m half-span. T-0084 is not silently resumed; unresolved T-0079 is not accepted. No bulk branch import, automatic simulator takeover, hidden overlay replacement or certification claim. Dirty overlapping paths block integration until reconciled without overwriting them.
- **Baseline identities:** Primary HEAD `f87b89cc34996e7a346f5eb48337baf53125b29e`; profile/legacy worktree anchor `b517a9924d80750bd19ee1094b95984fe6463b96`. Dirty primary is not a frozen baseline. Before execution record reviewed source ranges/prerequisites, dirty-input dispositions, combined SHA, player/build hash, profile hash, separate ROS overlay identity, course/mission/autonomy hashes, load, lease and run ID. All candidate/build/live identities are pending.
- **Allowed checks:** After unblock, up to 3 focused check batches: (1) `wsl -d Ubuntu-24.04 -- bash tools/check_core.sh`, plus the three new/updated focused suites and frozen 12-case byte/profile matrix when not already covered; (2) ASTRA-managed pinned Unity import/build and `IGVC.RulesProfile2027Validation.Run`, with visual and RGB/depth/lidar geometry checks under the documented build workflow; (3) the single frozen trial's existing independent audit and `tools/rules_score_2027.py` report using recorded inputs. Freeze exact supported launcher/build/audit/report commands and receipts in a DECISION before execution. Do not repeat passing broad checks without new changes/evidence. For this recording-only turn, only board generation/check and task-format/diff validation are authorized.
- **Live trial:** At most 1 after reviewed integration, explicit LEASE-REQUEST/LEASE-GRANT and idle-resource verification. Proposed original instance: TCP 10000, ROS domain 42, managed `tools/igvc.ps1` / sandbox workflow, seed 2027 normal with `igvc2027`, unchanged approved controller/speed, separate overlay. Record exact profile/command, committed source, runtime/termination budget and build identity before grant. Respect any existing live session; verify shutdown before lease release. No live trial is granted by this packet.
- **Acceptance:** Both reviewers approve exact candidates with no unresolved blocking findings; review prerequisite realism/perception changes separately and integrate only reviewed ranges. T-0085 dimensions, no-barricade policy, determinism/legacy matrix and clearance tests pass; centered obstacles have 1.524 m on BOTH sides to inner paint edges and staggered bottlenecks are detected. T-0086 width/dash/ramp/finish representation is validated in Unity, including actual sensor surfaces; source mesh containment alone is insufficient. T-0087 timing/ticket observations bind to immutable input hashes without changing audit verdicts or resolving official ambiguities by assumption. Document implemented, tested, live-evidenced and pending behavior separately, including retained six-goal mismatch, opening-speed/ticket-sign ambiguities and missing rules image pages. A timing result over 360 seconds is reported as such, never fixed by an unapproved speed increase; 6/6 progress alone is no audit pass. An audit failure limits the claim and blocks promotion. ASTRA-authored acceptance requires Sonnet + Sol and explicit user approval recorded as DECISION; any new live evidence needs Sol's post-integration review before promotion. No automatic repeatability, physical calibration or 2027 compliance claim.
- **Stop condition:** Remain blocked until predecessor handbacks/reviews, ownership reconciliation and prerequisite decisions are complete. After dispatch, stop on a dirty-path conflict, failed combined/build/audit check, missing resource/identity, scope/invariant change or wall limit; preserve all attempts and report partial evidence. No automatic retry or silent reassignment. Do not promote without protocol gates.
- **Budget:** `gpt-6-astra`, high effort, 35-minute active integration/check window once unblocked; no paid worker launch in this recording turn. Each eventual reviewer: high effort, USD 5 target (`--max-budget-usd 5` for Claude), 10 minutes, one pass per handback; exact models `claude-sonnet-5-5` and `gpt-6.1-sol`. Record actual usage; targets are not universal enforced caps. No budget escalation is authorized here.

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

Blocked on reviewed immutable T-0085/T-0086/T-0087 handbacks, prerequisite review and dirty-path/ownership reconciliation. No integration, build, live lease, shared-interface change or promotion is dispatched now.
ASTRA owns integration and final validation; Sonnet reviews code and Sol reviews evidence, with explicit user approval required for acceptance of ASTRA-authored work under PROTOCOL.md.
Current user instruction authorizes only recording these four task files and regenerating BOARD.md, with no commits and no other file edits. Preserve all unrelated primary work.

### 2026-10-12T18:10:00-07:00 · gpt-6-astra → all · NOTE

Recording checks: all four new packets have required headers and Packet/Handback/Log sections. The requested WSL board command failed with `Wsl/Service/E_ACCESSDENIED`; Windows `python` is unavailable. Concurrent commit `3914c504d04dc0c45a10a7ae4a3f73c3c4e833c3` introduced another T-0085 task, which also prevents valid board generation under board.py's duplicate-ID check. BOARD.md was not hand-edited. Resolution is pending user/other-owner coordination; no code tests, worker launches, commits or live actions were performed in this turn.

### 2026-10-12T19:41:10-07:00 · gpt-6-astra → all · DECISION

Integration plan accepted for scheduling only; **T-0088 remains blocked** on prerequisite review, T-0086 and dirty-path reconciliation. Current primary is `codex/transport-probe` at `202336bd59404a9db2b54d3ee7e5921b621b9ee7`, not the packet's historical HEAD. The user now authorizes a coordination-only commit; no source merge/cherry-pick into primary or main, build, trial or promotion this turn.
1. **Independent report first, in a later integration turn:** cherry-pick with `-x` exactly `559119cad155fb90d65842580342d4a1bb5e1159`, `62202bae7fec4aaba510b11a21bf1aa9600bea9f`, `1f701b87b9821c4259866d09f8b17ad1c814626e`, in that order. Verified `b517a99..1f701b8` touches only `tools/rules_score_2027.py` and `tools/tests/test_rules_score_2027.py`; its reused checker/profile match primary HEAD. No ancestor realism code is needed. Recheck clean destination paths and dependency identities before execution; validate this slice on the actual integration tree.
2. **Separate minimal prerequisite review before T-0085:** extract only the `b517a99^..b517a99` rule-pothole generator changes to `tools/generate_course_variant.py`, `tools/tests/test_rule_potholes.py` and the pothole-flag/forwarding hunks of `tools/sandbox.ps1` into a new isolated, scoped candidate. Review it with Sonnet + Sol before acceptance/cherry-pick. Exclude `b517a99`'s `lane_node.py`, `lanes.py`, painted-pothole perception tests and processing-idle test changes. Do not cherry-pick all of `b517a99` or use path copies that silently include ancestors. Launcher adaptation around the earlier `-Conditions` context is part of this new candidate and review, not authority to import `e8a5f02`.
3. **Reconcile dirty overlapping primary paths without overwrite/stash**, especially `tools/sandbox.ps1`, before any application to them. Record a reviewed checkpoint/port and immutable hashes in a later scoped decision; preserve unrelated latency/batch work. Once the minimal prerequisite is accepted and applied, cherry-pick with `-x` the complete T-0085 range in order: `6eeb552dcf8b700030ca2a8af7272be0c2e89ae5`, `937a7e60a3557ab403b688404bf1205ebd1f8a10`. Include the frozen legacy fixture. Any conflict resolution or functional port gets its own exact diff and review; acceptance of the original SHAs does not cover new behavior.
4. **Do not import the earlier realism chain by ancestry.** `e8a5f02337ee8ed32111a96732a89c821d57303a` (lighting/assets/conditions), `b4054a0b247f23b5a11e4c4e680179e5f1da86ea` (contrast-relative lane perception), `5931c61164ac59aa294bba7e510393f98bc68891` (dark-pothole perception), and the remaining perception portion of `b517a99` each require separate scoped source/evidence review before any inclusion. They are deferred, not rejected or accepted prerequisites. If realistic rendering is later selected, review its complete dependency chain in that order; unaudited laps and the disclosed stale-overlay attempts do not establish acceptance. For an ideal-renderer path, review a minimal Unity port instead. Live white-pothole navigation still needs an explicit reviewed perception/representation decision; visual generation alone does not prove detection.
5. **T-0086 next, only after ownership reconciliation:** retain T-0070's SandboxDocument reservation as decided in T-0086; no concurrent owner. Preserve its three hashed parked Unity inputs, establish the successor base/worktree and explicit release/transfer, then dispatch the bounded width/dash/rendering slice to the existing interactive Opus session with exact paths. Review its complete candidate (including any port), then cherry-pick only its reviewed range. Neither its branch nor the sim-realism branch may be merged wholesale.
6. **Combined evidence last:** freeze integrated source/profile/course/mission/autonomy hashes and supported commands before execution. Run the packet's bounded core/focused checks, independent frozen legacy/profile 12-case matrix and real launcher unset/set/unknown-profile checks; ASTRA then runs pinned Unity validation/build and actual RGB/depth/lidar/ramp/finish inspection under managed locks. Only afterward consider the separately granted single live trial/overlay, unchanged audit and T-0087 report with actual course/checker/run-byte provenance and the approved declared-receipt caveats. No speed increase, auditor relaxation or automatic repeat; failures stop the gate.
7. Record implemented, tested, live-evidenced and pending claims separately. New integration changes/evidence need their applicable Sonnet/Sol review; new live evidence requires Sol's post-integration review before any promotion and ASTRA-authored acceptance retains user-approval gates. Realism, general-route validator edge cases, official scoring, retained six-goal mismatch, missing rules images, hardware fidelity and competition compliance remain unproven. Refresh affected knowledge/profile/evidence documentation only in the later authorized integration slice.

### 2026-10-12T19:43:44-07:00 · gpt-6-astra → all · NOTE

The requested `wsl -d Ubuntu-24.04 -- python3 tools/agents/board.py` failed before Python execution with `Wsl/Service/E_ACCESSDENIED` (exit 1). WSL is unavailable to this session. Per the user instruction, leave BOARD.md for a later turn; no fallback generation or hand edit. Its SHA-256 remains `2e8abfcb99575200e6b96175d8ce7e94d847daa75fcc01af15a4529723ce275c`; it is now stale relative to these decisions.
PowerShell structural checks passed for the four task headers and Packet/Handback/Log sections, required candidate SHAs and repository-wide task-ID uniqueness. This is not an execution of board.py or a behavioral test. Preservation checks found no changes to the 16 inventoried unrelated dirty tracked/untracked files and source proposal; no simulator, source tests or integration ran. The coordination commit is limited to T-0085 through T-0088 plus the unchanged IGVC2027 source proposal; BOARD.md is excluded.

### 2026-10-12T19:44:45-07:00 · gpt-6-astra → all · NOTE

Coordination commit **not created**: explicit-path `git add` for the four task files and source proposal failed with `Unable to create .../.git/index.lock: Permission denied`. The session permits no approval escalation. The index remains empty and HEAD remains `202336bd59404a9db2b54d3ee7e5921b621b9ee7`; all five files remain untracked, saved in primary. No unrelated file was staged or reverted. No-index whitespace checks reported no findings for those five files.
Later writable session: regenerate BOARD.md with the requested WSL command, inspect it, then stage only these four tasks, the optional source proposal and regenerated BOARD.md; commit with `coord: accept IGVC 2027 slices and plan scoped integration`. No code integration is authorized by this continuation note.
