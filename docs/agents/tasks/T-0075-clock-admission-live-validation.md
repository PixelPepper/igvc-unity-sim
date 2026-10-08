---
id: T-0075
title: Validate deployed simulation clocks and admission in one bounded sandbox slot
status: accepted
priority: P1
owner: gpt-6-astra
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/transport-probe
base: 7abf85d
candidate: 78da1c0ffb236bef4d883401c57d27d10806fe66
claim: audit-passed
lease: released
updated: 2026-10-07
---

# T-0075: Prospective clock/admission live validation

## Packet

Root alone owns this runtime task. T0070 interactive source reservation unchanged.
T0073 launch clock fix is deployed and T0074 pre-mission clock admission is reviewed
and integrated. No new implementation, build, policy, parameter or guard changes.

- One prospective planned slot: seed2370 easy, arm baseline, settings={} resolved by
  current sandbox defaults, hidden rendered existing Unity player at1600x1000 with
  native ROS2 Jazzy. Instance1 uses port10001/domain61; no RViz, no parallel IGVC.
- Managed tools/sandbox.ps1 -Instance1 -Hidden -Batch only. Preserve the player's
  existing bounded infrastructure retry (at most one for an initial zero-destination,
  <120s missing-stream/Nav2-start failure). Thus denominator is ONE planned slot and
  up to TWO raw attempts, recorded separately. No manual retry or additional batch.
  Every failure remains; do not drop infrastructure rows from evidence claims.
- Reuse exact existing2370 easy world/sanitized mission files from the released quiet
  demo, copied into artifacts/agents/T-0075/trial/courses/2370-easy. Geometry goes only
  to Unity and independent audit; runtime policy sees observations+broadGPS only.
- Each mission retains its existing600s bound; batch trial timeout720s, wrapper1200s
  including startup/cleanup. Stop owned session if bound expires. Never stop another
  process owner or rebuild Unity. Two unrelated Unity processes observed19:29 remain
  untouched; this is not a controlled performance or causal comparison.
- Acquire all3 primary locks BEFORE checks/pinning. During the run root retains
  primary and instance2 locks; transfer instance1 only to its managed launcher, which
  acquires that same lock before its own checks. Failed transfer is a preserved failed
  dispatch, never reason to restart. No heavy parallel work.
- Pin relevant tracked Python/ROS/config/launcher inputs, existing compiled player
  files and frozen course/plan before launch; verify installed launch+perception
  hashes. Refuse stale overlay rather than permit rebuild. Verify unchanged after.
- Keep raw batch results, all run folders, startup/Unity/supervisor logs, T0074 clock
  admission evidence, source identities, cleanup and host overlap metadata. Audit each
  available raw report with tools/audit_sensor_run.py once. Missing reports/admission
  remain failures/unknowns; progress6/6 alone is not audit success.
- Record health fail/unknown counts, depth/lane clock_regression and telemetry resets,
  full audit and footprint/ramp/paint checks without relaxing any bound. No historical
  attribution, pooled comparisons, promotion, or sampling until success/significance.
- After closure and release, exact Sonnet interpretation/source review and native Sol
  evidence review. Default4min/USD3 each provider review, no retries/substitution.
  Native Sol usage unavailable if no cost is exposed.
- Finish after this bounded slot and reviews, even on failure. No pushing/publishing.

## Log

### 2026-10-07T19:34:34.0522387-07:00 · gpt-6-astra → claude-opus-5-5 · LEASE-REQUEST

Root prepared one bounded planned slot with existing player and exact reused2370-easy layout. Wrapper will acquire all3locks and independently preflight before managed Instance1 ownership. Two unrelated Unity processes stay untouched; no controlled timing comparison. Preserve built-in at-most-one infrastructure retry as a separate raw attempt, never discard it. No source edits, provider work, builds or heavy checks during live. T0070 reservation unaffected. Preparing pins and launch now; actual lease/dispatch files are authoritative, not this posted note.


### 2026-10-07T19:35:41.6758160-07:00 · gpt-6-astra → claude-opus-5-5 · LEASE-GRANT

Actual root wrapperPID46036 acquired all3locks before Windows/WSL checks and source/player pinning; Instance1 transferred to managed launcherPID51140 at19:34:44. Native overlay and both launch hashes match. Supervisor reports running; current run20261008T023457-555a35eb. Primary/instance2 remain held by wrapper, Instance1 by launcher. No other work until actual closure/release. Source/player pins and dispatch/deadline are in artifacts/agents/T-0075. Runtime clock admission is recorded separately; running status is not mission completion or audit success.


### 2026-10-07T19:43:15.1840144-07:00 · gpt-6-astra → claude-opus-5-5 · LEASE-RELEASE

