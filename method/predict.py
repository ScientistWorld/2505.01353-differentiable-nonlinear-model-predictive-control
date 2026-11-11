#!/usr/bin/env python3
"""Reference predictor: the paper's acados solution-sensitivity method.

Contract (shared by every method in this gym, see briefing/evaluation.md):

    python3 method/predict.py INSTANCES_JSON PREDICTIONS_JSON

INSTANCES_JSON lists problem instances per experiment (the evaluator writes
it; the method never sees answers).  PREDICTIONS_JSON must contain

    {"methods": {<method_name>: {<experiment>: {<instance_id>: {...}}}}}

with ``{"u0": float, "du0_dtheta": float}`` for the pendulum experiments and
``{"u0": [4 floats], "adjoint": [248 floats]}`` for the bounded-LQR one.

Methods written by this reference predictor:

* ``acados_exact_hessian`` (proposed, Sections 2-4 of the paper): a
  Gauss-Newton SQP nominal solver (S1), primal-dual iterate transfer to an
  exact-Hessian sensitivity solver, factorization of the exact-Hessian KKT
  matrix (S2, S3), and adjoint solution sensitivities (S4, S5).  For the
  strictly convex LQR the single exact-Hessian solver is both nominal and
  sensitivity solver, as in Section 5.2.
* ``gauss_newton_approx`` (baseline, Remark 3): the same IFT step but with
  the Gauss-Newton Hessian of the nominal solver.
* ``unconstrained_ift`` (baseline, related work limited to unconstrained
  formulations): drops every inequality constraint, then applies the exact
  Hessian IFT.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
import traceback

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_reproduction as rr  # noqa: E402

PEND_EXPERIMENTS = ("pendulum_sensitivity_accuracy", "pendulum_smoothed_sensitivity")
LQR_EXPERIMENT = "bounded_lqr_adjoint_accuracy"

PROPOSED = "acados_exact_hessian"
GAUSS_NEWTON = "gauss_newton_approx"
UNCONSTRAINED = "unconstrained_ift"

BIG_BOUND = 1e6

PEND_SPEC = {
    "N": 50,
    "T": 2.0,
    "f_max": 80.0,
    "path_bound": 1.5,
    "m_ball": 0.1,
    "gravity": 9.81,
    "rod_length": 0.8,
    "Q_diag": [2e3, 2e3, 2e-2, 2e-2],
    "R": 0.2,
}
LQR_SPEC = {"N": 20, "nx": 8, "nu": 4, "n_theta": 248, "dt": 1.0}


def _check_spec(problem: dict, expected: dict, label: str) -> None:
    """Refuse to silently solve a different problem than the evaluator asks for."""
    for key, value in expected.items():
        got = problem.get(key)
        if isinstance(value, list):
            ok = isinstance(got, list) and len(got) == len(value) and all(
                abs(float(a) - float(b)) <= 1e-12 * max(1.0, abs(float(b))) for a, b in zip(got, value)
            )
        else:
            ok = got is not None and abs(float(got) - float(value)) <= 1e-12 * max(1.0, abs(float(value)))
        if not ok:
            raise ValueError(f"{label}: problem field {key}={got!r} differs from implemented {value!r}")


# ---------------------------------------------------------------------------
# Pendulum (Section 5.1 / Appendix A.10)
# ---------------------------------------------------------------------------


class PendulumSolvers:
    """Two-solver approach of Section 4 for the parametric pendulum OCP."""

    # HPIPM initial barrier: the paper's 1e3 whenever a smoothed (tau_min > 0)
    # problem is solved (mu0 below tau_min stalls HPIPM with MINSTEP), the
    # gym's 1e-3 for tau_min = 0; the other value is a single fallback.
    MU0_EXACT = 1e-3
    MU0_SMOOTHED = 1e3

    def __init__(self, tag: str = "", sens_t_lam_min: float | None = None, nominal_max_iter: int = 400):
        self.c = rr._build_parametric_pendulum_components()
        self.N = int(self.c["n_horizon"])
        solver_cls = self.c["AcadosOcpSolver"]
        gn_name = f"pend_nominal_gn{tag}"
        ex_name = f"pend_sens_exact{tag}"
        gs_name = f"pend_sens_gn{tag}"
        self.nominal = solver_cls(
            rr._build_pendulum_ocp(self.c, hessian_approx="GAUSS_NEWTON", name=gn_name, max_iter=nominal_max_iter),
            json_file=rr._generated_path(f"{gn_name}.json"),
        )
        # Paper's sensitivity solver: exact Hessian, classic Riccati, no condensing.
        self.sens = solver_cls(
            rr._build_pendulum_ocp(
                self.c,
                hessian_approx="EXACT",
                name=ex_name,
                qp_cond_n=self.N,
                sens_t_lam_min=sens_t_lam_min,
            ),
            json_file=rr._generated_path(f"{ex_name}.json"),
        )
        # Baseline sensitivity solver: identical except for the Gauss-Newton Hessian.
        self.sens_gn = solver_cls(
            rr._build_pendulum_ocp(
                self.c,
                hessian_approx="GAUSS_NEWTON",
                name=gs_name,
                qp_cond_n=self.N,
                sens_t_lam_min=sens_t_lam_min,
            ),
            json_file=rr._generated_path(f"{gs_name}.json"),
        )

    # -- problem data ------------------------------------------------------
    def _set_bounds(self, solver, x0: np.ndarray, unconstrained: bool) -> None:
        f_max = BIG_BOUND if unconstrained else 80.0
        path = BIG_BOUND if unconstrained else 1.5
        solver.set(0, "lbx", x0)
        solver.set(0, "ubx", x0)
        for stage in range(self.N):
            solver.constraints_set(stage, "lbu", np.array([-f_max]))
            solver.constraints_set(stage, "ubu", np.array([f_max]))
        for stage in range(1, self.N):
            solver.constraints_set(stage, "lh", np.array([-path]))
            solver.constraints_set(stage, "uh", np.array([path]))

    def _rollout_init(self, solver, x0: np.ndarray, theta: float) -> None:
        state = np.array(x0, dtype=float)
        for stage in range(self.N):
            solver.set(stage, "x", state)
            solver.set(stage, "u", np.zeros(1))
            state = np.array(self.c["step_fun"](state, 0.0, float(theta)), dtype=float).reshape(-1)
            if not np.all(np.isfinite(state)):
                state = np.array(x0, dtype=float)
        solver.set(self.N, "x", state)

    def configure(self, theta: float, x0: np.ndarray, tau: float, unconstrained: bool = False) -> None:
        for solver in (self.nominal, self.sens, self.sens_gn):
            solver.set_p_global_and_precompute_dependencies(np.array([float(theta)]))
            solver.options_set("tau_min", float(tau))
            self._set_bounds(solver, x0, unconstrained)

    def set_nominal_tolerance(self, tol: float) -> None:
        for field in ("tol_stat", "tol_eq", "tol_ineq", "tol_comp"):
            self.nominal.options_set(field, float(tol))
        for field in ("qp_tol_stat", "qp_tol_eq", "qp_tol_ineq", "qp_tol_comp"):
            self.nominal.options_set(field, float(tol) * 0.1)

    def _guess_init(self, solver, guess: dict) -> None:
        for stage in range(self.N):
            solver.set(stage, "x", np.asarray(guess["x"][stage], dtype=float))
            solver.set(stage, "u", np.asarray(guess["u"][stage], dtype=float))
        solver.set(self.N, "x", np.asarray(guess["x"][self.N], dtype=float))

    # -- (S1) nominal solve ------------------------------------------------
    def solve_nominal(self, theta: float, x0: np.ndarray, tau: float, unconstrained: bool = False, guess=None):
        """Warm-started from the instance's initial guess (the solution at a
        neighbouring parameter, as in the paper's sweep); RK4 rollout otherwise."""
        self.configure(theta, x0, tau, unconstrained)
        primary = self.MU0_SMOOTHED if tau > 0.0 else self.MU0_EXACT
        fallback = self.MU0_EXACT if tau > 0.0 else self.MU0_SMOOTHED
        result = None
        for mu0 in (primary, fallback):
            self.nominal.options_set("qp_mu0", float(mu0))
            self.nominal.reset()
            if guess is not None:
                self._guess_init(self.nominal, guess)
            else:
                self._rollout_init(self.nominal, x0, theta)
            status = int(self.nominal.solve())
            u0 = float(self.nominal.get(0, "u")[0])
            attempt = (u0, status, self.nominal.get_iterate())
            if result is None:
                result = attempt
            if status == 0 and np.isfinite(u0):
                result = attempt
                break
        self.nominal.options_set("qp_mu0", float(primary))
        return result

    def resolve_from(self, iterate, theta: float, x0: np.ndarray, tau: float):
        """Warm-started nominal solve at a nearby parameter (used by FD variants)."""
        self.configure(theta, x0, tau)
        self.nominal.options_set("qp_mu0", float(self.MU0_SMOOTHED if tau > 0.0 else self.MU0_EXACT))
        self.nominal.set_iterate(iterate)
        status = int(self.nominal.solve())
        if status not in (0, 2):
            self.nominal.reset()
            self._rollout_init(self.nominal, x0, theta)
            status = int(self.nominal.solve())
        return float(self.nominal.get(0, "u")[0]), status

    # -- (S2)-(S5) sensitivity --------------------------------------------
    @staticmethod
    def _adjoint_u0(solver) -> float:
        raw = solver.eval_adjoint_solution_sensitivity(
            [(0, np.zeros((4, 1)))],
            [(0, np.ones((1, 1)))],
            with_respect_to="p_global",
            sanity_checks=False,
        )
        return float(np.asarray(raw).reshape(-1)[0])

    def exact_sensitivity(self, iterate) -> float:
        self.sens.set_iterate(iterate)
        self.sens.setup_qp_matrices_and_factorize()
        return self._adjoint_u0(self.sens)

    def gauss_newton_sensitivity(self, iterate) -> float:
        # Same IFT step, but the KKT matrix uses the Gauss-Newton Hessian (Remark 3).
        self.sens_gn.set_iterate(iterate)
        self.sens_gn.setup_qp_matrices_and_factorize()
        return self._adjoint_u0(self.sens_gn)


