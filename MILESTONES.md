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

## Stop Justification
- Not stopped. Corrected benchmark is being submitted for compute-node validation.
