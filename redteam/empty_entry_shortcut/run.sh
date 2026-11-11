#!/bin/bash
set -euo pipefail
cd /home/user
source redteam/runtime.sh
python3 redteam/empty_entry_shortcut/method.py
python3 redteam/test_case.py empty_entry_shortcut
