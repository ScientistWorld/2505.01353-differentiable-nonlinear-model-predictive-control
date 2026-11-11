"""Independent high-precision ground truth for the solution-sensitivity gym.

Nothing here uses acados or anything under ``method/``.  Every instance is
solved with IPOPT (CasADi), refined by Newton's method on the KKT system to
machine precision, and differentiated with the implicit function theorem on a
dense KKT matrix (longdouble iterative refinement).  A Richardson finite
difference of the Newton-refined solution map cross-checks every answer.

Problem definitions (also stated in briefing/problem.md):

Pendulum (paper Sec. 5.1 / App. A.10)
    states x=(p, phi, v, omega), control u (force), parameter theta (cart mass)
    min  sum_{n<N} dt*(theta*x_n'Qx_n + R*u_n^2) + theta*x_N'Qx_N
    s.t. x_0 = x0,  x_{n+1} = RK4(x_n, u_n; theta)  (dt = T/N)
         -f_max <= u_n <= f_max          n = 0..N-1
         -1.5 <= theta*p_n <= 1.5        n = 1..N-1
    tau_min = 0: exact KKT conditions;  tau_min > 0: smoothed interior-point
    KKT system (paper eq. 23) where every one-sided inequality h_i <= 0 has
    mu_i * h_i = -tau_min (equalities stay exact).

    Target: the lowest-objective KKT point found from three initialisations
    (strict complementarity margin >= 1e-7 for tau_min = 0).  Every instance
    ships ``initial_guess``: the primal solution on the same branch at a
    neighbouring parameter theta -/+ 1e-3, i.e. the warm start of the paper's
    parameter sweep, so that the local solution map being differentiated is
    unambiguous.

Bounded LQR (paper Sec. 5.2 / App. A.11)
    theta = [vec(A) (64), vec(B) (32), b (8), vec(H) (144)]  (column-major)
    min  sum_{n<N} [x_n;u_n]' H [x_n;u_n] + x_N' H[:nx,:nx] x_N
    s.t. x_0 = x0,  x_{n+1} = A x_n + B u_n + b,  -u_max <= u_n <= u_max
"""

from __future__ import annotations

import math
import time

import casadi as ca
import numpy as np
import scipy.linalg as sla

PEND = {
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
LQR = {"N": 20, "nx": 8, "nu": 4, "n_theta": 248, "dt": 1.0}

MARGIN_MIN = 1e-7      # strict-complementarity margin required for tau_min = 0
NEWTON_TOL = 1e-9      # accepted KKT residual (inf-norm) after refinement
FD_REJECT_SMOOTH = 1e-6
FD_REJECT_BARRIER = 1e-4


# ---------------------------------------------------------------------------
# NLP construction
# ---------------------------------------------------------------------------


def _pendulum_nlp():
    N, T = PEND["N"], PEND["T"]
    dt = T / N
    m, g, l = PEND["m_ball"], PEND["gravity"], PEND["rod_length"]
    Q = np.diag(PEND["Q_diag"])
    R = PEND["R"]
    theta = ca.SX.sym("theta", 1)
    x0p = ca.SX.sym("x0p", 4)

    xs_ = ca.SX.sym("xs_", 4)
    us_ = ca.SX.sym("us_", 1)
    th_ = ca.SX.sym("th_", 1)
    phi, v, om = xs_[1], xs_[2], xs_[3]
    cphi, sphi = ca.cos(phi), ca.sin(phi)
    den = th_ + m - m * cphi * cphi
    f_expl = ca.vertcat(
        v,
        om,
        (-m * l * sphi * om**2 + m * g * cphi * sphi + us_) / den,
        (-m * l * cphi * sphi * om**2 + us_ * cphi + (th_ + m) * g * sphi) / (l * den),
    )
    ode = ca.Function("ode", [xs_, us_, th_], [f_expl])
    k1 = ode(xs_, us_, th_)
    k2 = ode(xs_ + dt / 2 * k1, us_, th_)
    k3 = ode(xs_ + dt / 2 * k2, us_, th_)
    k4 = ode(xs_ + dt * k3, us_, th_)
    step = ca.Function("step", [xs_, us_, th_], [xs_ + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)])

    X = [ca.SX.sym(f"x{n}", 4) for n in range(N + 1)]
    U = [ca.SX.sym(f"u{n}", 1) for n in range(N)]
    parts = []
    for n in range(N):
        parts += [X[n], U[n]]
    parts.append(X[N])
    z = ca.vertcat(*parts)

    f = 0
    for n in range(N):
        f += dt * (theta * (X[n].T @ Q @ X[n]) + R * U[n] ** 2)
    f += theta * (X[N].T @ Q @ X[N])

    geq = [X[0] - x0p]
    for n in range(N):
        geq.append(X[n + 1] - step(X[n], U[n], theta))
    hin = []
    fmax, pb = PEND["f_max"], PEND["path_bound"]
    for n in range(N):
        hin += [U[n] - fmax, -fmax - U[n]]
    for n in range(1, N):
        hin += [theta * X[n][0] - pb, -pb - theta * X[n][0]]

    return {
        "z": z,
        "theta": theta,
        "data": x0p,
        "f": f,
        "g": ca.vertcat(*geq),
        "h": ca.vertcat(*hin),
        "u0_idx": [4],
        "step": step,
        "N": N,
    }


