#!/bin/bash
set -euo pipefail
cd /home/user
source redteam/runtime.sh
python3 redteam/constant_zero_shortcut/method.py
python3 redteam/test_case.py constant_zero_shortcut
