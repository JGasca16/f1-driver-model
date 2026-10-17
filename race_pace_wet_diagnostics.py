"""Compare fixed wet field minimums; never write official wet results."""
import argparse
import time
from pathlib import Path
from types import FunctionType

import fastf1
import numpy as np
import pandas as pd

import race_pace_wet as wet

MINIMUMS = (8, 4, 5, 6)
KEYS = ["round_number", "race", "team", "driver", "teammate"]


def analysis_for(minimum):
    # Give the existing functions a private settings dictionary. Their code,
    # all other settings, and the imported module remain unchanged.
    settings = dict(vars(wet), MIN_FIELD_DRIVERS=minimum)
    settings["field_changes"] = FunctionType(wet.field_changes.__code__, settings)
    return FunctionType(wet.analyse_race.__code__, settings)


def field_audit(clean, minimum):
    valid = clean.loc[np.isfinite(clean.lap_seconds) & clean.lap_seconds.gt(0)]
    valid = valid.loc[~valid.duplicated(["DriverNumber", "LapNumber"], keep=False)]
    counts = valid.groupby("LapNumber").DriverNumber.nunique()
    settings = dict(vars(wet), MIN_FIELD_DRIVERS=minimum)
    field = FunctionType(wet.field_changes.__code__, settings)(clean)
    for offset, name in [(-1, "before"), (0, "current"), (1, "after")]:
        field[f"drivers_{name}"] = counts.reindex(field.index + offset, fill_value=0).to_numpy()
    insufficient = field[["drivers_before", "drivers_current", "drivers_after"]].lt(minimum).any(axis=1)
    # Missing neighbouring lap numbers have zero clean drivers, so they fall
    # in insufficient_field rather than an extra third category.
    assert insufficient.eq(~field.reference_known).all()
    field["weather_reason"] = np.where(insufficient, "insufficient_field",
        np.where(field.stable_2pct, "", "measured_jump"))
    return field


