# October 6 route-scorer comparison and teacher review

This is local development evidence for the ideal Unity/ROS fixture, not calibrated
hardware autonomy or a release. Runtime still uses observations and six broad GPS
destinations. No course geometry was added to runtime policy.

## Completed comparison: T0043

The independently launched `artifacts/sandbox/batch/ab-route-2/` compared route
weights 0 and 8 on seeds 2331–2340 at two isolated instances. The coordinator
observed it in progress, preserved ownership, and did not launch duplicate trials.
Both wrappers exited 0; both players ended, ROS shutdown was reported, and TCP
10000–10002 were observed free after completion. The parent generated the audits.

| Result | Route weight 0 | Route weight 8 |
|---|---:|---:|
| Planned trials | 10 | 10 |
| Recorded attempts, including startup retry | 10 | 11 |
| Reached 6/6 | 8 | 9 |
| Passed all independent audit checks | 7 | 9 |
| Audit-pass fraction of all attempts | 7/10 | 9/11 |

Every failure remains in the record:

- Seed2331, both treatments: sensor/clock freshness expiry latched autonomy off.
- Seed2335, weight0: no observed collision-free backup with useful forward clearance.
- Seed2336, weight0: reached6/6, but failed `sensor_health_interval_verified`.
  All other audit checks passed. A completed lap is not sufficient for acceptance.
- Seed2339, weight8: one missing-live-costmap startup attempt, then a successful
  retry. The retry does not erase the failed attempt or enlarge the seed sample.

Among seven pairs where **both** treatments passed the full audit, weight8 was
slower on six. Median extra simulation time was6.44s; mean extra time24.39s;
aggregate time was6.56% higher. These are conditional comparisons of mutually
passing pairs, not unconditional speed or causal-effect estimates.

Assignments were deterministic and complementary across instances, balancing
five trials per treatment per instance. Shared host load, instance-by-seed
effects, order/carryover and startup stagger remain confounders. Normal mean
frame times do not exclude rare long stalls. The sample does not justify changing
defaults, claiming statistical significance, or optional batching until a desired
p-value. Corridor scorer remains off. This batch does not replace the separate
T0034/T0035 promotion criteria or resolve the original2029 freshness failure.

### Evidence binding

- Merged report: `artifacts/sandbox/batch/ab-route-2/batch-report.json`, SHA256
  `0b64d29bfb480303b2fdefd577a446aa6a0c9b4e3c36b88b1badc173ad04b752`.
- Complete attempt index: `artifacts/agents/T-0043/closed-attempts.json`.
- Derived counts and matched timing: `artifacts/agents/T-0043/final-summary.json`.
- Per-run `provenance.json`, `run.json`, and `batch-audit.json` remain under their
  original `artifacts/sandbox-instance-{1,2}/runs/` directories.
- First-pair provenance confirms effective weights0/8 and the weight8 model
  `d9b3935081e65be9acfe806fd0521cbfcf3682a104d8d72df60f282bb0afc9c6`.
  Both record sensor_course source hash
  `c3c93114231b0b5748540b366262fd11e27510fc4a42a37a968504684ccb0a66`.
  Coordinator observed the sandbox assembly hash matching T0042 on disk, but
  launch-time player identity was not bound by each run. Do not claim otherwise.

### Narrowed transport evidence

Root and Sol independently inspected the first pair's received-odometry samples.
Last inferred receipt times were189.445073789 and189.459392880 on the shared WSL
monotonic clock, 14.319ms apart. Mission loops continued with increasing receipt
ages before cleanup began at190.366072262 and190.238445497 (ages0.921/0.779s).
This supports stalled receipt updates preceding cleanup. Callbacks are not wire
arrival times; this does not identify Unity, transport, ROS processing or host
scheduling as the cause. Nor does it establish scorer causation or synchronized
failure onset. See `initial-pair-completion-phases.json` in the T0043 artifacts.
No transport timing records were found in finished instance1's Unity log;
T0042 tracing must not be assumed to have been enabled for this batch.

## Offline teacher: not integrated

An existing Claude branch supplied95b0baf. Independent reviews found unchecked
endpoint attachments, a bounded search mislabeled as unreachable, an invented
100m target penalty, mixed-group regret changes, and missing dataset version
guards. That candidate was not accepted for training or integration.

Opus revised it on a separate branch as ece7278 (T0045), with additive opt-in
path-v3 targets, unavailable statuses, unchanged legacy numeric targets and
dataset admission checks. Root validation:12 Python tests passed; C# checks
reported75 passed/4 failed, including an indexing exception in the synthetic
fixture. Original failures are preserved. A bounded revision is in progress;
no successful C# validation, integration, retraining or live benefit is claimed.

The WORLD-derived teacher is an approximate offline grid reference. It must never
feed course geometry or oracle paths into runtime features or navigation.

See [T0043](../agents/tasks/T-0043-active-scorer-comparison.md) and
[T0045](../agents/tasks/T-0045-corridor-teacher-integrity.md) for current review
state, source identities and the next bounded action.
