#!/usr/bin/env python3
"""Generate checked visual-only STL reductions; never alter canonical mesh URIs."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import struct
import sys
import tempfile

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / 'artifacts/deps/mesh-python'))
import numpy as np
import fast_simplification

DTYPE = np.dtype([('normal', '<f4', 3), ('vertices', '<f4', (3, 3)), ('attribute', '<u2')])


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def load(path):
    with path.open('rb') as stream:
        header = stream.read(84)
        if len(header) != 84:
            raise ValueError('Invalid binary STL header')
        count = struct.unpack_from('<I', header, 80)[0]
        if path.stat().st_size != 84 + count * 50 or count == 0:
            raise ValueError('Invalid binary STL length/count')
        data = np.fromfile(stream, dtype=DTYPE, count=count)
    if not np.isfinite(data['vertices']).all():
        raise ValueError('Nonfinite source vertices')
    return data


def bounds(triangles):
    vertices = triangles.reshape(-1, 3)
    return np.array([vertices.min(axis=0), vertices.max(axis=0)], dtype=float)


def normals(triangles):
    double = triangles.astype(np.float64)
    cross = np.cross(double[:, 1]-double[:, 0], double[:, 2]-double[:, 0])
    lengths = np.linalg.norm(cross, axis=1)
    return cross, lengths


def simplify(source, target, count, tolerance):
    original = load(source)
    original_bounds = bounds(original['vertices'])
    vertices, indices = np.unique(original['vertices'].reshape(-1, 3), axis=0, return_inverse=True)
    faces = indices.reshape(-1, 3)
    _, areas = normals(vertices[faces])
    keep = areas > 1e-16
    faces = faces[keep]
    points, faces = fast_simplification.simplify(vertices.astype(np.float64), faces,
                                               target_count=min(count, len(faces)), agg=7)
    triangles = points[faces].astype(np.float32)
    cross, lengths = normals(triangles)
    # Remove triangles which collapse after float32 serialization.
    keep_output = lengths > 1e-16
    triangles, cross, lengths = triangles[keep_output], cross[keep_output], lengths[keep_output]
    if not len(triangles) or len(triangles) > count:
        raise ValueError(f'{source.name}: triangle budget violated')
    result = np.zeros(len(triangles), dtype=DTYPE)
    result['vertices'] = triangles
    result['normal'] = cross / lengths[:, None]
    with target.open('wb') as stream:
        stream.write(b'IGVC provisional simplified visual mesh'.ljust(80, b'\0'))
        stream.write(struct.pack('<I', len(result)))
        result.tofile(stream)
    checked = load(target)
    cross, lengths = normals(checked['vertices'])
    if not (lengths > 1e-16).all() or not np.isfinite(checked['normal']).all():
        raise ValueError(f'{source.name}: invalid/degenerate output')
    if not np.allclose(checked['normal'], cross / lengths[:, None], atol=1e-6, rtol=0):
        raise ValueError(f'{source.name}: normals inconsistent with winding')
    simplified_bounds = bounds(checked['vertices'])
    deviation = float(np.abs(simplified_bounds-original_bounds).max())
    if deviation > tolerance:
        raise ValueError(f'{source.name}: bound deviation {deviation:.6f} m exceeds {tolerance}')
    return {'name': source.name, 'source_sha256': digest(source), 'output_sha256': digest(target),
            'source_triangles': len(original), 'target_triangles': count, 'output_triangles': len(checked),
            'removed_source_degenerate': int((~keep).sum()), 'removed_output_degenerate': int((~keep_output).sum()),
            'source_bounds_m': original_bounds.tolist(), 'output_bounds_m': simplified_bounds.tolist(),
            'max_bound_deviation_m': deviation, 'finite_nondegenerate': True, 'valid_unit_normals': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, default=REPO / 'ros2/src/igvc_description')
    parser.add_argument('--budget', type=int, default=150000)
    parser.add_argument('--max-bound-deviation', type=float, default=0.005)
    parser.add_argument('--report', type=Path, default=REPO / 'artifacts/checks/mesh-simplification.json')
    args = parser.parse_args()
    if not 20 <= args.budget <= 150000 or not 0 <= args.max_bound_deviation <= 0.005:
        parser.error('Budget must be 20..150000; bound tolerance must be 0..0.005 metres')
    package = args.package.resolve()
    source_dir, output_dir = package / 'meshes/visual', package / 'meshes/simplified'
    if args.report.resolve().is_relative_to(source_dir):
        parser.error('Report must not overwrite original meshes')
    provenance = json.loads((package / 'provenance.json').read_text())
    sources = sorted(provenance['meshes'], key=lambda item: item['output'])
    total = sum(item['triangles'] for item in sources)
    report = {'status': 'failed', 'algorithm': 'fast quadric simplification', 'aggressiveness': 7,
              'versions': {'python': platform.python_version(), 'numpy': np.__version__,
                           'fast-simplification': importlib.metadata.version('fast-simplification')},
              'platform': platform.platform(), 'budget': args.budget, 'max_bound_deviation_m': args.max_bound_deviation,
              'limitations': 'Axis-aligned extrema checks do not establish silhouette, Hausdorff distance, topology, watertightness or sensor fidelity. Geometry assumes source units are metres. Normals match local winding; outward orientation is not established.',
              'meshes': []}
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix='stage-', dir=output_dir) as temporary:
            for item in sources:
                source = package / item['output']
                if digest(source) != item['sha256']:
                    raise ValueError('Source provenance mismatch: ' + str(source))
                count = max(4, int(args.budget * item['triangles'] / total))
                result = simplify(source, Path(temporary) / source.name, count, args.max_bound_deviation)
                if digest(source) != item['sha256']:
                    raise ValueError('Source changed during simplification')
                report['meshes'].append(result)
                print(f"{source.name}: {result['source_triangles']} -> {result['output_triangles']}; bounds {result['max_bound_deviation_m']:.6f} m", flush=True)
            report['total_triangles'] = sum(item['output_triangles'] for item in report['meshes'])
            if report['total_triangles'] > args.budget:
                raise ValueError('Combined triangle budget exceeded')
            for item in report['meshes']:
                (Path(temporary) / item['name']).replace(output_dir / item['name'])
            report['status'] = 'passed'
    except Exception as exc:
        report['error'] = str(exc)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'status': report['status'], 'report': str(args.report), 'error': report.get('error')}))
    return int(report['status'] != 'passed')


if __name__ == '__main__':
    raise SystemExit(main())
