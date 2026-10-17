"""Synthetic checks for the approved weights, symmetry and evidence rules."""
import itertools
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

import driver_rating as ratings
import qualifying_gaps_combined as quali


def season_fixture(wet_only=False):
    """Two drivers across eight weekends, with a linked pair at each event."""
    records, roster = [], []
    for number in range(1, 9):
        for driver, opponent, sign in [("AAA", "BBB", -1), ("BBB", "AAA", 1)]:
            roster.append({"round_number": number, "race": f"Race {number}", "team": "Team",
                           "driver": driver, "teammate": opponent, "period": 1})
            for signal in ratings.SIGNALS:
                valid = not wet_only or signal == "wet"
                records.append({"round_number": number, "race": f"Race {number}", "team": "Team",
                    "driver": driver, "teammate": opponent, "signal": signal, "period": 1,
                    "contribution": sign * (number / 10) if valid else np.nan, "se_log": .1,
                    "reason_code": "" if valid else "missing", "warnings": "", "method_used": "strict",
                    "race_ci_low": -1., "race_ci_high": 1.})
    return pd.DataFrame(records), pd.DataFrame(roster)


class DriverRatingTests(unittest.TestCase):
    def test_round_weights_every_missing_round_case(self):
        values = {"q1": 1., "q2": 2., "q3": 4.}
        for mask in itertools.product([False, True], repeat=3):
            data = {key: values[key] if present else "" for key, present in zip(values, mask)}
            with self.subTest(mask=mask):
                gap, used, reason = quali.combine_rounds(data)
                kept = [key for key, flag in zip(values, mask) if flag]
                if not kept:
                    self.assertTrue(np.isnan(gap))
                    self.assertEqual(reason, "no_valid_round")
                else:
                    expected = sum(values[key] * quali.ROUND_WEIGHTS[key] for key in kept) / sum(quali.ROUND_WEIGHTS[key] for key in kept)
                    self.assertAlmostEqual(gap, expected)
                    self.assertEqual(reason, "")
                    self.assertIn(kept[0].upper(), used)
        self.assertAlmostEqual(quali.combine_rounds({"q1": 1, "q2": 2})[0], 1.6)
        self.assertEqual(quali.combine_rounds(values)[1], "Q3+Q2+Q1")

    def test_log_conversion_exactly_symmetric_and_error_correct(self):
        gap = 100 * (90 - 90.3) / 90.3
        a, b, se = ratings.log_pair(gap, .2)
        self.assertEqual(a, -b)
        self.assertLess(a, 0)
        self.assertAlmostEqual(a, 100 * np.log(90 / 90.3))
        self.assertAlmostEqual(se, .2 / (1 + gap / 100))
        self.assertAlmostEqual(ratings.log_pair(-100 * gap / (100 + gap))[0], b)

    def test_invalid_gaps_are_rejected_not_treated_as_missing(self):
        for gap in [-100, -101, float("nan"), float("inf"), "NaN", "inf", "oops"]:
            with self.subTest(gap=gap):
                with self.assertRaises(quali.InvalidGap):
                    ratings.log_pair(gap)
        self.assertTrue(np.isnan(ratings.log_pair("")[0]))
        result = quali.combine_rounds({"q1": -100, "q2": .5})
        self.assertTrue(np.isnan(result[0]))
        self.assertIn("invalid_gap", result[2])

    def test_evidence_factor_zero_partial_full(self):
        np.testing.assert_array_equal(ratings.evidence_factor(np.array([0, 4, 8, 16]), 8), [0, .5, 1, 1])
        self.assertEqual(ratings.evidence_factor(1.5, 3), .5)

    def test_monaco_multiplier_only_dry_only_monaco(self):
        default, no_discount = ratings.Settings(), ratings.Settings(monaco_multiplier=1)
        for signal in ratings.SIGNALS:
            for race in ["Monaco Grand Prix", "Chinese Grand Prix"]:
                with self.subTest(signal=signal, race=race):
                    base = ratings.observation_weight(signal, .15, race, no_discount)
                    weight = ratings.observation_weight(signal, .15, race, default)
                    self.assertEqual(weight, base * (.5 if signal == "dry" and race == "Monaco Grand Prix" else 1))

    def test_confidence_boundaries_and_ci_gate(self):
        for args, expected in [
            ((0., 12, 12, .75, .75, True), "high"),
            ((0., 12, 11.9, .75, .75, True), "medium"),
            ((0., 6, 6, .50, .50, True), "medium"),
            ((0., 5.99, 6, 1., 1., True), "low/provisional"),
            ((0., 20, 20, .749, 1., True), "medium"),
            ((0., 20, 20, 1., 1., False), "low/provisional"),
            ((np.nan, 20, 20, 1., 1., True), "unavailable"),
        ]:
            with self.subTest(args=args):
                self.assertEqual(ratings.confidence_label(*args), expected)

    def test_weekend_bootstrap_reproducible_and_pair_symmetric(self):
        observations, roster = season_fixture()
        first, _, _ = ratings.build_ratings(observations, roster, resamples=200, seed=42)
        second, _, _ = ratings.build_ratings(observations, roster, resamples=200, seed=42)
        pd.testing.assert_frame_equal(first, second)
        a, b = first.iloc[0], first.iloc[1]
        self.assertEqual(a.combined_rating, -b.combined_rating)
        self.assertAlmostEqual(a.combined_ci_low, -b.combined_ci_high)
        self.assertAlmostEqual(a.combined_ci_high, -b.combined_ci_low)
        counts = ratings.weekend_draws(8, 200, 42)
        self.assertTrue(np.all(counts.sum(axis=1) == 8))

    def test_no_qualifying_or_dry_is_unavailable_even_with_wet(self):
        observations, roster = season_fixture(wet_only=True)
        table, _, _ = ratings.build_ratings(observations, roster, resamples=100)
        self.assertTrue(table.rating_status.eq("unavailable").all())
        self.assertTrue(table.confidence.eq("unavailable").all())
        self.assertTrue(table.combined_rating.isna().all())
        self.assertTrue(table.wet_rating.notna().all())

    def test_missing_se_uses_floor_and_missing_races_are_not_zero(self):
        self.assertEqual(ratings.observation_weight("dry", np.nan, "Race"), .25)
        observations, _ = season_fixture()
        group = ratings.add_weights(observations.loc[(observations.driver == "AAA") & (observations.signal == "qualifying")])
        group.loc[group.round_number > 2, "contribution"] = np.nan
        group.loc[group.round_number > 2, "reason_code"] = "missing"
        summary = ratings.summarize_signal(group)
        self.assertEqual(summary["valid"], 2)
        self.assertEqual(summary["missing"], 6)
        self.assertEqual(summary["coverage"], .25)
        self.assertAlmostEqual(summary["rating"], -.15)
        self.assertEqual(summary["effective_races"], 2)

    def test_ci_requires_six_distinct_original_weekends_and_95_percent(self):
        values = np.arange(2000, dtype=float)
        self.assertEqual(ratings.bootstrap_ci(values, 5)[3], "insufficient_evidence")
        values[:100] = np.nan
        self.assertEqual(ratings.bootstrap_ci(values, 6)[3], "")
        values[100] = np.nan
        self.assertEqual(ratings.bootstrap_ci(values, 6)[3], "insufficient_evidence")

    def test_single_wet_observation_keeps_race_interval_not_season_interval(self):
        observations, roster = season_fixture()
        observations.loc[(observations.signal == "wet") & (observations.round_number > 1), "contribution"] = np.nan
        _, diagnostic, _ = ratings.build_ratings(observations, roster, resamples=200)
        wet = diagnostic.loc[diagnostic.signal == "wet"]
        self.assertTrue(wet.season_ci_low.isna().all())
        self.assertTrue(wet.single_race_ci_low.notna().all())
        self.assertTrue(wet.season_ci_reason.eq("single_race_evidence").all())

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.csv"
            quali.write_csv_new(pd.DataFrame({"a": [1]}), path)
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                quali.write_csv_new(pd.DataFrame({"a": [2]}), path)
            self.assertEqual(path.read_bytes(), before)

    def test_invalid_source_pair_is_flagged_on_both_sides(self):
        source, dry, wet = [quali.read_csv(ratings.ROOT / path) for path in ratings.SOURCES]
        roster = ratings.check_roster(source)
        # A nonfinite race gap is rejected, while its missing-evidence record remains.
        index = dry.loc[dry.final_gap.ne("")].index[0]
        pair = dry.loc[index]
        dry.loc[index, "final_gap"] = "NaN"
        observations, audit, _ = ratings.make_observations(source, quali.combine_table(source), dry, wet, roster)
        rejected = observations.loc[(observations.signal == "dry") &
                                    (observations.round_number == int(pair.round_number)) &
                                    observations.driver.isin([pair.driver, pair.teammate])]
        self.assertEqual(len(rejected), 2)
        self.assertTrue(rejected.contribution.isna().all())
        self.assertTrue(rejected.reason_code.eq("invalid_gap_nonfinite").all())
        self.assertEqual(len(audit), 1)
        self.assertEqual(audit.iloc[0].value, "NaN")
        # An invalid reverse qualifying row must not be ignored either.
        source.loc[0, "q1_gap"] = "NaN"
        observations, audit, _ = ratings.make_observations(source, quali.combine_table(source), dry, wet, roster)
        self.assertEqual(len(audit), 2)

    def test_approved_swap_periods_and_missing_eligibility(self):
        source = quali.read_csv(ratings.ROOT / ratings.SOURCES[0])
        roster = ratings.check_roster(source)
        self.assertEqual(roster.loc[roster.driver.eq("DOO")].shape[0], 6)
        self.assertEqual(roster.loc[roster.driver.eq("COL")].shape[0], 18)
        for driver, expected in [("LAW", [(1, 2, "VER"), (3, 24, "HAD")]),
                                 ("GAS", [(1, 6, "DOO"), (7, 24, "COL")])]:
            actual = [(g.round_number.min(), g.round_number.max(), g.teammate.iloc[0])
                      for _, g in roster.loc[roster.driver.eq(driver)].groupby("period")]
            self.assertEqual(actual, expected)
        self.assertEqual(roster.loc[roster.driver.eq("DOO") & roster.round_number.isin(ratings.DRY_ROUNDS)].shape[0], 4)


if __name__ == "__main__":
    unittest.main()
