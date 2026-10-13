# Driving the PROPOSED rule-dimensioned reference course (T-0091)

**Status:** source only. Nothing has been built or run yet.

The selected geometry variant is `rules-485`. The name is legacy; the r4 target is 484 ft. It keeps the shallow, isotropic shape of the source image in a larger footprint that the user authorized. It is **not** II.2 compliant, because the area differs from 120 × 100 ft and judged timing is unverified. The T-0089/T-0090 sources, scenes, players and materials are not modified.

## Inputs (pinned by root after review)
Generate the geometry:

```bash
python3 tools/reference_rules_geometry.py --variant rules-485 --out artifacts/agents/T-0091/prototype-r4/selected --reference <source PNG>
```

Then copy two of its outputs to the pinned paths:
- **`rules-485/unity-input.json` → `artifacts/agents/T-0091/unity-input.json`.** This is the build-time authoring input. It is never copied into Resources, StreamingAssets or player data, and never given to autonomy.
- **`rules-485/metadata.json` → `artifacts/agents/T-0091/mission-metadata.json`.** This holds only the spawn and the six goals.

The build fails closed if the input is missing or malformed, names the wrong task or variant, has the wrong drum count (93), has changed physical sizes (drum, tape or ramp), contains non-finite values, or has a spawn heading more than 2° off north.

## Commands (PowerShell, repository root; root runs these under the simulator locks)
```powershell
powershell -ExecutionPolicy Bypass -File tools/reference-rules-map.ps1 -Action build
powershell -ExecutionPolicy Bypass -File tools/reference-rules-map.ps1 -Action start -Conditions clear-noon
```

- **build** runs `ReferenceRulesDriveBuild.Build`. It produces the scene `Assets/IGVC/Scenes/ReferenceRulesAutoNav2027Drive.unity` and the player `artifacts/build-reference-rules/IGVCReferenceRules.exe`. It then runs `ReferenceRulesDriveChecks`, which writes `artifacts/agents/T-0091/unity-validation.json` and the `artifacts/agents/T-0091/unity/rules-*.png` captures.
- **Protected files** that `R3aDriveBuild`/`ProbeBuild` rewrite are restored byte-for-byte afterwards, even when the build fails. The restore is recorded in `unity-protected-restore.json`.
- **Launcher.** `tools/reference-rules-map.ps1` is the T-0090 launcher with only these changes: paths, player name, build method, and the mission export (`tools/reference_rules_mission.py --metadata`). Locks, preflight, cleanup, ownership latches and the trial policy are unchanged. The 180 s diagnostic trial is not six-minute rule enforcement.

## Scene
- **Robot:** the R3-a robot, sensors and TransportProbe come from `R3aDriveBuild.CreateScene`. Only the probe's test props are removed.
- **Origin:** the course root is translated so the north start-line centre is odom (0, 0), heading north (Unity +z, ROS +x). The lane heading at the start is 0.28° off north; this is reported.
- **Physical sizes:**
  - 93 drums: 0.597 × 1.008 m cylinder colliders, each with a `RealisticObstacles.DrumMesh` visual.
  - Two 4 in tape ribbons.
  - Ramp: 0.30 m rise, 14 % grade, three support colliders.
  - Asphalt ground the size of the footprint.
- **Materials** are created in `Assets/IGVC/GeneratedReferenceRules`. The Asphalt031 textures are shared read-only. `RealismAssets.Asphalt`, `Lit` and `Sky` are deliberately not called, because they would modify T-0090 materials.
- **Lane guard:** built from both edges of every saved tape mesh. It is simulator truth only, run with `--line-guard scoring`. It has no policy geometry and is not relaxed.
- **Lighting:** a single soft sun and procedural sky, with `ReferenceDriveConditions` presets clear-noon, overcast and low-sun. No stars or labels are visible to the sensors.

## Checks (`ReferenceRulesDriveChecks`, on the SAVED scene)
- Drum ids, colours, positions (≤ 1 mm) and sizes, checked against the input.
- Tape centres (≤ 1 mm) and widths.
- Ramp colliders, guard segments and spawn `CanOccupy`.
- Robot pose and camera.
- Persistent meshes, and materials only from `GeneratedReferenceRules`.
- No annotations; a single sun.
- Captures: clear-noon overview, oblique and sensor views, plus a low-sun overview. The camera data needed for root's independent render checks is recorded.

## Not claimed
Navigation success, II.2 compliance, driven-route curvature, and weather or sensor noise. The nominal centreline lengths (484.2 ft north→south, 512.7 ft closed) are measuring conventions, not a driven path.
