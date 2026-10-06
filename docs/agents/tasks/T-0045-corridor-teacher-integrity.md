---
id: T-0045
title: Make offline corridor labels honest about reachability and label versions
status: in-progress
priority: P2
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0045-corridor-teacher-integrity
base: 95b0baf61052651765f7924e21bd52c8e7d59777
candidate: none
claim: none
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
