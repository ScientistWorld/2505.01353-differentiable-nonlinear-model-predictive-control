# Hardening Report

## Summary

The old hidden test scored a single number the method wrote about itself. That was the error of its own finite difference at one parameter value, compared against "anchor" errors the method also supplied. Fabricated numbers, inflated anchors and self-graded finite differences therefore outranked the reference. Meanwhile a genuinely better derivative (lower sensitivity clipping) scored *lower*.

The test is rebuilt around raw predictions on hidden instances:

- **Protocol.** `scripts/evaluate_test.sh` (no arguments) writes instances that only `eval/test/` holds and runs the method's `scripts/predict.sh` on them. The method returns only `u0` and its sensitivity. Every metric is recomputed from those raw numbers.
  - The ground truth is computed independently of any method (no acados): IPOPT, Newton refinement of the KKT system to machine precision, an implicit-function-theorem derivative with long-double iterative refinement, and a Richardson finite-difference cross-check.
  - Cross-check agreement is a median of 1e-11 and a worst case of 6e-9 relative.
  - Answers are cached in `eval/test/cache/` and loaded into memory before the predictor runs.
- **Three scored experiments** from the paper (weights 0.5 / 0.2 / 0.3):
  - `pendulum_sensitivity_accuracy`: Sec. 5.1, exact map, 193 hidden instances.
  - `pendulum_smoothed_sensitivity`: Sec. 2.2 / Fig. 2, `tau_min` in {1e-4, 1e-3, 1e-2}, 180 instances.
  - `bounded_lqr_adjoint_accuracy`: Sec. 5.2 / App. A.11, 248-parameter adjoint, `u_max` in {1, 1e4}, 140 instances.
- **Metrics per experiment:** `frac_sens_accurate` (primary), `mean_log10_sens_rel_err`, and the constraint `frac_u0_accurate`. Each instance is gated by a correct solution. Wall-clock timing is no longer scored; the paper's Table 1/2 numbers are kept unchanged in `scoring/reference.json` under `_paper_table1_timings_ms` / `_paper_table2_gpu_timings_s`.
- **Failure handling:**
  - Missing, malformed, boolean, string or non-finite entries make that instance fail.
  - An omitted experiment gets the worst value for that method.
  - A crashed, empty or timed-out predictor gets the worst value in every metric of every experiment.
  - A placeholder "failed" score file is written before anything else runs.
  - Every method name in the predictions is scored, so no writable index decides coverage.
- **Visible train slice:** `eval/train/` uses the same protocol with independent code and public instances (103 / 90 / 69).

All numbers below are actual outputs of the hidden-test evaluator (`hardening/results/`, job `30e92385-4ff`; harness `hardening/run_checks.py`). The reference predictor is deterministic: two independent runs produced byte-identical scores, so seed noise is 0. Paired comparisons use identical instances; ± is one standard error of the per-instance mean difference.

## Fixes to the reproduction (method side)

1. **Sensitivity solver restored to the paper's.** The earlier iteration partially condensed it to 5 stages. It now uses the exact Hessian, classic Riccati and no condensing (paper code; acados documents factorization only without condensing).
2. **Gauss–Newton baseline isolated.** It now uses an identical, non-condensed sensitivity solver with the Gauss–Newton Hessian, so it differs from the proposal only in the Hessian (Remark 3).
3. **Warm start from the paper's sweep.** The pendulum OCP is multimodal: on train, 90 of 120 instances reached distinct local minima from different starts. The old reference at θ = 0.8 was on a non-optimal branch, with du0/dθ = −55 where the best local minimum has +146.
   - Each instance now carries the warm start of the paper's sweep: the solution on the same branch at θ ∓ 1e-3. The derivative being scored is therefore unambiguous.
4. **Smoothed solves.** These use the paper's HPIPM `mu0 = 1e3`. The earlier iteration's 1e-3 is below `tau_min` and stalled 88 of 180 smoothed solves with MINSTEP.
5. **Forward sensitivity for the pendulum**, as in the paper's Figure 2 code. The adjoint path gives the same numbers within 0.01 decades.
6. **LQR parameter layout defined explicitly.** It is column-major `vec(A), vec(B), b, vec(H)`, and instances carry θ directly; the red-team noted an earlier A/B transposition.

## Do better results now score higher?

**Before** (old test, `(A↑, R↓)` per REDTEAM.md):

| variant | before |
|---|---|
| reference | (6.115, 0) |
| lower sensitivity clipping (78× more accurate derivative) | (6.098, 0), **lower** |
| tighter solve, tolerance 1e-10 | (8.512, 0), higher |
| Gauss–Newton derivative | (0, 0), lower |

