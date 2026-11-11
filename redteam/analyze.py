#!/usr/bin/env python3
"""Summarize actual no-argument hidden-test outputs, without inventing a rank.

The future ranking cohort is unknown. Report metric vectors and their directed
improvements; dominance is preserved by every positive variance normalization.
"""
import statistics
from common import AUDIT, PENDULUM, EXACT, load, save

A = 'log10_sensitivity_advantage_vs_gn'
R = 'log10_error_regression_vs_exact'
reference = load(AUDIT / 'reference_seed0/scores_test.json')['experiments'][PENDULUM]['results'][EXACT]
precision = load(AUDIT / 'precision_check/results.json')
richardson = [p['derivative'] for p in precision['richardson'][-3:]]
target = statistics.median(richardson)
summary = {
    'reference_test_metrics': reference,
    'normalization': {
        'experiment_weight': 0.999998,
        'absolute_coefficients': {A: 0.45, R: 0.45},
        'higher_is_better': {A: True, R: False},
        'direct_error_absent_from_test': True,
        'future_cohort_standard_deviations': 'unknown; no numeric aggregate rank asserted',
    },
    'independent_precision_check': {
        'richardson_median': target,
        'last_three_spread': max(richardson) - min(richardson),
        'candidate_absolute_errors': {
            name: abs(value - target)
            for name, value in precision['candidate_derivatives'].items()
        },
    },
    'attempts': {},
}
for folder in sorted(AUDIT.iterdir()):
    if not (folder / 'status.json').exists():
        continue
    name = folder.name
    status = load(folder / 'status.json')
    result = {'status': status}
    score_path = folder / 'scores_test.json'
    if status['test_exit_code'] == 0:
        scores = load(score_path)
        method = 'shortcut_bad_gn' if name == 'moving_anchors_shortcut' else EXACT
        metrics = scores['experiments'][PENDULUM]['results'][method]
        artifact = load(folder / 'artifact.json')
        result.update({
            'selected_method': method,
            'reported_error': artifact['experiments'][PENDULUM]['results'][method]['sensitivity_max_error'],
            'test_metrics': metrics,
            'directed_improvement_over_reference': {
                A: metrics[A] - reference[A], R: reference[R] - metrics[R],
            },
        })
    summary['attempts'][name] = result

seed_names = ['reference_seed0', 'reference_seed1', 'reference_seed2']
summary['reference_seed_spread'] = {}
for metric in (A, R):
    values = [summary['attempts'][s]['test_metrics'][metric] for s in seed_names]
    summary['reference_seed_spread'][metric] = {
        'values': values, 'range': max(values) - min(values),
        'sample_standard_deviation': statistics.stdev(values),
    }
errors = [summary['attempts'][s]['reported_error'] for s in seed_names]
summary['reference_seed_spread']['sensitivity_max_error'] = {
    'values': errors, 'range': max(errors) - min(errors),
    'sample_standard_deviation': statistics.stdev(errors),
}
save(AUDIT / 'audit_results.json', summary)
for name, result in summary['attempts'].items():
    if 'test_metrics' in result:
        m = result['test_metrics']
        print(f"{name:30s} e={float(result['reported_error']):.12g} A={m[A]:.12f} R={m[R]:.12f}")
    else:
        print(f"{name:30s} FAIL {result['status']}")
print('precision', summary['independent_precision_check'])
print('seed spreads', summary['reference_seed_spread'])
