# Paper's Method

How the paper approaches the problem, i.e. the paper's core contributions.

## Key Contribution

The paper proposes an **efficient implementation of parametric solution sensitivity computation** for general nonlinear programs (NLPs) arising in optimal control, using:
1. Implicit function theorem (IFT) applied to the KKT conditions of an interior-point SQP method
2. Exact Hessian computation (not just Gauss-Newton approximation) for correct sensitivities
3. A **two-solver approach**: nominal solver (with approximations for speed) + sensitivity solver (with exact Hessian)
4. Structure-exploiting Riccati factorization via HPIPM/BLASFEO

## Approach

### Mathematical Framework
The NLP solution map z*(θ) is differentiated via IFT applied to the KKT conditions:
- Forward sensitivities: ∂w/∂θ = M⁻¹ · ∂r/∂θ (solve linear system)
- Adjoint sensitivities: s_adj = (∂r/∂θ)ᵀ · M⁻ᵀ · ν (for backpropagation)

Key insight: The KKT matrix M has the same structure as the QP subproblem, so its factorization (Riccati) is reused.

### Two-Solver Approach
1. **Nominal solver**: Uses Gauss-Newton Hessian approximation + regularization for fast convergence
2. **Sensitivity solver**: Uses exact Lagrangian Hessian for accurate sensitivity computation
- Only shares the primal-dual solution (z*, λ*, μ*) between solvers
- Different QP subproblem formulations are allowed

### Smoothed KKT System
Using a barrier parameter τ_min > 0 produces a continuously differentiable approximation of the solution map — valuable for gradient-based learning where the exact map is nondifferentiable at active-set changes.

## Main Claims

1. **Primary**: acados provides correct forward and adjoint sensitivities for general NLPs with inequality constraints, matching finite-difference baselines
2. **Secondary**: Speedups of 3.6x–520x over mpc.pytorch and 19x–160x over cvxpygen for bounded LQR problems
3. **Tertiary**: Adjoint sensitivity computation is ~2.5x faster than full forward Jacobian for single-adjoint queries
4. **Pitfall warning**: Using Gauss-Newton Hessian approximation instead of exact Hessian gives completely wrong sensitivities (shown in Remark 3 and Sec 5.1)

## Reproduction Notes (gym reference, `method/predict.py`)

- **Nominal solver (S1):** acados SQP with the Gauss-Newton Hessian, tolerance 1e-8 (paper Sec. 5.1). It is warm-started from the instance's `initial_guess`, as in the paper's parameter sweep. The HPIPM initial barrier is the paper's `mu0 = 1e3` for smoothed (`tau_min > 0`) solves and `1e-3` otherwise, with the other value as a single fallback.
- **Sensitivity solver (S2-S5):** exact Hessian, classic Riccati, no condensing (as in the paper's code). The primal-dual iterate is transferred, then the solver factorizes and evaluates the forward sensitivity for the one-parameter pendulum (the paper's Figure 2 code). For the 248-parameter LQR, the exact-Hessian solver is both nominal and sensitivity solver (Sec. 5.2), and the adjoint is evaluated.
- **Baselines written by the same predictor:**
  - `gauss_newton_approx`: identical sensitivity solver but with the Gauss-Newton Hessian (Remark 3).
  - `unconstrained_ift`: inequality constraints dropped, then exact-Hessian IFT (related work limited to unconstrained formulations).
