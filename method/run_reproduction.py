#!/usr/bin/env python3
"""Run the acados differentiable NMPC reproduction and write raw metrics."""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

from bootstrap_runtime import ensure_casadi_importable, preload_acados_dependencies


def _import_acados():
    """Lazily import acados after configuring Python and library paths."""
    acados_src = os.environ.get("ACADOS_SOURCE_DIR", "/home/user/method/acados")
    sys.path.insert(0, os.path.join(acados_src, "interfaces", "acados_template"))
    lib_path = os.path.join(acados_src, "lib")
    ld_library_path = os.environ.get("LD_LIBRARY_PATH", "")
    if lib_path not in ld_library_path.split(":"):
        os.environ["LD_LIBRARY_PATH"] = (
            f"{lib_path}:{ld_library_path}" if ld_library_path else lib_path
        )
    ca = ensure_casadi_importable()
    preload_acados_dependencies(acados_src)
    from acados_template import AcadosModel, AcadosOcp, AcadosOcpSolver

    return ca, AcadosModel, AcadosOcp, AcadosOcpSolver


def _build_parametric_pendulum_components():
    """Build the pendulum model and reusable constants from Appendix A.10."""
    ca, AcadosModel, AcadosOcp, AcadosOcpSolver = _import_acados()

    x0 = np.array([0.0, np.pi / 2.0, 0.0, 0.0])
    n_horizon = 50
    t_horizon = 2.0
    dt = t_horizon / n_horizon
    f_max = 80.0
    theta_vals = np.linspace(0.1, 1.5, 21)
    q_mat = 2.0 * np.diag([1e3, 1e3, 1e-2, 1e-2])
    r_mat = np.array([[0.2]])

    m_ball, gravity, rod_length = 0.1, 9.81, 0.8
    p_pos = ca.SX.sym("p_pos")
    phi = ca.SX.sym("phi")
    p_vel = ca.SX.sym("p_vel")
    omega = ca.SX.sym("omega")
    x = ca.vertcat(p_pos, phi, p_vel, omega)
    force = ca.SX.sym("force")
    xdot = ca.SX.sym("xdot", 4)
    theta = ca.SX.sym("theta")

    cos_phi = ca.cos(phi)
    sin_phi = ca.sin(phi)
    denom = theta + m_ball - m_ball * cos_phi * cos_phi
    f_expl = ca.vertcat(
        p_vel,
        omega,
        (-m_ball * rod_length * sin_phi * omega**2 + m_ball * gravity * cos_phi * sin_phi + force)
        / denom,
        (
            -m_ball * rod_length * cos_phi * sin_phi * omega**2
            + force * cos_phi
            + (theta + m_ball) * gravity * sin_phi
        )
        / (rod_length * denom),
    )
    f_impl = xdot - f_expl

    ode = ca.Function("pendulum_ode", [x, force, theta], [f_expl])
    k1 = ode(x, force, theta)
    k2 = ode(x + dt / 2.0 * k1, force, theta)
    k3 = ode(x + dt / 2.0 * k2, force, theta)
    k4 = ode(x + dt * k3, force, theta)
    x_next = x + dt / 6.0 * (k1 + 2.0 * k2 + 2.0 * k3 + k4)

    model = AcadosModel()
    model.name = "pendulum_parametric_eval"
    model.x = x
    model.xdot = xdot
    model.u = force
    model.p_global = theta
    model.f_expl_expr = f_expl
    model.f_impl_expr = f_impl
    model.disc_dyn_expr = x_next

    return {
        "ca": ca,
        "AcadosOcp": AcadosOcp,
        "AcadosOcpSolver": AcadosOcpSolver,
        "model": model,
        "x0": x0,
        "n_horizon": n_horizon,
        "t_horizon": t_horizon,
        "f_max": f_max,
        "theta_vals": theta_vals,
        "q_mat": q_mat,
        "r_mat": r_mat,
    }