def _lqr_nlp():
    N, nx, nu = LQR["N"], LQR["nx"], LQR["nu"]
    n_a, n_b, n_bias, n_h = nx * nx, nx * nu, nx, (nx + nu) * (nx + nu)
    theta = ca.SX.sym("theta", n_a + n_b + n_bias + n_h)
    data = ca.SX.sym("data", nx + 1)  # x0 and u_max
    A = ca.reshape(theta[:n_a], nx, nx)
    B = ca.reshape(theta[n_a : n_a + n_b], nx, nu)
    bias = theta[n_a + n_b : n_a + n_b + n_bias]
    H = ca.reshape(theta[n_a + n_b + n_bias :], nx + nu, nx + nu)
    x0p, umax = data[:nx], data[nx]
    X = [ca.SX.sym(f"x{n}", nx) for n in range(N + 1)]
    U = [ca.SX.sym(f"u{n}", nu) for n in range(N)]
    parts = []
    for n in range(N):
        parts += [X[n], U[n]]
    parts.append(X[N])
    z = ca.vertcat(*parts)
    f = 0
    for n in range(N):
        xu = ca.vertcat(X[n], U[n])
        f += LQR["dt"] * (xu.T @ H @ xu)
    f += X[N].T @ H[:nx, :nx] @ X[N]
    geq = [X[0] - x0p]
    for n in range(N):
        geq.append(X[n + 1] - (A @ X[n] + B @ U[n] + bias))
    hin = []
    for n in range(N):
        hin += [U[n] - umax, -umax - U[n]]
    return {
        "z": z,
        "theta": theta,
        "data": data,
        "f": f,
        "g": ca.vertcat(*geq),
        "h": ca.vertcat(*hin),
        "u0_idx": list(range(nx, nx + nu)),
        "N": N,
    }


