# Overview

- **Paper ID:** 2505.01353
- **Title:** Differentiable Nonlinear Model Predictive Control
- **Domain:** Optimization / Control Theory / Differentiable Programming
- **TL;DR:** Efficient computation of parametric solution sensitivities for nonlinear MPC using implicit function theorem with interior-point SQP, achieving 3x+ speedups over state-of-the-art differentiable MPC solvers.

## Short Summary

This paper addresses the key challenge of computing parametric solution sensitivities (gradients of optimal solutions with respect to parameters) for general nonlinear programs in model predictive control. The approach combines the implicit function theorem applied to the KKT conditions solved by an interior-point SQP method, with a two-solver strategy: a fast nominal solver for convergence and an exact-Hessian sensitivity solver for accuracy. The implementation in the acados framework exploits the OCP structure via Riccati factorization, achieving significant speedups over prior differentiable MPC implementations like mpc.pytorch and cvxpygen.

## Key Results

- **Pendulum OCP**: Solution sensitivities match finite-difference baselines across parameter range including active-set change boundaries; Gauss-Newton Hessian gives completely wrong results (Remark 3)
- **Bounded LQR**: acados is 3.6x–520x faster than mpc.pytorch and 19x–160x faster than cvxpygen for solving 128 problems with adjoint sensitivities
- **Chain of masses**: Single adjoint sensitivity is ~2.5x faster than full forward Jacobian evaluation

---

# Problem Definition

What problem does this paper address? Write this so that someone with no knowledge of the paper can understand what needs to be solved and how success is measured.

Do NOT describe the paper's method or solution here — only the problem itself. Think about if a future scientist agent try to solve this problem from scratch without knowing what approach the paper took. If you leak the solution, you compromise the benchmark.

## Research Question

The paper addresses the problem of computing **parametric solution sensitivities** — that is, the gradients (derivatives) of the optimal solution of an optimization problem with respect to its parameters. This is critical for combining learning-based methods (neural networks, RL) with model predictive control (MPC), where one needs to backpropagate through an optimization solver.

The challenge is: given an optimal control problem (OCP) of the form:
```
minimize cost(x, u; θ)
subject to dynamics(x, u; θ) = 0
          inequality constraints(x, u; θ) ≤ 0
```
where θ are parameters, compute ∂solution/∂θ efficiently.

This is hard because:
1. The solution involves solving an NLP with inequality constraints
2. At constraint boundaries, the solution map can be nondifferentiable (kinks)
3. Computing exact sensitivities requires the exact Hessian, not just an approximation
4. Existing methods (mpc.pytorch, cvxpygen) are either slow, limited to simple problem forms, or give wrong sensitivities

## Why It Matters

Parametric solution sensitivities are a key building block for:
- Differentiable MPC layers in neural networks
- Learning-enhanced MPC (learning system models, costs, or policies)
- Imitation learning from MPC demonstrations
- Real-time MPC with online adaptation

Without efficient and accurate sensitivity computation, learning-enhanced control cannot achieve the necessary real-time performance, especially on embedded platforms.

## Success Criteria

A successful solution must:
1. **Solve general NLPs**: Support nonlinear cost, nonlinear dynamics, and nonlinear inequality constraints — not just quadratic costs with simple bounds
2. **Compute accurate sensitivities**: Solution sensitivities should match finite-difference baselines
3. **Handle nondifferentiability gracefully**: At active-set changes, provide correct smoothed sensitivities
4. **Be computationally efficient**: Meet or exceed the speed of specialized solvers (3x+ speedup over prior art)
5. **Support both forward and adjoint modes**: Forward for few parameters, adjoint for backpropagation through networks

---

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

---

# Evaluation

How success is measured. Describe only the metrics, targets, and evaluation procedure — do NOT describe the paper's method or how they achieved these results. Think of this as a general evaluation protocol for other scientists trying to solve the same problem, where they should not see this paper's solution.

## Metrics

The paper evaluates on three dimensions:

### 1. Sensitivity Accuracy
- **Metric**: Comparison of computed sensitivities against finite-difference (FD) baselines
- **How computed**: For the highly-parametric OCP, compute ∂u₀*(θ)/∂θ via the method and via finite differences. Report max absolute error.
- **Direction**: Lower error is better (0 = exact match)

### 2. Computational Efficiency (Timing)
- **Metric**: Wall-clock time in milliseconds for solving N batch problems and computing sensitivities
- **How computed**: Time to solve n_batch = 128 bounded LQR problems with N=20, nx=8, nu=4, nθ=248 parameters
- **Comparison**: Reported as speedup factor relative to baseline solvers (mpc.pytorch, cvxpygen/OSQP)
- **Direction**: Lower time is better; speedup > 1 means faster than baseline

