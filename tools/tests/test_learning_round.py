"""Learning-round orchestration: seed registry, plans, promotion gate, resumable steps."""

import argparse
import json
from pathlib import Path
import random
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / 'learning'))
import round_gate  # noqa: E402
import run_round  # noqa: E402

try:
    import sklearn  # noqa: F401
    HAVE_SKLEARN = True
except ImportError:
    HAVE_SKLEARN = False

PROFILE_KEYS = {'controller', 'execution', 'speed_mps', 'inflation_m', 'clearance_weight', 'planning_budget_s',
                'lookahead_m', 'escape'}


def stub_validator(known):
    def validate(settings):
        if set(settings) - known:
            raise ValueError('Unknown sandbox setting')
        if 'speed_mps' in settings and not .1 <= settings['speed_mps'] <= 2.2:
            raise ValueError('Invalid speed_mps')
        return settings
    return validate


def synthetic_rows(runs=6, decisions=40, seed=3, noise=0.):
    """Teacher prefers larger observed clearance; the heuristic picks the lowest score."""
    rng, rows = random.Random(seed), []
    for r in range(runs):
        run = f'run-{r}'
        for d in range(decisions):
            cands = [dict(score=rng.uniform(0, 1), min_lethal_clearance_m=rng.uniform(0, 2)) for _ in range(3)]
            cost = [3 - 1.5 * c['min_lethal_clearance_m'] + rng.gauss(0, noise) for c in cands]
            best, heur = min(range(3), key=cost.__getitem__), min(range(3), key=lambda i: cands[i]['score'])
            for k, c in enumerate(cands):
                rows.append(dict(run=run, index=d, group=f'{run}:{d}', source='grid' if k == heur else 'route_alt',
                                 heuristic_choice=k == heur, features=c, teacher_cost_m=cost[k],
                                 regret_m=round(cost[k] - cost[best], 4), teacher_best=k == best,
                                 # Synthetic measured-pose rows: readers admit only measured by default.
                                 pose_source='measured', pose_reason='latency_compensation_not_applied'))
    return rows


