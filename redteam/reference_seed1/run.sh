#!/bin/bash
set -euo pipefail
cd /home/user
source redteam/runtime.sh
python3 redteam/reference_seed1/method.py
python3 redteam/test_case.py reference_seed1
