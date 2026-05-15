# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-05-15 16:19] - core_claim
- Audited the existing implementation and successful compute-node run `58199a5f-9c0`.
- Confirmed the paper's actual acados-based differentiable NMPC path runs end-to-end and writes method artifacts through `method/run_reproduction.py`.
- Confirmed reproduced core metrics: exact-Hessian pendulum sensitivity error `0.0025974539` versus Gauss-Newton `2.2001354963`, plus bounded-LQR timing checks.
- Re-ran `python3 validate.py --compare`; all scoring, split-evaluation, and import-separation checks passed.

## Stop Justification
- Completed at milestone `core_claim`.
