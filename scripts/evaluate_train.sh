#!/bin/bash
# Visible train evaluation. No arguments.
#
# Same protocol as the hidden test on the public instances of eval/train/:
# runs scripts/predict.sh, recomputes every metric from raw predictions, and
# writes scoring/scores_train.json for every method found in the predictions.

set -euo pipefail

cd /home/user
bash /home/user/scripts/repair_vendor_runtime.sh >/dev/null
source /home/user/scripts/_runtime_env.sh
mkdir -p scoring

echo "=== Evaluating train slice ==="
python3 /home/user/eval/train/evaluator.py
echo "=== Train evaluation complete: scoring/scores_train.json ==="
