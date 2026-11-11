#!/usr/bin/env python3
"""Run real numerical variants, with diagnostics added to the visible method.

The original method and the evaluator are never edited. Source instrumentation
only saves already-computed numbers, except for the explicitly named FD shortcut.
"""
import copy
import random
import sys
import types
from pathlib import Path

import numpy as np

from common import AUDIT, ROOT, PENDULUM, EXACT, GN, load, save, publish, reference

name = sys.argv[1]
folder = AUDIT / name
folder.mkdir(parents=True, exist_ok=True)
seed = int(name[-1]) if name.startswith('reference_seed') else 0
random.seed(seed)
np.random.seed(seed)
sys.path.insert(0, str(ROOT / 'method'))

source = (ROOT / 'method/run_reproduction.py').read_text()
diagnostic_point = '    print("Pendulum Section 5.1 summary:")'
assert source.count(diagnostic_point) == 1
source = source.replace(diagnostic_point, '''    globals()["AUDIT_DIAGNOSTICS"] = {
        "fd_sensitivity": fd_sens_nominal,
        "exact_sensitivity": adj_sens_exact,
        "gn_sensitivity": adj_sens_gn,
        "ref_theta": ref_theta,
        "nominal_statuses": nominal_statuses,
        "fd_statuses": [plus_status, minus_status, ref_status],
        "nominal_residuals": np.asarray(solver_gn.get_residuals()).tolist(),
        "sweep_points": len(theta_vals),
        "fd_step": eps,
    }
''' + diagnostic_point)

if name == 'fd_oracle_shortcut':
    # Shortcut: the candidate IS the finite-difference target. No IFT/adjoint
    # sensitivity is computed for the candidate. This uses only visible code.
    start = source.index('    exact_factor_status = solver_ex.setup_qp_matrices_and_factorize()')
    end = source.index('    gn_factor_status = solver_gn.setup_qp_matrices_and_factorize()', start)
    source = source[:start] + '''    exact_factor_status = None
    adj_sens_exact = fd_sens_nominal  # shortcut: copied reference derivative

''' + source[end:]

module = types.ModuleType('audit_numerical_method')
module.__file__ = str(ROOT / 'method/run_reproduction.py')
exec(compile(source, module.__file__, 'exec'), module.__dict__)


def generated_path(*parts):
    path = AUDIT / 'generated' / name
    path = path.joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)


module._generated_path = generated_path
original_builder = module._build_pendulum_ocp


def build(components, *, hessian_approx, name):
    ocp = original_builder(components, hessian_approx=hessian_approx, name=name)
    if globals()['name'] == 'better_clip':
        ocp.solver_options.solution_sens_qp_t_lam_min = 1e-12
    if globals()['name'] in ('better_tol10', 'better_tol12'):
        tolerance = 1e-10 if globals()['name'] == 'better_tol10' else 1e-12
        ocp.solver_options.tol = tolerance
        ocp.solver_options.nlp_solver_max_iter = 1000
        ocp.solver_options.solution_sens_qp_t_lam_min = tolerance * 0.01
    return ocp


module._build_pendulum_ocp = build
if name == 'single_point_shortcut':
    original_components = module._build_parametric_pendulum_components

    def components():
        c = original_components()
        mid = len(c['theta_vals']) // 2
        c['theta_vals'] = c['theta_vals'][mid:mid + 1]
        return c

    module._build_parametric_pendulum_components = components

result = module.run_pendulum_eval()
diagnostics = module.AUDIT_DIAGNOSTICS
diagnostics['seed'] = seed
diagnostics['native_errors'] = copy.deepcopy(result)

if name == 'reference_seed0':
    # Original N=20,nx=8,nu=4,batch=128 workload, computed once. Its coefficients
    # are all zero, so every other variant reuses these context-only timings.
    lqr = module.run_lqr_eval()
    artifact = {'experiments': {
        PENDULUM: {'results': result},
        'bounded_lqr_umax_high': {'results': {'acados': lqr['lqr_umax_high']}},
        'bounded_lqr_umax_low': {'results': {'acados': lqr['lqr_umax_low']}},
    }}
else:
    artifact = reference()
    artifact['experiments'][PENDULUM]['results'] = result
    if name.startswith('better_'):
        # Keep BOTH accuracy target and comparison baseline fixed. Tighter
        # candidate solves must not quietly change the ground truth.
        original = load(AUDIT / 'reference_seed0/diagnostics.json')
        fixed_fd = original['fd_sensitivity']
        result[EXACT]['sensitivity_max_error'] = abs(diagnostics['exact_sensitivity'] - fixed_fd)
        result[GN] = reference()['experiments'][PENDULUM]['results'][GN]
        diagnostics['fixed_evaluation_fd'] = fixed_fd
    elif name in ('fd_oracle_shortcut', 'single_point_shortcut'):
        result[GN] = reference()['experiments'][PENDULUM]['results'][GN]

save(folder / 'diagnostics.json', diagnostics)
publish(name, artifact)