def _pendulum_instance(inst: dict):
    theta = float(inst["theta"])
    x0 = np.array([float(v) for v in inst["x0"]], dtype=float)
    tau = float(inst.get("tau_min", 0.0))
    return theta, x0, tau


def _guess(inst: dict):
    guess = inst.get("initial_guess")
    if isinstance(guess, dict) and "x" in guess and "u" in guess:
        return guess
    return None


def _finite(*values) -> bool:
    return all(np.all(np.isfinite(np.asarray(v, dtype=float))) for v in values)


def predict_pendulum(solvers: PendulumSolvers, experiment: dict, out: dict, exp_name: str, log=print) -> None:
    _check_spec(experiment.get("problem", {}), PEND_SPEC, exp_name)
    for name in (PROPOSED, GAUSS_NEWTON, UNCONSTRAINED):
        out.setdefault(name, {}).setdefault(exp_name, {})
    statuses: dict[int, int] = {}
    for inst in experiment["instances"]:
        iid = inst["id"]
        theta, x0, tau = _pendulum_instance(inst)
        try:
            u0, status, iterate = solvers.solve_nominal(theta, x0, tau, guess=_guess(inst))
            statuses[status] = statuses.get(status, 0) + 1
            sens_gn = solvers.gauss_newton_sensitivity(iterate)
            sens_ex = solvers.exact_sensitivity(iterate)
            if _finite(u0, sens_ex):
                out[PROPOSED][exp_name][iid] = {"u0": u0, "du0_dtheta": sens_ex}
            if _finite(u0, sens_gn):
                out[GAUSS_NEWTON][exp_name][iid] = {"u0": u0, "du0_dtheta": sens_gn}
        except Exception as exc:  # keep going; missing predictions count as failures
            log(f"[predict] {exp_name}/{iid}: proposed/GN failed: {exc}")
        try:
            u0_unc, _, iterate_unc = solvers.solve_nominal(theta, x0, tau, unconstrained=True, guess=_guess(inst))
            sens_unc = solvers.exact_sensitivity(iterate_unc)
            if _finite(u0_unc, sens_unc):
                out[UNCONSTRAINED][exp_name][iid] = {"u0": u0_unc, "du0_dtheta": sens_unc}
        except Exception as exc:
            log(f"[predict] {exp_name}/{iid}: unconstrained baseline failed: {exc}")
    log(f"[predict] {exp_name}: {len(experiment['instances'])} instances, nominal status histogram {statuses}")


