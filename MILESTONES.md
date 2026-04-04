# Reproduction Milestones

**Current: method_runs**

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

## Notes
- Bash shell is non-functional in this session (all commands return exit code 1)
- Workspace code is prepared, job will execute on compute node with proper bash
- acados cloned with --depth 1, submodules not included (need git submodule update in job)
- Core claim: exact Hessian gives correct sensitivities, Gauss-Newton gives wrong results

## Stop Justification

<!-- Do not edit this unless you decide to stop -->
