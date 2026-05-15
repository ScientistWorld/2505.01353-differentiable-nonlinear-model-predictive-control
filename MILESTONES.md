# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-05-15 16:19] - core_claim
- Audited the existing implementation and successful compute-node run `58199a5f-9c0`.
- Confirmed the paper's actual acados-based differentiable NMPC path runs end-to-end and writes method artifacts through `method/run_reproduction.py`.
- Confirmed reproduced core metrics: exact-Hessian pendulum sensitivity error `0.0025974539` versus Gauss-Newton `2.2001354963`, plus bounded-LQR timing checks.
- Re-ran `python3 validate.py --compare`; all scoring, split-evaluation, and import-separation checks passed.

### [2026-05-15 16:31] - core_claim
- Continued from the reset audit state and re-read the method, evaluation, scripts, scoring, briefing, and environment files.
- Confirmed the implementation is not a surrogate: it constructs the paper's acados OCPs, uses SQP/IPM solver settings, compares exact-Hessian and Gauss-Newton sensitivity paths, factorizes QP/KKT matrices, and calls acados adjoint sensitivity APIs.
- Re-ran `bash scripts/evaluate.sh` and `python3 validate.py --compare`; both completed successfully and verified standalone evaluation, split score files, and method/eval separation.
- Restored the audited milestone to `core_claim`.

## Stop Justification
- Completed at milestone `core_claim`.
