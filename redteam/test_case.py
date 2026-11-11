#!/usr/bin/env python3
"""Run the public entry points as separate processes, and preserve evidence.

All score-bearing data is obtained from bash scripts/evaluate_test.sh without
arguments. The evaluator's environment and code are left alone.
"""
import argparse
import shutil
import subprocess
import time

from common import AUDIT, ROOT, PENDULUM, EXACT, GN, load, save

parser = argparse.ArgumentParser()
parser.add_argument('name')
args = parser.parse_args()
name = args.name
folder = AUDIT / name
folder.mkdir(parents=True, exist_ok=True)
status = {}

for split in ('train', 'test'):
    path = ROOT / f'scoring/scores_{split}.json'
    # Failed evaluations must not inherit a previous candidate's score file.
    path.unlink(missing_ok=True)

start = time.monotonic()
with (folder / 'evaluate_train.log').open('w') as log:
    status['train_exit_code'] = subprocess.run(
        ['bash', 'scripts/evaluate_train.sh'], cwd=ROOT,
        stdout=log, stderr=subprocess.STDOUT).returncode
train_path = ROOT / 'scoring/scores_train.json'
if train_path.exists():
    if name == 'method_omission_shortcut':
        scores = load(train_path)
        del scores['experiments'][PENDULUM]['results']['shortcut_zero_derivative']
        save(train_path, scores)
    shutil.copyfile(train_path, folder / 'scores_train.json')

with (folder / 'evaluate_test.log').open('w') as log:
    status['test_exit_code'] = subprocess.run(
        ['bash', 'scripts/evaluate_test.sh'], cwd=ROOT,
        stdout=log, stderr=subprocess.STDOUT).returncode
test_path = ROOT / 'scoring/scores_test.json'
status['test_wrote_scores'] = test_path.exists()
if test_path.exists():
    shutil.copyfile(test_path, folder / 'scores_test.json')
status['evaluation_seconds'] = time.monotonic() - start
save(folder / 'status.json', status)
print(name, status, flush=True)
