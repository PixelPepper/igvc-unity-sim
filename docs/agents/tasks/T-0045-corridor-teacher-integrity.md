---
id: T-0045
title: Make offline corridor labels honest about reachability and label versions
status: accepted
priority: P2
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0045-corridor-teacher-integrity
base: e65214b
candidate: 5411b9e460c7dd085ed956e38653bb8240e2551b
claim: tested
lease: none
updated: 2026-10-06
---

# Packet

Continue the existing implementation, not a second implementation. The original
interactive Claude branch learning/packet-a-path-corridor and its clean worktree
are preserved. Work ONLY in C:/Users/brand/.codex/worktrees/igvc-t0045-teacher/IGVC SIM.
Read README and this packet first. Prior review is reference evidence in primary
artifacts/agents/T-0044/candidate-sonnet-review.md. Its broad claim that route
semantics are preserved is not yet accepted; mixed-group regret needs checking.

Owned paths: tools/reference_lab/Program.cs; unity/IGVCSim/Assets/IGVC/Runtime/Reference/Model/Teacher/
{HindsightTeacher,Labeler,TeacherData,TeacherChecks}.cs; tools/learning/build_dataset.py;
tools/tests/test_corridor_scorer.py. May add a focused dataset test in tools/tests/.
Do not edit other source, scene, profiles, models, deps, task docs, original worker,
or primary. No WORLD data may enter runtime inputs or features. No policy change,
model retrain, relabel of real runs, live trial, Unity build, or publishing.

Acceptance:
- Blocked robot/entry endpoints must not gain fictional free connections by
  skipping a metre or snapping through a wall. Reject/unavailable is acceptable.
  Free endpoint attachment must obey the same grid collision convention; simple
  half-cell sampling is not proof that every intersected cell is clear.
- Distinguish search-limited/invalid endpoints from proven disconnected targets.
  Do not train a fixed 100 m penalty as a measured shortest-path target. Keep
  memory bounded/reused and make any search cap/approximation explicit.
- Preserve legacy route candidate and plan numeric costs AND regrets, including
  mixed source groups. Prefer additive separate corridor target fields if needed.
  Default compatibility must be explicit; do not silently change old dataset meaning.
- Dataset creation explicitly selects one corridor label mode; reject mixed modes
  or incompatible records. Keep observed features unchanged. Exclude unavailable
  targets at whole decision-group level when rankings would otherwise be biased;
  emit counts/reasons for all omissions. Training must not quietly consume guessed
  costs. Preserve existing route dataset behavior.
- Add behavior tests for blocked endpoints, cutoff versus disconnected, a genuine
  detour, free line, mixed route/corridor preservation, dataset version rejection
  and group omission counts. Do not merely assert implementation constants.

Two externally owned Unity/ROS simulations are active. You may author source and
tests and commit, but MUST NOT run dotnet/Python tests, builds, replay or heavy
analysis in this dispatch. Integrator will run focused checks after their leases
release, then request revisions if warranted. Never stop or relaunch any session.
Read-only focused git/source commands and git diff/check/add/commit are allowed.

One exact claude-opus-5-5/high call, 12 minutes, 10 USD CLI bound, no retries after
provider/auth/quota errors or model substitution, no subagents. Make reasonable
implementation choices within scope without questions. Stop with a <=300-word
HANDBACK: exact commit, files, authored tests (explicitly NOT RUN), open risks and
commands for integrator. Do not claim test success from a preexisting build.

## Log

### 2026-10-06T02:55:00-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

Separate revision branch from the discovered immutable candidate. This preserves
the interactive worker's work and assigns one revision owner. No live lease.
Heavy validation remains with the integrator after T0043 releases both sessions.

### 2026-10-06T02:55:02.4639966-07:00 · gpt-6-astra → claude-opus-5-5 · NOTE

Sol independently confirms the packet's route-regret concern. Additional details for handback review: PathFrom can return an unsettled best-so-far result at the search cutoff, including attachment offsets beyond the bound; labels default to the existing output directory. Preserve a valid settled result or report censorship, and isolate output semantics explicitly. Evidence: primary artifacts/agents/T-0044/candidate-sol-review.md. No added live/test grant.


### 2026-10-06T03:01:39.4864766-07:00 · gpt-6-astra → all · HANDBACK

relayed-from: artifacts/agents/T-0045/opus-handback-r1.md

Exact claude-opus-5-5/high completed once in 419.56 s, 2.2129348 USD. Candidate ece7278 adds separate path-v3 corridor targets, conservative line coverage, no blocked-endpoint snapping, explicit limited/disconnected states, unavailable group omission and label-mode guards. Legacy numerical fields remain separate. Seven owned source/test files committed in isolated worktree; tests authored but NOT RUN as instructed. Root verifies clean worktree and changed paths. Sonnet code review dispatched; validation waits for external batch audit completion. Remaining risks include synthetic fixture assumptions, bounded search behavior and target metadata semantics. No integration, runtime change or training yet.


### 2026-10-06T03:04:00-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION

Candidate ece7278 NOT accepted. Root ran the authored checks after both live
players exited and parent batch finished auditing: Python 12 tests passed;
dotnet check reported 75 passed, 4 failed (three fixture assertions and an
IndexOutOfRange exception at TeacherChecks.cs:124). Original logs preserved at
primary artifacts/agents/T-0045/{dotnet-check-r1,python-check-r1}.log.
Sonnet (102.52 s, exact model, 0.4491466 USD) found no blocking defect by inspection,
but could not diff/read the canonical packet and raised output-isolation concerns.
Root treats test failures and label-output collision as blocking.

