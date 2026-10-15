#!/usr/bin/env python3
"""Reproduce animal-paired RT-qPCR summaries and the complete 18-test family.

Inputs are the accompanying S2 CSV and S4 JSON, never private local files.
The CSV contains Nox1/Nox4; the JSON retains raw Cq pairs for all six targets
that define the original family of 18 two-sided Welch comparisons.

Recorded runtime: Python 3.12.14, NumPy 2.5.4, SciPy 1.18.1.
Install the required packages in a suitable environment before running.

Run: python S2_Appendix_Reproduce_RTqPCR.py
Optional paths: --values-csv FILE --statistics-json FILE --output FILE
Without --output, the verified reproduction results are printed to stdout.
The supplied input files are read only and are never rewritten.

Each rat has one recorded target/reference pair per target. Source worksheet
columns are traceability labels, not verified specimen IDs. Amplification
efficiency E=2 is an unverified assumption. Descriptive values are Q divided
by the sham arithmetic mean Q; inference uses animal delta Cq, with Holm
adjustment across all 18 tests. Confidence intervals are nominal 95% Welch
intervals and are not simultaneous, multiplicity-adjusted intervals.
"""

import argparse
import csv
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy import stats
import scipy


GROUPS = ('Sham-operated', 'Model', 'Restoration')
PAIRS = (('Model', 'Sham-operated'),
         ('Restoration', 'Sham-operated'),
         ('Restoration', 'Model'))


def assert_close(actual, expected, label):
    if not math.isclose(float(actual), float(expected), rel_tol=1e-9, abs_tol=1e-12):
        raise AssertionError(f'{label}: recomputed {actual!r}, recorded {expected!r}')


def describe(values):
    values = np.asarray(values, dtype=float)
    return {'n': len(values), 'mean': float(values.mean()),
            'sample_sd': float(values.std(ddof=1)),
            'min': float(values.min()), 'max': float(values.max())}


def welch_anova(groups):
    """Welch one-way F, both degrees of freedom and unadjusted diagnostic P."""
    n = np.array([len(x) for x in groups], dtype=float)
    means = np.array([np.mean(x) for x in groups])
    variances = np.array([np.var(x, ddof=1) for x in groups])
    weights = n / variances
    total = weights.sum()
    weighted_mean = np.sum(weights * means) / total
    k = len(groups)
    term = np.sum((1 - weights / total) ** 2 / (n - 1))
    f = (np.sum(weights * (means - weighted_mean) ** 2) / (k - 1)) / (
        1 + 2 * (k - 2) * term / (k * k - 1))
    df1 = k - 1
    df2 = (k * k - 1) / (3 * term)
    return {'F': float(f), 'df1': float(df1), 'df2': float(df2),
            'p_raw': float(stats.f.sf(f, df1, df2))}


def holm_all(p_values):
    p_values = np.asarray(p_values, dtype=float)
    order = np.argsort(p_values, kind='stable')
    ordered_adjusted = np.minimum(1, np.maximum.accumulate(
        (len(p_values) - np.arange(len(p_values))) * p_values[order]))
    adjusted = np.empty_like(ordered_adjusted)
    adjusted[order] = ordered_adjusted
    return adjusted


