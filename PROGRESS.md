# Progress

## What Works

- Paper analysis complete: understood the differentiable MPC approach using IFT with interior-point SQP
- Briefing files filled: problem.md, method.md, evaluation.md, overview.md
- reference.json created with 3 experiments matching the paper's main results
- acados repository cloned and studied (pendulum, chain, LQR examples)
- Method implementation: pendulum_sensitivity.py (Section 5.1 core claim)
- Method implementation: lqr_benchmark.py (Section 5.2)
- Method implementation: chain_sensitivity.py (Section 5.3)
- Evaluation code: eval/evaluator.py
- All shell scripts: download.sh, method.sh, reproduce.sh, baseline.sh, evaluate.sh, run.sh
- Environment: container.def (CUDA base), setup.sh (Python deps)

## Results

- Not yet available (job pending execution)
- Expected: sensitivity accuracy matches FD (error < 0.1) with exact Hessian
- Expected: Gauss-Newton Hessian gives wrong sensitivities (error > 1.0)
- Expected: LQR timing comparable to paper's reported numbers

## Remaining

- Job execution to verify acados builds correctly
- Run pendulum experiment to validate core claim
- Run LQR benchmark for timing comparison
- Generate scores.json with reproduced numbers
- Compare against reference.json

## Issues

- Bash shell was non-functional in this turn (could not run git or any shell commands)
- Workaround: prepared all code files using file tools, submitted job for build+run
- acados requires cmake + build tools which need to be installed in the container

## Deviations from Paper

- Using smaller batch sizes for LQR benchmark (n_batch=64 vs 128) to fit within time budget
- Chain example uses simplified parameter structure compared to paper's full setup
- No comparison against mpc.pytorch or cvxpygen (not installed in environment) — focus is on reproducing acados results
