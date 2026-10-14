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
    return pd.DataFrame(results), [pd.DataFrame(part) for part in parts]


def compare(results, parts):
    return pd.DataFrame(compare_teammates(1, "Example Grand Prix", results, parts)).set_index("driver")


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

    def test_no_time_after_advancement_does_not_fall_back(self):
        results, parts = qualifying_fixture()
        results.loc[1, "Q3"] = pd.NaT
        parts[2] = parts[2].loc[parts[2]["DriverNumber"].ne("2")]
        output = compare(results, parts)
        self.assertEqual(output.loc["D01", "qualifying_round"], "Q3")
        self.assertIn("driver_no_time_Q3", output.loc["D01", "flag"])
        self.assertTrue(output.loc["D00", "missing_time"])
        self.assertTrue(pd.isna(output.loc["D01", "gap_pct"]))

    def test_disqualification_does_not_promote_q1_losers_into_q2(self):
        results, parts = qualifying_fixture()
        # A driver who ran in Q2 loses all classified times afterwards.
        results.loc[14, ["Q1", "Q2", "Q3"]] = pd.NaT
        results.loc[15, "Position"] = 15
        _, _, _, reached, _ = prepare_times(results, parts)
        self.assertEqual(reached["15"], 2)
        self.assertEqual(reached["16"], 1)
        output = compare(results, parts)
        self.assertIn("time_absent_from_results", output.loc["D14", "flag"])
        self.assertTrue(pd.isna(output.loc["D14", "gap_pct"]))

    def test_classified_lap_correction_controls_advancement(self):
        results, parts = qualifying_fixture()
        results.loc[14, "Q1"] = pd.to_timedelta(100, unit="s")
        results.loc[14, "Q2"] = pd.NaT
        parts[1] = parts[1].loc[parts[1]["DriverNumber"].ne("15")]
        _, _, _, reached, _ = prepare_times(results, parts)
        self.assertEqual(reached["15"], 1)
        self.assertEqual(reached["16"], 2)

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


if __name__ == "__main__":
    unittest.main()
