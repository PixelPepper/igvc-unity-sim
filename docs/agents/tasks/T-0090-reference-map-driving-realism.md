---
id: T-0090
title: Drive the traced AutoNav map with realistic visual conditions
status: ready
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: pending
base: 15cae186f773ba1b5db350a16460c12bc8ba35ce
candidate: none
claim: none
lease: none
updated: 2026-10-13
---

# T-0090: Traced-map driving and realistic conditions

## Packet

Human requests robot on the newly accepted image-traced map, bounded runs, better barrels and lighting/shadows, reusing Claude's existing realism work. Preserve the T0089 diagram geometry. Runtime policy remains sensor-led with only sanitized broad destinations. No geometry leakage, guard weakening, unreviewed whole-branch imports, or blocked T0084 retry. T70/T86/T85/T88 ownership unchanged.

First slice is READ-ONLY integration discovery: five minutes active. Read T0089 final log/source; relevant R3aDriveBuild, TransportProbe, SoonerCourseBuild, and sim-realism branch SimConditions/RealisticObstacles and their integration. Identify minimal nonconflicting owned paths, scene/launch/mission interface and exact existing source commits. Propose practical robot placement and first test protocol on this map, acknowledging incomplete auditor compatibility and possible impassable traced gaps. Return plan <=300 words plus evidence path. No source edits/tests/builds/live/providers/delegation. Root independently examines managed launch and validation. After plan root will dispatch a concrete implementation slice.

## Log

### 2026-10-13T00:36:49.879326-07:00 · gpt-6-astra → team · ANSWER
Direct user authorizes bot running on the new map, test runs, and realistic conditions/lighting/shadows/barrel visuals. This is new scope after T0089 completion; prior no-live restriction superseded for bounded trials here. It does not authorize retrying T0084 or changing autonomy/auditor guards.

### 2026-10-13T00:36:49.879326-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
reference-driving-discovery-r1: existing linked interactive session only. Read packet and append ACK, then bounded plan to artifacts/agents/T-0090/discovery-plan.md and this log. Five-minute read-only task. No source/Unity/provider/new worker actions. Preserve all existing owners.
