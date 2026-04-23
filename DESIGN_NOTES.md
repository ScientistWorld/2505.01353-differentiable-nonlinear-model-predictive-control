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