class KKT:
    """KKT residual, IPOPT solver factory, Newton refinement and IFT."""

    def __init__(self, nlp: dict):
        self.nlp = nlp
        z, th, d = nlp["z"], nlp["theta"], nlp["data"]
        g, h, f = nlp["g"], nlp["h"], nlp["f"]
        self.nz, self.ng, self.nh, self.nth = z.shape[0], g.shape[0], h.shape[0], th.shape[0]
        self.nw = self.nz + self.ng + self.nh
        lam = ca.SX.sym("lam", self.ng)
        mu = ca.SX.sym("mu", self.nh)
        act = ca.SX.sym("act", self.nh)
        tau = ca.SX.sym("tau", 1)
        smooth = ca.SX.sym("smooth", 1)
        lag = f + ca.dot(lam, g) + ca.dot(mu, h)
        grad = ca.gradient(lag, z)
        r3 = smooth * (mu * h + tau) + (1 - smooth) * (act * h + (1 - act) * mu)
        F = ca.vertcat(grad, g, r3)
        w = ca.vertcat(z, lam, mu)
        self.F = ca.Function("F", [w, th, d, act, tau, smooth], [F])
        self.FJ = ca.Function(
            "FJ", [w, th, d, act, tau, smooth], [F, ca.jacobian(F, w), ca.jacobian(F, th)]
        )
        self.fh = ca.Function("fh", [z, th, d], [f, h])
        self._ipopt: dict = {}

    def ipopt(self, tau: float):
        key = float(tau)
        if key not in self._ipopt:
            nlp = self.nlp
            prob = {
                "x": nlp["z"],
                "p": ca.vertcat(nlp["theta"], nlp["data"]),
                "f": nlp["f"],
                "g": ca.vertcat(nlp["g"], nlp["h"]),
            }
            opts = {
                "print_time": False,
                "ipopt.print_level": 0,
                "ipopt.sb": "yes",
                "ipopt.tol": 1e-10,
                "ipopt.max_iter": 3000,
                "ipopt.nlp_scaling_method": "none",
                "ipopt.bound_relax_factor": 0.0,
            }
            if key > 0.0:
                opts["ipopt.mu_target"] = key
            self._ipopt[key] = ca.nlpsol(f"ipopt_{len(self._ipopt)}", "ipopt", prob, opts)
        return self._ipopt[key]

    def objective(self, z, th, d, tau):
        fv, hv = self.fh(z, th, d)
        fv = float(fv)
        hv = np.asarray(hv.full()).ravel()
        if tau > 0.0:
            if np.any(hv >= 0.0):
                return math.inf
            fv -= tau * float(np.sum(np.log(-hv)))
        return fv

    def solve_ipopt(self, z_init, th, d, tau):
        solver = self.ipopt(tau)
        lbg = np.concatenate([np.zeros(self.ng), -np.inf * np.ones(self.nh)])
        ubg = np.zeros(self.ng + self.nh)
        res = solver(x0=z_init, p=np.concatenate([np.atleast_1d(th), d]), lbg=lbg, ubg=ubg)
        stats = solver.stats()
        z = np.asarray(res["x"].full()).ravel()
        lam_g = np.asarray(res["lam_g"].full()).ravel()
        return z, lam_g[: self.ng], lam_g[self.ng :], bool(stats.get("success", False)), str(stats.get("return_status"))

    def newton(self, w, th, d, act, tau, smooth, max_iter=40):
        best_norm, best_w = math.inf, w.copy()
        prev = math.inf
        for _ in range(max_iter):
            F, J, _ = self.FJ(w, th, d, act, tau, smooth)
            F = np.asarray(F.full()).ravel()
            norm = float(np.max(np.abs(F)))
            if not math.isfinite(norm):
                break
            if norm < best_norm:
                best_norm, best_w = norm, w.copy()
            if norm < 1e-13 or (norm < 1e-10 and norm > 0.5 * prev):
                break
            prev = norm
            try:
                dw = np.linalg.solve(np.asarray(J.full()), -F)
            except np.linalg.LinAlgError:
                break
            if not np.all(np.isfinite(dw)):
                break
            alpha = 1.0
            if smooth > 0.5:
                mu = w[self.nz + self.ng :]
                dmu = dw[self.nz + self.ng :]
                neg = dmu < 0
                if np.any(neg):
                    alpha = min(1.0, 0.995 * float(np.min(-mu[neg] / dmu[neg])))
            w = w + alpha * dw
        return best_w, best_norm

    def adjoint(self, w, th, d, act, tau, smooth, seed_w):
        _, J, Jth = self.FJ(w, th, d, act, tau, smooth)
        J = np.asarray(J.full())
        Jth = np.asarray(Jth.full())
        lu = sla.lu_factor(J)
        y = sla.lu_solve(lu, seed_w, trans=1)
        Jl = J.astype(np.longdouble).T
        bl = seed_w.astype(np.longdouble)
        yl = y.astype(np.longdouble)
        for _ in range(3):
            r = bl - Jl @ yl
            dy = sla.lu_solve(lu, np.asarray(r, dtype=np.float64), trans=1)
            yl = yl + dy.astype(np.longdouble)
        grad = -(Jth.astype(np.longdouble).T @ yl)
        return np.asarray(grad, dtype=np.float64), None


# ---------------------------------------------------------------------------
# Solving one instance
# ---------------------------------------------------------------------------


