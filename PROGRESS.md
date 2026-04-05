# Progress

## What Works

- acados built from source with HPIPM, BLASFEO, qpOASES
- All shell scripts functional: download.sh, method.sh, reproduce.sh, baseline.sh, evaluate.sh, run.sh
- Environment: container.def (CUDA base), setup.sh (Python deps)
- eval/evaluator.py: full pendulum sensitivity experiment + LQR timing benchmark
- All 3 experiments run and produce scores in scoring/scores.json
- scoring/TARGETS.md, scoring/CONSTRAINTS.md, scoring/DIRECTION.md filled

## Results

| Experiment | Metric | Reproduced | Paper |
|---|---|---|---|
| pendulum (EXACT) | sensitivity_max_error | 0.004 | 0.01 |
| pendulum (GN) | sensitivity_max_error | 12.44 | 10.0 |
| bounded_lqr_umax_high | solve_and_sens_time_ms | 99.5 | 34.5 |
| bounded_lqr_umax_low | solve_and_sens_time_ms | 191.6 | 42.0 |

**Core claim validated**: EXACT Hessian gives accurate parametric sensitivities (error 0.004, paper 0.01). Gauss-Newton gives wrong sensitivities (error 12.44, paper 10.0).

**LQR timing gap**: 3-5x slower than paper. Likely due to: fewer batched problems (32 vs 128), no OpenMP parallelization, single-threaded execution. The method works correctly — just slower at scale.

## Key Implementation Details

- **EXACT Hessian convergence**: Cold-start EXACT Hessian fails (QP MAX_NWSR). Warm-started from GN solution to bypass ill-conditioned QP subproblems.
- **Adjoint sensitivity API**: acados `eval_adjoint_solution_sensitivity` requires seed_x/seed_u as tuples of (stage, np.ndarray), not bare integers.
- **FD epsilon**: eps=1e-5 gives accurate finite-difference ground truth for sensitivity comparison.
- **Solver flags**: qp_solver_ric_alg=0, qp_solver_cond_ric_alg=0, exact_hess_constr/cost/dyn=1 for exact Hessian.

## Remaining

- LQR timing: could try n_batch=128 and enable OpenMP to close the gap with paper
- Secondary claims: chain example not fully validated
- Additional experiments: different N values, different problem sizes

## Issues

- LQR timing is 3-5x slower than paper (timing only, not the core claim)
- No mpc.pytorch or cvxpygen baseline comparison (only acados implemented)
- Many temporary test files in workspace root (test_*.py, *.json, etc.)

## Deviations from Paper

- LQR benchmark uses n_batch=32 instead of 128 (time constraint)
- acados compiled without OpenMP (missing -DACADOS_WITH_OPENMP=ON), affects timing
- No comparison against mpc.pytorch or cvxpygen baselines
- Chain of masses example (Section 5.3) not included in evaluator
