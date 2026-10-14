"""Focused checks for qualifying-round selection and signed gap calculations."""

import unittest

import pandas as pd

from qualifying_gaps import compare_teammates, prepare_times


def qualifying_fixture():
    results = []
    parts = [[], [], []]
    for index in range(20):
        driver = str(index + 1)
        result = {
            "DriverNumber": driver,
            "Abbreviation": f"D{index:02}",
            "TeamName": f"Team {index // 2:02}",
            "Position": index + 1,
        }
        for number, cutoff in [(1, 20), (2, 15), (3, 10)]:
            time = pd.to_timedelta((81 - number) * 1000 + index * 100, unit="ms")
            result[f"Q{number}"] = time if index < cutoff else pd.NaT
            if index < cutoff:
                parts[number - 1].append({
                    "DriverNumber": driver, "LapTime": time,
                    "Time": pd.to_timedelta(number * 20 + index, unit="min"),
                    "Deleted": False, "PitOutTime": pd.NaT, "PitInTime": pd.NaT,
                })
        results.append(result)
    frames = [pd.DataFrame(part) for part in parts]
    for frame in frames:
        frame["FastF1Generated"] = False
        for name in ["LapTime", "Time", "PitOutTime", "PitInTime"]:
            frame[name] = pd.to_timedelta(frame[name].tolist()).astype("timedelta64[ns]")
    return pd.DataFrame(results), frames


def compare(results, parts, disqualified=None):
    return pd.DataFrame(compare_teammates(
        1, "Example Grand Prix", results, parts, disqualified,
    )).set_index("driver")


