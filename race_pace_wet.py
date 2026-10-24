"""Standalone wet/mixed race teammate gaps. See METHOD_WET_RACEPACE.md."""
import argparse
import time
from dataclasses import dataclass
from pathlib import Path

import fastf1
import numpy as np
import pandas as pd

from season_config import DEFAULT, add_season_arguments, from_args

YEAR = DEFAULT.year
RACES = {int(n): name for n, name in DEFAULT.facts["wet_races"].items()}
COMPOUNDS = {"SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"}
TRAFFIC_SECONDS = 1.5
MIN_FIELD_DRIVERS = 8
THRESHOLDS = (1, 2, 3)
PRIMARY_THRESHOLD = 2
MIN_MATCHED_LAPS = 10
BLOCK = 5
RESAMPLES = 2000
SEED = 42
NAN = float("nan")
COLUMNS = "round_number race team driver teammate matched_laps_2pct wet_gap_2pct wet_gap_se_pp_2pct wet_gap_ci_low_2pct wet_gap_ci_high_2pct wet_gap_1pct matched_laps_1pct wet_gap_3pct matched_laps_3pct final_confidence reason_code wet_flag".split()


@dataclass
class RaceData:
    round_number: int
    race: str
    roster: pd.DataFrame
    laps: pd.DataFrame


def build_roster(race_results, qualifying_results=None, season_settings=None):
    """Race entries take precedence; qualifying fills withdrawn entries only."""
    columns = ["DriverNumber", "Abbreviation", "TeamName", "Status"]
    roster = pd.DataFrame(race_results).reindex(columns=columns).copy()
    if qualifying_results is not None:
        extra = pd.DataFrame(qualifying_results).reindex(columns=columns).copy()
        extra = extra.loc[~extra["DriverNumber"].isin(roster["DriverNumber"])]
        extra["Status"] = "Absent from race results"
        roster = pd.concat([roster, extra], ignore_index=True)
    required = columns[:3]
    if roster[required].isna().any().any() or roster[required].eq("").any().any():
        raise ValueError("Incomplete driver/team roster")
    if roster["DriverNumber"].duplicated().any() or roster["Abbreviation"].duplicated().any():
        raise ValueError("Duplicate race entries")
    if not roster.groupby("TeamName").size().eq((season_settings or DEFAULT).facts["team_size"]).all():
        raise ValueError("A team does not have two identifiable weekend entries")
    return roster.sort_values(["TeamName", "Abbreviation"]).reset_index(drop=True)

def filter_clean_laps(laps):
    """Apply driver-level exclusions before matching teammates' lap numbers."""
    laps = pd.DataFrame(laps).copy().sort_values(["DriverNumber", "LapNumber"])
    laps["lap_seconds"] = laps["LapTime"].dt.total_seconds()
    laps["TyreLife"] = pd.to_numeric(laps["TyreLife"], errors="coerce")
    laps["pit_warmup"] = False
    laps["restart_buffer"] = False
    for _, group in laps.groupby("DriverNumber"):
        after_outlaps = group.loc[group["PitOutTime"].notna(), "LapNumber"] + 1
        laps.loc[group.index, "pit_warmup"] = group["LapNumber"].isin(after_outlaps)
        waiting_for_green = False
        for index, row in group.iterrows():
            status = str(row["TrackStatus"])
            if any(code in status for code in "4567"):
                waiting_for_green = True
            elif status == "1" and waiting_for_green:
                laps.loc[index, "restart_buffer"] = True
                waiting_for_green = False
    keep = (
        laps["LapNumber"].gt(1)
        & laps["lap_seconds"].gt(0) & laps["lap_seconds"].lt(float("inf"))
        & laps["PitInTime"].isna() & laps["PitOutTime"].isna()
        & laps["TrackStatus"].eq("1")
        & laps["Deleted"].eq(False)
        & laps["FastF1Generated"].eq(False)
        & laps["IsAccurate"].eq(True)
        & laps["Compound"].isin(COMPOUNDS)
        & laps["TyreLife"].ge(1) & laps["TyreLife"].lt(float("inf"))
        & ~laps["pit_warmup"] & ~laps["restart_buffer"]
        & ~laps.duplicated(["DriverNumber", "LapNumber"], keep=False)
    )
    return laps.loc[keep].copy()

def bootstrap_summary(values):
    low, high = np.percentile(values, [2.5, 97.5], method="linear")
    return float(np.std(values, ddof=1)), float(low), float(high)

def strict_bootstrap(values, seed=SEED):
    values = np.asarray(values, dtype=float)
    if len(values) < 2 * BLOCK or not np.isfinite(values).all():
        return NAN, NAN, NAN
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, len(values) - BLOCK + 1,
                          size=(RESAMPLES, int(np.ceil(len(values) / BLOCK))))
    indexes = (starts[:, :, None] + np.arange(BLOCK)).reshape(RESAMPLES, -1)
    medians = np.median(values[indexes[:, :len(values)]], axis=1)
    return bootstrap_summary(medians)

