#!/usr/bin/env python3
"""
Pendulum OCP Sensitivity Experiment (Section 5.1 of the paper).

This reproduces the core claim: acados sensitivities match finite differences
while Gauss-Newton Hessian approximation gives wrong results.

Problem: Cart-pole with parametric mass m = theta.
- State: x = [p, phi, s, omega] (cart position, pendulum angle, velocities)
- Control: u = F (force on cart)
- Parameter: theta = cart mass
- The parameter enters cost, dynamics, and constraints nonlinearly.
"""

import numpy as np
import casadi as ca
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import time
import os
import sys

# Add acados to path
ACADOS_SOURCE_DIR = os.environ.get('ACADOS_SOURCE_DIR', '/home/user/method/acados')
sys.path.insert(0, os.path.join(ACADOS_SOURCE_DIR, 'interfaces', 'acados_template'))

from acados_template import AcadosModel, AcadosOcp, AcadosOcpSolver


def export_pendulum_ode_model_with_mass_as_p_global(dt):
    """Export pendulum on cart model with cart mass as parameter."""
    model_name = 'pendulum_parametric'

    m = 0.1  # mass of the ball [kg]
    g = 9.81  # gravity constant [m/s^2]
    l = 0.8  # length of the rod [m]

    # States
    x1 = ca.SX.sym('x1')
    theta = ca.SX.sym('theta')
    v1 = ca.SX.sym('v1')
    dtheta = ca.SX.sym('dtheta')
    x = ca.vertcat(x1, theta, v1, dtheta)

    # Control
    F = ca.SX.sym('F')
    u = F

    # xdot
    xdot = ca.SX.sym('xdot', 4)

    # Parameter: cart mass
    m_cart = ca.SX.sym('m_cart')
    p = m_cart

    # Dynamics
    cos_theta = ca.cos(theta)
    sin_theta = ca.sin(theta)
    denominator = m_cart + m - m * cos_theta * cos_theta

    f_expl = ca.vertcat(
        v1,
        dtheta,
        (-m * l * sin_theta * dtheta * dtheta + m * g * cos_theta * sin_theta + F) / denominator,
        (-m * l * cos_theta * sin_theta * dtheta * dtheta + F * cos_theta + (m_cart + m) * g * sin_theta) / (l * denominator)
    )

    f_impl = xdot - f_expl

    # Discrete dynamics via RK4
    ode = ca.Function('ode', [x, u, p], [f_expl])
    k1 = ode(x, u, p)
    k2 = ode(x + dt / 2 * k1, u, p)
    k3 = ode(x + dt / 2 * k2, u, p)
    k4 = ode(x + dt * k3, u, p)
    xf = x + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)

    model = AcadosModel()
    model.disc_dyn_expr = xf
    model.f_impl_expr = f_impl
    model.f_expl_expr = f_expl
    model.x = x
    model.xdot = xdot
    model.u = u
    model.p_global = p
    model.name = model_name

    return model