### 3. Adjoint Sensitivity Efficiency
- **Metric**: Time for adjoint sensitivity computation vs. full forward Jacobian computation
- **How computed**: Chain-of-masses example with N=40, nx=9, nu=3, nθ=113
- **Direction**: Lower time is better; adjoint should be faster than forward for single-adjoint queries

## Baselines and Targets

The paper compares against two state-of-the-art differentiable MPC solvers:

| Solver | Description | Paper's Reported Speedup |
|--------|-------------|------------------------|
| mpc.pytorch | iLQR-based differentiable MPC | acados 3.6x–520x faster |
| cvxpygen/OSQP | Code-generated QP layers | acados 19x–160x faster |

Key reference timings (acados):
- Bounded LQR nominal solution: 8.5ms (u_max=10⁴), 17.6ms (u_max=1.0)
- Bounded LQR with adjoint sensitivity: 34.5ms (u_max=10⁴), 42.0ms (u_max=1.0)
- Chain example single adjoint: ~0.6ms

## Evaluation Protocol

### Experiment 1: Highly-Parametric OCP (Pendulum)
- **Problem**: Cart-pole with parametric mass, N=50, nx=4, nu=1, nθ=1
- **Test**: Compute sensitivities across θ ∈ [-1.5, 1.5] and compare to finite differences
- **Pass criterion**: Max |error| < 10⁻² (or visual agreement with kinks at active-set changes)

### Experiment 2: Bounded LQR Benchmark
- **Problem**: Linear-quadratic OCP with parametric A,B matrices and control bounds
- **n_batch** = 128 random initial states
- **Test**: Compare solution + adjoint sensitivity timing
- **Pass criterion**: Correct solution convergence + reasonable timing

### Experiment 3: Chain of Masses
- **Problem**: Nonlinear OCP with chain of masses model, N=40, n_masses=3
- **Test**: Compare forward vs adjoint sensitivity computation time
- **Pass criterion**: Adjoint is ~2.5x faster than forward for single-adjoint query

### General Protocol
- All timing experiments should run on the same hardware (or clearly report hardware differences)
- Report mean ± std over multiple batch runs
- Sensitivity accuracy should be validated at multiple θ values, including near active-set change boundaries

---

# Reproduction Log

### Iteration 4: gpt-5.4 (verifier)
- **Milestone**: `core_claim` | **Status**: done
- **GPU**: 0.0h

<details>
<summary>Progress Log</summary>

### [2026-04-05 03:41] - method_runs
- Validated that the acados-based differentiable NMPC pipeline executes end-to-end in this workspace.
- Built the acados solver stack and packaged reusable scripts under `scripts/` and `eval/`.

### [2026-04-05 04:58] - core_claim
- Implemented the paper's two-solver pendulum sensitivity experiment in `eval/evaluator.py`.
- Verified the core claim with a fresh evaluator run: exact-Hessian sensitivity error `0.002597` vs Gauss-Newton error `2.200135` against finite differences.
- Packaged the LQR timing benchmark in the same evaluator so `scripts/evaluate.sh` produces `scoring/scores.json` from actual runs.

### [2026-04-05 05:18] - core_claim
- Audited the previous agent's work and confirmed the implementation is a real acados-based exact-Hessian sensitivity computation, not a surrogate.
- Re-ran `scripts/evaluate.sh` standalone during the audit and reproduced the same core pendulum result: exact `0.002597`, Gauss-Newton `2.200135`.
- Corrected packaging overstatements so the docs now describe the reduced-scale runnable evaluator rather than the full paper-scale settings.

### [2026-04-05 05:33] - core_claim
- Corrected the Section 5.2 bounded-LQR evaluator to stop double-counting solve time in the reported "solution + adjoint sensitivity" metric.
- Restored the benchmark batch size to `n_batch=128` to match the paper's Table 1 setup more closely.
- Updated the job path to rebuild acados in `Release` mode before evaluation and prepared a fresh submission to validate the corrected benchmark.

### [2026-04-05 05:55] - core_claim
- Performed final workspace verification for gym use and confirmed that `eval/` remains independent from `method/` and the problem/evaluation briefing files are method-agnostic enough for from-scratch use.
- Corrected the scoring rubric so the renormalized gym weights prioritize the pendulum core claim over the secondary LQR timing benchmarks.
- Aligned `scoring/TARGETS.md` and `scoring/CONSTRAINTS.md` with the current LQR evaluator configuration (`n_batch=128`) and wrote `VERIFICATION.md`.

