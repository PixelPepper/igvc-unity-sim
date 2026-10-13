---
id: T-0088
title: Integrate and validate the reviewed IGVC 2027 profile and offline report
status: ready
priority: P1
owner: gpt-6-astra
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0088-igvc2027-integration-astra
base: 7d0ad25
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

### 2026-10-12T23:08:22-07:00 · user → gpt-6-astra · DECISION
The user said "ok approve and go" in the interactive claude-opus-5-5 session, in reply to a summary that listed three items: T-0070's source handback 97de519 awaiting root Unity compile, harness and reviews; T-0088's integration plan; and T-0089's continuation. claude-opus-5-5 relays it verbatim.

As interpreted for ASTRA's confirmation:
- **T-0070:** approve the handback and proceed to the root Unity compile and harness plus Sonnet and Sol reviews.
- **T-0088:** proceed with plan steps 1-2 (cherry-pick T-0087 with -x; scoped rule-pothole prerequisite candidate and reviews).
- **T-0089:** proceed with a bounded continuation.

Integration and acceptance actions remain ASTRA's decisions.

### 2026-10-12T23:14:29.4263754-07:00 · gpt-6-astra → all · DECISION

The user's "ok approve and go" authorizes plan steps 1-2 now. `ready` in the header means those two bounded offline steps only; T-0086, full combined integration, Unity/player/sensor checks and any live gate remain blocked. Interactive `claude-opus-5-5` is ASTRA's mechanical executor for these recorded operations; ASTRA retains acceptance and promotion authority. Preserve primary on `codex/transport-probe`, including unrelated dirty work. No main/primary source cherry-pick, snapshot of all dirt, stash, reset, cleanup or branch checkout in primary.
Explicit scoped exception to GIT_WORKFLOW's usual primary integration/snapshot route: stage the reviewed report on NEW branch `codex/t0088-igvc2027-integration-astra`, isolated worktree `C:/Users/brand/.codex/worktrees/igvc-t0088-integration/IGVC SIM`, anchored at the committed user-reported coordination checkpoint `7d0ad25^{commit}`. Resolve its full SHA and record it before creation. This branch represents committed-history staging only, not the whole dirty current application. If that object is absent, is not the reported coordination commit, or is not an ancestor of current primary HEAD, STOP for ASTRA; never silently choose a new base. The dated base in the original packet is superseded for steps 1-2 only.
At most two implementers and two concurrent reviewers globally. Here the interactive executor plus, if used, one separately launched prerequisite Opus are the only implementation slots; T-0070 authoring has ended and T-0086 stays blocked. T-0089's completed worker must not be restarted. Queue reviews across tasks; no recursive delegation by a headless worker. Heavy offline checks/Unity imports must respect T-0070's all-three-lock validation window.

### 2026-10-12T23:14:29.4263754-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

STEP 1: integrate the accepted T-0087 report ONLY into `codex/t0088-igvc2027-integration-astra`. Before branching run `git status --short`, `git worktree list`, `git branch -vv` in primary, record full primary HEAD/branch, and hash/inventory its dirty tracked and untracked inputs. Verify index has no unrelated staged entries, no cherry-pick/rebase/merge in progress and no conflicting writer. Do not touch `.claude/worktrees/sim-realism` inputs. A pre-existing target branch/worktree is a stop-and-inspect condition, not permission to delete/reuse it blindly.
Verify source range `b517a9924d80750bd19ee1094b95984fe6463b96..1f701b87b9821c4259866d09f8b17ad1c814626e` consists of the THREE commits below, touching ONLY `tools/rules_score_2027.py` and `tools/tests/test_rules_score_2027.py`; check T-0087 final Sonnet/Sol and ASTRA acceptance records. Verify target paths absent/clean and byte-identical reused `tools/check_competition_profile.py` and `config/competition/igvc-2027-autonav.json` between the selected committed base and reviewed source. Also record relevant dependency/import identities; drift blocks application, it does not authorize a port. Recheck pristine destination index/worktree immediately before each pick.
Run these commands individually, stopping at the first nonzero exit or conflict. No conflict-resolution edits are delegated by step 1; preserve the partial state and report. All git below is for the interactive session, not this restricted Codex exec session:

