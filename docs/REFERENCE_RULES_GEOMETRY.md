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
5. **Drums.** Top and bottom drums sit at the diagram's x stations. Each drum's intended class is fixed before any measurement. NML interior obstacles are spaced evenly in diagram order, and two NML centre singles are omitted (93 drums).

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
