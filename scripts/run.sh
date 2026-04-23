#!/bin/bash
# CPU-only split-evaluation job for the frozen reproduction artifact.

set -euo pipefail

cd /home/user

echo "========================================"
echo "ACADOS DIFFERENTIABLE MPC - SPLIT EVAL"
echo "========================================"

if [ ! -f /home/user/checkpoints/reproduction_results.json ]; then
    echo "ERROR: missing /home/user/checkpoints/reproduction_results.json"
    exit 1
fi

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

print("split_outputs_validated=true")
PY

echo ""
echo "========================================"
echo "JOB COMPLETE"
echo "Results in scoring/scores_train.json and scoring/scores_test.json"
echo "========================================"
