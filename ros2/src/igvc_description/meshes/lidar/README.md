# RPLIDAR A1 supplied CAD visual

`rplidar_a1.stl` is a 30,000-triangle binary visual mesh in metres. Source archive, Inventor parts, IGES and reference PNGs remain unchanged; extracted files and full tessellation are under ignored `artifacts/vendor/rplidar-a1`. `provenance.json` records all source hashes, conversion versions, fit evidence and validation.

The supplied top/bottom PNGs show a circular rotor above the board and mounting feet. IGES global units are MM; its named `head`, `laser` and `detector` placements and tessellated cap establish native +Y as upright. A 44-point top-cap circle fit locates rotor native X/Z at approximately (-90.553263,132.917572) mm, with micrometre-scale tessellation fit residual. This is geometric alignment evidence, not hardware calibration.

Output axes map `(-native X, native Z, native Y)` after subtracting native origin (-90.553263,719.692322,132.917572) mm and scaling by .001. Thus Z is up, rotor XY is zero, bottom feet lie at Z=0, and the small motor end points toward -X. The corresponding mounting-hole pairs are approximately output X=+28 mm and -42 mm. Robot rim measurements place rotor at canonical (.2700228,0,.295) m when mounting feet seat on the bosses.

Named laser instance Y=764.29231955246 mm gives a **provisional scan height of .0446 m above feet**; detector instance center is .0436 m above feet. This is not a measured optical plane or azimuth calibration. For a scan-frame origin using that provisional height, visual origin translation is (0,0,-.0446) m with identity rotation.

The original CAD tessellation has 127,350 triangles. Quadric reduction to 30,000 preserves finite nondegenerate output with normals matching winding, and maximum axis-bound deviation is 1.111 mm (2 mm gate). Output bounds are approximately X[-.062290,.035916], Y[-.035998,.035993], Z[0,.054611] m. Exact topology, outward normals and visual/occlusion fidelity are not established; this is not collision geometry.

Reproduce from repository root in PowerShell:

```powershell
$cadPython = 'C:/Users/brand/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $cadPython -m pip install --target artifacts/deps/cad-python cadquery-ocp==8.0.1.0.0
& $cadPython -m pip install --target artifacts/deps/mesh-python fast-simplification==0.1.12 numpy==2.2.6
& $cadPython tools/prepare_lidar.py --archive 'C:/Users/brand/Downloads/rp-lidar-a1-inventor-reassembly-1.snapshot.8.zip'
```

The conversion uses OpenCascade IGES transfer and meshing with .2 mm linear/.4 rad angular deflection, followed by the existing checked simplifier. [OpenCascade IGES documentation](https://github.com/Open-Cascade-SAS/OCCT/wiki/iges) documents millimetre transfer units. Archive extraction rejects traversal, absolute paths, symlinks and duplicate destinations. Redistribution terms for the supplied CAD are not established by conversion.
