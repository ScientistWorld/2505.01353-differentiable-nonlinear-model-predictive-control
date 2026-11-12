The baselines are written by the same predictor as the proposed method
(`method/predict.py`, entry point `scripts/predict.sh`) and scored in every
experiment:

- `gauss_newton_approx`: implicit-function-theorem sensitivities with the
  Gauss-Newton Hessian instead of the exact Lagrangian Hessian (paper Remark 3).
- `unconstrained_ift`: inequality constraints dropped, exact-Hessian IFT on
  the resulting unconstrained problem.

`bash scripts/baseline.sh` scores them on the visible train instances.
