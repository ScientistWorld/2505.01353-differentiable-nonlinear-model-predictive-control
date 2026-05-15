# Scientist Constraints

## Fixed Benchmark Problems

Future scientists must keep the benchmark problem definitions fixed when claiming improvement on the existing experiment names:

- `pendulum_sensitivity_accuracy`: same parameterized pendulum control problem, same horizon and time horizon, same finite-difference reference procedure, and the same reported metric `sensitivity_max_error`.
- `bounded_lqr_umax_high`: same batched bounded-LQR problem dimensions, same loose control-bound setting, and the same reported diagnostic `solve_and_sens_time_ms`.
- `bounded_lqr_umax_low`: same batched bounded-LQR problem dimensions, same tight control-bound setting, and the same reported diagnostic `solve_and_sens_time_ms`.

## Fair Comparison Rules

Scientists may improve the method, implementation, or numerical strategy, but they may not:

- Rename a different task to one of the existing experiment names.
- Reduce the benchmark dimensions, shorten the horizon, shrink the batch size, or loosen the problem while keeping the same score entry.
- Replace the finite-difference reference in the pendulum experiment with a different accuracy target.
- Report runtime for a materially different workload under the same LQR experiment name.

The LQR entries are retained as context-only diagnostics. Their metric coefficients are zero because wall-clock runtime is hardware-dependent; a future scored efficiency target should use a machine-independent proxy.

## Output Contract

Any competing method must still write `scoring/scores.json` with the same experiment names and metric names used by the packaged evaluator. New experiments may be added, but existing ones must remain comparable.
