#!/bin/bash
set -euo pipefail
cd /home/user
source redteam/runtime.sh
python3 redteam/reference_seed2/method.py
python3 redteam/test_case.py reference_seed2