# ---------------------------------------------------------------------------
# Bounded LQR (Section 5.2 / Appendix A.11)
# ---------------------------------------------------------------------------


class LqrSolver:
    """Bounded-LQR OCP with all of (A, B, b, H) as global parameters."""

    def __init__(self, tag: str = "", hessian_approx: str = "EXACT", sens_t_lam_min: float | None = None,
                 max_iter: int = 50):
        ca, AcadosModel, AcadosOcp, AcadosOcpSolver = rr._import_acados()
        nx, nu, n_horizon = LQR_SPEC["nx"], LQR_SPEC["nu"], LQR_SPEC["N"]
        self.nx, self.nu, self.N = nx, nu, n_horizon
        n_a, n_b, n_bias, n_h = nx * nx, nx * nu, nx, (nx + nu) * (nx + nu)
        p = ca.SX.sym("p", n_a + n_b + n_bias + n_h)
        # Column-major (CasADi reshape) layout: theta = [vec(A), vec(B), b, vec(H)].
        a_sym = ca.reshape(p[:n_a], nx, nx)
        b_sym = ca.reshape(p[n_a : n_a + n_b], nx, nu)
        bias_sym = p[n_a + n_b : n_a + n_b + n_bias]
        h_sym = ca.reshape(p[n_a + n_b + n_bias :], nx + nu, nx + nu)

        name = f"lqr_{hessian_approx.lower()}{tag}"
        ocp = AcadosOcp()
        ocp.model = AcadosModel()
        ocp.model.name = name
        ocp.code_export_directory = rr._generated_path(name)
        ocp.model.x = ca.SX.sym("x", nx)
        ocp.model.u = ca.SX.sym("u", nu)
        ocp.model.p_global = p
        ocp.model.disc_dyn_expr = a_sym @ ocp.model.x + b_sym @ ocp.model.u + bias_sym
        xu = ca.vertcat(ocp.model.x, ocp.model.u)
        ocp.cost.cost_type = "EXTERNAL"
        ocp.cost.cost_type_e = "EXTERNAL"
        ocp.model.cost_expr_ext_cost = xu.T @ h_sym @ xu
        ocp.model.cost_expr_ext_cost_e = ocp.model.x.T @ h_sym[:nx, :nx] @ ocp.model.x
        ocp.constraints.idxbu = np.arange(nu)
        ocp.constraints.lbu = -np.ones(nu)
        ocp.constraints.ubu = np.ones(nu)
        ocp.constraints.x0 = np.zeros(nx)
        p_default = np.concatenate(
            [np.eye(nx).flatten(order="F"), np.zeros(n_b), np.zeros(nx), np.eye(nx + nu).flatten(order="F")]
        )
        ocp.p_global_values = p_default
        opts = ocp.solver_options
        opts.N_horizon = n_horizon
        opts.tf = float(n_horizon)  # dt = 1: stage cost scaling is 1
        opts.integrator_type = "DISCRETE"
        opts.nlp_solver_type = "SQP"
        opts.qp_solver = "PARTIAL_CONDENSING_HPIPM"
        opts.hessian_approx = hessian_approx
        opts.qp_solver_cond_N = n_horizon
        opts.with_solution_sens_wrt_params = True
        opts.nlp_solver_max_iter = int(max_iter)
        opts.tol = 1e-6  # Appendix A.11: problems solved to a tolerance of 1e-6
        if sens_t_lam_min is not None:
            opts.solution_sens_qp_t_lam_min = float(sens_t_lam_min)
        self.solver = AcadosOcpSolver(ocp, json_file=rr._generated_path(f"{name}.json"))

    def set_tolerance(self, tol: float) -> None:
        for field in ("tol_stat", "tol_eq", "tol_ineq", "tol_comp"):
            self.solver.options_set(field, float(tol))
        for field in ("qp_tol_stat", "qp_tol_eq", "qp_tol_ineq", "qp_tol_comp"):
            self.solver.options_set(field, float(tol) * 0.1)

    def configure(self, theta: np.ndarray, x0: np.ndarray, u_max: float) -> None:
        s = self.solver
        s.set_p_global_and_precompute_dependencies(np.asarray(theta, dtype=float))
        s.set(0, "lbx", x0)
        s.set(0, "ubx", x0)
        for stage in range(self.N):
            s.constraints_set(stage, "lbu", -u_max * np.ones(self.nu))
            s.constraints_set(stage, "ubu", u_max * np.ones(self.nu))

    def solve(self, theta: np.ndarray, x0: np.ndarray, u_max: float):
        self.configure(theta, x0, u_max)
        s = self.solver
        s.reset()
        s.set(0, "x", x0)
        status = int(s.solve())
        return np.array(s.get(0, "u"), dtype=float).reshape(-1), status

    def adjoint(self, seed_u0: np.ndarray) -> np.ndarray:
        s = self.solver
        s.setup_qp_matrices_and_factorize()
        raw = s.eval_adjoint_solution_sensitivity(
            [(0, np.zeros((self.nx, 1)))],
            [(0, np.asarray(seed_u0, dtype=float).reshape(self.nu, 1))],
            with_respect_to="p_global",
            sanity_checks=False,
        )
        return np.asarray(raw, dtype=float).reshape(-1)


