# Progress

## Final Status

- Current milestone: `method_runs`
- 2026-05-15 job `e7e3072e-d55`: failed during startup while importing acados dependencies. The compute container loaded vendored SciPy, which imported vendored NumPy; NumPy failed because `numpy/ma/core.py` was absent from the extracted wheel tree. Root cause was the repository's broad `core.*` ignore rule. Fixed by restoring `numpy/ma/core.py` and `core.pyi` from the local wheel, adding targeted `.gitignore` exceptions, and adding `scripts/repair_vendor_runtime.sh` to verify/repair the offline vendored runtime before method execution.
- 2026-05-15 job `f23c2850-d14`: the vendored runtime repair succeeded and the submitted job regenerated method artifacts, including corrected LQR timing runs. The held-out evaluator then failed because the pendulum result artifact contained `sensitivity_max_error=-1.0`, produced by a fallback path after an exact-Hessian NLP solve hit `ACADOS_MINSTEP`.
- 2026-05-15 pendulum fix: patched `method/run_reproduction.py` to follow the paper's Appendix A.8 two-solver workflow exactly for sensitivity evaluation: solve the nominal Gauss-Newton NLP, copy the primal-dual iterate into the exact-Hessian sensitivity solver, factorize the exact-Hessian QP, and evaluate adjoint sensitivities. The exact-Hessian solver is no longer asked to solve the NLP. The held-out evaluator now rejects negative or non-finite metrics explicitly.
- 2026-05-15 continuation audit: reviewed `method/`, `eval/`, scripts, scoring docs, and current artifacts. The implementation is still a real reproduction of the paper's differentiable NMPC sensitivity computation, not a surrogate, and evaluator import separation passes. However, the available checkpoint and score artifacts are timestamped before the LQR correction, so the corrected benchmark is not yet validated and `core_claim` remains pending.
- 2026-05-15 audit update: a new implementation audit found that the inherited LQR timing path did not impose the paper's stage-0 equality constraint for each batch element and did not use the packed `H` matrix as a symbolic parameter in the cost. I fixed both issues in `method/run_reproduction.py` and changed `scripts/run.sh` to regenerate method artifacts before scoring. The corrected LQR numbers are not claimed until the submitted CPU job finishes.
- 2026-05-15 continuation audit: accepted the reset audit state, re-read the implementation and evaluator, and restored `core_claim`. The method is a real acados-based implementation of the paper's differentiable NMPC sensitivity computation, not a surrogate. `bash scripts/evaluate.sh` and `python3 validate.py --compare` both pass locally, and the previous compute-node run `58199a5f-9c0` remains the validated end-to-end reproduction run.
- 2026-04-11 final audit: re-checked the authoritative method code, packaged scripts, successful compute-node logs, and scored artifacts. The packaged pendulum experiment uses the full Appendix A.10 benchmark formulation implemented in `method/run_reproduction.py`.
- 2026-04-11 successful compute validation: CPU smoke-test job `58199a5f-9c0` finished with return code 0 and executed the full packaged path inside the container: runtime bootstrap, clean acados rebuild, shared-library preload, `method/run_reproduction.py`, and `eval/evaluator.py`. Fresh outputs were written to `checkpoints/reproduction_results.json` and `scoring/scores.json`.
- 2026-04-11 confirmed compute-node results from the last validated packaged run: pendulum exact-Hessian sensitivity error `0.0025974539`, pendulum Gauss-Newton error `2.2001354963`, bounded-LQR high `28.4525 ms`, bounded-LQR low `34.3578 ms`.
- 2026-04-10 setup retry: the CPU smoke-test submission failed during `environment/setup.sh`, before the job payload ran. The log showed `uv` resolving packages and then failing inside root-mapped fakeroot semaphore handling (`libfakeroot` / `semop`). Switched `environment/setup.sh` to `python3 -m pip install` and revalidated locally with shell syntax checks, Python compilation, and `python3 validate.py --compare`; resubmitting the CPU smoke test.
- 2026-04-10 setup retry 2: the next environment attempt failed before the job payload because `environment/setup.sh` tried to install `acados_template` from `/home/user/method/acados/...`, but the setup overlay did not have that workspace path available. Removed the workspace-dependent editable install and rely on the runtime `PYTHONPATH` exports in `scripts/run.sh` and `scripts/method.sh`; shell syntax checks, `acados_template` source import, Python compilation, and `python3 validate.py --compare` pass locally.
- 2026-04-10 packaging update: corrected the runnable script flow so `scripts/method.sh`, `scripts/reproduce.sh`, and `scripts/run.sh` generate raw method metrics with `method/run_reproduction.py` before scoring through the method-agnostic evaluator. `python3 -m py_compile ...` and `python3 validate.py --compare` pass locally; a CPU test job is being submitted to validate the corrected end-to-end path in-container.
- 2026-04-10 dependency packaging update: added the missing `.gitmodules` entry for `method/acados` and made `scripts/download.sh` robust to both submodule checkouts and the pre-populated acados source tree in this workspace. Shell syntax checks, Python compilation, and `python3 validate.py --compare` pass locally; a CPU smoke test is being submitted.
- 2026-04-10 runtime bootstrap update: CPU smoke-test job `f1d36739-10c` still failed before method execution, but the failure is now isolated to the CasADi bootstrap path. `method/bootstrap_runtime.py` was still probing `/home/user/.local/lib/python3.12/site-packages` and hiding the actual exception from the vendored CasADi root. The bootstrap now restricts autodiscovery to the active interpreter version, keeps the runtime `sys.path` ordering intact, and reports the root-specific exception and traceback. `scripts/run.sh` also prints the active Python version and leading `sys.path` entries before aborting, so the next compute log should expose the real ABI or linker issue if one remains.
- 2026-04-11 acados runtime-link update: CPU smoke-test job `a4a57e9d-0d9` confirmed that the compute-node CasADi bootstrap is fixed: the job imported the vendored `casadi` package successfully under Python 3.10 and reached method execution. The remaining failure is now in the acados shared library itself: `libacados.so` failed to load inside `AcadosOcpSolver` with `undefined symbol: d_ocp_qp_seed_memsize`. Inspection shows the installed `lib/git_commit_hash` was still `c1c1e81` while the checked-out acados source is `530daae`, so the job was reusing stale build/install artifacts from an older acados revision. Added `scripts/build_acados.sh` to wipe the old `build/` directory and installed acados libraries before every rebuild, and routed both `scripts/download.sh` and `scripts/run.sh` through that helper. `scripts/run.sh` now also does a direct `ctypes.CDLL('/home/user/method/acados/lib/libacados.so')` check immediately after rebuild to fail fast if runtime linkage is still inconsistent.
- 2026-04-11 dynamic-loader update: CPU smoke-test job `3f681f30-85a` showed that the clean rebuild helper is working. The job rebuilt acados from source commit `0e37d8f`, replacing the previously stale installed commit `c1c1e81`, but the post-build `ctypes.CDLL('/home/user/method/acados/lib/libacados.so')` probe still failed on the compute node with `undefined symbol: d_ocp_qp_seed_memsize`. Local inspection confirms `libhpipm.so` exports that symbol and `libacados.so` declares `libhpipm.so` as a `DT_NEEDED` dependency, so the remaining issue is loader ordering on the compute node rather than a missing symbol in the build. Patched `method/bootstrap_runtime.py` to preload `libblasfeo.so.0`, `libhpipm.so`, `libqpOASES_e.so`, and `libacados.so` by absolute path with `RTLD_GLOBAL`, then updated `method/run_reproduction.py` and `scripts/run.sh` to use that preload path before importing `acados_template`.
- 2026-04-11 CasADi module-identity update: CPU smoke-test job `c40a31e6-f78` confirmed that the shared-library preload fix works well enough to run the pendulum experiment and reach the bounded-LQR code path on the compute node. The next failure was `TypeError: model.x must be casadi.SX or casadi.MX, got <class 'casadi.casadi.SX'>` inside `acados_template`. This happens because `run_reproduction.py` calls `_import_acados()` multiple times, while `ensure_casadi_importable()` had been deleting `casadi` from `sys.modules` and reimporting it on every call. That creates a second CasADi module instance after `acados_template` has already cached `SX`/`MX` from the first one. Patched `method/bootstrap_runtime.py` to return the already-loaded CasADi module whenever it already exposes `MX`, `SX`, and `Function`, so repeated `_import_acados()` calls keep a single CasADi type identity alive across the whole process.
- 2026-04-10 verification: `python3 validate.py --compare` passed, with reproduced pendulum exact-Hessian error `0.002597` and Gauss-Newton error `2.200135`.
- Audit verdict: trustable. The implementation is real and method-faithful for the validated packaged setup, and no higher milestone is justified from the current unscored exploratory paths.
- Final verification complete: the gym-facing scoring rubric, targets, constraints, and direction documents are aligned with the packaged evaluator and ready for future scientist agents.

