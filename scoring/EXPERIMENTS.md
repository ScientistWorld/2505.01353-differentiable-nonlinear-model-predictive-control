# Experiment Overview

All experiments use the same protocol. The evaluator gives a predictor problem instances without answers. The predictor returns the optimal first control `u0` and a derivative. The evaluator then compares both against its own independent high-precision ground truth. It solves each instance itself, refines the optimality system to machine precision, and differentiates it exactly, cross-checking with finite differences. Full definitions are in `briefing/problem.md` and `briefing/evaluation.md`.

## pendulum_sensitivity_accuracy (weight 0.5)

A nonlinear pendulum-on-cart OCP (50 intervals). One scalar parameter enters the cost, the dynamics and a path constraint. Instances vary the parameter and the initial state. Each comes with the warm start of a parameter sweep: the solution at a neighbouring parameter on the same local branch. Reported: `d u0 / d theta` of the exact (unsmoothed) solution map.

## pendulum_smoothed_sensitivity (weight 0.2)

The same OCP with complementarity replaced by the barrier-smoothed condition `mu_i * h_i = -tau_min` for `tau_min` in {1e-4, 1e-3, 1e-2}. Reported: the derivative of the smoothed solution map. It is differentiable everywhere, including across constraint switches.

## bounded_lqr_adjoint_accuracy (weight 0.3)

A bounded linear-quadratic OCP (20 intervals, 8 states, 4 controls). All dynamics and cost data form a 248-dimensional parameter. The control bound is either loose (`1e4`) or tight (`1`). Reported: `u0` and the adjoint `d(seed . u0)/d theta` for a given seed. This is the quantity needed for back-propagation.

Each experiment scores `frac_sens_accurate`, `mean_log10_sens_rel_err` and the solution-correctness constraint `frac_u0_accurate`.
