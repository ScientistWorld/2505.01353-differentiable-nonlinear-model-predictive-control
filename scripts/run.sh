#!/bin/bash
# CPU-only end-to-end job: regenerate the method artifact, then score it.

set -euo pipefail

cd /home/user

echo "========================================"
echo "ACADOS DIFFERENTIABLE MPC - SPLIT EVALUATION"
echo "========================================"

echo ""
echo ">>> Regenerating method artifact..."
bash /home/user/scripts/method.sh

echo ""
echo ">>> Checking regenerated core-claim artifact..."
python3 - <<'PY'
import json
import math
from pathlib import Path

artifact = Path("/home/user/checkpoints/reproduction_results.json")
scores = json.loads(artifact.read_text())
pendulum = scores["experiments"]["pendulum_sensitivity_accuracy"]["results"]
exact = float(pendulum["acados_exact_hessian"]["sensitivity_max_error"])
gn = float(pendulum["gauss_newton_approx"]["sensitivity_max_error"])

if not (math.isfinite(exact) and math.isfinite(gn)):
    raise SystemExit(f"Non-finite pendulum sensitivity metrics: exact={exact}, gn={gn}")
if exact < 0.0 or gn < 0.0:
    raise SystemExit(f"Negative pendulum sensitivity metrics: exact={exact}, gn={gn}")
if exact >= gn:
    raise SystemExit(
        "Core claim not supported: exact-Hessian sensitivity error is not "
        f"smaller than Gauss-Newton (exact={exact}, gn={gn})"
    )
if exact > 0.1:
    raise SystemExit(
        "Core claim not supported: exact-Hessian sensitivity error is too large "
        f"for the Section 5.1 reproduction (exact={exact})"
    )

print(f"core_claim_artifact_valid=true exact_error={exact:.6g} gn_error={gn:.6g}")
PY

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
echo ">>> Checking scored metrics are machine-independent..."
python3 - <<'PY'
import json
from pathlib import Path

reference = json.loads(Path("/home/user/scoring/reference.json").read_text())
for experiment_name, experiment in reference.get("experiments", {}).items():
    experiment_weight = float(experiment.get("weight", 0.0))
    for metric_name, metric in experiment.get("metrics", {}).items():
        coefficient = abs(float(metric.get("coefficient", 0.0)))
        lowered = metric_name.lower()
        if experiment_weight and coefficient and any(token in lowered for token in ("time", "speed", "runtime", "throughput")):
            raise SystemExit(
                f"Wall-clock metric still contributes to scoring: "
                f"{experiment_name}/{metric_name}"
            )
print("machine_independent_scoring_check=true")
PY

echo ""
echo "========================================"
echo "JOB COMPLETE"
echo "Results in scoring/scores_train.json and scoring/scores_test.json"
echo "========================================"
