#!/usr/bin/env python3
"""Run the remaining numerical checks and restore scoring/artifact files."""
import subprocess
from common import ROOT, AUDIT

paths = [ROOT / 'checkpoints/reproduction_results.json',
         ROOT / 'scoring/scores_train.json', ROOT / 'scoring/scores_test.json']
saved = {p: p.read_bytes() if p.exists() else None for p in paths}
try:
    p = AUDIT / 'precision_check'
    p.mkdir(exist_ok=True)
    with (p / 'run.log').open('w') as log:
        subprocess.run(['python3', 'redteam/precision_check.py'], cwd=ROOT,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    for name in ('better_native_tol10', 'better_native_tol12'):
        with (AUDIT / name / 'run.log').open('w') as log:
            subprocess.run(['bash', f'redteam/{name}/run.sh'], cwd=ROOT,
                           stdout=log, stderr=subprocess.STDOUT, check=True)
finally:
    for p, content in saved.items():
        if content is None:
            p.unlink(missing_ok=True)
        else:
            p.write_bytes(content)