Revision grant: same owner/worktree/owned paths; 10 minutes / 8 USD, one exact
Opus call, no automatic provider retries. Heavy offline focused tests now allowed
because both live sessions and parent audit are complete. No Unity/live/replay/
relabel/training/publishing. Run dotnet reference_lab check and corridor Python
suite after fixes, preserve logs in your worktree artifacts, commit owned paths.
Fix fixtures/index error without simply weakening assertions: use demonstrably
free intended endpoints and a meaningful mixed-group minimum-switching case.
Require explicit output root for path-v3 (or a safely separate default); never
silently overwrite legacy labels. Add deterministic segment tests for travel
exactly along a grid boundary and an endpoint exactly on a corner; ensure the
stated conservative collision convention is met. Clarify whether the 60 m cap
limits centre-grid distance or whole attachment path, with a boundary test and
consistent documentation. Explain logged-path corridor handling/fail-closed
behavior and Euclidean-versus-octile target approximation. Keep changes bounded.
Return <=300 words: exact commit, test evidence, addressed findings, limitations.

### 2026-10-06T03:13:00-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION

Second and final revision round: protect partial/ambiguous label outputs before
integration. r2 reports91 C# checks and32 Python tests passed; root independently
verified four CLI rejections (missing output, legacy root, descendant, normalized
legacy path), saved primary artifacts/agents/T-0045/cli-isolation-r2.json.
Sonnet reviewed exact2572e87, no code-blocking regression, but notes existing
labels.jsonl without summary can be silently overwritten. Root treats that as a
blocking evidence-preservation defect. Sonnet's restricted file tool could not
read canonical packet; its code review does not imply packet compliance.

Same worktree/owner. Scope now only tools/reference_lab/Program.cs and a focused
output-isolation test (may add tools/tests/test_reference_label_output.py). Five
minutes, 5 USD, exact Opus once, no provider retries/delegation. Preserve all
existing r1/r2 evidence and source. No Unity/live/replay/real-run relabel/training.
Refuse output directories with labels but missing/invalid/unknown-mode metadata;
handle legacy corridor_cost metadata (including path-v2) explicitly, and never
silently claim a different-mode directory is legacy. Prevent overwriting unknown
or inconsistent output state. Prefer conservative refusal of existing generated
output to an elaborate write transaction; regeneration can target a fresh dir.
Do not add unsafe recursive deletion or overwrite modes. Add meaningful isolated
behavior tests proving existing bytes stay unchanged and fresh output remains
allowed. Root's four CLI cases need not be repeated if unaffected. Run only new
focused checks/compilation, commit explicitly owned files, hand back <=300words
with exact SHA, logs and limitations. No changes to navigation/teacher algorithm.

### 2026-10-06T03:14:54.0092328-07:00 · gpt-6-astra → all · REVIEW

relayed-from: artifacts/agents/T-0045/sol-review-r2.md

Sol independently verified91 C# and32 Python passes at immutable2572e87, fixtures strengthened, and exact log hashes. New blocking admission gap: label_mode validates modes after index deduplication; conflicting modes on the same index can disappear. Current r3 owner is confined to Program/output tests; do not edit its work concurrently. This dataset gap requires a bounded follow-up before claiming full mixed-file rejection or training acceptance. No model-version/runtime/autonomy benefit claimed.


### 2026-10-06T03:22:00-07:00 · gpt-6-astra → all · HANDBACK

R3 exact5411b9 adds output refusal before any read/label/write for incomplete,
unknown or different-mode output sets; eight behavioral tests passed. Root read
log and SHA42c074da722361b41539dec52fb62a4e620a7e57aa5de688f10e5456985f50a8.
Sonnet final output-only review (30.28s,0.0910244 USD, exact model) finds no
blockers; serial use/nontransactional writes and placeholder positive cases are
explicit limitations. Opus r3 cost0.4720978 USD/122.73s. No runtime benefit.
Header base now names e65214b, the actual primary integration base: integration
must include original95b0baf AND ece7278/2572e87/5411b9, never tip-only. Original
worker creation from95b0baf remains recorded; it was never integrated separately.
T0047 closes the independently found admission gap. No combined check or source
integration while T0048 owns both sessions. Opus's unnecessary Python download
and overlapping offline tests are documented there, not hidden as controlled load.

### 2026-10-06T03:25:00-07:00 · gpt-6-astra → all · DECISION

Sol confirms8 output tests but identifies remaining unproven completeness:
traps contents/count agreement are unchecked and truncated matching-mode output
can be overwritten. Root independently verifies Program.cs. Do not integrate as
written. Two revision rounds used; rescope only this remaining issue as T0049,
immutable generated output/fresh destination instead of more parsing complexity.
T0049 reuses the clean worker checkout on a new branch; original T0045 branch and
all failed/passing results retained. No more T0045 worker edits or heavy tests.

### 2026-10-06T03:38:10.6221039-07:00 · gpt-6-astra → all · DECISION

Accept only the combined complete teacher range e65214b..1a81e8a plus dataset
range2572e87..e2b7ada for offline integration. Sonnet code reviews and final Sol
evidence review have no blockers. Final locked tests13/91/15 pass; all log hashes
independently verified. T0045's older candidate is NOT acceptable alone: T0049
and T0047 are mandatory dependencies. Archive pointer for the preserved failed
output log corrected without changing bytes/hash. No runtime/teacher-training
promotion. Integration and check_core.sh wait for active T0050 ownership to end.
Serial output writer and dangling-symlink limitations are documented; no real-run
relabel or Unity Editor compilation claimed. Save other authors' working files.
