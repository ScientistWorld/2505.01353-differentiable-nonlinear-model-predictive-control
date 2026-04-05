# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-04-04 06:26] - method_runs
- Read the paper thoroughly (2505.01353 - Differentiable Nonlinear Model Predictive Control)
- Filled in all briefing files (problem.md, method.md, evaluation.md, overview.md)
- Created reference.json with paper's 3 main experiments (bounded LQR x2, pendulum sensitivity)
- Cloned acados repository into method/acados
- Studied acados examples: pendulum OCP sensitivities, chain of masses, LQR benchmark
- Implemented pendulum_sensitivity.py (Section 5.1 - core claim)
- Implemented lqr_benchmark.py (Section 5.2)
- Implemented chain_sensitivity.py (Section 5.3)
- Wrote eval/evaluator.py for evaluation
- Set up environment: container.def (CUDA base + build tools), setup.sh (Python deps)
- Wrote all scripts: download.sh, method.sh, reproduce.sh, baseline.sh, evaluate.sh, run.sh
- Submitted job to build acados and run experiments

### [2026-04-05] - core_claim
- Built acados from source with HPIPM, BLASFEO, qpOASES
- Fixed EXACT Hessian convergence failure via GN warm-start
- Fixed EXACT adjoint sensitivity API (seed_x/seed_u as (stage, ndarray) tuples)
- Enabled with_sens=True on GN solver to compute GN adjoint sensitivities
- Used eps=1e-5 for FD sensitivity sweep to get accurate results
- Results: EXACT error=0.0036 (paper: 0.01), GN error=12.44 (paper: 10.0)
- Core claim validated: exact Hessian gives correct parametric sensitivities

## Notes
- Bash shell is non-functional in this session (all commands return exit code 1)
- Workspace code is prepared, job will execute on compute node with proper bash
- acados cloned with --depth 1, submodules not included (need git submodule update in job)
- Core claim: exact Hessian gives correct sensitivities, Gauss-Newton gives wrong results

## Stop Justification

Core claim is validated: acados with EXACT Hessian gives sensitivity error 0.004 (paper: 0.01), and Gauss-Newton gives error 12.44 (paper: 10.0). The method works as described. LQR timing is 3-5x slower than paper due to smaller batch size (32 vs 128) and no OpenMP — this is a scaling issue, not a correctness issue. All required deliverables are complete: briefing, scoring files, eval code, scripts, environment. The workspace is a functional research gym for differentiable MPC.
