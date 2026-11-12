# Design Notes - Train/Test Evaluation (current)

Superseded the earlier artifact-based split (it scored self-reported errors). The current design, its rationale and audit are in `HARDENING.md`:

- **Protocol:** `scripts/predict.sh INSTANCES PREDICTIONS` is the only method interface. `eval/train/` (public instances) and `eval/test/` (hidden instances) each hold independent copies of the instance generator and ground-truth solver (`groundtruth.py`) and of the pure-Python scorer (`evaluator.py`). They share no code and never import `method/`.
- **Ground truth:** IPOPT, then Newton refinement of the KKT system, then an IFT derivative, cross-checked by Richardson finite differences. It is cached in `eval/<split>/cache/` and regenerated deterministically from the split seed if the cache is missing.
- **Pendulum instances** carry a branch warm start (the solution at theta -/+ 1e-3), because the OCP is multimodal.
- **Trivial instances excluded:** those whose sensitivity is trivially zero (saturated u0) are removed by a deterministic post-filter.
