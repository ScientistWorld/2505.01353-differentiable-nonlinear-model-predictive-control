#!/usr/bin/env python3
"""
Chain of Masses Sensitivity Experiment (Section 5.3 of the paper).

Nonlinear OCP with chain-of-masses model.
Comparison of forward vs adjoint sensitivity computation time.

Problem: n_masses=3, N=40, nx=9, nu=3, n_theta=113
"""

import numpy as np
import casadi as ca
from casadi.tools import struct_symSX, entry
import time
import sys
import os

ACADOS_SOURCE_DIR = os.environ.get('ACADOS_SOURCE_DIR', '/home/user/method/acados')
sys.path.insert(0, os.path.join(ACADOS_SOURCE_DIR, 'interfaces', 'acados_template'))

from acados_template import AcadosModel, AcadosOcp, AcadosOcpSolver


def export_discrete_erk4_step(f_expl, x, u, p, h, n_steps=2):
    """RK4 integrator for continuous dynamics."""
    dt = h / n_steps
    ode = ca.Function("f", [x, u, p], [f_expl])
    xnext = x
    for _ in range(n_steps):
        k1 = ode(xnext, u, p)
        k2 = ode(xnext + dt / 2 * k1, u, p)
        k3 = ode(xnext + dt / 2 * k2, u, p)
        k4 = ode(xnext + dt * k3, u, p)
        xnext = xnext + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
    return xnext


def export_chain_mass_model(n_mass, Ts):
    """Export chain of masses model."""
    M = n_mass - 2
    nx = (2 * M + 1) * 3
    nu = 3

    xpos = ca.SX.sym("xpos", (M + 1) * 3)
    xvel = ca.SX.sym("xvel", M * 3)
    u = ca.SX.sym("u", nu)
    xdot = ca.SX.sym("xdot", nx)

    f = ca.SX.zeros(3 * M)
    p = ca.SX.sym("p", 113)  # 3*(n_mass-1) + 3*3*(n_mass-1) + 3*3*(n_mass-1) + nx^2 + nu^2

    # Simplified parameter structure
    n_link = n_mass - 1
    m = p[0:n_link]
    D_vec = ca.SX(n_link, 3)
    idx = n_link
    for i in range(n_link):
        D_vec[i, :] = p[idx:idx+3]
        idx += 3
    L_vec = ca.SX(n_link, 3)
    for i in range(n_link):
        L_vec[i, :] = p[idx:idx+3]
        idx += 3
    C_vec = ca.SX(n_link, 3)
    for i in range(n_link):
        C_vec[i, :] = p[idx:idx+3]
        idx += 3

    x0_fixed = ca.SX.zeros(3)
    for i in range(M + 1):
        if i == 0:
            dist = xpos[i*3:(i+1)*3] - x0_fixed
        else:
            dist = xpos[i*3:(i+1)*3] - xpos[(i-1)*3:i*3]

        F_spring = ca.SX.zeros(3)
        for j in range(3):
            F_spring[j] = D_vec[i, j] / m[i] * (1 - L_vec[i, j] / (ca.norm_2(dist) + 1e-10)) * dist[j]

        if i < M:
            f[i*3:(i+1)*3] -= F_spring
        if i > 0:
            f[(i-1)*3:i*3] += F_spring

    for i in range(M + 1):
        if i == 0:
            vel = xvel[i*3:(i+1)*3]
        elif i == M:
            vel = u - xvel[(i-1)*3:i*3]
        else:
            vel = xvel[i*3:(i+1)*3] - xvel[(i-1)*3:i*3]

        F_damp = ca.SX.zeros(3)
        for j in range(3):
            F_damp[j] = C_vec[i, j] * vel[j]

        if i < M:
            f[i*3:(i+1)*3] -= F_damp
        if i > 0:
            f[(i-1)*3:i*3] += F_damp

    # Gravity
    for i in range(M):
        f[i*3+2] -= 9.81

    x = ca.vertcat(xpos, xvel)
    f_expl = ca.vertcat(xvel, u, f)
    f_impl = xdot - f_expl

    # RK4 discrete dynamics
    f_disc = export_discrete_erk4_step(f_expl, x, u, p, Ts)

    model = AcadosModel()
    model.f_impl_expr = f_impl
    model.f_expl_expr = f_expl
    model.disc_dyn_expr = f_disc
    model.x = x
    model.xdot = xdot
    model.u = u
    model.p_global = p
    model.name = f"chain_mass_{n_mass}"

    return model, nx, nu, m, D_vec, L_vec, C_vec


