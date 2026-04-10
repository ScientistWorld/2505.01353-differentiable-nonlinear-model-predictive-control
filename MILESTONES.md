# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-04-05 03:41] - method_runs
- Validated that the acados-based differentiable NMPC pipeline executes end-to-end in this workspace.
- Built the acados solver stack and packaged reusable scripts under `scripts/` and `eval/`.

### [2026-04-05 04:58] - core_claim
- Implemented the paper's two-solver pendulum sensitivity experiment in `eval/evaluator.py`.
- Verified the core claim with a fresh evaluator run: exact-Hessian sensitivity error `0.002597` vs Gauss-Newton error `2.200135` against finite differences.
- Packaged the LQR timing benchmark in the same evaluator so `scripts/evaluate.sh` produces `scoring/scores.json` from actual runs.

### [2026-04-05 05:18] - core_claim
- Audited the previous agent's work and confirmed the implementation is a real acados-based exact-Hessian sensitivity computation, not a surrogate.
- Re-ran `scripts/evaluate.sh` standalone during the audit and reproduced the same core pendulum result: exact `0.002597`, Gauss-Newton `2.200135`.
- Corrected packaging overstatements so the docs now describe the reduced-scale runnable evaluator rather than the full paper-scale settings.

### [2026-04-05 05:33] - core_claim
- Corrected the Section 5.2 bounded-LQR evaluator to stop double-counting solve time in the reported "solution + adjoint sensitivity" metric.
- Restored the benchmark batch size to `n_batch=128` to match the paper's Table 1 setup more closely.
- Updated the job path to rebuild acados in `Release` mode before evaluation and prepared a fresh submission to validate the corrected benchmark.

### [2026-04-05 05:55] - core_claim
- Performed final workspace verification for gym use and confirmed that `eval/` remains independent from `method/` and the problem/evaluation briefing files are method-agnostic enough for from-scratch use.
- Corrected the scoring rubric so the renormalized gym weights prioritize the pendulum core claim over the secondary LQR timing benchmarks.
- Aligned `scoring/TARGETS.md` and `scoring/CONSTRAINTS.md` with the current LQR evaluator configuration (`n_batch=128`) and wrote `VERIFICATION.md`.

### [2026-04-10 01:16] - core_claim
- Re-validated the packaged workspace with `python3 validate.py --compare`; all checks passed.
- Confirmed tracked reproduction deliverables are already pushed to `origin/main`; remaining dirty paths are system/trajectory artifacts outside the method/evaluation package.
- Left `action.yaml` at `done` with milestone `core_claim`.

## Stop Justification

- Stopping at `core_claim` is justified because the paper's central qualitative result is reproduced and verified in this workspace: exact-Hessian sensitivities closely match finite differences while the Gauss-Newton approximation is materially worse on the same pendulum OCP.
- The workspace is now packaged as a usable gym: problem and evaluation components are separated from the method implementation, `scripts/evaluate.sh` writes `scoring/scores.json`, and the scoring rubric emphasizes the validated core claim while preserving the LQR timing benchmarks as constraint targets.
- The remaining gaps are completeness-related rather than correctness-related: the LQR timing benchmarks are still reduced-scale and timing-volatile, no local reproduction of external baselines is included, and the Section 5.3 chain-of-masses result is outside the authoritative evaluation path.
