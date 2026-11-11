#!/bin/bash
set -euo pipefail
cd /home/user
source redteam/runtime.sh
python3 redteam/fd_oracle_shortcut/method.py
python3 redteam/test_case.py fd_oracle_shortcut