```powershell
git worktree add 'C:/Users/brand/.codex/worktrees/igvc-t0088-integration/IGVC SIM' -b codex/t0088-igvc2027-integration-astra 7d0ad25
Set-Location 'C:/Users/brand/.codex/worktrees/igvc-t0088-integration/IGVC SIM'
git cherry-pick -x 559119cad155fb90d65842580342d4a1bb5e1159
git cherry-pick -x 62202bae7fec4aaba510b11a21bf1aa9600bea9f
git cherry-pick -x 1f701b87b9821c4259866d09f8b17ad1c814626e
```

After all three picks, verify ONLY the two reviewed paths differ from resolved base, patch/content equality to the reviewed final blobs, clean index/worktree and all three `-x` provenance trailers. Record full resulting tip as `report_integrated_sha` in primary `artifacts/agents/T-0088/step1/receipt.json`; stop if that directory already contains a completed run. Do not label the whole T-0088 task integrated.
Run focused checks from that actual integration worktree using `wsl -d Ubuntu-24.04 --cd '/mnt/c/Users/brand/.codex/worktrees/igvc-t0088-integration/IGVC SIM' -- ...`: (1) `python3 -m unittest discover -s tools/tests -p test_rules_score_2027.py`; (2) `python3 -m unittest discover -s tools/tests -p test_competition_profile.py`; (3) `python3 tools/rules_score_2027.py --help` plus one fresh, hash-bound synthetic CLI fixture matching T-0087 `rev2/check3-smoke.txt` (locate its preserved fixture, verify hashes, recreate under ignored step1 outputs; never alter old evidence). Assert expected report JSON/exit semantics and unchanged input bytes; recorded 21/11 counts are expectations, not results. Observe the global idle checks/leases in T-0070 before test batches; no ROS launch or overlay build.
Record exact base/source/result SHAs, changed paths and dependency hashes, each command/cwd/exit/count, fixture/input/output hashes, UTC/local timings, preserved primary pre/post dirty hashes and all failures. Append a <=300-word HANDBACK in this task. Existing unchanged T-0087 source reviews stand; queue one exact-model Sol evidence review of this NEW integration receipt using the T-0070 headless command form, high/USD5 target/10 minutes, output `artifacts/agents/T-0088/step1/sol-review.md` with model header log. Its request distinguishes declared observations from official timing, discloses the accepted nits and confirms no inherited realism code. No redundant Sonnet pass unless a source/dependency change actually occurred; such a change first stops step 1 for ASTRA. Full check_core and combined profile/Unity validation remain later gates before promotion to primary; the isolated report checks alone do not complete them.

### 2026-10-12T23:14:29.4263754-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

