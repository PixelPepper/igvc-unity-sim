# Reference AutoNav 2027 map (T-0089)

Diagram-derived authoring scene. It's a separate map and is not certified against the rules.
It contains no robot, controller, ROS link or route export.

- Menu: `IGVC/Reference Map/Create 2027 AutoNav Map` (prompts to save modified scenes first).
- Batch: `ReferenceMapBuild.GenerateAndValidate` writes
  `artifacts/agents/T-0089/unity-validation.json`, `overview.png` and `oblique.png`.
- Output: `Assets/IGVC/Scenes/ReferenceAutoNav2027.unity`; generated meshes/materials only under
  `Assets/IGVC/GeneratedReferenceMap`.

## Geometry (metres; x = east, z = north)

- Area 36.576 x 30.48 (120 x 100 ft). Centreline stays 1.85 m inside the boundary.
- Lane 3.2 m (within 10-20 ft). White tape 0.1016 m, drawn at +0.01 m on the ground/ramp surface.
- Right straight with a centred ramp: 0.45 m high, 3 m ascent, 1.2 m deck, 3 m descent (15 % grade), 3.7 m wide.
- North/South start-finish lines 4.6 m either side of the ramp centre. Speed-check posts sit 13.41 m (44 ft)
  along the path from each line, heading away from the ramp.
- North and south connectors are single-period cosine dips (5 m amplitude) with 3.2 m corner arcs.
- The No Man's Land on the left is unpainted. Its authoring path is a 4 m cosine bulge.
- Drums are 0.597 m diameter and 1.008 m tall. These sizes were reported by the interactive author from user
  measurements and were not independently confirmed here. Connector clusters hold two yellow drums each and
  alternate sides. They sit 0.15 m inside the tape and leave a 2.35 m bypass on the open side. None are centred.
- No Man's Land has four mixed-colour drums plus six flat, non-colliding white 0.61 m pothole disks.
  Waypoints and labels are EditorOnly.

## Assumptions and limits

- The south edge of the diagram is cropped, so it is reconstructed as a mirror of the north connector.
- Blue ink, arrows and stars in the diagram are treated as annotations. All tape is white.
- Path length is below target. The analytic estimate is about 136 m (~446 ft), short of the 480-520 ft goal.
  Deeper connector dips would make the north and south lanes overlap within 100 ft. The JSON reports the
  measured length, and the path is never labelled 500 ft.
- Validation checks the following: tape width, footprint, ramp grade, path length, minimum turn radius
  (conservative 0.2 m/1 m circumradius), non-local lane separation, speed-check distance, obstacle-tape and
  waypoint gaps, colliders, and durable assets.
- Not verified: rule certification, navigation success, sensor appearance, pothole/tire physics and drum dimensions.
