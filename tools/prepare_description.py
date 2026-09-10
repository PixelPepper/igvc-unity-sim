#!/usr/bin/env python3
"""Stage normalized description from unchanged audited SolidWorks exports."""
import argparse
import copy
import json
import math
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

from audit_robot import audit, sha256

PHYSICAL_NAMES = {'wheel_left': 'wheel_right', 'wheel_right': 'wheel_left',
                  'left_caster': 'right_caster', 'right_caster': 'left_caster',
                  'leftWheel': 'rightWheel', 'rightWheel': 'leftWheel',
                  'leftCaster': 'rightCaster', 'rightCaster': 'leftCaster'}


def physical_vector(values):
    return [-values[0], -values[1], values[2]]


def normalize_forward(robot):
    """Change every link basis by Rz(pi), with physical left/right name mapping."""
    for link in robot.findall('link'):
        link.set('name', PHYSICAL_NAMES.get(link.get('name'), link.get('name')))
        for visual in link.findall('visual'):
            origin = visual.find('origin')
            if origin is None:
                origin = ET.SubElement(visual, 'origin')
            origin.set('xyz', format_vector(physical_vector(vector(origin.get('xyz', '0 0 0')))))
            rpy = vector(origin.get('rpy', '0 0 0'))
            rpy[2] += math.pi  # Mesh bytes stay in the original coordinate basis.
            origin.set('rpy', format_vector(rpy))
        for origin in link.findall('inertial/origin') + link.findall('collision/origin'):
            # Export has identity origin rotations; conjugation preserves identity.
            if any(abs(v) > 1e-12 for v in vector(origin.get('rpy', '0 0 0'))):
                raise ValueError('Nonidentity inertial/collision rotation requires explicit conjugation support')
            origin.set('xyz', format_vector(physical_vector(vector(origin.get('xyz', '0 0 0')))))
            origin.set('rpy', '0 0 0')
        inertia = link.find('inertial/inertia')
        if inertia is not None:
            for component in ('ixz', 'iyz'):
                inertia.set(component, format(-float(inertia.get(component)), '.17g'))
    for joint in robot.findall('joint'):
        joint.set('name', PHYSICAL_NAMES.get(joint.get('name'), joint.get('name')))
        for tag in ('parent', 'child'):
            element = joint.find(tag)
            element.set('link', PHYSICAL_NAMES.get(element.get('link'), element.get('link')))
        origin = joint.find('origin')
        if origin is not None:
            if any(abs(v) > 1e-12 for v in vector(origin.get('rpy', '0 0 0'))):
                raise ValueError('Nonidentity joint rotation requires explicit conjugation support')
            origin.set('xyz', format_vector(physical_vector(vector(origin.get('xyz', '0 0 0')))))
            origin.set('rpy', '0 0 0')
        axis = joint.find('axis')
        if axis is not None:
            axis.set('xyz', format_vector(physical_vector(vector(axis.get('xyz')))))
    joints = {joint.get('name'): joint for joint in robot.findall('joint')}
    for name in ('leftWheel', 'rightWheel', 'leftCaster', 'rightCaster'):
        xyz = vector(joints[name].find('origin').get('xyz'))
        if not (xyz[0] > 0 if 'Wheel' in name else xyz[0] < 0):
            raise ValueError('Physical front/rear semantic check failed: ' + name)
        if not (xyz[1] > 0 if name.startswith('left') else xyz[1] < 0):
            raise ValueError('Physical left/right semantic check failed: ' + name)
    if vector(joints['leftWheel'].find('axis').get('xyz')) != [0, 1, 0] or vector(joints['rightWheel'].find('axis').get('xyz')) != [0, -1, 0]:
        raise ValueError('Physical wheel axis signs failed')


def vector(text):
    return [float(x) for x in text.split()]


def format_vector(values):
    return ' '.join(format(x, '.17g') for x in values)


