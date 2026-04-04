#!/usr/bin/env python3
"""
Bounded LQR Benchmark (Section 5.2 of the paper).

This compares acados timing against mpc.pytorch and cvxpygen/OSQP.
Since mpc.pytorch and cvxpygen are not available in our environment,
we reproduce the benchmark setup and measure acados timing.

Problem formulation (from paper, Eq. 32):
- min sum_n [x_n; u_n]^T H [x_n; u_n] + x_N^T Hx x_N
- s.t. x_0 = x_bar
-      x_{n+1} = A x_n + B u_n + b
-      -u_max <= u_n <= u_max

With parametric A, B, b, H matrices.
"""

import numpy as np
import casadi as ca
import time
import sys
import os

ACADOS_SOURCE_DIR = os.environ.get('ACADOS_SOURCE_DIR', '/home/user/method/acados')
sys.path.insert(0, os.path.join(ACADOS_SOURCE_DIR, 'interfaces', 'acados_template'))

from acados_template import AcadosModel, AcadosOcp, AcadosOcpSolver


def export_parametric_lqr_ocp(A, B, b, H, Hx, x0, u_max, N=20, name="lqr"):
    """Export bounded LQR OCP with parametric A, B, b, H."""
    nx = A.shape[0]
    nu = B.shape[1]

    ocp = AcadosOcp()
    ocp.model.name = name

    # States and controls
    ocp.model.x = ca.SX.sym('x', nx)
    ocp.model.u = ca.SX.sym('u', nu)

    # Parameter: concatenate A, B, b, H as p_global
    # n_theta = nx^2 + nx*nu + nx + (nx+nu)^2
    n_A = nx * nx
    n_B = nx * nu
    n_b = nx
    n_H = (nx + nu) * (nx + nu)
    n_theta = n_A + n_B + n_b + n_H

    p = ca.SX.sym('p', n_theta)
    idx_A = slice(0, n_A)
    idx_B = slice(n_A, n_A + n_B)
    idx_b = slice(n_A + n_B, n_A + n_B + n_b)
    idx_H = slice(n_A + n_B + n_b, n_theta)

    A_mat = ca.reshape(p[idx_A], nx, nx)
    B_mat = ca.reshape(p[idx_B], nx, nu)
    b_vec = p[idx_b]
    H_mat = ca.reshape(p[idx_H], nx + nu, nx + nu)

    # Discrete dynamics: x_{n+1} = A x_n + B u_n + b
    ocp.model.disc_dyn_expr = A_mat @ ocp.model.x + B_mat @ ocp.model.u + b_vec

    # Quadratic cost
    xu = ca.vertcat(ocp.model.x, ocp.model.u)
    ocp.cost.cost_type = 'LINEAR_LS'
    ocp.cost.yref = np.zeros(nx + nu)
    ocp.cost.R = H_mat[nu:, nu:]
    ocp.cost.Q = H_mat[:nu, :nu]

    # Terminal cost
    ocp.cost.cost_type_e = 'LINEAR_LS'
    ocp.cost.yref_e = np.zeros(nx)
    ocp.cost.Q_e = Hx

    # Control bounds
    ocp.constraints.idxbu = np.arange(nu)
    ocp.constraints.lbu = -u_max * np.ones(nu)
    ocp.constraints.ubu = u_max * np.ones(nu)

    # Initial state
    ocp.constraints.x0 = x0

    # Parameter values
    p_vals = np.concatenate([
        A.flatten(), B.flatten(), b.flatten(), H.flatten()
    ])
    ocp.model.p_global = p
    ocp.p_global_values = p_vals

    # Solver options
    ocp.solver_options.N_horizon = N
    ocp.solver_options.tf = N  # dummy
    ocp.solver_options.integrator_type = 'DISCRETE'
    ocp.solver_options.nlp_solver_type = 'SQP'
    ocp.solver_options.qp_solver = 'PARTIAL_CONDENSING_HPIPM'
    ocp.solver_options.hessian_approx = 'EXACT'  # exact for linear-quadratic
    ocp.solver_options.qp_solver_cond_N = N
    ocp.solver_options.with_solution_sens_wrt_params = True
    ocp.solver_options.nlp_solver_max_iter = 50
    ocp.solver_options.tol = 1e-6

    return ocp


def run_benchmark(n_batch=128, n_repeat=3):
    """Run bounded LQR benchmark."""
    print("=" * 70)
    print("BOUNDED LQR BENCHMARK (Section 5.2)")
    print("=" * 70)
    print(f"n_batch={n_batch}, n_repeat={n_repeat}")
    print()

    # Problem dimensions (from paper)
    nx = 8
    nu = 4
    N = 20
    n_theta = nx * nx + nx * nu + nx + (nx + nu) * (nx + nu)  # = 248

    # Generate random problem data
    np.random.seed(42)

    # A = I + 0.2 * M where M ~ N(0,1)
    M_A = np.random.randn(nx, nx)
    A = np.eye(nx) + 0.2 * M_A

    # B, b from standard normal
    B = np.random.randn(nx, nu)
    b = np.random.randn(nx)

    # Cost matrices
    H = np.eye(nx + nu)
    Hx = np.eye(nx)

    # Control bounds to test
    for u_max, u_max_label in [(1e4, '1e4'), (1.0, '1.0')]:
        print(f"\n--- u_max = {u_max} ---")

        # Generate random initial states for batch
        x0_batch = [np.random.randn(nx) for _ in range(n_batch)]

        # Time nominal solve
        times_nominal = []
        times_sens = []

        for rep in range(n_repeat):
            # Create solver
            x0_init = x0_batch[0]
            ocp = export_parametric_lqr_ocp(A, B, b, H, Hx, x0_init, u_max, N=N,
                                             name=f"lqr_umax{u_max_label}_{rep}")

            json_file = f"acados_lqr_umax{u_max_label}_{rep}.json"
            solver = AcadosOcpSolver(ocp, json_file=json_file)

            # Time nominal solves
            t0 = time.time()
            for x0 in x0_batch:
                solver.reset()
                solver.solve_for_x0(x0)
            t_nominal = time.time() - t0
            times_nominal.append(t_nominal)

            # Time with sensitivities
            solver.setup_qp_matrices_and_factorize()
            t0 = time.time()
            for x0 in x0_batch:
                solver.setup_qp_matrices_and_factorize()
                _ = solver.eval_adjoint_solution_sensitivity(
                    seed_u=[(0, np.ones((nu, 1)))]
                )
            t_sens = time.time() - t0
            times_sens.append(t_sens)

        nominal_time_ms = 1000 * np.median(times_nominal)
        sens_time_ms = 1000 * np.median(times_sens)
        total_time_ms = nominal_time_ms + sens_time_ms

        print(f"  Median nominal solve time: {nominal_time_ms:.2f} ms for {n_batch} problems")
        print(f"  Median solve+sens time:   {sens_time_ms:.2f} ms for {n_batch} problems")
        print(f"  Total time:               {total_time_ms:.2f} ms for {n_batch} problems")
        print(f"  Per-problem nominal:       {nominal_time_ms/n_batch:.3f} ms")
        print(f"  Per-problem with sens:     {sens_time_ms/n_batch:.3f} ms")

    return {
        'nominal_time_ms': nominal_time_ms,
        'sens_time_ms': sens_time_ms,
        'total_time_ms': total_time_ms,
    }


if __name__ == '__main__':
    results = run_benchmark()