**After.** Hidden test, `frac_sens_accurate / mean_log10_sens_rel_err / frac_u0_accurate`; paired Δ of the per-instance log error against the reference:

| method | exact pendulum | smoothed pendulum | LQR adjoint |
|---|---|---|---|
| **reference** `acados_exact_hessian` | **1.000 / −7.77 / 1.000** | **0.811 / −5.41 / 0.989** | **0.971 / −8.79 / 1.000** |
| better: tighter nominal solve 1e-10 + clipping 1e-12 | 1.000 / −9.20 / 1.000 (Δ −1.43 ± 0.13, 165 of 193 better) | 0.811 / −5.41 / 0.989 | 1.000 / −9.97 / 1.000 (Δ −1.18 ± 0.14; Δfrac +0.029 ± 0.014) |
| better: clipping 1e-12 | 0.995 / −8.78 / 1.000 (Δ −1.02 ± 0.12) | 0.811 / −5.41 / 0.989 | 0.971 / −9.18 / 1.000 (Δ −0.39 ± 0.07) |
| weaker: nominal tolerance 1e-5 (LQR 1e-4) | 0.974 / −7.09 / 1.000 (Δ +0.68 ± 0.08) | 0.800 / −5.33 / 0.989 | 0.936 / −8.38 / 0.971 |
| weaker: Gauss–Newton Hessian (baseline) | 0.005 / −0.16 / 1.000 | 0.000 / −0.54 / 0.989 | 0.971 / −8.79 / 1.000 (equals exact for a QP) |
| weaker: drop inequality constraints (baseline) | 0.000 / 0.00 / 0.000 | 0.000 / 0.00 / 0.000 | 0.586 / −5.86 / 0.586 |

- **Better variants** are above the reference by about 10 standard errors on paired instances. Tighter tolerance is worse on no metric. Lower clipping loses one exact-pendulum instance on the accurate fraction (0.995) but gains a decade of precision.
- **Weaker variants** are below it.
- **Illustrative aggregate rank.** These use the stated weights and coefficients, with each metric divided by its spread across these methods; the real normalisation comes from future attempts. Test scores: better_tight +0.35, better_clip +0.12, reference 0, weaker −0.27, Gauss–Newton −2.27, unconstrained −5.21.
- **Train matches test:** reference train scores are 1.000 / −7.90, 0.778 / −5.10 and 0.971 / −8.88.

## Shortcuts: fix and score before → after

| shortcut (REDTEAM.md) | before | fix | after (hidden test) |
|---|---|---|---|
| FD oracle: finite differences graded against themselves | (13.67, 0), **higher** | Independent high-precision ground truth; no self-reported error is read | central FD at the paper's settings: 0.990 / −6.52 (exact), 0.950 / −8.28 (LQR), both **below**; aggregate −0.07 |
| Fabricated zero error | (12.0, 0), **higher** | Metrics recomputed from raw predictions | 0 / 0 / 0 in every experiment (worst) |
| Boolean / null / NaN / negative / empty / success-flag entries | `false` scored (12.0, 0); the others raised, with **no** worst values | Strict numeric parsing (bool, str, None, NaN, inf rejected); each bad instance fails; worst values written | garbage types 0 / 0 / 0; extreme values (±1e308) 0 / 0 / 0 |
| Baseline inflation / moving anchors | (12.12, 0) / (13.33, −13.33), **higher** | No method-supplied anchors; comparisons only against fixed ground truth and stored reference scores | injecting a garbage `gauss_newton_approx` leaves the reference at 1.000 / −7.77 / 1.000; the garbage method gets 0 |
| Single point (answer fewer instances) | tie | Test size fixed by `eval/`; missing instances count as failed | 10% of answers → 0.098 / −0.77 / 0.098 |
| Method omission via writable train-score index | tie (bad method hidden) | Every method in the predictions is scored in every experiment; an omitted experiment gets the worst value | omitting two experiments → 0 / 0 / 0 in those |
| Missing method / crash | raised, no worst values | Placeholder failed scores written first; a crash, timeout or empty output gives worst values for every metric of every experiment | crash and empty output → status `failed`, all 0 |
| *(new)* Copy nearest train answer | n/a | Hidden continuous instances; trivially-zero-sensitivity instances excluded (u0 at the force bound) | 0 / 0 / 0 (it was 0.071 on exact before the exclusion) |
| *(new)* Self-reported metrics or extra fields | n/a | Only `u0` and the sensitivity are read | identical to the reference (fields ignored) |
| *(new)* Answer exact instances with a smoothed solution | n/a | Per-instance solution check (`frac_u0_accurate` gate) | exact pendulum 0.000 / −0.03 / 0.010 |

## Shortcuts and issues left open