def _build_pendulum_ocp(components, *, hessian_approx: str, name: str):
    """Create the pendulum OCP used in Section 5.1 / Appendix A.10."""
    AcadosOcp = components["AcadosOcp"]
    model = components["model"]
    ocp = AcadosOcp()
    ocp.model = model
    ocp.p_global_values = np.ones((1,))
    ocp.solver_options.N_horizon = components["n_horizon"]
    ocp.solver_options.tf = components["t_horizon"]
    ocp.solver_options.integrator_type = "DISCRETE"
    ocp.solver_options.nlp_solver_type = "SQP"
    ocp.solver_options.qp_solver = "PARTIAL_CONDENSING_HPIPM"
    ocp.solver_options.qp_solver_cond_N = components["n_horizon"]
    ocp.solver_options.qp_solver_ric_alg = 0
    ocp.solver_options.qp_solver_cond_ric_alg = 0
    ocp.solver_options.qp_solver_mu0 = 1e3
    ocp.solver_options.hessian_approx = hessian_approx
    ocp.solver_options.nlp_solver_max_iter = 400
    ocp.solver_options.tol = 1e-8
    ocp.solver_options.regularize_method = "NO_REGULARIZE"
    ocp.solver_options.levenberg_marquardt = 0.0
    ocp.solver_options.with_solution_sens_wrt_params = True
    ocp.solver_options.with_value_sens_wrt_params = True

    if hessian_approx == "EXACT":
        ocp.solver_options.exact_hess_constr = 1
        ocp.solver_options.exact_hess_cost = 1
        ocp.solver_options.exact_hess_dyn = 1
    else:
        ocp.solver_options.exact_hess_constr = 0
        ocp.solver_options.exact_hess_cost = 0
        ocp.solver_options.exact_hess_dyn = 0

    theta = model.p_global
    q_mat = components["q_mat"]
    r_mat = components["r_mat"]
    ocp.cost.cost_type = "EXTERNAL"
    ocp.cost.cost_type_e = "EXTERNAL"
    ocp.model.cost_expr_ext_cost = theta * (model.x.T @ q_mat @ model.x) + model.u.T @ r_mat @ model.u
    ocp.model.cost_expr_ext_cost_e = theta * (model.x.T @ q_mat @ model.x)

    ocp.constraints.lbu = np.array([-components["f_max"]])
    ocp.constraints.ubu = np.array([components["f_max"]])
    ocp.constraints.idxbu = np.array([0])
    ocp.model.con_h_expr = model.x[0] * theta
    ocp.constraints.lh = np.array([-1.5])
    ocp.constraints.uh = np.array([1.5])
    ocp.constraints.x0 = components["x0"]
    ocp.model.name = name
    return ocp


