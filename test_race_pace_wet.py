"""Fixed-rule checks for the standalone wet method."""
import ast
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np
import pandas as pd

import race_pace_wet as wet


def crossing_laps(gap=1.2):
    # Driver A crosses before B; A and B can be on different race lap numbers.
    frame = pd.DataFrame([
        dict(DriverNumber="A", LapNumber=3., Time=pd.to_timedelta(90, unit="s"),
             LapStartTime=pd.to_timedelta(0, unit="s"), LapTime=pd.to_timedelta(90, unit="s"),
             PitInTime=pd.NaT, FastF1Generated=False),
        dict(DriverNumber="B", LapNumber=2., Time=pd.to_timedelta(180+gap, unit="s"),
             LapStartTime=pd.to_timedelta(90+gap, unit="s"), LapTime=pd.to_timedelta(90, unit="s"),
             PitInTime=pd.NaT, FastF1Generated=False)])
    frame["PitInTime"] = pd.Series(pd.NaT, index=frame.index, dtype="timedelta64[ns]")
    return frame


def field_laps(middle=100., drivers=8):
    return pd.DataFrame([dict(DriverNumber=str(d), LapNumber=n, lap_seconds=t)
                         for n, t in [(4, 100.), (5, middle), (6, 100.)]
                         for d in range(drivers)])


