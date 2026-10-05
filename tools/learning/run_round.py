#!/usr/bin/env python3
"""One DAgger-style learning round: the current student generates the data that teaches the next.

    python3 tools/learning/run_round.py --round N [--instances 4] [--seeds K] [--repeats R] [--dry-run]

Steps (each resumable; state in artifacts/learning/rounds/round-N/state.json; a step is
skipped when its outputs exist and its input hash is unchanged; ``--force STEP`` reruns it):

  plan     K never-used seeds (artifacts/learning/rounds/seed-registry.json), difficulties
           normal/hard/easy, R repeats; settings = accepted defaults + the promoted weights
           (route_weight / corridor_weight from artifacts/learning/models/current/manifest.json,
           0 when absent). Frozen once collect has finished.
  collect  tools/parallel_batch.py <plan> --instances N  (LIVE simulators)
  replay   build_dataset.py replay over the round's run folders (fraction .5, 10 jobs)
  label    Reference Lab teacher labels (dotnet via powershell.exe), idempotent per run
  build    build_dataset.py build --kind route|corridor over ALL rounds' labelled runs
  train    train_scorer.py --kind route|corridor --group-by course
  gate     round_gate.py: new vs promoted vs heuristic on the same course-held-out folds;
           promote into artifacts/learning/models/current/ only when the gate passes
  report   round-N/report.md + report.json

Corridor build/train runs only when both tools accept ``--kind`` (detected from --help).
``--from-existing round0`` imports data round 0 (artifacts/learning/data-round-0 and the
labelled runs in artifacts/learning/replayed) in place of steps plan..label.
``--dry-run`` prints every command and writes nothing.
"""
import argparse
from collections import Counter
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from round_gate import WEIGHTS  # noqa: E402

STEPS = ('plan', 'collect', 'replay', 'label', 'build', 'train', 'gate', 'report')
KINDS = ('route', 'corridor')
DIFFICULTIES = ('normal', 'hard', 'easy')
WEIGHT_KEYS = {'route': 'route_weight', 'corridor': 'corridor_weight'}
RUN_NAME = re.compile(r'[A-Za-z0-9_.-]+')
LATCH_PREFIX = 'Autonomy gate stopped'
MANIFEST_SCHEMA = 'igvc-learning-models/1'
# Seeds used before the round tool existed (data round 0 and earlier live tests).
KNOWN_SEEDS = {**{s: dict(round=0, source='data round 0') for s in range(2101, 2121)},
               **{s: dict(round=None, source='earlier live tests') for s in (2027, 2031, 2032, 2033, 2034, 2035)}}


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:16]


def file_sha(path):
    from round_gate import sha256
    return sha256(path)


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, default=str) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


# ---------------------------------------------------------------- seeds and plan

def load_registry(path):
    registry = read_json(path) or dict(schema_version=1, seeds={})
    for seed, info in KNOWN_SEEDS.items():
        registry['seeds'].setdefault(str(seed), dict(info))
    return registry


def choose_seeds(registry, round_n, count):
    """Seeds already registered to this round first, then the next never-used ones."""
    seeds = registry['seeds']
    own = sorted(int(s) for s, info in seeds.items() if info.get('round') == round_n
                 and info.get('source') == 'run_round')
    chosen = own[:count]
    candidate = max(int(s) for s in seeds) + 1 if seeds else 2121
    while len(chosen) < count:
        if str(candidate) not in seeds:
            chosen.append(candidate)
        candidate += 1
    return chosen


def register(registry, seeds, round_n):
    for seed in seeds:
        info = registry['seeds'].setdefault(str(seed), dict(round=round_n, source='run_round', registered=now()))
        if info.get('round') != round_n or info.get('source') != 'run_round':
            raise ValueError(f'Seed {seed} is already used ({info})')
    return registry


def current_manifest(models_dir):
    return read_json(Path(models_dir) / 'manifest.json')