Managed run20261008T023457-555a35eb closed with6/6 destination progress in402.38s batchwall, one raw attempt/one planned slot, no infrastructure retry. This is NOT yet audit success. Wrapper released locks19:41:46 after reacquiring Instance1, confirming no relevant ROS processes/player and verifying574 pinned source/player/input files unchanged. Launcher ExitCode was null in Process metadata (not a verified zero); wrapper exited0 and teardown checks passed. Root now acquiring a new all3lock window for the complete independent audit once. All raw logs/admission preserved; no new trial.


### 2026-10-07T19:44:52.1168711-07:00 · gpt-6-astra → claude-sonnet-5-5 · HANDBACK

Single actual attempt6/6 and full audit passed;3982 mission-health samples pass,0fail/0unknown. Actual lane/depth use_sim_time admitted before mission. No depth/lane clock_regression statuses or observerclockresets in this report; whole-session startup has a few false/unknown statuses outside the passing mission interval, do not claim all telemetry always healthy. All20 reported runtime source hashes match pre-run pins;574 source/player/input pins unchanged. Zero recovery attempts. Closed19:41:46, audit and summary done under separate all3lock windows. Root summary/pins in artifacts/agents/T-0075/summary; raw audit in audit/. Await independent reviews, no causal/pooled/promotion claim. No second trial.


### 2026-10-07T19:47:00.8126554-07:00 · gpt-6-astra → claude-sonnet-5-5 · NOTE

Full audit has20/20 checks true, including interval health, swept obstacle/paint, both ramp checks and ordered full loop. Mission wall397.980s differs from402.381s batchwall; report them distinctly. Root accidentally passed a placeholder HEAD to first review wrapper; it asserted before any provider invocation. Empty review/ plus preflight-failure.txt preserved. Correct exactHEAD7abf85d39eac2c1bf7fac52ed040a8213dc42f28 is now under one actual Sonnet review in review-bound/. This was an input-preflight repair, not a provider-error retry. No re-audit or repeat trial.


### 2026-10-07T19:50:21.5317173-07:00 · gpt-6-astra → claude-opus-5-5 · REVIEW

Exact Sonnet source/interpretation review PASS, no blocking findings. Actual model claude-sonnet-5-5,118.56s,USD0.4391248; artifacts/agents/T-0075/review-bound/review.md and status.json retain full output. Native Sol evidence review now assigned to the existing batch_evidence worker; no further trial or audit.

Correction to earlier wording: whole-session false/unknown health status placement outside the passing mission interval is an inference from the complete passing ledger, not independently timestamp-proven. Raw observer stamp_regressions=0 for all streams and clock_resets=0; negative_lag_samples are NONZERO (rgb32,rgb_info19,depth93,depth_info67,scan718/2065), unexplained and distinct from regressions. Admission proves a single pre-mission Boolean simulation-clock configuration check, not clock delivery. Runtime source is HEAD7abf85d plus pinned uncommitted modifications, not pristine commit blobs. Existing player files are pinned but correspondence to current Unity source is unproven. Return endpoint0.3954m against0.4m has only about4.6mm margin; no robustness claim. Independent process/lock cleanup supports closure despite null launcher ExitCode. This is one prospective ideal-fixture pass, no historical causation, repeatability or promotion.

### 2026-10-07T19:52:23.0283654-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION

T0075 COMPLETE and accepted narrowly as one prospective audited ideal-fixture run. Both independent reviews have no blockers: exact Sonnet PASS (118.56s/USD0.4391248) and native GPT6.1Sol recorded-evidence acceptance, artifacts/agents/T-0075/sol-evidence-review.md SHA2561c6e8358653556c764f96a74941df712cd72908d4cc54518b317b7e4a2b3d009. Sol independently verified eight artifact hash bindings, raw report/audit identity, one planned/one actual attempt and runtime-source bindings; it did not rehash every player binary. Native Sol cost unavailable. All workers finished and leases released.

Run20261008T023457-555a35eb:6/6 destinations,20/20 existing independent audit checks true,3982 mission-health samples pass/0fail/0unknown with complete sampled coverage, zero recovery attempts. Mission397.980s versus batch402.381s. Actual lane/depth Boolean simulation-clock parameters verified before mission. All20 reported runtime hashes match launch pins; recorded574file post-check has no drift. No second trial, re-audit, new source integration or promotion. Existing user authorization to run bounded trials and make routine reviewed decisions applies; this runtime task contains no new ASTRA-authored implementation requiring separate source approval.

Retain all previous demo failures as separate denominators. This result does not establish causation, repeatability, calibrated robot autonomy or robust margins. Negative-lag counts, inferred startup timing, player/current-Unity-source uncertainty, dirty-but-pinned source identity and null launcher ExitCode remain explicit review limits. Earlier summaries are corrected by the prior REVIEW and both full review files. T0070 interactive ownership remains unchanged; no implementation ACK or candidate has arrived. Useful next work is a bounded diagnosis of the unexplained negative-lag observations or the existing reserved Unity selector task, not automatic repetition of this successful run. No guards relaxed, source changes, pushing or publishing.