def export_parametric_ocp(x0, N_horizon, T_horizon, Fmax,
                          hessian_approx="GAUSS_NEWTON",
                          qp_solver_ric_alg=1,
                          with_parametric_constraint=True):
    """Export OCP for pendulum on cart with parametric mass."""
    ocp = AcadosOcp()
    dt = T_horizon / N_horizon
    ocp.model = export_pendulum_ode_model_with_mass_as_p_global(dt=dt)

    ocp.solver_options.N_horizon = N_horizon

    # Set mass parameter value (will be overridden)
    ocp.p_global_values = np.ones((1,))

    # Cost weights
    Q_mat = 2 * np.diag([1e3, 1e3, 1e-2, 1e-2])
    R_mat = 2 * np.diag([1e-1])

    ocp.cost.cost_type = "EXTERNAL"
    ocp.cost.cost_type_e = "EXTERNAL"

    # Cost: L_n(x, u; theta) = theta * x^T Q x + u^T R u
    #       M_N(x; theta) = theta * x^T Q x
    theta_param = ocp.model.p_global
    ocp.model.cost_expr_ext_cost = theta_param * (ocp.model.x.T @ Q_mat @ ocp.model.x) + ocp.model.u.T @ R_mat @ ocp.model.u
    ocp.model.cost_expr_ext_cost_e = theta_param * (ocp.model.x.T @ Q_mat @ ocp.model.x)

    # Control bounds
    ocp.constraints.lbu = np.array([-Fmax])
    ocp.constraints.ubu = np.array([+Fmax])
    ocp.constraints.idxbu = np.array([0])

    # Parametric constraint: -1.5 <= p * theta <= 1.5
    if with_parametric_constraint:
        ocp.model.con_h_expr = -ocp.model.x[0] * ocp.model.p_global[0]**2
        ocp.constraints.lh = np.array([-1.5])
        ocp.constraints.uh = np.array([1.5])

    ocp.constraints.x0 = x0

    # Solver options
    ocp.solver_options.qp_solver = "PARTIAL_CONDENSING_HPIPM"
    ocp.solver_options.integrator_type = "DISCRETE"
    ocp.solver_options.nlp_solver_type = "SQP"
    ocp.solver_options.qp_solver_cond_N = N_horizon
    ocp.solver_options.tf = T_horizon
    ocp.solver_options.qp_solver_ric_alg = qp_solver_ric_alg
    ocp.solver_options.qp_solver_cond_ric_alg = qp_solver_ric_alg
    ocp.solver_options.qp_solver_mu0 = 1e3
    ocp.solver_options.hessian_approx = hessian_approx
    ocp.solver_options.nlp_solver_max_iter = 400
    ocp.solver_options.tol = 1e-8

    # Sensitivity options
    if hessian_approx == 'EXACT':
        ocp.solver_options.with_solution_sens_wrt_params = True
        ocp.solver_options.with_value_sens_wrt_params = True

    return ocp


def compute_sensitivity_with_finite_differences(x0, N_horizon, T_horizon, Fmax,
                                                theta_values, hessian_approx='EXACT',
                                                generate_solvers=True):
    """Compute sensitivities via acados and finite differences."""
    print(f"\n{'='*60}")
    print(f"Running with hessian_approx={hessian_approx}")
    print(f"{'='*60}")

    # Create nominal solver
    ocp_nominal = export_parametric_ocp(x0, N_horizon, T_horizon, Fmax,
                                         hessian_approx=hessian_approx,
                                         qp_solver_ric_alg=1,
                                         with_parametric_constraint=True)
    json_file_nominal = f"acados_ocp_{ocp_nominal.model.name}_{hessian_approx}.json"
    solver_nominal = AcadosOcpSolver(ocp_nominal, json_file=json_file_nominal,
                                      generate=generate_solvers, build=generate_solvers)

    # Create sensitivity solver (always uses exact Hessian)
    ocp_sens = export_parametric_ocp(x0, N_horizon, T_horizon, Fmax,
                                      hessian_approx='EXACT',
                                      qp_solver_ric_alg=1,
                                      with_parametric_constraint=True)
    ocp_sens.model.name = f'{ocp_nominal.model.name}_sens'
    json_file_sens = f"acados_sensitivity_ocp_{ocp_sens.model.name}.json"
    solver_sens = AcadosOcpSolver(ocp_sens, json_file=json_file_sens,
                                   generate=generate_solvers, build=generate_solvers)

    # Storage for results
    u0_opt = np.zeros(len(theta_values))
    sens_u0_acados = np.zeros(len(theta_values))
    max_error = 0.0
    errors = []

    for i, theta in enumerate(theta_values):
        # Set parameter
        p_val = np.array([theta])
        solver_nominal.set_p_global_and_precompute_dependencies(p_val)
        solver_sens.set_p_global_and_precompute_dependencies(p_val)

        # Solve
        status = solver_nominal.solve_for_x0(x0)
        u0_opt[i] = solver_nominal.get(0, "u")[0]

        # Transfer iterate to sensitivity solver
        iterate = solver_nominal.get_flat_iterate()
        solver_sens.set_iterate(iterate)

        # Factorize and compute sensitivity
        solver_sens.setup_qp_matrices_and_factorize()

        # Forward sensitivity for u at stage 0
        out_dict = solver_sens.eval_solution_sensitivity([0], "p_global")
        sens_u0_acados[i] = out_dict['sens_u'][0, 0]

        if i > 0:
            # Finite difference approximation
            delta_theta = theta_values[i] - theta_values[i-1]
            fd_sens = (u0_opt[i] - u0_opt[i-1]) / delta_theta
            error = abs(sens_u0_acados[i] - fd_sens)
            errors.append(error)
            max_error = max(max_error, error)

    if errors:
        mean_error = np.mean(errors)
        median_error = np.median(errors)
        max_error = np.max(errors)
    else:
        mean_error = median_error = max_error = 0.0

    print(f"  Sensitivity accuracy (vs FD):")
    print(f"    Mean error:   {mean_error:.6e}")
    print(f"    Median error: {median_error:.6e}")
    print(f"    Max error:    {max_error:.6e}")

    return u0_opt, sens_u0_acados, max_error


