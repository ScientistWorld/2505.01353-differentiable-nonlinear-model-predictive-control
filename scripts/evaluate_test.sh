#!/bin/bash
# Hidden test evaluation. No arguments.
#
# Runs the method's predictor (scripts/predict.sh) on instances that only
# eval/test/ holds, recomputes every metric from the raw predictions against an
# independent high-precision ground truth, and writes scoring/scores_test.json
# for every method found in the predictions.

set -euo pipefail

cd /home/user
bash /home/user/scripts/repair_vendor_runtime.sh >/dev/null
source /home/user/scripts/_runtime_env.sh
mkdir -p scoring

echo "=== Evaluating held-out test slice ==="
python3 /home/user/eval/test/evaluator.py
echo "=== Test evaluation complete: scoring/scores_test.json ==="
