"""Season paths and exact 2025 compatibility; never load another season's data."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

import season_config as seasons
from season_eligibility_audit import compound_pit_audit
from season_parity import compare_csv, compare_json, compare_chart_data
from test_fastf1 import write_results

ROOT = Path(__file__).resolve().parent
SCRIPTS = ["test_fastf1.py", "qualifying_gaps_by_round.py", "qualifying_gaps_combined.py",
           "race_pace_dry.py", "race_pace_wet.py", "driver_rating.py", "prediction_test.py",
           "make_sanity_charts.py"]


def directory_snapshot(directory):
    """Record every file's relative path, size and contents, or nothing if absent."""
    directory = Path(directory)
    return {str(path.relative_to(directory)): (path.stat().st_size,
            hashlib.sha256(path.read_bytes()).hexdigest())
            for path in sorted(directory.rglob("*")) if path.is_file()}


class SeasonExtensionTests(unittest.TestCase):
    def test_2025_manifest_matches_original_facts(self):
        f = seasons.DEFAULT.facts
        self.assertEqual([f[k] for k in ["season", "round_count", "expected_entries", "team_size",
                                         "expected_appearances", "expected_unique_drivers"]],
                         [2025, 24, 20, 2, 480, 21])
        self.assertEqual(f["method_id"], "2025_teammate_rating_1_log_round_fix")
        self.assertEqual(f["wet_races"], {"1": "Australian Grand Prix", "12": "British Grand Prix", "13": "Belgian Grand Prix"})
        self.assertEqual(set(f["dry_rounds"]), set(range(1, 25)) - {1, 6, 12, 13})
        self.assertEqual(f["qualifying_advancement"], {"Q1": 15, "Q2": 10})
        self.assertEqual(seasons.DEFAULT.disqualifications(17), {"31": "rear-wing deflection infringement"})
        self.assertEqual(seasons.DEFAULT.disqualifications(18), {"23": "rear-wing/DRS technical infringement", "55": "rear-wing/DRS technical infringement"})
        self.assertEqual(f["charts"]["pairs"], [["TSU", "VER"], ["NOR", "PIA"], ["HAM", "LEC"]])
        self.assertEqual(f["charts"]["monaco_round"], 8)
        self.assertEqual(f["qualifying_summary"], {"race": "Miami Grand Prix", "round": 6, "label": "Miami"})
        self.assertEqual([(p["driver"], p["teammate"], p["first"], p["last"]) for p in f["roster_periods"]],
                         [("VER", "LAW", 1, 2), ("HAD", "TSU", 1, 2), ("VER", "TSU", 3, 24),
                          ("HAD", "LAW", 3, 24), ("GAS", "DOO", 1, 6), ("GAS", "COL", 7, 24)])

    def test_2025_default_paths_are_unchanged(self):
        cfg = seasons.DEFAULT
        self.assertEqual(cfg.sources(), ("data/2025_qualifying_gaps_by_round.csv", "data/race_pace_dry_final.csv", "data/race_pace_wet_final.csv"))
        self.assertEqual(cfg.input("ratings"), ROOT / "data/driver_rating_2025.csv")
        self.assertEqual(cfg.path("cache_sqlite"), ROOT / "cache/fastf1_http_cache.sqlite")
        self.assertEqual(cfg.path("runs"), ROOT / "data/runs")
        self.assertEqual(cfg.facts["chart_files"], ["rating_by_group.png", "qualifying_vs_dry.png", "gap_by_race_selected_pairs.png", "data_coverage.png"])

    def test_2024_paths_reject_2025_and_shared_output_locations(self):
        cfg = seasons.load_season(2024, require_verified=False)
        for path in ["data/driver_rating_2025.csv", "data/runs", "charts", "cache/2025",
                     "data/2024/../2025_result.csv", "data/2024/2025_results.csv"]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                cfg.checked(path)
        for key in cfg.facts["files"]:
            path = cfg.input(key)
            self.assertTrue(path.is_relative_to(ROOT / "data/2024"))
            self.assertIn("2024", path.name)

    def test_allowlist_and_published_name_are_enforced(self):
        cfg = seasons.load_season(2024, require_verified=False)
        with self.assertRaises(ValueError):
            cfg.checked("data/2024/ratings.csv", published=True)
        with self.assertRaises(ValueError):
            seasons.DEFAULT.checked("/outside-season-allowlist/result.csv")

    def test_unverified_skeleton_lists_missing_facts(self):
        with self.assertRaises(ValueError) as caught:
            seasons.load_season(2024)
        for name in ["round_count", "wet_races", "dry_rounds", "roster_verified", "charts", "miami_audit"]:
            self.assertIn(name, str(caught.exception))
        self.assertIn("UNVERIFIED", str(caught.exception))

    def test_all_eight_cli_commands_stop_before_unverified_data(self):
        directories = [ROOT / "data/2024", ROOT / "cache/season_2024"]
        for script in SCRIPTS:
            with self.subTest(script=script):
                before = {path: directory_snapshot(path) for path in directories}
                env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
                result = subprocess.run([sys.executable, "-B", str(ROOT / script), "--season", "2024", "--offline"],
                                        cwd=ROOT, env=env, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("UNVERIFIED required facts", result.stderr)
                self.assertIn("round_count", result.stderr)
                after = {path: directory_snapshot(path) for path in directories}
                self.assertEqual(before, after, "Rejected command changed season files")

    def test_directory_snapshot_detects_created_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "season"
            before = directory_snapshot(path)
            self.assertEqual(before, {})
            path.mkdir()
            (path / "unexpected.txt").write_text("unexpected output")
            with self.assertRaises(self.failureException):
                self.assertEqual(before, directory_snapshot(path))

    def test_unverified_manifest_never_substitutes_default_year(self):
        with self.assertRaisesRegex(ValueError, "disagrees"):
            seasons.load_season(2024, ROOT / "seasons/2025.json")

    def test_no_verified_chart_pairs_stops(self):
        facts = deepcopy(seasons.DEFAULT.facts)
        facts["charts"]["pairs"] = []
        with self.assertRaisesRegex(ValueError, "chart pairs"):
            replace(seasons.DEFAULT, facts=facts).require_verified()

    def test_exporter_refuses_overwrite_with_fixture_only(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "2025_fixture.csv"
            frame = pd.DataFrame({"Abbreviation": ["AAA"], "Position": [1]})
            write_results(frame, path)
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                write_results(frame.assign(Position=2), path)
            self.assertEqual(before, path.read_bytes())

    def test_prediction_copy_only_changes_season_and_manifest(self):
        original = json.loads((ROOT / "prediction_test_config.json").read_text())
        copied = json.loads((ROOT / "prediction_test_config_2024.json").read_text())
        self.assertEqual(copied.pop("manifest"), "seasons/2024.json")
        self.assertEqual(copied["season"], 2024)
        copied["season"] = original["season"]
        self.assertEqual(original, copied)

    def test_miami_is_a_2025_manifest_exception_only(self):
        self.assertEqual(seasons.DEFAULT.holdout("Miami Grand Prix")["round"], 6)
        other = seasons.load_season(2024, require_verified=False)
        self.assertIsNone(other.holdout("Miami Grand Prix"))
        self.assertEqual(other.facts["dry_holdouts"], [])
        self.assertEqual(other.facts["miami_audit"], "UNVERIFIED")

    def test_miami_hook_on_existing_2025_cache_copy(self):
        import fastf1
        cache = ROOT / "cache/_parity/cache_copy"
        source = cache / "2025/2025-05-04_Miami_Grand_Prix/2025-05-04_Race/timing_app_data.ff1pkl"
        if not source.exists():
            self.skipTest("Isolated 2025 cache copy is required for this integration check")
        fastf1.Cache.enable_cache(str(cache))
        fastf1.Cache.offline_mode(True)
        fastf1.set_log_level("ERROR")
        session = fastf1.get_session(2025, 6, "R")
        session.load(telemetry=False, weather=False)
        evidence, report = compound_pit_audit(session.laps, pickle.loads(source.read_bytes())["data"])
        self.assertEqual(report["compound_conflicts"], 54)
        self.assertEqual(report["unknown_compounds"], 354)
        self.assertEqual(report["tyre_age_conflicts"], 403)
        self.assertEqual(len(report["affected_drivers"]), 12)
        self.assertEqual(report["unresolved"], [])
        self.assertTrue(report["exclude_for_compound_conflict"])
        self.assertFalse(evidence.applied_to_pace.any())
        old = pd.read_csv(ROOT / "data/miami_compound_recovery_spec_audit.csv")
        recovered = evidence.loc[evidence.unknown_compound].merge(old, left_on=["driver", "lap_number"],
                                                                   right_on=["driver", "lap_number"], validate="one_to_one")
        self.assertEqual(len(recovered), 354)
        self.assertTrue(recovered.pit_aligned_compound.eq(recovered.recovered_compound).all())

    def test_ambiguous_audit_returns_review_instead_of_guessing(self):
        laps = pd.DataFrame([dict(DriverNumber="1", Driver="AAA", FastF1Generated=False,
            LapNumber=1, TrackStatus="1", PitInTime=pd.NaT, PitOutTime=pd.NaT,
            Compound="nan", TyreLife=np.nan)])
        timing = pd.DataFrame([dict(Driver="1", Stint=0, Compound="SOFT", StartLaps=0, TotalLaps=2)])
        _, report = compound_pit_audit(laps, timing)
        self.assertEqual(report["audit_status"], "review_required")
        self.assertIsNone(report["exclude_for_compound_conflict"])

    def test_parity_helpers_reject_injected_mismatches(self):
        with tempfile.TemporaryDirectory() as directory:
            a, b = Path(directory) / "a.csv", Path(directory) / "b.csv"
            a.write_text("driver,gap\nAAA,-0.1\n")
            b.write_bytes(a.read_bytes())
            self.assertEqual(compare_csv(a, b)["mismatches"], 0)
            b.write_text("driver,gap\nAAA,-0.10000000000000001\n")
            with self.assertRaises(AssertionError):
                compare_csv(a, b)
            a.write_text('{"gap": 1, "runtime_seconds": 1}')
            b.write_text('{"gap": 1, "runtime_seconds": 2}')
            self.assertEqual(list(compare_json(a, b, ["runtime_seconds"])), ["runtime_seconds"])
            b.write_text('{"gap": 2, "runtime_seconds": 2}')
            with self.assertRaises(AssertionError):
                compare_json(a, b, ["runtime_seconds"])
        with self.assertRaises(AssertionError):
            compare_chart_data({"order": ["A", "B"]}, {"order": ["B", "A"]})


if __name__ == "__main__":
    unittest.main()
