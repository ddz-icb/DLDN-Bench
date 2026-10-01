"""
End-to-end tests for calc_and_plot_precision_coverage.py.

Run from the repository root with:
    python -m unittest discover -s tests

The full reproduction test is skipped by default. To run it, create the aligned predictions of PXD043425 with
create_result_csv.py (see README) and set the path (runtime ~6 min):
    DE_NOVO_EVAL_FULL_CSV=/path/to/PXD043425_benchmark_predictions.csv python -m unittest discover -s tests
"""
import os
import subprocess
import sys
import tempfile
import unittest

import pandas as pd

REPO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
DATA_DIR = os.path.join(REPO_DIR, 'tests', 'data')

# Some tools (mainly Pi-HelixNovo) assign identical scores to many PSMs. The order of tied PSMs after sorting by
# score is not guaranteed across platforms, which changes the AUC slightly (up to ~0.008 on the mini dataset,
# up to ~0.0005 on the full dataset), hence the tolerances below.
MINI_TOLERANCE = 0.01
REPORTED_TOLERANCE = 0.002  # reported values are rounded to 3 decimals


def run_precision_coverage(input_csv, dataset_name, output_dir):
    subprocess.run([sys.executable, 'calc_and_plot_precision_coverage.py', '-i', input_csv, '-o', output_dir,
                    '-d', dataset_name, '--tables', output_dir], cwd=REPO_DIR, check=True, capture_output=True)
    return pd.read_csv(os.path.join(output_dir, f'{dataset_name}_auc.csv')).set_index('tool')


class TestEndToEnd(unittest.TestCase):

    def assert_auc_close(self, result, expected, tolerance):
        self.assertEqual(sorted(result.index), sorted(expected.index))
        for tool in expected.index:
            for col in ('peptide_auc', 'aa_auc'):
                self.assertAlmostEqual(result.loc[tool, col], expected.loc[tool, col], delta=tolerance,
                                       msg=f'{tool} {col}')

    def test_mini_dataset(self):
        # 1,000 PSMs randomly sampled (seed 0) from the aligned predictions of PXD043425
        expected = pd.read_csv(os.path.join(DATA_DIR, 'PXD043425_mini_expected_auc.csv')).set_index('tool')
        with tempfile.TemporaryDirectory() as output_dir:
            result = run_precision_coverage(os.path.join(DATA_DIR, 'PXD043425_mini_benchmark_predictions.csv'),
                                            'PXD043425_mini', output_dir)
            for suffix in ('peptide_precision_coverage.png', 'aminoacid_precision_coverage.png',
                           'peptide_precision_coverage.csv', 'aminoacid_precision_coverage.csv'):
                self.assertTrue(os.path.isfile(os.path.join(output_dir, f'PXD043425_mini_{suffix}')), suffix)
        self.assert_auc_close(result, expected, MINI_TOLERANCE)

    @unittest.skipUnless(os.environ.get('DE_NOVO_EVAL_FULL_CSV'), 'set DE_NOVO_EVAL_FULL_CSV to run')
    def test_reproduce_reported_PXD043425(self):
        # AUC values reported for PXD043425 (peptide and amino acid level precision-coverage plots)
        reported = pd.read_csv(os.path.join(DATA_DIR, 'PXD043425_reported_auc.csv')).set_index('tool')
        with tempfile.TemporaryDirectory() as output_dir:
            result = run_precision_coverage(os.environ['DE_NOVO_EVAL_FULL_CSV'], 'PXD043425', output_dir)
        self.assert_auc_close(result, reported, REPORTED_TOLERANCE)


if __name__ == '__main__':
    unittest.main()
