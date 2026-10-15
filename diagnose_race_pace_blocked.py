"""Offline audit only: writes new diagnostics, never the production pace CSVs."""
from pathlib import Path
from unittest.mock import patch

import fastf1
import pandas as pd

import race_pace_gaps as rp


def failure_flags(laps):
    laps = laps.copy().sort_values(["DriverNumber", "LapNumber"])
    seconds = laps.LapTime.dt.total_seconds()
    age = pd.to_numeric(laps.TyreLife, errors="coerce")
    warmup = pd.Series(False, index=laps.index)
    restart = warmup.copy()
    for _, group in laps.groupby("DriverNumber"):
        warmup.loc[group.index] = group.LapNumber.isin(
            group.loc[group.PitOutTime.notna(), "LapNumber"] + 1)
        waiting = False
        for index, row in group.iterrows():
            status = str(row.TrackStatus)
            if any(code in status for code in "4567"):
                waiting = True
            elif status == "1" and waiting:
                restart.loc[index] = True
                waiting = False
    status = laps.TrackStatus.astype(str)
    sc = status.str.contains("[4567]")
    yellow = status.str.contains("2")
    flags = pd.DataFrame({
        "lap1_or_invalid_number": ~laps.LapNumber.gt(1),
        "invalid_time": ~(seconds.gt(0) & seconds.lt(float("inf"))),
        "generated_or_unknown": ~laps.FastF1Generated.eq(False),
        "duplicate": laps.duplicated(["DriverNumber", "LapNumber"], keep=False),
        "pit": laps.PitInTime.notna() | laps.PitOutTime.notna() | warmup,
        "sc_vsc_red": sc | restart,
        "yellow": yellow,
        "other_track_status": ~status.eq("1") & ~sc & ~yellow,
        "deleted_or_unknown": ~laps.Deleted.eq(False),
        "inaccurate_or_unknown": ~laps.IsAccurate.eq(True),
        "unknown_or_non_slick_compound": ~laps.Compound.isin(rp.SLICKS),
        "invalid_tyre_age": ~(age.ge(1) & age.lt(float("inf"))),
    }).fillna(True)
    # This independent expression must retain exactly the production clean laps.
    expected = rp.filter_clean_laps(laps)
    assert set(laps.loc[~flags.any(axis=1)].index) == set(expected.index)
    flags["LapNumber"] = laps.LapNumber
    return flags, laps


def diagnose_pair(race, stored):
    members = race.roster.set_index("Abbreviation")
    numbers = [members.loc[stored.driver, "DriverNumber"],
               members.loc[stored.teammate, "DriverNumber"]]
    all_laps = race.laps.loc[race.laps.DriverNumber.isin(numbers)]
    flags, ordered = failure_flags(all_laps)
    sides = [ordered.loc[ordered.DriverNumber.eq(n)] for n in numbers]
    per_side = [flags.loc[s.index].groupby("LapNumber", dropna=False).any()
                for s in sides]
    shared = per_side[0].index.intersection(per_side[1].index)
    union = per_side[0].index.union(per_side[1].index)
    bad = per_side[0].loc[shared] | per_side[1].loc[shared]
    record = {"round_number": race.round_number, "race": race.race,
              "team": stored.team, "driver": stored.driver,
              "teammate": stored.teammate, "matched_laps": int(stored.matched_laps),
              "tyre_age_tolerance": 3, "minimum_matched_laps": 10,
              "driver_raw_records": len(sides[0]), "teammate_raw_records": len(sides[1]),
              "driver_clean_laps": int(stored.driver_clean_laps),
              "teammate_clean_laps": int(stored.teammate_clean_laps),
              "union_lap_numbers": len(union),
              "removed_missing_teammate_record": len(union) - len(shared),
              "shared_raw_lap_numbers": len(shared)}
    keep = pd.Series(True, index=shared)
    for name in bad.columns:
        record[f"removed_{name}"] = int((keep & bad[name]).sum())
        record[f"affected_{name}_overlapping"] = int(bad[name].sum())
        keep &= ~bad[name]
    clean_shared = shared[keep]
    assert len(clean_shared) == stored.same_lap_clean_matches
    a, b = [s.drop_duplicates("LapNumber").set_index("LapNumber").loc[clean_shared]
            for s in sides]
    same = a.Compound.eq(b.Compound)
    record["shared_clean_laps"] = len(clean_shared)
    record["removed_compound_mismatch"] = int((~same).sum())
    record["shared_same_compound_laps"] = int(same.sum())
    age_ok = (a.TyreLife - b.TyreLife).abs().le(3)
    record["removed_tyre_age_mismatch"] = int((same & ~age_ok).sum())
    assert int(same.sum()) == stored.same_compound_matches
    assert int((same & age_ok).sum()) == stored.matched_laps
    removed = sum(value for key, value in record.items() if key.startswith("removed_"))
    assert len(union) - removed == stored.matched_laps
    return record