def current_weights(manifest):
    """Live weights for plans. A kind under manifest['live_veto'] runs at 0 regardless of offline gates:
    offline teacher agreement did not transfer live for it, and only a person lifts a veto after a
    winning live A/B (docs/LEARNING_PLAN.md)."""
    weights = {}
    vetoed = (manifest or {}).get('live_veto') or {}
    for kind, key in WEIGHT_KEYS.items():
        model = ((manifest or {}).get('models') or {}).get(kind) or {}
        weights[key] = 0. if kind in vetoed else float(model.get('weight') or 0.)
    return weights


def check_settings(settings, validator=None):
    """Validate against sandbox_profile; tolerate the two weight keys while the profile lacks them.

    Returns (ok_for_live_runs, warning)."""
    if validator is None:
        from sandbox_profile import validate_settings as validator
    try:
        validator(settings)
        return True, None
    except ValueError as exc:
        stripped = {k: v for k, v in settings.items() if k not in WEIGHT_KEYS.values()}
        validator(stripped)  # anything else wrong is a real error
        return False, f'sandbox_profile rejects {sorted(set(settings) - set(stripped))} ({exc}); ' \
                      'live collection needs the integrator\'s route_weight/corridor_weight settings'


def make_plan(seeds, repeats, settings, timeout=720):
    """Batch-plan v1. Repeats are interleaved so a seed's runs are spread over the batch."""
    trials = [dict(arm='baseline', seed=seed, difficulty=DIFFICULTIES[i % len(DIFFICULTIES)], settings=dict(settings))
              for _ in range(repeats) for i, seed in enumerate(seeds)]
    return dict(schema_version=1, trial_timeout_s=timeout, trials=trials)


# ---------------------------------------------------------------- run statistics

def batch_stats(report):
    rows = [r for r in (report or {}).get('rows', []) if not r.get('infrastructure_retry')]
    # Group by the reason's head; the parenthesised tail carries per-run numbers.
    reasons = Counter((r.get('reason') or ('completed' if r.get('completed') == 6 else r.get('state') or 'unknown'))
                      .split(' (')[0] for r in rows)
    return dict(trials=len(rows), six_of_six=sum(r.get('completed') == 6 for r in rows),
                audit_passed=sum(bool(r.get('audit_passed')) for r in rows),
                perception_latch=sum((r.get('reason') or '').startswith(LATCH_PREFIX) for r in rows),
                infrastructure_retries=sum(bool(r.get('infrastructure_retry')) for r in (report or {}).get('rows', [])),
                failure_reasons=dict(reasons.most_common()))


def run_dirs(report, root):
    """Run folders of a batch report that hold decision snapshots (instance folder first)."""
    found = []
    for row in (report or {}).get('rows', []):
        name = row.get('run')
        if not name:
            continue
        candidates = ([root / f"artifacts/sandbox-instance-{row['instance']}/runs/{name}"] if row.get('instance') else [])
        candidates += sorted(root.glob(f'artifacts/sandbox-instance-*/runs/{name}')) + [root / f'artifacts/sandbox/runs/{name}']
        for path in candidates:
            if path.is_dir() and any((path / 'decisions').glob('*.json.gz')):
                if path not in found:
                    found.append(path)
                break
    return found


# ---------------------------------------------------------------- the round