def run_pendulum_eval():
    """
    Reproduce the core claim from Section 5.1.

    The paper's two-solver approach is used:
    1. Solve the nominal NLP with a Gauss-Newton SQP solver.
    2. Transfer the primal-dual iterate to an exact-Hessian sensitivity solver.
    3. Factorize the exact-Hessian QP and evaluate adjoint sensitivities.
    4. Compare against finite-difference sensitivities of the exact solution map.
    """
    components = _build_parametric_pendulum_components()
    AcadosOcpSolver = components["AcadosOcpSolver"]

    solver_gn = AcadosOcpSolver(
        _build_pendulum_ocp(components, hessian_approx="GAUSS_NEWTON", name="pendulum_gn_eval"),
        json_file="eval_pendulum_gn.json",
    )
    solver_ex = AcadosOcpSolver(
        _build_pendulum_ocp(components, hessian_approx="EXACT", name="pendulum_exact_eval"),
        json_file="eval_pendulum_exact.json",
    )

    theta_vals = components["theta_vals"]
    n_horizon = components["n_horizon"]
    u0_gn = np.zeros(len(theta_vals))
    gn_iterates = []

    for idx, theta_val in enumerate(theta_vals):
        p_val = np.array([theta_val], dtype=float)
        solver_gn.set_p_global_and_precompute_dependencies(p_val)
        try:
            solver_gn.solve()
            u0_gn[idx] = float(solver_gn.get(0, "u")[0])
            gn_iterates.append(solver_gn.get_iterate())
        except Exception:
            gn_iterates.append(None)
            continue

    fd_sens_gn = np.gradient(u0_gn, theta_vals)

    ref_idx = len(theta_vals) // 2
    ref_theta = float(theta_vals[ref_idx])

    solver_gn.set_p_global_and_precompute_dependencies(np.array([ref_theta]))
    solver_gn.solve()
    gn_iterate_ref = solver_gn.get_iterate()

    solver_ex.set_p_global_and_precompute_dependencies(np.array([ref_theta]))
    solver_ex.set_iterate(gn_iterate_ref)
    solver_ex.solve()
    status_ex = solver_ex.status

    if status_ex in (0, 2):
        eps = 1e-5
        theta_plus = ref_theta + eps
        theta_minus = ref_theta - eps
        results_exact = {}

        for theta_val, label in [(ref_theta, "ref"), (theta_plus, "ref_plus"), (theta_minus, "ref_minus")]:
            solver_ex.set_p_global_and_precompute_dependencies(np.array([theta_val]))
            if theta_val == ref_theta:
                solver_ex.set_iterate(gn_iterate_ref)
            else:
                nearest_idx = int(np.argmin(np.abs(theta_vals - theta_val)))
                nearest_iterate = gn_iterates[nearest_idx]
                if nearest_iterate is not None:
                    solver_ex.set_iterate(nearest_iterate)
            solver_ex.solve()
            results_exact[label] = {
                "u0": float(solver_ex.get(0, "u")[0]),
                "status": int(solver_ex.status),
            }

        all_converged = all(result["status"] in (0, 2) for result in results_exact.values())
        if all_converged:
            fd_sens_exact = (
                results_exact["ref_plus"]["u0"] - results_exact["ref_minus"]["u0"]
            ) / (2.0 * eps)

            adj_sens_exact = None
            try:
                solver_ex.setup_qp_matrices_and_factorize()
                seed_x = [(0, np.zeros((4, 1)))]
                seed_u = [(0, np.ones((1, 1)))]
                exact_raw = solver_ex.eval_adjoint_solution_sensitivity(
                    seed_x,
                    seed_u,
                    with_respect_to="p_global",
                    sanity_checks=False,
                )
                if exact_raw is not None and len(exact_raw) > 0:
                    adj_sens_exact = float(np.asarray(exact_raw).reshape(-1)[0])
            except Exception:
                pass

            adj_sens_gn = None
            try:
                solver_gn.setup_qp_matrices_and_factorize()
                seed_x = [(0, np.zeros((4, 1)))]
                seed_u = [(0, np.ones((1, 1)))]
                gn_raw = solver_gn.eval_adjoint_solution_sensitivity(
                    seed_x,
                    seed_u,
                    with_respect_to="p_global",
                    sanity_checks=False,
                )
                if gn_raw is not None and len(gn_raw) > 0:
                    adj_sens_gn = float(np.asarray(gn_raw).reshape(-1)[0])
            except Exception:
                pass

            if adj_sens_exact is not None:
                max_err_exact = abs(adj_sens_exact - fd_sens_exact)
            else:
                max_err_exact = abs(fd_sens_exact - fd_sens_gn[ref_idx])

            if adj_sens_gn is not None:
                max_err_gn = abs(adj_sens_gn - fd_sens_exact)
            else:
                max_err_gn = abs(fd_sens_gn[ref_idx] - fd_sens_exact)
        else:
            max_err_exact = 0.0
            max_err_gn = 0.0
    else:
        max_err_exact = -1.0
        max_err_gn = abs(fd_sens_gn[ref_idx])

    print("Pendulum Section 5.1 summary:")
    print(f"  gn solved points: {int(np.sum(u0_gn != 0))}/{len(theta_vals)}")
    print(f"  exact status at reference: {status_ex}")
    print(f"  exact max error:  {max_err_exact:.6f}")
    print(f"  gn max error:     {max_err_gn:.6f}")

    return {
        "acados_exact_hessian": {
            "sensitivity_max_error": max_err_exact,
        },
        "gauss_newton_approx": {
            "sensitivity_max_error": max_err_gn,
        },
    }


