#!/usr/bin/env python3
"""Tessellate official OAK-D Pro enclosure without destructive decimation."""
import importlib.metadata
import json
from pathlib import Path
import struct
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'artifacts/deps/cad-python'))
import numpy as np
from OCP.STEPControl import STEPControl_Reader
from OCP.IFSelect import IFSelect_RetDone
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
from simplify_robot import DTYPE, digest, load, normals

URL = 'https://oak-files.fra1.cdn.digitaloceanspaces.com/OAK-D-Pro/DM9098Pro_enclosure.stp'
EXPECTED_SHA256 = '9440c72a8e5abdb9737ff7add4ad45f3571cfb69c0341570c093dbcaeb5137f4'


def make_markers(output, body_center, front_x):
    """Appearance overlays at CAD aperture centers, not simulated lenses."""
    segments = 32
    centers = [(native_x-body_center[0], -6.98622-body_center[1])
               for native_x in (6.99995, 44.49995, 81.99995)]
    rings, glass = [], []
    import math
    for y_mm, z_mm in centers:
        y, z = y_mm*.001, z_mm*.001
        for index in range(segments):
            a, b = index*2*math.pi/segments, (index+1)*2*math.pi/segments
            def point(radius, angle, x):
                return (x, y+radius*math.cos(angle), z+radius*math.sin(angle))
            outer_a, outer_b = point(.0045, a, front_x+.0002), point(.0045, b, front_x+.0002)
            inner_a, inner_b = point(.0036, a, front_x+.0002), point(.0036, b, front_x+.0002)
            rings.extend([(outer_a, outer_b, inner_b), (outer_a, inner_b, inner_a)])
            glass.append(((front_x+.00025, y, z), point(.00355, a, front_x+.00025), point(.00355, b, front_x+.00025)))
    records = []
    for name, triangles in [('oak_d_pro_lens_rings.stl', rings), ('oak_d_pro_lens_glass.stl', glass)]:
        vertices = np.asarray(triangles, dtype=np.float32)
        cross, lengths = normals(vertices)
        assert np.isfinite(vertices).all() and (lengths > 1e-16).all()
        result = np.zeros(len(vertices), dtype=DTYPE)
        result['vertices'], result['normal'] = vertices, cross/lengths[:, None]
        assert np.allclose(result['normal'], [1, 0, 0], atol=1e-6)
        target = output / name
        with target.open('wb') as stream:
            stream.write(b'OAK CAD aperture appearance markers only, +X front'.ljust(80, b'\0'))
            stream.write(struct.pack('<I', len(result)))
            result.tofile(stream)
        checked = load(target)
        records.append({'file': name, 'triangles': len(checked), 'sha256': digest(target), 'normals': '+X'})
    report = {'purpose': 'Visual aperture overlays to avoid opaque enclosure glass hiding cameras; not lens simulation',
              'source': URL, 'source_sha256': EXPECTED_SHA256,
              'cad_aperture_centers_body_m': [[front_x, y*.001, z*.001] for y, z in centers],
              'cad_aperture_outer_radius_m': .0045,
              'appearance_inner_ring_radius_m': .0036, 'appearance_glass_radius_m': .00355,
              'forward_offsets_m': {'rings': .0002, 'glass': .00025}, 'segments': segments,
              'suggested_materials': {'rings': 'grey metallic', 'glass': 'dark blue'},
              'limitations': 'Positions and outer radius derive from official CAD aperture cylinders. Inner radii/colors are visual choices. No optical calibration, IR projectors or lens physics represented.',
              'files': records}
    (output / 'lens-markers.json').write_text(json.dumps(report, indent=2)+'\n')


