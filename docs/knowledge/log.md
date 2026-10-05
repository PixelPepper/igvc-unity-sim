# Knowledge Update Log

## 2026-10-05

* **Recovery gate target**: T-0032 adds bounded nearer-station selection inside
  observed corridor support for recovery, with an ahead-of-trap bound and unchanged
  footprint/unknown/path acceptance. Both reviews accepted the source; live evidence
  is still pending. Updated the sensor-led navigation source fingerprint.
* **Update**: Documented user-approved Opus task ownership (ADR-011) and the reviewed completion-evidence channel (T-0019). Existing source pins remain unchanged; runtime validation is tracked in task evidence.
* **Update**: Re-pinned the workflow guide again after documenting case-folded exclusions, canonical pin paths and which pins create edges (T-0015 review round 2).
* **Update**: Re-pinned the workflow guide in [Knowledge maintenance](knowledge-maintenance.md) and [OKF v0.2](okf-v0-2.md) after the T-0015 review revision. Corrected `generated.at` to the actual authoring time.
* **Initialization**: Created the bundle (T-0015) with eight concepts covering transport, frames and sensors, sensor-led navigation, processing health, trial/audit/promotion, agent handoffs, knowledge maintenance and the pinned [OKF v0.2 reference](okf-v0-2.md).

- 2026-10-05T11:52:57.866375Z: Sensor-led-navigation now describes default-off T0021 fallback, pins its source and integrated path-entry helper, and separates freshness from admission-to-send pose drift. No live benefit claimed.

* **Update**: Reviewed recovery evidence. Updated sensor-led-navigation for T0023/T0026: bounded failed-search traces,
submitted/worker/capture binding, deferred capture after health-end, and explicit
skip after recorded cleanup errors. Source pin added. Behavioral checks and live
wiring remain separate; no reliability improvement is claimed by this metadata.
