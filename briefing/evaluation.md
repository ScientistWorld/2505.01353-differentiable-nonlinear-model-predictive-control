# Evaluation

## Overview

The workspace evaluates candidate methods on one accuracy-focused experiment and two efficiency-focused experiments. All methods are judged by the same output contract in `scoring/scores.json`.

## Metrics

### 1. Sensitivity Accuracy

- **Experiment**: `pendulum_sensitivity_accuracy`
- **Quantity measured**: Maximum absolute difference between the method's reported local sensitivity and a finite-difference reference on a parameterized pendulum optimal control problem.
- **Direction**: Lower is better.
- **Purpose**: This is the primary scientific target. It checks whether the method produces trustworthy local sensitivities on a nonlinear constrained problem.

### 2. Solve-Plus-Sensitivity Runtime

- **Experiments**: `bounded_lqr_umax_high`, `bounded_lqr_umax_low`
- **Quantity measured**: Total wall-clock time in milliseconds to solve a batch of bounded linear-quadratic control problems and compute sensitivities.
- **Direction**: Lower is better.
- **Purpose**: These are efficiency benchmarks. They check whether the method remains practical when sensitivities must be computed repeatedly across many related problems.

## Evaluation Protocol

### Experiment 1: `pendulum_sensitivity_accuracy`

- Use the benchmark's parameterized pendulum control problem.
- Evaluate sensitivity quality against finite differences at the benchmark reference parameter.
- Report `sensitivity_max_error`.

### Experiment 2: `bounded_lqr_umax_high`

- Use the benchmark's batched bounded-LQR setting with a loose control bound.
- Report `solve_and_sens_time_ms`.

### Experiment 3: `bounded_lqr_umax_low`

- Use the benchmark's batched bounded-LQR setting with a tight control bound.
- Report `solve_and_sens_time_ms`.

## Reporting Rules

1. Use the same benchmark formulations and metric definitions as the packaged workspace.
2. If hardware differs from the reproduction environment, report that difference clearly when interpreting runtime results.
3. Do not substitute a different task while keeping the same experiment name.
