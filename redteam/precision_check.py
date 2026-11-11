#!/usr/bin/env python3
"""Independent FD step-size sweep, using the unchanged OCP and actual solves."""
import sys
import numpy as np
from common import AUDIT, ROOT, load, save

sys.path.insert(0, str(ROOT / 'method'))
import run_reproduction as method

folder = AUDIT / 'precision_check'


def generated_path(*parts):
    p = (AUDIT / 'generated/precision_check').joinpath(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    return str(p)


method._generated_path = generated_path
c = method._build_parametric_pendulum_components()
ocp = method._build_pendulum_ocp(c, hessian_approx='GAUSS_NEWTON', name='precision_gn')
ocp.solver_options.tol = 1e-12
ocp.solver_options.nlp_solver_max_iter = 1000
solver = c['AcadosOcpSolver'](ocp, json_file=generated_path('precision.json'))
theta = float(c['theta_vals'][len(c['theta_vals']) // 2])
solver.reset()
method._initialize_pendulum_primal(solver, c, theta)
solver.set_p_global_and_precompute_dependencies(np.array([theta]))
solver.solve()
iterate = solver.get_iterate()
points = []
for h in (0.002, 0.001, 0.0005, 0.00025, 0.000125, 0.0000625, 0.00001, 0.000003):
    controls, residuals, statuses = [], [], []
    for delta in (h, -h):
        solver.set_iterate(iterate)
        solver.set_p_global_and_precompute_dependencies(np.array([theta + delta]))
        solver.solve()
        controls.append(float(solver.get(0, 'u')[0]))
        statuses.append(int(solver.status))
        residuals.append(np.asarray(solver.get_residuals()).tolist())
    points.append({'h': h, 'controls': controls, 'statuses': statuses,
                   'residuals': residuals, 'derivative': (controls[0] - controls[1]) / (2 * h)})
richardson = []
for left, right in zip(points, points[1:]):
    if abs(left['h'] / right['h'] - 2) < 1e-9:
        richardson.append({'h': right['h'],
                           'derivative': (4 * right['derivative'] - left['derivative']) / 3})
diagnostics = {name: load(AUDIT / name / 'diagnostics.json')['exact_sensitivity']
               for name in ('reference_seed0', 'better_clip', 'better_tol10', 'better_tol12')}
save(folder / 'results.json', {'theta': theta, 'central_differences': points,
                              'richardson': richardson, 'candidate_derivatives': diagnostics})
print('precision_check', richardson, flush=True)
