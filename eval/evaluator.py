#!/usr/bin/env python3
"""Method-agnostic scorer for differentiable NMPC reproduction outputs."""

from __future__ import annotations

import argparse
import json
import math
import os

DEFAULT_INPUT = "/home/user/checkpoints/reproduction_results.json"
DEFAULT_OUTPUT = "/home/user/scoring/scores.json"


REQUIRED_METRICS = {
    ("pendulum_sensitivity_accuracy", "acados_exact_hessian"): ["sensitivity_max_error"],
    ("pendulum_sensitivity_accuracy", "gauss_newton_approx"): ["sensitivity_max_error"],
    ("bounded_lqr_umax_high", "acados"): ["solve_and_sens_time_ms"],
    ("bounded_lqr_umax_low", "acados"): ["solve_and_sens_time_ms"],
}


def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _validate_results(scores: dict) -> None:
    experiments = scores.get("experiments")
    if not isinstance(experiments, dict):
        raise ValueError("Input must contain an 'experiments' object")

    for (experiment_name, method_name), metric_names in REQUIRED_METRICS.items():
        experiment = experiments.get(experiment_name)
        if not isinstance(experiment, dict):
            raise ValueError(f"Missing experiment: {experiment_name}")
        results = experiment.get("results")
        if not isinstance(results, dict):
            raise ValueError(f"Missing results for experiment: {experiment_name}")
        metrics = results.get(method_name)
        if not isinstance(metrics, dict):
            raise ValueError(f"Missing method {method_name} in {experiment_name}")
        for metric_name in metric_names:
            value = metrics.get(metric_name)
            if not isinstance(value, (int, float)):
                raise ValueError(
                    f"Metric {experiment_name}/{method_name}/{metric_name} "
                    "must be numeric"
                )
            if not math.isfinite(float(value)) or float(value) < 0.0:
                raise ValueError(
                    f"Metric {experiment_name}/{method_name}/{metric_name} "
                    "must be finite and nonnegative"
                )


def write_scores_json(scores: dict, output_path: str = DEFAULT_OUTPUT) -> None:
    """Write `scoring/scores.json` in the expected structure."""
    _validate_results(scores)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(scores, handle, indent=2)
    print(f"Scores written to {output_path}")


def evaluate_all(input_path: str = DEFAULT_INPUT, output_path: str = DEFAULT_OUTPUT) -> dict:
    """Score a method-produced metrics artifact without importing method code."""
    if not os.path.exists(input_path):
        raise FileNotFoundError(
            f"Missing method results artifact: {input_path}. "
            "Run scripts/method.sh or provide --input."
        )
    scores = _load_json(input_path)
    write_scores_json(scores, output_path)
    return scores


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=DEFAULT_INPUT, help="method results JSON")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="scores JSON path")
    args = parser.parse_args()
    scores = evaluate_all(args.input, args.output)
    print(json.dumps(scores, indent=2))


if __name__ == "__main__":
    main()