class Round:
    def __init__(self, args, root=REPO, runner=None, validator=None, kind_support=None):
        self.args, self.root = args, Path(root)
        self.rounds = self.root / 'artifacts/learning/rounds'
        self.dir = self.rounds / f'round-{args.round}'
        self.models_dir = Path(args.models_dir) if args.models_dir else self.root / 'artifacts/learning/models/current'
        self.replayed = self.root / 'artifacts/learning/replayed'
        self.labels = self.root / 'artifacts/learning/labels-replayed'
        self.runner = runner or self._run
        self.validator = validator
        self._kind_support = kind_support
        self.state = read_json(self.dir / 'state.json') or dict(round=args.round, steps={})
        self.python = sys.executable or 'python3'

    # -- infrastructure
    def log(self, text):
        print(text, flush=True)

    def _run(self, argv, log=None):
        if log is None:
            subprocess.run([str(a) for a in argv], cwd=self.root, check=True)
            return
        Path(log).parent.mkdir(parents=True, exist_ok=True)
        with Path(log).open('w', encoding='utf-8') as stream:
            code = subprocess.run([str(a) for a in argv], cwd=self.root, stdout=stream, stderr=subprocess.STDOUT).returncode
        if code:
            raise SystemExit(f'Command failed ({code}); see {log}')

    def command(self, argv, log=None):
        """Print and run one command; ``log`` (a name under round-N/logs/) captures its output."""
        shown = [str(a) for a in argv]
        if len(shown) > 24:
            shown = shown[:20] + [f'... ({len(shown) - 22} more)'] + shown[-2:]
        self.log('  $ ' + ' '.join(shlex.quote(a) for a in shown))
        if not self.args.dry_run:
            self.runner(argv, self.dir / 'logs' / log if log else None)

    def rel(self, path):
        try:
            return Path(path).resolve().relative_to(self.root.resolve()).as_posix()
        except ValueError:
            return str(path)

    def save(self):
        if not self.args.dry_run:
            write_json(self.dir / 'state.json', self.state)

    def step(self, name, inputs, outputs_ok, action):
        record = self.state['steps'].get(name)
        key = digest(inputs)
        forced = name in self.args.force or name.split('_')[0] in self.args.force
        if (not forced and record and record.get('status') in ('done', 'imported')
                and (record.get('status') == 'imported' or record.get('input_hash') == key) and outputs_ok(record)):
            self.log(f'[{name}] up to date ({record["status"]}); skipped')
            return record
        self.log(f'[{name}] running' + (' (dry run)' if self.args.dry_run else ''))
        result = action() or {}
        record = dict(status='dry-run' if self.args.dry_run else 'done', input_hash=key, finished=now(), **result)
        if not self.args.dry_run:
            self.state['steps'][name] = record
            self.save()
        return record

    def done(self, name):
        record = self.state['steps'].get(name) or {}
        return record.get('status') in ('done', 'imported')

    def kind_support(self):
        if self._kind_support is None:
            support = {}
            for tool, argv in (('build', [self.python, HERE / 'build_dataset.py', 'build', '--help']),
                               ('train', [self.python, HERE / 'train_scorer.py', '--help'])):
                try:
                    support[tool] = '--kind' in subprocess.run([str(a) for a in argv], capture_output=True,
                                                               text=True, cwd=self.root).stdout
                except OSError:
                    support[tool] = False
            self._kind_support = support
        return self._kind_support

    def kinds(self):
        support = self.kind_support()
        return [k for k in KINDS if k == 'route' or (support.get('build') and support.get('train'))]

    # -- step 1
    def plan(self):
        if self.args.from_existing:
            return self.import_round0()
        registry_path = self.rounds / 'seed-registry.json'
        manifest = current_manifest(self.models_dir)
        settings = dict(json.loads(self.args.settings) if self.args.settings else {}, **current_weights(manifest))
        inputs = dict(round=self.args.round, seeds=self.args.seeds, repeats=self.args.repeats, settings=settings,
                      timeout=self.args.trial_timeout)
        plan_path = self.dir / 'plan.json'
        if self.done('collect') and plan_path.exists() and 'plan' not in self.args.force:
            if self.state['steps']['plan'].get('input_hash') != digest(inputs):
                self.log('[plan] inputs changed (e.g. a newer promoted model) but data was already collected; plan frozen')
            else:
                self.log('[plan] up to date; skipped')
            return self.state['steps']['plan']

        def action():
            registry = load_registry(registry_path)
            seeds = choose_seeds(registry, self.args.round, self.args.seeds)
            ok, warning = check_settings(settings, self.validator)
            plan = make_plan(seeds, self.args.repeats, settings, self.args.trial_timeout)
            self.log(f'  seeds {seeds}; {len(plan["trials"])} trials; settings {settings}')
            if warning:
                self.log('  WARNING: ' + warning)
            if not self.args.dry_run:
                write_json(registry_path, register(registry, seeds, self.args.round))
                write_json(plan_path, plan)
            else:
                self.log('  plan (not written): ' + json.dumps(plan['trials'][0]) + ' ...')
            return dict(plan=self.rel(plan_path), seeds=seeds, settings=settings, live_settings_ok=ok,
                        warning=warning, plan_sha256=None if self.args.dry_run else file_sha(plan_path))
        return self.step('plan', inputs, lambda r: plan_path.exists(), action)

    def import_round0(self):
        source = self.root / 'artifacts/learning/data-round-0'
        plan = read_json(source / 'plan.json')
        report = read_json(source / 'batch-report.json')
        if plan is None or report is None:
            raise SystemExit(f'--from-existing round0 needs {source}/plan.json and batch-report.json')
        labelled = sorted(p.parent.name for p in self.labels.glob('*/labels.jsonl')
                          if (self.replayed / p.parent.name / 'decisions/outcomes.jsonl').exists())
        self.log(f'[import] data round 0: {len(report["rows"])} batch rows, {len(labelled)} labelled replayed runs')
        if self.args.dry_run:
            return
        registry_path = self.rounds / 'seed-registry.json'
        write_json(registry_path, load_registry(registry_path))
        self.dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / 'plan.json', self.dir / 'plan.json')
        stamp = dict(status='imported', finished=now(), source=self.rel(source))
        self.state['steps'].update(
            plan=dict(stamp, plan=self.rel(self.dir / 'plan.json'), seeds=sorted({t['seed'] for t in plan['trials']}),
                      settings={}),
            collect=dict(stamp, batch_report=self.rel(source / 'batch-report.json')),
            replay=dict(stamp, replayed_runs=labelled),
            label=dict(stamp, labelled_runs=labelled, missing=[]))
        self.state['data_runs'] = labelled
        self.save()

    # -- step 2
    def collect(self):
        plan_path = self.dir / 'plan.json'
        report_path = self.dir / 'batch-report.json'
        plan_record = self.state['steps'].get('plan') or {}

        def action():
            if not self.args.dry_run and not plan_record.get('live_settings_ok', True):
                raise SystemExit('Refusing live collection: ' + str(plan_record.get('warning')))
            self.command([self.python, self.root / 'tools/parallel_batch.py', plan_path, '--instances', self.args.instances])
            if self.args.dry_run:
                return {}
            return dict(batch_report=self.rel(report_path), stats=batch_stats(read_json(report_path)))
        inputs = dict(plan=plan_record.get('plan_sha256'), instances=self.args.instances)
        return self.step('collect', inputs, lambda r: (self.root / r.get('batch_report', '\0')).exists(), action)

    def batch_report(self):
        record = self.state['steps'].get('collect') or {}
        return read_json(self.root / record['batch_report']) if record.get('batch_report') else None

    # -- step 3
    def replay(self):
        dirs = run_dirs(self.batch_report(), self.root)
        names = [d.name for d in dirs]
        out = lambda name: self.replayed / name / 'decisions/outcomes.jsonl'

        def action():
            pending = [d for d in dirs if not out(d.name).exists()]
            if pending or self.args.dry_run:
                self.command(['bash', self.root / 'tools/run_ros.sh', 'python3', HERE / 'build_dataset.py', 'replay',
                              '--runs', *(pending or ['<run dirs from batch-report.json>']),
                              '--fraction', self.args.fraction, '--jobs', self.args.jobs], 'replay.log')
            return dict(replayed_runs=[n for n in names if out(n).exists()], source_runs=len(dirs))
        return self.step('replay', dict(runs=names, fraction=self.args.fraction),
                         lambda r: all(out(n).exists() for n in r.get('replayed_runs', [])), action)

    # -- step 4
    def label_command(self, runs):
        """One PowerShell script: build the Reference Lab once, then label ONLY ``runs``."""
        bad = [r for r in runs if not RUN_NAME.fullmatch(r)]
        if bad:
            raise ValueError(f'Unexpected run names: {bad}')
        if os.name == 'nt':
            win = str(self.root)
        else:
            try:
                win = subprocess.run(['wslpath', '-w', str(self.root)], capture_output=True, text=True,
                                     check=True).stdout.strip()
            except (OSError, subprocess.CalledProcessError):
                win = str(self.root)
        project = 'tools/reference_lab'
        lines = [f"Set-Location -LiteralPath '{win}'", '$failed = 0',
                 f'dotnet build -c Release {project} --nologo -v q; if ($LASTEXITCODE) {{ exit $LASTEXITCODE }}']
        lines += [f'dotnet run -c Release --no-build --project {project} -- label --run artifacts/learning/replayed/{r} '
                  f'--out artifacts/learning/labels-replayed/{r}; if ($LASTEXITCODE) {{ $failed++ }}' for r in runs]
        lines.append('exit $failed')
        return ['powershell.exe' if os.name != 'nt' else 'powershell', '-NoProfile', '-Command', '; '.join(lines)]

    def label(self):
        replayed = (self.state['steps'].get('replay') or {}).get('replayed_runs', [])
        done = lambda name: (self.labels / name / 'labels.jsonl').exists()

        def action():
            pending = [n for n in replayed if not done(n)]
            if pending or self.args.dry_run:
                self.log(f'  labelling {len(pending)} of {len(replayed)} replayed runs (the rest already have labels)')
                self.command(self.label_command(pending or ['RUN']), 'label.log')
            labelled = [n for n in replayed if done(n)]
            self.state['data_runs'] = labelled
            return dict(labelled_runs=labelled, missing=[n for n in replayed if not done(n)])
        return self.step('label', dict(runs=replayed), lambda r: all(map(done, r.get('labelled_runs', []))), action)

    # -- step 5
    def all_runs(self):
        runs = set()
        for k in range(self.args.round + 1):
            state = self.state if k == self.args.round else read_json(self.rounds / f'round-{k}/state.json') or {}
            runs.update(state.get('data_runs') or [])
        if self.args.round > 0 and not (self.rounds / 'round-0/state.json').exists() and not getattr(self, '_warned', 0):
            self._warned = 1
            self.log('  WARNING: round-0 state missing; import it with --round 0 --from-existing round0')
        return sorted(runs)

    def file_stamp(self, path):
        try:
            stat = Path(path).stat()
            return [stat.st_size, stat.st_mtime_ns]
        except OSError:
            return None

    def build(self):
        runs = self.all_runs()
        support = self.kind_support()
        records = {}
        for kind in self.kinds():
            out = self.dir / f'dataset/{kind}_candidates.jsonl'

            def action(kind=kind, out=out):
                argv = [self.python, HERE / 'build_dataset.py', 'build', '--runs', *(runs or ['<all rounds\' runs>']),
                        '--out', out] + (['--kind', kind] if support.get('build') else [])
                self.command(argv, f'build_{kind}.log')
                if self.args.dry_run:
                    return {}
                summary = read_json(out.with_suffix('.summary.json')) or {}
                return dict(dataset=self.rel(out), sha256=file_sha(out), runs=len(runs),
                            rows=summary.get('rows'), groups=summary.get('groups'),
                            runs_with_groups=summary.get('runs_with_groups'))
            inputs = dict(kind=kind, runs={n: [self.file_stamp(self.replayed / n / 'decisions/outcomes.jsonl'),
                                               self.file_stamp(self.labels / n / 'labels.jsonl')] for n in runs})
            records[kind] = self.step(f'build_{kind}', inputs, lambda r, out=out: out.exists(), action)
        return records

    # -- step 5b
    def train(self, built):
        support = self.kind_support()
        records = {}
        for kind in self.kinds():
            dataset = self.dir / f'dataset/{kind}_candidates.jsonl'
            model = self.dir / f'models/{kind}_scorer.json'
            report = self.dir / f'models/{kind}_scorer.report.json'

            def action(kind=kind, dataset=dataset, model=model, report=report):
                self.command([self.python, HERE / 'train_scorer.py', '--dataset', dataset, '--model-out', model,
                              '--report-out', report, '--group-by', 'course',
                              '--hook-weight', *[f'{w:g}' for w in WEIGHTS]]
                             + (['--kind', kind] if support.get('train') else []), f'train_{kind}.log')
                if self.args.dry_run:
                    return {}
                return dict(model=self.rel(model), sha256=file_sha(model), report=self.rel(report))
            inputs = dict(kind=kind, dataset=(built.get(kind) or {}).get('sha256'), hook=WEIGHTS, group_by='course')
            records[kind] = self.step(f'train_{kind}', inputs, lambda r, model=model: model.exists(), action)
        return records

    # -- step 6
    def gate(self, trained):
        import round_gate
        records = {}
        for kind in self.kinds():
            model = self.dir / f'models/{kind}_scorer.json'
            dataset = self.dir / f'dataset/{kind}_candidates.jsonl'
            out = self.dir / f'gate/{kind}.json'
            if self.args.dry_run:
                self.log(f'[gate_{kind}] would compare {self.rel(model)} vs '
                         f'{self.rel(self.models_dir / (kind + "_scorer.json"))} vs heuristic and promote on pass')
                continue
            manifest = current_manifest(self.models_dir) or {}
            current = (manifest.get('models') or {}).get(kind)
            new_sha = (trained.get(kind) or {}).get('sha256')
            previous = self.state['steps'].get(f'gate_{kind}')
            if current and current.get('sha256') == new_sha and previous and 'gate' not in self.args.force:
                self.log(f'[gate_{kind}] this model is already the promoted one; skipped')
                records[kind] = previous
                continue
            current_path = self.root / current['path'] if current else None
            if current_path is not None and not current_path.exists():
                raise SystemExit(f'Promoted {kind} model missing: {current_path}')

            def action(kind=kind, model=model, dataset=dataset, out=out, current=current, current_path=current_path):
                report = round_gate.gate(dataset, model, current, repo=self.root)
                write_json(out, report)
                decision = report['decision']
                self.log(f'  {kind} ({report.get("mode")}): promote={decision["promote"]} weight={decision.get("weight")}; '
                         + '; '.join(decision['reasons']))
                promoted = False
                if decision['promote'] and not self.args.no_promote:
                    self.promote(kind, model, report)
                    promoted = True
                return dict(report=self.rel(out), decision=decision, promoted=promoted,
                            overall=report.get('overall'), mode=report.get('mode'), notes=report.get('notes'),
                            new_sha256=report.get('new_sha256'),
                            current_sha256=report.get('current_sha256'))
            inputs = dict(model=new_sha, dataset=file_sha(dataset), current=(current or {}).get('sha256'),
                          no_promote=self.args.no_promote)
            records[kind] = self.step(f'gate_{kind}', inputs, lambda r, out=out: out.exists(), action)
        return records

    def promote(self, kind, model, report):
        self.models_dir.mkdir(parents=True, exist_ok=True)
        target = self.models_dir / f'{kind}_scorer.json'
        shutil.copy2(model, target)
        manifest = current_manifest(self.models_dir) or dict(schema=MANIFEST_SCHEMA, models={})
        manifest.setdefault('models', {})[kind] = dict(
            path=self.rel(target), sha256=file_sha(target), weight=report['decision']['weight'], kind=kind,
            recipe=report['new_recipe'], gate_mode=report['mode'],
            round=self.args.round, promoted=now(), source=self.rel(model), gate_report=self.rel(self.dir / f'gate/{kind}.json'),
            metrics=dict(overall=report['overall'], hook=report['hook'],
                         new_vs_current=report.get('new_vs_current'), new_vs_heuristic=report['new_vs_heuristic']),
            data_runs=sorted({r for r in self.all_runs()}))
        manifest.update(schema=MANIFEST_SCHEMA, updated_round=self.args.round, updated=now(),
                        **current_weights(manifest))
        write_json(self.models_dir / 'manifest.json', manifest)
        self.log(f'  promoted {kind} -> {self.rel(target)}')

    # -- step 7
    def report(self, built, trained, gated):
        stats = batch_stats(self.batch_report())
        cv = {}
        for kind, record in trained.items():
            report = read_json(self.root / record['report']) if record.get('report') else None
            if report:
                cv[kind] = {k: v for k, v in (report.get('cross_validation') or {}).items() if k != 'per_run'}
        plan_record = self.state['steps'].get('plan') or {}
        summary = dict(round=self.args.round, generated=now(), plan=plan_record.get('plan'),
                       seeds=plan_record.get('seeds'), settings=plan_record.get('settings'), runs=stats,
                       data_runs_this_round=len(self.state.get('data_runs') or []), data_runs_all_rounds=len(self.all_runs()),
                       label_missing=(self.state['steps'].get('label') or {}).get('missing'),
                       datasets={k: {f: v.get(f) for f in ('dataset', 'rows', 'groups', 'runs_with_groups', 'sha256')}
                                 for k, v in built.items()},
                       train_cv=cv, gate={k: {f: v.get(f) for f in ('report', 'decision', 'promoted', 'overall', 'mode', 'notes',
                                                                     'new_sha256', 'current_sha256')}
                                          for k, v in gated.items()},
                       skipped_kinds=[k for k in KINDS if k not in self.kinds()],
                       manifest=current_manifest(self.models_dir))
        if self.args.dry_run:
            self.log(f'[report] would write {self.rel(self.dir / "report.md")} and report.json')
            return summary
        write_json(self.dir / 'report.json', summary)
        (self.dir / 'report.md').write_text(render_markdown(summary, self.root, self.dir), encoding='utf-8')
        self.state['steps']['report'] = dict(status='done', finished=now(), report=self.rel(self.dir / 'report.md'))
        self.save()
        self.log(f'[report] {self.rel(self.dir / "report.md")}')
        return summary

    def run(self):
        self.log(f'Learning round {self.args.round} -> {self.rel(self.dir)}'
                 + (' (DRY RUN: nothing is executed or written)' if self.args.dry_run else ''))
        self.plan()
        if not self.args.from_existing:
            self.collect()
            self.replay()
            self.label()
        built = self.build()
        trained = self.train(built)
        gated = self.gate(trained)
        return self.report(built, trained, gated)


