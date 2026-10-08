---
id: T-0074
title: Verify actual perception clock configuration before sandbox mission start
status: integrated
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0074-clock-admission-opus
base: ccc92fbe845733b761374dfa3ba9cb460099e1c5
candidate: 2bde9882fa8ca53e05dda819023df4323520cfb2
claim: tested
lease: released
updated: 2026-10-07
---

# T-0074: Actual clock configuration admission

## Packet

Sole implementation session: opus-t0074-clock-admission-20261007, authenticated
exact claude-opus-5-5 high, six-minute/requested USD5 bound. No recursive delegation,
providers, tests, imports, live sessions or builds. Source edits and git only.
Worktree C:/Users/brand/.codex/worktrees/igvc-t0074-clock-admission/IGVC SIM.
Own only tools/sandbox_session.py and NEW tools/tests/test_sandbox_clock_admission.py.
Existing owned source is clean at base; external dirty profile/launcher/Unity files
are NOT included or owned. Their behavior is not being replaced. Root tests candidate
then primary compatibility before any integration. Do not copy another branch.

T0073 explicitly sets use_sim_time=true for lane/depth in both ROS simulator launchers.
It is integrated and deployed, with actual parameter services verified on domain89.
However the normal supervisor currently starts navigation then immediately spawns the
mission. The overlay freshness checker omits launch files. A stale/differently configured
launch can therefore evade the expected clock configuration. Add a bounded fail-closed
pre-mission parameter check and record its result, without changing any motion policy.

- Add a RosControl operation querying /igvc_lane_detector and /igvc_depth_processor
  use_sim_time through actual ROS parameter services. Require exactly one Boolean true
  response per node; false, absent, malformed/wrong type, timeout, exception must fail
  closed with a useful error. Use Jazzy AsyncParameterClient public API
  wait_for_services (plural), or equivalent actual service clients. Bound discovery
  and response using a monotonic overall deadline (at most16 seconds total).
- Integrate after owned nav start and BEFORE mission Popen. Simulator autonomy remains
  disabled. Persist structured success/failure clock-configuration evidence into the
  existing run folder/provenance, including both requested node names and observed
  status/value/type where available. No successful evidence fabricated on exceptions.
- Failed admission must enter existing cleanup and error state, never spawn a mission,
  enable autonomy, or leave owned navigation active without failed-cleanup indication.
  Beware process_command's ValueError/OSError handling bypassing the generic cleanup
  branch: ensure failures after nav start use the cleanup path.
- Do not weaken or replace sensor freshness/processing health, /clock progress, body,
  unknown-space, recovery or audit guards. Parameter true is only configuration
  admission, NOT proof of /clock delivery, sensor health or a safe/audited mission.
- Add focused behavior tests: success persists evidence before mission spawn; each
  failure category prevents spawn and confirms navigation cleanup/error handling;
  unavailable response is bounded; preserve original reason when cleanup also fails.
  Use dependency fakes without installed ROS for unit coverage, but cover real response
  shape and strict Boolean type rather than testing source strings. No source imports
  or test execution by this worker; root owns validation under all3locks.
- No launcher, profile, runtime policy, node-class or Unity edits. Commit exactly owned
  paths and return SHA, changed files, unrun tests and unresolved risks in <=300 words.

This new admission task is disjoint from T0070 interactive reservation, and is not a
retry of T0072's provider timeout. No mission or promotion is authorized by this packet.

## Log

### 2026-10-07T19:16:29.9819339-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

Assign source-only implementation to opus-t0074-clock-admission-20261007 in its isolated worktree. T0070 interactive slot stays reserved. All3 primary locks were obtainable at19:15, no Windows players/ports, two unrelated Unity processes; locks released and WSL not checked, so no live/test grant. Root will validate under a new lease only after committed handback.


### 2026-10-07T19:21:20.4661541-07:00 · gpt-6-astra → claude-opus-5-5 · CHANGES-REQUESTED

First handback2b0bc34b8c449a186d921bcc3ff6b8811b993ef5, implementation196.28s/USD0.8104576 exact Opus. Assignment ended. Root32 focused tests PASS/no skips under all3locks (validation/tests.log SHA25626d65c964f810531bd50586ed63fd9a16eabc02d91e6ed5cacbbb0148fe842e4),9 protected preimages unchanged. Sonnet static PASS46.69s/USD0.1633734, but root blocks acceptance on new installed-API evidence: Jazzy AsyncParameterClient has no destroy method and creates6 underlying node clients. Swallowing that AttributeError leaks12 clients per sandbox start on the long-lived supervisor; small per-start is not a bound over repeated runs. No integration or live claim. Sol acceptance waits for corrected candidate.

