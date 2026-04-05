# Progress

## Final Status

- Final milestone: `core_claim`
- Audit verdict: trustable after correction. The implementation is real and method-faithful, and the final packaging now states the runnable reduced-scale setup honestly.

## What Works

- acados built from source with HPIPM, BLASFEO, qpOASES
- All shell scripts functional: download.sh, method.sh, reproduce.sh, baseline.sh, evaluate.sh, run.sh
- Environment: container.def (CUDA base), setup.sh (Python deps)
- `eval/evaluator.py`: authoritative reproduction path for the pendulum sensitivity experiment and bounded-LQR timing benchmark
- `scripts/evaluate.sh` is the standard entry point and writes `scoring/scores.json`
- scoring/TARGETS.md, scoring/CONSTRAINTS.md, scoring/DIRECTION.md filled
- Audit confirmed the implementation is a real acados-based exact-Hessian / Gauss-Newton comparison, not a surrogate model

## Results

| Experiment | Metric | Reproduced | Paper |
|---|---|---|---|
| pendulum (EXACT) | sensitivity_max_error | 0.0026 | 0.01 |
| pendulum (GN) | sensitivity_max_error | 2.2001 | 10.0 |
| bounded_lqr_umax_high | solve_and_sens_time_ms | 48.95 | 34.5 |
| bounded_lqr_umax_low | solve_and_sens_time_ms | 67.00 | 42.0 |

**Core claim validated**: EXACT Hessian gives accurate parametric sensitivities (error 0.0026, paper 0.01). Gauss-Newton remains materially worse (error 2.20), preserving the qualitative claim that the approximate Hessian gives incorrect sensitivities relative to the exact-Hessian method.

**LQR timing**: the benchmark runs and writes real timings, but the numbers vary materially across reruns and do not consistently match the paper. This benchmark is therefore packaged as informative timing, not as the main success criterion for the reproduction.

## Key Implementation Details

- **EXACT Hessian convergence**: Cold-start EXACT Hessian fails (QP MAX_NWSR). Warm-started from GN solution to bypass ill-conditioned QP subproblems.
- **Adjoint sensitivity API**: acados `eval_adjoint_solution_sensitivity` requires seed_x/seed_u as tuples of (stage, np.ndarray), not bare integers.
- **FD epsilon**: eps=1e-5 gives accurate finite-difference ground truth for sensitivity comparison.
- **Solver flags**: qp_solver_ric_alg=0, qp_solver_cond_ric_alg=0, exact_hess_constr/cost/dyn=1 for exact Hessian.

## Remaining

- LQR timing: validate the corrected Section 5.2 benchmark on a fresh Release rebuild inside the job environment.
- OpenMP remains optional; the larger known issue was incorrect timing accounting rather than thread-level parallelism.
- Secondary claims: the Section 5.3 chain benchmark is not yet part of the authoritative evaluation path.

## Issues

- LQR timing varies noticeably across reruns, so the current timing benchmark is less stable than the pendulum sensitivity result
- A local smoke test showed that `solve_for_x0()` is not compatible with the current generated x0 constraint layout in this evaluator, so the repeated benchmark keeps the existing runtime `x` update path.
- No local `mpc.pytorch` or `cvxpygen` reproduction; reference values come from the paper only
- Temporary generated files appear when acados regenerates C code during evaluation

## Deviations from Paper

- The packaged pendulum evaluator is a smaller but faithful version of the paper's setup: `N=20`, `T=1.0`, and sensitivity is checked at a central reference parameter using finite differences around that point rather than across the full paper-scale trajectory map.
- The Section 5.2 benchmark code has now been updated back to the paper's `n_batch=128`; validation of the corrected benchmark is pending the next submitted job.
- The LQR evaluator previously double-counted solve time when reporting "solution + adjoint sensitivity" timing; this has been corrected and needs fresh benchmark results.
- acados is rebuilt in `Release` mode on the job path for the next validation run.
- No comparison against mpc.pytorch or cvxpygen baselines
- Chain of masses example (Section 5.3) not included in evaluator
