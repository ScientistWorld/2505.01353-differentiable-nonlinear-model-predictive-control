# Evaluation

## Overview

The workspace evaluates candidate methods on one scored accuracy experiment and two context-only timing diagnostics. All methods are judged by the same output contract in `scoring/scores.json`, but the composite gym score uses only hardware-independent metrics.

## Metrics

### 1. Sensitivity Accuracy

- **Experiment**: `pendulum_sensitivity_accuracy`
- **Quantity measured**: Maximum absolute difference between the method's reported local sensitivity and a finite-difference reference on a parameterized pendulum optimal control problem.
- **Direction**: Lower is better.
- **Purpose**: This is the primary scientific target. It checks whether the method produces trustworthy local sensitivities on a nonlinear constrained problem.

### 2. Solve-Plus-Sensitivity Runtime Diagnostics

- **Experiments**: `bounded_lqr_umax_high`, `bounded_lqr_umax_low`
- **Quantity measured**: Total wall-clock time in milliseconds to solve a batch of bounded linear-quadratic control problems and compute sensitivities.
- **Direction**: Lower is better.
- **Purpose**: These diagnostics record the runtime side of the paper's benchmark, but they are not scored in this gym because wall-clock time varies with hardware and scheduler placement.

## Evaluation Protocol

### Experiment 1: `pendulum_sensitivity_accuracy`

- Use the benchmark's parameterized pendulum control problem.
- Evaluate sensitivity quality against finite differences at the benchmark reference parameter.
- Report `sensitivity_max_error`.

### Experiment 2: `bounded_lqr_umax_high`

- Use the benchmark's batched bounded-LQR setting with a loose control bound.
- Report `solve_and_sens_time_ms` for context. This metric has a zero scoring coefficient.

### Experiment 3: `bounded_lqr_umax_low`

- Use the benchmark's batched bounded-LQR setting with a tight control bound.
- Report `solve_and_sens_time_ms` for context. This metric has a zero scoring coefficient.

## Reporting Rules

1. Use the same benchmark formulations and metric definitions as the packaged workspace.
2. Treat runtime values as diagnostic context only unless a future evaluator adds a machine-independent efficiency proxy such as operation count, iterations, or samples processed.
3. Do not substitute a different task while keeping the same experiment name.
