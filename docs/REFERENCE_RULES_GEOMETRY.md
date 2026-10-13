# Rule-dimensioned reference course: PROPOSED geometry (T-0091, r2)

`tools/reference_rules_geometry.py` produces deterministic course geometry in metres. It is a **proposal only**: no Unity, no navigation policy and no certification.

r1 (commit `6761c726`) reached 500 ft with deep arc meanders and was rejected as unlike the reference image. r2 instead builds the centreline from the reference trace itself. That gives shallow connector waves, a straight right side and an open No Man's Land (NML) with four stars.

```bash
python3 tools/reference_rules_geometry.py --out artifacts/agents/T-0091/prototype-r2/attempt-2 --reference artifacts/agents/T-0089/trace-plan.png
```

## Construction
1. **Midline.** The traced outer and inner tapes (Catmull-Rom, the same as `ReferenceMapBuild.Curve`) are paired by nearest point, and the midpoint of each pair is taken. A straight NML segment closes the loop, which runs counter-clockwise starting from the right straight.
2. **Fit.** The midline is fitted into a box that leaves room for the physical lane, tape and drum allowances. It is then smoothed with a fixed periodic Gaussian (σ = 1.5 m) and resampled every 0.02 m. There are two variants:
   - **`field-120x100`:** fitted into 120 ft east–west × 100 ft north–south. The fit is anisotropic (1.49×, reported).
   - **`length-500ft`:** the same fit, scaled uniformly until the nominal lap is 500 ft. The required footprint is reported as an issue, never accepted silently.
3. **Widths.** The right straight is 3.048 m, the corridors 4.4 m and NML 6.0 m. NML width is an authoring assumption between the drum columns. Width changes taper over 3 m.
4. **Fixed physical sizes.** Drums, tape (0.1016 m) and ramp (0.30 m over 2.145 m, 14 %) are never scaled.
5. **Drums.** Top and bottom drums sit at the diagram's x stations. Each drum's intended class is fixed before any measurement. NML interior obstacles are spaced evenly in diagram order. r2–r5 omitted two NML centre singles (93 drums); r6 restores them 0.35 of a station gap from each NML end, giving all 95 reference markers, enforced by identity, not only by count.

## Measurements
- **Lap:**
  - The nominal closed-centreline length is a measuring convention: it passes through centred drums.
  - The north start → south start length is reported separately.
- **Usable width:** the nearest distance from the centreline to each of the lane's own two inner tape edges, summed. It is not the construction offset.
- **Radius:**
  - The II.2 five-foot rule is applied to the nominal centreline.
  - The inner tape-edge radius, the fraction of it below 5 ft, and any fold are reported separately.
- **Drum gaps:** cross-sections in 1 cm steps that consider all drums jointly. Each gap is reduced by two steps to stay conservative.
- **5 ft corridor raster:**
  - Inflated by half a cell diagonal, with diagonal moves allowed only when both orthogonal neighbours are free.
  - The loop is cut at the north start.
  - The ordered witness must reach the six goals in order. Its length is a **grid estimate, not a bound and not a gate**, and the path is not curvature-limited; an indicative radius is reported.
- **Silhouette:**
  - the maximum deviation from the fitted trace;
  - for each connector: vertical excursion, maximum tangent angle and number of direction reversals, compared with the source trace.
- **44 ft marker:** placed along the route and allowed to fall on a curve.
- **Negative controls in the tests:** a blocked lane and a wrong goal order.

## Exclusions
- Optional potholes are omitted.
- Black circles are drums.
- Timing behaviours are not enforced.

## r3: mission-length variant `rules-485` (larger footprint authorized by the user)
- **Purpose.** The exported mission runs from the north start to the south start. `rules-485` uniformly scales the same shallow silhouette so that run is about 485 ft, while keeping the closed loop at or under 520 ft. The calibration takes 3 bounded steps.
- **Footprint.** The required footprint is reported in `authorized_deviations`.
- **Verdicts are kept separate:**
  - `authorized_geometry_met`: true only when there are no issues.
  - `full_rule_compliance`: always false or "not claimed", because the field differs from II.2's 120 × 100 ft area, and judged timing and Unity are unverified.
- **Radius.** The local osculating-circle radius of the nominal centreline: the three-point circumradius of samples ±0.5 m apart. It must be at least 5 ft. The inner tape-edge radius equals the nominal radius minus half the lane width, and is reported only. Driven-route curvature is unverified.
- **Shallow-shape gate** (`SHAPE_LIMITS`, compared with the fitted source trace at the same scale):
  - direction reversals equal to the source's;
  - maximum tangent no more than the source's + 5°;
  - excursion no more than 1.25× the source's;
  - silhouette deviation no more than 1.25 m.
  - A hairpin control in the tests must fail this gate.
- **Width.** Measured lane width must be at least 3.048 m, with no tolerance. The right lane is 3.058 m.

## Proposed Unity adapter (not implemented; root assigns it separately)
**New owned paths only:**
- **`Editor/ReferenceRulesMapBuild.cs`.** Reads `geometry.json` and builds a new `Scenes/ReferenceAutoNav2027Rules.unity`.
  - Tape ribbons from the exported tape centrelines.
  - Ground sized to the footprint.
  - A ramp with three colliders.
  - Drums: existing `RealisticObstacles.DrumMesh` visuals over the original cylinder colliders.
  - `RealismAssets` materials.
  - Annotations are `EditorOnly`.
- **`Editor/ReferenceRulesDriveBuild.cs`.** Builds a separate drive scene and player. It merges the map with `R3aDriveBuild.CreateScene` and spawns at the north start, heading north. It adds `LaneBoundaryGuard` from the tape edges and terrain supports, reusing the existing `ReferenceDriveConditions`.
- **`Editor/ReferenceRulesDriveChecks.cs`.** Adds independent saved-scene checks.
- **`tools/reference_rules_mission.py`.** A mission exporter that reads `metadata.json` only.

The T-0089/T-0090 sources, scenes and players, the runtime guards and the launchers stay unchanged. Any reuse of `ReferenceDriveBuild` internals needs a reviewed, minimal, additive parametrization.
