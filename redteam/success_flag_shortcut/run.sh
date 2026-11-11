#!/bin/bash
set -euo pipefail
cd /home/user
source redteam/runtime.sh
python3 redteam/success_flag_shortcut/method.py
python3 redteam/test_case.py success_flag_shortcut