STEP 2: after step 1's three focused checks pass and its full `report_integrated_sha` is recorded, prepare ONE minimal rule-pothole prerequisite candidate. Do not apply it to the staging integration branch yet. Owner is the interactive `claude-opus-5-5` session; optionally it may launch ONE headless exact `claude-opus-5-5` worker in its place for this slice, not alongside a second implementation of it. Explicitly ACK the chosen owner in this log before edits. Headless uses high effort, `--max-budget-usd 10 --permission-mode acceptEdits --no-session-persistence --output-format json`, 35-minute wall limit; interactive has the same tracked budget target. No automatic retries, provider substitution or further delegation. Root validation orchestration is not authority for that worker to build Unity.
New branch `codex/t0088-rule-pothole-prereq-opus`; new worktree `C:/Users/brand/.codex/worktrees/igvc-t0088-rule-pothole/IGVC SIM`. BASE is EXACTLY the recorded full `report_integrated_sha`, not moving primary, b517a99, sim-realism HEAD or its dirty files. Resolve/recheck staging HEAD equals that receipt; substitute that full SHA in `git worktree add 'C:/Users/brand/.codex/worktrees/igvc-t0088-rule-pothole/IGVC SIM' -b codex/t0088-rule-pothole-prereq-opus <report_integrated_sha>`. Stop on existing branch/path, dirty base or dependency/ownership drift. Record the full base in ACK and handback; task header remains the integration anchor, not this subcandidate.
Inputs: README, this step-2 decision, T-0085/T-0087 acceptance and the actual immutable diff `b517a9924d80750bd19ee1094b95984fe6463b96^..b517a9924d80750bd19ee1094b95984fe6463b96`. Extract/port hunks from that diff, not whole-file copies from its descendants. Own ONLY `tools/generate_course_variant.py`, `tools/tests/test_rule_potholes.py` and `tools/sandbox.ps1` IN THE NEW WORKTREE. ASTRA delegates these three isolated paths solely for this candidate; primary dirty sandbox.ps1 stays untouched and generator ownership does not transfer to T-0086.
Allowed generator hunks: opt-in `bowl`/`rule` style selection/validation and CLI forwarding, 0.6096 m solid-white-circle representation with depth 0, and the narrow placement/metadata adjustments actually needed by that b517a99 rule-pothole delta. Omitted style must preserve legacy bowl behavior and emitted course/mission/autonomy bytes. Allowed launcher hunks: PotholeStyle parameter/validation and forwarding to the actual batch course generator invocation only; adapt against this base's existing arguments, preserving latency/batch/instance behavior. Do not import `-Conditions`, sim_conditions, lighting/material/realism infrastructure or their ancestor context just to make a patch apply. Tests may extend the named test file to verify this port behavior.
EXCLUDE all profile/drum/dash/variable-width/passages work from T-0085/T-0086, `course_passage.py`, Unity/C# edits, perception files `lane_node.py`/`lanes.py`, painted-pothole perception tests, processing-idle tests, runtime policy, auditors, pins, ROS interfaces and unrelated b517a99 or e8a5f02 ancestry. No claim that generated white circles are detected/rendered/drivable; T-0086 and a reviewed perception/representation decision still gate that. Stop for a required fourth source/test file or an unapproved semantic dependency.
Three focused offline batches, under the shared idle-resource rules: (1) `python3 -m unittest discover -s tools/tests -p test_rule_potholes.py`; (2) `python3 -m unittest discover -s tools/tests -p test_course_variants.py`; (3) actual generator CLI and isolated launcher-argument behavioral smoke, plus immutable legacy-byte comparison for seeds 2027-2030 x easy/normal/hard. Freeze outputs from the exact step-2 BASE before edits, then compare omitted style and explicit bowl against those 12 course/mission/autonomy triples; compare against the T-0085 b517a99 legacy fixture where available and report any mismatch without changing that fixture. The base comparison protects this port independently of inherited branch assumptions.
CLI/launcher cases: omitted, explicit bowl, explicit rule and unknown style. Rule output must contain 0.6096 m white zero-depth circles with unchanged non-pothole geometry; unknown must fail before side effects. Exercise the production parameter/forwarding seam with inert process/WSL stubs (or extracted actual PowerShell AST statements in an isolated harness), checking the resulting generator arguments and paths containing spaces. Do NOT launch tools/sandbox.ps1 against real processes/ROS just to test flags; source-string matching is not behavioral verification. Save ignored harness/commands and evidence under `artifacts/agents/T-0088/prerequisite-r1/` and document any unexercised path honestly. No live simulator/Unity/package install/overlay rebuild.
Commit only the three owned paths, then freeze candidate SHA, full base..candidate diff, source hunk origins/adaptations, baseline/candidate byte hashes, command/results and actual usage. Headless returns <=300-word HANDBACK for interactive relay; it never writes docs/agents. Do not cherry-pick this candidate, T-0085's commits, or any realism chain at this step. Stop after candidate/reviews; failures and partial evidence stay preserved.
Launch BOTH read-only reviews against the exact new full base..candidate range, not against b517a99 alone: Sonnet `claude-sonnet-5-5` high/USD5/10 minutes checks scope/hunk provenance, launcher adaptation, default byte preservation and behavioral coverage; Sol `gpt-6.1-sol` high/USD5 target/10 minutes checks baseline identity, all 12 triples, actual command/exit/hash evidence, usage and untested renderer/perception limits. Use T-0070's exact headless command forms with `$reviewDir` = absolute primary `artifacts/agents/T-0088/prerequisite-r1`; write separate bounded sonnet/sol request files naming this subcandidate. Verify actual model/exit status, preserve JSON/stderr, relay both REVIEW blocks with `relayed-from`, and stop for ASTRA's acceptance decision. At most two reviewers globally; finish T-0070's pair before starting another pair. No worker self-acceptance or automatic retry on a finding.

### 2026-10-12T23:14:29.4263754-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

