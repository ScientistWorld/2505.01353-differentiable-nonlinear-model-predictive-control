# Overview

- **Paper ID:** 2505.01353
- **Title:** Differentiable Nonlinear Model Predictive Control
- **Domain:** Optimization / Control Theory / Differentiable Programming
- **TL;DR:** Efficient computation of parametric solution sensitivities for nonlinear MPC using implicit function theorem with interior-point SQP, achieving 3x+ speedups over state-of-the-art differentiable MPC solvers.

## Short Summary

This paper addresses the key challenge of computing parametric solution sensitivities (gradients of optimal solutions with respect to parameters) for general nonlinear programs in model predictive control. The approach combines the implicit function theorem applied to the KKT conditions solved by an interior-point SQP method, with a two-solver strategy: a fast nominal solver for convergence and an exact-Hessian sensitivity solver for accuracy. The implementation in the acados framework exploits the OCP structure via Riccati factorization, achieving significant speedups over prior differentiable MPC implementations like mpc.pytorch and cvxpygen.

## Key Results

- **Pendulum OCP**: Solution sensitivities match finite-difference baselines across parameter range including active-set change boundaries; Gauss-Newton Hessian gives completely wrong results (Remark 3)
- **Bounded LQR**: acados is 3.6x–520x faster than mpc.pytorch and 19x–160x faster than cvxpygen for solving 128 problems with adjoint sensitivities
- **Chain of masses**: Single adjoint sensitivity is ~2.5x faster than full forward Jacobian evaluation

---

# Problem Definition

What problem does this paper address? Write this so that someone with no knowledge of the paper can understand what needs to be solved and how success is measured.

Do NOT describe the paper's method or solution here — only the problem itself. Think about if a future scientist agent try to solve this problem from scratch without knowing what approach the paper took. If you leak the solution, you compromise the benchmark.

## Research Question

The paper addresses the problem of computing **parametric solution sensitivities** — that is, the gradients (derivatives) of the optimal solution of an optimization problem with respect to its parameters. This is critical for combining learning-based methods (neural networks, RL) with model predictive control (MPC), where one needs to backpropagate through an optimization solver.

The challenge is: given an optimal control problem (OCP) of the form:
```
minimize cost(x, u; θ)
subject to dynamics(x, u; θ) = 0
          inequality constraints(x, u; θ) ≤ 0
```
where θ are parameters, compute ∂solution/∂θ efficiently.

This is hard because:
1. The solution involves solving an NLP with inequality constraints
2. At constraint boundaries, the solution map can be nondifferentiable (kinks)
3. Computing exact sensitivities requires the exact Hessian, not just an approximation
4. Existing methods (mpc.pytorch, cvxpygen) are either slow, limited to simple problem forms, or give wrong sensitivities

## Why It Matters

Parametric solution sensitivities are a key building block for:
- Differentiable MPC layers in neural networks
- Learning-enhanced MPC (learning system models, costs, or policies)
- Imitation learning from MPC demonstrations
- Real-time MPC with online adaptation

Without efficient and accurate sensitivity computation, learning-enhanced control cannot achieve the necessary real-time performance, especially on embedded platforms.

## Success Criteria

A successful solution must:
1. **Solve general NLPs**: Support nonlinear cost, nonlinear dynamics, and nonlinear inequality constraints — not just quadratic costs with simple bounds
2. **Compute accurate sensitivities**: Solution sensitivities should match finite-difference baselines
3. **Handle nondifferentiability gracefully**: At active-set changes, provide correct smoothed sensitivities
4. **Be computationally efficient**: Meet or exceed the speed of specialized solvers (3x+ speedup over prior art)
5. **Support both forward and adjoint modes**: Forward for few parameters, adjoint for backpropagation through networks

---

# Paper's Method

How the paper approaches the problem, i.e. the paper's core contributions.

## Key Contribution

The paper proposes an **efficient implementation of parametric solution sensitivity computation** for general nonlinear programs (NLPs) arising in optimal control, using:
1. Implicit function theorem (IFT) applied to the KKT conditions of an interior-point SQP method
2. Exact Hessian computation (not just Gauss-Newton approximation) for correct sensitivities
3. A **two-solver approach**: nominal solver (with approximations for speed) + sensitivity solver (with exact Hessian)
4. Structure-exploiting Riccati factorization via HPIPM/BLASFEO

## Approach

### Mathematical Framework
The NLP solution map z*(θ) is differentiated via IFT applied to the KKT conditions:
- Forward sensitivities: ∂w/∂θ = M⁻¹ · ∂r/∂θ (solve linear system)
- Adjoint sensitivities: s_adj = (∂r/∂θ)ᵀ · M⁻ᵀ · ν (for backpropagation)

