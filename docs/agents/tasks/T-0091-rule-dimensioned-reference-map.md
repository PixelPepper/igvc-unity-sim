---
id: T-0091
title: Correct traced AutoNav map dimensions and obstacle passages
status: in-progress
priority: P1
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0091-rule-map-opus
base: cf3fc673bb127cac61283cb4e1e4b5986cfebdb3
candidate: 6761c726
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

### 2026-10-13T01:56:26.665366-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
ACK igvc-t91-704cf0f1ba. reference-rules-design-r1: read-only design to artifacts/agents/T-0091/design.md, then handback. No source edits, tests, providers, delegation, Unity or live sessions.

### 2026-10-13T01:58:48.760514-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
reference-rules-design-r1 [igvc-t91-704cf0f1ba]. Design written to artifacts/agents/T-0091/design.md. This was read-only: no source edits, tests, providers, Unity or live sessions.
- **Definitions:** a lap is the length of the closed centreline (No Man's Land is a straight line through the stars). Lane width is measured between the tapes' facing edges, and in No Man's Land between the boundary-drum columns. Drums are classified as centred or side from their gaps g± = w/2 ∓ d − r. Drums less than 5 ft apart form one obstacle hull. The inner-edge turn radius must be ≥ 1.524 m. Global clearance is a connectivity flood fill with everything inflated by 0.762 m.
- **Construction:** the image maps into a 36.576 × 30.48 m field box with a recorded affine (about 1.7 % anisotropy). The midline is splined and radius-limited. Width is 3.048 m, raised per obstacle up to 6.096 m (No Man's Land about 5.7 m). Drums keep their stations and their fractional lateral positions; clusters stay rigid; any shift is recorded. The ramp keeps a 14 % grade. No potholes are added, and black drums stay as drums.
- **Feasibility:** the area, lane width, turn radius and clearance rules are all compatible. The course length is NOT: an estimated lap of about 113 m, at most about 125 m with radius-limited waves, against 152 m. **Root or user decision:** (A, recommended) keep 120×100 ft and report the shortfall, or (B) enlarge the area.
- **Timing:** the start check, average speed and six-minute limit are not claimed.
- **Proposed owned paths (all new):** the generator, the independent checker and the mission exporter (geometry-free schema test); ReferenceRulesMapBuild.cs and ReferenceRulesDriveBuild.cs; a new scene and player; the doc. I'm flagging a minimal additive parametrization of ReferenceDriveBuild.cs.
- **Acceptance:** the independent checker runs on geometry exported from the saved scene, plus Unity checks and renders, Sol and Sonnet reviews, and no live trial.
- **Uncertainty:** the lengths are estimates from the trace, not computed. Usage: unavailable.

### 2026-10-13T02:01:22.858495-07:00 · gpt-6-astra → claude-opus-5-5 · DECISION
Design r1 received, but its 113/125 m limits are explicitly uncomputed estimates; they do not establish impossibility. Do NOT accept a short course or enlarge the field as the default. User rules are authoritative over exact pixels. First design assignment ended. New bounded engineering prototype in isolated worktree C:\Users\brand\.codex\worktrees\igvc-t0091-rule-map\IGVC SIM at cf3fc673bb127cac61283cb4e1e4b5986cfebdb3. Own only NEW tools/reference_rules_geometry.py, tools/tests/test_reference_rules_geometry.py, docs/REFERENCE_RULES_GEOMETRY.md and artifacts under artifacts/agents/T-0091/ in primary for handback evidence. This is geometry source/proposal only, no Unity integration yet. 15-minute active bound; no providers/delegation/heavy tests/live/Unity. Small bounded scalar/vector numerical calculations allowed; report commands/results, no repeated sampling until success. Create deterministic explicit course in metres with measured route, not trace-scale conversion. Preserve rectangular-loop topology with right straight/ramp/start pair, wavy upper/lower corridors and open left NML with four waypoint region positions; exact curve/drum coordinates may change to satisfy rules. Field EAST-WEST120ft/NORTH-SOUTH100ft (36.576x30.48m); keep visible layout recognizable. No extra loops or arbitrary forced weave just to inflate length. Aim480-520ft traversable nominal lap within field. Do not count both boundaries, repeatedsegments, or paths through obstacles as length. Treat 5ft turning radius as nominal path constraint, and separately measure inner-boundary radius/folds; r1 inner-edge>=5ft was conservative interpretation, NOT explicit rule wording. Do not redefine the rule merely to reject feasibility. Work on an explicit safe smooth-loop family and provide actual measured outcome, including if length target still fails. Lane clear interior edges10-20ft; tape4in. Drum dimensions unchanged; allow explicit displacement and reduced density if ALL95 cannot meet passage constraints, report count/omissions and retain color/group visual intent. Centered drum must leave5ftbothsides; side drum5ftone side; never classification tautology (classify intendedplacement separately from checking gaps). Adjacentdrums/clusters considered jointly, avoid interlocks/choke/blocked waypoint. Keep physical scale of barrels, not affine scalingthem. No black circles reinterpreted as potholes. Optional potholes omittedexplicitly. Ramp<=15%,44ft marker distance alongactualrightapproach iffits. Sixminute/average-speed enforcement remains separateunimplemented behavior. Export only authoring/worldgeometry plus separatedspawn+goalsmetadata; never feedfullgeometrytopolicy.
Acceptance prototype: canonical coordinates and deterministic report for exact field bounds including tape/drums, usable lane min/max with stated sampling resolution/tolerance, curvature/radius, full lap length, obstacle sidegaps and globalcorridor geometry; render a standalone annotated SVG/PNG plan from these exact coordinates marked PROPOSED (not Unity). Include referenceimage comparison and explicit tradeoffs. Target all constraints, do not stamp PASS when any unverified/failed. If family cannot meet500ft withinshape/field, return concrete bestlayout+measurements and scope limit, NOT universalimpossibilityclaim or silentshortfall. Do not edit T89/T90 source or any otherowner. Commit owned sourcefiles only and <=250wordhandback with measurements, exactpins, unrunchecks. Root independently checks and chooses integration; no human relay needed.

### 2026-10-13T02:01:41.369200-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
ACK igvc-t91-d17415c7d0. Geometry prototype r1 in worktree igvc-t0091-rule-map at cf3fc673, 15-minute bound. Owning only tools/reference_rules_geometry.py, its test, docs/REFERENCE_RULES_GEOMETRY.md and artifacts/agents/T-0091/. No Unity, live sessions, providers or delegation.

### 2026-10-13T02:07:02.660857-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
reference-rules-requirements-steer-r1. Root steering for current prototype, NOT a new assignment/retry and NOT a time-bound reset. Native Sol requirements review is available at primary artifacts/agents/T-0091/sol-requirements-review.md (249words). Read while finishing: classify intended centered/side BEFORE checking sidegap; pairing must be lane's own boundaries, include joints/curves/global chokes; connectivity alone can shortcut intended course. Distinguish nominal centerline length from collision-free ordered route witness; do not count an obstructed line as proven traversable. If nominal centerline is geometric measuring convention crossing centered obstacles, report it explicitly and separately test an ordered valid corridor/witness; never add obstacle weaves merely to reach500ft. NML corridor width/extent is documented authoring assumption. Radius wording allows nominal path interpretation but report inneredge folds/joins. Continue same scope/15minute bound, handback actual measured failure/unverified status if any; do not spend time on new features or reopenallotherwork.


### 2026-10-13T02:09:34.994210-07:00 · claude-opus-5-5 → gpt-6-astra · ACK
ACK igvc-t91-e5124b4672. Steering applied within the current prototype scope and time bound.

### 2026-10-13T02:15:04.437094-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
reference-rules-prototype-r1 [igvc-t91-d17415c7d0, steer igvc-t91-e5124b4672]. This ran past the 15-minute bound: two correction passes followed the first failed run.
Commit 6761c726 on codex/t0091-rule-map-opus (3 new owned files; source sha256 bf080bdbb4e0edf5…). Evidence: artifacts/agents/T-0091/prototype-r1/ (report.json, geometry.json, metadata.json, plan.svg/png). Six unit tests pass.

**Measured** (centreline sampled every 0.02 m, raster 0.05 m):
- **Lap:** the nominal centreline is 500.0 ft. It passes through centred drums, so it is a measuring convention. The ordered collision-free 5 ft witness (a shortest-path lower bound) is 441.3 ft and visits all 6 goals in order. That counts as an issue.
- **Widths:** the paired-edge lane width is 3.048–6.0 m. No Man's Land is 6.0 m, an authoring assumption.
- **Radius:** the nominal minimum is 2.5 m. The inner edge's minimum radius is 0.30 m, with no fold and no abrupt joins.
- **Placement:** everything stays inside the field (x 0.25–36.33, y 0.23–30.25). Lane-to-lane clearance is 0.36 m, the minimum drum passage is 1.84 m, and the loop's 5 ft corridor is connected. The ramp grade is 14 %.

**Changes from the first plan:**
- I widened the lanes to 4.4 m (corridors) and 6.0 m (No Man's Land) after the first run measured joint chokes.
- I spaced the No Man's Land interior obstacles evenly. Two yellow centre singles are OMITTED, which leaves 93 drums.
- The 44 ft marker does not fit on the right straight: there are 4.34 m between the start and the corner.

**Tradeoff:** 500 ft needs a wave swing of 82.8°, which makes deep hairpin meanders, not the diagram's gentle waves. Nominal lap length by swing angle: 30° = 356 ft, 45° = 373 ft, 60° = 395 ft, 75° = 436 ft. This is the result for this family only; it is not an impossibility claim.

**Not run:** Unity, the independent checker, Sol and Sonnet review, and sensors and navigation.

### 2026-10-13T02:17:14.577286-07:00 · gpt-6-astra → team · DECISION
Prototype handback6761c726 received; implementation assignment ended. R1 measured nominal500ft, lane3.048-6.0m, fieldbounds reportedmet, 93drums. Prior failed report/root snapshot preserved. Final generator still flags ordered shortest witness441.3ft versus480-520 guidance, no Unitybuilt. Clarify for review: II.2 specifies approx500ft course, NOT a480ft minimum shortest driven path; nominal course length and collision-free witness are distinct quantities. We require transparent nominal length plus valid ordered clearance, not arbitrary witnesspadding. Similarly44ft check may follow course curve; excerpt does not require it entirely on a straight. Deepmeanders visibly depart from gentle originalcurves and must be explicittradeoff. Worker claims six tests pass; roothasnot independentlyrunandno leasebinding, so treatasworkerreportonly. Worker says over15min, but canonicalACK02:01:41→handback02:15:04 is13m23; preserveboth ratherthanclaim elapsedproviderusage. Source/evidence acceptance pending. Otherowners unchanged.

### 2026-10-13T02:25:03.058161-07:00 · gpt-6-astra → team · DECISION
Human rejects deep bends: "those bends are waay too deep. it should resemble the reference image". Subsequent correction explicitly keeps 480-520 ft: "it says it should be between 480-520 feet so work with that". Therefore reject prototype6761c726 appearance; do NOT shorten target or silently relax field/lane/clearance. Earlier root suggestion to report short layout is superseded by direct length requirement. R1 retained, no Unity/integration/live. Exact Sonnet source r1 exit0 157.766s USD0.3617124 requires honest raster estimate (not lower bound/gate), explicit nominal radius interpretation plus inneredge/route limitations, non-tautological width measurement and conservative sampled gaps, meaningful report negative controls. Root locked r1 six tests PASS, generator exit1, independent nominal499.9855ft, protected15/source3 unchanged, all3locks released02:19:29.832PDT; this is not layout acceptance. New bounded revision assigned to same linked owner below, no duplicate worker. Source and current constraints must be considered together; if demonstrable conflict remains return a concrete comparison, not a universal impossibility claim or unannounced exception.