def _lqr_instance(inst: dict):
    theta = np.array([float(v) for v in inst["theta"]], dtype=float)
    x0 = np.array([float(v) for v in inst["x0"]], dtype=float)
    return theta, x0, float(inst["u_max"]), np.array([float(v) for v in inst["seed_u0"]], dtype=float)


def predict_lqr(exact: LqrSolver, gauss_newton: LqrSolver, experiment: dict, out: dict, log=print) -> None:
    _check_spec(experiment.get("problem", {}), LQR_SPEC, LQR_EXPERIMENT)
    for name in (PROPOSED, GAUSS_NEWTON, UNCONSTRAINED):
        out.setdefault(name, {}).setdefault(LQR_EXPERIMENT, {})
    statuses: dict[int, int] = {}
    for inst in experiment["instances"]:
        iid = inst["id"]
        theta, x0, u_max, seed = _lqr_instance(inst)
        for name, solver, bound in (
            (PROPOSED, exact, u_max),
            (GAUSS_NEWTON, gauss_newton, u_max),
            (UNCONSTRAINED, exact, BIG_BOUND),
        ):
            try:
                u0, status = solver.solve(theta, x0, bound)
                if name == PROPOSED:
                    statuses[status] = statuses.get(status, 0) + 1
                adj = solver.adjoint(seed)
                if _finite(u0, adj):
                    out[name][LQR_EXPERIMENT][iid] = {"u0": u0.tolist(), "adjoint": adj.tolist()}
            except Exception as exc:
                log(f"[predict] {LQR_EXPERIMENT}/{iid}/{name} failed: {exc}")
    log(f"[predict] {LQR_EXPERIMENT}: {len(experiment['instances'])} instances, status histogram {statuses}")


