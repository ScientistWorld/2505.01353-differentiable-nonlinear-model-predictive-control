#!/bin/bash
# The baselines (gauss_newton_approx: IFT with the Gauss-Newton Hessian;
# unconstrained_ift: IFT after dropping all inequality constraints) are written
# by the same predictor as the proposed method, so one train evaluation scores
# all of them. Results: scoring/scores_train.json.
set -euo pipefail
cd /home/user
bash /home/user/scripts/evaluate_train.sh
