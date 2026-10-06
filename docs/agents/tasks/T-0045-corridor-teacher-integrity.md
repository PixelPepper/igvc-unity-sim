---
id: T-0045
title: Make offline corridor labels honest about reachability and label versions
status: changes-requested
priority: P2
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0045-corridor-teacher-integrity
base: 95b0baf61052651765f7924e21bd52c8e7d59777
candidate: ece7278f95b92434a01e9fdb4cfbf7f3e4a964f2
claim: implemented
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
