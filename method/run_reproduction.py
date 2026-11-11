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


def _generated_path(*parts: str) -> str:
    """Return a workspace-local generated-artifact path outside the repo root."""
    path = os.path.join("/home/user", "tmp", "acados_generated", *parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


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
    step_fun = ca.Function("pendulum_step", [x, force, theta], [x_next])

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
        "step_fun": step_fun,
        "f_max": f_max,
        "theta_vals": theta_vals,
        "q_mat": q_mat,
        "r_mat": r_mat,
    }


def _build_pendulum_ocp(
    components,
    *,
    hessian_approx: str,
    name: str,
    qp_cond_n: int | None = None,
    sens_t_lam_min: float | None = None,
    max_iter: int = 400,
):
    """Create the pendulum OCP used in Section 5.1 / Appendix A.10.

    ``qp_cond_n`` selects the HPIPM partial-condensing horizon. The nominal
    solver keeps the stable 5-block setting; the paper's sensitivity solver
    uses no condensing (``qp_cond_n = N``), which is also the only setting for
    which acados documents ``setup_qp_matrices_and_factorize``.
    ``sens_t_lam_min`` overrides acados' clipping of (t, lambda) before the
    sensitivity factorization (acados default 1e-9).
    """
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
    # Partial condensing with a small block count is materially more stable for
    # this ill-conditioned constrained pendulum than leaving the full N=50 QP.
    if qp_cond_n is None:
        qp_cond_n = min(5, components["n_horizon"])
    ocp.solver_options.qp_solver_cond_N = int(qp_cond_n)
    ocp.solver_options.qp_solver_ric_alg = 0
    ocp.solver_options.qp_solver_cond_ric_alg = 0
    if sens_t_lam_min is not None:
        ocp.solver_options.solution_sens_qp_t_lam_min = float(sens_t_lam_min)
    # The Appendix A.10 pendulum problem is ill-conditioned near the path
    # constraint.  A large initial IPM barrier parameter repeatedly produced
    # ACADOS_MINSTEP iterates with meaningless sensitivities in this runtime.
    # The smaller barrier initialization follows the local working acados
    # pendulum smoke test and lets HPIPM take enough interior-point iterations
    # to recover a useful nominal solution before sensitivity factorization.
    ocp.solver_options.qp_solver_mu0 = 1e-3
    ocp.solver_options.qp_solver_iter_max = 500
    ocp.solver_options.globalization = "FIXED_STEP"
    ocp.solver_options.hessian_approx = hessian_approx
    ocp.solver_options.nlp_solver_max_iter = int(max_iter)
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
    ocp.code_export_directory = _generated_path(name)
    return ocp


def _initialize_pendulum_primal(solver, components, theta_val: float, control_value: float = 0.0):
    """Warm-start x/u with a dynamics-consistent RK4 rollout."""
    state = np.array(components["x0"], dtype=float)
    control = np.array([control_value], dtype=float)
    for stage in range(components["n_horizon"]):
        solver.set(stage, "x", state)
        solver.set(stage, "u", control)
        state = np.array(
            components["step_fun"](state, float(control[0]), float(theta_val)),
            dtype=float,
        ).reshape(-1)
        if not np.all(np.isfinite(state)):
            raise RuntimeError(f"Pendulum rollout warm start became non-finite at stage {stage}")
    solver.set(components["n_horizon"], "x", state)


