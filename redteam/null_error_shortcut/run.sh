#!/bin/bash
set -euo pipefail
cd /home/user
source redteam/runtime.sh
python3 redteam/null_error_shortcut/method.py
python3 redteam/test_case.py null_error_shortcut
