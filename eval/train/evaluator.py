#!/usr/bin/env python3
"""Visible train-slice scorer for differentiable NMPC result artifacts."""

from __future__ import annotations

import argparse
import json
import os

DEFAULT_INPUT = "/home/user/checkpoints/reproduction_results.json"
DEFAULT_OUTPUT = "/home/user/scoring/scores_train.json"


REQUIRED_METRICS = {
    ("pendulum_sensitivity_accuracy", "acados_exact_hessian"): ["sensitivity_max_error"],
    ("pendulum_sensitivity_accuracy", "gauss_newton_approx"): ["sensitivity_max_error"],
    ("bounded_lqr_umax_high", "acados"): ["solve_and_sens_time_ms"],
    ("bounded_lqr_umax_low", "acados"): ["solve_and_sens_time_ms"],
}


def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _metric(scores: dict, experiment_name: str, method_name: str, metric_name: str) -> float:
    try:
        value = scores["experiments"][experiment_name]["results"][method_name][metric_name]
    except KeyError as exc:
        raise ValueError(
            f"Missing metric {experiment_name}/{method_name}/{metric_name}"
        ) from exc
    if not isinstance(value, (int, float)):
        raise ValueError(f"{experiment_name}/{method_name}/{metric_name} must be numeric")
    return float(value)


def _validate_results(scores: dict) -> None:
    if not isinstance(scores.get("experiments"), dict):
        raise ValueError("Input must contain an 'experiments' object")

    for (experiment_name, method_name), metric_names in REQUIRED_METRICS.items():
        for metric_name in metric_names:
            _metric(scores, experiment_name, method_name, metric_name)


def evaluate_all(input_path: str = DEFAULT_INPUT, output_path: str = DEFAULT_OUTPUT) -> dict:
    """Write the train split using the paper-visible benchmark metrics."""
    if not os.path.exists(input_path):
        raise FileNotFoundError(
            f"Missing method results artifact: {input_path}. "
            "Run scripts/method.sh or provide --input."
        )

    scores = _load_json(input_path)
    _validate_results(scores)
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
