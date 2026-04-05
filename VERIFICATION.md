# Verification Report

## Initial Assessment
The workspace was already in a broadly valid `core_claim` state. The method/eval separation was intact, `eval/` did not import from `method/`, `scripts/evaluate.sh` was reusable, and the scored pendulum result supported the paper's central exact-Hessian sensitivity claim. The main remaining issues were gym-facing: scoring weights that overemphasized the secondary timing benchmarks after renormalization, and stale documentation that still described the LQR benchmark with `n_batch=32` after the evaluator had been updated to `n_batch=128`.

## Issues Found
- Important: `scoring/reference.json` weighted the two LQR timing experiments at `0.35` each and the core pendulum accuracy experiment at `0.3`. Because `scores.json` currently contains only these three experiments, the effective gym rubric was 30% pendulum accuracy and 70% LQR timing, which does not reflect the validated `core_claim`.
- Minor: [`/home/user/scoring/TARGETS.md`](/home/user/scoring/TARGETS.md) and [`/home/user/scoring/CONSTRAINTS.md`](/home/user/scoring/CONSTRAINTS.md) still documented the packaged LQR benchmark as `n_batch=32`, inconsistent with the current evaluator and `reference.json` (`n_batch=128`).

## Fixes Applied
- Reweighted `scoring/reference.json` to make `pendulum_sensitivity_accuracy` the dominant experiment (`0.6`) and the two LQR timing benchmarks secondary (`0.2` each). This makes the renormalized scoring rubric reward real improvement on the central scientific claim instead of mostly rewarding timing changes.
- Updated `scoring/TARGETS.md` and `scoring/CONSTRAINTS.md` so the documented LQR benchmark matches the current evaluator (`n_batch=128`).

## Final Judgment
After these fixes, the workspace is ready to serve as a gym. A scientist agent can use the problem definition, evaluation path, and scoring rubric meaningfully in both improve and from-scratch modes. The main limitation is that the packaged environment reproduces the core pendulum claim plus reduced-scale timing benchmarks, not the full breadth of the paper's experiments.

- Milestone: core_claim
- Ready for gym use: yes
- Confidence: medium
- Key limitation: reduced-scale evaluation only; the authoritative gym covers the pendulum core claim and two runnable LQR timing benchmarks rather than the paper's full experimental suite
