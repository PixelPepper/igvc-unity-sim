# Rule-dimensioned reference course: PROPOSED geometry (T-0091 prototype)

`tools/reference_rules_geometry.py` produces a deterministic course, in metres, for the AutoNav II.2 dimensions. It is a geometry proposal only. It has no Unity integration, sets no navigation policy and certifies nothing.

```bash
python3 tools/reference_rules_geometry.py --out artifacts/agents/T-0091/prototype-r1 --reference artifacts/agents/T-0089/trace-plan.png
```

**Outputs:**
- `geometry.json`: authoring and render world geometry.
- `metadata.json`: spawn and six goals only. This is the only file a mission exporter may read.
- `report.json`: measurements and issues.
- `plan.svg` and `plan.png`: the plan marked PROPOSED, next to the reference trace.

## Construction
- **Field:** 36.576 m east–west × 30.48 m north–south; x points east, y north, and the origin is the south-west corner.
- **Loop:** the course is driven counter-clockwise from the north start, heading north. It keeps the diagram's topology: a right straight with the ramp and start pair, wavy upper and lower corridors, and the open left No Man's Land with four star regions.
- **Centreline:** an exact chain of straights and arcs.
  - The corners have a 4 m radius.
  - Each corridor has two arc–straight–arc waves of radius 2.5 m.
  - The wave swing angle is solved by bisection so the nominal centreline is exactly 500 ft.
- **Lane widths (clear interior):**
  - right straight: 3.048 m;
  - corridors: 4.4 m;
  - No Man's Land: 6.0 m. This is an authoring assumption, measured between the inner edges of the coloured drum columns.
  - Widths taper along the corners.
- **Tape:** 0.1016 m wide, with no tape across No Man's Land.
- **Ramp:** 0.30 m rise over 2.145 m runs (14 %). It is 0.3 m wider than the lane on each side.
- **Drums:** 0.597 × 1.008 m, physical size. Each drum's intended class (centre, side, boundary or flank) is set *before* any measurement. Stations follow the diagram's order.

## Measurement conventions
- **Usable width:** the distance between the lane's own paired inner tape edges, along the local normal, sampled every 0.02 m.
- **Turn radius:** the nominal radius is the centreline radius. The inner-edge radius and fold detection are reported separately.
- **Drum gaps:** each drum gets a cross-section along its local normal (1 cm steps) that considers every drum jointly. Blocked runs closer than 5 ft are merged.
- **Global passage:**
  - The raster (5 cm) holds the free positions for the centre of a 5 ft disc. It is inflated by half a cell diagonal, and diagonal moves are allowed only when both orthogonal neighbours are free.
  - The loop is cut at the north start line.
  - The **ordered route witness** is the shortest free path all the way around the cut. It must enter all six goal regions in order.
- **Nominal centreline vs proven route:** the nominal centreline is a measuring convention and passes through centred drums. The witness proves that a collision-free lap exists. Because it is the shortest path, its length is a lower bound on any driven lap.

## Exclusions
- Optional 2 ft potholes are omitted.
- The black circles are drums.
- Timing behaviour is not enforced or claimed: 44 ft in 30 s, an average above 1 mph, and the six-minute cap.
