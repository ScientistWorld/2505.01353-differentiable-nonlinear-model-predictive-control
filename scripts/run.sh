#!/bin/bash
# CPU-only end-to-end reproduction and split-evaluation job.

set -euo pipefail

cd /home/user

echo "========================================"
echo "ACADOS DIFFERENTIABLE MPC - REPRODUCTION"
echo "========================================"

if [ ! -f /home/user/method/acados/lib/libacados.so ]; then
    echo ""
    echo ">>> acados library missing; building from local source..."
    bash /home/user/scripts/build_acados.sh
fi

echo ""
echo ">>> Running method to regenerate reproduction artifact..."
bash /home/user/scripts/method.sh

echo ""
echo ">>> Running visible train-slice evaluation..."
bash /home/user/scripts/evaluate_train.sh

echo ""
echo ">>> Running held-out test-slice evaluation..."
bash /home/user/scripts/evaluate_test.sh

echo ""
echo ">>> Validating split outputs..."
python3 - <<'PY'
import json
from pathlib import Path

train_path = Path("/home/user/scoring/scores_train.json")
test_path = Path("/home/user/scoring/scores_test.json")

train = json.loads(train_path.read_text())
test = json.loads(test_path.read_text())

train_experiments = set(train.get("experiments", {}))
test_experiments = set(test.get("experiments", {}))
if train_experiments != test_experiments:
    raise SystemExit(
        f"Experiment mismatch: train={sorted(train_experiments)} "
        f"test={sorted(test_experiments)}"
    )

for experiment_name in sorted(train_experiments):
    train_methods = set(train["experiments"][experiment_name].get("results", {}))
    test_methods = set(test["experiments"][experiment_name].get("results", {}))
    if train_methods != test_methods:
        raise SystemExit(
            f"Method mismatch for {experiment_name}: "
            f"train={sorted(train_methods)} test={sorted(test_methods)}"
        )
    if not train_methods:
        raise SystemExit(f"No methods scored for {experiment_name}")

    for method_name in sorted(train_methods):
        train_metrics = train["experiments"][experiment_name]["results"][method_name]
        test_metrics = test["experiments"][experiment_name]["results"][method_name]

        if not train_metrics or not test_metrics:
            raise SystemExit(
                f"Empty metric payload for {experiment_name}/{method_name}: "
                f"train={train_metrics} test={test_metrics}"
            )

        for split_name, split_metrics in (("train", train_metrics), ("test", test_metrics)):
            for metric_name, metric_value in split_metrics.items():
                if metric_value is None:
                    raise SystemExit(
                        f"Null metric in {split_name}: "
                        f"{experiment_name}/{method_name}/{metric_name}"
                    )
                if not isinstance(metric_value, (int, float)):
                    raise SystemExit(
                        f"Non-numeric metric in {split_name}: "
                        f"{experiment_name}/{method_name}/{metric_name}={metric_value!r}"
                    )

        leaked_metrics = set(train_metrics) & set(test_metrics)
        if leaked_metrics:
            raise SystemExit(
                f"Metric leakage between train and test for {experiment_name}/{method_name}: "
                f"{sorted(leaked_metrics)}"
            )

if train_path.read_text() == test_path.read_text():
    raise SystemExit("Train/test score files are byte-identical")

print("split_outputs_validated=true")
print(f"train_experiments={sorted(train_experiments)}")
print(f"test_experiments={sorted(test_experiments)}")
PY

echo ""
echo "========================================"
echo "JOB COMPLETE"
echo "Results in scoring/scores_train.json and scoring/scores_test.json"
echo "========================================"
