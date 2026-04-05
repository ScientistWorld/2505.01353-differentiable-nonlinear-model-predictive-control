#!/usr/bin/env python3
"""Minimal test: can we solve a simple pendulum OCP at all?"""

import numpy as np
import casadi as ca
import os
import sys

ACADOS_SOURCE_DIR = os.environ.get('ACADOS_SOURCE_DIR', '/home/user/method/acados')
sys.path.insert(0, os.path.join(ACADOS_SOURCE_DIR, 'interfaces', 'acados_template'))

from acados_template import AcadosModel, AcadosOcp, AcadosOcpSolver


def export_simple_model(dt):
    model_name = 'simple_pendulum'

    m = 0.1
    g = 9.81
    l = 0.8
    m_cart = 1.0

    x1 = ca.SX.sym('x1')
    theta = ca.SX.sym('theta')
    v1 = ca.SX.sym('v1')
    dtheta = ca.SX.sym('dtheta')
    x = ca.vertcat(x1, theta, v1, dtheta)

    F = ca.SX.sym('F')
    u = F

    xdot = ca.SX.sym('xdot', 4)

    # Parameter: cart mass
    m_cart_param = ca.SX.sym('m_cart')
    p = m_cart_param

    cos_theta = ca.cos(theta)
    sin_theta = ca.sin(theta)
    denom = m_cart_param + m - m * cos_theta * cos_theta

    f_expl = ca.vertcat(
        v1,
        dtheta,
        (-m * l * sin_theta * dtheta * dtheta + m * g * cos_theta * sin_theta + F) / denom,
        (-m * l * cos_theta * sin_theta * dtheta * dtheta + F * cos_theta + (m_cart_param + m) * g * sin_theta) / (l * denom)
    )

    f_impl = xdot - f_expl

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
    model.name = model_name
    model.p_global = p
    return model


def main():
    print("Testing simple pendulum OCP...")

    x0 = np.array([0.0, np.pi / 2, 0.0, 0.0])
    N = 20
    T = 1.0
    Fmax = 80.0
    dt = T / N

    ocp = AcadosOcp()
    ocp.model = export_simple_model(dt)

    Q_mat = np.diag([1e3, 1e3, 1e-2, 1e-2])
    R_mat = np.diag([1e-1])

    ocp.cost.cost_type = "EXTERNAL"
    ocp.cost.cost_type_e = "EXTERNAL"
    ocp.model.cost_expr_ext_cost = ocp.model.p_global[0] * (ocp.model.x.T @ Q_mat @ ocp.model.x) + ocp.model.u.T @ R_mat @ ocp.model.u
    ocp.model.cost_expr_ext_cost_e = ocp.model.p_global[0] * (ocp.model.x.T @ Q_mat @ ocp.model.x)

    ocp.constraints.lbu = np.array([-Fmax])
    ocp.constraints.ubu = np.array([+Fmax])
    ocp.constraints.idxbu = np.array([0])
    ocp.constraints.x0 = x0
    ocp.p_global_values = np.ones((1,))

    ocp.solver_options.N_horizon = N
    ocp.solver_options.tf = T
    ocp.solver_options.qp_solver = "PARTIAL_CONDENSING_HPIPM"
    ocp.solver_options.nlp_solver_type = "SQP"
    ocp.solver_options.qp_solver_cond_N = 5
    ocp.solver_options.integrator_type = "DISCRETE"
    ocp.solver_options.qp_solver_mu0 = 1e-3
    ocp.solver_options.qp_solver_iter_max = 200
    ocp.solver_options.globalization = "FIXED_STEP"
    ocp.solver_options.hessian_approx = "EXACT"
    ocp.solver_options.with_solution_sens_wrt_params = True
    ocp.solver_options.with_value_sens_wrt_params = True
    ocp.solver_options.nlp_solver_max_iter = 100
    ocp.solver_options.tol = 1e-3

    json_file = "test_simple_pendulum.json"
    solver = AcadosOcpSolver(ocp, json_file=json_file, generate=True, build=True)

    # Initialize controls to zero
    for i in range(N):
        solver.set(i, 'u', np.array([0.0]))

    # Set parameter
    p_val = np.array([1.0])
    solver.set_p_global_and_precompute_dependencies(p_val)

    print("Calling solve_for_x0...")
    status = solver.solve_for_x0(x0)
    print(f"Solver status: {status}")

    if status == 0:
        print("SUCCESS!")
        u0 = solver.get(0, 'u')[0]
        print(f"Optimal u0 = {u0}")
    else:
        print(f"FAILED with status {status}")

    return status


if __name__ == '__main__':
    main()
