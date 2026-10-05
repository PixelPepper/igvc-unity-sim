"""Freeze explicitly selected source/evidence for the September review, no secrets."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/reviews/2026-09-30/baseline'


def main():
    if OUT.exists():
        raise SystemExit('Baseline already exists; never replace an in-flight review snapshot')
    paths = {ROOT/'README.md', ROOT/'AGENTS.md'}
    for folder, patterns in {
        'tools': ['*.py'], 'tools/tests': ['*.py'],
        'tools/agents': ['offline_check.py', 'review-check.sh'],
        'ros2/src/igvc_perception': ['**/*.py', '**/*.yaml', '**/*.json'],
        'ros2/src/igvc_gps': ['**/*.py', '**/*.yaml'],
        'ros2/src/igvc_sim_bridge': ['**/*.py', '**/*.yaml'],
        'ros2/src/igvc_navigation': ['**/*.py', '**/*.yaml', '**/*.xml'],
        'fixtures/white_barrel_cap': ['*.json','*.png','*.npz'],
        'config': ['**/*.json'],
        'docs/reviews/2026-09-30': ['*.md'],
    }.items():
        for pattern in patterns:
            paths.update(p for p in (ROOT/folder).glob(pattern) if p.is_file())
    for name in ('PROJECT_GUIDE.md','FILE_INDEX.md','NAVIGATION_INVESTIGATION.md','RUNBOOK.md'):
        paths.add(ROOT/'docs'/name)
    for name in ('directed-sweep-recovery-diagnosis.json',
                 'oriented-entry-execution-diagnosis.json',
                 'oriented-entry-planner-diagnosis.json',
                 'oriented-entry-paint-truth.json',
                 'checked-path-rpp.yaml','rpp-short-lookahead.yaml',
                 'directed-sweep-decisions/00089.json.gz',
                 'oriented-entry-decisions/00131.json.gz'):
        paths.add(ROOT/'artifacts/checks'/name)
    trials=[]
    for name in ('progress-recovery','checked-path','rpp-path','rpp-entry',
                 'directed-sweep','mppi-directed','oriented-entry','short-lookahead'):
        run_path=ROOT/f'artifacts/checks/{name}-run.json'
        audit_path=ROOT/f'artifacts/checks/{name}-audit.json'
        if not run_path.exists():continue
        run=json.loads(run_path.read_text())
        row={'name':name,'run_sha256':hashlib.sha256(run_path.read_bytes()).hexdigest(),
             'result':{k:run.get(k) for k in ('status','reason','completed_destinations',
                'elapsed_wall_s','requested_speed_mps','path_execution','guidance_memory','source_sha256')}}
        if audit_path.exists():
            a=json.loads(audit_path.read_text())
            row['audit']={k:a.get(k) for k in ('passed','checks','minimum','maximum_interval_speed_mps')}
        trials.append(row)
    OUT.mkdir(parents=True)
    missing=[]
    for src in sorted(paths):
        if not src.exists():missing.append(src.relative_to(ROOT).as_posix());continue
        if src.is_symlink() or not src.resolve().is_relative_to(ROOT):
            raise SystemExit('Unexpected source link or escaped path')
        dst=OUT/src.relative_to(ROOT);dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(src,dst)
    (OUT/'trial-summary.json').write_text(json.dumps({'trials':trials},indent=2)+'\n')
    def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
    manifest={'schema_version':1,'git_head':git('rev-parse','HEAD'),
        'branch':git('branch','--show-current'),'working_tree_dirty':bool(git('status','--porcelain')),
        'missing_optional_files':missing,'files':{p.relative_to(OUT).as_posix():
            hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.rglob('*')) if p.is_file()}}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'baseline':str(OUT),'files':len(manifest['files']),
        'manifest_sha256':hashlib.sha256((OUT/'manifest.json').read_bytes()).hexdigest(),
        'missing_optional_files':missing}))

if __name__=='__main__':main()
