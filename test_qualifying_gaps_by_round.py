"""Round-specific qualifying checks, plus exact parity with the old export."""
import ast
from pathlib import Path
import unittest
from unittest.mock import Mock

import pandas as pd
import qualifying_gaps_by_round as rounds

ROOT = Path(__file__).resolve().parent

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
    return pd.DataFrame(rounds.compare_by_round(1, "Example Grand Prix", results, parts, disqualified)).set_index("driver")


class QualifyingByRoundTests(unittest.TestCase):
    def test_q1_elimination_leaves_later_rounds_blank(self):
        output = compare(*qualifying_fixture())
        for driver in ["D18", "D19"]:
            self.assertTrue(pd.notna(output.loc[driver, "q1_gap"]))
            for name in ["q2", "q3"]:
                self.assertTrue(pd.isna(output.loc[driver, f"{name}_gap"]))
                self.assertEqual(output.loc[driver, f"{name}_reason_code"], "eliminated_prior_round")

    def test_sign_convention_each_round(self):
        output = compare(*qualifying_fixture())
        for name, faster in [("q1", 80.), ("q2", 79.), ("q3", 78.)]:
            self.assertAlmostEqual(output.loc["D00", f"{name}_gap"], 100 * (faster-(faster+.1)) / (faster+.1))
            self.assertAlmostEqual(output.loc["D01", f"{name}_gap"], 100 * ((faster+.1)-faster) / faster)
        self.assertEqual(output.loc["D00", "selected_gap"], output.loc["D00", "q3_gap"])

    def test_sprint_weekend_loads_only_main_qualifying(self):
        event = Mock()
        event.EventFormat = "sprint_qualifying"
        session = rounds.load_qualifying(event)
        event.get_session.assert_called_once_with("Q")
        self.assertIs(session, event.get_session.return_value)
        session.load.assert_called_once_with(laps=True, telemetry=False, weather=False, messages=True)

    def test_exact_selected_and_all_legacy_column_parity(self):
        new = pd.read_csv(ROOT / "data/2025_qualifying_gaps_by_round.csv", float_precision="round_trip")
        old = pd.read_csv(ROOT / "data/2025_qualifying_teammate_gaps.csv", float_precision="round_trip")
        rounds.verify_parity(new, old)
        self.assertEqual(len(new), 480)
        self.assertEqual(new.groupby(["round_number", "team"]).ngroups, 240)
        for name in ["q1", "q2", "q3"]:
            self.assertTrue(new[f"{name}_gap"].notna().eq(new[f"{name}_reason_code"].isna()).all())

    def test_reached_round_without_lap(self):
        results, parts = qualifying_fixture()
        results.loc[1, "Q3"] = pd.NaT
        parts[2] = parts[2].loc[parts[2].DriverNumber.ne("2")]
        output = compare(results, parts)
        self.assertEqual(output.loc["D00", "q3_reason_code"], "no_valid_lap")
        self.assertEqual(output.loc["D00", "q3_teammate_reason"], "no_valid_lap")
        self.assertEqual(output.loc["D00", "selected_round"], "Q2")

    def test_miami_style_recovery_all_rounds(self):
        results, parts = qualifying_fixture()
        expected = compare(results, parts)
        for name in rounds.ROUNDS:
            results[name] = pd.Series(pd.NaT, index=results.index, dtype="timedelta64[ns]")
        output = compare(results, parts)
        for name in ["q1", "q2", "q3"]:
            pd.testing.assert_series_equal(expected[f"{name}_gap"], output[f"{name}_gap"])
            self.assertEqual(output.loc["D00", f"{name}_driver_time_source"], "laps")

    def test_disqualification_removes_all_rounds(self):
        output = compare(*qualifying_fixture(), disqualified={"1": "technical exclusion"})
        for driver in ["D00", "D01"]:
            for name in ["q1", "q2", "q3"]:
                self.assertTrue(pd.isna(output.loc[driver, f"{name}_gap"]))
                self.assertEqual(output.loc[driver, f"{name}_reason_code"], "dsq")

    def test_lap_correction_blocks_invalid_q2_recovery(self):
        results, parts = qualifying_fixture()
        results.loc[14, "Q1"] = pd.to_timedelta(100, unit="s")
        results.loc[14, "Q2"] = pd.NaT
        output = compare(results, parts)
        self.assertEqual(output.loc["D14", "q2_driver_reason"], "eliminated_prior_round")
        self.assertTrue(output.loc["D14", "q2_driver_recovery_blocked"])
        self.assertTrue(pd.isna(output.loc["D14", "q2_driver_time_seconds"]))

    def test_standalone_script_has_no_old_script_import(self):
        tree = ast.parse(Path(rounds.__file__).read_text())
        names = [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
        names += [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        self.assertNotIn("qualifying_gaps", names)

    def test_red_flag_audit_does_not_count_chequered_or_investigation(self):
        event = Mock(RoundNumber=1, EventName="Example Grand Prix")
        session = Mock()
        session.race_control_messages = pd.DataFrame([
            {"Flag": "CHEQUERED", "Message": "CHEQUERED FLAG"},
            {"Flag": "RED", "Message": "RED FLAG"},
            {"Flag": None, "Message": "FIA STEWARDS: RED FLAG INFRINGEMENT INVESTIGATED"}])
        evidence = rounds.session_evidence(event, session)
        self.assertEqual(sum(r["category"] == "red_flag" for r in evidence), 1)


if __name__ == "__main__":
    unittest.main()
