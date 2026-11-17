# Experiment Overview

All experiments use the same protocol. The evaluator gives a predictor the problem instances of one experiment at a time, without answers. The predictor returns the optimal first control `u0` and a derivative. The evaluator then compares both against its own independent high-precision ground truth. It solves each instance itself, refines the optimality system to machine precision, and differentiates it exactly, cross-checking with finite differences. Each predictor call runs under a CPU budget that fits one solution, one factorization and one backsolve per instance with a wide margin. Full definitions are in `briefing/problem.md` and `briefing/evaluation.md`.

## pendulum_sensitivity_accuracy (weight 0.35)

A nonlinear pendulum-on-cart OCP (50 intervals). One scalar parameter enters the cost, the dynamics and a path constraint. Instances vary the parameter and the initial state. Each comes with the warm start of a parameter sweep: the solution at a neighbouring parameter on the same local branch. Reported: `d u0 / d theta` of the exact (unsmoothed) solution map.

## pendulum_smoothed_sensitivity (weight 0.15)

The same OCP with complementarity replaced by the barrier-smoothed condition `mu_i * h_i = -tau_min` for `tau_min` in {1e-4, 1e-3, 1e-2}. Reported: the derivative of the smoothed solution map. It is differentiable everywhere, including across constraint switches.

## pendulum_near_active_set_change (weight 0.15)

The exact map of the same OCP at parameters close to a constraint switch. The smallest strict-complementarity margin (a multiplier of an active inequality, or the slack of an inactive one) is between 1e-6 and 1e-3, so the derivative is still well defined. Initial states are perturbed, and the warm start lies on the side away from the switch. Reported: `d u0 / d theta`.

## bounded_lqr_adjoint_accuracy (weight 0.15)

A bounded linear-quadratic OCP (20 intervals, 8 states, 4 controls). All dynamics and cost data form a 248-dimensional parameter. The control bound is either loose (`1e4`) or tight (`1`). Reported: `u0` and the adjoint `d(seed . u0)/d theta` for a given seed. This is the quantity needed for back-propagation.

## bounded_lqr_large_adjoint (weight 0.20)

The same OCP at 16 states and 8 controls: a 976-dimensional parameter, with two thirds of the instances at the tight bound. Reported: `u0` and the 976-entry adjoint. Spending one or more extra solves per parameter does not fit the compute budget here.

Each experiment scores `frac_sens_accurate`, `mean_log10_sens_rel_err` and the solution-correctness constraint `frac_u0_accurate`.
