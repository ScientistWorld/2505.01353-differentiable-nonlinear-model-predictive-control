# Evaluation Targets

Reference values come from the reproduced paper method (`acados_exact_hessian`: two-solver acados IFT sensitivities) and its baselines on the hidden test (`scoring/scores_test.json`). Visible-train values are in parentheses. Each metric is listed as `frac_sens_accurate / mean_log10_sens_rel_err / frac_u0_accurate`.

## Primary target: `pendulum_sensitivity_accuracy` (weight 0.5)

- **Tests:** exact solution-map sensitivity `d u0/d theta` of the parametric pendulum OCP (paper Sec. 5.1).
- **Benefit metrics:** `frac_sens_accurate` (higher, primary) and `mean_log10_sens_rel_err` (lower).
- **Constraint metric:** `frac_u0_accurate` (higher). The derivative must belong to the correct solution of the stated problem.
- **Reference:** `1.000 / -7.77 / 1.000` (train `1.000 / -7.90 / 1.000`).
- **Baselines:**
  - Gauss–Newton Hessian IFT: `0.005 / -0.16 / 1.000`.
  - IFT without inequality constraints: `0.000 / 0.00 / 0.000`.
- **Headroom:** precision. The reference median error is about 1e-7.8 against a floor of 1e-10. A tighter nominal solve reaches -9.20 and lower sensitivity clipping -8.78.

## Secondary target: `pendulum_smoothed_sensitivity` (weight 0.2)

- **Tests:** derivative of the barrier-smoothed solution map (`tau_min` in {1e-4, 1e-3, 1e-2}; paper eq. 10/23, Thm. 3, Fig. 2).
- **Metrics:** same three as above.
- **Reference:** `0.811 / -5.41 / 0.989` (train `0.778 / -5.10 / 1.000`).
- **Baselines:** Gauss–Newton `0.000 / -0.54 / 0.989`; unconstrained `0.000 / 0.00 / 0.000`.
- **Headroom:** large. The reference's smoothed sensitivities carry a systematic error that grows with `tau_min` (relative 1e-4 to 2e-3 at `tau_min = 1e-2`). Finite differences of the very same solutions are accurate to about 1e-7.

## Secondary target: `bounded_lqr_adjoint_accuracy` (weight 0.3)

- **Tests:** adjoint sensitivity with respect to 248 LQR parameters (paper Sec. 5.2 / App. A.11), `u_max` in {1, 1e4}.
- **Metrics:** same three.
- **Reference:** `0.971 / -8.79 / 1.000` (train `0.971 / -8.88 / 0.986`).
- **Baselines:** Gauss–Newton, which coincides with the exact Hessian for this convex QP: `0.971 / -8.79 / 1.000`. Unconstrained IFT: `0.586 / -5.86 / 0.586`.
- **Headroom:** the tightly constrained instances (`u_max = 1`). A tighter solve reaches `1.000 / -9.97 / 1.000`.

## Not scored

The paper's wall-clock speed-ups (Table 1, Table 2, Fig. 3) are not scored because they depend on hardware. They are kept for context in `scoring/reference.json`.
