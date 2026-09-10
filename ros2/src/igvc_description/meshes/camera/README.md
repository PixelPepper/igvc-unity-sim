# Official OAK-D Pro enclosure

`oak_d_pro.stl` is the official standard USB OAK-D Pro enclosure, sourced through [Luxonis's CAD index](https://github.com/luxonis/oak-hardware/blob/master/DM9098_OAK-D-Pro/3D_Models/README.md), not Pro W or PoE. The supplied front/back/side images were inspected for orientation. The original robot attachment assembly was located, but conversion used the available official neutral STEP instead of changing that assembly.

The mesh is in metres with body bounding-box center at the origin, forward +X, left +Y and up +Z. Dimensions are 23.1009 mm deep ×97 mm wide ×29.5 mm high. OpenCascade tessellation uses .25 mm linear and .7 rad angular deflection without QEM/mesh decimation, preserving the CAD planar surfaces. The resulting count and hashes are recorded in `provenance.json`; output is checked below 60,000 triangles with finite nondegenerate faces and consistent normals.

The central RGB aperture's front-surface datum is approximately **(.01155045,0,.00476378) m** relative to body center. This is the aperture center projected onto front glass/enclosure, not a measured optical center. The lower mounting boss datum is approximately **(-.00555045,-.03705,-.01475) m**, from a CAD bore radius2.55 mm, down-facing axis. Its off-center location agrees with the supplied side photograph. No thread standard or physical bracket alignment is inferred.

Reproduce from repository root:

```powershell
$cadPython = 'C:/Users/brand/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $cadPython -m pip install --target artifacts/deps/cad-python cadquery-ocp==8.0.1.0.0
& $cadPython tools/prepare_camera.py
```

The script checks the inspected STEP SHA256 before conversion, preserves downloaded source under `artifacts/vendor/oak-d-pro`, and emits mesh/provenance here. CAD colors are not retained in STL. Hardware revision, optical calibration and assembled visual correctness still need validation. No camera mounts, URDF frames or Unity scene changes are included.