class WetPaceTests(unittest.TestCase):
    def test_traffic_under_1_5_seconds(self):
        result = wet.traffic_at_lap_start(crossing_laps())
        self.assertAlmostEqual(result.loc[1, "gap_ahead_seconds"], 1.2)
        self.assertTrue(result.loc[1, "in_traffic"])

    def test_exact_traffic_boundary_passes(self):
        result = wet.traffic_at_lap_start(crossing_laps(1.5))
        self.assertFalse(result.loc[1, "in_traffic"])

    def test_no_car_ahead_is_not_discarded(self):
        result = wet.traffic_at_lap_start(crossing_laps())
        self.assertTrue(result.loc[0, "traffic_unknown"])
        self.assertFalse(result.loc[0, "in_traffic"])
        result = wet.traffic_at_lap_start(crossing_laps().iloc[:1])
        self.assertTrue(result.traffic_unknown.all())
        self.assertFalse(result.in_traffic.any())

    def test_missing_start_is_not_discarded(self):
        laps = crossing_laps()
        laps.loc[1, "LapStartTime"] = pd.NaT
        result = wet.traffic_at_lap_start(laps)
        self.assertTrue(result.loc[1, "traffic_unknown"])
        self.assertFalse(result.loc[1, "in_traffic"])

    def test_future_and_pit_crossings_not_used(self):
        laps = crossing_laps()
        laps.loc[0, "Time"] = pd.to_timedelta(95, unit="s")
        self.assertTrue(wet.traffic_at_lap_start(laps).loc[1, "traffic_unknown"])
        laps = crossing_laps()
        laps.loc[0, "PitInTime"] = pd.to_timedelta(89, unit="s")
        self.assertTrue(wet.traffic_at_lap_start(laps).loc[1, "traffic_unknown"])

    def test_weather_jump_above_threshold(self):
        result = wet.field_changes(field_laps(102.5))
        self.assertFalse(result.loc[5, "stable_1pct"])
        self.assertFalse(result.loc[5, "stable_2pct"])
        self.assertTrue(result.loc[5, "stable_3pct"])

    def test_weather_exact_boundary_and_both_neighbours(self):
        result = wet.field_changes(field_laps(102.))
        self.assertTrue(result.loc[5, "stable_2pct"])
        frame = field_laps()
        frame.loc[frame.LapNumber.eq(6), "lap_seconds"] = 110.
        self.assertFalse(wet.field_changes(frame).loc[5, "stable_2pct"])

    def test_weather_requires_eight_drivers_and_adjacent_laps(self):
        self.assertFalse(wet.field_changes(field_laps(drivers=7)).reference_known.any())
        frame = field_laps()
        frame.loc[frame.LapNumber.eq(4), "LapNumber"] = 3
        self.assertFalse(wet.field_changes(frame).loc[5, "reference_known"])
        # Repeating one driver eight times cannot satisfy the eight-driver gate.
        frame = field_laps()
        frame["DriverNumber"] = "A"
        self.assertFalse(wet.field_changes(frame).reference_known.any())

    def test_same_seed_same_bootstrap(self):
        values = np.sin(np.arange(25))
        self.assertEqual(wet.strict_bootstrap(values), wet.strict_bootstrap(values))
        self.assertNotEqual(wet.strict_bootstrap(values, 42), wet.strict_bootstrap(values, 43))

    def test_minimum_ten_and_signed_gap(self):
        self.assertTrue(all(np.isnan(value) for value in wet.estimate(np.full(9, -.3))))
        gap = 100 * (90.0-90.3) / 90.3
        actual, se, low, high = wet.estimate(np.full(10, gap))
        self.assertAlmostEqual(actual, gap)
        self.assertAlmostEqual(se, 0.)
        self.assertAlmostEqual(low, gap)
        self.assertAlmostEqual(high, gap)

    def test_confidence_rule(self):
        for gap, se, count, label in [(0., .15, 20, "high"), (0., .15, 19, "medium"),
            (.2, .30, 10, "medium"), (.2, .30001, 30, "low"), (.2, .1, 9, "low"),
            (.2, np.nan, 30, "low"), (np.nan, .1, 30, "unavailable")]:
            self.assertEqual(wet.confidence(gap, se, count), label)

    def test_canonical_and_numbered_runs_are_preserved(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            first = pd.DataFrame({"value": [1]})
            run1, canonical = wet.save_output(first, root)
            run2, _ = wet.save_output(pd.DataFrame({"value": [2]}), root)
            self.assertEqual(run1.parent.name, "wet_001")
            self.assertEqual(run2.parent.name, "wet_002")
            self.assertEqual(canonical.read_text(), first.to_csv(index=False))
            self.assertEqual(run1.read_text(), canonical.read_text())
            self.assertNotEqual(run2.read_text(), canonical.read_text())

    def test_wet_evidence_and_miami_exclusion(self):
        self.assertNotIn(6, wet.RACES)
        frame = pd.DataFrame({"FastF1Generated": [False], "Compound": ["HARD"]})
        self.assertEqual(wet.wet_tyre_status(frame), "no_wet_tyres_recorded")
        frame.loc[0, "Compound"] = None
        self.assertEqual(wet.wet_tyre_status(frame), "wet_tyre_evidence_unknown")
        frame.loc[0, "Compound"] = "INTERMEDIATE"
        self.assertEqual(wet.wet_tyre_status(frame), "wet_tyres_recorded")

    def test_standalone_imports(self):
        tree = ast.parse(Path(wet.__file__).read_text())
        names = [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
        names += [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        self.assertFalse(any(n and n.startswith("race_pace") for n in names))

    def test_saved_output_schema_counts_and_labels(self):
        root = Path(wet.__file__).resolve().parent
        table = pd.read_csv(root / "data/race_pace_wet_final.csv")
        self.assertEqual(list(table.columns), wet.COLUMNS)
        self.assertEqual(len(table), 30)
        self.assertEqual(set(table.round_number), {1, 12, 13})
        self.assertTrue(table.wet_flag.eq(True).all())
        self.assertFalse(table.duplicated(["round_number", "team"]).any())
        self.assertTrue(table.matched_laps_1pct.le(table.matched_laps_2pct).all())
        self.assertTrue(table.matched_laps_2pct.le(table.matched_laps_3pct).all())
        for p in wet.THRESHOLDS:
            self.assertTrue(table[f"wet_gap_{p}pct"].notna().eq(table[f"matched_laps_{p}pct"].ge(10)).all())
        for row in table.itertuples():
            self.assertEqual(row.final_confidence, wet.confidence(
                row.wet_gap_2pct, row.wet_gap_se_pp_2pct, row.matched_laps_2pct))
            self.assertEqual(pd.isna(row.reason_code), pd.notna(row.wet_gap_2pct))
        self.assertEqual((root / "data/race_pace_wet_final.csv").read_bytes(),
                         (root / "data/runs/wet_001/race_pace_wet_final.csv").read_bytes())


if __name__ == "__main__":
    unittest.main()
