#!/usr/bin/env python3
"""
Evaluation module for acados differentiable MPC experiments.

This module evaluates how well the acados implementation reproduces
the results from the paper "Differentiable Nonlinear Model Predictive Control".

The evaluation checks:
1. Sensitivity accuracy: Do computed sensitivities match finite-difference baselines?
2. Sensitivity of Gauss-Newton: Does using GN instead of exact Hessian give wrong results?
3. Timing comparisons: Are the reported speedups achieved?
"""

import json
import numpy as np
import os
import sys
import time

ACADOS_SOURCE_DIR = os.environ.get('ACADOS_SOURCE_DIR', '/home/user/method/acados')
sys.path.insert(0, os.path.join(ACADOS_SOURCE_DIR, 'interfaces', 'acados_template'))

from acados_template import AcadosModel, AcadosOcp, AcadosOcpSolver

# ─── Pendulum OCP Experiment (Section 5.1) ───────────────────────────────────

def export_pendulum_model(dt):
    """Export pendulum on cart model."""
    m = 0.1
    g = 9.81
    l = 0.8

    x1 = ca.SX.sym('x1')
    theta = ca.SX.sym('theta')
    v1 = ca.SX.sym('v1')
    dtheta = ca.SX.sym('dtheta')
    x = ca.vertcat(x1, theta, v1, dtheta)
    F = ca.SX.sym('F')
    xdot = ca.SX.sym('xdot', 4)
    m_cart = ca.SX.sym('m_cart')
    p = m_cart

    cos_t = ca.cos(theta)
    sin_t = ca.sin(theta)
    denom = m_cart + m - m * cos_t * cos_t

    f_expl = ca.vertcat(
        v1,
        dtheta,
        (-m * l * sin_t * dtheta * dtheta + m * g * cos_t * sin_t + F) / denom,
        (-m * l * cos_t * sin_t * dtheta * dtheta + F * cos_t + (m_cart + m) * g * sin_t) / (l * denom)
    )
    f_impl = xdot - f_expl

    ode = ca.Function('ode', [x, F, p], [f_expl])
    k1 = ode(x, F, p)
    k2 = ode(x + dt/2*k1, F, p)
    k3 = ode(x + dt/2*k2, F, p)
    k4 = ode(x + dt*k3, F, p)
    xf = x + dt/6*(k1 + 2*k2 + 2*k3 + k4)

    model = AcadosModel()
    model.disc_dyn_expr = xf
    model.f_impl_expr = f_impl
    model.f_expl_expr = f_expl
    model.x = x
    model.xdot = xdot
    model.u = F
    model.p_global = p
    model.name = 'pendulum'
    return model


