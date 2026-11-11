#!/bin/bash
set -euo pipefail
cd /home/user
source redteam/runtime.sh
python3 redteam/better_tol12/method.py
python3 redteam/test_case.py better_tol12