def _solve_instance(kkt: KKT, th, d, tau, inits):
    """Return dict(w, act, smooth, u0, objective, ...) or a rejection reason string."""
    nz, ng, nh = kkt.nz, kkt.ng, kkt.nh
    smooth = 1.0 if tau > 0.0 else 0.0
    candidates = []
    for z_init in inits:
        try:
            z, lam, mu, ok, ret = kkt.solve_ipopt(z_init, th, d, tau)
        except Exception as exc:  # pragma: no cover - diagnostic only
            candidates.append({"error": str(exc)})
            continue
        if not np.all(np.isfinite(z)):
            continue
        _, hv = kkt.fh(z, th, d)
        hv = np.asarray(hv.full()).ravel()
        if smooth > 0.5:
            act = np.zeros(nh)
            mu = np.maximum(mu, 1e-16)
        else:
            act = (np.maximum(mu, 0.0) > -hv).astype(float)
            mu = np.where(act > 0.5, mu, 0.0)
        w0 = np.concatenate([z, lam, mu])
        try:
            w, res = kkt.newton(w0, th, d, act, tau, smooth)
        except Exception as exc:
            candidates.append({"ipopt": ret, "rejected": f"newton_exception: {exc}"})
            continue
        if res > NEWTON_TOL:
            candidates.append({"ipopt": ret, "newton_res": res, "rejected": "newton"})
            continue
        zr = w[:nz]
        mur = w[nz + ng :]
        _, hr = kkt.fh(zr, th, d)
        hr = np.asarray(hr.full()).ravel()
        if smooth > 0.5:
            if np.any(hr >= 0.0) or np.any(mur <= 0.0):
                candidates.append({"ipopt": ret, "rejected": "barrier_interior"})
                continue
            margin = float(min(np.min(-hr), np.min(mur)))
        else:
            a = act > 0.5
            m_act = float(np.min(mur[a])) if np.any(a) else math.inf
            m_inact = float(np.min(-hr[~a])) if np.any(~a) else math.inf
            margin = min(m_act, m_inact)
            if margin < MARGIN_MIN:
                candidates.append({"ipopt": ret, "rejected": "degenerate_active_set", "margin": margin})
                continue
        candidates.append(
            {
                "w": w,
                "act": act,
                "smooth": smooth,
                "u0": zr[kkt.nlp["u0_idx"]].copy(),
                "objective": kkt.objective(zr, th, d, tau),
                "newton_res": res,
                "margin": margin,
                "ipopt": ret,
            }
        )
    good = [c for c in candidates if "w" in c]
    if not good:
        return "no_converged_kkt_point", candidates
    good.sort(key=lambda c: c["objective"])
    best = good[0]
    distinct = 0
    for other in good[1:]:
        du = float(np.max(np.abs(other["u0"] - best["u0"])))
        if du > 1e-6 * max(1.0, float(np.max(np.abs(best["u0"])))):
            distinct += 1
            rel_gap = (other["objective"] - best["objective"]) / max(1.0, abs(best["objective"]))
            if rel_gap < 1e-7:
                return "ambiguous_global_minimum", candidates
    best["n_local_minima_seen"] = 1 + distinct
    return best, candidates


def _u0_of(kkt: KKT, w0, th, d, act, tau, smooth):
    try:
        w, res = kkt.newton(w0, th, d, act, tau, smooth)
    except Exception:
        return None
    if res > NEWTON_TOL:
        return None
    return w[: kkt.nz][kkt.nlp["u0_idx"]]


WARM_START_DTHETA = 1e-3


def _continue_branch(kkt: KKT, sol, th_new, d, tau):
    """Primal solution on the same branch at a neighbouring parameter, or None.

    Newton on the same KKT system (same active set for tau_min = 0, smoothed
    system for tau_min > 0) from the instance's solution; rejected if the active
    set / interior is not consistent at the new parameter."""
    try:
        w, res = kkt.newton(sol["w"], th_new, d, sol["act"], tau, sol["smooth"])
    except Exception:
        return None
    if res > NEWTON_TOL:
        return None
    nz, ng = kkt.nz, kkt.ng
    z, mu = w[:nz], w[nz + ng :]
    _, h = kkt.fh(z, th_new, d)
    h = np.asarray(h.full()).ravel()
    if sol["smooth"] > 0.5:
        if np.any(h >= 0.0) or np.any(mu <= 0.0):
            return None
    else:
        a = sol["act"] > 0.5
        if (np.any(a) and np.min(mu[a]) <= 0.0) or (np.any(~a) and np.min(-h[~a]) <= 0.0):
            return None
    return z


