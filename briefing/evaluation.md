# Evaluation

## Protocol

A method is a predictor with one entry point:

```
bash scripts/predict.sh INSTANCES_JSON PREDICTIONS_JSON
```

- `INSTANCES_JSON` holds, per experiment, the full `problem` specification and a list of `instances`. These contain parameters, initial state, `tau_min` or `u_max` and `seed_u0`, plus the pendulum `initial_guess`. They never contain answers.
- The predictor writes

```json
{"methods": {"<method name>": {"<experiment>": {"<instance id>": {...}}}}}
```

- **Pendulum experiments:** each entry is `{"u0": float, "du0_dtheta": float}`.
- **LQR experiment:** each entry is `{"u0": [4 floats], "adjoint": [248 floats]}`.
- **Several methods:** a predictor may write several named methods (e.g. a proposal and its baselines). Every name is scored in every experiment.

`scripts/evaluate_train.sh` runs the predictor on the visible instances in `eval/train/` and writes `scoring/scores_train.json`. The hidden test `scripts/evaluate_test.sh` (no arguments) runs the same predictor on instances that only the hidden test holds. It writes `scoring/scores_test.json`. Both evaluators compute the ground truth independently of any method: IPOPT solve, Newton refinement of the KKT system to machine precision, an implicit-function-theorem derivative, and a finite-difference cross-check.

## Metrics (per experiment, per method)

For each instance:
- **Solution check:** `u0` is correct if its relative error, `|du0| / max(1, |u0_true|)` (max over components for the LQR), is `<= 1e-5`.
- **Sensitivity error:** relative error `|ds| / max(1, |s_true|)` (2-norm for the 248-vector adjoint).

| metric | direction | definition |
|---|---|---|
| `frac_sens_accurate` (primary) | higher | fraction of instances with a correct `u0` and sensitivity relative error `<= 1e-4` |
| `mean_log10_sens_rel_err` | lower | mean of `log10(relative error)` clipped to `[-10, 0]`; an instance with a wrong or missing solution counts as `0` |
| `frac_u0_accurate` (constraint) | higher | fraction of instances with a correct `u0` |

## Failure Rules

- Missing, malformed, boolean, string or non-finite entries make that instance count as failed (worst value).
- An experiment the method omits gets the worst value in every metric.
- A crashed, empty or timed-out predictor gets the worst value in every metric of every experiment.
- Only the raw `u0` and sensitivity values are read; any other field (self-reported errors, flags, scores) is ignored.
- Wall-clock time is not scored.

## Experiments and Weights

| experiment | weight | what it measures |
|---|---|---|
| `pendulum_sensitivity_accuracy` | 0.5 | exact solution-map sensitivity of the nonlinear constrained pendulum OCP |
| `pendulum_smoothed_sensitivity` | 0.2 | sensitivity of the barrier-smoothed solution map, `tau_min` in {1e-4, 1e-3, 1e-2} |
| `bounded_lqr_adjoint_accuracy` | 0.3 | adjoint sensitivity w.r.t. 248 parameters of a bounded LQR, `u_max` in {1, 1e4} |

Metric coefficients: `frac_sens_accurate` 1.0, `mean_log10_sens_rel_err` 0.5, `frac_u0_accurate` 0.5. Instances whose answer is a trivially zero sensitivity are excluded: pendulum `u0` at the force bound, and LQR with every `u0` component at its bound.
