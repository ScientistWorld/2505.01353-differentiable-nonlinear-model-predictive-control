# Scientist Constraints

## What is fixed (by `eval/`, not by the method)

- Problem definitions: every instance file carries the full `problem` block, and predictions must solve exactly that problem. This covers the pendulum OCP with RK4 discretisation, cost scaling `dt` and the path constraint on stages 1..N-1, and the bounded LQR with its column-major parameter layout.
- The instances, their number, the ground truth, the accuracy thresholds (`1e-5` for `u0`, `1e-4` for sensitivities), the log-error clip `[-10, 0]`, and the exclusion of trivially-zero-sensitivity instances.
- The target branch of the multimodal pendulum OCP: the locally optimal solution reached from the instance's `initial_guess` (solution at `theta -/+ 1e-3` on the same branch).
- `tau_min` of each smoothed instance. A method must differentiate the smoothed problem it was given, not substitute a different smoothing level or an unsmoothed solution.

## What a method may change

- Anything inside the predictor: nominal solver, Hessian treatment, globalisation, tolerances, linear algebra, refinement steps, forward vs. adjoint evaluation, or a completely different algorithm. All methods are scored through `scripts/predict.sh`.
- A predictor may emit several named methods. Each is scored in every experiment. An experiment a method omits gets the worst value there.

## Fair-comparison rules

- Do not read anything under `eval/` from the predictor, and do not rely on the hidden test's instances. Train answers (`eval/train/cache/`) are for development only.
- Report the raw `u0` and sensitivity values only. Other fields are ignored, and any non-finite or malformed value counts as a failed instance.
- Wall-clock time is not scored. The hidden test only bounds the predictor's run time with a generous safety timeout (3 hours).

## Output contract

`bash scripts/predict.sh INSTANCES_JSON PREDICTIONS_JSON` writes `{"methods": {name: {experiment: {instance_id: {"u0": ..., "du0_dtheta" | "adjoint": ...}}}}}`. `scripts/evaluate_train.sh` and `scripts/evaluate_test.sh` take no arguments and score every method in the predictions.