class QualifyingGapTests(unittest.TestCase):
    def test_signed_percentage_uses_each_teammates_time(self):
        output = compare(*qualifying_fixture())
        self.assertAlmostEqual(output.loc["D00", "gap_pct"], 100 * (78 - 78.1) / 78.1)
        self.assertAlmostEqual(output.loc["D01", "gap_pct"], 100 * (78.1 - 78) / 78)
        self.assertFalse(output["missing_time"].any())

    def test_latest_shared_round_and_current_team_membership(self):
        results, parts = qualifying_fixture()
        # A changed team entry must change the teammate used for this race.
        results.loc[1, "TeamName"], results.loc[10, "TeamName"] = (
            results.loc[10, "TeamName"], results.loc[1, "TeamName"]
        )
        results.loc[0, "Q1"] = pd.to_timedelta(70, unit="s")
        output = compare(results, parts)
        self.assertEqual(output.loc["D00", "teammate"], "D10")
        self.assertEqual(output.loc["D00", "qualifying_round"], "Q2")
        self.assertEqual(output.loc["D00", "driver_time_seconds"], 79)
        self.assertEqual(output.loc["D00", "driver_best_qualifying_time_seconds"], 70)

    def test_no_q3_time_falls_back_to_q2(self):
        results, parts = qualifying_fixture()
        results.loc[1, "Q3"] = pd.NaT
        parts[2] = parts[2].loc[parts[2]["DriverNumber"].ne("2")]
        output = compare(results, parts)
        self.assertEqual(output.loc["D01", "qualifying_round"], "Q2")
        self.assertIn("driver_no_time_Q3", output.loc["D01", "flag"])
        self.assertFalse(output.loc["D00", "missing_time"])
        self.assertAlmostEqual(output.loc["D01", "gap_pct"], 100 * (79.1 - 79) / 79)

    def test_missing_times_in_q3_and_q2_fall_back_to_q1(self):
        results, parts = qualifying_fixture()
        results.loc[1, ["Q2", "Q3"]] = pd.NaT
        for number in [1, 2]:
            parts[number] = parts[number].loc[parts[number]["DriverNumber"].ne("2")]
        output = compare(results, parts)
        self.assertEqual(output.loc["D01", "qualifying_round"], "Q1")
        self.assertAlmostEqual(output.loc["D01", "gap_pct"], 100 * (80.1 - 80) / 80)

    def test_individual_missing_result_time_is_recovered(self):
        results, parts = qualifying_fixture()
        results.loc[1, "Q3"] = pd.NaT
        output = compare(results, parts)
        self.assertEqual(output.loc["D01", "qualifying_round"], "Q3")
        self.assertEqual(output.loc["D01", "driver_time_source"], "laps")
        self.assertEqual(output.loc["D01", "teammate_time_source"], "results")
        self.assertEqual(output.loc["D01", "time_source"], "mixed")
        self.assertFalse(output.loc["D01", "missing_time"])
        self.assertEqual(output.loc["D01", "flag"], "ok")

    def test_no_time_in_any_round_keeps_both_rows_blank(self):
        results, parts = qualifying_fixture()
        results.loc[0, ["Q1", "Q2", "Q3"]] = pd.NaT
        parts = [part.loc[part["DriverNumber"].ne("1")] for part in parts]
        output = compare(results, parts)
        for driver in ["D00", "D01"]:
            self.assertEqual(output.loc[driver, "qualifying_round"], "")
            self.assertTrue(pd.isna(output.loc[driver, "gap_pct"]))
            self.assertTrue(output.loc[driver, "missing_time"])
            self.assertIn("D00: no valid qualifying lap time", output.loc[driver, "blank_gap_reason"])

    def test_times_in_different_rounds_are_not_compared(self):
        results, parts = qualifying_fixture()
        results.loc[0, ["Q2", "Q3"]] = pd.NaT
        results.loc[1, ["Q1", "Q3"]] = pd.NaT
        parts[0] = parts[0].loc[parts[0]["DriverNumber"].ne("2")]
        parts[1] = parts[1].loc[parts[1]["DriverNumber"].ne("1")]
        parts[2] = parts[2].loc[~parts[2]["DriverNumber"].isin(["1", "2"])]
        output = compare(results, parts)
        self.assertTrue(output.loc["D00", "missing_time"])
        self.assertEqual(output.loc["D00", "qualifying_round"], "")
        self.assertIn("No qualifying round", output.loc["D00", "blank_gap_reason"])

    def test_disqualification_does_not_promote_q1_losers_into_q2(self):
        results, parts = qualifying_fixture()
        # A driver who ran in Q2 loses all classified times afterwards.
        results.loc[14, ["Q1", "Q2", "Q3"]] = pd.NaT
        results.loc[15, "Position"] = 15
        exclusions = {"15": "technical infringement"}
        _, _, _, reached, _, _ = prepare_times(results, parts, disqualified=exclusions)
        self.assertEqual(reached["15"], 2)
        self.assertEqual(reached["16"], 1)
        output = compare(results, parts, disqualified=exclusions)
        self.assertIn("driver_disqualified", output.loc["D14", "flag"])
        self.assertIn("disqualified (technical infringement)", output.loc["D14", "blank_gap_reason"])
        self.assertTrue(pd.isna(output.loc["D14", "gap_pct"]))
        self.assertTrue(pd.isna(output.loc["D14", "driver_best_qualifying_time_seconds"]))

    def test_classified_lap_correction_controls_advancement(self):
        results, parts = qualifying_fixture()
        results.loc[14, "Q1"] = pd.to_timedelta(100, unit="s")
        results.loc[14, "Q2"] = pd.NaT
        _, times, _, reached, sources, _ = prepare_times(results, parts)
        self.assertEqual(reached["15"], 1)
        self.assertEqual(reached["16"], 2)
        # Raw Q2 laps from a driver who lost Q1 advancement are not valid.
        self.assertTrue(pd.isna(times.loc["15", "Q2"]))
        self.assertEqual(sources.loc["15", "Q2"], "missing")

    def test_wholly_missing_result_times_use_laps_and_ignore_deleted_laps(self):
        results, parts = qualifying_fixture()
        expected = compare(results, parts)
        for name in ["Q1", "Q2", "Q3"]:
            results[name] = pd.Series(pd.NaT, index=results.index, dtype="timedelta64[ns]")
        deleted = parts[2].iloc[[0]].copy()
        deleted["LapTime"] = pd.to_timedelta(50, unit="s")
        deleted["Deleted"] = True
        parts[2] = pd.concat([parts[2], deleted], ignore_index=True)
        actual = compare(results, parts)
        self.assertTrue(actual["time_source"].eq("laps").all())
        pd.testing.assert_series_equal(actual["gap_pct"], expected["gap_pct"])

    def test_recovery_rejects_generated_pit_and_nonpositive_laps(self):
        results, parts = qualifying_fixture()
        results.loc[1, "Q3"] = pd.NaT
        original = parts[2].loc[parts[2]["DriverNumber"].eq("2")].copy()
        parts[2] = parts[2].loc[parts[2]["DriverNumber"].ne("2")]
        bad = []
        for column, value in [
            ("FastF1Generated", True),
            ("PitInTime", pd.to_timedelta(1, unit="s")),
            ("PitOutTime", pd.to_timedelta(1, unit="s")),
            ("LapTime", pd.to_timedelta(0, unit="s")),
            ("Deleted", True),
        ]:
            lap = original.copy()
            lap[column] = value
            bad.append(lap)
        parts[2] = pd.concat([parts[2], *bad], ignore_index=True)
        output = compare(results, parts)
        self.assertEqual(output.loc["D01", "qualifying_round"], "Q2")
        self.assertIn("driver_no_time_Q3", output.loc["D01", "flag"])


if __name__ == "__main__":
    unittest.main()
