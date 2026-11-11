#!/bin/bash
# Run the paper's method (acados two-solver sensitivities) through the gym's
# predictor contract on the visible train instances and score it.
set -euo pipefail
cd /home/user
bash /home/user/scripts/evaluate_train.sh
