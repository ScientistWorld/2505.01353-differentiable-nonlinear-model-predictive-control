# Progress

## Final Status

- Final milestone: `core_claim`
- 2026-04-10 setup retry: the CPU smoke-test submission failed during `environment/setup.sh`, before the job payload ran. The log showed `uv` resolving packages and then failing inside root-mapped fakeroot semaphore handling (`libfakeroot` / `semop`). Switched `environment/setup.sh` to `python3 -m pip install` and revalidated locally with shell syntax checks, Python compilation, and `python3 validate.py --compare`; resubmitting the CPU smoke test.
- 2026-04-10 setup retry 2: the next environment attempt failed before the job payload because `environment/setup.sh` tried to install `acados_template` from `/home/user/method/acados/...`, but the setup overlay did not have that workspace path available. Removed the workspace-dependent editable install and rely on the runtime `PYTHONPATH` exports in `scripts/run.sh` and `scripts/method.sh`; shell syntax checks, `acados_template` source import, Python compilation, and `python3 validate.py --compare` pass locally.
- 2026-04-10 packaging update: corrected the runnable script flow so `scripts/method.sh`, `scripts/reproduce.sh`, and `scripts/run.sh` generate raw method metrics with `method/run_reproduction.py` before scoring through the method-agnostic evaluator. `python3 -m py_compile ...` and `python3 validate.py --compare` pass locally; a CPU test job is being submitted to validate the corrected end-to-end path in-container.
- 2026-04-10 dependency packaging update: added the missing `.gitmodules` entry for `method/acados` and made `scripts/download.sh` robust to both submodule checkouts and the pre-populated acados source tree in this workspace. Shell syntax checks, Python compilation, and `python3 validate.py --compare` pass locally; a CPU smoke test is being submitted.
- 2026-04-10 runtime bootstrap update: CPU smoke-test job `f1d36739-10c` still failed before method execution, but the failure is now isolated to the CasADi bootstrap path. `method/bootstrap_runtime.py` was still probing `/home/user/.local/lib/python3.12/site-packages` and hiding the actual exception from the vendored CasADi root. The bootstrap now restricts autodiscovery to the active interpreter version, keeps the runtime `sys.path` ordering intact, and reports the root-specific exception and traceback. `scripts/run.sh` also prints the active Python version and leading `sys.path` entries before aborting, so the next compute log should expose the real ABI or linker issue if one remains.
- 2026-04-11 acados runtime-link update: CPU smoke-test job `a4a57e9d-0d9` confirmed that the compute-node CasADi bootstrap is fixed: the job imported the vendored `casadi` package successfully under Python 3.10 and reached method execution. The remaining failure is now in the acados shared library itself: `libacados.so` failed to load inside `AcadosOcpSolver` with `undefined symbol: d_ocp_qp_seed_memsize`. Inspection shows the installed `lib/git_commit_hash` was still `c1c1e81` while the checked-out acados source is `530daae`, so the job was reusing stale build/install artifacts from an older acados revision. Added `scripts/build_acados.sh` to wipe the old `build/` directory and installed acados libraries before every rebuild, and routed both `scripts/download.sh` and `scripts/run.sh` through that helper. `scripts/run.sh` now also does a direct `ctypes.CDLL('/home/user/method/acados/lib/libacados.so')` check immediately after rebuild to fail fast if runtime linkage is still inconsistent.
- 2026-04-10 verification: `python3 validate.py --compare` passed, with reproduced pendulum exact-Hessian error `0.002597` and Gauss-Newton error `2.200135`.
- Audit verdict: trustable after correction. The implementation is real and method-faithful, and the final packaging states the runnable reduced-scale setup honestly.
- Final verification complete: the gym-facing scoring rubric, targets, constraints, and direction documents are aligned with the packaged evaluator and ready for future scientist agents.

## What Works

