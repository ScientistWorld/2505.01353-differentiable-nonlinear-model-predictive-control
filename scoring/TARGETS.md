# Evaluation Targets

## Primary: pendulum_sensitivity_accuracy
How accurately does the solver compute parametric sensitivities (du/dtheta) of the optimal control solution?

- **Metric**: sensitivity_max_error (lower is better) — max absolute error between adjoint sensitivity and finite-difference ground truth
- **How to run**: `scripts/evaluate.sh` or `python3 eval/evaluator.py` → runs `run_pendulum_eval()`

### What it tests
The pendulum OCP (N=20, cart-pole system) with parametric cost weight theta. Measures how well the solver's parametric sensitivity computation matches ground-truth finite differences. This is the paper's core claim: exact Hessian gives accurate sensitivities while Gauss-Newton approximation gives wrong results.

## Primary: bounded_lqr_umax_high
How fast can the solver compute optimal controls and parametric sensitivities for bounded LQR problems with loose control limits?

- **Metric**: solve_and_sens_time_ms (lower is better) — wall-clock time to solve n_batch problems with adjoint sensitivities
- **How to run**: `scripts/evaluate.sh` or `python3 eval/evaluator.py` → runs `run_lqr_eval()`

### What it tests
Bounded LQR OCP (N=20, nx=8, nu=4, u_max=10^4). Measures solve + sensitivity time. From paper's Table 1.

## Primary: bounded_lqr_umax_low
How fast can the solver compute optimal controls and parametric sensitivities for bounded LQR problems with tight control limits?

- **Metric**: solve_and_sens_time_ms (lower is better) — wall-clock time to solve n_batch problems with adjoint sensitivities
- **How to run**: `scripts/evaluate.sh` or `python3 eval/evaluator.py` → runs `run_lqr_eval()`

### What it tests
Bounded LQR OCP (N=20, nx=8, nu=4, u_max=1.0). Measures solve + sensitivity time with tight control limits. From paper's Table 1. Note: mpc.pytorch fails to converge consistently in this setting.