Coordination mechanics delegated explicitly: this Codex turn edits ONLY primary `docs/agents/tasks/T-0070-unity-latency-selection.md`, `docs/agents/tasks/T-0086-igvc2027-lanes-rendering.md`, `docs/agents/tasks/T-0088-igvc2027-integration-validation.md` and `docs/agents/tasks/T-0089-reference-autonav-map.md`. BOARD.md and the commit are LEFT TO THE INTERACTIVE SESSION; this is a narrow exception authorizing mechanical board generation/commit for ASTRA, not new header/acceptance decisions. The user-reported earlier commit `7d0ad25` must not be recreated.
From primary `C:/Users/brand/Documents/ChatGPT/IGVC SIM`, run `wsl -d Ubuntu-24.04 -- python3 tools/agents/board.py`, then `wsl -d Ubuntu-24.04 -- python3 tools/agents/board.py --check`; inspect the generated board and exact-path diff/whitespace. Confirm there are no unrelated staged entries; do not unstage someone else's index. Stage ONLY the four exact task paths above plus `docs/agents/BOARD.md`, using explicit paths, then commit with message `agents: dispatch T-0070 validation and T-0088 scoped integration`. No proposals, source, evidence, generated Unity assets or other tasks in this commit. Do this once before source execution so dispatches are durable; relay later execution results in a separate coordination-only commit after regenerating/checking the board. Stop if concurrent edits make the scoped commit ambiguous; preserve all work.
Do not update headers to accepted/integrated, release T-0070's source reservation, dispatch T-0086 or promote a baseline on ASTRA's behalf. Return the coordination commit SHA, generated-board check result and all mechanical execution receipts. This session has run no git, WSL, Unity, source tests or paid reviewers; all dispatched execution remains pending unless an existing evidence record is explicitly identified.
### 2026-10-12T23:22:11-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
STEP 2 owner: the interactive claude-opus-5-5 session itself; no headless worker is launched for this slice. Base: report_integrated_sha 37a6e892aa35cde9ec79b002415c5144630c80d7, from step 1 (receipt artifacts/agents/T-0088/step1/receipt.json). Step 1's three focused checks passed, and its Sol evidence review is running. Heavy step-2 test batches will wait until T-0070's locked Unity validation window, now running, releases its locks.

### 2026-10-12T23:26:29-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
```text
STEP 1: T-0087 report staged on codex/t0088-igvc2027-integration-astra.
Hypothesis and outcome: the exact reviewed report slice applied cleanly to 7d0ad25.
Changed files / SHAs: worktree C:/Users/brand/.codex/worktrees/igvc-t0088-integration/IGVC SIM, base 7d0ad25.
  Picks with -x: 559119c -> 228289b, 62202ba -> 5b686c7, 1f701b8 -> 37a6e89.
  report_integrated_sha = 37a6e892aa35cde9ec79b002415c5144630c80d7.
  Only tools/rules_score_2027.py and tools/tests/test_rules_score_2027.py differ from base; both blobs equal
  1f701b8's. Checker and profile blobs are identical in base and source.
Evidence: artifacts/agents/T-0088/step1/ (preconditions, commands, verify, run_checks, check1-3,
  fixture/, report-compare, primary-dirty-pre/post, receipt.json sha256 0f15a51a).
  commands.txt is transcribed from session output because the live tee failed on an unquoted path.
Tests: test_rules_score_2027 21 OK; test_competition_profile 11 OK; smoke: help 0, report 1 (synthetic
  careless_driving), usage 2, inputs unchanged. The fixture inputs are byte-identical to T-0087 rev2; the
  report differs only in its three input-path strings.
Live: none. Unrelated primary dirty files are unchanged pre/post.
Claim level: tested (isolated slice). T-0088 is NOT integrated; the combined gates remain.
Remaining risks: the accepted T-0087 limitations are in its acceptance DECISION and not re-listed in this
  receipt (Sol nit 2). The scripts print results rather than asserting them (Sol nit 3).
```

### 2026-10-12T23:26:29-07:00 · claude-opus-5-5 → gpt-6-astra · NOTE
Step 1 evidence review relayed verbatim. relayed-from: artifacts/agents/T-0088/step1/sol-review.md. Model per log header: `model: gpt-6.1-sol`. The invocation is recorded in step1/sol-launch.txt.

### 2026-10-12T23:22:56-07:00 • gpt-6.1-sol → gpt-6-astra • REVIEW
Task: T-0088   Candidate: 37a6e892aa35cde9ec79b002415c5144630c80d7   Scope: evidence
Verdict: approve-with-nits

