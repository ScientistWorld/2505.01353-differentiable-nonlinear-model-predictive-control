"""Artifact helpers. Candidate code never imports the hidden evaluator."""
import copy
import json
from pathlib import Path

ROOT = Path('/home/user')
AUDIT = ROOT / 'redteam'
PENDULUM = 'pendulum_sensitivity_accuracy'
EXACT = 'acados_exact_hessian'
GN = 'gauss_newton_approx'
ARTIFACT = ROOT / 'checkpoints/reproduction_results.json'


def load(path):
    return json.loads(Path(path).read_text())


def save(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=True) + '\n')


def reference():
    return copy.deepcopy(load(AUDIT / 'reference_seed0/artifact.json'))


def publish(name, obj):
    save(AUDIT / name / 'artifact.json', obj)
    save(ARTIFACT, obj)


def minimal(error=0.0, gn_error=1.0):
    # Constructed from the visible train scorer's public artifact contract.
    return {'experiments': {
        PENDULUM: {'results': {
            EXACT: {'sensitivity_max_error': error},
            GN: {'sensitivity_max_error': gn_error},
        }},
        'bounded_lqr_umax_high': {'results': {'acados': {'solve_and_sens_time_ms': 0.0}}},
        'bounded_lqr_umax_low': {'results': {'acados': {'solve_and_sens_time_ms': 0.0}}},
    }}
