#!/bin/bash
set -euo pipefail
cd /home/user
source redteam/runtime.sh
python3 redteam/weaker_gn/method.py
python3 redteam/test_case.py weaker_gn