def confidence(gap, se, laps):
    if not np.isfinite(gap):
        return "unavailable"
    if np.isfinite(se) and 0 <= se <= 0.15 and laps >= 20:
        return "high"
    if np.isfinite(se) and 0 <= se <= 0.30 and laps >= 10:
        return "medium"
    return "low"


def traffic_at_lap_start(laps):
    """Estimate start-line headway from other cars' recorded line crossings."""
    laps = pd.DataFrame(laps)
    # Time is the lap-end crossing; LapStartTime is this driver's next crossing.
    # Use all lap numbers, so a lapped car can be the nearest car ahead.
    seconds = laps.LapTime.dt.total_seconds()
    valid = (laps.FastF1Generated.eq(False) & laps.Time.notna()
             & seconds.gt(0) & np.isfinite(seconds) & laps.PitInTime.isna()
             & ~laps.duplicated(["DriverNumber", "LapNumber"], keep=False))
    crossings = laps.loc[valid, ["DriverNumber", "Time"]].sort_values("Time")
    result = pd.DataFrame(index=laps.index)
    result["gap_ahead_seconds"] = NAN
    for driver, own in laps.groupby("DriverNumber", sort=True):
        others = crossings.loc[crossings.DriverNumber.ne(driver), "Time"].dt.total_seconds().to_numpy()
        starts = own.LapStartTime.dt.total_seconds().to_numpy()
        if len(others) == 0:
            continue
        positions = np.searchsorted(others, starts, side="right") - 1
        known = np.isfinite(starts) & (positions >= 0)
        gaps = np.full(len(starts), NAN)
        gaps[known] = starts[known] - others[positions[known]]
        result.loc[own.index, "gap_ahead_seconds"] = gaps
    # Unknown headway is allowed by the requested rule, not interpreted as zero.
    result["traffic_unknown"] = result.gap_ahead_seconds.isna()
    result["in_traffic"] = result.gap_ahead_seconds.lt(TRAFFIC_SECONDS)
    return result


def field_changes(clean):
    """Compare each field median with both immediate neighbouring lap numbers."""
    valid = clean.loc[np.isfinite(clean.lap_seconds) & clean.lap_seconds.gt(0)]
    valid = valid.loc[~valid.duplicated(["DriverNumber", "LapNumber"], keep=False)]
    field = valid.groupby("LapNumber").agg(median_seconds=("lap_seconds", "median"),
                                           drivers=("DriverNumber", "nunique"))
    medians = field.median_seconds.where(field.drivers.ge(MIN_FIELD_DRIVERS))
    # Reindex by actual lap number, never the next retained observation.
    before = medians.reindex(field.index - 1).to_numpy()
    after = medians.reindex(field.index + 1).to_numpy()
    current = medians.to_numpy()
    field["reference_known"] = np.isfinite(current) & np.isfinite(before) & np.isfinite(after)
    field["change_before_pct"] = 100 * np.abs(current - before) / before
    field["change_after_pct"] = 100 * np.abs(current - after) / after
    for threshold in THRESHOLDS:
        field[f"stable_{threshold}pct"] = (field.reference_known
            & field.change_before_pct.le(threshold) & field.change_after_pct.le(threshold))
    return field


def estimate(values):
    values = np.asarray(values, dtype=float)
    if len(values) < MIN_MATCHED_LAPS:
        return NAN, NAN, NAN, NAN
    gap = float(np.median(values))
    se, low, high = strict_bootstrap(values)
    return gap, se, low, high


def exclusion_reason(race, members):
    if any(d["Status"] == "Disqualified" for d in members):
        return "race_disqualification"
    if any(not (race.laps.DriverNumber.eq(d["DriverNumber"])
                & race.laps.FastF1Generated.eq(False)).any() for d in members):
        return "no_race_laps"
    return ""


