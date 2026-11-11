#!/usr/bin/env python3
"""One CPU job; independent candidate/evaluator processes, restore on exit."""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from common import AUDIT, ROOT, save

CASES = [
    'reference_seed0', 'reference_seed1', 'reference_seed2',
    'better_clip', 'better_tol10', 'better_tol12', 'weaker_gn',
    'fd_oracle_shortcut', 'single_point_shortcut',
    'fabricated_zero_shortcut', 'boolean_zero_shortcut',
    'baseline_inflation_shortcut', 'moving_anchors_shortcut',
    'method_omission_shortcut', 'constant_zero_shortcut',
    'negative_error_shortcut', 'null_error_shortcut', 'nan_error_shortcut',
    'empty_entry_shortcut', 'missing_method_shortcut', 'success_flag_shortcut',
]

paths = [ROOT / 'checkpoints/reproduction_results.json',
         ROOT / 'scoring/scores_train.json', ROOT / 'scoring/scores_test.json']
snapshots = {str(p): p.read_bytes() if p.exists() else None for p in paths}
outcomes = {}
try:
    for name in CASES:
        folder = AUDIT / name
        folder.mkdir(parents=True, exist_ok=True)
        # Resume completed cases if a later one or the node fails.
        if (folder / 'status.json').exists():
            print('ALREADY_EVALUATED', name, flush=True)
            continue
        start = time.monotonic()
        print('START', name, flush=True)
        with (folder / 'run.log').open('w') as log:
            result = subprocess.run(['bash', str(folder / 'run.sh')], cwd=ROOT,
                                    stdout=log, stderr=subprocess.STDOUT, timeout=1200)
        outcomes[name] = {'exit_code': result.returncode,
                          'seconds': time.monotonic() - start}
        save(AUDIT / 'suite_status.json', outcomes)
        print('DONE', name, outcomes[name], flush=True)
        if name == 'reference_seed0' and result.returncode:
            raise RuntimeError('Reference failed; see reference_seed0/run.log')
finally:
    for path, content in snapshots.items():
        p = Path(path)
        if content is None:
            p.unlink(missing_ok=True)
        else:
            p.write_bytes(content)