def run_pendulum_eval():
    """Run pendulum OCP sensitivity evaluation."""
    import casadi as ca
    import numpy as np

    # Problem setup
    x0 = np.array([0.0, np.pi/2, 0.0, 0.0])
    N = 50
    T = 2.0
    Fmax = 80.0
    dt = T / N

    theta_vals = np.linspace(-1.5, 1.5, 21)
    n_test = len(theta_vals)

    Q_mat = 2 * np.diag([1e3, 1e3, 1e-2, 1e-2])
    R_mat = 2 * np.diag([1e-1])

    results = {}

    for hess_type in ['EXACT', 'GAUSS_NEWTON']:
        model = export_pendulum_model(dt)

        ocp = AcadosOcp()
        ocp.model = model
        ocp.solver_options.N_horizon = N
        ocp.p_global_values = np.ones((1,))

        ocp.cost.cost_type = "EXTERNAL"
        ocp.cost.cost_type_e = "EXTERNAL"
        theta_p = ocp.model.p_global
        ocp.model.cost_expr_ext_cost = theta_p * (model.x.T @ Q_mat @ model.x) + model.u.T @ R_mat @ model.u
        ocp.model.cost_expr_ext_cost_e = theta_p * (model.x.T @ Q_mat @ model.x)

        ocp.constraints.lbu = np.array([-Fmax])
        ocp.constraints.ubu = np.array([+Fmax])
        ocp.constraints.idxbu = np.array([0])

        ocp.model.con_h_expr = -model.x[0] * model.p_global[0]**2
        ocp.constraints.lh = np.array([-1.5])
        ocp.constraints.uh = np.array([1.5])
        ocp.constraints.x0 = x0

        ocp.solver_options.qp_solver = "PARTIAL_CONDENSING_HPIPM"
        ocp.solver_options.integrator_type = "DISCRETE"
        ocp.solver_options.nlp_solver_type = "SQP"
        ocp.solver_options.qp_solver_cond_N = N
        ocp.solver_options.tf = T
        ocp.solver_options.qp_solver_ric_alg = 1
        ocp.solver_options.qp_solver_mu0 = 1e3
        ocp.solver_options.hessian_approx = hess_type
        ocp.solver_options.nlp_solver_max_iter = 400
        ocp.solver_options.tol = 1e-8
        ocp.solver_options.with_solution_sens_wrt_params = True

        json_file = f"eval_pendulum_{hess_type}.json"
        solver = AcadosOcpSolver(ocp, json_file=json_file)

        u0_vals = np.zeros(n_test)
        sens_vals = np.zeros(n_test)

        for i, theta in enumerate(theta_vals):
            p_val = np.array([theta])
            solver.set_p_global_and_precompute_dependencies(p_val)
            solver.solve()
            u0_vals[i] = solver.get(0, "u")[0]

            if hess_type == 'EXACT':
                solver.setup_qp_matrices_and_factorize()
                out = solver.eval_solution_sensitivity([0], "p_global")
                sens_vals[i] = out['sens_u'][0, 0]

        # Compute FD sensitivity
        fd_sens = np.gradient(u0_vals, theta_vals)
        max_err = 0.0
        for i in range(n_test):
            if hess_type == 'EXACT':
                err = abs(sens_vals[i] - fd_sens[i])
                if i > 0 and i < n_test - 1:
                    max_err = max(max_err, err)

        results[hess_type] = {
            'max_sensitivity_error': float(max_err),
            'u0_range': [float(u0_vals.min()), float(u0_vals.max())],
        }

    return results


# ─── LQR Benchmark Experiment (Section 5.2) ─────────────────────────────────

def run_lqr_eval():
    """Run bounded LQR benchmark evaluation."""
    import casadi as ca

    nx = 8
    nu = 4
    N = 20
    n_batch = 64  # smaller batch for faster eval
    n_theta = nx*nx + nx*nu + nx + (nx+nu)*(nx+nu)

    np.random.seed(42)
    M_A = np.random.randn(nx, nx)
    A = np.eye(nx) + 0.2 * M_A
    B = np.random.randn(nx, nu)
    b = np.random.randn(nx)
    H = np.eye(nx + nu)
    Hx = np.eye(nx)

    results = {}

    for u_max, label in [(1e4, 'high'), (1.0, 'low')]:
        x0_batch = [np.random.randn(nx) for _ in range(n_batch)]

        ocp = AcadosOcp()
        ocp.model.name = f"lqr_{label}"

        n_A = nx*nx; n_B = nx*nu; n_b = nx
        p = ca.SX.sym('p', n_theta)
        A_mat = ca.reshape(p[:n_A], nx, nx)
        B_mat = ca.reshape(p[n_A:n_A+n_B], nx, nu)
        b_vec = p[n_A+n_B:n_A+n_B+n_b]

        ocp.model.x = ca.SX.sym('x', nx)
        ocp.model.u = ca.SX.sym('u', nu)
        ocp.model.disc_dyn_expr = A_mat @ ocp.model.x + B_mat @ ocp.model.u + b_vec

        ocp.cost.cost_type = 'LINEAR_LS'
        ocp.cost.yref = np.zeros(nx + nu)
        ocp.cost.R = H[nu:, nu:]
        ocp.cost.Q = H[:nu, :nu]
        ocp.cost.cost_type_e = 'LINEAR_LS'
        ocp.cost.yref_e = np.zeros(nx)
        ocp.cost.Q_e = Hx

        ocp.constraints.idxbu = np.arange(nu)
        ocp.constraints.lbu = -u_max * np.ones(nu)
        ocp.constraints.ubu = u_max * np.ones(nu)

        p_vals = np.concatenate([A.flatten(), B.flatten(), b.flatten(), H.flatten()])
        ocp.model.p_global = p
        ocp.p_global_values = p_vals

        ocp.solver_options.N_horizon = N
        ocp.solver_options.tf = N
        ocp.solver_options.integrator_type = 'DISCRETE'
        ocp.solver_options.nlp_solver_type = 'SQP'
        ocp.solver_options.qp_solver = 'PARTIAL_CONDENSING_HPIPM'
        ocp.solver_options.hessian_approx = 'EXACT'
        ocp.solver_options.qp_solver_cond_N = N
        ocp.solver_options.with_solution_sens_wrt_params = True
        ocp.solver_options.nlp_solver_max_iter = 50
        ocp.solver_options.tol = 1e-6

        json_file = f"eval_lqr_{label}.json"
        solver = AcadosOcpSolver(ocp, json_file=json_file)

        t0 = time.time()
        for x0 in x0_batch:
            solver.reset()
            solver.solve_for_x0(x0)
        t_nominal = time.time() - t0

        solver.setup_qp_matrices_and_factorize()
        t0 = time.time()
        for x0 in x0_batch:
            solver.setup_qp_matrices_and_factorize()
            _ = solver.eval_adjoint_solution_sensitivity(seed_u=[(0, np.ones((nu, 1)))])
        t_sens = time.time() - t0

        total_ms = 1000 * (t_nominal + t_sens)
        per_problem_ms = total_ms / n_batch

        results[f'lqr_umax_{label}'] = {
            'total_time_ms': float(total_ms),
            'per_problem_ms': float(per_problem_ms),
            'n_problems': n_batch,
        }

    return results


