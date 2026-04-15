#!/usr/bin/env python3
"""Held-out test-slice scorer for differentiable NMPC result artifacts."""

from __future__ import annotations

import argparse
import json
import math
import os

DEFAULT_INPUT = "/home/user/checkpoints/reproduction_results.json"
DEFAULT_OUTPUT = "/home/user/scoring/scores_test.json"
EPS = 1e-12
LQR_BATCH_SIZE = 128.0


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


def _test_scores(scores: dict) -> dict:
    exact_err = _metric(
        scores,
        "pendulum_sensitivity_accuracy",
        "acados_exact_hessian",
        "sensitivity_max_error",
    )
    gn_err = _metric(
        scores,
        "pendulum_sensitivity_accuracy",
        "gauss_newton_approx",
        "sensitivity_max_error",
    )
    high_time = _metric(
        scores,
        "bounded_lqr_umax_high",
        "acados",
        "solve_and_sens_time_ms",
    )
    low_time = _metric(
        scores,
        "bounded_lqr_umax_low",
        "acados",
        "solve_and_sens_time_ms",
    )

    log10_advantage = math.log10((gn_err + EPS) / (exact_err + EPS))
    tight_to_loose_ratio = low_time / max(high_time, EPS)

    return {
        "experiments": {
            "pendulum_sensitivity_accuracy": {
                "results": {
                    "acados_exact_hessian": {
                        "sensitivity_max_error": exact_err,
                        "log10_sensitivity_advantage_vs_gn": log10_advantage,
                    },
                    "gauss_newton_approx": {
                        "sensitivity_max_error": gn_err,
                    },
                }
            },
            "bounded_lqr_umax_high": {
                "results": {
                    "acados": {
                        "solve_and_sens_time_ms": high_time,
                        "per_problem_solve_and_sens_ms": high_time / LQR_BATCH_SIZE,
                    }
                }
            },
            "bounded_lqr_umax_low": {
                "results": {
                    "acados": {
                        "solve_and_sens_time_ms": low_time,
                        "per_problem_solve_and_sens_ms": low_time / LQR_BATCH_SIZE,
                        "tight_to_loose_runtime_ratio": tight_to_loose_ratio,
                    }
                }
            },
        }
    }


def evaluate_all(input_path: str = DEFAULT_INPUT, output_path: str = DEFAULT_OUTPUT) -> dict:
    """Write the held-out split with consistency metrics from the same artifact."""
    if not os.path.exists(input_path):
        raise FileNotFoundError(
            f"Missing method results artifact: {input_path}. "
            "Run scripts/method.sh or provide --input."
        )

    raw_scores = _load_json(input_path)
    _validate_results(raw_scores)
    scores = _test_scores(raw_scores)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(scores, handle, indent=2)
    print(f"Test scores written to {output_path}")
    return scores


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=DEFAULT_INPUT, help="method results JSON")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="test scores JSON path")
    args = parser.parse_args()
    scores = evaluate_all(args.input, args.output)
    print(json.dumps(scores, indent=2))


if __name__ == "__main__":
    main()