# ---------------------------------------------------------------------------


def run(instances_path: str, predictions_path: str) -> None:
    t_start = time.time()
    with open(instances_path, "r", encoding="utf-8") as handle:
        instances = json.load(handle)
    experiments = instances.get("experiments", {})
    out: dict = {}

    if any(name in experiments for name in PEND_EXPERIMENTS):
        solvers = PendulumSolvers()
        for exp_name in PEND_EXPERIMENTS:
            if exp_name in experiments:
                predict_pendulum(solvers, experiments[exp_name], out, exp_name)
    if LQR_EXPERIMENT in experiments:
        exact = LqrSolver()
        gauss_newton = LqrSolver(hessian_approx="GAUSS_NEWTON")
        predict_lqr(exact, gauss_newton, experiments[LQR_EXPERIMENT], out)

    os.makedirs(os.path.dirname(os.path.abspath(predictions_path)), exist_ok=True)
    with open(predictions_path, "w", encoding="utf-8") as handle:
        json.dump({"methods": out}, handle)
    print(f"[predict] wrote {predictions_path} in {time.time() - t_start:.1f}s")


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: predict.py INSTANCES_JSON PREDICTIONS_JSON")
    try:
        run(sys.argv[1], sys.argv[2])
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)


if __name__ == "__main__":
    main()
