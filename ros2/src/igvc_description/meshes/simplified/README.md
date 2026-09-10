# Provisional simplified visuals

Five binary STL reductions total **149,986 triangles**, down from 888,264. Original files under `meshes/visual` and canonical URIs remain unchanged. See `validation.json` for per-file hashes, versions, counts, bounds and checks; the working report is also written to `artifacts/checks/mesh-simplification.json`.

From the repository root in PowerShell, using the bundled Python 3.12 runtime:

```powershell
$meshPython = 'C:/Users/brand/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $meshPython -m pip install --target artifacts/deps/mesh-python fast-simplification==0.1.12 numpy==2.2.6
& $meshPython tools/simplify_robot.py --budget 150000 --max-bound-deviation 0.005
```

Dependencies are task-local Windows wheels; they cannot be reused by WSL Python. Another Python installation may install those same pinned versions in its own environment. The generator records actual versions and platform. Two runs on the current host produced identical STL SHA256 hashes; cross-platform bitwise identity is unverified.

The algorithm uses welded equal-coordinate vertices and quadric edge collapse with aggressiveness 7, distributing triangle budget proportionally among source meshes. Degenerate source/output faces are removed; normals are recomputed from float32 output winding. Binary output is reloaded and checked for finite vertices, nondegenerate faces, normal agreement and axis-aligned bounds before promotion. Original hashes must match provenance.

Largest bound deviation was 1.703 mm, below the 5 mm limit. This checks bounding extrema, not complete silhouettes or surface distances. Topology, watertightness, outward normal orientation, tiny components, occlusion and visual fidelity require separate inspection before switching runtime URIs. These meshes are visual assets, not wheel/contact collision models.
