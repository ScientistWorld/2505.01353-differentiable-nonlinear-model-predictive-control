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