### [2026-04-10 01:16] - core_claim
- Re-validated the packaged workspace with `python3 validate.py --compare`; all checks passed.
- Confirmed tracked reproduction deliverables are already pushed to `origin/main`; remaining dirty paths are system/trajectory artifacts outside the method/evaluation package.
- Left `action.yaml` at `done` with milestone `core_claim`.

</details>


---

# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-04-05 03:41] - method_runs
- Validated that the acados-based differentiable NMPC pipeline executes end-to-end in this workspace.
- Built the acados solver stack and packaged reusable scripts under `scripts/` and `eval/`.

### [2026-04-05 04:58] - core_claim
- Implemented the paper's two-solver pendulum sensitivity experiment in `eval/evaluator.py`.
- Verified the core claim with a fresh evaluator run: exact-Hessian sensitivity error `0.002597` vs Gauss-Newton error `2.200135` against finite differences.
- Packaged the LQR timing benchmark in the same evaluator so `scripts/evaluate.sh` produces `scoring/scores.json` from actual runs.

### [2026-04-05 05:18] - core_claim
- Audited the previous agent's work and confirmed the implementation is a real acados-based exact-Hessian sensitivity computation, not a surrogate.
- Re-ran `scripts/evaluate.sh` standalone during the audit and reproduced the same core pendulum result: exact `0.002597`, Gauss-Newton `2.200135`.
- Corrected packaging overstatements so the docs now describe the reduced-scale runnable evaluator rather than the full paper-scale settings.

### [2026-04-05 05:33] - core_claim
- Corrected the Section 5.2 bounded-LQR evaluator to stop double-counting solve time in the reported "solution + adjoint sensitivity" metric.
- Restored the benchmark batch size to `n_batch=128` to match the paper's Table 1 setup more closely.
- Updated the job path to rebuild acados in `Release` mode before evaluation and prepared a fresh submission to validate the corrected benchmark.

### [2026-04-05 05:55] - core_claim
- Performed final workspace verification for gym use and confirmed that `eval/` remains independent from `method/` and the problem/evaluation briefing files are method-agnostic enough for from-scratch use.
- Corrected the scoring rubric so the renormalized gym weights prioritize the pendulum core claim over the secondary LQR timing benchmarks.
- Aligned `scoring/TARGETS.md` and `scoring/CONSTRAINTS.md` with the current LQR evaluator configuration (`n_batch=128`) and wrote `VERIFICATION.md`.

### [2026-04-10 01:16] - core_claim
- Re-validated the packaged workspace with `python3 validate.py --compare`; all checks passed.
- Confirmed tracked reproduction deliverables are already pushed to `origin/main`; remaining dirty paths are system/trajectory artifacts outside the method/evaluation package.
- Left `action.yaml` at `done` with milestone `core_claim`.

### [2026-04-10 01:34] - core_claim
- Fixed a packaging regression in the script chain: `scripts/method.sh` now runs `method/run_reproduction.py` to regenerate raw results, and `scripts/run.sh` / `scripts/reproduce.sh` call method execution before `scripts/evaluate.sh`.
- Preserved the separation rule by keeping `eval/evaluator.py` method-independent; it only validates and scores the method-produced JSON artifact.
- Preparing a CPU test submission to verify the corrected end-to-end path in the compute container.

### [2026-04-10 04:54] - core_claim
- Corrected the runnable script flow so `scripts/method.sh`, `scripts/reproduce.sh`, and `scripts/run.sh` generate `checkpoints/reproduction_results.json` with `method/run_reproduction.py` before scoring it via `eval/evaluator.py`.
- Fixed helper scripts that incorrectly imported experiment functions from `eval/`; the raw acados experiment code now remains in `method/` while `eval/` remains a method-agnostic scorer.
- Lightweight checks passed locally: Python compilation and `python3 validate.py --compare`. Submitting a CPU test job to validate the corrected end-to-end path inside the compute container.

## Stop Justification

- Stopping at `core_claim` is justified because the paper's central qualitative result is reproduced and verified in this workspace: exact-Hessian sensitivities closely match finite differences while the Gauss-Newton approximation is materially worse on the same pendulum OCP.
- The workspace is now packaged as a usable gym: problem and evaluation components are separated from the method implementation, `scripts/evaluate.sh` writes `scoring/scores.json`, and the scoring rubric emphasizes the validated core claim while preserving the LQR timing benchmarks as constraint targets.
- The remaining gaps are completeness-related rather than correctness-related: the LQR timing benchmarks are still reduced-scale and timing-volatile, no local reproduction of external baselines is included, and the Section 5.3 chain-of-masses result is outside the authoritative evaluation path.