def run_chain_experiment(n_test=20):
    """Run chain of masses sensitivity experiment."""
    print("=" * 70)
    print("CHAIN OF MASSES SENSITIVITY EXPERIMENT (Section 5.3)")
    print("=" * 70)

    # Problem parameters (from paper)
    n_mass = 3
    N = 40
    Ts = 0.2
    nx, nu = (2*(n_mass-2)+1)*3, 3

    np.random.seed(42)

    # Default parameters
    m_default = 0.033 * np.ones(n_mass - 1)
    D_default = 1.0 * np.ones((n_mass - 1, 3))
    L_default = 0.033 * np.ones((n_mass - 1, 3))
    C_default = 0.1 * np.ones((n_mass - 1, 3))
    Q_mat = 2 * np.diag(np.ones(nx))
    R_mat = 2 * 1e-2 * np.diag(np.ones(nu))

    # Build parameter vector
    p_default = np.concatenate([
        m_default,
        D_default.flatten(), L_default.flatten(), C_default.flatten(),
        Q_mat.flatten(), R_mat.flatten()
    ])

    # Initial state (simplified steady state)
    x0 = np.zeros(nx)

    # Create OCP
    ocp = AcadosOcp()
    model, _, _, _, _, _, _ = export_chain_mass_model(n_mass, Ts)
    ocp.model = model

    ocp.solver_options.N_horizon = N
    ocp.solver_options.tf = N * Ts
    ocp.solver_options.integrator_type = 'DISCRETE'
    ocp.solver_options.nlp_solver_type = 'SQP'
    ocp.solver_options.qp_solver = 'PARTIAL_CONDENSING_HPIPM'
    ocp.solver_options.hessian_approx = 'EXACT'
    ocp.solver_options.qp_solver_cond_N = N
    ocp.solver_options.with_solution_sens_wrt_params = True
    ocp.solver_options.nlp_solver_max_iter = 50
    ocp.solver_options.tol = 1e-5

    # Cost
    ocp.cost.cost_type = 'EXTERNAL'
    ocp.cost.cost_type_e = 'EXTERNAL'
    ocp.model.cost_expr_ext_cost = ocp.model.x.T @ Q_mat @ ocp.model.x + ocp.model.u.T @ R_mat @ ocp.model.u
    ocp.model.cost_expr_ext_cost_e = ocp.model.x.T @ Q_mat @ ocp.model.x

    # Control bounds
    umax = 1.0 * np.ones(nu)
    ocp.constraints.lbu = -umax
    ocp.constraints.ubu = umax
    ocp.constraints.idxbu = np.arange(nu)
    ocp.constraints.x0 = x0

    ocp.model.p_global = model.p_global
    ocp.p_global_values = p_default

    print(f"Problem: n_mass={n_mass}, N={N}, nx={nx}, nu={nu}")

    # Build solver
    json_file = "acados_chain.json"
    solver = AcadosOcpSolver(ocp, json_file=json_file)

    # Timing arrays
    times_solve = []
    times_forward = []
    times_adjoint = []

    for i in range(n_test):
        # Solve
        t0 = time.time()
        status = solver.solve()
        times_solve.append(time.time() - t0)

        # Forward sensitivity
        solver.setup_qp_matrices_and_factorize()
        t0 = time.time()
        out = solver.eval_solution_sensitivity(0, "p_global")
        times_forward.append(time.time() - t0)

        # Adjoint sensitivity
        seed_u = [(0, np.ones((nu, 1)))]
        seed_x = [(0, np.ones((nx, 1)))]
        t0 = time.time()
        adj = solver.eval_adjoint_solution_sensitivity(seed_u=seed_u, seed_x=seed_x)
        times_adjoint.append(time.time() - t0)

    times_solve = np.array(times_solve) * 1000  # ms
    times_forward = np.array(times_forward) * 1000
    times_adjoint = np.array(times_adjoint) * 1000

    print(f"\nMedian timings over {n_test} runs:")
    print(f"  Solve:               {np.median(times_solve)*1000:.3f} us")
    print(f"  Forward sensitivity: {np.median(times_forward):.3f} ms")
    print(f"  Adjoint sensitivity: {np.median(times_adjoint):.3f} ms")
    print(f"  Adjoint speedup:    {np.median(times_forward)/np.median(times_adjoint):.2f}x")

    return {
        'forward_time_ms': np.median(times_forward),
        'adjoint_time_ms': np.median(times_adjoint),
        'adjoint_speedup': np.median(times_forward) / np.median(times_adjoint),
    }


if __name__ == '__main__':
    results = run_chain_experiment()