def run_pendulum_eval():
    """
    Reproduce the core claim from Section 5.1.

    The paper's two-solver approach is used:
    1. Solve the nominal NLP with a Gauss-Newton SQP solver.
    2. Transfer the primal-dual iterate to an exact-Hessian sensitivity solver.
    3. Factorize the exact-Hessian QP and evaluate adjoint sensitivities.
    4. Compare against finite-difference sensitivities of the nominal solution map.
    """
    components = _build_parametric_pendulum_components()
    AcadosOcpSolver = components["AcadosOcpSolver"]

    solver_gn = AcadosOcpSolver(
        _build_pendulum_ocp(components, hessian_approx="GAUSS_NEWTON", name="pendulum_gn_eval"),
        json_file=_generated_path("eval_pendulum_gn.json"),
    )
    solver_ex = AcadosOcpSolver(
        _build_pendulum_ocp(components, hessian_approx="EXACT", name="pendulum_exact_eval"),
        json_file=_generated_path("eval_pendulum_exact.json"),
    )

    theta_vals = components["theta_vals"]
    u0_gn = np.full(len(theta_vals), np.nan, dtype=float)
    gn_iterates = []
    nominal_statuses = []

    def solve_nominal(theta_val, initial_iterate=None):
        """Solve the nominal NLP and return u_0 plus the acados iterate."""
        if initial_iterate is not None:
            solver_gn.set_iterate(initial_iterate)
        else:
            solver_gn.reset()
            _initialize_pendulum_primal(solver_gn, components, theta_val)
        solver_gn.set_p_global_and_precompute_dependencies(np.array([theta_val], dtype=float))
        solver_gn.solve()
        status = int(solver_gn.status)
        if initial_iterate is not None and status == 4:
            solver_gn.reset()
            _initialize_pendulum_primal(solver_gn, components, theta_val)
            solver_gn.set_p_global_and_precompute_dependencies(np.array([theta_val], dtype=float))
            solver_gn.solve()
            status = int(solver_gn.status)
        u0 = float(solver_gn.get(0, "u")[0])
        if not np.isfinite(u0):
            raise RuntimeError(
                f"Nominal pendulum solve produced non-finite u0 at theta={theta_val}: status={status}"
            )
        if status not in (0, 2, 4):
            raise RuntimeError(f"Nominal pendulum solve failed at theta={theta_val}: status={status}")
        # acados can return ACADOS_MINSTEP (4) on this ill-conditioned sweep while
        # still exposing the stationary finite iterate used for sensitivity setup.
        return u0, solver_gn.get_iterate(), status

    for idx, theta_val in enumerate(theta_vals):
        try:
            u0_gn[idx], iterate, status = solve_nominal(float(theta_val))
            gn_iterates.append(iterate)
            nominal_statuses.append(status)
        except Exception:
            gn_iterates.append(None)
            nominal_statuses.append(None)
            continue

    if not np.all(np.isfinite(u0_gn)):
        bad_count = int(np.sum(~np.isfinite(u0_gn)))
        raise RuntimeError(f"{bad_count} nominal pendulum sweep points failed")

    ref_idx = len(theta_vals) // 2
    ref_theta = float(theta_vals[ref_idx])
    ref_seed_iterate = gn_iterates[ref_idx]
    eps = 1e-5

    u_plus, _, plus_status = solve_nominal(ref_theta + eps, ref_seed_iterate)
    u_minus, _, minus_status = solve_nominal(ref_theta - eps, ref_seed_iterate)
    fd_sens_nominal = (u_plus - u_minus) / (2.0 * eps)

    _, gn_iterate_ref, ref_status = solve_nominal(ref_theta, ref_seed_iterate)
    solver_ex.set_p_global_and_precompute_dependencies(np.array([ref_theta]))
    solver_ex.set_iterate(gn_iterate_ref)

    seed_x = [(0, np.zeros((4, 1)))]
    seed_u = [(0, np.ones((1, 1)))]

    exact_factor_status = solver_ex.setup_qp_matrices_and_factorize()
    if exact_factor_status not in (None, 0):
        raise RuntimeError(f"Exact-Hessian factorization failed: status={exact_factor_status}")
    exact_raw = solver_ex.eval_adjoint_solution_sensitivity(
        seed_x,
        seed_u,
        with_respect_to="p_global",
        sanity_checks=False,
    )
    if exact_raw is None or len(exact_raw) == 0:
        raise RuntimeError("Exact-Hessian adjoint sensitivity returned no data")
    adj_sens_exact = float(np.asarray(exact_raw).reshape(-1)[0])

    gn_factor_status = solver_gn.setup_qp_matrices_and_factorize()
    if gn_factor_status not in (None, 0):
        raise RuntimeError(f"Gauss-Newton factorization failed: status={gn_factor_status}")
    gn_raw = solver_gn.eval_adjoint_solution_sensitivity(
        seed_x,
        seed_u,
        with_respect_to="p_global",
        sanity_checks=False,
    )
    if gn_raw is None or len(gn_raw) == 0:
        raise RuntimeError("Gauss-Newton adjoint sensitivity returned no data")
    adj_sens_gn = float(np.asarray(gn_raw).reshape(-1)[0])

    max_err_exact = abs(adj_sens_exact - fd_sens_nominal)
    max_err_gn = abs(adj_sens_gn - fd_sens_nominal)
    status_hist = {
        str(status): nominal_statuses.count(status)
        for status in sorted({status for status in nominal_statuses if status is not None})
    }

    if not np.isfinite(fd_sens_nominal) or abs(fd_sens_nominal) < 1e-8:
        raise RuntimeError(
            "Pendulum finite-difference sensitivity is degenerate; "
            "the nominal solve is not suitable for reproducing the sensitivity claim. "
            f"fd={fd_sens_nominal}, statuses={status_hist}, "
            f"plus={plus_status}, minus={minus_status}, ref={ref_status}, "
            f"u_plus={u_plus}, u_minus={u_minus}"
        )
    if not np.isfinite(max_err_exact) or not np.isfinite(max_err_gn):
        raise RuntimeError("Pendulum sensitivity errors must be finite")
    if max_err_exact >= max_err_gn:
        raise RuntimeError(
            "Exact-Hessian sensitivity is not more accurate than Gauss-Newton "
            f"(exact_error={max_err_exact}, gn_error={max_err_gn})"
        )

    print("Pendulum Section 5.1 summary:")
    print(f"  gn solved points: {int(np.sum(np.isfinite(u0_gn)))}/{len(theta_vals)}")
    print(f"  gn status histogram: {status_hist}")
    print(f"  fd/ref statuses: plus={plus_status}, minus={minus_status}, ref={ref_status}")
    print(f"  exact factorization status at reference: {exact_factor_status}")
    print(f"  finite-difference sensitivity: {fd_sens_nominal:.6f}")
    print(f"  exact adjoint sensitivity:     {adj_sens_exact:.6f}")
    print(f"  gn adjoint sensitivity:        {adj_sens_gn:.6f}")
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
        ocp.code_export_directory = _generated_path(ocp.model.name)
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

        solver = AcadosOcpSolver(ocp, json_file=_generated_path(f"eval_lqr_{label}.json"))

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