def analyse_race(race):
    clean = filter_clean_laps(race.laps)
    clean = clean.join(traffic_at_lap_start(race.laps))
    field = field_changes(clean)
    clean = clean.join(field[["reference_known"] + [f"stable_{p}pct" for p in THRESHOLDS]], on="LapNumber")
    clean["reference_known"] = clean.reference_known.eq(True)
    for p in THRESHOLDS:
        clean[f"stable_{p}pct"] = clean[f"stable_{p}pct"].eq(True)
    # Report individual driver-laps separately from paired comparison laps.
    audit = dict(race=race.race, clean_driver_laps=len(clean),
                 traffic_removed_driver_laps=int(clean.in_traffic.sum()),
                 unknown_headway_driver_laps=int(clean.traffic_unknown.sum()),
                 thresholds={})
    after_traffic = clean.loc[~clean.in_traffic]
    for p in THRESHOLDS:
        audit["thresholds"][p] = dict(
            weather_jump_removed_driver_laps=int((after_traffic.reference_known & ~after_traffic[f"stable_{p}pct"]).sum()),
            weather_unknown_removed_driver_laps=int((~after_traffic.reference_known).sum()),
            weather_jump_independent_driver_laps=int((clean.reference_known & ~clean[f"stable_{p}pct"]).sum()),
            weather_unknown_independent_driver_laps=int((~clean.reference_known).sum()),
            same_compound_pair_laps=0, traffic_removed_pair_laps=0,
            weather_jump_removed_pair_laps=0, weather_unknown_removed_pair_laps=0,
            retained_pair_laps=0)
    rows = []
    for team, members in race.roster.groupby("TeamName", sort=True):
        first, second = members.sort_values("Abbreviation").to_dict("records")
        external = exclusion_reason(race, [first, second])
        a = clean.loc[clean.DriverNumber.eq(first["DriverNumber"])]
        b = clean.loc[clean.DriverNumber.eq(second["DriverNumber"])]
        shared = a.merge(b, on="LapNumber", suffixes=("_a", "_b"), validate="one_to_one").sort_values("LapNumber")
        same = shared.loc[shared.Compound_a.eq(shared.Compound_b)]
        free = same.loc[~same.in_traffic_a & ~same.in_traffic_b]
        row = dict(round_number=race.round_number, race=race.race, team=team,
                   driver=first["Abbreviation"], teammate=second["Abbreviation"], wet_flag=True)
        for p in THRESHOLDS:
            selected = free.loc[free[f"stable_{p}pct_a"]]
            if external:
                selected = selected.iloc[:0]
            else:
                details = audit["thresholds"][p]
                details["same_compound_pair_laps"] += len(same)
                details["traffic_removed_pair_laps"] += len(same) - len(free)
                details["weather_jump_removed_pair_laps"] += int((free.reference_known_a & ~free[f"stable_{p}pct_a"]).sum())
                details["weather_unknown_removed_pair_laps"] += int((~free.reference_known_a).sum())
                details["retained_pair_laps"] += len(selected)
            values = (100 * (selected.lap_seconds_a-selected.lap_seconds_b) / selected.lap_seconds_b).to_numpy()
            gap, se, low, high = estimate(values)
            row[f"wet_gap_{p}pct"] = gap
            row[f"matched_laps_{p}pct"] = len(selected)
            if p == PRIMARY_THRESHOLD:
                row.update(wet_gap_se_pp_2pct=se, wet_gap_ci_low_2pct=low, wet_gap_ci_high_2pct=high,
                           final_confidence=confidence(gap, se, len(selected)))
                if external:
                    reason = external
                elif len(shared) < MIN_MATCHED_LAPS:
                    reason = "too_few_same_number_laps"
                elif len(same) < MIN_MATCHED_LAPS:
                    reason = "too_few_same_compound_laps"
                elif len(free) < MIN_MATCHED_LAPS:
                    reason = "too_few_traffic_qualified_laps"
                elif len(selected) < MIN_MATCHED_LAPS:
                    reason = "too_few_stable_condition_laps"
                else:
                    reason = ""
                row["reason_code"] = reason
        rows.append(row)
    return rows, audit


def load_race(event, season_settings=None):
    cfg = season_settings or DEFAULT
    session = event.get_session("R")
    session.load(laps=True, telemetry=False, weather=False, messages=True)
    results = pd.DataFrame(session.results)
    qualifying = None
    if len(results) != cfg.facts["expected_entries"] or not results.groupby("TeamName").size().eq(cfg.facts["team_size"]).all():
        q = event.get_session("Q")
        q.load(laps=False, telemetry=False, weather=False, messages=False)
        qualifying = q.results
    roster = build_roster(results, qualifying, cfg)
    if len(roster) != cfg.facts["expected_entries"]:
        raise ValueError("Could not establish the manifest weekend roster; schema audit required")
    laps = pd.DataFrame(session.laps).reset_index(drop=True)
    if laps.empty or session.track_status.empty or session.race_control_messages.empty:
        raise ValueError("Race laps, track status or race-control messages unavailable")
    if laps.Deleted.isna().all():
        raise ValueError("Lap-deletion information unavailable")
    return RaceData(int(event.RoundNumber), event.EventName, roster, laps)


def wet_tyre_status(laps):
    actual = laps.loc[laps.FastF1Generated.eq(False)]
    if actual.Compound.isin(["INTERMEDIATE", "WET"]).any():
        return "wet_tyres_recorded"
    if actual.empty or not actual.Compound.isin(COMPOUNDS).all():
        return "wet_tyre_evidence_unknown"
    return "no_wet_tyres_recorded"


