#!/usr/bin/env python3
"""Read-only URDF/STL inventory. Numerical consistency is not physical calibration."""
import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import struct
import xml.etree.ElementTree as ET


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def inspect_stl(path):
    """Stream binary triangles without retaining mesh geometry in memory."""
    size = path.stat().st_size
    with path.open('rb') as stream:
        header = stream.read(84)
        if len(header) != 84:
            return {'format': 'unrecognized'}, 'STL too short for binary format'
        count = struct.unpack_from('<I', header, 80)[0]
        if 84 + count * 50 != size:
            return {'format': 'nonbinary_or_size_mismatch'}, 'Binary STL size does not match; ASCII/other mesh inspection pending'
        lo, hi = [math.inf] * 3, [-math.inf] * 3
        for _ in range(count):
            values = struct.unpack('<12fH', stream.read(50))
            if not all(math.isfinite(value) for value in values[:12]):
                raise ValueError('Nonfinite STL normal or vertex')
            for offset in (3, 6, 9):
                for axis in range(3):
                    lo[axis] = min(lo[axis], values[offset + axis])
                    hi[axis] = max(hi[axis], values[offset + axis])
    return {'format': 'binary_stl', 'triangles': count,
            'bounds_m_assuming_urdf_units': {'min': lo, 'max': hi} if count else None}, None