def main():
    vendor = ROOT / 'artifacts/vendor/oak-d-pro'
    output = ROOT / 'ros2/src/igvc_description/meshes/camera'
    vendor.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    source = vendor / 'DM9098Pro_enclosure.stp'
    if not source.exists():
        with urlopen(URL, timeout=60) as response:
            contents = response.read(50_000_001)
        if len(contents) > 50_000_000:
            raise ValueError('CAD download exceeds size budget')
        source.write_bytes(contents)
    if digest(source) != EXPECTED_SHA256:
        raise ValueError('Official CAD source differs from inspected pin')
    reader = STEPControl_Reader()
    if reader.ReadFile(str(source)) != IFSelect_RetDone:
        raise ValueError('STEP read failed')
    reader.TransferRoots()
    shape = reader.OneShape()
    if shape.IsNull():
        raise ValueError('No CAD shapes transferred')
    # OpenCascade STEP transfer produces millimetres. Preserve surfaces; no QEM.
    BRepMesh_IncrementalMesh(shape, 0.25, False, 0.7, False)
    raw = vendor / 'tessellated-mm.stl'
    writer = StlAPI_Writer()
    writer.ASCIIMode = False
    if not writer.Write(shape, str(raw)):
        raise ValueError('STL export failed')
    data = load(raw)
    vertices = data['vertices'].astype(np.float64)
    low, high = vertices.reshape(-1, 3).min(axis=0), vertices.reshape(-1, 3).max(axis=0)
    if not np.allclose(high-low, [97, 29.5, 23.1009], atol=0.02):
        raise ValueError('Unexpected source bounds or units')
    origin = (low + high) * 0.5
    rotation = np.array([[0, 0, 1], [1, 0, 0], [0, 1, 0]], dtype=float)
    normalized = ((vertices-origin) @ rotation.T * 0.001).astype(np.float32)
    cross, lengths = normals(normalized)
    keep = lengths > 1e-16
    result = np.zeros(int(keep.sum()), dtype=DTYPE)
    result['vertices'] = normalized[keep]
    result['normal'] = cross[keep] / lengths[keep, None]
    if not 0 < len(result) <= 60000:
        raise ValueError('Triangle budget exceeded')
    candidate = vendor / 'validated-camera.stl'
    with candidate.open('wb') as stream:
        stream.write(b'Official OAK-D Pro CAD enclosure, metres, X forward Z up'.ljust(80, b'\0'))
        stream.write(struct.pack('<I', len(result)))
        result.tofile(stream)
    checked = load(candidate)
    cross, lengths = normals(checked['vertices'])
    if not (lengths > 1e-16).all() or not np.isfinite(checked['normal']).all():
        raise ValueError('Invalid output geometry')
    if not np.allclose(checked['normal'], cross/lengths[:, None], atol=1e-6, rtol=0):
        raise ValueError('Output normals inconsistent with winding')
    target = output / 'oak_d_pro.stl'
    candidate.replace(target)

    def convert(point):
        return ((np.array(point)-origin) @ rotation.T * .001).tolist()

    report = {'status': 'passed', 'source_url': URL, 'source_sha256': digest(source),
              'official_index': 'https://github.com/luxonis/oak-hardware/blob/master/DM9098_OAK-D-Pro/3D_Models/README.md',
              'product': 'https://docs.luxonis.com/hardware/products/OAK-D%20Pro',
              'source_model': '2022-06-03 CREO 010-00008-02_ASM enclosure',
              'cadquery_ocp_version': importlib.metadata.version('cadquery-ocp'),
              'method': 'CAD tessellation only, no decimation', 'linear_deflection_mm': .25,
              'angular_deflection_rad': .7, 'raw_triangles': len(data), 'triangles': len(checked),
              'removed_degenerate': int((~keep).sum()), 'output_sha256': digest(target),
              'source_bounds_mm': [low.tolist(), high.tolist()], 'source_body_center_mm': origin.tolist(),
              'source_to_output_rotation': rotation.tolist(), 'output_axes': '+X forward, +Y left, +Z up',
              'bounds_m': [(rotation @ (low-origin)*.001).tolist(), (rotation @ (high-origin)*.001).tolist()],
              'rgb_front_surface_datum_m': convert([44.49995, -6.98622, high[2]]),
              'rgb_datum_basis': 'Center of central CAD aperture projected onto frontmost enclosure/glass plane; not calibrated optical center',
              'bottom_tripod_boss_datum_m': convert([7.45, -26.5, -7.0]),
              'tripod_datum_basis': 'CAD cylindrical bore radius2.55mm at native(7.45,-26.5,-7), axis-Y; thread standard not inferred',
              'finite_nondegenerate': True, 'normals_match_winding': True,
              'limitations': ['Exact device revision/focus variant match requires hardware confirmation.',
                              'Enclosure CAD includes openings and windows, not calibrated optical frames or active camera simulation.',
                              'STL loses CAD colors/materials; no topology/outer-normal guarantee from numeric checks alone.']}
    (output / 'provenance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'output': str(target), 'triangles': len(checked),
                      'rgb_front_surface_datum_m': report['rgb_front_surface_datum_m'],
                      'bottom_tripod_boss_datum_m': report['bottom_tripod_boss_datum_m']}))
    make_markers(output, origin, report['bounds_m'][1][0])


if __name__ == '__main__':
    if sys.argv[1:] == ['--markers-only']:
        directory = ROOT / 'ros2/src/igvc_description/meshes/camera'
        existing = json.loads((directory / 'provenance.json').read_text())
        make_markers(directory, existing['source_body_center_mm'], existing['bounds_m'][1][0])
    else:
        main()
