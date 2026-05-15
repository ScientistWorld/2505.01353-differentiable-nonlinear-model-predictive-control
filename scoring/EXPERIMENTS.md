# Experiment Overview

## pendulum_sensitivity_accuracy

Measures whether a method can report accurate local sensitivities on a nonlinear constrained control problem. The experiment compares the method's sensitivity output against a finite-difference reference and uses the largest absolute mismatch as the score.

## bounded_lqr_umax_high

Records the wall-clock time for solving a batch of related bounded linear-quadratic control problems and computing sensitivities when the control bound is loose. This is a context-only diagnostic; all of its metric coefficients are zero because wall-clock time is hardware-dependent.

## bounded_lqr_umax_low

Records the same batched solve-plus-sensitivity workload under a tighter control bound, where constraints are more likely to matter. This is a context-only diagnostic; all of its metric coefficients are zero because wall-clock time is hardware-dependent.
