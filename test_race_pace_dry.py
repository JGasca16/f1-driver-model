"""Tests for the standalone method and its saved offline results."""
import ast
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

import numpy as np
import pandas as pd

import race_pace_dry as dry

ROOT = Path(__file__).resolve().parent
KEYS = ["round_number", "race", "team", "driver", "teammate"]


def read_output(name):
    return pd.read_csv(ROOT / "data" / name, float_precision="round_trip").set_index(KEYS).sort_index()


def sample_laps():
    # Four laps in the first stint exercise the shorter-than-five case.
    rows = []
    for driver in ["1", "2"]:
        for stint, length in [(1, 4), (2, 8), (3, 11)]:
            for age in range(1, length + 1):
                lap = 15 * (stint-1) + age + (driver == "2")
                seconds = 90 + 0.3 * (driver == "1") + 0.05 * age - 0.01 * lap + 0.1 * np.sin(lap)
                rows.append(dict(DriverNumber=driver, Stint=stint, LapNumber=lap,
                                 Compound="MEDIUM", TyreLife=age, lap_seconds=seconds))
    return pd.DataFrame(rows)


class StandaloneDryTests(unittest.TestCase):
    def test_repeat_runs_preserve_existing_outputs(self):
        for existing in ["race_pace_dry_final.csv", "race_pace_dry_run_summary.json"]:
            with self.subTest(existing=existing), TemporaryDirectory() as folder:
                root = Path(folder)
                paths = dry.output_paths(root)
                self.assertEqual(paths[0].parent, root)
                (root / existing).write_text("original result")
                first = dry.output_paths(root)
                second = dry.output_paths(root)
                self.assertEqual(first[0].parent, root / "runs/dry_001")
                self.assertEqual(second[0].parent, root / "runs/dry_002")
                self.assertEqual((root / existing).read_text(), "original result")
                self.assertTrue(first[0].parent.is_dir())

    def test_point_parity_with_v3(self):
        actual = read_output("race_pace_dry_final.csv")
        old = read_output("race_pace_dry_combined_v3.csv")
        self.assertTrue(actual.index.is_unique and actual.index.equals(old.index))
        for new, previous in [("strict_gap", "strict_gap"), ("linear_gap", "regression_gap_linear"), ("final_gap", "final_gap")]:
            pd.testing.assert_series_equal(actual[new], old[previous], check_names=False, check_exact=True)

    def test_errors_and_intervals_match_v3(self):
        actual, old = read_output("race_pace_dry_final.csv"), read_output("race_pace_dry_combined_v3.csv")
        for new, previous in [("strict_se_pp", "strict_gap_se_pp"), ("linear_se_pp", "regression_gap_linear_se_block_pp"),
                              ("strict_ci_low", "strict_gap_ci_low"), ("strict_ci_high", "strict_gap_ci_high"),
                              ("linear_ci_low", "regression_gap_linear_ci_low"), ("linear_ci_high", "regression_gap_linear_ci_high")]:
            np.testing.assert_allclose(actual[new], old[previous], rtol=0, atol=1e-6, equal_nan=True)

    def test_final_gap_equals_v1(self):
        actual, old = read_output("race_pace_dry_final.csv"), read_output("race_pace_dry_combined.csv")
        self.assertTrue(actual.index.equals(old.index))
        pd.testing.assert_series_equal(actual.final_gap, old.final_gap, check_exact=True)

    def test_strict_seed_is_repeatable(self):
        values = np.sin(np.arange(31)) + np.arange(31) / 10
        self.assertEqual(dry.strict_bootstrap(values, seed=42), dry.strict_bootstrap(values, seed=42))
        self.assertNotEqual(dry.strict_bootstrap(values, seed=42), dry.strict_bootstrap(values, seed=43))

    def test_regression_seed_is_repeatable(self):
        frame = sample_laps()
        first = dry.linear_bootstrap(frame, "1", seed=42)
        self.assertEqual(first, dry.linear_bootstrap(frame, "1", seed=42))
        self.assertGreater(first["valid"], 1)

    def test_short_stint_kept_and_does_not_crash(self):
        frame = sample_laps()
        groups = dry.stint_blocks(frame)
        self.assertEqual([len(chunk) for chunk in groups[0]], [4])
        result = dry.linear_bootstrap(frame, "1")
        self.assertTrue(np.isfinite(result["se"]))
        self.assertEqual(result["attempted"], 2000)
        self.assertEqual(result["valid"] + result["skipped"], 2000)

    def test_confidence_boundaries(self):
        for gap, se, count, label in [(0, .15, 20, "high"), (0, .15, 19, "medium"),
                (.2, .30, 10, "medium"), (.2, .300001, 50, "low"), (.2, .01, 9, "low"),
                (.2, np.nan, 30, "low"), (np.nan, .01, 100, "unavailable")]:
            with self.subTest(se=se, count=count):
                self.assertEqual(dry.confidence(gap, se, count), label)

    def test_strict_first_including_zero(self):
        self.assertEqual(dry.choose_final(0., -.4), (0., "strict"))
        self.assertEqual(dry.choose_final(np.nan, -.4), (-.4, "linear"))
        gap, method = dry.choose_final(np.nan, np.nan)
        self.assertTrue(np.isnan(gap))
        self.assertEqual(method, "unavailable")

    def test_disagreement_threshold_and_missing_errors(self):
        # SEs .3 and .4 make the threshold exactly 1 percentage point.
        self.assertFalse(dry.disagreement(0, .3, 1, .4))
        self.assertTrue(dry.disagreement(0, .3, 1.00001, .4))
        self.assertFalse(dry.disagreement(-.2, .1, -.1, .1))
        self.assertIsNone(dry.disagreement(0, np.nan, 1, .4))
        self.assertIsNone(dry.disagreement(np.nan, .3, 1, .4))

    def test_gap_sign_and_strategy_gate(self):
        frame = sample_laps()
        frame["lap_seconds"] = np.where(frame.DriverNumber.eq("1"), 90., 90.3)
        gap, reason = dry.fit_linear(frame, "1", "2")
        self.assertEqual(reason, "")
        self.assertAlmostEqual(gap, 100 * (90 - 90.3) / 90.3, places=10)
        frame.loc[frame.DriverNumber.eq("2"), "Compound"] = "HARD"
        gap, reason = dry.fit_linear(frame, "1", "2")
        self.assertTrue(np.isnan(gap))
        self.assertEqual(reason, "strategy_confounded")

    def test_schema_exclusions_and_no_old_imports(self):
        output = pd.read_csv(ROOT / "data/race_pace_dry_final.csv")
        self.assertEqual(list(output.columns), dry.COLUMNS)
        self.assertEqual(len(output), 200)
        self.assertFalse(output.round_number.isin([1, 6, 12, 13]).any())
        self.assertEqual(output.track_reliability_flag.notna().sum(), 10)
        self.assertTrue(output.loc[output.track_reliability_flag.notna(), "race"].eq("Monaco Grand Prix").all())
        tree = ast.parse((ROOT / "race_pace_dry.py").read_text())
        imports = [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
        imports += [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        self.assertFalse(any(name and name.startswith(("race_pace_", "diagnose_")) for name in imports))

    def test_all_rule_export_has_twelve_pairs(self):
        output = pd.read_csv(ROOT / "data/race_pace_dry_all_rule_disagreements.csv")
        self.assertEqual(len(output), 12)
        self.assertFalse(output.duplicated(["race", "driver", "teammate"]).any())


if __name__ == "__main__":
    unittest.main()
