---
id: T-0081
title: Retain observation-only rejection stages when forward planning returns no route
status: integrated
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0081-forward-rejection-opus
base: 2fed608
candidate: eb2140cec851fd0c0a4f556430a8e99f32a19a66
claim: tested
lease: released
updated: 2026-10-08
---

# T-0081: Bounded null-forward-plan evidence

## Packet

Named headless owner opus-t0081-forward-rejection-20261008. Isolated worktree
C:/Users/brand/.codex/worktrees/igvc-t0081-forward-rejection/IGVC SIM, base2fed608.
Only owned paths: tools/sensor_route_policy.py, tools/observed_navigation.py,
NEW tools/tests/test_forward_rejection_evidence.py. Do not edit any other file.
No primary edits, docs/agents edits, tests/imports/live/builds or providers. Source
edits and static ast.parse only; commit the three owned paths and hand back SHA.

T0080 accepted diagnosis found eight null forward-plan results with no retained
rejection stage. This task exposes future executed branch evidence only. It does
not explain the historical T0078 run or prove that a safe route does not exist.

Add optional bounded diagnostics to select_local_goal and its forward helper,
then propagate them in plan_observed_navigation/evaluate_observed_navigation's
existing diagnostics even on None. Do not change the existing plan-or-None return
contract, successful plan contents, option validation, search ordering, budgets,
clock reads, clearance/body/unknown/continuation gates, scorer behavior, or audit.
No replay, new route search, extra geometry pass, fallback, retry or guard change.

Use a fixed versioned small scalar record with truthful mutually distinguishable
executed stages: invalid options/input, start outside grid, initial circle/body
rejection, too-close progress target, and forward search finding no admissible
candidate. For the latter retain already available expansion count and budget/
time/queue exhaustion flags without new clock reads. Distinguish stage evidence
from causal proof. Successful and non-forward/not-evaluated paths must not retain
stale rejection state if a collector is reused. Never put arrays, maps, costmaps,
source geometry or exception messages in the bounded record. Avoid diagnostic
sink misuse changing navigation behavior; use only a supported plain dict sink
or safely ignore unsupported sink types. Preserve returned mutable-state ownership.

Behavior tests should exercise representative real early rejections, starting
body rejection, deterministic no-candidate search and successful planning. Compare
results with and without diagnostics, verify success clears reused rejection data,
verify wrapper retains a null stage and output is detached, and cover unsupported
sink and non-forward behavior. No wall-time performance claim or benchmark. Root
will choose focused existing geometry/planner regressions under all3locks after
handback. Existing broad passing suites and T0051 probe must not be repeated.

Exact authenticated Opus5.5,6min/USD5 default; no recursive delegation/provider
retries/model substitution. <=300word handback with paths, SHA, tests NOT run and
limitations. Exact Sonnet source review, root focused behavioral validation and
Sol evidence review required before root integration. No automatic live trial.
T0070 interactive slot and T0079 external finish-line ownership remain untouched.

## Log

### 2026-10-08T13:07:14.5817415-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

Assign only opus-t0081-forward-rejection-20261008 to source-only isolated worktree. Base2fed608c6fcab8e6809f604c23c28d2ad9d3235d; two owned preimages match primary, newtest absent. Nine tracked externalpreimages pinned and untouched. All3locks preceded Windows/WSL process/portchecks, no activeIGVC session; provisionlocks released. Existing attached worktrees contain unrelated completed work and were preserved. T0070 reserves otherworker slot. Actual model/exit/handback required; posting does not prove completion.


### 2026-10-08T13:12:16.0661671-07:00 · gpt-6-astra → claude-sonnet-5-5 · HANDBACK

Exact Opus completed269.86s/USD1.292776,is_errorfalse, committedcandidateeb2140cec851fd0c0a4f556430a8e99f32a19a66. Assignmentended. Onlythreeownedpaths reported. No tests or ast.parse ran (Python tool required approval); handback explicitly marks hand-calculated fixtures unverified. Root validatesactualcleanSHA/paths and runs focusedchecks underall3locks; Sonnet source review now. No primaryintegration/live/behaviorclaims yet.


### 2026-10-08T13:13:53.9407935-07:00 · gpt-6-astra → gpt-6.1-sol · REVIEW

Exact Sonnet sourcePASS55.77s/USD0.1681744 plus root21focusedchecksPASS/no skips oncandidateeb2140c. All3locks held beforeprocess/portchecks and throughouttests thenreleased. Threecandidatehashes/nineprotectedpreimages unchanged. Sonnet rawoverlongreview preserved; root review-summary.md scopes claims and fixed recording overhead (no zero-overheadclaim). Caller-owned plain dict sink iscleared and must notalias navigationinput; runtime usesprivate sink. Source review nonblockingpre-entryexception staleexternalcollector and one mirroredassertion retained. Opus USD1.292776,totalClaudeUSD1.4609504. No live/audit/replay or primaryintegration yet. Sol now checks actualbindings.


### 2026-10-08T13:15:18.3025767-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION

Candidateeb2140c accepted for bounded sourceintegration after exactSonnet PASS,21rootfocusedchecks and Sol e939a46c9ced291f29de550200d34c509ec0247d3666f9e0f7cad8ed2ea2b6cd. Solassignmentended. Root reacquiresall3locks beforeprocess/portchecks, verifiespreimages/index/cleanworker and completecommit range, thencherry-picks threeownedpaths and runssamefocusedchecks onprimary. No live/replay/audit/benchmark. Nineexternalpreimages mustremainidentical; recordfixeddiagnosticsoverhead and publicmutablecollector limitations, no navigationbenefitclaim.


### 2026-10-08T13:16:28.2133078-07:00 · gpt-6-astra → claude-opus-5-5 · INTEGRATION

T0081 COMPLETE source-integrated31ee59dbdaa9e9f7c1b5e29351a0f5fa6c7128b1 from
complete one-commit candidateeb2140cec851fd0c0a4f556430a8e99f32a19a66. Three owned
source hashes equal candidate;21focusedchecks PASS/no skips on both candidate and
primary; nine tracked external preimages unchanged. ExactSonnet sourcePASS and
Sol candidate acceptance followed by finalintegrationbinding accepted
4efc0ffdd24486a71156fffabdd03d33faa1df49d6f1bc1a12ec9d2c8722c0e5,
artifacts/agents/T-0081/sol-integration-review.md. Allworkersended, all3rootlocks
released13:15:25.824Oct8 after primaryvalidation. ClaudeactualUSD1.4609504;
nativeSolunknown. Worker no tests/ast.parse; root21checks provide actual evidence.
Rawoverlong handback/review and all outputs retained; no failed behavioral attempt.

Forward planning now retains fixed ten-scalar version1 executed-stage evidence
through observed-navigation diagnostics on null results, including alreadyexisting
expansion/exhaustion counters when search returns no admissible candidate. Return
values/search/gates unchanged by source review and focused checks. No newclock
reads/geometrypasses; dictionarywrites/copies still add unmeasured overhead. This
is not a claim of timing equivalence, physical cause, no-safe-route proof, historical
T0078 explanation or navigation benefit. No new live run, replay, benchmark or audit.
Plain-dict output is cleared/caller-owned and mustnotaliasnavigationinputs;
runtimeusesprivate sink. Separatecallercollector maystaystale if guidance raises
beforeplannerentry; onecounterassertionmirrorsformula. These limits are preserved.

No repeat implementation/tests/reviews/integration without newcause. Check actual
T0070/T0079 interactive response/ownership before choosing a next separate task;
no headlessduplicate, finishlineintegration or automatic live trial. Board and
observatory updated. No publishing/pushing.
