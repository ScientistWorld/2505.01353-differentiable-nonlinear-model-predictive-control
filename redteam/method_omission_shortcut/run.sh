#!/bin/bash
set -euo pipefail
cd /home/user
source redteam/runtime.sh
python3 redteam/method_omission_shortcut/method.py
python3 redteam/test_case.py method_omission_shortcut
