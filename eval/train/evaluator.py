#!/usr/bin/env python3
"""Visible train-slice scorer for differentiable NMPC result artifacts.

This slice exposes the direct benchmark quantities future agents are expected
to optimize during development. It is method-agnostic: every method entry found
under the supported experiments in the method artifact is scored, rather than a
fixed reproduced-method name.
"""

from __future__ import annotations

import argparse
import json
import math
import os

DEFAULT_INPUT = "/home/user/checkpoints/reproduction_results.json"
DEFAULT_OUTPUT = "/home/user/scoring/scores_train.json"


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


def _metric(method_scores: dict, experiment_name: str, method_name: str, metric_name: str) -> float:
    try:
        value = method_scores[metric_name]
    except KeyError as exc:
        raise ValueError(
            f"Missing metric {experiment_name}/{method_name}/{metric_name}"
        ) from exc
    if not isinstance(value, (int, float)):
        raise ValueError(f"{experiment_name}/{method_name}/{metric_name} must be numeric")
    value = float(value)
    if not math.isfinite(value) or value < 0.0:
        raise ValueError(
            f"{experiment_name}/{method_name}/{metric_name} must be finite and nonnegative"
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
                _metric(method_scores, experiment_name, method_name, metric_name)


def _train_scores(scores: dict) -> dict:
    """Return only the visible primary metrics for the train slice."""
    output = {"experiments": {}}
    for experiment_name, metric_names in TRAIN_METRICS_BY_EXPERIMENT.items():
        experiment = output["experiments"].setdefault(experiment_name, {"results": {}})
        for method_name in sorted(_experiment_results(scores, experiment_name)):
            method_scores = scores["experiments"][experiment_name]["results"][method_name]
            result = experiment["results"].setdefault(method_name, {})
            for metric_name in metric_names:
                result[metric_name] = _metric(
                    method_scores,
                    experiment_name,
                    method_name,
                    metric_name,
                )
    return output


def evaluate_all(input_path: str = DEFAULT_INPUT, output_path: str = DEFAULT_OUTPUT) -> dict:
    """Write the train split using only the paper-visible benchmark metrics."""
    if not os.path.exists(input_path):
        raise FileNotFoundError(
            f"Missing method results artifact: {input_path}. "
            "Run scripts/method.sh or provide --input."
        )

    raw_scores = _load_json(input_path)
    _validate_results(raw_scores)
    scores = _train_scores(raw_scores)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(scores, handle, indent=2)
    print(f"Train scores written to {output_path}")
    return scores


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=DEFAULT_INPUT, help="method results JSON")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="train scores JSON path")
    args = parser.parse_args()
    scores = evaluate_all(args.input, args.output)
    print(json.dumps(scores, indent=2))


if __name__ == "__main__":
    main()
