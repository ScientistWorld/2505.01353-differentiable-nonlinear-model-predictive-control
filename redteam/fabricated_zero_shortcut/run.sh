#!/bin/bash
set -euo pipefail
cd /home/user
source redteam/runtime.sh
python3 redteam/fabricated_zero_shortcut/method.py
python3 redteam/test_case.py fabricated_zero_shortcut
