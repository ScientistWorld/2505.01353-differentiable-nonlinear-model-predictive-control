#!/bin/bash
set -euo pipefail
cd /home/user
source redteam/runtime.sh
python3 redteam/negative_error_shortcut/method.py
python3 redteam/test_case.py negative_error_shortcut
