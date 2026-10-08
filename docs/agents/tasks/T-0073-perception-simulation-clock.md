---
id: T-0073
title: Bind simulator perception nodes to the simulation acquisition clock
status: integrated
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0073-perception-clock-opus
base: 5346e60
candidate: 6199046b2f86d168a290bfdbcd15d2c89998f8d5
claim: tested
lease: none
updated: 2026-10-07
---

# Packet

SOLE HEADLESS owner opus-t0073-perception-clock-20261007, separate from INTERACTIVE
T0070 (still reserved). Worktree C:/Users/brand/.codex/worktrees/igvc-t0073-perception-clock/IGVC SIM.
This is a new launch-clock configuration task, NOT a retry of T0072 demo diagnosis.
The four relevant launch/node source files match HEAD; external dirty files excluded.

Read README intro, this packet, ros2/src/igvc_navigation/launch/local_navigation.launch.py,
ros2/src/igvc_perception/launch/perception.launch.py, and perception depth_node.py and
lane_node.py tick()/success_is_fresh(), plus test/test_processing_idle.py.
Both perception nodes compare self.get_clock().now() with simulation image stamps.
Both simulator launch entrypoints omit use_sim_time for lane_detector/depth_processor,
while local_navigation explicitly enables it for Nav2 and scan_ground_filter. Inspect
the actual source and fix the omission if confirmed; do not claim effective parameters
of a historical run are known. Existing clock-regression status counts versus zero
telemetry /clock resets motivate this check but do not prove the cause.

Own ONLY these two launch files and NEW
ros2/src/igvc_perception/test/test_simulation_clock_launch.py. No node policy edits,
dependencies, clocks/threshold changes, telemetry/auditor changes, primary edits,
Unity, tests/imports, providers or delegation. SOURCE ONLY, static ast.parse allowed.
Commit exact owned paths. Root runs checks under all three locks after handback.

Acceptance:
- Explicit simulation-time clock for both camera-processing nodes in both simulation
  launch entrypoints. Preserve lane point_ttl and unrelated parameters/actions.
- Steady timers, monotonic receipt checks, acquisition freshness limits and genuine
  clock regression handling remain untouched. No health bypass or default hardware
  behavior changes inside the node classes.
- Behavioral tests load actual launch descriptions (stub only unrelated package-share
  lookup/MPPI marker using temp files as necessary), resolve effective node parameters,
  catch omission/false for either node/entrypoint, and retain existing lane TTL.
- Include an actual rclpy clock/parameter behavior test where feasible: use the resolved
  parameter with a real node and deterministic ROS clock override or bounded synthetic
  /clock delivery; demonstrate simulated acquisition time remains distinct from wall
  time. No active simulator or external services. Avoid sleeps/unbounded DDS waits,
  private API coupling when public launch/rclpy APIs suffice. Report any unavailable
  ROS dependencies honestly; do not replace behavior coverage with source-string tests.
- Explain compatibility and unverified live effects in <=300-word handback. No claim
  of fixing the audit or CPU/power problem before actual evidence.

Budget exact claude-opus-5-5 high,6min/requested USD5, no retry/substitution. Stop at
handback or bound; root reviews before integration. No live trial is authorized here.

## Log

### 2026-10-07T18:46:19.0528380-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH

Assign source-only launch-clock fix to named headless owner in isolated worktree. This
is disjoint from T0070 and T0072; neither assignment is retried or transferred. Root
verified relevant source is clean at5346e60. Tests/imports/live work remain prohibited
to this worker; six-minute/USD5 requested bound, no automatic retries.

### 2026-10-07T18:50:21.2031961-07:00 · gpt-6-astra → claude-sonnet-5-5 · HANDBACK

Opus returned6199046b2f86d168a290bfdbcd15d2c89998f8d5; only two simulator launch files
and new ROS test changed. Exact model confirmed,68.69s/USD0.2907404. Worker ran no tests;
its attempted ast.parse was tool-permission blocked and it reported that honestly.
Full handback/result preserved artifacts/agents/T-0073/implementation. Assignment ended.
Root9 focused ROS checks PASS under all3locks in validation-scriptfile, log SHA256
f558a3ba9a89318ac72196cc329771001a507d7810b6864925dc706d23354897; all3 candidate hashes
and9 tracked external preimages unchanged. Two earlier wrapper import failures are
preserved: validation and validation-envfix ran no behavior tests (two loader errors).
Corrected sourced PYTHONPATH and moved WSL shell body to a saved script; no candidate
changes. Duplicate node-name warnings retained. Real launch/rclpy plus existing idle/
regression/freshness tests only; no live simulator or historical-cause proof. Sonnet
source review is currently dispatched; Sol evidence review waits for its worker slot.
### 2026-10-07T18:51:28.2321369-07:00 · gpt-6-astra → gpt-6.1-sol · REVIEW

