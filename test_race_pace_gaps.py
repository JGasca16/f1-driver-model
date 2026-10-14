"""Tests of matching, safety filters, missing results, and sensitivity."""

import unittest

import pandas as pd

from race_pace_gaps import (
    RaceData, build_roster, dry_race_status, filter_clean_laps,
    paired_rows, sensitivity_tables,
)


def fixture(count=12, teammate="BBB", second_age_offset=0):
    roster = pd.DataFrame([
        {"DriverNumber": "1", "Abbreviation": "AAA", "TeamName": "Team", "Status": "Finished"},
        {"DriverNumber": "2", "Abbreviation": teammate, "TeamName": "Team", "Status": "Finished"},
    ])
    records = []
    for driver, seconds in [("1", 90.0), ("2", 90.3)]:
        for lap in range(1, count + 2):
            records.append({
                "DriverNumber": driver, "LapNumber": float(lap),
                "LapTime": pd.to_timedelta(seconds, unit="s"),
                "LapStartTime": pd.to_timedelta((lap - 1) * seconds, unit="s"),
                "Time": pd.to_timedelta(lap * seconds, unit="s"),
                "PitInTime": pd.NaT, "PitOutTime": pd.NaT,
                "TrackStatus": "1", "Deleted": False, "IsAccurate": True,
                "FastF1Generated": False, "Compound": "MEDIUM",
                "TyreLife": lap + (second_age_offset if driver == "2" else 0),
            })
    laps = pd.DataFrame(records)
    for col in ["PitInTime", "PitOutTime"]:
        laps[col] = pd.Series(pd.NaT, index=laps.index, dtype="timedelta64[ns]")
    end = laps["Time"].max()
    weather = pd.DataFrame({
        "Time": pd.to_timedelta(range(0, int(end.total_seconds()) + 61, 60), unit="s"),
        "Rainfall": False,
    })
    return RaceData(1, "Example Grand Prix", roster, laps, weather, pd.to_timedelta(0, unit="s"), end)


def output(race, tolerance=3):
    return pd.DataFrame(paired_rows(race, tolerance)).set_index("driver", drop=False)