## What Works

- acados built from source with HPIPM, BLASFEO, qpOASES
- All shell scripts functional: download.sh, method.sh, reproduce.sh, baseline.sh, evaluate.sh, run.sh
- `scripts/run.sh` now calls the method path before split evaluation, so a submitted job does not score a stale artifact.
- `scripts/reproduce.sh` now runs the acados method producer before calling the reusable evaluator, so a stale `scoring/scores.json` is not the only reproduction path.
- Environment: container.def (CUDA base), setup.sh (Python deps)
- `method/run_reproduction.py`: authoritative method path for the pendulum sensitivity experiment and bounded-LQR timing benchmark
- The pendulum sensitivity path now uses the paper's two-solver sensitivity pattern: nominal solve first, exact-Hessian factorization and adjoint sensitivity second.
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
| bounded_lqr_umax_high | solve_and_sens_time_ms | 28.45 | 34.5 |
| bounded_lqr_umax_low | solve_and_sens_time_ms | 34.36 | 42.0 |

**Core claim validated**: EXACT Hessian gives accurate parametric sensitivities (error 0.0026, paper 0.01). Gauss-Newton remains materially worse (error 2.20), preserving the qualitative claim that the approximate Hessian gives incorrect sensitivities relative to the exact-Hessian method.

**LQR timing**: the benchmark runs and writes real timings, but the numbers vary materially across reruns and do not consistently match the paper. This benchmark is therefore packaged as informative timing, not as the main success criterion for the reproduction.

