#!/bin/bash
# End-to-end job (CPU only): build the ground-truth caches if missing, make
# sure acados carries the sign fix, run the reference predictor through the
# visible train and the hidden test evaluators, and (optionally) the hardening
# audit of variants and shortcuts.
#
#   bash scripts/run.sh                          # reference end to end
#   RUN_HARDENING_CHECKS=1 bash scripts/run.sh   # + smoke test, unpatched-acados
#                                                #   reference, variants, shortcuts

set -euo pipefail

cd /home/user
RUN_HARDENING_CHECKS="${RUN_HARDENING_CHECKS:-0}"  # 1: also smoke test, unpatched-acados reference, variants, shortcuts
R=/home/user/hardening/results

echo "========================================"
echo "DIFFERENTIABLE NMPC SOLUTION-SENSITIVITY GYM"
echo "========================================"

bash /home/user/scripts/repair_vendor_runtime.sh
source /home/user/scripts/_runtime_env.sh
mkdir -p "${R}"

if [ "${RUN_HARDENING_CHECKS}" = "1" ] && [ ! -f "${R}/smoke_ok" ]; then
    echo ">>> Predictor smoke test on every experiment (tiny instance file, no answers needed)"
    python3 /home/user/hardening/smoke_instances.py "${R}/smoke_instances.json"
    bash /home/user/scripts/predict.sh "${R}/smoke_instances.json" "${R}/smoke_predictions.json" > "${R}/smoke_predict.log" 2>&1 \
        || { tail -n 60 "${R}/smoke_predict.log"; exit 1; }
    python3 /home/user/hardening/smoke_instances.py --check "${R}/smoke_instances.json" "${R}/smoke_predictions.json"
    touch "${R}/smoke_ok"
fi

echo ">>> Ground truth (independent IPOPT + Newton + IFT; cached, builds only missing experiments)"
python3 /home/user/eval/train/evaluator.py --build-cache-only 2>&1 | tee -a "${R}/groundtruth_train.log"
python3 /home/user/eval/test/evaluator.py --build-cache-only 2>&1 | tee -a "${R}/groundtruth_test.log"

if [ "${RUN_HARDENING_CHECKS}" = "1" ] && ! bash /home/user/scripts/patch_acados.sh --check; then
    echo ">>> Audit: reference with the installed (unpatched) acados library, for the before/after record"
    python3 /home/user/hardening/run_checks.py --cases reference_unpatched_acados 2>&1 | tee -a "${R}/run_checks.log"
fi

echo ">>> acados with the sign fix of the parametric constraint Hessian (rebuilds only if needed)"
bash /home/user/scripts/ensure_acados.sh 2>&1 | tail -n 20

echo ">>> Reference method on the visible train slice"
bash /home/user/scripts/evaluate_train.sh
cp /home/user/scoring/scores_train.json /home/user/scoring/scores.json

echo ">>> Reference method on the hidden test slice"
bash /home/user/scripts/evaluate_test.sh

if [ "${RUN_HARDENING_CHECKS}" = "1" ]; then
    echo ">>> Hardening audit: variants and shortcuts through the same evaluators"
    python3 /home/user/hardening/run_checks.py 2>&1 | tee -a "${R}/run_checks.log"
fi

echo "========================================"
echo "JOB COMPLETE: scoring/scores_train.json, scoring/scores_test.json"
echo "========================================"
