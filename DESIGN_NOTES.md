# Design Notes - Train/Test Evaluation Split

## What I Checked

- Read `scripts/evaluate_train.sh` and `scripts/evaluate_test.sh` side by side. Train invokes `eval/train/` and writes `scoring/scores_train.json`; test invokes `eval/test/` and writes `scoring/scores_test.json`.
- Read both split evaluators. They score the method-produced artifact at `checkpoints/reproduction_results.json` and do not import from `method/`.
- Grepped for hardcoded method defaults, train/test cross-imports, paper-agreement metric names, stale `log10_gn_vs_exact_ratio`, and score stubs.
- Confirmed `scoring/scores_train.json` and `scoring/scores_test.json` do not exist.
- Ran `bash -n scripts/evaluate_train.sh` and `bash -n scripts/evaluate_test.sh`.

## Changes Made

- Fixed a held-out pendulum metric direction bug in `eval/test/evaluator.py`.
  The old `log10_gn_vs_exact_ratio` description said it measured `GN error / exact error`, but the implementation emitted `exact error / method error`. I replaced it with `log10_error_regression_vs_exact`, computed as `method error / exact-Hessian error` with `higher_is_better: false`.
- Strengthened the pendulum anti-shortcut signal by keeping two complementary hidden ratios:
  `log10_sensitivity_advantage_vs_gn` rewards preserving the advantage over the Gauss-Newton shortcut, while `log10_error_regression_vs_exact` penalizes regressions away from the exact-Hessian method.
- Cleaned `scoring/reference.json` so every active metric has `higher_is_better`, `coefficient`, and `description`.
- Removed active metric definitions for `speedup_vs_mpc_pytorch` and `speedup_vs_cvxpygen` because the train/test evaluators do not compute those keys. The paper-reported result fields remain under `results.<method_name>` for context, but they are no longer scored split metrics.
- Updated coefficients for the two pendulum held-out ratio metrics to equal magnitude with opposite directions.

## Current Split Design

- Train slice exposes direct visible quantities:
  `sensitivity_max_error` for pendulum and `solve_and_sens_time_ms` for the two bounded-LQR settings.
- Test slice rescales or compares those quantities from hidden angles:
  pendulum relative advantage over Gauss-Newton, pendulum regression relative to exact Hessian, per-problem LQR timing, and tight-bound versus loose-bound timing ratio.
- The split remains method-agnostic: it enumerates method keys from the artifact or from existing train scores rather than hardcoding a future method name.

## Runtime Concerns For The Next Iteration

- The LQR metrics are still wall-clock timing metrics because the current method artifact does not expose a machine-independent proxy such as FLOPs, QP iteration counts, generated-code operation counts, or factorization counts. This is the main residual weakness: the runner should watch for hardware noise or future methods that improve timing by changing reporting rather than algorithmic work.
- `per_problem_solve_and_sens_ms` is a deterministic normalization of the visible batch total. It mainly catches inconsistent batch reporting; the stronger hidden timing signal is `tight_to_loose_runtime_ratio`.
- The pendulum held-out ratios are derived from the same two sensitivity errors as the visible metric. They sharpen comparative-ordering checks but do not create a new OOD pendulum sample. A future design pass could improve this further if the method artifact is extended to include additional theta points or finite-difference checks.
