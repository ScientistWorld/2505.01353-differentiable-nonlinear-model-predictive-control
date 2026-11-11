#!/bin/bash
# Standard evaluation entry point: scores the method on the visible train
# instances and writes scoring/scores.json (same metrics as the split files).

set -euo pipefail

cd /home/user
bash /home/user/scripts/repair_vendor_runtime.sh >/dev/null
source /home/user/scripts/_runtime_env.sh
mkdir -p scoring

python3 /home/user/eval/train/evaluator.py --output /home/user/scoring/scores.json
echo "Results written to scoring/scores.json"
