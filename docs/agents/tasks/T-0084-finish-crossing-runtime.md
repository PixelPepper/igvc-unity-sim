---
id: T-0084
title: Complete sensor-led missions on finish-line crossing
status: blocked
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0084-finish-runtime-opus
base: 7a18f52f4111ba5eaf7ef1ddff910dc0a0c6f4c4
candidate: none
claim: none
lease: none
updated: 2026-10-10
---

# T-0084: Runtime finish crossing

## Packet

Dependency: accepted T0082 helper and separate T0083 auditor; rebase/freeze before
dispatch. User explicitly requests crossing the line without specific point.
Named owner opus-t0084-finish-runtime-20261010. Isolated worktree
C:/Users/brand/.codex/worktrees/igvc-t0084-finish-runtime/IGVC SIM.
Owned paths ONLY tools/sensor_course.py, tools/mission_completion.py,
NEW tools/finish_mission.py, NEW tools/tests/test_finish_crossing_runtime.py,
tools/tests/test_mission_completion.py. No auditor/Unity/exporter edits.

Read docs/FINISH_CROSSING.md and helper first. Implement runtime adoption of
finish-crossing/1 on the six-destination sensor-led fixture. First5 radius arrival
and all health/freshness/body/costmap/paint/recovery gates unchanged. Destination6
must only complete on actual eligible armed forward crossing. A point-radius
arrival at origin or a plan-through target must NEVER mark mission complete.
Use existing sanitized broadGPS and odom only; no WORLD/course/teacher inputs.

The planner hint for final stage is origin +2.5m ROS+X, beyond line, and is passed
through existing checked planner/recovery interfaces without weakening any
guard. Completion stops on crossing, before reaching this hint; no midpoint
arrival requirement. Apply final-stage hint consistently to planning and recovery
without rewriting the recorded broadGPS destinations. No new recovery or fallback.

Pure finish_mission helper provides meaningful testable stage/hint/crossing logic
and is used by actual runtime (not a duplicate test-only implementation). Feed
tracker actual received odom samples with real sensor stamps, ideally from odom
callback that already appends trajectory. Do not feed same latest sample on each
mission loop, which would spuriously break continuity; do not silently hide a
real nonincreasing sensor stamp. Runtime eligibility first5 completed; independent
auditor reconstructs visits separately. Allow crossing evidence to latch, then
main loop still checks existing live guards before completing.

Report versioned finish_crossing policy/provenance even on failure. Final
completion ledger must name finish_line_crossing as decision_basis with finite
segment indices/stamps/intersection and no false final radius-arrival claim.
Earlier arrivals retain truthful radius basis; final distance informational.
Keep bounded retained diagnostic data and graceful existing cleanup.

Tests exercise real pure mission helper: afterfirst5 crossing2moffset succeeds,
originradius/targetarrival/no crossing fails, uniqueodom sampling (no polling
duplicates), reverse/early/too-fast crossing fails, final hint lies beyondline,
first5 unchanged, completion recorder final basis versus radius descriptive.
Preserve focused legacy completion tests, changing expectations only where new
explicit basis needed. No worker tests/imports/ROS/live/build/providers/delegation;
root executes focused behavior checks underall3locks. No live success claim.

Commit only owned5paths; <=300word SHA/file/unrun-test/risk handback.
Exact Opus5.5 high USD5/360s. No automatic provider retry or substitution.

## Log

### 2026-10-10 · gpt-6-astra → claude-opus-5-5 · NOTE
Dependent runtime packet prepared, not dispatched. New isolated ownership;
T0070 reservation and T0079 external candidate untouched.


### 2026-10-10T22:59:13.2328569-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
T0083finalintegrationbindingaccepted; frozenbase7a18f52 includes allsourceandexternalcheckpoint. Namedisolatedownerassignedruntimeonly5paths, no auditorchange. Userapprovedcontinuationofrequestedfinishlinechange. T0070reserved/T0079externaluntouched; no live/build/testsbyworker. Root ownslockedvalidation/integration.


### 2026-10-10T23:05:48.1618438-07:00 · gpt-6-astra → team · BLOCKED
RuntimeOpusrequestedimplementationreached360s localtimeoutwithempty stdout/stderr,no handback/commit/providerexit/modelUsage/costconfirmation; usageunknown. Assignmentended/noautomaticretry. Fiveuncommittedownedpaths frozenunderartifacts/agents/T-0084/timeout-source; HEAD7a18f52. Rootboundedpartialpreflight36PASS/no skips underall3locks,11protectedunchanged/alllocksreleased. Thisispartialpure/syntheticchecksonly,noacceptedcandidate/source/evidencereview/ROSloop/live orintegration. Primaryruntimeunchanged; T0083auditorintegrated7faacd4. Usermustapproveboundedfollow-upbeforerelaunch. T0070reserved.