def diagnose_race(race, minimum):
    official_rows, official_audit = analysis_for(minimum)(race)
    clean = wet.filter_clean_laps(race.laps).join(wet.traffic_at_lap_start(race.laps))
    field = field_audit(clean, minimum)
    free = clean.loc[~clean.in_traffic].join(field, on="LapNumber")
    lap_rows = []
    for row in free.loc[free.weather_reason.ne("")].itertuples():
        lap_rows.append(dict(round_number=race.round_number, race=race.race,
            field_minimum=minimum, driver_number=row.DriverNumber, lap_number=row.LapNumber,
            weather_reason=row.weather_reason, drivers_before=row.drivers_before,
            drivers_current=row.drivers_current, drivers_after=row.drivers_after,
            change_before_pct=row.change_before_pct, change_after_pct=row.change_after_pct))
    race_row = dict(round_number=race.round_number, race=race.race, field_minimum=minimum,
        status="analysed", insufficient_field=int(free.weather_reason.eq("insufficient_field").sum()),
        measured_jump=int(free.weather_reason.eq("measured_jump").sum()))
    check = official_audit["thresholds"][2]
    assert race_row["insufficient_field"] == check["weather_unknown_removed_driver_laps"]
    assert race_row["measured_jump"] == check["weather_jump_removed_driver_laps"]
    rows = []
    roster = race.roster.set_index("Abbreviation")
    for row in official_rows:
        a = clean.loc[clean.DriverNumber.eq(roster.loc[row["driver"], "DriverNumber"])]
        b = clean.loc[clean.DriverNumber.eq(roster.loc[row["teammate"], "DriverNumber"])]
        pair = a.merge(b, on="LapNumber", suffixes=("_a", "_b"), validate="one_to_one")
        pair = pair.loc[pair.Compound_a.eq(pair.Compound_b) & ~pair.in_traffic_a & ~pair.in_traffic_b]
        if row["reason_code"] in ["no_race_laps", "race_disqualification"]:
            pair = pair.iloc[:0]
        reasons = pair.LapNumber.map(field.weather_reason)
        insufficient = int(reasons.eq("insufficient_field").sum())
        jump = int(reasons.eq("measured_jump").sum())
        assert len(pair) == insufficient + jump + row["matched_laps_2pct"]
        rows.append(dict(**{key: row[key] for key in KEYS}, field_minimum=minimum,
            matched_laps=row["matched_laps_2pct"], gap=row["wet_gap_2pct"],
            gap_se_pp=row["wet_gap_se_pp_2pct"], ci_low=row["wet_gap_ci_low_2pct"],
            ci_high=row["wet_gap_ci_high_2pct"], confidence=row["final_confidence"],
            reason_code=row["reason_code"], before_weather_pair_laps=len(pair),
            insufficient_field=insufficient, measured_jump=jump))
    assert sum(r["insufficient_field"] for r in rows) == check["weather_unknown_removed_pair_laps"]
    assert sum(r["measured_jump"] for r in rows) == check["weather_jump_removed_pair_laps"]
    return rows, race_row, lap_rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    destination = args.output_dir or root / "data"
    names = ["race_pace_wet_diagnostics.csv", "race_pace_wet_field_race_diagnostics.csv",
             "race_pace_wet_weather_removed_laps.csv"]
    if any((destination / name).exists() for name in names):
        parser.error("Diagnostics already exist; choose a new --output-dir. No files overwritten.")
    started = time.perf_counter()
    fastf1.Cache.enable_cache(str(root / "cache"))
    fastf1.Cache.offline_mode(args.offline)
    fastf1.set_log_level("ERROR")
    schedule = fastf1.get_event_schedule(2025, include_testing=False)
    pairs, races, laps = [], [], []
    for number, name in wet.RACES.items():
        events = schedule.loc[schedule.RoundNumber.eq(number) & schedule.EventName.eq(name)]
        assert len(events) == 1
        race = wet.load_race(events.iloc[0])
        assert wet.wet_tyre_status(race.laps) == "wet_tyres_recorded"
        for minimum in MINIMUMS:
            p, r, l = diagnose_race(race, minimum)
            pairs.extend(p)
            races.append(r)
            laps.extend(l)
    for minimum in MINIMUMS:
        races.append(dict(round_number=6, race="Miami Grand Prix", field_minimum=minimum,
            status="excluded_not_evaluated", insufficient_field=np.nan, measured_jump=np.nan))
    output = pd.DataFrame(pairs)
    base = output.loc[output.field_minimum.eq(8)].set_index(KEYS).sort_index()
    official = pd.read_csv(root / "data/race_pace_wet_final.csv", float_precision="round_trip").set_index(KEYS).sort_index()
    assert len(base) == 30 and base.index.equals(official.index)
    for column, original in [("gap", "wet_gap_2pct"), ("matched_laps", "matched_laps_2pct"),
        ("gap_se_pp", "wet_gap_se_pp_2pct"), ("ci_low", "wet_gap_ci_low_2pct"),
        ("ci_high", "wet_gap_ci_high_2pct"), ("confidence", "final_confidence")]:
        pd.testing.assert_series_equal(base[column], official[original], check_names=False, check_exact=True)
    baseline_gaps = output.set_index(KEYS).index.map(base.gap.notna())
    output["new_pair_vs_8"] = output.gap.notna().to_numpy() & ~np.asarray(baseline_gaps)
    race_output = pd.DataFrame(races).sort_values(["field_minimum", "round_number"])
    destination.mkdir(parents=True, exist_ok=True)
    for name, frame in zip(names, [output, race_output, pd.DataFrame(laps)]):
        with (destination / name).open("x") as stream:
            frame.to_csv(stream, index=False)
    print("Baseline matches every official primary gap, count, error, interval and confidence exactly.")
    print("Driver-lap removals after the unchanged traffic filter:")
    print(race_output.to_string(index=False))
    print("\nField minimum | gaps | new pairs | driver-lap insufficient/jump | pair-lap insufficient/jump | confidence")
    for minimum in MINIMUMS:
        group = output.loc[output.field_minimum.eq(minimum)]
        r = race_output.loc[race_output.field_minimum.eq(minimum)]
        print(minimum, int(group.gap.notna().sum()), int(group.new_pair_vs_8.sum()),
            int(r.insufficient_field.sum()), int(r.measured_jump.sum()),
            int(group.insufficient_field.sum()), int(group.measured_jump.sum()), group.confidence.value_counts().to_dict())
    print("\nNew pairs:")
    print(output.loc[output.new_pair_vs_8, ["field_minimum", "race", "driver", "teammate", "matched_laps", "gap", "gap_se_pp", "confidence"]].to_string(index=False))
    print(f"Runtime: {time.perf_counter()-started:.2f} seconds")
    assert wet.MIN_FIELD_DRIVERS == 8


if __name__ == "__main__":
    main()
