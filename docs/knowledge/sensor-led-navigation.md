---
type: Architecture
title: Sensor-led navigation
description: The observed-only planning pipeline and its hard safety checks.
tags: [navigation, planning, guidance, path-entry, safety]
status: stable
generated: { by: codex/gpt-6-astra, at: 2026-10-05T12:31:17.335811Z }
sources:
  - id: sensor-autonomy
    resource: ../SENSOR_AUTONOMY.md
    title: Sensor-led autonomy design
  - id: guidance
    resource: ../../tools/observed_navigation.py
  - id: path-entry
    resource: ../../tools/path_entry.py
  - id: replacement-path
    resource: ../../tools/replacement_path.py
  - id: recovery-evidence
    resource: ../../tools/recovery_evidence.py
igvc_sources:
  - path: tools/recovery_evidence.py
    sha256: 27ed8ce71d27dc384503f5849043eb9ba410a24c8daa29d13dd93a4c181cf367
  - path: tools/path_entry.py
    sha256: 4f11a1cbc4e894df92acdceabf745e8fc4ac9414dd41bd44fdb4dc6aceb574ac
  - path: tools/replacement_path.py
    sha256: d86453392284eb244cb346ff533ad582a238471caac800c4508a8ab03a348da7
  - path: docs/SENSOR_AUTONOMY.md
    sha256: 1dd11e27fafbce6866bebc09943c8d2a76d5890cc7bf702803035a091ecf995c
  - path: tools/observed_navigation.py
    sha256: ad93a94721502c6f00422f0598826ec46f7e48a0006ec76aa325aa971ee67ce5
---

# Inputs allowed at run time

Observations (paint, hazards, depth, lidar, odometry) plus six broad GPS destinations in a sanitized `autonomy.json`.
The policy never reads `course.json`, WORLD geometry, Reference Lab output or teacher labels. Those are for rendering
and the independent audit only.[^sensor-autonomy]

# Pipeline

1. **Guidance.** Observed corridor guidance proposes intent from lane pairs. An entered visible mouth hands off into
   the shared observed span.[^guidance]
2. **Search.** The search admits only full-footprint, forward, curvature-bounded paths under a wall and expansion budget.
3. **Path entry.** Path entry joins the latest pose with a checked forward biarc and re-sweeps the connector and the
   remaining path. It rejects excessive tracking error, lethal cells and unknown cells.[^path-entry]
   The caller checks stream freshness; that does not prove zero pose drift during admission and dispatch.
4. **Replacement fallback (experimental, default off).** With the explicit revalidation option, a rejected new
   proposal may trigger one check of the accepted active path for the same action/destination. Only the resulting
   checked connector and suffix are submitted; the old geometry is not blindly retained.[^replacement-path]
   Unit checks are separate from live preemption, timing and performance evidence.
5. **Recovery.** Recovery uses checked backups within a bounded budget.
   If a far observed gate has no clear lateral target, recovery can try nearer
   stations in the same observed boundary overlap, at most64 steps. New retreated
   targets remain ahead of the trap by a nominal front offset. All body/unknown
   checks and the downstream checked backup/forward continuation remain required.
   Ordinary planning does not enable this recovery-only target option.[^guidance]
   Failed legacy searches retain bounded rejection stages and fingerprints of the submitted and worker inputs.
   The full observed-input capture is deferred until after attempted command-stop cleanup and health-interval end,
   and skipped if cleanup records errors. Capture/worker mismatch or unavailable binding remains explicit.
   Diagnostic evidence does not alter recovery acceptance or prove a timed replay will be identical.[^recovery-evidence]

# Not claimed

A bounded search that finds no route is not proof that no route exists. Replay of a saved decision is not a live result.

[^sensor-autonomy]: Sensor-led autonomy design
[^guidance]: Observed navigation guidance
[^path-entry]: Path-entry admission

[^replacement-path]: Optional checked replacement fallback

[^recovery-evidence]: Failed-search diagnostics and deferred exact-input capture