def _pct(part, whole):
    return f'{part}/{whole}' + (f' ({100 * part / whole:.0f}%)' if whole else '')


def render_markdown(s, root, folder):
    lines = [f"# Learning round {s['round']}", '', f"Generated {s['generated']}. Plan: `{s['plan']}`; "
             f"seeds {s['seeds']}; settings `{json.dumps(s['settings'])}`.", '', '## Runs', '']
    r = s['runs']
    lines += [f"- Trials (excluding infrastructure retries): {r['trials']} (retries: {r['infrastructure_retries']})",
              f"- 6/6: {_pct(r['six_of_six'], r['trials'])}; audit passed: {_pct(r['audit_passed'], r['trials'])}",
              f"- Perception latch (`{LATCH_PREFIX}...`, decisions still used): {r['perception_latch']}",
              f"- Labelled runs this round: {s['data_runs_this_round']}; all rounds: {s['data_runs_all_rounds']}"
              + (f"; labels missing: {len(s['label_missing'])}" if s.get('label_missing') else ''), '',
              '| Outcome / failure reason | Runs |', '| --- | --- |']
    lines += [f"| {reason[:90].replace('|', '/')} | {n} |" for reason, n in r['failure_reasons'].items()]
    lines += ['', '## Datasets', '', '| Kind | Rows | Decisions | Runs with decisions |', '| --- | --- | --- | --- |']
    lines += [f"| {k} | {v.get('rows')} | {v.get('groups')} | {v.get('runs_with_groups')} |" for k, v in s['datasets'].items()]
    if s['skipped_kinds']:
        lines += ['', f"Skipped kinds (tools lack `--kind`): {', '.join(s['skipped_kinds'])}."]
    for kind, g in s['gate'].items():
        report = read_json(root / g['report']) if g.get('report') else None
        lines += ['', f'## Gate: {kind}', '']
        if not report or 'overall' not in report:
            lines.append('No gate report.')
            continue
        arms = [a for a in ('new', 'current', 'heuristic') if a in report['overall']]
        lines += [f"Course-held-out CV: {report['folds']} folds over {report['courses']} courses, "
                  f"{report['decisions']} decisions compared. Gate mode: **{report.get('mode')}**"
                  + (f"; {100 * report['current_seen_fraction']:.0f}% of all decisions come from courses the "
                     'current model trained on' if report.get('current_seen_fraction') is not None else '') + '.']
        lines += [f'- {note}' for note in report.get('notes') or []]
        lines += ['',
                  '| Fold | ' + ' | '.join(f'{a} top-1 | {a} regret (m)' for a in arms) + ' |',
                  '| --- |' + ' --- | --- |' * len(arms)]
        for entry in report['per_fold'] + [dict(report['overall'], fold='all')]:
            lines.append(f"| {entry['fold']} | " + ' | '.join(f"{entry[a]['top1']} | {entry[a]['mean_regret_m']}" for a in arms) + ' |')
        for name in ('new_vs_current', 'new_vs_heuristic'):
            if name in report:
                t = report[name]
                lines.append(f"\n{name.replace('_', ' ')}: picks differ {t['picks_differ']}, better/worse "
                             f"{t['wins']}/{t['losses']}, sign test p={t['sign_test_p']:.3g}")
        lines += ['', 'Hook-form weight curve (score + w * prediction; a weight whose top-1 is below the heuristic '
                  f"({report['overall']['heuristic']['top1']}) is never chosen):", '',
                  '| Hook weight | top-1 | regret (m) | better/worse vs heuristic |', '| --- | --- | --- | --- |']
        lines += [f"| {w} | {h['top1']} | {h['mean_regret_m']} | {h['wins']}/{h['losses']} |" for w, h in report['hook'].items()]
        d = g['decision']
        verdict = 'PROMOTED' if g.get('promoted') else ('passes gate (not promoted: --no-promote)' if d['promote'] else 'NOT promoted')
        lines += ['', f"**Decision: {verdict}**, weight {d.get('weight')} (recommended {d.get('recommended_weight')}).", '']
        lines += [f'- {reason}' for reason in d['reasons']]
        lines += ['', f"New model sha256 `{g.get('new_sha256')}`; current `{g.get('current_sha256')}`."]
    manifest = s.get('manifest')
    lines += ['', '## Promoted models', '']
    if manifest:
        for kind, m in manifest.get('models', {}).items():
            lines.append(f"- {kind}: `{m['path']}` sha256 `{m['sha256']}`, weight {m['weight']}, round {m['round']}")
    else:
        lines.append('None (weights 0 = round-0 behaviour).')
    lines += ['', 'Offline teacher-agreement metrics only; not live navigation or hardware evidence.', '']
    return '\n'.join(lines)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--round', type=int, required=True)
    parser.add_argument('--instances', type=int, default=4, help='4 for training data (latched runs flagged)')
    parser.add_argument('--seeds', type=int, default=20, help='fresh seeds to plan')
    parser.add_argument('--repeats', type=int, default=3, help='runs per seed')
    parser.add_argument('--trial-timeout', type=int, default=720)
    parser.add_argument('--settings', help='JSON of extra sandbox settings (weights come from the manifest)')
    parser.add_argument('--fraction', type=float, default=.5, help='replay alternative fraction')
    parser.add_argument('--jobs', type=int, default=10)
    parser.add_argument('--models-dir', type=Path, help='promoted models (default artifacts/learning/models/current)')
    parser.add_argument('--from-existing', choices=('round0',), help='import data round 0 instead of steps plan..label')
    parser.add_argument('--no-promote', action='store_true', help='record the gate decision without promoting')
    parser.add_argument('--force', action='append', default=[], help='rerun a step (plan, collect, replay, label, '
                        'build_route, build_corridor, train_route, train_corridor, gate_route, gate_corridor, gate)')
    parser.add_argument('--dry-run', action='store_true', help='print the commands; execute and write nothing')
    args = parser.parse_args(argv)
    if args.round < 0 or args.seeds < 1 or args.repeats < 1 or not 1 <= args.instances <= 8:
        parser.error('invalid --round/--seeds/--repeats/--instances')
    if args.from_existing and args.round != 0:
        parser.error('--from-existing round0 imports round 0; use --round 0')
    return args


def main(argv=None):
    Round(parse_args(argv)).run()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
