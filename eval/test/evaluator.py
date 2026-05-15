#!/usr/bin/env python3
"""Held-out test-slice scorer for differentiable NMPC result artifacts.

The test slice reads the same method artifact as the visible train slice, but
scores derived consistency metrics instead of the direct development metrics.
When `scoring/scores_train.json` exists, its experiment/method keys define the
exact set of entries to score here.
"""

from __future__ import annotations

import argparse
import json
import math
import os

DEFAULT_INPUT = "/home/user/checkpoints/reproduction_results.json"
DEFAULT_OUTPUT = "/home/user/scoring/scores_test.json"
DEFAULT_TRAIN_SCORES = "/home/user/scoring/scores_train.json"
EPS = 1e-12
LQR_BATCH_SIZE = 128.0


TRAIN_METRICS_BY_EXPERIMENT = {
    "pendulum_sensitivity_accuracy": ["sensitivity_max_error"],
    "bounded_lqr_umax_high": ["solve_and_sens_time_ms"],
    "bounded_lqr_umax_low": ["solve_and_sens_time_ms"],
}


def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _experiment_results(scores: dict, experiment_name: str) -> dict:
    try:
        results = scores["experiments"][experiment_name]["results"]
    except KeyError as exc:
        raise ValueError(f"Missing experiment results: {experiment_name}") from exc
    if not isinstance(results, dict) or not results:
        raise ValueError(f"{experiment_name}/results must be a non-empty object")
    return results


def _metric(scores: dict, experiment_name: str, method_name: str, metric_name: str) -> float:
    results = _experiment_results(scores, experiment_name)
    try:
        value = results[method_name][metric_name]
    except KeyError as exc:
        raise ValueError(
            f"Missing metric {experiment_name}/{method_name}/{metric_name}"
        ) from exc
    if not isinstance(value, (int, float)):
        raise ValueError(f"{experiment_name}/{method_name}/{metric_name} must be numeric")
    return float(value)


def _nonnegative_metric(scores: dict, experiment_name: str, method_name: str, metric_name: str) -> float:
    value = _metric(scores, experiment_name, method_name, metric_name)
    if not math.isfinite(value) or value < 0.0:
        raise ValueError(
            f"{experiment_name}/{method_name}/{metric_name} must be a finite nonnegative value"
        )
    return value


def _validate_results(scores: dict) -> None:
    if not isinstance(scores.get("experiments"), dict):
        raise ValueError("Input must contain an 'experiments' object")

    for experiment_name, metric_names in TRAIN_METRICS_BY_EXPERIMENT.items():
        for method_name, method_scores in _experiment_results(scores, experiment_name).items():
            if not isinstance(method_scores, dict):
                raise ValueError(f"{experiment_name}/{method_name} must be a metric object")
            for metric_name in metric_names:
                _nonnegative_metric(scores, experiment_name, method_name, metric_name)


def _train_method_index(raw_scores: dict, train_scores_path: str) -> dict[str, list[str]]:
    """Return experiment -> method names to score on the held-out slice."""
    if os.path.exists(train_scores_path):
        train_scores = _load_json(train_scores_path)
    else:
        train_scores = raw_scores

    if not isinstance(train_scores.get("experiments"), dict):
        raise ValueError("Train scores must contain an 'experiments' object")

    method_index: dict[str, list[str]] = {}
    for experiment_name in TRAIN_METRICS_BY_EXPERIMENT:
        method_index[experiment_name] = sorted(_experiment_results(train_scores, experiment_name))
    return method_index


def _test_scores(scores: dict, method_index: dict[str, list[str]]) -> dict:
    """Compute derived consistency metrics for the held-out test slice."""
    output = {
        "experiments": {
            "pendulum_sensitivity_accuracy": {"results": {}},
            "bounded_lqr_umax_high": {"results": {}},
            "bounded_lqr_umax_low": {"results": {}},
        }
    }

    exact_err = _nonnegative_metric(
        scores,
        "pendulum_sensitivity_accuracy",
        "acados_exact_hessian",
        "sensitivity_max_error",
    )
    gn_err = _nonnegative_metric(
        scores,
        "pendulum_sensitivity_accuracy",
        "gauss_newton_approx",
        "sensitivity_max_error",
    )

    for method_name in method_index["pendulum_sensitivity_accuracy"]:
        err = _nonnegative_metric(
            scores,
            "pendulum_sensitivity_accuracy",
            method_name,
            "sensitivity_max_error",
        )
        output["experiments"]["pendulum_sensitivity_accuracy"]["results"][method_name] = {
            "log10_sensitivity_advantage_vs_gn": math.log10((gn_err + EPS) / (err + EPS)),
            "log10_gn_vs_exact_ratio": math.log10((exact_err + EPS) / (err + EPS)),
        }

    high_times = {}
    for method_name in method_index["bounded_lqr_umax_high"]:
        high_time = _nonnegative_metric(
            scores,
            "bounded_lqr_umax_high",
            method_name,
            "solve_and_sens_time_ms",
        )
        high_times[method_name] = high_time
        output["experiments"]["bounded_lqr_umax_high"]["results"][method_name] = {
            "per_problem_solve_and_sens_ms": high_time / LQR_BATCH_SIZE,
        }

    for method_name in method_index["bounded_lqr_umax_low"]:
        low_time = _nonnegative_metric(
            scores,
            "bounded_lqr_umax_low",
            method_name,
            "solve_and_sens_time_ms",
        )
        result = {
            "per_problem_solve_and_sens_ms": low_time / LQR_BATCH_SIZE,
        }
        if method_name in high_times:
            result["tight_to_loose_runtime_ratio"] = low_time / max(high_times[method_name], EPS)
        output["experiments"]["bounded_lqr_umax_low"]["results"][method_name] = result

    return output


def _assert_method_keys_match(train_index: dict[str, list[str]], test_scores: dict) -> None:
    for experiment_name, train_methods in train_index.items():
        test_methods = sorted(test_scores["experiments"][experiment_name]["results"])
        if test_methods != train_methods:
            raise ValueError(
                f"Method-key mismatch for {experiment_name}: "
                f"train={train_methods}, test={test_methods}"
            )


def evaluate_all(
    input_path: str = DEFAULT_INPUT,
    output_path: str = DEFAULT_OUTPUT,
    train_scores_path: str = DEFAULT_TRAIN_SCORES,
) -> dict:
    """Write the held-out split with consistency metrics from the same artifact."""
    if not os.path.exists(input_path):
        raise FileNotFoundError(
            f"Missing method results artifact: {input_path}. "
            "Run scripts/method.sh or provide --input."
        )

    raw_scores = _load_json(input_path)
    _validate_results(raw_scores)
    method_index = _train_method_index(raw_scores, train_scores_path)
    scores = _test_scores(raw_scores, method_index)
    _assert_method_keys_match(method_index, scores)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(scores, handle, indent=2)
    print(f"Test scores written to {output_path}")
    return scores


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=DEFAULT_INPUT, help="method results JSON")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="test scores JSON path")
    parser.add_argument(
        "--train-scores",
        default=DEFAULT_TRAIN_SCORES,
        help="train scores JSON whose experiment/method keys must be mirrored",
    )
    args = parser.parse_args()
    scores = evaluate_all(args.input, args.output, args.train_scores)
    print(json.dumps(scores, indent=2))


if __name__ == "__main__":
    main()
