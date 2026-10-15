"""Small checks for the new models; no race files are changed."""
import unittest

import numpy as np
import pandas as pd

from race_pace_regression import choose_final, comparison_summary, disagreement, fit_pair


def fixture():
    rows = []
    for driver, time in [("A", 90.0), ("B", 90.3)]:
        for i in range(32):
            rows.append(dict(DriverNumber=driver, Compound="MEDIUM", TyreLife=1 + i % 11,
                             LapNumber=2 + i, lap_seconds=time))
    return pd.DataFrame(rows)


class RegressionTests(unittest.TestCase):
    def test_signed_gap_and_reverse(self):
        for curved in [False, True]:
            a = fit_pair(fixture(), "A", "B", curved)
            b = fit_pair(fixture(), "B", "A", curved)
            self.assertEqual(a["reason_code"], "")
            self.assertAlmostEqual(a["gap_pct"], 100 * (90 - 90.3) / 90.3)
            self.assertAlmostEqual(b["gap_pct"], 100 * (90.3 - 90) / 90)
            self.assertAlmostEqual(a["driver_term_seconds"], -.3)
            self.assertLess(a["driver_term_se_seconds"], 1e-10)

    def test_seven_shared_compound_laps_is_confounded(self):
        data = fixture()
        data.loc[(data.DriverNumber == "B") & (data.LapNumber >= 9), "Compound"] = "HARD"
        result = fit_pair(data, "A", "B")
        self.assertTrue(result["strategy_confounded"])
        self.assertEqual(result["reason_code"], "strategy_confounded")
        self.assertTrue(np.isnan(result["gap_pct"]))
        self.assertTrue(np.isfinite(result["unreliable_gap_pct"]))

    def test_eight_shared_compound_laps_pass(self):
        data = fixture()
        data.loc[(data.DriverNumber == "B") & (data.LapNumber >= 10), "Compound"] = "HARD"
        self.assertFalse(fit_pair(data, "A", "B")["strategy_confounded"])

    def test_no_shared_compound_cannot_identify_driver_effect(self):
        data = fixture()
        data.loc[data.DriverNumber == "B", "Compound"] = "HARD"
        result = fit_pair(data, "A", "B")
        self.assertIn("effects_not_identifiable", result["all_reason_codes"])
        self.assertTrue(np.isnan(result["unreliable_gap_pct"]))

    def test_age_lap_collinearity(self):
        data = fixture()
        data.TyreLife = data.LapNumber
        self.assertEqual(fit_pair(data, "A", "B")["reason_code"], "effects_not_identifiable")

    def test_fallback_order_including_zero(self):
        row = dict(strict_gap=0., regression_gap_linear=.2, lowconf_gap=.4, regression_gap_curved=.1)
        self.assertEqual(choose_final(row), (0., "strict_gap", "high"))
        row["strict_gap"] = np.nan
        self.assertEqual(choose_final(row), (.2, "regression_gap_linear", "medium"))
        row["regression_gap_linear"] = np.nan
        self.assertEqual(choose_final(row), (.4, "lowconf_gap", "low"))
        row["lowconf_gap"] = np.nan
        self.assertEqual(choose_final(row)[1], "unavailable")

    def test_disagreement_boundary_and_curved(self):
        row = dict(strict_gap=0., regression_gap_linear=.3, lowconf_gap=np.nan,
                   regression_gap_curved=np.nan)
        self.assertFalse(disagreement(row))
        row["regression_gap_curved"] = .30001
        self.assertTrue(disagreement(row))

    def test_curved_model_recovers_known_difference(self):
        data = fixture()
        data.lap_seconds += .004 * data.TyreLife ** 2 - .001 * data.LapNumber ** 2
        result = fit_pair(data, "A", "B", curved=True)
        self.assertAlmostEqual(result["driver_term_seconds"], -.3)
        self.assertEqual(result["reason_code"], "")

    def test_standard_error_matches_independent_ols(self):
        data = fixture()
        rng = np.random.default_rng(42)
        data.lap_seconds += rng.normal(0, .15, len(data))
        result = fit_pair(data, "A", "B")
        x = np.column_stack([np.ones(len(data)), (data.DriverNumber == "A").astype(float),
                             data.TyreLife, data.LapNumber])
        beta = np.linalg.solve(x.T @ x, x.T @ data.lap_seconds)
        residual = data.lap_seconds - x @ beta
        covariance = (residual @ residual / (len(data) - 4)) * np.linalg.inv(x.T @ x)
        self.assertAlmostEqual(result["driver_term_se_seconds"], np.sqrt(covariance[1, 1]))

    def test_nine_clean_laps_keeps_only_unreliable_estimate(self):
        data = fixture()
        data = data.loc[(data.DriverNumber == "B") | (data.LapNumber <= 10)]
        result = fit_pair(data, "A", "B")
        self.assertFalse(result["strategy_confounded"])
        self.assertEqual(result["reason_code"], "too_few_clean_laps")
        self.assertTrue(np.isnan(result["gap_pct"]))
        self.assertTrue(np.isfinite(result["unreliable_gap_pct"]))

    def test_gap_standard_error_includes_reference_uncertainty(self):
        data = fixture()
        data.lap_seconds += np.random.default_rng(7).normal(0, .3, len(data))
        result = fit_pair(data, "A", "B")
        x = np.column_stack([np.ones(len(data)), (data.DriverNumber == "A").astype(float),
                             data.TyreLife, data.LapNumber])
        beta = np.linalg.solve(x.T @ x, x.T @ data.lap_seconds)
        residual = data.lap_seconds - x @ beta
        covariance = (residual @ residual / (len(data) - 4)) * np.linalg.inv(x.T @ x)
        reference = x.mean(axis=0)
        reference[1] = 0
        def percentage(b):
            return 100 * b[1] / (reference @ b)
        step = 1e-5
        gradient = np.array([(percentage(beta + np.eye(4)[i] * step)
                              - percentage(beta - np.eye(4)[i] * step)) / (2 * step)
                             for i in range(4)])
        self.assertAlmostEqual(result["gap_se_pp"], np.sqrt(gradient @ covariance @ gradient))

    def test_mean_comparison_uses_same_pairs(self):
        table = pd.DataFrame({"regression_gap_linear": [-1., 20., np.nan],
                              "regression_gap_curved": [-2., np.nan, 30.]})
        summary = comparison_summary(table)
        self.assertEqual(summary["common_pairs"], 1)
        self.assertEqual(summary["curved_minus_linear_mean_absolute_gap_pp"], 1.)


if __name__ == "__main__":
    unittest.main()
