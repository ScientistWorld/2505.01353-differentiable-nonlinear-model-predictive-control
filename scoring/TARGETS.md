# Evaluation Targets

Reference values come from the reproduced paper method (`acados_exact_hessian`: two-solver acados IFT sensitivities, with the acados sign fix described in `briefing/method.md`) and its baselines on the hidden test (`scoring/scores_test.json`). Visible-train values are in parentheses. Each metric is listed as `frac_sens_accurate / mean_log10_sens_rel_err / frac_u0_accurate`.

All experiments share one compute constraint: each predictor call must stay within `150 + n_instances * c` CPU seconds (`c` = 1.0 for the pendulum experiments, 0.3 for the 248-parameter LQR, 0.15 for the 976-parameter LQR). Otherwise the run fails, with the worst value everywhere. The reference's own usage is 17–21 / 7 / 51 CPU s, against budgets of 300–343 / 192 / 219.

## Primary target: `pendulum_sensitivity_accuracy` (weight 0.35)

- **Tests:** exact solution-map sensitivity `d u0/d theta` of the parametric pendulum OCP (paper Sec. 5.1).
- **Benefit metrics:** `frac_sens_accurate` (higher, primary) and `mean_log10_sens_rel_err` (lower).
- **Constraint metric:** `frac_u0_accurate` (higher). The derivative must belong to the correct solution of the stated problem.
- **Reference:** `1.000 / -7.76 / 1.000` (train `1.000 / -7.91 / 1.000`).
- **Baselines:**
  - Gauss–Newton Hessian IFT: `0.005 / -0.16 / 1.000`.
  - IFT without inequality constraints: `0.000 / 0.00 / 0.000`.
- **Headroom:** precision. The reference median error is about 1e-7.8 against a floor of 1e-10. A tighter nominal solve reaches -9.19, and lower sensitivity clipping -8.80.

## Secondary target: `pendulum_smoothed_sensitivity` (weight 0.15)

- **Tests:** derivative of the barrier-smoothed solution map (`tau_min` in {1e-4, 1e-3, 1e-2}; paper eq. 10/23, Thm. 3, Fig. 2).
- **Metrics:** same three as above.
- **Reference:** `0.989 / -9.67 / 0.989` (train `0.989 / -9.73 / 1.000`). The unpatched acados scored `0.811 / -5.41`.
- **Baselines:** Gauss–Newton `0.000 / -0.54 / 0.989`; unconstrained `0.000 / 0.00 / 0.000`.
- **Headroom:** small. The two failed instances are solutions on a different branch (`frac_u0_accurate` 0.989), and a tighter solve reaches -9.88.

## Secondary target: `pendulum_near_active_set_change` (weight 0.15)

- **Tests:** exact-map sensitivity at parameters close to a constraint switch (smallest strict-complementarity margin 1e-6 to 1e-3).
- **Metrics:** same three.
- **Reference:** `0.120 / -1.77 / 0.967` (train `0.067 / -1.33 / 0.983`).
- **Baselines:** Gauss–Newton `0.000 / -0.24 / 0.967`; unconstrained `0.000 / 0.00 / 0.000`. Central finite differences `0.060 / -1.29` (paper tolerance) and `0.020 / -0.91` (tight solve plus Richardson extrapolation): the steps cross the switch.
- **Headroom:** large. An interior-point iterate at tolerance 1e-8 blurs nearly-active constraints. A tighter nominal solve (1e-10) with clipping 1e-12 reaches `0.500 / -4.41 / 0.973` (paired Δfrac +0.38 ± 0.04). The ground truth is exact.

## Secondary target: `bounded_lqr_adjoint_accuracy` (weight 0.15)

- **Tests:** adjoint sensitivity with respect to 248 LQR parameters (paper Sec. 5.2 / App. A.11), `u_max` in {1, 1e4}.
- **Metrics:** same three.
- **Reference:** `0.971 / -8.79 / 1.000` (train `0.971 / -8.88 / 0.986`).
- **Baselines:** Gauss–Newton, which coincides with the exact Hessian for this convex QP: `0.971 / -8.79 / 1.000`. Unconstrained IFT: `0.586 / -5.86 / 0.586`.
- **Headroom:** the tightly constrained instances (`u_max = 1`). A tighter solve reaches `1.000 / -9.97 / 1.000`.

## Secondary target: `bounded_lqr_large_adjoint` (weight 0.20)

- **Tests:** the same adjoint at `nx = 16, nu = 8`: 976 parameters, two thirds of the instances at `u_max = 1`. Under the compute budget this measures accuracy *and* the paper's efficiency claim.
- **Metrics:** same three.
- **Reference:** `0.952 / -7.92 / 0.989` (train `0.960 / -8.06 / 0.995`).
- **Baselines:** Gauss–Newton `0.952 / -7.92 / 0.989` (equals the exact Hessian here); unconstrained IFT `0.348 / -3.48 / 0.348`. Brute-force finite differences exceed the budget, and the run fails.
- **Headroom:** a tighter solve reaches `1.000 / -9.93 / 1.000` (paired Δlog -2.01 ± 0.09).

## Not scored

The paper's wall-clock speed-ups (Table 1, Table 2, Fig. 3) are not scored because they depend on hardware. They are kept for context in `scoring/reference.json`. Efficiency enters only through the CPU budget.
