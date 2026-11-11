#!/bin/bash
# Method entry point used by BOTH evaluators (train and hidden test):
#
#   bash scripts/predict.sh INSTANCES_JSON PREDICTIONS_JSON
#
# Reads problem instances (no answers) and writes raw predictions
# {"methods": {name: {experiment: {instance_id: {...}}}}}. Replace the python
# call below to plug in a different method; the evaluators only rely on this
# contract (see briefing/evaluation.md).

set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "usage: bash scripts/predict.sh INSTANCES_JSON PREDICTIONS_JSON" >&2
    exit 2
fi

cd /home/user
bash /home/user/scripts/repair_vendor_runtime.sh >/dev/null
source /home/user/scripts/_runtime_env.sh
export ACADOS_SOURCE_DIR=/home/user/method/acados
export LD_LIBRARY_PATH=/home/user/method/acados/lib:${LD_LIBRARY_PATH:-}
export PYTHONPATH=/home/user/method/acados/interfaces/acados_template:${PYTHONPATH:-}

python3 /home/user/method/predict.py "$1" "$2"
