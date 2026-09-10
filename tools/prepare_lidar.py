#!/usr/bin/env python3
"""Convert supplied RPLIDAR IGES into a checked, provisional visual mesh."""
import argparse
import importlib.metadata
import json
from pathlib import Path, PurePosixPath
import stat
import struct
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'artifacts/deps/cad-python'))
import numpy as np
from OCP.IGESControl import IGESControl_Reader
from OCP.IFSelect import IFSelect_RetDone
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
from simplify_robot import DTYPE, digest, load, normals, simplify


def extract(archive_path, destination):
    destination = destination.resolve()
    entries = []
    with ZipFile(archive_path) as archive:
        if sum(i.file_size for i in archive.infolist()) > 500_000_000:
            raise ValueError('Archive exceeds extraction budget')
        seen = set()
        for entry in archive.infolist():
            name = entry.filename.replace('\\', '/')
            path = PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or ':' in name or stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError('Unsafe ZIP entry: ' + name)
            target = destination.joinpath(*path.parts).resolve()
            if not target.is_relative_to(destination) or str(target).lower() in seen:
                raise ValueError('ZIP path collision/escape')
            seen.add(str(target).lower())
            entries.append((entry, target))
        for entry, target in entries:
            if not entry.is_dir():
                target.parent.mkdir(parents=True, exist_ok=True)
                contents = archive.read(entry)
                if not target.exists() or target.read_bytes() != contents:
                    target.write_bytes(contents)
    return [{'path': str(p.relative_to(destination)), 'sha256': digest(p)} for e, p in entries if not e.is_dir()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    args = parser.parse_args()
    vendor = ROOT / 'artifacts/vendor/rplidar-a1'
    output = ROOT / 'ros2/src/igvc_description/meshes/lidar'
    output.mkdir(parents=True, exist_ok=True)
    sources = extract(args.archive, vendor)
    iges = vendor / 'RP-lidar-A1.igs'
    reader = IGESControl_Reader()
    if reader.ReadFile(str(iges)) != IFSelect_RetDone:
        raise ValueError('IGES read failed')
    unit = reader.IGESModel().GlobalSection().UnitName().ToCString()
    if unit != 'MM':
        raise ValueError('Expected the inspected millimetre source')
    component_centers = {}
    model = reader.IGESModel()
    for index in range(1, model.NbEntities() + 1):
        entity = model.Entity(index)
        if entity.TypeNumber() == 408:
            name = entity.Subfigure().Name().ToCString()
            if name in ('laser', 'detector', 'head'):
                component_centers[name] = list(entity.TransformedTranslation().Coord())
    reader.TransferRoots()
    shape = reader.OneShape()
    if shape.IsNull():
        raise ValueError('No transferred CAD shape')
    # OCCT transfers IGES into millimetres; scale vertices explicitly below.
    BRepMesh_IncrementalMesh(shape, 0.2, False, 0.4, False)
    raw = vendor / 'cad-tessellation-mm.stl'
    writer = StlAPI_Writer()
    writer.ASCIIMode = False
    if not writer.Write(shape, str(raw)):
        raise ValueError('STL export failed')
    data = load(raw)
    vertices = data['vertices'].reshape(-1, 3).astype(np.float64)
    low, high = vertices.min(axis=0), vertices.max(axis=0)
    # Inspected PNGs and Y-level sections establish +Y as top/rotor direction.
    cap = np.unique(vertices[vertices[:, 1] >= high[1] - 0.001][:, [0, 2]], axis=0)
    center_guess = (cap.min(axis=0) + cap.max(axis=0)) * 0.5
    radius = np.linalg.norm(cap - center_guess, axis=1)
    ring = cap[radius > radius.max() * 0.98]
    coefficients = np.linalg.lstsq(np.column_stack((2 * ring, np.ones(len(ring)))),
                                    (ring * ring).sum(axis=1), rcond=None)[0]
    center = coefficients[:2]
    ring_radius = float(np.sqrt(coefficients[2] + sum(center * center)))
    residual = float(np.abs(np.linalg.norm(ring - center, axis=1) - ring_radius).max())
    if len(ring) < 12 or residual > 0.01 or not 30 < ring_radius < 40:
        raise ValueError('Rotor cap circle evidence failed')
    # Right-handed mapping: native -X -> model +X, +Z -> +Y, +Y -> +Z.
    transform = np.array([[-1, 0, 0], [0, 0, 1], [0, 1, 0]], dtype=float)
    origin = np.array([center[0], low[1], center[1]])
    normalized = ((vertices - origin) @ transform.T * 0.001).reshape(-1, 3, 3).astype(np.float32)
    cross, lengths = normals(normalized)
    keep = lengths > 1e-16
    intermediate = np.zeros(int(keep.sum()), dtype=DTYPE)
    intermediate['vertices'] = normalized[keep]
    intermediate['normal'] = cross[keep] / lengths[keep, None]
    normalized_path = vendor / 'normalized-full-m.stl'
    with normalized_path.open('wb') as stream:
        stream.write(b'RPLIDAR visual only, metres, rotor XY and feet Z datum'.ljust(80, b'\0'))
        stream.write(struct.pack('<I', len(intermediate)))
        intermediate.tofile(stream)
    temporary = vendor / 'validated-lidar.stl'
    mesh = simplify(normalized_path, temporary, 30000, 0.002)
    target = output / 'rplidar_a1.stl'
    temporary.replace(target)
    report = {'status': 'passed', 'archive': str(args.archive.resolve()), 'archive_sha256': digest(args.archive),
              'sources': sources, 'iges_unit': unit, 'ocp_version': importlib.metadata.version('cadquery-ocp'),
              'numpy_version': np.__version__, 'simplifier_version': importlib.metadata.version('fast-simplification'),
              'tessellation': {'linear_deflection_mm': 0.2, 'angular_deflection_rad': 0.4, 'triangles': len(data)},
              'datum': {'native_upright_axis': '+Y', 'origin_native_mm': origin.tolist(),
                        'rotation_native_to_output': transform.tolist(), 'scale_to_metres': 0.001,
                        'output_origin': 'rotor axis in XY, bottom mounting foot plane Z=0',
                        'output_orientation': 'Z up; motor end toward -X',
                        'rotor_cap_circle_radius_mm': ring_radius, 'fit_points': len(ring), 'fit_residual_mm': residual,
                        'provisional_scan_height_m': (component_centers['laser'][1] - low[1]) * 0.001,
                        'scan_height_basis': 'Named laser IGES instance center; provisional, not calibrated optical center',
                        'component_instance_centers_native_mm': component_centers,
                        'optical_zero_azimuth': None},
              'source_mesh_bounds_mm': [low.tolist(), high.tolist()], 'mesh': mesh,
              'output': 'meshes/lidar/rplidar_a1.stl',
              'limitations': ['CAD reassembly provenance; no hardware calibration or redistribution license inferred.',
                              'True optical scan-plane height and azimuth are uncalibrated; provisional height uses CAD laser instance placement.',
                              'Decimated visual mesh is not exact topology or collision geometry; bounds checks do not prove full surface fidelity.']}
    (output / 'provenance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'output': str(target), 'triangles': mesh['output_triangles'], 'bounds_m': mesh['output_bounds_m'],
                      'max_bound_deviation_m': mesh['max_bound_deviation_m'], 'native_origin_mm': origin.tolist()}))


if __name__ == '__main__':
    main()