Findings (ranked, ≤ 5):
1. [nit] artifacts/agents/T-0088/step1/commands.txt:1; receipt.json:7: Command provenance is partly reconstructed, and base/intermediate identities are abbreviated.
   Mechanism: The failed tee weakens contemporaneous evidence of command exits, pre-pick cleanliness and sequencing. WSL also recorded `head n/a`. These limitations do not undermine the resulting tree: Git independently confirms the three ordered commits, matching patch IDs, trailers and final blobs.
   Evidence: Read commands.txt, preconditions.txt, verify.txt and run_checks.out; resolved base to `7d0ad2591a1489c21f85b8b85414574bbdcb79f9`, an ancestor of recorded primary HEAD. | UNVERIFIED: Original command transcript and historical per-pick cleanliness.

2. [nit] artifacts/agents/T-0088/step1/receipt.json:77: The new receipt does not explicitly enumerate or link all accepted T-0087 limitations.
   Mechanism: Readers must consult T-0087’s acceptance DECISION for absence-of-crossing failure with an unusable clock, incomplete-clock duration failure, partial E-stop chronology checking, declared connected-check trust and exit-code ambiguity. The unchanged commit message also retains the superseded “Every other path is unknown” wording. None establishes a new defect in this integration.
   Evidence: Compared receipt, fixture report and final T-0087 reviews/DECISION. Gross-clock trust, synthetic provenance, passage uncertainty and certification limits remain visible in the report. | UNVERIFIED: Real timing, geometry and E-stop chronology.

3. [nit] artifacts/agents/T-0088/step1/run_checks.sh:5; smoke.sh:29: The scripts print results without enforcing all expected exits/report values or stopping after a failed batch.
   Mechanism: Their final shell exit alone cannot certify success. For this receipt, individual saved exits and independent inspection establish the expected results; no failed batch is concealed.
   Evidence: Saved checks show 21/11 tests OK, help 0, report 1, usage 2 and unchanged inputs. The report preserves the synthetic careless-driving failure. | UNVERIFIED: Independent behavioral execution.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓. Exactly three reviewed picks entered the branch; only the two report/test files differ from base. Pairwise patch IDs match, final blobs equal `1f701b8`, all `-x` trailers match, and checker/profile dependencies are identical. None of `e8a5f02`, `b4054a0`, `5931c61` or `b517a99` is an ancestor. Runtime policy, mounts, footprints and auditors are untouched.

Tests run: none (read-only). Independently ran Git range/diff/blob/trailer/patch-ID checks, `git diff --check`, SHA-256 recomputation and recursive report comparison. All four source/dependency hashes and three fixture hashes match. Fixture inputs equal rev2 bytes; reports differ only at the three `/inputs/*/path` strings. Smoke changes only its comment, cwd and output directory. All 15 inventoried primary dirty files match pre/post hashes and current bytes; primary HEAD/status/index remain consistent. `.claude/` contents were not inventoried, so blanket preservation there is UNVERIFIED.

Missing acceptance coverage: Implemented: exact report slice staged on the isolated branch. Tested: saved focused offline results support this slice; declared crossing arithmetic is 354.7 seconds, not official timing. Live-evidenced: none. Pending: combined core/profile/legacy/launcher checks, prerequisites, Unity/sensor validation, actual checker/course-byte binding, real-run replay and separately authorized live gates. Historical idle-resource verification is absent from this receipt. These checks do not complete T-0088 or authorize promotion; official scoring, missing rules images, hardware fidelity and compliance remain UNVERIFIED.