def _pendulum_guess(kkt: KKT, sol, theta, d, tau, index):
    """Warm start = solution on the same branch at theta -/+ 1e-3 (paper's sweep)."""
    N = kkt.nlp["N"]
    sign = 1.0 if index % 2 == 0 else -1.0
    for s in (sign, -sign):
        th_prev = theta - s * WARM_START_DTHETA
        z = _continue_branch(kkt, sol, np.array([th_prev]), d, tau)
        if z is None:
            continue
        xs = [[float(v) for v in z[5 * n : 5 * n + 4]] for n in range(N + 1)]
        us = [[float(z[5 * n + 4])] for n in range(N)]
        return {"theta": th_prev, "x": xs, "u": us}
    return None


def _richardson_directional(kkt, sol, th, d, tau, direction, seed_u0, h):
    vals = []
    for step in (h, h / 2.0):
        up = _u0_of(kkt, sol["w"], th + step * direction, d, sol["act"], tau, sol["smooth"])
        dn = _u0_of(kkt, sol["w"], th - step * direction, d, sol["act"], tau, sol["smooth"])
        if up is None or dn is None:
            return None
        vals.append(float(np.dot(seed_u0, (up - dn) / (2.0 * step))))
    return (4.0 * vals[1] - vals[0]) / 3.0


# ---------------------------------------------------------------------------
# Instance generators
# ---------------------------------------------------------------------------


def _pendulum_rollout(step, x0, theta, N):
    xs = [np.asarray(x0, dtype=float)]
    for _ in range(N):
        nxt = np.asarray(step(xs[-1], 0.0, theta).full()).ravel()
        if not np.all(np.isfinite(nxt)) or np.max(np.abs(nxt)) > 1e3:
            nxt = xs[-1].copy()
        xs.append(nxt)
    return xs


def _pendulum_inits(nlp, x0, theta):
    N = nlp["N"]
    rollout = _pendulum_rollout(nlp["step"], x0, theta, N)
    inits = []
    for xs in (rollout, [np.asarray(x0, dtype=float)] * (N + 1)):
        parts = []
        for n in range(N):
            parts += [xs[n], np.zeros(1)]
        parts.append(xs[N])
        inits.append(np.concatenate(parts))
    lin = [np.asarray(x0, dtype=float) * (1.0 - n / N) for n in range(N + 1)]
    parts = []
    for n in range(N):
        parts += [lin[n], np.zeros(1)]
    parts.append(lin[N])
    inits.append(np.concatenate(parts))
    return inits


def _draw_pendulum(rng, smoothed: bool):
    if rng.random() < 0.5:
        x0 = [0.0, math.pi / 2.0, 0.0, 0.0]
        theta = float(rng.uniform(0.8, 1.5))
    else:
        x0 = [
            float(rng.uniform(-0.25, 0.25)),
            float(math.pi / 2.0 + rng.uniform(-0.35, 0.35)),
            float(rng.uniform(-0.5, 0.5)),
            float(rng.uniform(-0.5, 0.5)),
        ]
        theta = float(rng.uniform(0.6, 1.5))
    tau = float(rng.choice([1e-4, 1e-3, 1e-2])) if smoothed else 0.0
    return theta, x0, tau


def _draw_lqr(rng, index: int):
    nx, nu = LQR["nx"], LQR["nu"]
    A = np.eye(nx) + 0.2 * rng.standard_normal((nx, nx))
    B = rng.standard_normal((nx, nu))
    b = rng.standard_normal(nx)
    H = np.eye(nx + nu)
    theta = np.concatenate([A.flatten(order="F"), B.flatten(order="F"), b, H.flatten(order="F")])
    x0 = rng.standard_normal(nx)
    u_max = 1e4 if index % 2 == 0 else 1.0
    seed = rng.standard_normal(nu)
    return theta, x0, u_max, seed