1. **Brute-force finite differences with a much tighter solve.** Central differences with Richardson extrapolation (4 extra solves per parameter, 992 per LQR instance), with the nominal tolerance tightened 100× to 1e-10, score:
   - exact pendulum 0.974 / −9.09
   - smoothed pendulum 0.972 / −8.84
   - LQR 0.879 / −8.88
   - aggregate +0.06 test, +0.16 train

   That is slightly **above** the reference, but below the paper's own IFT run with the same tighter solve (+0.35), which beats it on accurate fraction in exact pendulum and LQR.
   - Its derivatives genuinely are more accurate. What it gives up is compute (n_θ-proportional solves), and wall-clock time may not be scored.
   - Making it fail by scale would need either a time budget or enormous parameter counts. These OCPs are so small that even 992 extra QP solves per instance take minutes.
   - The hidden test only applies a 3-hour safety timeout to the predictor. This is left open and stated here.
2. **Smoothed sensitivities of the reproduced implementation are biased.**
   - The bias grows with `tau_min`: relative 1e-4 to 2e-3 at `tau_min = 1e-2`. It is identical for acados' forward and adjoint paths and unchanged by tolerance or clipping.
   - Finite differences of the reference's own smoothed solutions match the independent ground truth to about 1e-7, so the problem definition and the nominal solutions agree. The error is in acados' τ_min > 0 sensitivity step. I checked that acados combines the two sides of the path-constraint multipliers and seeds correctly, but did not locate the root cause.
   - Consequence: on this experiment, central FD at the paper's settings beats the reference (0.983 / −6.84 vs 0.811 / −5.41). This is the headroom a correct smoothed IFT can claim. Overall that FD still ranks below the reference (aggregate −0.07).
3. **Not scored:** the paper's speed-ups (Table 1/2, Fig. 3) and the Sec. 5.3 chain example (wall-clock only).

## Headroom check

| experiment | metrics at their bound for the reference | headroom shown |
|---|---|---|
| exact pendulum | `frac_sens_accurate` = 1.000 and `frac_u0_accurate` = 1.000 | `mean_log10_sens_rel_err` −7.77 vs floor −10; better variants reach −9.20 |
| smoothed pendulum | none | all three; FD of the same solutions reaches 0.983 / −6.84 |
| LQR adjoint | `frac_u0_accurate` = 1.000 | 0.971 → 1.000 and −8.79 → −9.97 with a tighter solve |

The two added experiments come from where the paper's method falls short: the smoothed map and tightly constrained many-parameter adjoints. The reference and the baselines were run on both. Simple baselines sit far below the reference on a scale that leaves room above it. Gauss–Newton, the paper's foil, is accurate on 1 of 193 exact instances ("completely off"). Gauss–Newton equals the exact Hessian on the convex LQR, where the constraint-blind baseline separates instead.

## Reference score before → after

- **Before:** `log10_sensitivity_advantage_vs_gn = 6.115`, `log10_error_regression_vs_exact = 0`, on one self-graded parameter value.
- **After** (hidden test):
  - exact pendulum 1.000 / −7.77 / 1.000
  - smoothed pendulum 0.811 / −5.41 / 0.989
  - LQR 0.971 / −8.79 / 1.000

  `scoring/scores_test.json` and `scoring/scores_train.json` come from the reference runs alone (proposed method plus its two baselines). `scoring/scores.json` is the train copy.

The final files were rescored with the final evaluator (`math.fsum` aggregation, so results are bit-identical across Python versions) from the reference predictions of job `30e92385-4ff`. The predictor code is unchanged since that job, and its two runs were byte-identical. The rescoring changed values only at the 1e-15 level.

## Weights

- **Exact-map experiment 0.5:** the paper's core claim (Sec. 5.1, Remark 3).
- **LQR adjoint 0.3:** Table 1's correctness statement ("adjoint sensitivities match"), and the paper's case for adjoints with many parameters.
- **Smoothed map 0.2:** a stated contribution that the paper shows only graphically.

Coefficients: `frac_sens_accurate` 1.0, `mean_log10_sens_rel_err` 0.5, `frac_u0_accurate` 0.5. The old timing experiments, which had weight 1e-6 and zero coefficients, were removed.

## Reproducing this report

- `bash scripts/run.sh` rebuilds the caches if they are missing and scores the reference on train and hidden test.
- `RUN_HARDENING_CHECKS=1 bash scripts/run.sh` additionally reruns every variant and shortcut.
- Per-instance records (`records_*.json`: relative sensitivity error and scaled u0 error per instance) allow rescoring without solvers. The scoring code is pure Python.
- Earlier passes are kept for the record:
  - `hardening/job3_adjoint_path/`: adjoint-path reference.
  - `hardening/first_pass/`: before the `mu0` fix.
