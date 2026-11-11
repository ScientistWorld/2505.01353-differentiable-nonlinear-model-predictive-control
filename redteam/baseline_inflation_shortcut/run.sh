#!/bin/bash
set -euo pipefail
cd /home/user
source redteam/runtime.sh
python3 redteam/baseline_inflation_shortcut/method.py
python3 redteam/test_case.py baseline_inflation_shortcut