def write_jsonl(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(''.join(json.dumps(r) + '\n' for r in rows))


def report(new, heur, current=None, test=(30, 5, 1e-6), hook=None):
    overall = dict(new=dict(decisions=100, top1=new[0], mean_regret_m=new[1]),
                   heuristic=dict(decisions=100, top1=heur[0], mean_regret_m=heur[1]))
    result = dict(overall=overall, hook=hook or {'1': dict(top1=heur[0] + .01, mean_regret_m=heur[1] - .1)})
    t = dict(picks_differ=test[0] + test[1], wins=test[0], losses=test[1], sign_test_p=test[2])
    if current:
        overall['current'] = dict(decisions=100, top1=current[0], mean_regret_m=current[1])
        result['new_vs_current'] = t
        result['new_vs_heuristic'] = dict(t, sign_test_p=1e-9)
    else:
        result['new_vs_heuristic'] = t
    return result


class SeedsAndPlan(unittest.TestCase):
    def test_registry_preloads_used_seeds_and_picks_fresh_ones(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = run_round.load_registry(Path(tmp) / 'r.json')
            for seed in (2027, 2031, 2035, 2101, 2120):
                self.assertIn(str(seed), registry['seeds'])
            registry['seeds']['2122'] = dict(round=None, source='manual')
            seeds = run_round.choose_seeds(registry, 1, 3)
            self.assertEqual(seeds, [2123, 2124, 2125])  # never below the highest used seed
            run_round.register(registry, seeds, 1)
            # Re-planning the same round reuses its seeds; another round gets new ones.
            self.assertEqual(run_round.choose_seeds(registry, 1, 3), seeds)
            self.assertEqual(run_round.choose_seeds(registry, 2, 2), [2126, 2127])
            with self.assertRaises(ValueError):
                run_round.register(registry, [2101], 1)

    def test_plan_cycles_difficulties_and_interleaves_repeats(self):
        plan = run_round.make_plan([1, 2, 3, 4], 2, dict(route_weight=1.))
        self.assertEqual(plan['schema_version'], 1)
        self.assertEqual([t['seed'] for t in plan['trials']], [1, 2, 3, 4, 1, 2, 3, 4])
        self.assertEqual([t['difficulty'] for t in plan['trials'][:4]], ['normal', 'hard', 'easy', 'normal'])
        self.assertTrue(all(t['arm'] == 'baseline' and t['settings'] == dict(route_weight=1.) for t in plan['trials']))

    def test_weight_keys_tolerated_until_profile_supports_them(self):
        settings = dict(route_weight=2., corridor_weight=0.)
        ok, warning = run_round.check_settings(settings, stub_validator(PROFILE_KEYS))
        self.assertFalse(ok)
        self.assertIn('route_weight', warning)
        self.assertEqual(run_round.check_settings(settings, stub_validator(PROFILE_KEYS | set(settings))), (True, None))
        with self.assertRaises(ValueError):  # other invalid settings are still errors
            run_round.check_settings(dict(settings, speed_mps=9.), stub_validator(PROFILE_KEYS))

    def test_weights_from_manifest_default_to_zero(self):
        self.assertEqual(run_round.current_weights(None), dict(route_weight=0., corridor_weight=0.))
        manifest = dict(models=dict(route=dict(weight=2.)))
        self.assertEqual(run_round.current_weights(manifest), dict(route_weight=2., corridor_weight=0.))

    def test_batch_stats_flag_latches_and_skip_retries(self):
        rows = [dict(completed=6, audit_passed=True), dict(completed=2, reason='Autonomy gate stopped: latched (age 0.8)'),
                dict(completed=1, reason='Autonomy gate stopped: latched (age 0.9)'),
                dict(completed=0, reason='startup', infrastructure_retry=True)]
        stats = run_round.batch_stats(dict(rows=rows))
        self.assertEqual((stats['trials'], stats['six_of_six'], stats['audit_passed'], stats['perception_latch'],
                          stats['infrastructure_retries']), (3, 1, 1, 2, 1))
        self.assertEqual(stats['failure_reasons']['Autonomy gate stopped: latched'], 2)


class LiveVeto(unittest.TestCase):
    def test_vetoed_kind_runs_at_zero_weight(self):
        manifest = dict(models=dict(route=dict(weight=8.), corridor=dict(weight=8.)),
                        live_veto=dict(corridor=dict(reason='lost live A/B')))
        self.assertEqual(run_round.current_weights(manifest), dict(route_weight=8., corridor_weight=0.))

    def test_no_veto_keeps_promoted_weights(self):
        manifest = dict(models=dict(route=dict(weight=2.), corridor=dict(weight=4.)))
        self.assertEqual(run_round.current_weights(manifest), dict(route_weight=2., corridor_weight=4.))


class Gate(unittest.TestCase):
    def test_first_promotion_is_against_the_heuristic(self):
        decision = round_gate.decide(report((.7, .2), (.55, .6)))
        self.assertTrue(decision['promote'])
        self.assertEqual((decision['versus'], decision['weight']), ('heuristic', 1.))

    def test_must_beat_current_on_regret_top1_and_sign_test(self):
        self.assertTrue(round_gate.decide(report((.7, .2), (.55, .6), current=(.7, .25)))['promote'])
        worse_top1 = round_gate.decide(report((.69, .2), (.55, .6), current=(.7, .25)))
        self.assertFalse(worse_top1['promote'])
        self.assertTrue(any('top-1' in r for r in worse_top1['reasons']))
        tie = round_gate.decide(report((.7, .25), (.55, .6), current=(.7, .25)))
        self.assertFalse(tie['promote'])  # regret must be strictly better
        weak = round_gate.decide(report((.7, .2), (.55, .6), current=(.7, .25), test=(12, 8, .5)))
        self.assertFalse(weak['promote'])
        self.assertTrue(any('sign test vs current' in r for r in weak['reasons']))

    def test_weight_never_worsens_top1_vs_heuristic(self):
        hook = {'0.5': dict(top1=.56, mean_regret_m=.5), '1': dict(top1=.57, mean_regret_m=.45),
                '2': dict(top1=.54, mean_regret_m=.30)}
        decision = round_gate.decide(report((.7, .2), (.55, .6), hook=hook))
        self.assertEqual(decision['weight'], 1.)
        unsafe = {'1': dict(top1=.5, mean_regret_m=.3)}
        self.assertFalse(round_gate.decide(report((.7, .2), (.55, .6), hook=unsafe))['promote'])

    def test_sign_test_fallback_matches_binomial(self):
        self.assertAlmostEqual(round_gate.sign_p(0, 0), 1.)
        self.assertAlmostEqual(round_gate.sign_p(9, 1), 0.021484375)

    @unittest.skipUnless(HAVE_SKLEARN, 'needs scikit-learn')
    def test_promoted_model_gets_no_advantage_on_its_own_training_courses(self):
        import train_scorer
        features = ['score', 'min_lethal_clearance_m']
        rows = synthetic_rows(noise=.8)
        with tempfile.TemporaryDirectory() as tmp:
            dataset, new = Path(tmp) / 'd.jsonl', Path(tmp) / 'new.json'
            write_jsonl(dataset, rows)
            # The promoted model was trained on EVERY course of this dataset.
            recipe = round_gate.default_recipe(features)
            fitted = round_gate.make_model(recipe).fit(round_gate._encode(rows, features),
                                                       [r['regret_m'] for r in rows])
            Path(tmp, 'current.json').write_text(json.dumps(train_scorer.export(fitted, features)))
            new.write_text(json.dumps(dict(features=features)))
            current = dict(path='current.json', recipe=recipe, data_runs=sorted({r['run'] for r in rows}))
            result = round_gate.gate(dataset, new, current, repo=Path(tmp))
            in_sample = round_gate.metrics(round_gate.picks(
                rows, round_gate.LearnedScorer(json.loads(Path(tmp, 'current.json').read_text()))
                .score([r['features'] for r in rows])))
        self.assertEqual(result['mode'], 'retrain')
        self.assertEqual(result['current_seen_fraction'], 1.)
        # Scored as exported it would look better than it generalises ...
        self.assertLess(in_sample['mean_regret_m'], result['overall']['current']['mean_regret_m'])
        # ... retrained per fold, the same recipe on the same runs is exactly the new model: a tie.
        self.assertEqual(result['overall']['current'], result['overall']['new'])
        self.assertFalse(result['decision']['promote'])

    @unittest.skipUnless(HAVE_SKLEARN, 'needs scikit-learn')
    def test_without_recipe_gate_uses_unseen_courses_or_falls_back_to_heuristic(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset = Path(tmp) / 'd.jsonl'
            write_jsonl(dataset, synthetic_rows())
            # A constant model ties everywhere and falls back to the heuristic's pick.
            Path(tmp, 'current.json').write_text(json.dumps(dict(
                schema='igvc-route-scorer/1', features=['score'], fill_value=-1., base=0., learning_rate=1., trees=[])))
            new = Path(tmp) / 'new.json'
            new.write_text(json.dumps(dict(features=['score', 'min_lethal_clearance_m'])))
            unseen = round_gate.gate(dataset, new, dict(path='current.json', data_runs=['run-0', 'run-1']), repo=Path(tmp))
            few = round_gate.gate(dataset, new, dict(path='current.json', data_runs=[f'run-{i}' for i in range(5)]),
                                  repo=Path(tmp))
        self.assertEqual((unseen['mode'], unseen['decisions'], unseen['folds']), ('unseen', 160, 5))
        self.assertEqual(unseen['overall']['current'], unseen['overall']['heuristic'])
        self.assertTrue(unseen['decision']['promote'])
        self.assertEqual(unseen['decision']['versus'], 'current')
        self.assertEqual((few['mode'], few['decisions']), ('heuristic', 240))  # only 40 unseen < 100
        self.assertNotIn('current', few['overall'])
        self.assertEqual(few['decision']['versus'], 'heuristic')
        self.assertIn('heuristic only', few['notes'][0])
        self.assertEqual(list(unseen['hook']), ['0.5', '1', '2', '4', '8'])


class FakeTools:
    """Stands in for the simulator, replay, teacher, dataset builder and trainer."""

    def __init__(self, root):
        self.root, self.calls, self.labelled = Path(root), [], []

    def __call__(self, argv, log=None):
        argv = [str(a) for a in argv]
        joined = ' '.join(argv)
        self.calls.append(argv[1] if argv[0].endswith('python3') or 'python' in argv[0] else argv[0])
        if 'parallel_batch.py' in joined:
            plan = json.loads(Path(argv[2]).read_text())
            rows = []
            for i, trial in enumerate(plan['trials']):
                run = f'run-{trial["seed"]}-{i}'
                (self.root / f'artifacts/sandbox-instance-1/runs/{run}/decisions').mkdir(parents=True)
                (self.root / f'artifacts/sandbox-instance-1/runs/{run}/decisions/000001.json.gz').write_bytes(b'')
                rows.append(dict(run=run, instance=1, completed=6 if i % 2 else 3,
                                 reason=None if i % 2 else 'Autonomy gate stopped: latched'))
            (Path(argv[2]).parent / 'batch-report.json').write_text(json.dumps(dict(rows=rows)))
        elif 'replay' in argv:
            for run in argv[argv.index('--runs') + 1:argv.index('--fraction')]:
                write_jsonl(self.root / f'artifacts/learning/replayed/{Path(run).name}/decisions/outcomes.jsonl', [{}])
        elif argv[0].startswith('powershell'):
            import re
            for run in re.findall(r'--run artifacts/learning/replayed/(\S+) ', argv[-1]):
                self.labelled.append(run)
                write_jsonl(self.root / f'artifacts/learning/labels-replayed/{run}/labels.jsonl', [{}])
        elif 'build' in argv:
            runs = argv[argv.index('--runs') + 1:argv.index('--out')]
            out = Path(argv[argv.index('--out') + 1])
            rows = [dict(r, run=runs[int(r['run'].split('-')[1]) % len(runs)], group=f"{runs[int(r['run'].split('-')[1]) % len(runs)]}:{r['index']}")
                    for r in synthetic_rows()]
            write_jsonl(out, rows)
            out.with_suffix('.summary.json').write_text(json.dumps(dict(rows=len(rows), groups=240, runs_with_groups=6)))
        elif 'train_scorer.py' in joined:
            import contextlib, io, train_scorer
            with contextlib.redirect_stdout(io.StringIO()):
                train_scorer.main(argv[2:])
        else:
            raise AssertionError(joined)


def args(**overrides):
    base = dict(round=1, instances=4, seeds=3, repeats=2, trial_timeout=720, settings=None, fraction=.5, jobs=10,
                models_dir=None, from_existing=None, no_promote=False, force=[], dry_run=False)
    return argparse.Namespace(**dict(base, **overrides))


@unittest.skipUnless(HAVE_SKLEARN, 'needs scikit-learn')
class ResumableRound(unittest.TestCase):
    def make(self, root, tools, **overrides):
        round_ = run_round.Round(args(**overrides), root=root, runner=lambda argv, log: tools(argv, log),
                                 validator=stub_validator(PROFILE_KEYS | set(run_round.WEIGHT_KEYS.values())),
                                 kind_support=dict(build=False, train=False))
        round_.log = lambda text: None
        return round_

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tools = FakeTools(tmp)
            self.make(tmp, tools, dry_run=True).run()
            self.assertEqual(tools.calls, [])
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_full_round_promotes_then_resumes_without_rework(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, tools = Path(tmp), FakeTools(tmp)
            summary = self.make(root, tools).run()
            self.assertEqual(len(tools.calls), 5)  # collect, replay, label, build, train
            self.assertEqual(summary['runs']['perception_latch'], 3)
            self.assertEqual(summary['skipped_kinds'], ['corridor'])
            manifest = json.loads((root / 'artifacts/learning/models/current/manifest.json').read_text())
            route = manifest['models']['route']
            self.assertTrue(summary['gate']['route']['promoted'])
            self.assertEqual(route['round'], 1)
            self.assertEqual(route['sha256'], round_gate.sha256(root / route['path']))
            self.assertEqual(manifest['route_weight'], route['weight'])
            self.assertEqual(len(route['data_runs']), 6)
            self.assertTrue((root / 'artifacts/learning/rounds/round-1/report.md').exists())
            registry = json.loads((root / 'artifacts/learning/rounds/seed-registry.json').read_text())
            self.assertEqual(registry['seeds']['2121']['round'], 1)

            self.assertEqual(route['path'], 'artifacts/learning/models/current/route_scorer.json')
            model = json.loads((root / route['path']).read_text())
            self.assertEqual(route['recipe']['features'], model['features'])
            self.assertTrue({'n_estimators', 'max_depth', 'learning_rate', 'seed'} <= set(route['recipe']))

            tools.calls.clear()
            self.make(root, tools).run()  # every step is up to date; the gate sees its own promotion
            self.assertEqual(tools.calls, [])

            # A run that lost its labels is the only one relabelled.
            self.assertEqual(len(tools.labelled), 6)
            lost = tools.labelled[2]
            (root / f'artifacts/learning/labels-replayed/{lost}/labels.jsonl').unlink()
            tools.labelled.clear()
            self.make(root, tools).run()
            self.assertEqual(tools.labelled, [lost])

            # The next round plans fresh seeds with the promoted weight.
            nxt = self.make(root, tools, round=2, dry_run=True)
            plan = nxt.plan()
            self.assertEqual(plan['seeds'], [2124, 2125, 2126])
            self.assertEqual(plan['settings']['route_weight'], route['weight'])


if __name__ == '__main__':
    unittest.main()
