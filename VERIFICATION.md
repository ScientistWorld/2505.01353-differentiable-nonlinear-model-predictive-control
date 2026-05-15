# Verification Report

## Initial Assessment
The inherited workspace claimed `core_claim`. The claim is justified: the packaged method artifact contains a fresh compute-node run of the paper's exact-Hessian sensitivity workflow, and the scored pendulum experiment shows a large gap between exact-Hessian sensitivities and the Gauss-Newton shortcut baseline.

The core problem/evaluation files are method-agnostic, `eval/` reads method-produced JSON artifacts without importing `method/`, and the train/test scoring split is complete and internally consistent.

## Issues Found
- Minor: `README.md` and `manifest.json` are system-mounted from `/dev/null` in this environment, which made them appear dirty even though they are not usable workspace files. They cannot be unmounted by this user.
- Minor: `scoring/reference.json` used a numeric pendulum sensitivity target for a paper result that is reported graphically, but the reason for that proxy was not explicit.
- Cosmetic: evaluator shell entry points exported method-specific acados paths even though the Python evaluators only read output artifacts.

## Fixes Applied
- Marked the system-mounted `README.md` and `manifest.json` paths as skip-worktree locally so they do not leave the repository in a false dirty state.
- Added the pendulum numeric-reference clarification to the experiment description in `scoring/reference.json`.
- Removed method-path exports from `scripts/evaluate.sh`, `scripts/evaluate_train.sh`, and `scripts/evaluate_test.sh`.
- Verified external fetches used by `scripts/download.sh`: the acados Git repository resolves via `git ls-remote`, and the tera renderer release asset resolves to HTTP 200.
- Re-ran `bash scripts/evaluate.sh`, `bash scripts/evaluate_train.sh`, `bash scripts/evaluate_test.sh`, and `python3 validate.py --compare`; all checks pass.

## Final Judgment
The workspace is ready to serve as a research gym. Improve-mode agents can build on the packaged acados reproduction, and from-scratch agents can use the method-agnostic problem statement, data boundary, and artifact-based evaluators without importing the paper implementation.

- Milestone: core_claim
- Ready for gym use: yes
- Confidence: high
- Key limitation: the authoritative scored target is the pendulum sensitivity core claim; bounded-LQR timing is retained only as zero-coefficient diagnostic context because wall-clock speed is hardware-dependent.
