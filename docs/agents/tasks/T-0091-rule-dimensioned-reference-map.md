---
id: T-0091
title: Correct traced AutoNav map dimensions and obstacle passages
status: in-progress
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: none
base: 1f8d6ffc3677f38e2ecef07959d9dc29f5b551fa
candidate: none
claim: none
lease: none
updated: 2026-10-13
---

## Packet
User has challenged the 6 ft 4 in lane and supplied AutoNav II.2 requirements. Correct current drivable map to dimensional constraints while preserving image layout, detailed drums and lighting. Do not treat hand-drawn image as surveyed scale. Lane 10-20 ft, typical10ft; turn radius >=5ft; course approximately500ft in120x100ft area; tape3-4in; ramp <=15%; obstacle usable passages >=5ft, centered obstacles >=5ft BOTH sides. Thus a0.597m centered drum requires at least3.645m clear lane. North/south starts around right ramp, sinusoidal top/bottom, open No Man's Land at left and four waypoints remain recognizable. Optional potholes2ftdiameter must not be invented as black drums or silently alter existing diagram. Record exclusions/interpretations. Timing first44ft/30s and >1mph average, sixminute cap are separate judged behaviors; do not silently claim existing180s diagnostics enforce them. No policy/auditor/guard changes in this geometry slice; no geometry export to policy. Robot/sensor mounts unchanged.

FIRST assignment is bounded read-only geometry/integration design, FIVE active minutes. Read README, this packet, primary ReferenceMapBuild/ReferenceDriveBuild/ReferenceDriveChecks, mission exporter, lastT90 decisions and rules-pages-1-16.txt sectionII.2. Inspect only necessary source. Write artifacts/agents/T-0091/design.md <=700words with concrete geometrical construction, feasibility of ALL constraints together, exact proposed owned paths and independent acceptance strategy. Include course-length definition (one traversable lap, not sum of boundary lengths or invented weave), openleft handling, lane-width definition (usable interior edges), centered/side drum classification, curved-turn radius, global clearance/connectivity, renderer/export transform. No source edits/commits, tests, providers/delegation, Unity/live or task header changes. Short ACK and <=250word handback in this canonical log. Root will assign isolated successor only after design; no duplicate worker. Other task ownership unchanged.

## Log

### 2026-10-13T01:56:08.572398-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
reference-rules-design-r1. Direct user correction makes rules dimensions authoritative; current T89/T90 scaled trace inadequate. Original records preserved. Existing linked session only. Five-minute read-only design scope above; no retry of T84 or other blocked tasks.