### 2026-10-12T23:28:48-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
```text
STEP 2: minimal rule-pothole prerequisite candidate.
Owner: interactive claude-opus-5-5 (no headless worker).
Branch codex/t0088-rule-pothole-prereq-opus, worktree C:/Users/brand/.codex/worktrees/igvc-t0088-rule-pothole/IGVC SIM.
Base 37a6e892aa35cde9ec79b002415c5144630c80d7 (report_integrated_sha); candidate a089996; 3 files, +84 -7.
Hunk origins (patches in artifacts/agents/T-0088/prerequisite-r1):
- tools/generate_course_variant.py: b517a99^..b517a99 hunks applied exactly (the base blob equals b517a99^'s).
  Result sha256 16b952bb = b517a99's blob.
- tools/tests/test_rule_potholes.py: new file from b517a99, exact (56ed07e5).
- tools/sandbox.ps1: b517a99's two hunks adapted. -PotholeStyle ('bowl'|'rule', default 'bowl') goes after
  -Instance because this base has no -Conditions; --potholes is forwarded on the batch generator call only.
  Result sha256 63964a58.
Excluded: b517a99's perception files and tests, and all T-0085/T-0086 work.
Checks, run under no locks after T-0070's window had released them:
  (1) test_rule_potholes: 4 OK.
  (2) test_course_variants: 15 OK.
  (3) Bytes, CLI and launcher:
    - The 12 legacy triples (2027-2030 x easy/normal/hard) are identical for: the base blob executed via git
      show, the candidate with the style omitted, the candidate with explicit bowl, and the T-0085 b517a99
      fixture.
    - CLI: omitted and bowl give dark bowls; rule gives 0.6096 m white zero-depth solid_white_circle potholes
      with identical non-pothole obstacles at the same seed; unknown exits 2 and creates no output directory.
    - launcher_harness.ps1 evaluates the AST-extracted actual param block and generator statement with a
      recording stub. Omitted and bowl give --potholes bowl; rule gives --potholes rule; painted is rejected
      at binding. Paths with spaces stay single arguments; the base ignores the flag.
Evidence: artifacts/agents/T-0088/prerequisite-r1/ (batch*.out/txt, bytes-*.json, cli-smoke.json, launcher-harness*.txt, harness scripts).
Claim level: tested (offline). Generated white circles are not shown to be rendered, detected or drivable.
```

### 2026-10-12T23:33:33-07:00 · claude-opus-5-5 → gpt-6-astra · NOTE
**Step-2 reviews of 37a6e89..a089996,** relayed verbatim below. Both are approve-with-nits with no blocking finding.
- Sonnet: relayed-from artifacts/agents/T-0088/prerequisite-r1/sonnet-review.json; modelUsage claude-sonnet-5-5 only, is_error=false, USD 0.74.
- Sol: relayed-from artifacts/agents/T-0088/prerequisite-r1/sol-review.md; log header `model: gpt-6.1-sol`.

**On Sol #3 (usage):** the implementer is this interactive session, and its per-task token or cost usage is not separately measurable here. Usage is UNAVAILABLE.

**On Sonnet #1:** rule courses are not yet loadable faithfully by the current Unity player, so they must not be run before T-0086. Stopping here for your acceptance decision. No cherry-pick of this candidate or of T-0085 has been made.

### 2026-10-12T23:30:44-07:00 · claude-sonnet-5-5 → gpt-6-astra · REVIEW
Task: T-0088   Candidate: a089996eda4785cc55f59e1166688d7de798b537   Scope: code
Verdict: approve-with-nits

Findings (ranked, ≤ 5):
1. [minor] tools/generate_course_variant.py:243-246 (with unity/.../CourseVariant.cs:74-78,182-201 and SandboxDocument.cs:71): the generator now emits rule courses that the base Unity player cannot represent faithfully, and may reject.
   Mechanism: In rule mode `pothole_rim()` is 0 and `pothole_rims_clear()` returns True. Two rule potholes can therefore sit closer than 0.6096+0.85 = 1.46 m. At this base, `CourseVariant.Read` throws "Pothole rim overlaps another depression" for every pothole pair, whatever its depth. `Bowl()` also still draws a gray 0.85 m rim plus a flat dark disc, not a white circle. `SandboxDocument.ValidateEdit` requires pothole depth ≥ 0.02, so any sandbox edit of a rule course would throw. The handback says the circles are not shown to be rendered, which is accurate. But `-PotholeStyle rule` is a live-reachable flag with no warning.
   Evidence: Read CourseVariant.cs, SandboxDocument.cs and the generator placement loop. | UNVERIFIED: whether seeds 2027-2030 ever place a rule pair in [0.81, 1.46) m. I did not run it. Unity load and render behavior was not run.
2. [minor] tools/sandbox.ps1:11,72: `-PotholeStyle` has an effect only on the non-instance `-Batch` generator call, and nothing says so at run time.
   Mechanism: With `-Instance`, line 71 skips generation and only checks that `autonomy.json` exists. The target folder is keyed `seed-difficulty` with no style. A stale bowl layout is therefore accepted silently under `-PotholeStyle rule`. Without `-Batch`, the line-80 default-2027 generation drops the flag, so a rule session course is bowl. Other generator callers (igvc.ps1, docker.ps1, parallel_batch.py, linux_session.py) are unchanged. This is documented only in the param comment.
   Evidence: Read sandbox.ps1:1-85 and the AST harness. The harness evaluates only the extracted statement, not the `-Instance`/`continue` or line-80 paths. | UNVERIFIED: the full launcher flow, which the task forbids testing against real processes.
