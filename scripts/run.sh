#!/bin/bash
# End-to-end job (CPU only): build the ground-truth caches if missing, run the
# reference predictor through the visible train and the hidden test
# evaluators, and (optionally) the hardening audit of variants and shortcuts.

set -euo pipefail

cd /home/user
RUN_HARDENING_CHECKS="${RUN_HARDENING_CHECKS:-0}"  # 1: also rerun the hardening audit

echo "========================================"
echo "DIFFERENTIABLE NMPC SOLUTION-SENSITIVITY GYM"
echo "========================================"

bash /home/user/scripts/repair_vendor_runtime.sh
source /home/user/scripts/_runtime_env.sh
mkdir -p /home/user/hardening/results

if [ "${RUN_HARDENING_CHECKS}" = "1" ] && [ ! -f /home/user/hardening/results/smoke_predictions.json ]; then
    echo ">>> Predictor smoke test (tiny instance file, no answers needed)"
    python3 /home/user/hardening/smoke_instances.py /home/user/hardening/results/smoke_instances.json
    bash /home/user/scripts/predict.sh /home/user/hardening/results/smoke_instances.json \
        /home/user/hardening/results/smoke_predictions.json 2>&1 | tee /home/user/hardening/results/smoke_predict.log || true
fi

echo ">>> Train ground truth (independent IPOPT + Newton + IFT; cached after first build)"
python3 /home/user/eval/train/evaluator.py --build-cache-only 2>&1 | tee -a /home/user/hardening/results/groundtruth_train.log

echo ">>> Reference method on the visible train slice"
bash /home/user/scripts/evaluate_train.sh
cp /home/user/scoring/scores_train.json /home/user/scoring/scores.json

echo ">>> Hidden-test ground truth (eval/test only; cached after first build)"
python3 /home/user/eval/test/evaluator.py --build-cache-only 2>&1 | tee -a /home/user/hardening/results/groundtruth_test.log

echo ">>> Reference method on the hidden test slice"
bash /home/user/scripts/evaluate_test.sh

if [ "${RUN_HARDENING_CHECKS}" = "1" ]; then
    echo ">>> Hardening audit: variants and shortcuts through the same evaluators"
    python3 /home/user/hardening/run_checks.py 2>&1 | tee /home/user/hardening/results/run_checks.log
fi

echo "========================================"
echo "JOB COMPLETE: scoring/scores_train.json, scoring/scores_test.json"
echo "========================================"
