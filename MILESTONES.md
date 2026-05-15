# Reproduction Milestones

**Current: method_runs**

## Progress Log

### [2026-05-15 16:28] - method_runs
- Audited the inherited workspace and found the pendulum two-solver acados implementation is a real implementation of the paper's IFT/IPM sensitivity algorithm.
- Fixed the LQR benchmark before resubmission: stage-0 equality bounds now enforce `x_0 = x0_batch[i]`, and the packed cost matrix `H` is part of `p_global` in the cost expression.
- Updated `scripts/run.sh` so submitted jobs regenerate `checkpoints/reproduction_results.json` through `scripts/method.sh` before scoring train/test slices.
- Local syntax checks and `python3 validate.py --compare` pass; corrected end-to-end method results are pending a compute job.

### [2026-05-15 16:33] - method_runs
- Continued audit after handoff. The method path still implements the paper's actual acados IFT/IPM sensitivity workflow, and `eval/` remains method-independent.
- Existing `checkpoints/reproduction_results.json` and `scoring/scores.json` predate the LQR fix, so `core_claim` is not restored from stale artifacts.
- `python3 validate.py --compare` passes structurally on the stale artifact; submitting the corrected end-to-end CPU job again to regenerate and score fresh results.

### [2026-05-15 16:39] - method_runs
- Job `e7e3072e-d55` failed before the method ran because the vendored NumPy tree was missing `numpy/ma/core.py`; the broad `core.*` ignore rule had omitted that wheel file from the workspace.
- Restored the missing NumPy `core.py` and `core.pyi` files from the local wheel, unignored them, and added `scripts/repair_vendor_runtime.sh` so offline compute jobs repair/validate the vendored runtime before importing acados.
- Resubmitting the same corrected end-to-end CPU reproduction job after the environment packaging fix.

### [2026-05-15 16:58] - method_runs
- Job `f23c2850-d14` confirmed the vendored runtime repair works: the method built acados solvers, regenerated raw artifacts, and completed both bounded-LQR timing experiments.
- The job failed in the held-out scorer because the pendulum branch wrote a negative sentinel after incorrectly trying to solve the NLP with the exact-Hessian sensitivity solver; this is not the paper's two-solver sensitivity workflow.
- Patched the pendulum reproduction to solve only the nominal NLP, transfer the iterate to the exact-Hessian solver, factorize the exact-Hessian QP, and evaluate adjoint sensitivities against a finite-difference nominal solution map.
- Tightened the held-out evaluator to reject non-finite or negative metric values with a clear validation error.

### [2026-05-15 17:08] - method_runs
- Job `2709a928-9ac` failed earlier in the pendulum path because every nominal sweep solve returned acados status `ACADOS_MINSTEP`; the iterates were finite, but the new guard discarded them all.
- Updated the nominal pendulum guard to accept finite status-4 iterates, fail on non-finite values or unexpected statuses, and print a status histogram plus finite-difference statuses for auditability.

### [2026-05-15 16:58] - method_runs
- Job `76839165-68a` completed the packaged script path, but the regenerated pendulum artifact did not support the core claim: all nominal solves were status `ACADOS_MINSTEP`, the finite-difference sensitivity was zero, and exact-Hessian error was larger than Gauss-Newton.
- Kept the milestone at `method_runs` and patched the pendulum solver options to use a smaller HPIPM barrier initialization with more QP iterations.
- Added core-claim sanity checks so future submitted runs fail if the regenerated exact-Hessian sensitivity is non-finite, negative, worse than Gauss-Newton, or too inaccurate for the Section 5.1 reproduction.

### [2026-05-15 17:12] - method_runs
- Job `8abe96cf-11c` failed in the new pendulum sanity guard, confirming that the previous solver-option change still produced a degenerate finite-difference sensitivity rather than a valid core-claim result.
- Patched the pendulum nominal solve to start from a dynamics-consistent RK4 rollout and changed partial condensing to `qp_solver_cond_N=5`, matching the stable local acados smoke configuration while preserving the paper's OCP and sensitivity algorithm.
- Expanded the degenerate-sensitivity error message to include finite-difference values and nominal status counts for the next audit log.

## Stop Justification
- Not stopped. Dynamics-consistent pendulum warm starts and smaller partial-condensing blocks are being submitted for compute-node validation.