def run_pendulum_experiment():
    """Run the pendulum OCP sensitivity experiment (Section 5.1)."""
    print("=" * 70)
    print("PENDULUM OCP SENSITIVITY EXPERIMENT (Section 5.1)")
    print("=" * 70)

    # Problem parameters (from paper Section 5.1 / A.10)
    x0 = np.array([0.0, np.pi / 2, 0.0, 0.0])  # Initial state
    N_horizon = 50
    T_horizon = 2.0
    Fmax = 80.0

    # Parameter range
    theta_values = np.linspace(-1.5, 1.5, 31)

    # Compute with EXACT Hessian
    u0_opt_exact, sens_exact, max_error_exact = compute_sensitivity_with_finite_differences(
        x0, N_horizon, T_horizon, Fmax,
        theta_values, hessian_approx='EXACT'
    )

    # Compute with GAUSS_NEWTON Hessian (for comparison - should give wrong results)
    u0_opt_gn, sens_gn, max_error_gn = compute_sensitivity_with_finite_differences(
        x0, N_horizon, T_horizon, Fmax,
        theta_values, hessian_approx='GAUSS_NEWTON'
    )

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"EXACT Hessian:        Max sensitivity error vs FD = {max_error_exact:.6e}")
    print(f"GAUSS_NEWTON Hessian: Max sensitivity error vs FD = {max_error_gn:.6e}")
    print()

    # Check if exact Hessian is accurate
    exact_ok = max_error_exact < 0.1  # Should be much smaller
    gn_ok = max_error_gn > 1.0  # Should be much larger (wrong results)

    print(f"Exact Hessian correct: {exact_ok}")
    print(f"Gauss-Newton wrong:   {gn_ok}")

    # Create plot
    fig, axes = plt.subplots(2, 1, figsize=(10, 8))

    # Plot 1: Optimal control u0*
    ax = axes[0]
    ax.plot(theta_values, u0_opt_exact, 'k-', label='EXACT Hessian', linewidth=2)
    ax.plot(theta_values, u0_opt_gn, 'r--', label='GAUSS_NEWTON', linewidth=2, alpha=0.7)
    ax.set_xlabel(r'$\theta$ (cart mass)')
    ax.set_ylabel(r'$u_0^*$')
    ax.set_title('Optimal Control Input $u_0^*(\\theta)$')
    ax.legend()
    ax.grid(True)

    # Plot 2: Sensitivities
    ax = axes[1]
    ax.plot(theta_values[:-1], np.diff(u0_opt_exact) / np.diff(theta_values),
            'k-', label='FD (EXACT)', linewidth=2)
    ax.plot(theta_values, sens_exact, 'b:', label='Acados (EXACT)', linewidth=2)
    ax.plot(theta_values[:-1], np.diff(u0_opt_gn) / np.diff(theta_values),
            'r--', label='FD (GAUSS_NEWTON)', linewidth=2, alpha=0.7)
    ax.plot(theta_values, sens_gn, 'g-.', label='Acados (GAUSS_NEWTON)', linewidth=2, alpha=0.7)
    ax.set_xlabel(r'$\theta$ (cart mass)')
    ax.set_ylabel(r'$\partial_\theta u_0^*$')
    ax.set_title('Solution Sensitivity $\partial_\theta u_0^*(\\theta)$')
    ax.legend()
    ax.grid(True)

    plt.tight_layout()
    plt.savefig('/home/user/pendulum_sensitivity_results.png', dpi=150)
    print("\nPlot saved to /home/user/pendulum_sensitivity_results.png")

    return {
        'max_error_exact': max_error_exact,
        'max_error_gauss_newton': max_error_gn,
        'exact_ok': exact_ok,
        'gauss_newton_wrong': gn_ok,
    }


if __name__ == '__main__':
    results = run_pendulum_experiment()
    print("\nFinal results:")
    for k, v in results.items():
        print(f"  {k}: {v}")