- acados built from source with HPIPM, BLASFEO, qpOASES
- All shell scripts functional: download.sh, method.sh, reproduce.sh, baseline.sh, evaluate.sh, run.sh
- `scripts/reproduce.sh` now runs the acados method producer before calling the reusable evaluator, so a stale `scoring/scores.json` is not the only reproduction path.
- Environment: container.def (CUDA base), setup.sh (Python deps)
- `method/run_reproduction.py`: authoritative method path for the pendulum sensitivity experiment and bounded-LQR timing benchmark
- `eval/evaluator.py`: method-agnostic scorer for `checkpoints/reproduction_results.json`
- `scripts/evaluate.sh` is the standard scoring entry point and writes `scoring/scores.json`
- scoring/TARGETS.md, scoring/CONSTRAINTS.md, scoring/DIRECTION.md filled and aligned with the current evaluator configuration
- Audit confirmed the implementation is a real acados-based exact-Hessian / Gauss-Newton comparison, not a surrogate model
- Verification confirmed the scoring weights prioritize the pendulum core claim while retaining the LQR timing benchmarks as constraint targets

## Results

| Experiment | Metric | Reproduced | Paper |
|---|---|---|---|
| pendulum (EXACT) | sensitivity_max_error | 0.0026 | 0.01 |
| pendulum (GN) | sensitivity_max_error | 2.2001 | 10.0 |
| bounded_lqr_umax_high | solve_and_sens_time_ms | 48.95 | 34.5 |
| bounded_lqr_umax_low | solve_and_sens_time_ms | 67.00 | 42.0 |

**Core claim validated**: EXACT Hessian gives accurate parametric sensitivities (error 0.0026, paper 0.01). Gauss-Newton remains materially worse (error 2.20), preserving the qualitative claim that the approximate Hessian gives incorrect sensitivities relative to the exact-Hessian method.

**LQR timing**: the benchmark runs and writes real timings, but the numbers vary materially across reruns and do not consistently match the paper. This benchmark is therefore packaged as informative timing, not as the main success criterion for the reproduction.

## Key Implementation Details

- **EXACT Hessian convergence**: Cold-start EXACT Hessian fails (QP MAX_NWSR). Warm-started from GN solution to bypass ill-conditioned QP subproblems.
- **Adjoint sensitivity API**: acados `eval_adjoint_solution_sensitivity` requires seed_x/seed_u as tuples of (stage, np.ndarray), not bare integers.
- **FD epsilon**: eps=1e-5 gives accurate finite-difference ground truth for sensitivity comparison.
- **Solver flags**: qp_solver_ric_alg=0, qp_solver_cond_ric_alg=0, exact_hess_constr/cost/dyn=1 for exact Hessian.

## Remaining

- Secondary claims remain outside the packaged evaluator: the Section 5.3 chain benchmark is not part of the authoritative evaluation path.
- The LQR timing experiments remain informative constraint benchmarks rather than a fully stabilized reproduction of the paper's timing table.

## Issues

