#!/usr/bin/env python3
"""Check that the gym itself is back to its initial audit state.

Initial harness-owned placeholder changes are preserved. action.yaml may later
change only to deliver the mandatory final protocol signal.
"""
import hashlib
import subprocess
from common import ROOT, AUDIT, save

base = (AUDIT / 'base_commit.txt').read_text().strip()
paths = ['briefing', 'eval', 'method', 'baseline', 'data', 'environment',
         'scoring', 'scripts']
subprocess.run(['git', 'diff', '--exit-code', base, '--', *paths],
               cwd=ROOT, check=True, capture_output=True)
outside = subprocess.check_output([
    'git', 'diff', '--name-only', base, '--', '.',
    ':(exclude)README.md', ':(exclude)manifest.json',
    ':(exclude)trajectory/session.json', ':(exclude)redteam',
    ':(exclude)REDTEAM.md', ':(exclude)action.yaml',
], cwd=ROOT, text=True).splitlines()
assert not outside, outside
hashes = {}
for actual, original in (
    ('checkpoints/reproduction_results.json', 'packaged_artifact.json'),
    ('scoring/scores_test.json', 'packaged_scores_test.json'),
):
    content = (ROOT / actual).read_bytes()
    assert content == (AUDIT / original).read_bytes(), actual
    hashes[actual] = hashlib.sha256(content).hexdigest()
save(AUDIT / 'restoration_check.json', {
    'base_commit': base,
    'protected_tracked_directories_unchanged': paths,
    'unexpected_tracked_paths_outside_audit': outside,
    'original_artifact_byte_checks_sha256': hashes,
    'preserved_initial_harness_changes': [
        'README.md', 'manifest.json', 'trajectory/session.json', '.git-shims/',
    ],
    'protocol_control_exception': 'action.yaml is set to done after the final audit commit',
})
print('Gym restored; original artifact and test scores match byte for byte.')
