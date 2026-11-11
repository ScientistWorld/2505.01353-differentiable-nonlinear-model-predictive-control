#!/usr/bin/env python3
"""Concrete shortcuts at the public artifact interface; no evaluator tampering."""
import copy
import sys

from common import AUDIT, ROOT, PENDULUM, EXACT, GN, load, save, publish, reference, minimal

name = sys.argv[1]
if name in ('fabricated_zero_shortcut', 'boolean_zero_shortcut'):
    # Shortcut needs no method code, training data, paper, or hidden metric names.
    artifact = minimal(error=False if name == 'boolean_zero_shortcut' else 0.0)
elif name == 'baseline_inflation_shortcut':
    artifact = reference()
    artifact['experiments'][PENDULUM]['results'][GN]['sensitivity_max_error'] *= 1e6
elif name == 'moving_anchors_shortcut':
    artifact = reference()
    p = artifact['experiments'][PENDULUM]['results']
    # The actual candidate is the bad GN derivative, reused from a real solve.
    p['shortcut_bad_gn'] = copy.deepcopy(p[GN])
    p[EXACT]['sensitivity_max_error'] = 1e15
    p[GN]['sensitivity_max_error'] = 1e15
elif name == 'method_omission_shortcut':
    artifact = reference()
    d = load(AUDIT / 'reference_seed0/diagnostics.json')
    artifact['experiments'][PENDULUM]['results']['shortcut_zero_derivative'] = {
        'sensitivity_max_error': abs(d['fd_sensitivity'])}
elif name in ('weaker_gn', 'constant_zero_shortcut'):
    artifact = reference()
    p = artifact['experiments'][PENDULUM]['results']
    d = load(AUDIT / 'reference_seed0/diagnostics.json')
    # Real sensitivity outputs from the already-run control problem.
    sensitivity = d['gn_sensitivity'] if name == 'weaker_gn' else 0.0
    p[EXACT]['sensitivity_max_error'] = abs(sensitivity - d['fd_sensitivity'])
    save(AUDIT / name / 'diagnostics.json', {
        'candidate_sensitivity': sensitivity, 'evaluation_fd': d['fd_sensitivity'],
        'reused_nominal_solve': 'reference_seed0'})
elif name in ('negative_error_shortcut', 'null_error_shortcut', 'nan_error_shortcut',
              'empty_entry_shortcut', 'missing_method_shortcut', 'success_flag_shortcut'):
    artifact = reference()
    p = artifact['experiments'][PENDULUM]['results']
    if name == 'empty_entry_shortcut':
        p[EXACT] = {}
    elif name == 'missing_method_shortcut':
        del p[EXACT]
    elif name == 'success_flag_shortcut':
        p[EXACT] = {'success': True}
    else:
        p[EXACT]['sensitivity_max_error'] = {
            'negative_error_shortcut': -1.0,
            'null_error_shortcut': None,
            'nan_error_shortcut': float('nan'),
        }[name]
else:
    raise ValueError(name)
publish(name, artifact)
