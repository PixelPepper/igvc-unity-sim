"""Allowlisted sandbox controls and reproducible Nav2 profiles."""
import math
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULTS = dict(controller='rpp', execution='checked-path', speed_mps=.6,
                inflation_m=.3, clearance_weight=3., planning_budget_s=.5,
                lookahead_m=.65, escape='legacy', route_weight=0., corridor_weight=0.)
LIMITS = dict(speed_mps=(.1, 2.2), inflation_m=(.1, 1.5),
              clearance_weight=(0., 10.), planning_budget_s=(.1, 5.),
              lookahead_m=(.2, 2.), route_weight=(0., 10.), corridor_weight=(0., 10.))
# Promoted learned scorers (tools/learning/run_round.py); used only when their weight is > 0.
MODELS = ROOT / 'artifacts/learning/models/current'


def validate_settings(settings):
    if not isinstance(settings, dict) or set(settings) - set(DEFAULTS):
        raise ValueError('Unknown sandbox setting')
    result = DEFAULTS | settings
    if result['controller'] not in ('rpp', 'mppi'):
        raise ValueError('Invalid controller')
    if result['execution'] not in ('checked-path', 'nav2-goal'):
        raise ValueError('Invalid execution')
    if result['escape'] not in ('legacy', 'retrace'):
        raise ValueError('Invalid escape')
    for key, (lower, upper) in LIMITS.items():
        value = result[key]
        if type(value) not in (int, float) or not math.isfinite(value) or not lower <= value <= upper:
            raise ValueError('Invalid '+key)
    return result


def build_profile(settings):
    settings = validate_settings(settings)
    baseline = (ROOT / 'docs/evidence/navigation-2026-10-01-success/profile.yaml'
                if settings['controller'] == 'rpp' else
                ROOT / 'ros2/src/igvc_navigation/config/local_navigation.yaml')
    profile = yaml.safe_load(baseline.read_text())
    controller = profile['controller_server']['ros__parameters']['FollowPath']
    if settings['controller'] == 'rpp':
        controller['desired_linear_vel'] = settings['speed_mps']
        controller['lookahead_dist'] = settings['lookahead_m']
        controller['cost_scaling_dist'] = settings['inflation_m']
    else:
        controller['vx_max'] = settings['speed_mps']
    for name in ('local_costmap', 'global_costmap'):
        profile[name][name]['ros__parameters']['inflation_layer']['inflation_radius'] = settings['inflation_m']
    return profile, baseline


def mission_argv(python, mission, folder, settings):
    settings = validate_settings(settings)
    return [python, str(ROOT / 'tools/sensor_course.py'), '--mission', str(mission),
            '--report', str(folder / 'run.json'), '--capture-dir', str(folder / 'decisions'),
            '--timeout', '600', '--speed', str(settings['speed_mps']),
            '--planning-budget', str(settings['planning_budget_s']),
            '--path-execution', settings['execution'],
            '--body-clearance-weight', str(settings['clearance_weight'])] + (
                # Legacy keeps the accepted baseline's exact mission arguments.
                ['--escape', settings['escape']] if settings['escape'] != 'legacy' else []) + [
                arg for name in ('route', 'corridor') if settings[name+'_weight'] > 0
                for arg in (f'--{name}-scorer', str(MODELS / f'{name}_scorer.json'), f'--{name}-weight', str(settings[name+'_weight']))]
