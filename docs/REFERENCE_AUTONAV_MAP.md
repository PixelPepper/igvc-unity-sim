# Reference AutoNav 2027 map (image-traced)

`ReferenceMapBuild` builds a **separate** authoring scene, `Assets/IGVC/Scenes/ReferenceAutoNav2027.unity`, from the supplied 2027 AutoNav course diagram. Generated meshes and materials go under `Assets/IGVC/GeneratedReferenceMap`. The scene has no robot, controller, ROS connection, route or autonomy export.

- Menu: **IGVC > Reference Map > Create 2027 AutoNav Map**.
- Batch: `-executeMethod ReferenceMapBuild.GenerateAndValidate`. This saves the scene and assets, reopens them, validates, and writes `artifacts/agents/T-0089/unity-validation.json`, `overview.png` (portrait 1049 x 1160) and `oblique.png` (1600 x 1334).
- Both entry points offer to save modified open scenes first.

## What it reproduces
Following the user's correction ("look at the image and make it the same"), the geometry is **image-first**:
- Every coordinate comes from root's literal pixel trace of the diagram, embedded in the source:
  - image sha256 `67ca76bb94954549223de2804d6b33ceda7eecdf5c138c3b78c2f5336c4e068b`;
  - trace sha256 `b3ddd39101c58cc400790559b219b244eca99aadfbb10ae5d880db19e6dff239`.
- Mapping: isotropic 0.035 m per pixel, `x = (px - 548) * 0.035`, `z = (580 - py) * 0.035`. The ground covers the full 1049 x 1160 px image, which is 36.715 x 40.6 m.
- **Two independent white tape boundaries**, 0.1016 m wide, from 62 outer and 55 inner traced controls. They are smooth Catmull-Rom curves through the controls, with the long right edges kept exactly straight. No boundary is drawn across the open left No Man's Land. Tape follows the ramp's top surface.
- **Every traced circle at its traced position and colour:** 77 yellow, 6 red, 6 green and 6 black drums. Drums are 0.597 x 1.008 m, the user's measurement. The black circles have no legend, so they are interpreted as editable black drums. No white pothole discs are invented.
- **The ramp** fills the traced rectangle: 0.30 m high, 0.4 m deck, with symmetric slopes of about 14%.
- North and south start-finish lines are drawn across the right lane at their traced positions.
- **Annotations are EditorOnly and have no colliders:**
  - four blue waypoint stars;
  - the blue start and speed-check blocks shown on the diagram;
  - the labels.

  The previews show them. There is no reference route.

## Honest limits
- **Tracing accuracy:** the controls are visual tracing estimates, not exact pixel extraction.
- **Cropped edge:** the diagram is cropped near 1100 px, so the lower outer boundary controls 37-41 and 50-52 are reconstructed. The report lists them.
- **Diagram text is not a measurement:** "480-520 ft", "44 ft" and "4 in" are diagram annotations, not measurements of this map. Course route length is **unverified**.
- **No rule claims:** area, lane width, turn radius and passage clearances are not claimed. Objects are placed for visual fidelity, not moved to satisfy clearance rules. The report gives measured lane widths and drum-to-tape gaps.
- **Not validated here:** sensor appearance, navigation and drum dimensions.
