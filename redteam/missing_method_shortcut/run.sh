#!/bin/bash
set -euo pipefail
cd /home/user
source redteam/runtime.sh
python3 redteam/missing_method_shortcut/method.py
python3 redteam/test_case.py missing_method_shortcut
