# Evaluation Targets

## Primary Target

### Experiment: `pendulum_sensitivity_accuracy`

- **What it tests**: Whether the method reports accurate local sensitivities on the benchmark's nonlinear pendulum control problem.
- **Primary metric**: `sensitivity_max_error`
- **Direction**: Lower is better.
- **Why it matters**: This is the core scientific claim of the workspace. A method that improves the gym should reduce sensitivity error here without making the benchmark easier.
- **Score entry**: `scores.json -> experiments -> pendulum_sensitivity_accuracy`

## Context Diagnostics

### Experiment: `bounded_lqr_umax_high`

- **What it tests**: Solve-plus-sensitivity runtime on the loose-bound batched LQR benchmark.
- **Primary metric**: `solve_and_sens_time_ms`
- **Direction**: Lower is better.
- **Why it matters**: The paper reports practical runtime, so the workspace preserves the workload for auditability. Its metrics have zero scoring coefficients because wall-clock time is not comparable across ResearchGym hardware.
- **Score entry**: `scores.json -> experiments -> bounded_lqr_umax_high`

### Experiment: `bounded_lqr_umax_low`

- **What it tests**: Solve-plus-sensitivity runtime on the tight-bound batched LQR benchmark.
- **Primary metric**: `solve_and_sens_time_ms`
- **Direction**: Lower is better.
- **Why it matters**: This captures runtime behavior under a more constrained setting for context. Its metrics have zero scoring coefficients because wall-clock time is not comparable across ResearchGym hardware.
- **Score entry**: `scores.json -> experiments -> bounded_lqr_umax_low`