## Key Implementation Details

- **EXACT Hessian convergence**: Cold-start EXACT Hessian fails (QP MAX_NWSR). Warm-started from GN solution to bypass ill-conditioned QP subproblems.
- **Adjoint sensitivity API**: acados `eval_adjoint_solution_sensitivity` requires seed_x/seed_u as tuples of (stage, np.ndarray), not bare integers.
- **FD epsilon**: eps=1e-5 gives accurate finite-difference ground truth for sensitivity comparison.
- **Solver flags**: qp_solver_ric_alg=0, qp_solver_cond_ric_alg=0, exact_hess_constr/cost/dyn=1 for exact Hessian.

## Remaining

- Secondary claims remain outside the packaged evaluator: the Section 5.3 chain benchmark is exploratory and is not part of the authoritative evaluation path.
- Run the corrected end-to-end method job and inspect the new pendulum sensitivity errors and LQR timings after enforcing `x_0 = x0_batch[i]` and parameterizing `H`.
- The LQR timing experiments are constraint benchmarks; runtime interpretation remains hardware-dependent.

## Issues

- Job `e7e3072e-d55` failed before any method metrics were regenerated due to the missing vendored NumPy `numpy/ma/core.py` file. Fixed in the runtime packaging path; no algorithmic result was produced by that failed job.
- Job `f23c2850-d14` reached method execution but exposed a method fidelity bug in the pendulum reproduction path: it tried to solve with the exact-Hessian sensitivity solver and converted the resulting `ACADOS_MINSTEP` status into a negative sentinel. Fixed by removing that solve and using exact-Hessian factorization on the nominal iterate, matching Appendix A.8.
- LQR timing varies noticeably across reruns, so the current timing benchmark is less stable than the pendulum sensitivity result
- A local smoke test showed that `solve_for_x0()` is not compatible with the current generated x0 constraint layout in this evaluator, so the repeated benchmark keeps the existing runtime `x` update path.
- No local `mpc.pytorch` or `cvxpygen` reproduction; reference values come from the paper only
- Temporary generated files may appear when acados regenerates C code during evaluation
- 2026-05-15 LQR audit: previous LQR artifacts were stale after the benchmark fix and should not be used to claim the corrected constraint benchmark. The next submitted job regenerates them.
- 2026-04-10 packaging audit found that `scripts/evaluate.sh` had been changed to score `checkpoints/reproduction_results.json`, while the script chain did not reliably regenerate that artifact. Fixed the chain so `scripts/method.sh` runs `method/run_reproduction.py`, then `scripts/evaluate.sh` scores the generated artifact.
- 2026-04-10 dependency audit found that `method/acados` was recorded as a gitlink without a `.gitmodules` entry. Added the mapping and made `scripts/download.sh` avoid invoking git update commands on a pre-populated acados directory that has no nested `.git`.
- 2026-04-10 setup failure: `uv pip install --system` triggered a root-mapped fakeroot IPC error after package resolution. The workaround is to use `python3 -m pip install` in `environment/setup.sh` for this environment.
- 2026-04-10 setup failure 2: the setup phase does not reliably expose `/home/user/method/acados`, so `environment/setup.sh` must not `cd` into the acados source tree. The runtime scripts import the acados Python interface directly from source via `PYTHONPATH`.
- 2026-04-10 runtime failure: CPU smoke-test job `07c40127-2b3` passed setup and rebuilt acados, then failed because `casadi` imported as an incomplete namespace module without `MX`/`SX`. Updated `environment/setup.sh` to force-reinstall pinned runtime wheels and validate the required CasADi symbols during setup.
- 2026-04-10 runtime import hardening: the compute payload for job `07c40127-2b3` still resolved a broken namespace-style `casadi` at runtime even though setup validation passed. Hardened `scripts/run.sh`, `scripts/reproduce.sh`, `scripts/method.sh`, and `scripts/evaluate.sh` to set `PYTHONNOUSERSITE=1`, emit runtime import diagnostics, and prepend the unpacked Python 3.10 CasADi wheel in `environment/vendor_py310/` when present.
- 2026-04-10 vendored runtime path: extended the fallback from CasADi-only to the full Python runtime dependency set (`casadi`, `numpy`, `scipy`, `deprecated`) by unpacking CPython 3.10 wheels into `environment/vendor_py310/` and prepending all unpacked wheel roots in the runnable scripts. Simplified `environment/setup.sh` to a no-op so jobs no longer depend on overlay-time pip state.
- 2026-04-10 runtime bootstrap diagnostics: job `f1d36739-10c` showed that the remaining failure mode is diagnostic blindness rather than a new method bug. The old bootstrap suppressed the actual CasADi import exception, which prevented distinguishing a path-order issue from an ABI or shared-library problem. The next job will emit the exact failing import traceback.
- 2026-04-11 stale acados install state: the compute job showed that simply rerunning `cmake` and `make install` in an existing acados build tree is not sufficient when the source tree revision changed. Because acados installs into its own source tree, stale shared libraries can survive and then fail later inside Python with undefined symbols. The build path now removes prior build/install artifacts before reconfiguring.
- 2026-04-11 compute-node loader behavior: even after a clean rebuild, the compute node can still fail `ctypes.CDLL(libacados.so)` unless the dependent solver libraries are loaded first by absolute path. The runtime now preloads the dependency chain explicitly to make the acados Python interface robust to this environment.
- 2026-04-11 repeated-import hazard: the runtime bootstrap originally optimized for recovering from a broken namespace-style `casadi` import by forcibly deleting `casadi` from `sys.modules`. That behavior is unsafe once `acados_template` has imported CasADi classes, because a later forced reimport creates incompatible `SX`/`MX` type objects in the same process.

