"""Verify a trial imports the candidate perception package from its own overlay."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
overlay=Path(sys.argv[2]).resolve()
files=[]
for name in ('surface_projection','depth_node','lane_node'):
    source=Path(sys.argv[1]).resolve()/f'ros2/src/igvc_perception/igvc_perception/{name}.py'
    installed=Path(importlib.util.find_spec('igvc_perception.'+name).origin).resolve()
    source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    installed_hash=hashlib.sha256(installed.read_bytes()).hexdigest()
    files.append({'source_path':str(source),'installed_path':str(installed),
        'source_sha256':source_hash,'installed_sha256':installed_hash,
        'own_overlay':installed.is_relative_to(overlay),'content_matches':source_hash==installed_hash})
result={'files':files,'own_overlay':all(f['own_overlay'] for f in files),
        'content_matches':all(f['content_matches'] for f in files)}
print(json.dumps(result))
raise SystemExit(0 if result['own_overlay'] and result['content_matches'] else 1)
