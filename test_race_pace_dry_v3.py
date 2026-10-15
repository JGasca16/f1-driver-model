"""Determinism, preservation and fixed-rule checks for v3."""
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

import race_pace_dry_v2 as v2
from race_pace_dry_v3 import (regression_bootstrap, short_bootstrap, stint_blocks,
                             untestable_reason, BootstrapClock)
from test_race_pace_regression import fixture


def sample_laps():
    data = fixture()
    data["Stint"] = np.where(data.LapNumber <= 4, 1, 2)
    data.lap_seconds += np.random.default_rng(7).normal(0, .2, len(data))
    return data


class DryV3Tests(unittest.TestCase):
    def test_saved_final_gaps_equal_v1_for_every_pair(self):
        root = Path(__file__).resolve().parent
        target = root / "data/race_pace_dry_combined_v3.csv"
        if not target.exists():
            self.skipTest("Run integration check again after first export")
        a = pd.read_csv(root / "data/race_pace_dry_combined.csv", float_precision="round_trip")
        b = pd.read_csv(target, float_precision="round_trip")
        columns = ["round_number", "team", "driver", "teammate", "final_gap", "method_used"]
        pd.testing.assert_frame_equal(a[columns], b[columns], check_exact=True)

    def test_regression_bootstrap_repeats_with_same_seed(self):
        a = regression_bootstrap(sample_laps(), "A", "B", seed=42)
        b = regression_bootstrap(sample_laps(), "A", "B", seed=42)
        self.assertEqual(a, b)
        self.assertEqual(a["resamples_attempted"], 2000)
        self.assertEqual(a["resamples_valid"] + a["resamples_skipped"], 2000)
        self.assertTrue(np.isfinite(a["regression_gap_linear_se_block_pp"]))

    def test_short_bootstrap_repeats_with_same_seed(self):
        self.assertEqual(short_bootstrap([.1, .5, -.2], 42), short_bootstrap([.1, .5, -.2], 42))
        constant = short_bootstrap([.3]*3)
        self.assertAlmostEqual(constant[0], 0.)
        self.assertEqual(constant[1:], (.3, .3, ""))

    def test_stint_shorter_than_five_is_one_block(self):
        groups = stint_blocks(sample_laps())
        short = [g for g in groups if sum(len(b) for b in g) == 3]
        self.assertEqual(len(short), 2)
        self.assertTrue(all(len(g) == 1 and len(g[0]) == 3 for g in short))
        result = regression_bootstrap(sample_laps(), "A", "B")
        self.assertEqual(result["resamples_attempted"], 2000)

    def test_confidence_thresholds_unchanged(self):
        for se, laps, answer in [(.15, 20, "high"), (.150001, 20, "medium"),
                                  (.30, 10, "medium"), (.300001, 20, "low"),
                                  (.01, 9, "low"), (np.nan, 25, "low")]:
            self.assertEqual(v2.confidence(.2, se, laps), answer)
        self.assertEqual(v2.confidence(np.nan, .1, 20), "unavailable")

    def test_every_lowconf_gap_has_short_error_or_reason(self):
        target = Path(__file__).resolve().parent / "data/race_pace_dry_combined_v3.csv"
        if not target.exists():
            self.skipTest("Run integration check again after first export")
        data = pd.read_csv(target)
        low = data.loc[data.lowconf_gap.notna()]
        self.assertEqual(len(low), 12)
        self.assertTrue((low.lowconf_gap_se_pp_v3.notna() | low.lowconf_gap_se_reason_code_v3.notna()).all())
        self.assertTrue(low.lowconf_se_method.eq("block2").all())

    def test_untestable_reasons_are_exclusive(self):
        row = {key: np.nan for item in v2.METHOD_ERRORS.items() for key in item}
        self.assertEqual(untestable_reason(row, False), "no_gap_at_all")
        row.update(strict_gap=.1, strict_gap_se_pp=.1)
        self.assertEqual(untestable_reason(row, False), "only_one_estimate_available")
        row["lowconf_gap"] = .2
        self.assertEqual(untestable_reason(row, False), "estimate_missing_error")
        row["lowconf_gap_se_pp"] = .1
        self.assertEqual(untestable_reason(row, False), "")

    def test_runtime_limit_raises_without_lowering_resamples(self):
        clock = BootstrapClock()
        clock.check()
        clock.start -= 901
        with self.assertRaises(TimeoutError):
            clock.check()


if __name__ == "__main__":
    unittest.main()