Key insight: The KKT matrix M has the same structure as the QP subproblem, so its factorization (Riccati) is reused.

### Two-Solver Approach
1. **Nominal solver**: Uses Gauss-Newton Hessian approximation + regularization for fast convergence
2. **Sensitivity solver**: Uses exact Lagrangian Hessian for accurate sensitivity computation
- Only shares the primal-dual solution (z*, λ*, μ*) between solvers
- Different QP subproblem formulations are allowed

### Smoothed KKT System
Using a barrier parameter τ_min > 0 produces a continuously differentiable approximation of the solution map — valuable for gradient-based learning where the exact map is nondifferentiable at active-set changes.

## Main Claims

1. **Primary**: acados provides correct forward and adjoint sensitivities for general NLPs with inequality constraints, matching finite-difference baselines
2. **Secondary**: Speedups of 3.6x–520x over mpc.pytorch and 19x–160x over cvxpygen for bounded LQR problems
3. **Tertiary**: Adjoint sensitivity computation is ~2.5x faster than full forward Jacobian for single-adjoint queries
4. **Pitfall warning**: Using Gauss-Newton Hessian approximation instead of exact Hessian gives completely wrong sensitivities (shown in Remark 3 and Sec 5.1)

---

# Evaluation

How success is measured. Describe only the metrics, targets, and evaluation procedure — do NOT describe the paper's method or how they achieved these results. Think of this as a general evaluation protocol for other scientists trying to solve the same problem, where they should not see this paper's solution.

## Metrics

The paper evaluates on three dimensions:

### 1. Sensitivity Accuracy
- **Metric**: Comparison of computed sensitivities against finite-difference (FD) baselines
- **How computed**: For the highly-parametric OCP, compute ∂u₀*(θ)/∂θ via the method and via finite differences. Report max absolute error.
- **Direction**: Lower error is better (0 = exact match)

### 2. Computational Efficiency (Timing)
- **Metric**: Wall-clock time in milliseconds for solving N batch problems and computing sensitivities
- **How computed**: Time to solve n_batch = 128 bounded LQR problems with N=20, nx=8, nu=4, nθ=248 parameters
- **Comparison**: Reported as speedup factor relative to baseline solvers (mpc.pytorch, cvxpygen/OSQP)
- **Direction**: Lower time is better; speedup > 1 means faster than baseline

### 3. Adjoint Sensitivity Efficiency
- **Metric**: Time for adjoint sensitivity computation vs. full forward Jacobian computation
- **How computed**: Chain-of-masses example with N=40, nx=9, nu=3, nθ=113
- **Direction**: Lower time is better; adjoint should be faster than forward for single-adjoint queries

## Baselines and Targets

The paper compares against two state-of-the-art differentiable MPC solvers:

| Solver | Description | Paper's Reported Speedup |
|--------|-------------|------------------------|
| mpc.pytorch | iLQR-based differentiable MPC | acados 3.6x–520x faster |
| cvxpygen/OSQP | Code-generated QP layers | acados 19x–160x faster |

Key reference timings (acados):
- Bounded LQR nominal solution: 8.5ms (u_max=10⁴), 17.6ms (u_max=1.0)
- Bounded LQR with adjoint sensitivity: 34.5ms (u_max=10⁴), 42.0ms (u_max=1.0)
- Chain example single adjoint: ~0.6ms

## Evaluation Protocol

### Experiment 1: Highly-Parametric OCP (Pendulum)
- **Problem**: Cart-pole with parametric mass, N=50, nx=4, nu=1, nθ=1
- **Test**: Compute sensitivities across θ ∈ [-1.5, 1.5] and compare to finite differences
- **Pass criterion**: Max |error| < 10⁻² (or visual agreement with kinks at active-set changes)

### Experiment 2: Bounded LQR Benchmark
- **Problem**: Linear-quadratic OCP with parametric A,B matrices and control bounds
- **n_batch** = 128 random initial states
- **Test**: Compare solution + adjoint sensitivity timing
- **Pass criterion**: Correct solution convergence + reasonable timing

### Experiment 3: Chain of Masses
- **Problem**: Nonlinear OCP with chain of masses model, N=40, n_masses=3
- **Test**: Compare forward vs adjoint sensitivity computation time
- **Pass criterion**: Adjoint is ~2.5x faster than forward for single-adjoint query