- LQR timing varies noticeably across reruns, so the current timing benchmark is less stable than the pendulum sensitivity result
- A local smoke test showed that `solve_for_x0()` is not compatible with the current generated x0 constraint layout in this evaluator, so the repeated benchmark keeps the existing runtime `x` update path.
- No local `mpc.pytorch` or `cvxpygen` reproduction; reference values come from the paper only
- Temporary generated files appear when acados regenerates C code during evaluation
- 2026-04-10 packaging audit found that `scripts/evaluate.sh` had been changed to score `checkpoints/reproduction_results.json`, while the script chain did not reliably regenerate that artifact. Fixed the chain so `scripts/method.sh` runs `method/run_reproduction.py`, then `scripts/evaluate.sh` scores the generated artifact.
- 2026-04-10 dependency audit found that `method/acados` was recorded as a gitlink without a `.gitmodules` entry. Added the mapping and made `scripts/download.sh` avoid invoking git update commands on a pre-populated acados directory that has no nested `.git`.
- 2026-04-10 setup failure: `uv pip install --system` triggered a root-mapped fakeroot IPC error after package resolution. The workaround is to use `python3 -m pip install` in `environment/setup.sh` for this environment.
- 2026-04-10 setup failure 2: the setup phase does not reliably expose `/home/user/method/acados`, so `environment/setup.sh` must not `cd` into the acados source tree. The runtime scripts import the acados Python interface directly from source via `PYTHONPATH`.
- 2026-04-10 runtime failure: CPU smoke-test job `07c40127-2b3` passed setup and rebuilt acados, then failed because `casadi` imported as an incomplete namespace module without `MX`/`SX`. Updated `environment/setup.sh` to force-reinstall pinned runtime wheels and validate the required CasADi symbols during setup.
- 2026-04-10 runtime import hardening: the compute payload for job `07c40127-2b3` still resolved a broken namespace-style `casadi` at runtime even though setup validation passed. Hardened `scripts/run.sh`, `scripts/reproduce.sh`, `scripts/method.sh`, and `scripts/evaluate.sh` to set `PYTHONNOUSERSITE=1`, emit runtime import diagnostics, and prepend the unpacked Python 3.10 CasADi wheel in `environment/vendor_py310/` when present.
- 2026-04-10 vendored runtime path: extended the fallback from CasADi-only to the full Python runtime dependency set (`casadi`, `numpy`, `scipy`, `deprecated`) by unpacking CPython 3.10 wheels into `environment/vendor_py310/` and prepending all unpacked wheel roots in the runnable scripts. Simplified `environment/setup.sh` to a no-op so jobs no longer depend on overlay-time pip state.
- 2026-04-10 runtime bootstrap diagnostics: job `f1d36739-10c` showed that the remaining failure mode is diagnostic blindness rather than a new method bug. The old bootstrap suppressed the actual CasADi import exception, which prevented distinguishing a path-order issue from an ABI or shared-library problem. The next job will emit the exact failing import traceback.
- 2026-04-11 stale acados install state: the compute job showed that simply rerunning `cmake` and `make install` in an existing acados build tree is not sufficient when the source tree revision changed. Because acados installs into its own source tree, stale shared libraries can survive and then fail later inside Python with undefined symbols. The build path now removes prior build/install artifacts before reconfiguring.

## Pending Job

- 2026-04-10 18:50 UTC: resubmitting CPU test job after fixing the incomplete CasADi import observed in job `07c40127-2b3`. Local shell syntax checks, Python compilation, and `python3 validate.py --compare` pass before submission.
- 2026-04-10 22:56 UTC: resubmitting CPU test job after adding runtime import hardening for CasADi. Local shell syntax checks, Python compilation, and `python3 validate.py --compare` pass before submission.
- 2026-04-10 23:02 UTC: resubmitting CPU test job after switching to a fully vendored Python 3.10 runtime path and making `environment/setup.sh` a no-op. Local shell syntax checks, bootstrap CasADi import, and `python3 validate.py --compare` pass before submission.
- 2026-04-10 23:55 UTC: resubmitting CPU test job after tightening the CasADi bootstrap to the active interpreter version and exposing per-root import failures in the job log. Local shell syntax checks, Python compilation, and `python3 validate.py --compare` pass before submission.
- 2026-04-11 00:10 UTC: resubmitting CPU test job after replacing the in-place acados rebuild with a clean rebuild helper and adding a direct post-build `ctypes.CDLL` linkage probe for `libacados.so`. Local shell syntax checks, Python compilation, and `python3 validate.py --compare` pass before submission.

## Deviations from Paper

- The packaged pendulum evaluator is a smaller but faithful version of the paper's setup: `N=20`, `T=1.0`, and sensitivity is checked at a central reference parameter using finite differences around that point rather than across the full paper-scale trajectory map.
- The Section 5.2 benchmark code uses the paper's `n_batch=128`, but the packaged reproduction still reports reduced-scale timings from this local environment rather than a full hardware-matched timing study.
- The LQR evaluator previously double-counted solve time when reporting "solution + adjoint sensitivity" timing; this has been corrected in the packaged evaluator.
- No comparison against mpc.pytorch or cvxpygen baselines
- Chain of masses example (Section 5.3) not included in evaluator