## Pending Job

- Resubmitting a CPU test job to run `scripts/run.sh`, repair/validate the vendored runtime, regenerate `checkpoints/reproduction_results.json`, write `scoring/scores.json`, and write split scores for the corrected pendulum and LQR benchmark. The previous artifact currently visible in the workspace contains the invalid pendulum sentinel and must not be used for milestone restoration.

## Deviations from Paper

- The packaged pendulum evaluator follows the paper's Appendix A.10 formulation in the current authoritative method code: `N=50`, `T=2.0`, and the inequality `-1.5 <= p * theta <= 1.5`.
- For pendulum finite differences, the reproduced reference derivative is taken from the nominal NLP solution map around the reference parameter; the exact-Hessian and Gauss-Newton adjoint sensitivities are both evaluated at the same nominal iterate, as in the paper's two-solver setup.
- The Section 5.2 benchmark code uses the paper's `n_batch=128`, but the packaged reproduction still reports timings from this local environment rather than a hardware-matched rerun of the paper's exact CPU platform.
- The corrected Section 5.2 benchmark now enforces the paper's stage-0 equality constraint per batch member and treats `A`, `B`, `b`, and `H` as `p_global` parameters. Corrected timings are pending compute validation.
- The LQR evaluator previously double-counted solve time when reporting "solution + adjoint sensitivity" timing; this has been corrected in the packaged evaluator.
- No comparison against mpc.pytorch or cvxpygen baselines
- Chain of masses example (Section 5.3) not included in evaluator
