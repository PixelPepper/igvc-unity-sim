---
id: T-0038
title: Observe one diagnostic 2029 lap with reviewed Unity timing capture
status: in-progress
priority: P1
owner: gpt-6-astra
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0038-timed-2029-diagnosis
base: 20a18f3
candidate: 20a18f3e7df4da4fa6dce4e5c8e5d16323b4c5ef
claim: none
lease: requested
updated: 2026-10-05
---

# T-0038: A diagnostic repeat, not a replacement held-out result

## Packet

- Read T0035 failed first2029, accepted T0036 diagnosis and T0037 capture review.
  Original stopped2/6, health failure and12/20 audit remain in the ledger. The
  failure blocked promotion. This repeat is explicitly for missing timing evidence;
  even a pass must not erase the failed first attempt or establish a causal fix.
- Start ONLY after T0037 primary build and stopped player off/on smoke pass and
  cleanup is verified. Preserve old d6519e1 branch/player, use a new clean frozen
  branch in the existing trial checkout with primary20a18f3 source. No dirty or
  concurrently rebuilt source; dedicated t0024-control ROS overlay. Only one lease.
- Exactly one managed hidden rendered Unity + WSL ROS/Jazzy/Nav2 diagnostic lap,
  seed2029 and same profile/course/mission/autonomy bytes as T0035, .6m/s requested
  ceiling, .5s planning budget, body clearance weight3, checked-path/RPP, fallback
  off, scorers off, six sanitized broad GPS destinations. Compare all19 policy
  source hashes. Unity changes are optional timing component and env-only hook,
  with fresh built-player hash recorded. No policy/map/sensor/watchdog changes.
- Opt-in IGVC_TRANSPORT_TIMING_TRACE=1 inherited by this single supervised player.
  Save explicit environment choice in job/launcher provenance; restore coordinator
  environment immediately after launch. Require schema2 header in the captured
  Unity log. Ordinary launches remain trace-off. No unrecorded parameter change.
- Job artifacts/iterations/2026-10-05/timed-2029-diagnostic-1. Never reuse a launched
  job. Explicit LEASE-GRANT required below; header alone is not authority. Mission
  limit600s, usual managed build/start/audit bounds and verified cleanup. No heavy
  local tests/replay/builds during mission. No retries or2030 generation.
- Preserve every result including failed audit/health, all original logs and
  first-failure snapshot. Run unmodified independent full-course audit and append
  benchmark ledger regardless of outcome. Timing parsing is offline after cleanup,
  source-data only; report frame gaps versus subscriber ages without fabricating
  cross-host clock synchronization. UTC bracket bounds the local read placement,
  not clock accuracy. Queue warning counts are asynchronous observed log lines,
  not drops/wire timing/backlog. Terminal mono_s is last sampled frame: don't
  discard the unsampled tail. Actual header/final clock coverage controls claims.
- A completed run without reproducing freshness expiry is a non-reproduction,
  not proof that instrumentation fixed anything. A frame gap is not its cause:
  focus/GC/OS/rendering/host scheduling remain alternatives. No measured overhead
  comparison yet. Document any startup/render error as such. No promotion/push.
- Both reviewers inspect complete evidence, source/player/profile/input bindings,
  health and cleanup. Return completion/audit/health plus timing availability and
  remaining uncertainty separately. Choose next repair only from supported evidence.

## Log

Await T0037 build/smoke evidence and explicit grant. No live trial authorized yet.

### 2026-10-05T08:05:53.5627466-07:00 · gpt-6-astra → all · LEASE-GRANT

Grant exactly one diagnostic2029 mission in job timed-2029-diagnostic-1 after completedT0037review/build/smoke. Frozen runtime20a18f3,19policyhashes and4inputfiles verified identicalT0035. NewplayerCF8F4A64... and traceenv1 explicitly recorded. Old d6519e1branch and completeoldplayer preserved at runtime artifacts/build-course-d6519e1. Runtimeclean; no process/listener atpreflight, managedwrapperholdslease throughverifiedshutdown. This is diagnostic non-replacement trial, no secondattempt/2030 authorized. Primarysource20a18f3 includescapture/helperonly; runner source unchanged.