def reproduce(values_csv, statistics_json):
    record = json.loads(statistics_json.read_text(encoding='utf-8'))
    records = record['input_records']
    if len(record['genes']) != 6 or len(records) != 108:
        raise AssertionError('The complete six-target, 108-row input is required.')
    source_keys = set()
    reference_pairs = {}
    inputs = {}
    for row in records:
        key = (row['target'], row['group'], row['source_worksheet_column'])
        if key in source_keys:
            raise AssertionError(f'Duplicate input traceability key: {key}')
        source_keys.add(key)
        if row['group'] not in GROUPS:
            raise AssertionError(f'Unexpected group: {row["group"]}')
        ref_key = (row['group'], row['source_worksheet_column'])
        ref_value = (row['Actb_Cq_source_row'], row['paired_Actb_Cq'])
        if ref_key in reference_pairs and reference_pairs[ref_key] != ref_value:
            raise AssertionError(f'Inconsistent shared reference Cq at {ref_key}')
        reference_pairs[ref_key] = ref_value
        delta = float(row['target_Cq']) - float(row['paired_Actb_Cq'])
        quantity = 2.0 ** (-delta)
        assert_close(delta, row['delta_Cq'], f'{key}: delta Cq')
        assert_close(quantity, row['Q'], f'{key}: Q')
        inputs.setdefault(row['target'], {}).setdefault(row['group'], []).append(
            {**row, 'computed_delta_Cq': delta, 'computed_Q': quantity})

    # The public two-target CSV is checked against the full-family JSON inputs.
    with values_csv.open(newline='', encoding='utf-8') as handle:
        csv_rows = list(csv.DictReader(handle))
    if len(csv_rows) != 36:
        raise AssertionError('S2 must contain 36 paired Nox1/Nox4 records.')
    all_rows = {(r['target'], r['group'], r['source_worksheet_column']): r
                for r in records}
    csv_keys = set()
    for row in csv_rows:
        key = (row['target'], row['group'], row['source_worksheet_column'])
        if row['target'] not in ('Nox1', 'Nox4') or key in csv_keys:
            raise AssertionError(f'Unexpected or duplicate S2 row: {key}')
        csv_keys.add(key)
        supplied = all_rows[key]
        for field in ('target_Cq_source_row', 'Actb_Cq_source_row', 'target_Cq',
                      'paired_Actb_Cq', 'delta_Cq', 'Q', 'normalized_expression'):
            assert_close(float(row[field]), supplied[field], f'S2 {key}: {field}')
    expected_keys = {key for key in all_rows if key[0] in ('Nox1', 'Nox4')}
    if csv_keys != expected_keys:
        raise AssertionError('The two-target CSV does not match the JSON input.')

    summaries = []
    comparisons = []
    for gene in record['genes']:
        target = gene['gene']
        raw_groups = inputs[target]
        if set(raw_groups) != set(GROUPS):
            raise AssertionError(f'Incomplete groups for {target}')
        if any(len(raw_groups[name]) != 6 for name in GROUPS):
            raise AssertionError(f'{target} must have six rats in each group.')
        calibration = float(np.mean([r['computed_Q'] for r in raw_groups[GROUPS[0]]]))
        assert_close(calibration, gene['calibrator_control_arithmetic_mean_Q'],
                     f'{target}: arithmetic Q calibrator')
        deltas = {}
        folds = {}
        target_summary = {'target': target, 'calibrator_sham_arithmetic_mean_Q': calibration,
                          'groups': []}
        for original in gene['groups']:
            name = original['group']
            rows = raw_groups[name]
            deltas[name] = np.array([r['computed_delta_Cq'] for r in rows])
            folds[name] = np.array([r['computed_Q'] / calibration for r in rows])
            for row, fold in zip(rows, folds[name]):
                assert_close(fold, row['normalized_expression'],
                             f'{target}/{name}/{row["source_worksheet_column"]}: expression')
            group_summary = {'group': name, 'n_biological_animals': len(rows),
                             'delta_Cq_statistics': describe(deltas[name]),
                             'normalized_expression_statistics': describe(folds[name])}
            for output_field, recorded_field in (
                    ('delta_Cq_statistics','delta_ct_statistics'),
                    ('normalized_expression_statistics','fold_statistics')):
                for field, value in group_summary[output_field].items():
                    assert_close(value, original[recorded_field][field],
                                 f'{target}/{name}/{output_field}/{field}')
            shapiro = stats.shapiro(deltas[name])
            assert_close(shapiro.statistic, original['shapiro_wilk_delta_ct']['W'],
                         f'{target}/{name}: diagnostic Shapiro W')
            assert_close(shapiro.pvalue, original['shapiro_wilk_delta_ct']['p_diagnostic'],
                         f'{target}/{name}: diagnostic Shapiro P')
            group_summary['shapiro_wilk_diagnostic'] = {
                'W': float(shapiro.statistic), 'p': float(shapiro.pvalue)}
            target_summary['groups'].append(group_summary)
        global_diagnostic = welch_anova([deltas[g] for g in GROUPS])
        for field,value in global_diagnostic.items():
            assert_close(value,gene['welch_anova_delta_ct'][field],f'{target}: Welch ANOVA {field}')
        global_diagnostic['multiplicity_adjusted'] = False
        target_summary['welch_anova_delta_Cq_secondary_diagnostic'] = global_diagnostic
        levene = stats.levene(*[deltas[g] for g in GROUPS], center='median')
        assert_close(levene.statistic,gene['levene_median_delta_ct']['statistic'],f'{target}: Levene')
        assert_close(levene.pvalue,gene['levene_median_delta_ct']['p_diagnostic'],f'{target}: Levene P')
        target_summary['levene_median_diagnostic'] = {
            'statistic':float(levene.statistic), 'p':float(levene.pvalue)}
        summaries.append(target_summary)
        for numerator, denominator in PAIRS:
            result = stats.ttest_ind(deltas[numerator],deltas[denominator],
                                     equal_var=False, alternative='two-sided')
            ci = result.confidence_interval(confidence_level=.95)
            difference = float(deltas[numerator].mean()-deltas[denominator].mean())
            comparisons.append({
                'gene':target,'numerator_group':numerator,'denominator_group':denominator,
                'n_numerator':6,'n_denominator':6,
                'delta_ct_difference':difference,
                't_statistic':float(result.statistic), 'degrees_of_freedom':float(result.df),
                'p_raw':float(result.pvalue),
                'delta_ct_difference_CI95_unadjusted':[float(ci.low),float(ci.high)],
                'geometric_expression_ratio_2_power_negative_delta_ct_difference':2.0**(-difference),
                'geometric_expression_ratio_CI95_unadjusted':[2.0**(-float(ci.high)),2.0**(-float(ci.low))],
                'arithmetic_mean_expression_ratio':float(folds[numerator].mean()/folds[denominator].mean())
            })
    if len(comparisons) != 18:
        raise AssertionError('The Holm family must contain all 18 comparisons.')
    adjusted = holm_all([r['p_raw'] for r in comparisons])
    recorded_tests = {(r['gene'],r['numerator_group'],r['denominator_group']):r
                      for r in record['comparisons']}
    if len(recorded_tests) != 18:
        raise AssertionError('S4 must retain 18 distinct formal comparisons.')
    for row,p in zip(comparisons,adjusted):
        row['p_holm_18_test_family'] = float(p)
        row['significant_at_holm_0_05'] = bool(p < .05)
        expected = recorded_tests[(row['gene'],row['numerator_group'],row['denominator_group'])]
        for field,value in row.items():
            if isinstance(value, (float,int)):
                assert_close(value,expected[field],f'{row["gene"]} comparison: {field}')
            elif isinstance(value,list):
                for actual,original in zip(value,expected[field]):
                    assert_close(actual,original,f'{row["gene"]} comparison: {field}')
        if row['significant_at_holm_0_05'] != expected['significant_at_holm_0_05']:
            raise AssertionError('A Holm significance decision differs from S4.')
    return {'verification':'PASS: all input pairs, S2 rows, summaries and 18-test outputs match S4.',
            'runtime':{'python':sys.version.split()[0],'numpy':np.__version__,'scipy':scipy.__version__},
            'multiplicity':{'family_size':18,'method':'Holm step-down','alpha':.05,
                            'significant_comparison_count':sum(r['significant_at_holm_0_05'] for r in comparisons)},
            'descriptive_summaries':summaries,'comparisons':comparisons,
            'limitations':record['limitations']}


def main():
    folder = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--values-csv',type=Path,default=folder/'S2_Data_RTqPCR_Animal_Paired_Values.csv')
    parser.add_argument('--statistics-json',type=Path,default=folder/'S4_File_RTqPCR_Statistical_Outputs.json')
    parser.add_argument('--output',type=Path,help='Optional new file for recomputed results; input files remain read only.')
    args = parser.parse_args()
    if args.output and args.output.resolve() in (args.values_csv.resolve(),args.statistics_json.resolve()):
        parser.error('--output must not overwrite either input file.')
    result = reproduce(args.values_csv,args.statistics_json)
    serialized = json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
    if args.output:
        args.output.write_text(serialized,encoding='utf-8')
        print(result['verification'])
    else:
        print(serialized,end='')


if __name__ == '__main__':
    main()
