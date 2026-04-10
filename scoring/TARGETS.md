# Evaluation Targets

## Primary Target

### Experiment: `pendulum_sensitivity_accuracy`
- **What it tests**: The packaged method uses a reduced but faithful pendulum OCP derived from Appendix A.10 (`N=20`, `T=1.0`, cart-pole system) with parametric cost, dynamics, and constraints. It measures whether the exact-Hessian sensitivity computation matches finite differences at a reference parameter value.
- **Primary metric**: `sensitivity_max_error`
- **Direction**: Lower is better.
- **How to run**: `scripts/reproduce.sh`, or `scripts/method.sh` followed by `scripts/evaluate.sh`
- **Score entry**: `scores.json -> experiments -> pendulum_sensitivity_accuracy`

## Constraint Targets

### Experiment: `bounded_lqr_umax_high`
- **What it tests**: Reduced-scale bounded LQR timing benchmark with `N=20`, `nx=8`, `nu=4`, `u_max=10^4`, and `n_batch=128`. This captures the efficiency side of the paper's claim.
- **Primary metric**: `solve_and_sens_time_ms`
- **Direction**: Lower is better.
- **How to run**: `scripts/reproduce.sh`, or `scripts/method.sh` followed by `scripts/evaluate.sh`
- **Score entry**: `scores.json -> experiments -> bounded_lqr_umax_high`

### Experiment: `bounded_lqr_umax_low`
- **What it tests**: Reduced-scale bounded LQR timing benchmark with `N=20`, `nx=8`, `nu=4`, `u_max=1.0`, and `n_batch=128`. This tests efficiency when tight constraints are active.
- **Primary metric**: `solve_and_sens_time_ms`
- **Direction**: Lower is better.
- **How to run**: `scripts/reproduce.sh`, or `scripts/method.sh` followed by `scripts/evaluate.sh`
- **Score entry**: `scores.json -> experiments -> bounded_lqr_umax_low`

## Ablation Target

### Experiment: `pendulum_sensitivity_accuracy`
- **What it tests**: The same pendulum experiment also contains the key ablation: replacing the exact-Hessian sensitivity computation with the Gauss-Newton approximation should degrade sensitivity accuracy.
- **Primary metric**: `sensitivity_max_error` for method `gauss_newton_approx`
- **Direction**: Higher than the exact-Hessian error indicates the expected ablation failure.
- **How to run**: `scripts/reproduce.sh`, `scripts/method.sh` followed by `scripts/evaluate.sh`, or `bash scripts/baseline.sh`
- **Score entry**: `scores.json -> experiments -> pendulum_sensitivity_accuracy -> results -> gauss_newton_approx`
