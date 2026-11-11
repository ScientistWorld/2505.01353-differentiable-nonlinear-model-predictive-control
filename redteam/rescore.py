#!/usr/bin/env python3
"""Recheck every saved candidate with the original evaluator entry points.

Only stdlib scoring runs here; numerical outputs are reused unchanged. Each
evaluation is a new process with no method-only Python/library settings.
"""
import subprocess
from common import ROOT, AUDIT, load, save

paths = [ROOT / 'checkpoints/reproduction_results.json',
         ROOT / 'scoring/scores_train.json', ROOT / 'scoring/scores_test.json']
saved = {p: p.read_bytes() if p.exists() else None for p in paths}
outcomes = {}
try:
    for folder in sorted(AUDIT.iterdir()):
        artifact = folder / 'artifact.json'
        if not artifact.exists():
            continue
        (ROOT / 'checkpoints/reproduction_results.json').write_bytes(artifact.read_bytes())
        with (folder / 'rescore.log').open('w') as log:
            subprocess.run(['python3', 'redteam/test_case.py', folder.name],
                           cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
        outcomes[folder.name] = load(folder / 'status.json')
    save(AUDIT / 'rescore_status.json', outcomes)
finally:
    for p, content in saved.items():
        if content is None:
            p.unlink(missing_ok=True)
        else:
            p.write_bytes(content)