Assign revision r1 ONLY to opus-t0074-clock-admission-20261007-r1 in same worktree/owned2files, previous assignment explicitly ended. Replace the unsupported cleanup with public-API lifecycle management (e.g. a direct GetParameters service client per node, destroyed via Node.destroy_client) without poking private AsyncParameterClient fields or destroying the shared supervisor node. Preserve strict responses, deadline, evidence and cleanup invariants. Add repeated verification and failure-path lifecycle tests proving client count does not grow. Also check deadline after response completion before admitting a late successful response; test fake-clock overrun. Source/commit only, no imports/tests/providers/live. Six-minute/USD5 bound. Stop at committed handback; do not overwrite prior artifacts.


### 2026-10-07T19:24:35.9190523-07:00 · gpt-6-astra → claude-sonnet-5-5 · HANDBACK

Revision2bde9882fa8ca53e05dda819023df4323520cfb2 returned exact Opus139.36s/USD0.672526; r1 assignment ended. Direct GetParameters clients use public Node.destroy_client and late completed responses reject. Root40 focused tests PASS/no skips under all3locks, log5f59941e42989d86a74262866f9c2e813a2d6cc9ee73d5987d50e2881d980eaa. Added root real Jazzy synthetic parameter-node probe passes twice true then depth=false rejects; supervisor client count remains3 after each, no mission/Unity/sensor input. See validation-r1/actual-probe.json. Nine tracked external preimages unchanged. Sonnet whole-range revision review underway; Sol evidence review next. No source integration yet; original32PASS/client-leak candidate remains preserved.


### 2026-10-07T19:25:29.3587826-07:00 · gpt-6-astra → gpt-6.1-sol · REVIEW

Sonnet r1 whole-range source PASS49.05s/USD0.1872316. Native Sol now checking40-test and actual synthetic ROS evidence before integration. Total reported Claude usageUSD1.8335886; nativeSol unavailable. Both implementation assignments and both Sonnet reviews ended. Nonblocking existing post-spawn status-write OSError path noted; still supervised, outside admission path. Parameter check does not disambiguate duplicate node names or establish clock delivery. No source integration or live mission yet.


### 2026-10-07T19:26:36.2585646-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION

Accept revised candidate2bde988 as tested configuration admission only: exact Sonnet source PASS and Sol evidence accepted40 tests plus synthetic real-Jazzy parameter services/client lifecycle. Header now identifies r1; initial32PASS evidence remains source-insufficient. Root will integrate complete2-commit range fromccc92fb under all3locks and verify current-primary profile/supervisor compatibility and source hashes. No mission, sensor-health or audit claim.


### 2026-10-07T19:27:11.2973101-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION

Integrated complete2-commit range at78da1c0ffb236bef4d883401c57d27d10806fe66. Two source hashes match accepted2bde988. Current primary41 focused tests PASS/no skips (candidate40; primary external profile adds one check), log59e3dc3f41f3d0304f73b834a549c0c67d51f097e70debe8652569b8496b49e7. Nine protected external preimages unchanged. All3locks held through preflight/integration/tests then released. No repeat of the successful candidate real-ROS probe. Final Sol integration binding requested. This gate checks clock configuration before spawning a sandbox mission; no Unity run or course result yet. T0070 ownership and unintegrated latency chain remain unchanged.


### 2026-10-07T19:27:38.9376724-07:00 · gpt-6-astra → claude-opus-5-5 · REVIEW

Final native Sol integration binding accepted (sol-integration-review.md SHA25675a17e529273b943c962ba28cf13ffa5bb9515ba10f6a66eed176224ff805751): complete2commits/sourcehashes,41PASS/no skips, all3lock evidence and9 unchanged protected preimages. All T0074 workers finished. Total ClaudeUSD1.8335886, Solusage unavailable. Do not repeat completed tests/probe/integration. Next bounded live trial needs its own frozen source/settings/player packet and full audit; new provenance.clock_configuration records actual parameter admission before mission spawn. Existing status-write and duplicate-node limits remain in source review; no course improvement claimed.