3. [minor] tools/tests/test_rule_potholes.py:19-25: the legacy-preservation test is nearly tautological.
   Mechanism: It compares `generate(s,d)` with `generate(s,d,potholes='bowl')`, which share one code path. It would still pass if the default layout drifted from the base. Real legacy protection exists only in the out-of-tree evidence: 12 triples versus the git-show base blob and the T-0085 fixture. The committed suite does not pin default bytes. Also, `tools/tests/test_docker_reporting.py` exercises the changed `main()` and was not run in the batches.
   Evidence: Read the test and batch3.out ("omitted == base (12 triples)", "explicit bowl == base (12 triples)", "base == T-0085 b517a99 legacy fixture"). | UNVERIFIED: test_docker_reporting, which is expected to pass because it calls the real `generate` with default args.
4. [nit] tools/generate_course_variant.py:244 and tools/sandbox.ps1:11-13: comment accuracy and parameter order.
   Mechanism: "Same random draws as 'bowl'" holds per attempt only. Rule radii and rims change which candidates are accepted, so later pothole positions diverge from bowl layouts. Barrels and barricades are still identical, which the test asserts. Inserting `-PotholeStyle` before `Width`/`Height` shifts any positional use of those parameters; the original T-0085 change did the same after `-Conditions`.
   Evidence: Read the diff and the placement loop.

Provenance and adaptation (checked, no defect):
- Scope: `37a6e89..a089996` is one commit touching exactly the 3 owned files (+84/-7). b517a99 is not an ancestor. No perception, lanes or T-0085/T-0086 hunks are present.
- Hunk provenance: I diffed the `b517a99^..b517a99` patch for the three files against the candidate's patch.
  - Generator and test hunks are byte-identical, including the blob index `a168a5e..ca8e28f`.
  - Only sandbox.ps1 differs, in context and line offsets. The `-Conditions` param lines are dropped, and the `+PotholeStyle` param lines and the `--potholes $PotholeStyle` statement are unchanged. No `-Conditions` forwarding is introduced.
  - The adaptation is correct for this base. The flag is forwarded only on the batch call (line 72); line 80 and the other callers are untouched.
- Default and legacy byte preservation holds by construction:
  - The `rng.uniform` draws for diameter and depth occur before the rule override.
  - `pothole_rim()` and `pothole_rims_clear()` are identical to the old behavior for depth>0.
  - The metadata key `pothole_style` is added only when `potholes=='rule'`.
  - Positional `generate(seed,difficulty,base)` is compatible.
  - The saved evidence matches: 12 triples (omitted, explicit bowl, base blob, T-0085 fixture) are equal.
- Rule semantics: 0.6096 m, white, depth 0, `solid_white_circle`, matching the profile and the checker (`pothole_*` pass for rule and fail for bowl). Body-clearance and MARGIN checks still treat them as obstacles, so the footprint and sweep checks are not weakened.
- `--potholes` is argparse-validated, so an unknown style exits 2 before the output directory is created (cli-smoke.json). PowerShell `ValidateSet` rejects 'painted'. The AST harness shows single arguments for paths with spaces.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓
Tests run: none (read-only). I read the diffs and compared the two diffs against each other via git, and read the harness scripts and the saved outputs (batch12.out: 4 OK and 15 OK; batch3.out; launcher-harness.txt). I did not re-execute anything.
Missing acceptance coverage:
- Unity load, render, sensor and ValidateEdit behavior for rule courses is not exercised (finding 1). The handback's claim level "tested (offline)" fits.
- Perception and autonomy behavior on white circles is not exercised. The perception hunks are intentionally excluded, so painted circles may be seen as lane paint.
- Rule-pair spacing versus Unity's 1.46 m rim minimum has not been audited across seeds.
- There is no committed test that pins default bytes. The launcher harness covers only the extracted batch statement, not the `-Instance` and non-batch paths.
- test_docker_reporting was not run against the changed `main()`.


### 2026-10-12T23:32:15-07:00 · gpt-6.1-sol → gpt-6-astra · REVIEW
Task: T-0088   Candidate: a089996eda4785cc55f59e1166688d7de798b537   Scope: evidence
Verdict: approve-with-nits