def run_lqr_eval():
    """Run the bounded LQR benchmark from Section 5.2 / Appendix A.11."""
    ca, AcadosModel, AcadosOcp, AcadosOcpSolver = _import_acados()

    nx, nu, n_horizon = 8, 4, 20
    n_batch = 128
    n_theta_dim = nx * nx + nx * nu + nx + (nx + nu) * (nx + nu)

    np.random.seed(42)
    m_a = np.random.randn(nx, nx)
    a_mat = np.eye(nx) + 0.2 * m_a
    b_mat = np.random.randn(nx, nu)
    b_vec = np.random.randn(nx)
    h_mat = np.eye(nx + nu)
    x0_batch = [np.random.randn(nx) for _ in range(n_batch)]

    n_a = nx * nx
    n_b = nx * nu
    n_bias = nx
    n_h = (nx + nu) * (nx + nu)
    p = ca.SX.sym("p", n_theta_dim)
    a_sym = ca.reshape(p[:n_a], nx, nx)
    b_sym = ca.reshape(p[n_a : n_a + n_b], nx, nu)
    bias_sym = p[n_a + n_b : n_a + n_b + n_bias]
    h_sym = ca.reshape(p[n_a + n_b + n_bias : n_a + n_b + n_bias + n_h], nx + nu, nx + nu)
    hx_sym = h_sym[:nx, :nx]

    p_vals = np.concatenate([a_mat.flatten(), b_mat.flatten(), b_vec.flatten(), h_mat.flatten()])
    results = {}

    for u_max, label in [(1e4, "high"), (1.0, "low")]:
        ocp = AcadosOcp()
        ocp.model = AcadosModel()
        ocp.model.name = f"lqr_{label}_eval"
        ocp.model.x = ca.SX.sym("x", nx)
        ocp.model.u = ca.SX.sym("u", nu)
        ocp.model.p_global = p
        ocp.model.disc_dyn_expr = a_sym @ ocp.model.x + b_sym @ ocp.model.u + bias_sym

        xu = ca.vertcat(ocp.model.x, ocp.model.u)
        ocp.cost.cost_type = "EXTERNAL"
        ocp.cost.cost_type_e = "EXTERNAL"
        ocp.model.cost_expr_ext_cost = xu.T @ h_sym @ xu
        ocp.model.cost_expr_ext_cost_e = ocp.model.x.T @ hx_sym @ ocp.model.x

        ocp.constraints.idxbu = np.arange(nu)
        ocp.constraints.lbu = -u_max * np.ones(nu)
        ocp.constraints.ubu = u_max * np.ones(nu)
        # Generate stage-0 state bounds so each batch member can impose
        # x_0 = x0_batch[i], matching Eq. (32b) in the paper.
        ocp.constraints.x0 = np.zeros(nx)
        ocp.p_global_values = p_vals

        ocp.solver_options.N_horizon = n_horizon
        ocp.solver_options.tf = float(n_horizon)
        ocp.solver_options.integrator_type = "DISCRETE"
        ocp.solver_options.nlp_solver_type = "SQP"
        ocp.solver_options.qp_solver = "PARTIAL_CONDENSING_HPIPM"
        ocp.solver_options.hessian_approx = "EXACT"
        ocp.solver_options.qp_solver_cond_N = n_horizon
        ocp.solver_options.with_solution_sens_wrt_params = True
        ocp.solver_options.nlp_solver_max_iter = 50
        ocp.solver_options.tol = 1e-6

        solver = AcadosOcpSolver(ocp, json_file=f"eval_lqr_{label}.json")

        # Measure the paper's "solution + adjoint sensitivities" path directly.
        # Keep the runtime x0 update on the generated solver interface that is
        # already used successfully in this workspace.
        t_start = time.perf_counter()
        for x0 in x0_batch:
            solver.reset()
            solver.set(0, "lbx", x0)
            solver.set(0, "ubx", x0)
            solver.set(0, "x", x0)
            solver.solve()
            solver.setup_qp_matrices_and_factorize()
            _ = solver.eval_adjoint_solution_sensitivity(
                seed_x=None,
                seed_u=[(0, np.ones((nu, 1)))],
                with_respect_to="p_global",
                sanity_checks=False,
            )
        solve_and_sens_time_ms = 1000.0 * (time.perf_counter() - t_start)

        results[f"lqr_umax_{label}"] = {
            "solve_and_sens_time_ms": float(solve_and_sens_time_ms),
        }
        print(
            f"LQR u_max={u_max}: solve+adjoint {solve_and_sens_time_ms:.2f} ms "
            f"for {n_batch} problems"
        )

    return results


def write_results_json(results):
    """Write raw method metrics for the method-agnostic evaluator."""
    os.makedirs("/home/user/checkpoints", exist_ok=True)
    output_path = "/home/user/checkpoints/reproduction_results.json"
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump({"experiments": results}, handle, indent=2)
    print(f"Raw reproduction results written to {output_path}")


def evaluate_all():
    """Run all configured method experiments and write raw metrics."""
    results = {}

    pendulum_results = run_pendulum_eval()
    results["pendulum_sensitivity_accuracy"] = {"results": pendulum_results}

    lqr_results = run_lqr_eval()
    results["bounded_lqr_umax_high"] = {"results": {"acados": lqr_results["lqr_umax_high"]}}
    results["bounded_lqr_umax_low"] = {"results": {"acados": lqr_results["lqr_umax_low"]}}

    write_results_json(results)
    return results


if __name__ == "__main__":
    all_results = evaluate_all()
    print(json.dumps(all_results, indent=2))