def build_pendulum(rng, count: int, smoothed: bool, prefix: str, log=print):
    nlp = _pendulum_nlp()
    kkt = KKT(nlp)
    instances, answers, diags = [], {}, {}
    rejected: dict[str, int] = {}
    attempts = 0
    t0 = time.time()
    while len(instances) < count and attempts < 4 * count:
        attempts += 1
        theta, x0, tau = _draw_pendulum(rng, smoothed)
        th = np.array([theta])
        d = np.array(x0)
        try:
            sol, cands = _solve_instance(kkt, th, d, tau, _pendulum_inits(nlp, x0, theta))
            if isinstance(sol, str):
                rejected[sol] = rejected.get(sol, 0) + 1
                continue
            seed_w = np.zeros(kkt.nw)
            seed_w[nlp["u0_idx"][0]] = 1.0
            grad, cond = kkt.adjoint(sol["w"], th, d, sol["act"], tau, sol["smooth"], seed_w)
        except Exception as exc:
            key = f"exception:{type(exc).__name__}"
            rejected[key] = rejected.get(key, 0) + 1
            continue
        sens = float(grad[0])
        h = 1e-4 if tau == 0.0 else 1e-5
        fd = _richardson_directional(kkt, sol, th, d, tau, np.array([1.0]), np.array([1.0]), h)
        fd_rel = math.inf if fd is None else abs(fd - sens) / max(1.0, abs(sens))
        limit = FD_REJECT_SMOOTH if tau == 0.0 else FD_REJECT_BARRIER
        if not (fd_rel <= limit) or not math.isfinite(sens):
            rejected["fd_cross_check"] = rejected.get("fd_cross_check", 0) + 1
            continue
        guess = _pendulum_guess(kkt, sol, theta, d, tau, len(instances))
        if guess is None:
            rejected["no_branch_warm_start"] = rejected.get("no_branch_warm_start", 0) + 1
            continue
        iid = f"{prefix}{len(instances):04d}"
        instances.append({"id": iid, "theta": theta, "x0": x0, "tau_min": tau, "initial_guess": guess})
        answers[iid] = {"u0": float(sol["u0"][0]), "du0_dtheta": sens}
        diags[iid] = {
            "fd_rel_diff": fd_rel,
            "kkt_cond": cond,
            "margin": sol["margin"],
            "newton_res": sol["newton_res"],
            "n_local_minima_seen": sol["n_local_minima_seen"],
            "n_active": int(np.sum(sol["act"])),
        }
    log(
        f"[groundtruth] {prefix}: {len(instances)}/{count} accepted from {attempts} draws "
        f"in {time.time() - t0:.1f}s; rejected={rejected}"
    )
    if len(instances) < count:
        raise RuntimeError(f"could only build {len(instances)} of {count} pendulum instances")
    return instances, answers, diags


def build_lqr(rng, count: int, prefix: str, log=print):
    nlp = _lqr_nlp()
    kkt = KKT(nlp)
    nx = LQR["nx"]
    instances, answers, diags = [], {}, {}
    rejected: dict[str, int] = {}
    attempts = 0
    t0 = time.time()
    while len(instances) < count and attempts < 4 * count:
        index = len(instances)
        attempts += 1
        theta, x0, u_max, seed = _draw_lqr(rng, index)
        d = np.concatenate([x0, [u_max]])
        z_init = np.zeros(kkt.nz)
        z_init[:nx] = x0
        try:
            sol, _ = _solve_instance(kkt, theta, d, 0.0, [z_init])
            if isinstance(sol, str):
                rejected[sol] = rejected.get(sol, 0) + 1
                continue
            seed_w = np.zeros(kkt.nw)
            seed_w[nlp["u0_idx"]] = seed
            grad, cond = kkt.adjoint(sol["w"], theta, d, sol["act"], 0.0, 0.0, seed_w)
        except Exception as exc:
            key = f"exception:{type(exc).__name__}"
            rejected[key] = rejected.get(key, 0) + 1
            continue
        direction = rng.standard_normal(theta.shape[0])
        direction /= np.linalg.norm(direction)
        fd = _richardson_directional(kkt, sol, theta, d, 0.0, direction, seed, 1e-4)
        exact_dir = float(np.dot(grad, direction))
        fd_rel = math.inf if fd is None else abs(fd - exact_dir) / max(1.0, float(np.linalg.norm(grad)))
        if not (fd_rel <= FD_REJECT_SMOOTH) or not np.all(np.isfinite(grad)):
            rejected["fd_cross_check"] = rejected.get("fd_cross_check", 0) + 1
            continue
        iid = f"{prefix}{len(instances):04d}"
        instances.append(
            {
                "id": iid,
                "theta": theta.tolist(),
                "x0": x0.tolist(),
                "u_max": u_max,
                "seed_u0": seed.tolist(),
            }
        )
        answers[iid] = {"u0": [float(v) for v in sol["u0"]], "adjoint": grad.tolist()}
        diags[iid] = {
            "fd_rel_diff": fd_rel,
            "kkt_cond": cond,
            "margin": sol["margin"],
            "newton_res": sol["newton_res"],
            "n_active": int(np.sum(sol["act"])),
        }
    log(
        f"[groundtruth] {prefix}: {len(instances)}/{count} accepted from {attempts} draws "
        f"in {time.time() - t0:.1f}s; rejected={rejected}"
    )
    if len(instances) < count:
        raise RuntimeError(f"could only build {len(instances)} of {count} LQR instances")
    return instances, answers, diags