def add_lidar(robot, destination, provenance):
    mount_file = destination / 'config/lidar_mount.json'
    if not mount_file.exists():
        return
    mount = json.loads(mount_file.read_text(encoding='utf-8'))
    for key in ('scan_xyz_m', 'visual_xyz_m', 'visual_rpy_rad'):
        if len(mount[key]) != 3 or not all(math.isfinite(v) for v in mount[key]):
            raise ValueError('Invalid lidar transform: ' + key)
    mesh_path = (destination / mount['mesh']).resolve()
    if not mesh_path.is_relative_to(destination) or not mesh_path.is_file():
        raise ValueError('Lidar mesh must exist within description package')
    link = ET.SubElement(robot, 'link', {'name': 'lidar_link'})
    visual = ET.SubElement(link, 'visual')
    ET.SubElement(visual, 'origin', {'xyz': format_vector(mount['visual_xyz_m']),
                                   'rpy': format_vector(mount['visual_rpy_rad'])})
    ET.SubElement(ET.SubElement(visual, 'geometry'), 'mesh',
                  {'filename': 'package://igvc_description/' + mount['mesh']})
    ET.SubElement(ET.SubElement(visual, 'material', {'name': 'lidar_dark'}), 'color', {'rgba': '0.055 0.065 0.07 1'})
    joint = ET.SubElement(robot, 'joint', {'name': 'lidar_mount', 'type': 'fixed'})
    ET.SubElement(joint, 'parent', {'link': 'base_link'})
    ET.SubElement(joint, 'child', {'link': 'lidar_link'})
    ET.SubElement(joint, 'origin', {'xyz': format_vector(mount['scan_xyz_m']), 'rpy': '0 0 0'})
    provenance['lidar_mount'] = {'configuration': 'config/lidar_mount.json', 'configuration_sha256': sha256(mount_file),
                               'mesh_sha256': sha256(mesh_path), 'calibration': mount['calibration']}


def add_camera(robot, destination, provenance):
    mount_file = destination / 'config/camera_mount.json'
    if not mount_file.exists():
        return
    mount = json.loads(mount_file.read_text(encoding='utf-8'))
    for key in ('pivot_xyz_m', 'body_xyz_from_pivot_m', 'optical_xyz_from_body_m'):
        if len(mount[key]) != 3 or not all(math.isfinite(v) for v in mount[key]):
            raise ValueError('Invalid camera transform: ' + key)
    mesh_path = (destination / mount['mesh']).resolve()
    if not mesh_path.is_relative_to(destination) or not mesh_path.is_file():
        raise ValueError('Camera mesh must exist within description package')
    # Remove the extracted moving bracket from the base visual without changing the source-frame rotation.
    robot.find("link[@name='base_link']/visual/geometry/mesh").set('filename', 'package://igvc_description/' + mount['static_base_mesh'])
    moving = ET.SubElement(robot, 'link', {'name': 'camera_mount_link'})
    ET.SubElement(ET.SubElement(ET.SubElement(moving, 'visual'), 'geometry'), 'mesh',
                  {'filename': 'package://igvc_description/' + mount['moving_bracket_mesh']})
    joint = ET.SubElement(robot, 'joint', {'name': 'camera_pitch_joint', 'type': 'revolute'})
    ET.SubElement(joint, 'parent', {'link': 'base_link'})
    ET.SubElement(joint, 'child', {'link': 'camera_mount_link'})
    ET.SubElement(joint, 'origin', {'xyz': format_vector(mount['pivot_xyz_m']), 'rpy': '0 0 0'})
    ET.SubElement(joint, 'axis', {'xyz': '0 1 0'})
    ET.SubElement(joint, 'limit', {'lower': '-0.5235987755982988', 'upper': '0.5235987755982988', 'velocity': '1', 'effort': '1'})
    link = ET.SubElement(robot, 'link', {'name': 'camera_link'})
    visual = ET.SubElement(link, 'visual')
    ET.SubElement(ET.SubElement(visual, 'geometry'), 'mesh', {'filename': 'package://igvc_description/' + mount['mesh']})
    ET.SubElement(ET.SubElement(visual, 'material', {'name': 'camera_dark'}), 'color', {'rgba': '0.05 0.05 0.05 1'})
    for label, filename, color in [('lens_rings', 'oak_d_pro_lens_rings.stl', '0.3 0.35 0.4 1'),
                                   ('lens_glass', 'oak_d_pro_lens_glass.stl', '0.03 0.08 0.14 1')]:
        detail = ET.SubElement(link, 'visual', {'name': label})
        ET.SubElement(ET.SubElement(detail, 'geometry'), 'mesh', {'filename': 'package://igvc_description/meshes/camera/' + filename})
        ET.SubElement(ET.SubElement(detail, 'material', {'name': label}), 'color', {'rgba': color})
    for name, parent, child, xyz, rpy in [
        ('camera_body_fixed', 'camera_mount_link', 'camera_link', mount['body_xyz_from_pivot_m'], '0 0 0'),
        ('camera_optical_fixed', 'camera_link', 'camera_color_optical_frame', mount['optical_xyz_from_body_m'], '-1.5707963267948966 0 -1.5707963267948966')]:
        if child == 'camera_color_optical_frame':
            ET.SubElement(robot, 'link', {'name': child})
        fixed = ET.SubElement(robot, 'joint', {'name': name, 'type': 'fixed'})
        ET.SubElement(fixed, 'parent', {'link': parent}); ET.SubElement(fixed, 'child', {'link': child})
        ET.SubElement(fixed, 'origin', {'xyz': format_vector(xyz), 'rpy': rpy})
    provenance['camera_mount'] = {'configuration': 'config/camera_mount.json', 'configuration_sha256': sha256(mount_file),
                                'mesh_sha256': sha256(mesh_path), 'calibration': mount['calibration']}


