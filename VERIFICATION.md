# Verification Report

## Initial Assessment

The workspace started at milestone `core_claim`. That milestone is justified: the compute-node run regenerated the method artifact through `scripts/run.sh`, and the pendulum sensitivity experiment supports the paper's central claim. The exact-Hessian sensitivity error is `3.5699e-05`, while the Gauss-Newton approximation error is `46.542`.

The method implementation is a real acados-based reproduction of the paper's differentiable nonlinear MPC sensitivity workflow, not a surrogate. The evaluator reads method artifacts and does not import from `method/`.

## Issues Found

- **Minor**: The bounded-LQR wall-clock timing entries were described as efficiency targets in some docs. Their metric coefficients were already zero, but the wording could mislead future scientist agents into treating hardware-dependent runtime as a scored objective.
- **Minor**: A stale generated `c_generated_code/` directory remained at the workspace root after the method was redirected to `tmp/acados_generated/`.
- **Cosmetic/system**: The harness-managed `trajectory/` files appear deleted in this environment because they are mounted read-only. They are not part of the research gym deliverable.

## Fixes Applied

- Clarified `briefing/problem.md`, `briefing/evaluation.md`, `scoring/EXPERIMENTS.md`, `scoring/TARGETS.md`, `scoring/CONSTRAINTS.md`, and `scoring/DIRECTION.md` so LQR timing is documented as context-only with zero scoring coefficients.
- Updated `scoring/reference.json` descriptions to make the hardware-dependent timing metrics explicitly unscored while keeping the validator-compatible tiny experiment weights.
- Removed the stale root-level generated `c_generated_code/` directory.
- Marked the read-only harness trajectory paths skip-worktree locally so git status reflects the reproducible workspace files.

## Final Judgment

The workspace is ready to serve as a research gym. Improve-mode agents can use the method code and reproduced artifacts, while from-scratch agents can rely on the method-agnostic problem, data, evaluation, and scoring docs without seeing the paper's implementation details. The main limitation is scope: the scored gym centers on the pendulum sensitivity accuracy claim, while LQR timing is retained only as diagnostic context because wall-clock speed is not portable across hardware.

- Milestone: core_claim
- Ready for gym use: yes
- Confidence: high
- Key limitation: only the core pendulum sensitivity claim is scored; bounded-LQR timing is diagnostic context only.
