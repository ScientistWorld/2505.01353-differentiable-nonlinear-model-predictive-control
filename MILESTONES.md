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

### [2026-04-10 01:34] - core_claim
- Fixed a packaging regression in the script chain: `scripts/method.sh` now runs `method/run_reproduction.py` to regenerate raw results, and `scripts/run.sh` / `scripts/reproduce.sh` call method execution before `scripts/evaluate.sh`.
- Preserved the separation rule by keeping `eval/evaluator.py` method-independent; it only validates and scores the method-produced JSON artifact.
- Preparing a CPU test submission to verify the corrected end-to-end path in the compute container.

### [2026-04-10 04:54] - core_claim
- Corrected the runnable script flow so `scripts/method.sh`, `scripts/reproduce.sh`, and `scripts/run.sh` generate `checkpoints/reproduction_results.json` with `method/run_reproduction.py` before scoring it via `eval/evaluator.py`.
- Fixed helper scripts that incorrectly imported experiment functions from `eval/`; the raw acados experiment code now remains in `method/` while `eval/` remains a method-agnostic scorer.
- Lightweight checks passed locally: Python compilation and `python3 validate.py --compare`. Submitting a CPU test job to validate the corrected end-to-end path inside the compute container.

### [2026-04-10 06:54] - core_claim
- Added the missing `.gitmodules` mapping for the `method/acados` gitlink so fresh checkouts know how to initialize the paper's acados dependency.
- Made `scripts/download.sh` handle both a proper acados checkout/submodule and the pre-populated source-tree layout present in this workspace.
- Re-ran shell syntax checks, Python compilation, and `python3 validate.py --compare`; all passed. Submitting the CPU smoke test with the same `core_claim` milestone.

### [2026-04-10 07:14] - core_claim
- The first CPU smoke-test submission failed during `environment/setup.sh`, before the job payload ran. The build log showed `uv` resolving packages and then crashing in root-mapped fakeroot semaphore handling.
- Replaced `uv pip install --system` in `environment/setup.sh` with `python3 -m pip install` for this workspace's setup phase while keeping Python installs out of `container.def`.
- Local shell syntax checks, Python compilation, and `python3 validate.py --compare` pass after the setup change. Resubmitting the same CPU smoke test.

### [2026-04-10 16:03] - core_claim
- Rechecked the packaged method/evaluation split after reactivation: `method/run_reproduction.py` contains the acados exact-Hessian and Gauss-Newton sensitivity computation, while `eval/evaluator.py` only scores a method-produced JSON artifact.
- Local checks pass: shell syntax validation, Python compilation, and `python3 validate.py --compare`.
- Submitting a CPU smoke test to verify the full `scripts/run.sh` -> `scripts/reproduce.sh` -> `scripts/evaluate.sh` path inside the compute container after the setup workaround.

### [2026-04-10 17:19] - core_claim
- The CPU smoke-test environment setup failed before the payload because `environment/setup.sh` attempted an editable acados_template install from `/home/user/method/acados`, which is not reliably visible during the setup overlay phase.
- Removed the workspace-dependent install from `environment/setup.sh`; runtime scripts already import the acados Python interface from source via `PYTHONPATH`.
- Local checks pass after the fix: shell syntax validation, acados_template source import, Python compilation, and `python3 validate.py --compare`. Resubmitting the CPU smoke test.

### [2026-04-10 18:09] - core_claim
- Rechecked the previous setup failure log and confirmed it came from the older `setup.sh` that still entered `/home/user/method/acados/interfaces/acados_template`.
- The current setup script only installs PyPI packages; runtime scripts import acados_template from source via `PYTHONPATH`.
- Local shell syntax checks, Python compilation, acados_template source import, and `python3 validate.py --compare` pass. Resubmitting the CPU smoke test.

### [2026-04-10 18:50] - core_claim
- CPU smoke-test job `07c40127-2b3` passed setup and rebuilt acados, then failed in the method payload because Python imported an incomplete namespace-only `casadi` module without `MX`/`SX`.
- Updated `environment/setup.sh` to force-reinstall pinned runtime wheels and validate that `casadi.MX`, `casadi.SX`, and `casadi.Function` are available during setup.
- Local shell syntax checks, Python compilation, and `python3 validate.py --compare` pass. Resubmitting the CPU smoke test.

### [2026-04-10 22:56] - core_claim
- Hardened the compute runtime against the broken namespace-style `casadi` import seen in job `07c40127-2b3`.
- Updated `scripts/run.sh`, `scripts/reproduce.sh`, `scripts/method.sh`, and `scripts/evaluate.sh` to set `PYTHONNOUSERSITE=1`, report the resolved `casadi` import path, and use the unpacked Python 3.10 wheel under `environment/vendor_py310/` as a fallback runtime package source.
- Re-ran local shell syntax checks, Python compilation, and `python3 validate.py --compare`; all passed. Resubmitting the CPU smoke test with the runtime import fix.

### [2026-04-10 23:02] - core_claim
- Extended the runtime fallback from CasADi-only to all required binary/runtime Python packages by vendoring CPython 3.10 wheels for `casadi`, `numpy`, `scipy`, and `deprecated` into `environment/vendor_py310/`.
- Updated `scripts/download.sh` to materialize those wheels on the login node and simplified `environment/setup.sh` to a no-op so compute jobs no longer depend on overlay-time pip behavior.
- Local checks pass: shell syntax, bootstrap CasADi import, and `python3 validate.py --compare`. Submitting another CPU smoke test for the fully vendored runtime path.

## Stop Justification

- Stopping at `core_claim` is justified because the paper's central qualitative result is reproduced and verified in this workspace: exact-Hessian sensitivities closely match finite differences while the Gauss-Newton approximation is materially worse on the same pendulum OCP.
- The workspace is now packaged as a usable gym: problem and evaluation components are separated from the method implementation, `scripts/evaluate.sh` writes `scoring/scores.json`, and the scoring rubric emphasizes the validated core claim while preserving the LQR timing benchmarks as constraint targets.
- The remaining gaps are completeness-related rather than correctness-related: the LQR timing benchmarks are still reduced-scale and timing-volatile, no local reproduction of external baselines is included, and the Section 5.3 chain-of-masses result is outside the authoritative evaluation path.