def pendulum_problem_spec(smoothed: bool) -> dict:
    spec = dict(PEND)
    spec["name"] = "parametric_pendulum_on_cart"
    spec["integrator"] = "RK4, dt = T/N, one step per interval"
    spec["cost"] = "sum_{n<N} dt*(theta*x'Qx + R*u^2) + theta*x_N'Qx_N"
    spec["constraints"] = "x_0 = x0; |u_n| <= f_max (n<N); |theta*p_n| <= path_bound (1<=n<N)"
    spec["smoothing"] = (
        "tau_min > 0: smoothed interior-point KKT system, mu_i*h_i = -tau_min for every one-sided inequality"
        if smoothed
        else "tau_min = 0: exact KKT conditions"
    )
    spec["output"] = {"u0": "float", "du0_dtheta": "float"}
    return spec


def lqr_problem_spec() -> dict:
    spec = dict(LQR)
    spec["name"] = "bounded_lqr"
    spec["theta_layout"] = "[vec(A) 64, vec(B) 32, b 8, vec(H) 144], column-major vec"
    spec["cost"] = "sum_{n<N} dt*[x;u]'H[x;u] + x_N' H[:nx,:nx] x_N"
    spec["constraints"] = "x_0 = x0; x_{n+1} = A x_n + B u_n + b; |u_n| <= u_max (elementwise)"
    spec["output"] = {"u0": "list of nu floats", "adjoint": "list of 248 floats = d(seed_u0 . u0)/d theta"}
    return spec


def build_split(seed: int, n_pend: int, n_smooth: int, n_lqr: int, prefixes=("ps", "pt", "lq"), log=print,
                checkpoint_path: str | None = None) -> dict:
    """Build instances + answers. Resumable: after each experiment the partial
    result and the RNG state are saved to ``checkpoint_path`` (same sequence of
    draws as an uninterrupted build)."""
    import json
    import os

    rng = np.random.default_rng(seed)
    out = {"format_version": 1, "experiments": {}}
    key = [seed, n_pend, n_smooth, n_lqr, list(prefixes)]
    if checkpoint_path and os.path.exists(checkpoint_path):
        try:
            with open(checkpoint_path, "r", encoding="utf-8") as handle:
                ck = json.load(handle)
            if ck.get("key") == key:
                out = ck["out"]
                rng.bit_generator.state = ck["rng_state"]
                log(f"[groundtruth] resuming from checkpoint with {sorted(out['experiments'])}")
        except Exception as exc:
            log(f"[groundtruth] ignoring unreadable checkpoint: {exc}")

    def save():
        if checkpoint_path:
            tmp = checkpoint_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump({"key": key, "out": out, "rng_state": rng.bit_generator.state}, handle)
            os.replace(tmp, checkpoint_path)

    for exp, smoothed, count, prefix in (
        ("pendulum_sensitivity_accuracy", False, n_pend, prefixes[0]),
        ("pendulum_smoothed_sensitivity", True, n_smooth, prefixes[1]),
    ):
        if exp in out["experiments"]:
            continue
        inst, ans, diag = build_pendulum(rng, count, smoothed, prefix, log=log)
        out["experiments"][exp] = {
            "problem": pendulum_problem_spec(smoothed),
            "instances": inst,
            "answers": ans,
            "diagnostics": diag,
        }
        save()
    if "bounded_lqr_adjoint_accuracy" not in out["experiments"]:
        inst, ans, diag = build_lqr(rng, n_lqr, prefixes[2], log=log)
        out["experiments"]["bounded_lqr_adjoint_accuracy"] = {
            "problem": lqr_problem_spec(),
            "instances": inst,
            "answers": ans,
            "diagnostics": diag,
        }
    if checkpoint_path and os.path.exists(checkpoint_path):
        os.remove(checkpoint_path)
    return out