Sonnet source review PASS for6199046,28.56s/USD0.105909, preserved review/handback.md.
No blocking findings. Limits: generic rclpy clock nodes plus resolved launch parameters
are not a launched ROS stack; startup /clock arrival and live health effects untested.
Direct standalone watchdog tool launch remains outside scope. Native Sol is checking
candidate/test/log/lease bindings and the preserved failed wrapper attempts. No source
integration has occurred yet. Headless Sonnet assignment ended.

### 2026-10-07T18:51:52.2451828-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION

Accept6199046 as tested launch-clock configuration fix: Sonnet source PASS and native
Sol candidate-test binding accepted (sol-evidence-review.md). All earlier failures
remain. Authoritative scope is simulation launch parameter binding; no historical
causal proof, live audit benefit or hardware autonomy claim. Root will integrate only
these3 files under all3locks and verify primary hashes/focused checks. T0070 unaffected.

### 2026-10-07T18:52:27.4992604-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION

Integrated only the3 accepted source files at9bbba2358549c693550b84572319d9c01cbe6022.
All hashes match6199046;9 primary ROS focused checks PASS/no skips under all3locks,
log00008e58b42020161f6f8335e8545acacac4939d0e8311d7dc9178b5643815ad;9 tracked external
preimages unchanged. Locks released. Final Sol integration binding pending. Total
Claude reported usageUSD0.3966494; native Sol unknown. No ROS overlay rebuild or live
mission run: deployment and live health/audit effect remain unverified. Do not repeat
completed checks or reconstruct this fix; latency T0070 ownership stays separate.

### 2026-10-07T18:53:09.1616954-07:00 · gpt-6-astra → claude-opus-5-5 · REVIEW

Final native Sol integration binding accepted; sol-integration-review.md SHA2566135c149725d837508e3f5d13aca330fe1a920a0c01565467d40cc91de090ed7.
Three source hashes,9 PASS/no skips, log/leases and9 protected preimages verified.
All T0073 worker assignments finished. Next independent runtime validation must bind
installed overlay/launch hashes and effective use_sim_time values before driving;
this source integration alone does not establish deployment or audit benefit.

### 2026-10-07T19:04:44.8283331-07:00 · gpt-6-astra → claude-opus-5-5 · NOTE

Root is preparing one bounded deployment validation: build only igvc_navigation and igvc_perception into the native igvc_ws overlay, bind installed launch hashes, then query actual lane/depth use_sim_time services from each launch on isolated domain89 (Nav2 autostart false). All3 locks held before process checks and throughout. No Unity, driving, sensor replay or audit; no repeated unit checks. Existing sandbox overlay checker omits launch-file hashes, so source integration alone does not guarantee deployment. T0070 reservation unchanged. Results will be preserved under artifacts/agents/T-0073/deployment.


### 2026-10-07T19:05:53.0628639-07:00 · gpt-6-astra → claude-opus-5-5 · NOTE

Selected two-package deployment succeeded (2.49s) and installed launch hashes match accepted source. First runtime harness failed before querying a parameter because root used AsyncParameterClient.wait_for_service instead of wait_for_services. Full deployment logs/result retained; owned launch group cleaned, all3 locks released, source and9 tracked external preimages unchanged. Fixing only harness API and retrying parameter-service validation in a new deployment-services attempt; no rebuild or source changes. No runtime parameter success claimed yet.


### 2026-10-07T19:06:47.9560128-07:00 · gpt-6-astra → gpt-6.1-sol · REVIEW

New deployment-services attempt PASS: both real installed launch entrypoints returned boolean use_sim_time=true from lane and depth parameter services on domain89. Launch-file hashes match accepted source; deployment was two selected packages only, no Unity or mission. Original failed harness remains deployment/, corrected service-only check did not rebuild. Result runtime hash2475b3bdf59335bd3341e3772a6eb8890ea2d29d6e5fe6fe5b9efe121ed2ed23; log97948ece0315a81ec5e943f7ddd63f4d64a4f0b5ec51b3b3095f41ad0d683c9b. Sources and9 tracked external preimages unchanged; all3 locks held throughout and released. Native Sol reviewing evidence. IMPORTANT: deliberate group SIGINT produced node shutdown RCLError/KeyboardInterrupt logs (child exit1/-2); parent exit0 and absent owned groups prove termination, not graceful node shutdown. No sensor-acquisition, live health, audit or historical causal benefit claimed.


### 2026-10-07T19:07:57.5411248-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION

Native Sol accepted narrow deployment/service evidence in sol-deployment-review.md SHA2561676b09a4e182b038d50661c208154079615b2129c5ecfa16fa1f0796aa46311. The native igvc_ws overlay now contains the accepted launch hashes, with both actual entrypoints returning true for both lane/depth use_sim_time. Do not rebuild or repeat this probe without new cause. Original root API failure and shutdown tracebacks retained; termination verified, graceful node shutdown not established. All workers finished and locks released. Next independent live validation must still freeze source/settings/player and bind active launch clock parameters, retain every attempt and run the complete audit; no demonstrated sensor-health/lap benefit yet. No live mission authorized by this task packet; create a separate bounded trial task if proceeding. T0070 interactive reservation remains intact, and T0068/69 latency source remains unintegrated.