def observed_tyre_rule(laps, weather=None, start=None, end=None):
    actual = laps.loc[laps.FastF1Generated.eq(False)]
    if actual.Compound.isin(["INTERMEDIATE", "WET"]).any():
        return "wet", "Intermediate/wet tyres recorded"
    if not actual.Compound.isin(rp.SLICKS).any():
        return "unknown", "No slick observations"
    return "dry", "No observed wet tyres; missing compound laps remain excluded"


def main():
    root = Path(__file__).resolve().parent
    targets = [root / "data" / name for name in (
        "race_pace_blocked_diagnostics.csv",
        "race_pace_dry_rule_diagnostics.csv",
        "race_pace_returning_pairs_diagnostics.csv")]
    if any(p.exists() for p in targets):
        raise FileExistsError("Audit output already exists; refusing to overwrite")
    fastf1.Cache.enable_cache(str(root / "cache"))
    fastf1.Cache.offline_mode(True)
    fastf1.set_log_level("ERROR")
    baseline = pd.read_csv(root / "data/2025_race_pace_teammate_gaps.csv")
    pairs = rp.pair_view(baseline)
    blocked = pairs.loc[pairs.reason_code.eq("too_few_matched_laps")]
    assert len(blocked) == 88
    diagnostics, dry_rows, returning = [], [], []
    for _, event in fastf1.get_event_schedule(2025, include_testing=False).iterrows():
        race = rp.load_race(event)
        assert not race.issue, (race.race, race.issue)
        for row in blocked.loc[blocked.round_number.eq(race.round_number)].itertuples():
            diagnostics.append(diagnose_pair(race, row))
        old, _ = rp.dry_race_status(race.laps, race.weather, race.start, race.end)
        observed, _ = observed_tyre_rule(race.laps)
        actual = race.laps.loc[race.laps.FastF1Generated.eq(False)]
        missing = int((~actual.Compound.isin(rp.SLICKS | {"INTERMEDIATE", "WET"})).sum())
        strict = "unknown" if observed == "dry" and missing else observed
        with patch.object(rp, "dry_race_status", observed_tyre_rule):
            alternative = rp.pair_view(pd.DataFrame(rp.paired_rows(race, 3)))
        original = pairs.loc[pairs.round_number.eq(race.round_number)]
        old_count = int(original.gap_pct.notna().sum())
        count = int(alternative.gap_pct.notna().sum())
        if old == observed:
            pd.testing.assert_series_equal(original.gap_pct.reset_index(drop=True),
                alternative.gap_pct.reset_index(drop=True), check_exact=False,
                atol=0.00000051, rtol=0)
        elif observed == "dry":
            returning.extend(alternative.to_dict("records"))
        dry_rows.append({"round_number": race.round_number, "race": race.race,
            "current_dry_status": old, "strict_all_laps_slick_status": strict,
            "no_observed_wet_tyres_status": observed,
            "unknown_compound_records": missing,
            "current_pairs_with_gap": old_count,
            "strict_pairs_with_gap": count if strict == "dry" else 0,
            "observed_rule_pairs_with_gap": count,
            "extra_pairs_observed_rule": count - old_count})
        print(f"Checked {race.race}", flush=True)
    frame = pd.DataFrame(diagnostics)
    assert len(frame) == 88
    for target, output in zip(targets, [frame, pd.DataFrame(dry_rows), pd.DataFrame(returning)]):
        with target.open("x") as stream:
            output.to_csv(stream, index=False, float_format="%.6f")
    print("5–9:", frame.matched_laps.between(5, 9).sum(),
          "1–4:", frame.matched_laps.between(1, 4).sum(),
          "0:", frame.matched_laps.eq(0).sum())
    print("Sequential removals:", frame.filter(regex="^removed_").sum().to_dict())
    print(pd.DataFrame(dry_rows).to_string(index=False))


if __name__ == "__main__":
    main()
