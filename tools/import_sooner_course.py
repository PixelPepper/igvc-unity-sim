#!/usr/bin/env python3
"""Stage a local environment-only Sooner AutoNav scene without vendor code."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
PIN = '0298b11c4f469404d08b37ad98431cdab6e02818'
BARREL = 'b65e5813885621a47b96e74eaae29dd0'
GUID = re.compile(r'guid:\s*([a-f0-9]{32})')
DOCUMENT = re.compile(r'^--- !u!(\d+) &(-?\d+)(?: stripped)?\s*$', re.M)
ALLOWED = {'.mat', '.asset', '.fbx', '.obj', '.png', '.jpg', '.jpeg', '.tga', '.tif', '.tiff', '.exr', '.psd'}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def documents(text):
    matches = list(DOCUMENT.finditer(text))
    return [(int(m[1]), int(m[2]), text[m.start():matches[i+1].start() if i+1 < len(matches) else len(text)])
            for i, m in enumerate(matches)]


def local_reference(text, key):
    match = re.search(r'\b'+re.escape(key)+r':\s*\{fileID:\s*(-?\d+)\}', text)
    return int(match[1]) if match else None


def clean_scene(text):
    docs = documents(text)
    remove, removed_prefabs = set(), set()
    camera_objects = set()
    for kind, identity, body in docs:
        if kind == 114:
            remove.add(identity)
        if kind in (20, 81):
            camera_objects.add(local_reference(body, 'm_GameObject'))
        if kind == 1001:
            match = re.search(r'm_SourcePrefab:.*?guid:\s*([a-f0-9]{32})', body)
            if not match or match[1] != BARREL:
                remove.add(identity)
                removed_prefabs.add(identity)
    for kind, identity, body in docs:
        if identity in camera_objects or local_reference(body, 'm_GameObject') in camera_objects:
            remove.add(identity)
        if local_reference(body, 'm_PrefabInstance') in removed_prefabs:
            remove.add(identity)
    # Remove children of removed native transforms, not merely their roots.
    changed = True
    while changed:
        changed = False
        for kind, identity, body in docs:
            if identity in remove:
                continue
            if local_reference(body, 'm_Father') in remove or local_reference(body, 'm_GameObject') in remove:
                remove.add(identity)
                obj = local_reference(body, 'm_GameObject')
                if obj:
                    remove.add(obj)
                changed = True
    kept = []
    for kind, identity, body in docs:
        if identity in remove:
            continue
        # Remove component, hierarchy-child and SceneRoots list entries.
        lines = []
        for line in body.splitlines(keepends=True):
            ref = re.search(r'^\s*- (?:component: )?\{fileID: (-?\d+)\}\s*$', line)
            if ref and int(ref[1]) in remove:
                continue
            line = re.sub(r'\{fileID:\s*(-?\d+)\}',
                          lambda m: '{fileID: 0}' if int(m[1]) in remove else m[0], line)
            lines.append(line)
        kept.append(''.join(lines))
    output = text[:DOCUMENT.search(text).start()] + ''.join(kept)
    if any(kind == 114 for kind, _, _ in documents(output)):
        raise ValueError('MonoBehaviour survived stripping')
    kept_ids = {identity for _, identity, _ in documents(output)}
    local_ids = {int(value) for value in re.findall(r'\{fileID:\s*(-?\d+)\}', output)} - {0}
    if local_ids - kept_ids:
        raise ValueError('Dangling scene references: ' + str(sorted(local_ids - kept_ids)))
    source_inline = {identity: body for kind, identity, body in docs if kind == 43}
    output_inline = {identity: body for kind, identity, body in documents(output) if kind == 43}
    if source_inline != output_inline:
        raise ValueError('Inline baked mesh documents changed')
    return output, {'removed_document_ids': sorted(remove), 'removed_prefab_instances': sorted(removed_prefabs),
                    'retained_inline_meshes': len(output_inline),
                    'retained_barrel_instances': sum(kind == 1001 for kind, _, _ in documents(output))}


def main():
    source = ROOT / 'artifacts/vendor/scr_simulator'
    assets = source / 'Assets'
    output = ROOT / 'unity/IGVCSim/Assets/IGVC/External/SoonerAutoNav'
    actual = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != PIN:
        raise ValueError('Sooner source commit differs from inspected pin')
    index = {}
    for meta in assets.rglob('*.meta'):
        match = re.search(r'^guid:\s*([a-f0-9]{32})', meta.read_text(errors='strict'), re.M)
        if match:
            if match[1] in index:
                raise ValueError('Duplicate source GUID: ' + match[1])
            index[match[1]] = Path(str(meta)[:-5])
    scene = assets / 'Scenes/Maps/IGVC_2026_AutoNav.unity'
    adapted, changes = clean_scene(scene.read_text())
    missing_marker = '{fileID: -876546973899608171, guid: 2476a2d151e824143af40dce1fc93a12, type: 3}'
    if adapted.count(missing_marker) != 1:
        raise ValueError('Inspected missing Cylinder material reference changed')
    adapted = adapted.replace(missing_marker, '{fileID: 10303, guid: 0000000000000000f000000000000000, type: 0}')
    changes['explicit_missing_material_fallback'] = {
        'object': '#Environment/Cylinder', 'source_guid': '2476a2d151e824143af40dce1fc93a12',
        'replacement': 'Unity built-in Default-Material (10303)', 'geometry_preserved': True}
    required, seen, omitted_shaders, adapted_materials = {}, set(), set(), {}

    def dependencies(text, origin):
        shaders = set(re.findall(r'm_Shader:.*?guid:\s*([a-f0-9]{32})', text))
        for guid in GUID.findall(text):
            if guid.startswith('0000000000000000'):
                continue  # Unity built-in resource GUIDs.
            if guid in shaders:
                omitted_shaders.add(guid)
                continue  # Integrator converts materials to built-in shaders.
            if guid in seen:
                continue
            seen.add(guid)
            path = index.get(guid)
            if path is None or not path.is_file():
                raise ValueError(f'Unknown required dependency {guid} in {origin}')
            if path.suffix.lower() not in ALLOWED:
                raise ValueError('Forbidden dependency type: ' + str(path))
            meta = Path(str(path)+'.meta')
            metadata = meta.read_text()
            if 'ScriptedImporter:' in metadata:
                raise ValueError('Custom importer dependency rejected: ' + str(path))
            required[guid] = path
            dependencies(metadata, str(meta))
            if path.suffix.lower() in {'.mat', '.asset'}:
                content = path.read_text()
                if any(kind == 114 for kind, _, _ in documents(content)):
                    if path.suffix.lower() != '.mat':
                        raise ValueError('Scriptable/code asset rejected: ' + str(path))
                    # URP editor material version subassets are MonoBehaviours too.
                    content = content[:DOCUMENT.search(content).start()] + ''.join(
                        body for kind, _, body in documents(content) if kind != 114)
                    adapted_materials[path] = content
                dependencies(content, str(path))

    dependencies(adapted, str(scene))
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for guid, path in sorted(required.items()):
        target = output / 'Dependencies' / path.relative_to(assets)
        target.parent.mkdir(parents=True, exist_ok=True)
        for item, destination in [(path, target), (Path(str(path)+'.meta'), Path(str(target)+'.meta'))]:
            if item in adapted_materials:
                destination.write_text(adapted_materials[item], encoding='utf-8', newline='\n')
            else:
                shutil.copyfile(item, destination)
            records.append({'source': str(item.relative_to(source)), 'output': str(destination.relative_to(output)),
                            'source_sha256': digest(item), 'output_sha256': digest(destination), 'guid': guid,
                            'stripped_material_editor_subassets': item in adapted_materials})
    scene_target = output / 'IGVC_2026_AutoNav.unity'
    scene_target.write_text(adapted, encoding='utf-8', newline='\n')
    manifest = {'source_commit': PIN, 'source_repository': 'https://github.com/SoonerRobotics/scr_simulator',
                'source_scene': str(scene.relative_to(source)), 'source_scene_sha256': digest(scene),
                'adapted_scene_sha256': digest(scene_target), 'adaptations': changes,
                'pending_shader_conversion_guids': sorted(omitted_shaders), 'files': records,
                'scene_meta': 'Not copied; Unity creates a new scene GUID',
                'limits': 'Local user-requested import only; no source license detected. No 2027 compliance claim. Shader conversion and Unity visual validation pending.'}
    (output / 'import-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({'scene': str(scene_target), 'dependencies': len(required), 'adaptations': changes,
                      'pending_shader_conversion': sorted(omitted_shaders)}))


if __name__ == '__main__':
    main()
