# Design Notes — Train/Test Evaluation Split

## Split Style: Metric Triangulation

**Design choice:** Same-data, different-metric triangulation (not data partition).

This paper has three experiments with two methods across them. The evaluation is lightweight (no inference needed — all metrics are computed from existing reproduction results). Data-partition splitting would leave each slice underpowered with fewer than 3 experiments each. Instead, the split uses the **same underlying results artifact** but exposes different metrics in each slice, giving future agents multiple angles to probe the same scientific claim without requiring re-execution.

## Train Slice (`eval/train/`)

**Exposes:** Paper's primary metrics directly.
- `pendulum_sensitivity_accuracy` → `sensitivity_max_error`
- `bounded_lqr_umax_high` → `solve_and_sens_time_ms`
- `bounded_lqr_umax_low` → `solve_and_sens_time_ms`

Future agents optimize against these. The primary metrics are the direct scientific quantities from the paper.

## Test Slice (`eval/test/`)

**Exposes:** Derived composite metrics that verify consistency and robustness.
- `pendulum_sensitivity_accuracy` → `log10_sensitivity_advantage_vs_gn` (and `log10_gn_vs_exact_ratio`)
- `bounded_lqr_umax_high` → `per_problem_solve_and_sens_ms`
- `bounded_lqr_umax_low` → `per_problem_solve_and_sens_ms`, `tight_to_loose_runtime_ratio`

These metrics measure the **same underlying claims** (sensitivity accuracy matters, solving with sensitivities should be fast) but from angles that are harder to game:
- The log-ratio metrics capture the relative ordering between the exact-Hessian method and the Gauss-Newton baseline without exposing absolute error thresholds.
- Per-problem timing normalizes by batch size to catch inconsistent reporting.
- Tight-to-loose ratio verifies efficiency generalizes across control bounds.

## Improvements Applied

1. **Added `log10_gn_vs_exact_ratio` metric** — a comparative metric for the baseline method side. Previously, the test slice only had a comparative metric for `acados_exact_hessian`. Adding this metric gives the baseline method its own comparative signal in the test slice, balancing the triangulation.

2. **Deleted `scores_train.json` and `scores_test.json`** — these should be produced by the runner iteration, not committed as stubs. The score files were removed to avoid misleading the validator and runner.

## Script Wiring

- `scripts/evaluate_train.sh` invokes `eval/train/` and writes `scores_train.json`
- `scripts/evaluate_test.sh` invokes `eval/test/` and writes `scores_test.json`
- No hardcoded method names — both scripts discover methods from disk
- Both scripts are syntax-checked (`bash -n`) and pass structural validation

## No Leakage

- `eval/train/` and `eval/test/` are completely independent with no cross-imports
- Both use the same input artifact (`checkpoints/reproduction_results.json`) which is appropriate — the method has been run, we're just re-scoring it differently
- Top-level `eval/evaluator.py` is unchanged; train/test slices are self-contained

## Runtime Notes

Both slices are CPU-only and complete in milliseconds. No GPU needed. No re-execution of the method required — both evaluators read the pre-existing `checkpoints/reproduction_results.json` and compute metrics from it.

## First Compute Run Results

Official split-evaluation job `86bcd69e-e2a` finished successfully on 2026-04-23 with exit code 0.

- Train slice:
  - `pendulum_sensitivity_accuracy`
    - `acados_exact_hessian.sensitivity_max_error = 0.0025974539321929058`
    - `gauss_newton_approx.sensitivity_max_error = 2.2001354962645028`
  - `bounded_lqr_umax_high`
    - `acados.solve_and_sens_time_ms = 28.452532133087516`
  - `bounded_lqr_umax_low`
    - `acados.solve_and_sens_time_ms = 34.35777616687119`
- Test slice:
  - `pendulum_sensitivity_accuracy`
    - `acados_exact_hessian.log10_sensitivity_advantage_vs_gn = 2.9279015739291876`
    - `gauss_newton_approx.log10_gn_vs_exact_ratio = -2.9279015739291876`
  - `bounded_lqr_umax_high`
    - `acados.per_problem_solve_and_sens_ms = 0.22228540728974622`
  - `bounded_lqr_umax_low`
    - `acados.per_problem_solve_and_sens_ms = 0.2684201263036812`
    - `acados.tight_to_loose_runtime_ratio = 1.2075472230788364`

No warnings or stderr errors were emitted by the job.

## Remaining Caveat

The held-out timing metrics are valid scientific quantities, but `per_problem_solve_and_sens_ms` is a normalization of the visible train timing metric rather than an independent runtime measurement. The split therefore gets most of its anti-shortcut signal on the timing side from `tight_to_loose_runtime_ratio`, while the pendulum side has the stronger hidden comparative signal.

## Metric Coverage vs reference.json

| Experiment | Primary Metric | Secondary Metrics | Train/Test Coverage |
|------------|----------------|-------------------|---------------------|
| pendulum_sensitivity_accuracy | sensitivity_max_error | log10_sensitivity_advantage_vs_gn, log10_gn_vs_exact_ratio | Train=primary, Test=derived |
| bounded_lqr_umax_high | solve_and_sens_time_ms | per_problem_solve_and_sens_ms | Train=primary, Test=derived |
| bounded_lqr_umax_low | solve_and_sens_time_ms | per_problem_solve_and_sens_ms, tight_to_loose_runtime_ratio | Train=primary, Test=derived |

## Anti-Shortcut Signal

A shortcut agent might tune the acados exact-Hessian method to minimize `sensitivity_max_error` on the pendulum, or reduce `solve_and_sens_time_ms` on the LQR problems. These shortcuts would:
- Show improvement on train slice metrics
- But NOT show consistent improvement on the derived test metrics (the log-ratios, per-problem timing, and cross-bound ratio)

The gap between train and test scores distinguishes genuine improvement from metric-gaming.
