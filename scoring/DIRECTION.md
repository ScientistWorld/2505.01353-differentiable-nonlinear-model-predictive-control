# Research Direction

## In Scope

The gym is about **computing useful sensitivities for parameterized optimal control problems** while keeping the benchmark workload fixed. Strong follow-up work should primarily improve this scored target:

- Lower sensitivity error on `pendulum_sensitivity_accuracy`

The bounded-LQR entries record solve-plus-sensitivity runtime for context, but they are not part of the composite score because wall-clock time is hardware-dependent. Valid directions include better numerical stability, better solver engineering, more efficient sensitivity computation, or more robust handling of constrained operating points, as long as the benchmark problems and score definitions stay fixed.

## Out of Scope

The gym is not meant for approaches that sidestep the benchmark by changing the task family. In particular, a future scientist should not:

- Replace the control problem with supervised prediction or policy imitation and still claim the same experiment names
- Score a finite-difference-only brute-force procedure as if it were the same kind of method being benchmarked here
- Change the benchmark instances to make them easier while preserving the original score keys

## Practical Interpretation

This workspace should reward genuine progress on differentiable, parameter-sensitive optimal control benchmarks. Improvements should come from better ways to produce accurate and efficient sensitivities on the same problems, not from redefining the problems.