### General Protocol
- All timing experiments should run on the same hardware (or clearly report hardware differences)
- Report mean ± std over multiple batch runs
- Sensitivity accuracy should be validated at multiple θ values, including near active-set change boundaries

---

# Reproduction Log

### Iteration 4: gpt-5.4 (verifier)
- **Milestone**: `core_claim` | **Status**: done
- **GPU**: 0.0h

<details>
<summary>Progress Log</summary>

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

</details>

### Iteration 4: gpt-5.4 (verifier)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 3m | **GPU**: 0.0h
- **Jobs**: 6 total (1 completed, 5 failed)

<details>
<summary>Progress Log</summary>

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

### [2026-04-10 23:55] - core_claim
- CPU smoke-test job `f1d36739-10c` still failed in the runtime preflight, but the failure narrowed to `method/bootstrap_runtime.py`: it kept probing `/home/user/.local/lib/python3.12/site-packages` and then swallowed the real CasADi import exception from the vendored runtime.
- Patched `method/bootstrap_runtime.py` to restrict autodiscovery to the active interpreter version, preserve the job's `PYTHONPATH` ordering, and report the exact exception and traceback for each attempted CasADi root.
- Updated `scripts/run.sh` to print `python3` version details, leading `sys.path`, and the detailed bootstrap failure before aborting. Local shell syntax checks, Python compilation, and `python3 validate.py --compare` all pass before the next CPU smoke test.

### [2026-04-11 00:10] - core_claim
- CPU smoke-test job `a4a57e9d-0d9` passed the CasADi runtime bootstrap and rebuilt acados, which confirms the vendored Python runtime path now works on the compute node.
- The new failure moved into acados shared-library loading: `libacados.so` raised `undefined symbol: d_ocp_qp_seed_memsize` inside `AcadosOcpSolver`, while the installed library stamp still reported acados commit `c1c1e81` even though the source tree is at `530daae`.
- Added `scripts/build_acados.sh` and switched both `scripts/run.sh` and `scripts/download.sh` to use it so every build starts from a clean acados build/install state. `scripts/run.sh` now also performs a direct `ctypes.CDLL` load check on `libacados.so` before launching the method.

### [2026-04-11 00:22] - core_claim
- CPU smoke-test job `3f681f30-85a` confirmed the clean rebuild path is taking effect: the job rebuilt acados from source commit `0e37d8f` and replaced the stale installed commit `c1c1e81`.
- The remaining failure is now isolated to dynamic loading on the compute node: the fresh `libacados.so` still failed `ctypes.CDLL(...)` with `undefined symbol: d_ocp_qp_seed_memsize`, even though `libhpipm.so` exports that symbol and `libacados.so` lists `libhpipm.so` as a dependency.
- Patched the runtime bootstrap to preload `libblasfeo.so.0`, `libhpipm.so`, `libqpOASES_e.so`, and `libacados.so` by absolute path with `RTLD_GLOBAL` before importing `acados_template`. `scripts/run.sh` now uses the same preload path in its preflight check.

### [2026-04-11 00:36] - core_claim
- CPU smoke-test job `c40a31e6-f78` passed the shared-library preload workaround and progressed through the pendulum experiment into the bounded-LQR path, so the compute-node `libacados.so` loading issue is now effectively mitigated.
- The new failure is a pure Python/CasADi module-identity bug: during the later LQR setup, `acados_template` rejected `model.x` with `TypeError: model.x must be casadi.SX or casadi.MX, got <class 'casadi.casadi.SX'>`.
- Root cause: `ensure_casadi_importable()` was force-removing `casadi` from `sys.modules` on every call, so repeated `_import_acados()` calls in `run_reproduction.py` created a second CasADi module instance while `acados_template` still held `SX`/`MX` from the first one. Patched the bootstrap to reuse an already-valid CasADi module instead of reimporting it.

### [2026-04-11 00:49] - core_claim
- CPU smoke-test job `58199a5f-9c0` completed successfully end to end inside the compute container with return code 0.
- Verified the full packaged path `scripts/run.sh -> scripts/reproduce.sh -> scripts/method.sh -> scripts/evaluate.sh`, including vendored Python runtime bootstrap, clean acados rebuild, shared-library preload, raw result generation, and scoring.
- The compute-node run reproduced the core pendulum claim again (`exact=0.002597`, `gauss_newton=2.200135`) and also completed both reduced-scale LQR timing benchmarks (`28.45 ms`, `34.36 ms`), so the packaged environment is now confirmed runnable on cluster hardware rather than only on the login node.

</details>


---

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