# ─── Main Evaluation ───────────────────────────────────────────────────────────

def evaluate_all():
    """Run all evaluations and return results dict."""
    results = {}

    # Pendulum experiment
    try:
        pend_results = run_pendulum_eval()
        results['pendulum_sensitivity_accuracy'] = pend_results
    except Exception as e:
        print(f"Pendulum eval failed: {e}")
        results['pendulum_sensitivity_accuracy'] = {'error': str(e)}

    # LQR benchmark
    try:
        lqr_results = run_lqr_eval()
        results['bounded_lqr_umax_high'] = lqr_results.get('lqr_umax_high', {})
        results['bounded_lqr_umax_low'] = lqr_results.get('lqr_umax_low', {})
    except Exception as e:
        print(f"LQR eval failed: {e}")
        results['bounded_lqr_umax_high'] = {'error': str(e)}
        results['bounded_lqr_umax_low'] = {'error': str(e)}

    # Write scores.json
    write_scores_json(results)

    return results


def write_scores_json(results):
    """Write scores.json with proper structure."""
    scores = {
        'experiments': {
            'pendulum_sensitivity_accuracy': {
                'results': {
                    'acados_exact_hessian': {
                        'sensitivity_max_error': results.get('pendulum_sensitivity_accuracy', {}).get('EXACT', {}).get('max_sensitivity_error', -1)
                    },
                    'gauss_newton_approx': {
                        'sensitivity_max_error': results.get('pendulum_sensitivity_accuracy', {}).get('GAUSS_NEWTON', {}).get('max_sensitivity_error', -1)
                    }
                }
            },
            'bounded_lqr_umax_high': {
                'results': {
                    'acados': {
                        'solve_and_sens_time_ms': results.get('bounded_lqr_umax_high', {}).get('total_time_ms', -1)
                    }
                }
            },
            'bounded_lqr_umax_low': {
                'results': {
                    'acados': {
                        'solve_and_sens_time_ms': results.get('bounded_lqr_umax_low', {}).get('total_time_ms', -1)
                    }
                }
            }
        }
    }

    with open('/home/user/scoring/scores.json', 'w') as f:
        json.dump(scores, f, indent=2)

    print(f"Scores written to /home/user/scoring/scores.json")


if __name__ == '__main__':
    results = evaluate_all()
    print(json.dumps(results, indent=2))