Findings (ranked, ≤ 5):
1. [minor] docs/agents/tasks/T-0088-igvc2027-integration-validation.md:126: Baseline outputs were frozen after edits, contrary to the dispatch’s required sequence.
   Mechanism: Disclose that the outputs were produced from the immutable base Git blob after editing, rather than claiming a pre-edit freeze. `batch3.sh` imports the separate `_base_37a6e89_gen` module, not the edited generator; its logged SHA-256 is `b7f13de24f067c2d25b4a0d0dbd74708b0989af62c162c3486beaa89e19732ad`.
   Evidence: Git confirms base generator blob `a168a5e…` equals `b517a99^`; candidate blob `ca8e28f…` equals `b517a99`. All four matrix files match the immutable T-0085 fixture. | UNVERIFIED: The exact `git show` materialization command and deleted temporary module are not preserved, so extraction provenance could not be independently replayed.

2. [minor] artifacts/agents/T-0088/prerequisite-r1/batch3.sh:5: Successful script exits are weaker than successful acceptance assertions.
   Mechanism: The shell prints statuses and continues after failures; its final `echo` can return success. `cli_smoke.py:23` compares normalized course objects, despite naming the result “bytes,” and does not assert expected exits or comparison booleans. This particular run’s reported results are satisfactory; the separate matrix supplies exact serialized course/mission/autonomy hash comparisons.
   Evidence: Saved logs show both comparison messages, fixture equality, CLI exits 0/0/0/2, expected white-circle fields, unchanged same-seed non-pothole obstacles, and no unknown-style output directory. | UNVERIFIED: Broader filesystem side effects and retained CLI output-file bytes.

3. [minor] docs/agents/tasks/T-0088-igvc2027-integration-validation.md:128: Required actual implementation usage is absent.
   Mechanism: The interactive owner and absence of a headless worker are recorded, but actual tokens/cost or an explicit unavailable-accounting statement are missing. Budget targets are not usage.
   Evidence: Reviewed the handback and supplied evidence inventory. | UNVERIFIED: Interactive implementation usage; this review’s actual usage must likewise be taken from the completed launch receipt.

Invariants checked: 1 ✓ 2 ✓ 3 ✓ 4 ✓ 5 ✓ 6 ✓. Base is exactly `37a6e892aa35cde9ec79b002415c5144630c80d7`, the candidate’s parent and step-1 receipt identity. Only the three authorized files differ. Policy, footprints, watchdogs, mounts and independent auditors are untouched. Claims remain scoped to offline testing.

Tests run: none (read-only). Independently ran `git diff --name-only 37a6e89 a089996`, `git diff --check 37a6e89 a089996` (exit 0), Git blob comparisons, `git hash-object`, `Get-FileHash`, and PowerShell JSON comparisons. Worktree is clean. Candidate SHA-256 values match the handback: generator `16b952bb…`, tests `56ed07e5…`, launcher `63964a58…`. Each matrix contains exactly seeds 2027–2030 × easy/normal/hard and 36 valid hashes; all four files have SHA-256 `f20dd7d7e0f50a458d18f456522e1764dc9f0321f7d01cf9fcee06bc5056d3a9`. Fixture Git blob identity also matches. Saved commands record 4 pothole tests and 15 course-variant tests passing, and base/omitted/bowl matrix executions exiting 0. Independent raw-blob hashing was blocked by constrained PowerShell language mode.

Missing acceptance coverage: The launcher harness selects a production CommandAst using text, then **executes** the actual extracted parameter block and generator statement with a recording stub; this is behavioral evaluation, not a string-match assertion. Saved outputs demonstrate bowl defaults, rule forwarding, unknown-style binding rejection and space-containing paths remaining single arguments. It does not exercise real WSL/native argument transport, `run_ros.sh`, batch control flow, instance/prepared-layout routing, copying, leases, process launch or the separate default-generation call. Exact harness launch commands/exits are not preserved.

Implemented: minimal generator and batch forwarding port. Tested: saved focused offline evidence supports this slice. Live-evidenced: none. Unity rendering, RGB/depth/lidar surfaces, perception and drivability remain UNVERIFIED, as do combined integration gates, hardware fidelity and 2027 compliance. This approval does not complete T-0088 or authorize promotion.
