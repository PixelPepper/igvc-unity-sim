# Extracted camera tilt bracket

Regenerate using the bundled Python runtime and existing task-local mesh dependencies:

```powershell
& 'C:/Users/brand/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' tools/prepare_camera_mount.py --simplify
```

The script preserves the external original, selects a complete closed connected component, and retains the stationary pole. `assessment.json` records provenance and transforms.

- `base_static_source_basis.stl`: full stationary base, original source basis. Retain canonical visual Z=pi rotation.
- `base_static_source_basis_simplified.stl`: same coordinate contract, 101,237-triangle maximum, 5mm extrema tolerance; uses `tools/simplify_robot.py` helper with aggressiveness 7 and `artifacts/deps/mesh-python`.
- `moving_bracket_pivot_level.stl`: canonical physical-forward basis, pivot-relative and level. Use identity visual origin under the pitch joint at (-0.34396836,0,0.8), axis Y. Positive pitch is downward. Joint +4.094519 degrees recovers the original pose.

Extraction/simplification is visual-only. No calibrated collision or inertial split. Extrema agreement is not a silhouette, topology or sensor-occlusion fidelity guarantee.
