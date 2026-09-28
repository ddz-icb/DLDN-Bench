"""
Regression tests for the PTM processing of de novo predictions (utils.modify_de_novo_result_with_filter_out_df).

Run from the repository root with:
    python -m unittest discover -s tests
"""
import os
import sys
import unittest

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from constants import aa_dict, modification_dict
from utils import modify_de_novo_result_with_filter_out_df


def make_df(sequences):
    return pd.DataFrame({'sequence': sequences, 'score': range(len(sequences))})


class TestModifyDeNovoResultWithFilterOut(unittest.TestCase):

    def test_unmodified_peptides_are_kept(self):
        # No numeric modifications at all -> previously raised ZeroDivisionError
        df = make_df(['PEPTIDEK', 'ACDEFGHIK', 'LMNPQR'])
        kept, excluded = modify_de_novo_result_with_filter_out_df(df, modification_dict)
        self.assertEqual(kept['sequence'].tolist(), df['sequence'].tolist())
        self.assertTrue(excluded.empty)

    def test_empty_input(self):
        kept, excluded = modify_de_novo_result_with_filter_out_df(make_df([]), modification_dict)
        self.assertTrue(kept.empty)
        self.assertTrue(excluded.empty)

    def test_supported_modifications_are_kept_unchanged(self):
        # Oxidation, carbamidomethylation and N-terminal acetylation are part of the ground truth
        sequences = ['PEPM+15.995K', 'AC+57.021DEK', '+42.011PEPTIDEK', '+42.011M+15.995C+57.021K']
        df = make_df(sequences)
        kept, excluded = modify_de_novo_result_with_filter_out_df(df, modification_dict)
        self.assertEqual(kept['sequence'].tolist(), sequences)
        self.assertTrue(excluded.empty)

    def test_unsupported_modifications_are_excluded(self):
        # Deamidation, carbamylation and NH3 loss are not part of the ground truth
        sequences = ['PEPN+0.984K', 'PEPQ+0.984K', '+43.006PEPTIDEK', '-17.027PEPTIDEK', '+43.006-17.027PEPTIDEK']
        df = make_df(sequences)
        kept, excluded = modify_de_novo_result_with_filter_out_df(df, modification_dict)
        self.assertTrue(kept.empty)
        self.assertEqual(excluded['sequence'].tolist(), sequences)

    def test_mixed_predictions_are_split_correctly(self):
        df = make_df(['PEPTIDEK', 'PEPM+15.995K', 'PEPN+0.984K', '+42.011PEPTIDEK', '+43.006PEPTIDEK'])
        kept, excluded = modify_de_novo_result_with_filter_out_df(df, modification_dict)
        self.assertEqual(kept['sequence'].tolist(), ['PEPTIDEK', 'PEPM+15.995K', '+42.011PEPTIDEK'])
        self.assertEqual(excluded['sequence'].tolist(), ['PEPN+0.984K', '+43.006PEPTIDEK'])
        # Other columns and the original index are preserved
        self.assertEqual(kept['score'].tolist(), [0, 1, 3])
        self.assertEqual(kept.index.tolist(), [0, 1, 3])
        self.assertEqual(len(kept) + len(excluded), len(df))

    def test_kept_predictions_only_contain_ground_truth_tokens(self):
        # Every kept prediction can be scored with aa_dict (same tokenisation as calculate_criteria.aa_match_batch)
        df = make_df(['PEPTIDEK', 'PEPM+15.995K', 'AC+57.021DEK', '+42.011PEPTIDEK', 'PEPN+0.984K', '-17.027PEPTIDEK'])
        kept, _ = modify_de_novo_result_with_filter_out_df(df, modification_dict)
        tokens = kept['sequence'].str.split(r"(?<=.)(?=[A-Z])", regex=True).explode()
        self.assertTrue(tokens.isin(aa_dict.keys()).all(), tokens[~tokens.isin(aa_dict.keys())].tolist())


if __name__ == '__main__':
    unittest.main()