def rotate(point, rpy):
    x, y, z = point
    r, p, yaw = rpy
    y, z = math.cos(r)*y-math.sin(r)*z, math.sin(r)*y+math.cos(r)*z
    x, z = math.cos(p)*x+math.sin(p)*z, -math.sin(p)*x+math.cos(p)*z
    return [math.cos(yaw)*x-math.sin(yaw)*y, math.sin(yaw)*x+math.cos(yaw)*y, z]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--urdf', required=True, type=Path)
    parser.add_argument('--package', type=Path, default=Path(__file__).resolve().parent.parent / 'ros2/src/igvc_description')
    args = parser.parse_args()
    source, destination = args.urdf.resolve(), args.package.resolve()
    if destination.is_relative_to(source.parent.parent) or source.is_relative_to(destination):
        parser.error('Source and destination packages must be separate')
    inspected = audit(source)
    if inspected['errors']:
        raise SystemExit('Source audit failed: ' + '; '.join(inspected['errors']))
    robot = ET.parse(source).getroot()
    robot.set('name', 'r3_a')
    robot.set('xmlns:xacro', 'http://www.ros.org/wiki/xacro')
    robot.insert(0, ET.Comment('Canonical normalized export. Collision boxes are provisional outer bounds, not validated wheel/contact geometry. No sensor mounts or base_footprint added.'))
    mesh_info = {item['reference']: item for item in inspected['meshes']}
    provenance = {'schema_version': 1, 'source_urdf': str(source), 'source_urdf_sha256': inspected['urdf_sha256'],
                  'robot_name': 'r3_a', 'package_name': 'igvc_description',
                  'preserved': ['physical geometry', 'mass', 'inertia tensor under basis transformation', 'joint types and physical placement'],
                  'frame_normalization': {'rotation': 'Rz(pi) in every link coordinate basis',
                                          'physical_forward': 'large drive wheels front (+X), casters rear (-X), user confirmed',
                                          'name_mapping': PHYSICAL_NAMES,
                                          'mesh_policy': 'unchanged bytes; visual origins premultiplied by Rz(pi)',
                                          'joint_policy': 'transforms conjugated by Rz(pi); axes rotated',
                                          'inertia_policy': 'I_new = S I_source S^T; ixz and iyz negate',
                                          'base_to_drive_axle_x_m': 0.25591, 'footprint_to_base_x_m': -0.25591},
                  'limitations': inspected['warnings'][:1] + ['Provisional bounding boxes overapproximate geometry; wheel boxes are unsuitable for validated driving contacts.', 'Source asset reuse/license provenance is supplied by the user; redistribution rights are not inferred.'],
                  'meshes': [], 'collisions': []}
    staged = {}
    # Validate transformations before creating outputs.
    for link in robot.findall('link'):
        for collision in list(link.findall('collision')):
            link.remove(collision)
        for index, visual in enumerate(link.findall('visual')):
            mesh = visual.find('geometry/mesh')
            if mesh is None:
                raise ValueError('Expected exported mesh visual: ' + link.get('name'))
            uri = mesh.get('filename')
            info = mesh_info[uri]
            if info.get('format') != 'binary_stl' or not info.get('bounds_m_assuming_urdf_units'):
                raise ValueError('Binary mesh bounds required: ' + uri)
            filename = Path(info['resolved_path']).name.lower()
            if filename in staged and staged[filename]['sha256'] != info['sha256']:
                raise ValueError('Normalized mesh filename collision: ' + filename)
            staged[filename] = info
            mesh.set('filename', 'package://igvc_description/meshes/visual/' + filename)
            bounds = info['bounds_m_assuming_urdf_units']
            scale = vector(mesh.get('scale', '1 1 1'))
            size = [abs((b-a)*s) for a, b, s in zip(bounds['min'], bounds['max'], scale)]
            if any(s <= 0 for s in size):
                raise ValueError('Degenerate bounding box: ' + uri)
            center = [(a+b)*0.5*s for a, b, s in zip(bounds['min'], bounds['max'], scale)]
            original_origin = visual.find('origin')
            origin = copy.deepcopy(original_origin) if original_origin is not None else ET.Element('origin')
            xyz, rpy = vector(origin.get('xyz', '0 0 0')), vector(origin.get('rpy', '0 0 0'))
            xyz = [a+b for a, b in zip(xyz, rotate(center, rpy))]
            origin.set('xyz', format_vector(xyz))
            origin.set('rpy', format_vector(rpy))
            collision = ET.SubElement(link, 'collision', {'name': f'provisional_bounds_{index}'})
            collision.append(origin)
            ET.SubElement(ET.SubElement(collision, 'geometry'), 'box', {'size': format_vector(size)})
            provenance['collisions'].append({'link': link.get('name'), 'source_mesh': uri,
                                            'type': 'provisional_visual_aabb', 'center_link_m': xyz, 'rpy': rpy, 'size_m': size})
    normalize_forward(robot)
    for collision in provenance['collisions']:
        collision['link'] = PHYSICAL_NAMES.get(collision['link'], collision['link'])
        collision['center_link_m'] = physical_vector(collision['center_link_m'])
    (destination / 'meshes/visual').mkdir(parents=True, exist_ok=True)
    (destination / 'urdf').mkdir(parents=True, exist_ok=True)
    for filename, info in sorted(staged.items()):
        target = destination / 'meshes/visual' / filename
        if not target.exists() or sha256(target) != info['sha256']:
            shutil.copyfile(info['resolved_path'], target)
        if sha256(target) != info['sha256']:
            raise ValueError('Copied mesh checksum mismatch: ' + filename)
        provenance['meshes'].append({'source': info['resolved_path'], 'source_reference': info['reference'],
                                     'output': 'meshes/visual/' + filename, 'sha256': info['sha256'],
                                     'triangles': info['triangles'], 'bounds_m_assuming_urdf_units': info['bounds_m_assuming_urdf_units']})
    ET.indent(robot, space='  ')
    add_lidar(robot, destination, provenance)
    add_camera(robot, destination, provenance)
    ET.indent(robot, space='  ')
    target = destination / 'urdf/r3_a.urdf.xacro'
    ET.ElementTree(robot).write(target, encoding='utf-8', xml_declaration=True)
    provenance['canonical_sha256'] = sha256(target)
    (destination / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'canonical': str(target), 'meshes': len(staged), 'triangles': sum(x['triangles'] for x in staged.values()), 'provisional_collisions': len(provenance['collisions'])}))


if __name__ == '__main__':
    main()
