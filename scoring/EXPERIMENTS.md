# Experiment Overview

## pendulum_sensitivity_accuracy

Measures whether a method can report accurate local sensitivities on a nonlinear constrained control problem. The experiment compares the method's sensitivity output against a finite-difference reference and uses the largest absolute mismatch as the score.

## bounded_lqr_umax_high

Measures the efficiency of solving a batch of related bounded linear-quadratic control problems and computing sensitivities when the control bound is loose. This experiment exists to capture the runtime side of the benchmark rather than accuracy alone.

## bounded_lqr_umax_low

Measures the same batched solve-plus-sensitivity workload under a tighter control bound, where constraints are more likely to matter. It checks whether runtime remains practical in a less forgiving setting.