### [2026-04-10 23:55] - core_claim
- CPU smoke-test job `f1d36739-10c` still failed in the runtime preflight, but the failure narrowed to `method/bootstrap_runtime.py`: it kept probing `/home/user/.local/lib/python3.12/site-packages` and then swallowed the real CasADi import exception from the vendored runtime.
- Patched `method/bootstrap_runtime.py` to restrict autodiscovery to the active interpreter version, preserve the job's `PYTHONPATH` ordering, and report the exact exception and traceback for each attempted CasADi root.
- Updated `scripts/run.sh` to print `python3` version details, leading `sys.path`, and the detailed bootstrap failure before aborting. Local shell syntax checks, Python compilation, and `python3 validate.py --compare` all pass before the next CPU smoke test.

### [2026-04-11 00:10] - core_claim
- CPU smoke-test job `a4a57e9d-0d9` passed the CasADi runtime bootstrap and rebuilt acados, which confirms the vendored Python runtime path now works on the compute node.
- The new failure moved into acados shared-library loading: `libacados.so` raised `undefined symbol: d_ocp_qp_seed_memsize` inside `AcadosOcpSolver`, while the installed library stamp still reported acados commit `c1c1e81` even though the source tree is at `530daae`.
- Added `scripts/build_acados.sh` and switched both `scripts/run.sh` and `scripts/download.sh` to use it so every build starts from a clean acados build/install state. `scripts/run.sh` now also performs a direct `ctypes.CDLL` load check on `libacados.so` before launching the method.

### [2026-04-11 00:22] - core_claim
- CPU smoke-test job `3f681f30-85a` confirmed the clean rebuild path is taking effect: the job rebuilt acados from source commit `0e37d8f` and replaced the stale installed commit `c1c1e81`.
- The remaining failure is now isolated to dynamic loading on the compute node: the fresh `libacados.so` still failed `ctypes.CDLL(...)` with `undefined symbol: d_ocp_qp_seed_memsize`, even though `libhpipm.so` exports that symbol and `libacados.so` lists `libhpipm.so` as a dependency.
- Patched the runtime bootstrap to preload `libblasfeo.so.0`, `libhpipm.so`, `libqpOASES_e.so`, and `libacados.so` by absolute path with `RTLD_GLOBAL` before importing `acados_template`. `scripts/run.sh` now uses the same preload path in its preflight check.

### [2026-04-11 00:36] - core_claim
- CPU smoke-test job `c40a31e6-f78` passed the shared-library preload workaround and progressed through the pendulum experiment into the bounded-LQR path, so the compute-node `libacados.so` loading issue is now effectively mitigated.
- The new failure is a pure Python/CasADi module-identity bug: during the later LQR setup, `acados_template` rejected `model.x` with `TypeError: model.x must be casadi.SX or casadi.MX, got <class 'casadi.casadi.SX'>`.
- Root cause: `ensure_casadi_importable()` was force-removing `casadi` from `sys.modules` on every call, so repeated `_import_acados()` calls in `run_reproduction.py` created a second CasADi module instance while `acados_template` still held `SX`/`MX` from the first one. Patched the bootstrap to reuse an already-valid CasADi module instead of reimporting it.

### [2026-04-11 00:49] - core_claim
- CPU smoke-test job `58199a5f-9c0` completed successfully end to end inside the compute container with return code 0.
- Verified the full packaged path `scripts/run.sh -> scripts/reproduce.sh -> scripts/method.sh -> scripts/evaluate.sh`, including vendored Python runtime bootstrap, clean acados rebuild, shared-library preload, raw result generation, and scoring.
- The compute-node run reproduced the core pendulum claim again (`exact=0.002597`, `gauss_newton=2.200135`) and also completed both reduced-scale LQR timing benchmarks (`28.45 ms`, `34.36 ms`), so the packaged environment is now confirmed runnable on cluster hardware rather than only on the login node.

## Stop Justification

- Stopping at `core_claim` is justified because the paper's central qualitative result is reproduced and verified in this workspace: exact-Hessian sensitivities closely match finite differences while the Gauss-Newton approximation is materially worse on the same pendulum OCP.
- The workspace is now packaged as a usable gym: problem and evaluation components are separated from the method implementation, `scripts/evaluate.sh` writes `scoring/scores.json`, and the scoring rubric emphasizes the validated core claim while preserving the LQR timing benchmarks as constraint targets.
- The remaining gaps are completeness-related rather than correctness-related: the LQR timing benchmarks are still reduced-scale and timing-volatile, no local reproduction of external baselines is included, and the Section 5.3 chain-of-masses result is outside the authoritative evaluation path.