class RacePaceTests(unittest.TestCase):
    def test_90_vs_90_3_signed_example(self):
        result = output(fixture())
        self.assertAlmostEqual(result.loc["AAA", "gap_pct"], -0.33222591362126245)
        self.assertAlmostEqual(result.loc["BBB", "gap_pct"], 0.33333333333333015)
        self.assertEqual(result.loc["AAA", "matched_laps"], 12)
        self.assertEqual(result.loc["AAA", "blank_gap_reason"], "")

    def test_midseason_driver_swap_uses_current_race_roster(self):
        early = output(fixture(teammate="BBB"))
        later = output(fixture(teammate="CCC"))
        self.assertEqual(early.loc["AAA", "teammate"], "BBB")
        self.assertEqual(later.loc["AAA", "teammate"], "CCC")
        self.assertNotIn("BBB", later.index)

    def test_too_few_laps_and_exact_threshold(self):
        short = output(fixture(count=9))
        self.assertTrue(short["gap_pct"].isna().all())
        self.assertTrue(short["reason_code"].eq("too_few_matched_laps").all())
        self.assertIn("Only 9 matched laps; need 10", short.iloc[0]["blank_gap_reason"])
        self.assertTrue(output(fixture(count=10))["gap_pct"].notna().all())

    def test_lap_one_pit_laps_and_extra_warmup_lap(self):
        race = fixture()
        race.laps.loc[race.laps.LapNumber.eq(5), "PitInTime"] = pd.to_timedelta(1, unit="s")
        race.laps.loc[race.laps.LapNumber.eq(6), "PitOutTime"] = pd.to_timedelta(1, unit="s")
        kept = set(filter_clean_laps(race.laps).LapNumber)
        self.assertFalse(kept.intersection({1, 5, 6, 7}))
        self.assertIn(8, kept)

    def test_sc_vsc_and_red_flags_include_first_fully_green_lap(self):
        for status in ["4", "6", "7", "5"]:
            with self.subTest(status=status):
                race = fixture()
                race.laps.loc[race.laps.LapNumber.eq(4), "TrackStatus"] = status
                race.laps.loc[race.laps.LapNumber.eq(5), "TrackStatus"] = "12"
                kept = set(filter_clean_laps(race.laps).LapNumber)
                self.assertFalse(kept.intersection({4, 5, 6}))
                self.assertIn(7, kept)

    def test_yellow_deleted_inaccurate_generated_unknown_and_duplicate_laps(self):
        race = fixture()
        race.laps.loc[race.laps.LapNumber.eq(3), "TrackStatus"] = "12"
        race.laps.loc[race.laps.LapNumber.eq(5), "Deleted"] = True
        race.laps.loc[race.laps.LapNumber.eq(6), "IsAccurate"] = False
        race.laps.loc[race.laps.LapNumber.eq(7), "FastF1Generated"] = True
        race.laps.loc[race.laps.LapNumber.eq(8), "TyreLife"] = float("nan")
        race.laps.loc[race.laps.LapNumber.eq(9), "Compound"] = "UNKNOWN"
        race.laps = pd.concat([race.laps, race.laps.loc[race.laps.LapNumber.eq(10)]], ignore_index=True)
        kept = set(filter_clean_laps(race.laps).LapNumber)
        self.assertFalse(kept.intersection({3, 5, 6, 7, 8, 9, 10}))
        self.assertIn(4, kept)  # No extra restart buffer for a yellow alone.

    def test_same_compound_and_same_lap_are_required(self):
        race = fixture()
        race.laps.loc[race.laps.DriverNumber.eq("2"), "Compound"] = "HARD"
        self.assertEqual(output(race).iloc[0]["matched_laps"], 0)
        race = fixture()
        race.laps.loc[race.laps.DriverNumber.eq("2"), "LapNumber"] += 50
        self.assertEqual(output(race).iloc[0]["matched_laps"], 0)

    def test_tolerance_and_sensitivity_coverage(self):
        race = fixture(second_age_offset=3)
        outputs = {tol: output(race, tol).reset_index(drop=True) for tol in [2, 3, 5]}
        self.assertEqual(outputs[2].iloc[0]["matched_laps"], 0)
        self.assertEqual(outputs[3].iloc[0]["matched_laps"], 12)
        summary, details = sensitivity_tables(outputs)
        summary = summary.set_index("tyre_age_tolerance")
        self.assertEqual(summary.loc[2, "lost_pairs_vs_3"], 1)
        self.assertEqual(summary.loc[5, "max_abs_change_pp"], 0)
        self.assertEqual(len(details), 1)

    def test_sensitivity_reports_percentage_points_and_sign_change(self):
        race = fixture(count=20, second_age_offset=2)
        later = race.laps.LapNumber.gt(11)
        race.laps.loc[later & race.laps.DriverNumber.eq("2"), "TyreLife"] += 3
        race.laps.loc[later & race.laps.DriverNumber.eq("1"), "LapTime"] = pd.to_timedelta(92, unit="s")
        outputs = {tol: output(race, tol).reset_index(drop=True) for tol in [2, 3, 5]}
        summary, _ = sensitivity_tables(outputs)
        summary = summary.set_index("tyre_age_tolerance")
        expected_change = 100 * (91 - 90) / 90.3
        self.assertAlmostEqual(summary.loc[5, "max_abs_change_pp"], expected_change)
        self.assertAlmostEqual(summary.loc[5, "mean_abs_change_pp"], expected_change)
        self.assertEqual(summary.loc[5, "sign_flips_vs_3"], 1)
        self.assertEqual(summary.loc[5, "common_pairs_vs_3"], 1)

    def test_weather_rain_or_wet_tyres_exclude_entire_race(self):
        race = fixture()
        race.weather.loc[2, "Rainfall"] = True
        self.assertTrue(output(race)["reason_code"].eq("wet_race").all())
        race = fixture()
        race.laps.loc[2, "Compound"] = "INTERMEDIATE"
        self.assertTrue(output(race)["reason_code"].eq("wet_race").all())

    def test_weather_outside_race_is_ignored_and_missing_coverage_is_unknown(self):
        race = fixture()
        race.weather.loc[race.weather.Time.gt(race.end), "Rainfall"] = True
        self.assertEqual(dry_race_status(race.laps, race.weather, race.start, race.end)[0], "dry")
        race.weather = race.weather.iloc[[0, -2]]
        self.assertTrue(output(race)["reason_code"].eq("dry_status_unknown").all())
        race.weather = pd.DataFrame()
        self.assertTrue(output(race)["reason_code"].eq("dry_status_unknown").all())

    def test_no_race_laps_and_disqualification(self):
        race = fixture()
        race.laps = race.laps.loc[race.laps.DriverNumber.eq("1")]
        self.assertTrue(output(race)["reason_code"].eq("no_race_laps").all())
        race = fixture()
        race.roster.loc[1, "Status"] = "Disqualified"
        self.assertTrue(output(race)["reason_code"].eq("race_disqualification").all())

    def test_qualifying_roster_only_fills_absent_race_entries(self):
        race = fixture()
        roster = build_roster(race.roster.iloc[:1], race.roster)
        self.assertEqual(len(roster), 2)
        self.assertEqual(roster.loc[roster.Abbreviation.eq("AAA"), "Status"].iloc[0], "Finished")
        self.assertEqual(roster.loc[roster.Abbreviation.eq("BBB"), "Status"].iloc[0], "Absent from race results")

    def test_missing_cache_is_explained_and_slow_laps_are_not_automatically_removed(self):
        race = fixture()
        race.issue = "Missing cached timing data"
        result = output(race)
        self.assertTrue(result["gap_pct"].isna().all())
        self.assertTrue(result["blank_gap_reason"].eq(race.issue).all())
        race = fixture()
        race.laps.loc[(race.laps.DriverNumber == "1") & (race.laps.LapNumber == 3), "LapTime"] = pd.to_timedelta(110, unit="s")
        result = output(race)
        self.assertEqual(result.iloc[0]["matched_laps"], 12)
        self.assertAlmostEqual(result.loc["AAA", "gap_pct"], -0.33222591362126245)


if __name__ == "__main__":
    unittest.main()