def audit(source):
    report = {'source': str(source), 'package_root': str(source.parent.parent),
              'errors': [], 'warnings': ['All dimensions, masses and inertias are uncalibrated export values; positive definiteness does not establish physical validity. STL has no intrinsic units; reported bounds assume metres before mesh scale and link transforms.'],
              'links': [], 'joints': [], 'meshes': []}
    errors, warnings = report['errors'], report['warnings']
    report['urdf_sha256'] = sha256(source)
    root = ET.parse(source).getroot()
    if root.tag != 'robot':
        errors.append('Document root must be robot')
    report['robot_name'] = root.get('name')

    def numbers(text, count, label):
        try:
            values = [float(value) for value in text.split()]
            if len(values) != count or not all(math.isfinite(value) for value in values):
                raise ValueError()
            return values
        except (ValueError, AttributeError):
            errors.append('Invalid numeric value: ' + label)
            return None

    for element in root.iter():
        for attr, count in {'xyz': 3, 'rpy': 3, 'rgba': 4, 'scale': 3,
                            'lower': 1, 'upper': 1, 'effort': 1, 'velocity': 1,
                            'damping': 1, 'friction': 1, 'radius': 1, 'length': 1,
                            'size': 3}.items():
            if attr in element.attrib:
                numbers(element.get(attr), count, element.tag + '/' + attr)
    names = []
    for link in root.findall('link'):
        name = link.get('name')
        if not name or name in names:
            errors.append('Missing/duplicate link name: ' + str(name))
        names.append(name)
        item = {'name': name, 'mass_kg': None, 'inertia': None}
        inertial = link.find('inertial')
        if inertial is None:
            warnings.append(f'{name}: no inertial data')
        else:
            mass = inertial.find('mass')
            value = numbers(mass.get('value') if mass is not None else None, 1, f'{name}/mass')
            if value:
                item['mass_kg'] = value[0]
                if value[0] <= 0:
                    errors.append(f'{name}: mass must be positive')
            inertia = inertial.find('inertia')
            fields = ['ixx', 'ixy', 'ixz', 'iyy', 'iyz', 'izz']
            values = numbers(' '.join(inertia.get(k, '') for k in fields) if inertia is not None else None, 6, f'{name}/inertia')
            if values:
                a, b, c, d, e, f = values
                minors = [a, d, f, a*d-b*b, a*f-c*c, d*f-e*e,
                          a*d*f + 2*b*c*e - a*e*e - d*c*c - f*b*b]
                item['inertia'] = dict(zip(fields, values))
                item['inertia_principal_minors'] = [v if math.isfinite(v) else None for v in minors]
                if not all(math.isfinite(v) and v > 0 for v in minors):
                    errors.append(f'{name}: inertia principal minors must be finite and positive')
        report['links'].append(item)
    graph = {name: [] for name in names}
    incoming = {name: 0 for name in names}
    joint_names = set()
    for joint in root.findall('joint'):
        parent, child = joint.find('parent'), joint.find('child')
        item = {'name': joint.get('name'), 'type': joint.get('type'),
                'parent': parent.get('link') if parent is not None else None,
                'child': child.get('link') if child is not None else None}
        report['joints'].append(item)
        if not item['name'] or item['name'] in joint_names:
            errors.append('Missing/duplicate joint name: ' + str(item['name']))
        joint_names.add(item['name'])
        if item['type'] not in {'fixed', 'continuous', 'revolute', 'prismatic', 'floating', 'planar'}:
            errors.append('Unsupported joint type: ' + str(item))
        if item['parent'] not in graph or item['child'] not in graph:
            errors.append('Unknown joint link: ' + str(item))
        else:
            graph[item['parent']].append(item['child'])
            incoming[item['child']] += 1
    roots = [name for name in names if incoming[name] == 0]
    if len(roots) != 1:
        errors.append(f'Expected single root, found {roots}')
    if any(value > 1 for value in incoming.values()):
        errors.append('Link has multiple parents')
    visited, active, cycles = set(), set(), []

    def visit(name):
        if name in active:
            cycles.append(name)
            return
        if name in visited:
            return
        active.add(name)
        for child in graph[name]:
            visit(child)
        active.remove(name)
        visited.add(name)

    if roots:
        visit(roots[0])
    unreachable = sorted(set(names) - visited, key=str)
    for name in names:
        visit(name)
    if cycles:
        errors.append('Joint graph contains cycles')
    if unreachable:
        errors.append('Disconnected from selected root: ' + str(unreachable))
    report['graph'] = {'roots': roots, 'children': graph, 'cycles': cycles, 'disconnected': unreachable}
    package_root = source.parent.parent
    for uri in sorted({mesh.get('filename', '') for mesh in root.iter('mesh')}):
        mesh_report = {'reference': uri}
        report['meshes'].append(mesh_report)
        if not uri:
            errors.append('Mesh filename missing')
            continue
        if ' ' in uri or '\\' in uri or re.match(r'^[A-Za-z]:', uri):
            warnings.append(f'Linux/package portability: {uri}')
        if uri.startswith('package://'):
            package, separator, relative = uri[len('package://'):].partition('/')
            if not re.fullmatch(r'[a-z][a-z0-9_]*', package):
                warnings.append(f'Nonportable ROS package name: {package}')
            if package != package_root.name or not separator:
                errors.append('Cannot resolve source package reference: ' + uri)
                continue
            path = package_root.joinpath(*PurePosixPath(relative).parts)
        else:
            warnings.append('Non-package mesh reference: ' + uri)
            path = source.parent / uri
        path = path.resolve()
        mesh_report['resolved_path'] = str(path)
        if not path.is_file():
            errors.append('Missing mesh (check Linux case): ' + str(path))
            continue
        mesh_report.update(size_bytes=path.stat().st_size, sha256=sha256(path))
        if path.suffix.lower() == '.stl':
            try:
                details, warning = inspect_stl(path)
                mesh_report.update(details)
                if warning:
                    warnings.append(f'{uri}: {warning}')
            except ValueError as exc:
                errors.append(f'{uri}: {exc}')
        else:
            warnings.append('Mesh geometry not inspected: ' + uri)
    report['total_mass_kg'] = sum(link['mass_kg'] or 0 for link in report['links'])
    report['status'] = 'failed' if errors else 'structural_checks_passed_with_uncalibrated_values'
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--urdf', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.urdf.resolve().parent.parent):
        parser.error('Output must be outside the source package to preserve original assets')
    try:
        report = audit(args.urdf.resolve())
    except (OSError, ET.ParseError) as exc:
        report = {'status': 'failed', 'errors': [str(exc)]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'errors': len(report.get('errors', [])),
                      'warnings': len(report.get('warnings', [])), 'output': str(args.output)}))
    return int(bool(report.get('errors')))


if __name__ == '__main__':
    raise SystemExit(main())