def save_output(output, destination, season_settings=None):
    """Always archive this run. Create the canonical file only if absent."""
    cfg = season_settings or DEFAULT
    destination = cfg.checked(destination)
    runs = cfg.checked(destination / "runs")
    runs.mkdir(parents=True, exist_ok=True)
    number = 1
    while True:
        folder = cfg.checked(runs / f"{cfg.facts['run_prefixes']['wet']}{number:03d}")
        try:
            folder.mkdir()
            break
        except FileExistsError:
            number += 1
    target = cfg.output("wet", folder)
    content = output.to_csv(index=False)
    with target.open("x") as stream:
        stream.write(content)
    canonical = cfg.output("wet", destination)
    try:
        with canonical.open("x") as stream:
            stream.write(content)
        print(f"Created canonical result: {canonical}")
    except FileExistsError:
        same = canonical.read_text() == content
        print(f"Canonical result preserved ({'identical to this run' if same else 'DIFFERS from this run; review required'}): {canonical}")
    print(f"Saved run: {target}")
    return target, canonical


def print_summary(output, audits, held_out, runtime, season_settings=None):
    print(f"\nWet/mixed races analysed: {output.round_number.nunique()}; teammate pairs: {len(output)}")
    for p in THRESHOLDS:
        print(f"{p}% threshold: {output[f'wet_gap_{p}pct'].notna().sum()}/{len(output)} pairs have a gap")
    print("Primary (2%) confidence:", output.final_confidence.value_counts().to_dict())
    print("Primary blank reasons:", output.loc[output.wet_gap_2pct.isna(), "reason_code"].value_counts().to_dict())
    print("Removal counts use traffic first, then weather. Weather unknown is separate from a measured jump.")
    for audit in audits:
        print(f"{audit['race']}: {audit['clean_driver_laps']} clean driver-laps; traffic removes "
              f"{audit['traffic_removed_driver_laps']}; unknown headway allowed: {audit['unknown_headway_driver_laps']}")
        for p, counts in audit["thresholds"].items():
            print(f"  {p}%: weather removes {counts['weather_jump_removed_driver_laps']} driver-laps for jumps + "
                  f"{counts['weather_unknown_removed_driver_laps']} for unknown reference after traffic; "
                  f"without traffic first: {counts['weather_jump_independent_driver_laps']} jumps + "
                  f"{counts['weather_unknown_independent_driver_laps']} unknown")
            print(f"    Pair-laps: {counts['same_compound_pair_laps']} same-compound -> "
                  f"traffic -{counts['traffic_removed_pair_laps']} -> weather jumps -{counts['weather_jump_removed_pair_laps']} "
                  f"-> weather unknown -{counts['weather_unknown_removed_pair_laps']} -> {counts['retained_pair_laps']} kept")
    for item in (season_settings or DEFAULT).facts["dry_holdouts"]:
        print(f"{item['race'].removesuffix(' Grand Prix')} excluded entirely; no compound recovery attempted.")
    print("Other races held out pending classification approval:", held_out or "none")
    print(f"Runtime: {runtime:.2f} seconds")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Use only the existing FastF1 cache")
    parser.add_argument("--output-dir", type=Path, help="Parent folder for the canonical file and numbered runs")
    add_season_arguments(parser)
    args = parser.parse_args()
    cfg = from_args(args)
    started = time.perf_counter()
    root = Path(__file__).resolve().parent
    fastf1.Cache.enable_cache(str(cfg.path("cache")))
    fastf1.Cache.offline_mode(args.offline)
    fastf1.set_log_level("ERROR")
    schedule = fastf1.get_event_schedule(cfg.year, include_testing=False)
    if len(schedule) != cfg.facts["round_count"]:
        raise ValueError("Schedule length differs from the verified manifest")
    rows, audits, held_out = [], [], []
    for key, name in cfg.facts["wet_races"].items():
        number = int(key)
        events = schedule.loc[schedule.RoundNumber.eq(number) & schedule.EventName.eq(name)]
        if len(events) != 1:
            raise ValueError(f"Could not identify scheduled race {number}: {name}")
        race = load_race(events.iloc[0], cfg)
        status = wet_tyre_status(race.laps)
        if status != "wet_tyres_recorded":
            held_out.append(f"{race.race}: {status}; not reclassified or counted")
            continue
        entries, audit = analyse_race(race)
        rows.extend(entries)
        audits.append(audit)
        print(f"Analysed {race.race}", flush=True)
    output = pd.DataFrame(rows, columns=COLUMNS)
    save_output(output, args.output_dir or cfg.path("data"), cfg)
    print_summary(output, audits, held_out, time.perf_counter()-started, cfg)


if __name__ == "__main__":
    main()
