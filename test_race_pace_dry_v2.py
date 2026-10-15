"""Check uncertainty rules without changing any data file."""
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

from race_pace_dry_v2 import (METHOD_ERRORS, bootstrap_gap, cluster_covariance,
                             confidence, design_fit, smallest_error,
                             uncertainty_disagreement)
from test_race_pace_regression import fixture


class DryV2Tests(unittest.TestCase):
    def test_final_gap_unchanged_for_every_saved_pair(self):
        root = Path(__file__).resolve().parent
        target = root / "data/race_pace_dry_combined_v2.csv"
        if not target.exists():
            self.skipTest("Integration check runs after the first v2 export")
        a = pd.read_csv(root / "data/race_pace_dry_combined.csv", float_precision="round_trip")
        b = pd.read_csv(target, float_precision="round_trip")
        pd.testing.assert_frame_equal(a[["round_number", "team", "driver", "teammate", "final_gap", "method_used"]],
                                      b[["round_number", "team", "driver", "teammate", "final_gap", "method_used"]],
                                      check_exact=True)
        changed = {"strict_gap_se_pp", "lowconf_gap_se_pp", "final_confidence", "disagreement_flag"}
        for column in set(a.columns) - changed:
            pd.testing.assert_series_equal(a[column], b[column], check_exact=True)

    def test_bootstrap_same_seed_identical(self):
        values = np.sin(np.arange(31)) + np.arange(31) / 10
        self.assertEqual(bootstrap_gap(values, 42), bootstrap_gap(values, 42))
        self.assertNotEqual(bootstrap_gap(values, 42), bootstrap_gap(values, 43))

    def test_bootstrap_two_block_boundary_and_constant(self):
        self.assertEqual(bootstrap_gap(np.ones(9))[3], "too_few_laps_for_two_blocks")
        self.assertEqual(bootstrap_gap(np.ones(10)), (0., 1., 1., ""))

    def test_confidence_boundaries(self):
        for se, count, expected in [(.15, 20, "high"), (.15, 19, "medium"),
                                     (.30, 10, "medium"), (.30001, 30, "low"),
                                     (.1, 9, "low"), (np.nan, 30, "low")]:
            self.assertEqual(confidence(.1, se, count), expected)
        self.assertEqual(confidence(np.nan, .01, 100), "unavailable")

    def test_uncertainty_disagreement(self):
        row = {key: np.nan for pair in METHOD_ERRORS.items() for key in pair}
        row.update(strict_gap=0., strict_gap_se_pp=.15,
                   regression_gap_linear=.5, regression_gap_linear_se_cluster_pp=.20)
        self.assertEqual(uncertainty_disagreement(row), (False, 1))
        row["regression_gap_linear"] = .50001
        self.assertEqual(uncertainty_disagreement(row), (True, 1))
        row["regression_gap_linear_se_cluster_pp"] = np.nan
        self.assertEqual(uncertainty_disagreement(row), (None, 0))

    def test_smallest_error_does_not_change_final_gap(self):
        row = {key: np.nan for pair in METHOD_ERRORS.items() for key in pair}
        row.update(final_gap=.2, strict_gap=.2, strict_gap_se_pp=.3,
                   regression_gap_curved=-.1, regression_gap_curved_se_cluster_pp=.1)
        self.assertEqual(smallest_error(row), (-.1, "regression_gap_curved", .1))
        self.assertEqual(row["final_gap"], .2)

    def test_cluster_cr1_matches_direct_formula(self):
        x = np.column_stack([np.ones(12), np.arange(12)])
        y = np.array([2, 3, 5, 3, 8, 6, 7, 9, 9, 10, 11, 14.])
        bread = np.linalg.inv(x.T @ x)
        beta = bread @ x.T @ y
        residual = y - x @ beta
        labels = np.repeat(["A:1", "A:2", "B:1"], 4)
        expected = np.zeros((2, 2))
        for start in [0, 4, 8]:
            score = x[start:start+4].T @ residual[start:start+4]
            expected += np.outer(score, score)
        expected = (3 / 2) * (11 / 10) * bread @ expected @ bread
        np.testing.assert_allclose(cluster_covariance(x, residual, bread, labels), expected)

    def test_prediction_uses_training_design_and_known_driver_offset(self):
        frame = fixture()
        for curved in [False, True]:
            model, reason = design_fit(frame, "A", "B", curved)
            self.assertEqual(reason, "")
            np.testing.assert_allclose(model["predict"](frame), frame.lap_seconds, atol=1e-10)
            new = frame.iloc[:1].copy()
            new.Compound = "HARD"
            with self.assertRaisesRegex(ValueError, "unseen_compound"):
                model["predict"](new)


if __name__ == "__main__":
    unittest.main()
