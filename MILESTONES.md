# Reproduction Milestones

**Current: method_runs**

## Progress Log

### [2026-04-04] - method_runs
- Read the paper thoroughly (2505.01353 - Differentiable Nonlinear Model Predictive Control)
- Filled in all briefing files (problem.md, method.md, evaluation.md, overview.md)
- Created reference.json with paper's 3 main experiments
- Cloned acados repository into method/acados
- Studied acados examples: pendulum OCP sensitivities, chain of masses, LQR benchmark
- Implemented pendulum_sensitivity.py (Section 5.1 - core claim)
- Implemented lqr_benchmark.py (Section 5.2)
- Implemented chain_sensitivity.py (Section 5.3)
- Wrote evaluator.py in eval/
- Set up environment: container.def (CUDA base), setup.sh (dependencies)
- Wrote all scripts: download.sh, method.sh, reproduce.sh, baseline.sh, evaluate.sh, run.sh
- Submitted job to build acados and run experiments

## Stop Justification

<!-- Do not edit this unless you decide to stop -->
