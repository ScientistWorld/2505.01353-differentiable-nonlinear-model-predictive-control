# Evaluation

## Protocol

A method is a predictor with one entry point:

```
bash scripts/predict.sh INSTANCES_JSON PREDICTIONS_JSON
```

- The evaluator calls the predictor **once per experiment**. Each `INSTANCES_JSON` holds one experiment: its full `problem` specification and a list of `instances`. These contain parameters, initial state, `tau_min` or `u_max` and `seed_u0`, plus the pendulum `initial_guess`. They never contain answers.
- The predictor writes

```json
{"methods": {"<method name>": {"<experiment>": {"<instance id>": {...}}}}}
```

- **Pendulum experiments:** each entry is `{"u0": float, "du0_dtheta": float}`.
- **LQR experiments:** each entry is `{"u0": [nu floats], "adjoint": [n_theta floats]}` (`nu = 4, n_theta = 248` or `nu = 8, n_theta = 976`).
- **Several methods:** a predictor may write several named methods (e.g. a proposal and its baselines). Every name seen in any call is scored in every experiment. Only the entries of the experiment a call was given are read from that call.

`scripts/evaluate_train.sh` runs the predictor on the visible instances in `eval/train/` and writes `scoring/scores_train.json`. The hidden test `scripts/evaluate_test.sh` (no arguments) runs the same predictor on instances that only the hidden test holds. It writes `scoring/scores_test.json`. Both evaluators compute the ground truth independently of any method: IPOPT solve, Newton refinement of the KKT system to machine precision, an implicit-function-theorem derivative, and a finite-difference cross-check.

## Compute budget

Each predictor call may use at most

```
150 + n_instances * c   CPU seconds,   c = 1.0 (pendulum experiments), 0.3 (248-parameter LQR), 0.15 (976-parameter LQR)
```

measured over the predictor's whole process tree: threads, child processes and detached descendants all count (orphans are re-parented to the evaluator). A call that exceeds it is killed and the run fails. CPU time, not wall-clock time, is counted, and wall-clock time is never scored. A wall-clock safety stop at four times the budget plus 10 minutes only catches hung predictors.

For scale, the reference predictor (proposed method plus two baselines) used 17–21 CPU s per pendulum call, 7 CPU s on the 248-parameter LQR and 51 CPU s on the 976-parameter LQR, about 45 s of which is acados code generation. Budgets on the hidden test are 300–343, 192 and 219 s. The budget fits one solution, one factorization and one backsolve per instance with a wide margin. One or more extra solves per parameter, as in finite differences, do not fit on the 976-parameter LQR: about 1.8 CPU s per instance for central differences.

## Metrics (per experiment, per method)

For each instance:
- **Solution check:** `u0` is correct if its relative error, `|du0| / max(1, |u0_true|)` (max over components for the LQR), is `<= 1e-5`.
- **Sensitivity error:** relative error `|ds| / max(1, |s_true|)` (2-norm for the adjoint vector).

| metric | direction | definition |
|---|---|---|
| `frac_sens_accurate` (primary) | higher | fraction of instances with a correct `u0` and sensitivity relative error `<= 1e-4` |
| `mean_log10_sens_rel_err` | lower | mean of `log10(relative error)` clipped to `[-10, 0]`; an instance with a wrong or missing solution counts as `0` |
| `frac_u0_accurate` (constraint) | higher | fraction of instances with a correct `u0` |

## Failure Rules

- Missing, malformed, boolean, string or non-finite entries make that instance count as failed (worst value).
- An experiment the method omits gets the worst value in every metric.
- A crashed, empty, timed-out or over-budget predictor call fails the run: every method gets the worst value in every metric of every experiment.
- Only the raw `u0` and sensitivity values are read; any other field (self-reported errors, flags, scores) is ignored.

## Experiments and Weights

| experiment | weight | what it measures |
|---|---|---|
| `pendulum_sensitivity_accuracy` | 0.35 | exact solution-map sensitivity of the nonlinear constrained pendulum OCP |
| `pendulum_smoothed_sensitivity` | 0.15 | sensitivity of the barrier-smoothed solution map, `tau_min` in {1e-4, 1e-3, 1e-2} |
| `pendulum_near_active_set_change` | 0.15 | exact-map sensitivity at parameters close to a constraint switch (smallest strict-complementarity margin 1e-6 to 1e-3) |
| `bounded_lqr_adjoint_accuracy` | 0.15 | adjoint sensitivity w.r.t. 248 parameters of a bounded LQR, `u_max` in {1, 1e4} |
| `bounded_lqr_large_adjoint` | 0.20 | the same at `nx = 16, nu = 8`: adjoint w.r.t. 976 parameters |

Metric coefficients: `frac_sens_accurate` 1.0, `mean_log10_sens_rel_err` 0.5, `frac_u0_accurate` 0.5. Instances whose answer is a trivially zero sensitivity are excluded: pendulum `u0` at the force bound, and LQR with every `u0` component at its bound.
