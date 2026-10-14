"""2025 teammate race pace on matched clean laps; see RACEPACE.md."""

import argparse
from dataclasses import dataclass
from pathlib import Path

import fastf1
import pandas as pd


YEAR = 2025
MIN_MATCHED_LAPS = 10
SLICKS = {"SOFT", "MEDIUM", "HARD"}
WEATHER_EDGE_TOLERANCE = pd.to_timedelta(120, unit="s")
WEATHER_MAX_GAP = pd.to_timedelta(180, unit="s")


@dataclass
class RaceData:
    round_number: int
    race: str
    roster: pd.DataFrame
    laps: pd.DataFrame
    weather: pd.DataFrame
    start: object = pd.NaT
    end: object = pd.NaT
    issue: str = ""


def build_roster(race_results, qualifying_results=None):
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
    if not roster.groupby("TeamName").size().eq(2).all():
        raise ValueError("A team does not have two identifiable weekend entries")
    return roster.sort_values(["TeamName", "Abbreviation"]).reset_index(drop=True)


def dry_race_status(laps, weather, start, end):
    """Return dry, wet, or unknown with a reason, using the whole race window."""
    actual = laps.loc[laps["FastF1Generated"].eq(False)]
    if actual["Compound"].isin(["INTERMEDIATE", "WET"]).any():
        return "wet", "Intermediate or wet tyres recorded during the race"
    if pd.isna(start) or pd.isna(end) or end <= start:
        return "unknown", "Race start/end timestamps unavailable"
    if weather.empty or not {"Time", "Rainfall"}.issubset(weather.columns):
        return "unknown", "Race weather data unavailable"
    samples = weather.dropna(subset=["Time"]).sort_values("Time")
    # Include the most recent pre-start observation as the weather at start.
    before = samples.loc[samples["Time"].le(start)].tail(1)
    during = samples.loc[samples["Time"].gt(start) & samples["Time"].le(end)]
    if not before.empty and start - before.iloc[0]["Time"] > WEATHER_EDGE_TOLERANCE:
        before = before.iloc[:0]
    samples = pd.concat([before, during]).drop_duplicates("Time")
    if samples.empty:
        return "unknown", "No weather observations covering the race"
    if samples["Rainfall"].eq(True).any():
        return "wet", "Rainfall reported during the race window"
    if not samples["Rainfall"].eq(False).all():
        return "unknown", "Rainfall observations contain missing or unrecognised values"
    if (
        abs(samples.iloc[0]["Time"] - start) > WEATHER_EDGE_TOLERANCE
        or end - samples.iloc[-1]["Time"] > WEATHER_EDGE_TOLERANCE
        or samples["Time"].diff().max() > WEATHER_MAX_GAP
    ):
        return "unknown", "Weather coverage has a gap longer than the permitted interval"
    return "dry", "No reported rain and no intermediate/wet tyres in the race"


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
        & laps["Compound"].isin(SLICKS)
        & laps["TyreLife"].ge(1) & laps["TyreLife"].lt(float("inf"))
        & ~laps["pit_warmup"] & ~laps["restart_buffer"]
        & ~laps.duplicated(["DriverNumber", "LapNumber"], keep=False)
    )
    return laps.loc[keep].copy()


def paired_rows(race, tyre_age_tolerance=3, min_matched_laps=MIN_MATCHED_LAPS):
    if tyre_age_tolerance < 0 or min_matched_laps < 1:
        raise ValueError("Tyre tolerance must be nonnegative and minimum laps positive")
    if race.issue:
        dry_status, dry_reason = "unknown", race.issue
        clean = pd.DataFrame()
    else:
        dry_status, dry_reason = dry_race_status(race.laps, race.weather, race.start, race.end)
        clean = filter_clean_laps(race.laps) if dry_status == "dry" else pd.DataFrame()
    rows = []
    for team, members in race.roster.groupby("TeamName", sort=True):
        if len(members) != 2:
            raise ValueError(f"Expected two drivers for {team}")
        first, second = members.sort_values("Abbreviation").to_dict("records")
        reason_code = reason = ""
        count_first = count_second = same_lap = same_compound = 0
        matched = pd.DataFrame()
        if race.issue:
            reason_code, reason = "data_unavailable", race.issue
        elif dry_status != "dry":
            reason_code = "wet_race" if dry_status == "wet" else "dry_status_unknown"
            reason = dry_reason
        else:
            disqualified = [d["Abbreviation"] for d in [first, second] if d["Status"] == "Disqualified"]
            absent = [d["Abbreviation"] for d in [first, second] if not (
                race.laps["DriverNumber"].eq(d["DriverNumber"])
                & race.laps["FastF1Generated"].eq(False)
            ).any()]
            a = clean.loc[clean["DriverNumber"].eq(first["DriverNumber"])]
            b = clean.loc[clean["DriverNumber"].eq(second["DriverNumber"])]
            count_first, count_second = len(a), len(b)
            if disqualified:
                reason_code, reason = "race_disqualification", "Disqualified from race: " + ", ".join(disqualified)
            elif absent:
                reason_code, reason = "no_race_laps", "No non-generated race lap records: " + ", ".join(absent)
            else:
                columns = ["LapNumber", "lap_seconds", "Compound", "TyreLife"]
                shared = a[columns].merge(b[columns], on="LapNumber", suffixes=("_a", "_b"), validate="one_to_one")
                same_lap = len(shared)
                shared = shared.loc[shared["Compound_a"].eq(shared["Compound_b"])]
                same_compound = len(shared)
                matched = shared.loc[(shared["TyreLife_a"] - shared["TyreLife_b"]).abs().le(tyre_age_tolerance)]
                if len(matched) < min_matched_laps:
                    reason_code = "too_few_matched_laps"
                    reason = (
                        f"Only {len(matched)} matched laps; need {min_matched_laps} "
                        f"({same_lap} shared clean laps, {same_compound} on the same compound, "
                        f"tyre-age tolerance {tyre_age_tolerance})"
                    )
        for reverse in [False, True]:
            driver, teammate = (second, first) if reverse else (first, second)
            gap = float("nan")
            if not reason_code:
                d, t = ("b", "a") if reverse else ("a", "b")
                gap = (100 * (matched[f"lap_seconds_{d}"] - matched[f"lap_seconds_{t}"]) / matched[f"lap_seconds_{t}"]).median()
            rows.append({
                "round_number": race.round_number, "race": race.race, "team": team,
                "driver": driver["Abbreviation"], "teammate": teammate["Abbreviation"],
                "gap_pct": gap, "matched_laps": len(matched),
                "reason_code": reason_code, "blank_gap_reason": reason,
                "tyre_age_tolerance": tyre_age_tolerance, "minimum_matched_laps": min_matched_laps,
                "dry_status": dry_status, "dry_reason": dry_reason,
                "driver_clean_laps": count_second if reverse else count_first,
                "teammate_clean_laps": count_first if reverse else count_second,
                "same_lap_clean_matches": same_lap, "same_compound_matches": same_compound,
                "driver_status": driver["Status"], "teammate_status": teammate["Status"],
            })
    return rows


def load_race(event):
    session = event.get_session("R")
    session.load(laps=True, telemetry=False, weather=True, messages=True)
    results = pd.DataFrame(session.results)
    qualifying = None
    if len(results) != 20 or not results.groupby("TeamName").size().eq(2).all():
        q = event.get_session("Q")
        q.load(laps=False, telemetry=False, weather=False, messages=False)
        qualifying = q.results
    roster = build_roster(results, qualifying)
    if len(roster) != 20:
        raise ValueError("Could not establish the 20-driver weekend roster")
    race = RaceData(int(event["RoundNumber"]), event["EventName"], roster, pd.DataFrame(), pd.DataFrame())
    try:
        race.laps = pd.DataFrame(session.laps).reset_index(drop=True)
        if race.laps.empty or session.track_status.empty or session.race_control_messages.empty:
            raise ValueError("Race laps, track status, or race-control messages unavailable")
        if race.laps["Deleted"].isna().all():
            raise ValueError("Lap-deletion information unavailable")
        status = session.session_status
        race.start = status.loc[status["Status"].eq("Started"), "Time"].min()
        # Include the final classified cars finishing after the leader.
        race.end = max(status.loc[status["Status"].eq("Finished"), "Time"].max(), race.laps["Time"].max())
        try:
            race.weather = pd.DataFrame(session.weather_data)
        except fastf1.core.DataNotLoadedError:
            pass
    except (fastf1.core.DataNotLoadedError, ValueError, KeyError) as error:
        race.issue = str(error) + "; load this race online to populate/repair the cache"
    return race


def pair_view(output):
    """Use alphabetical driver orientation so each pair counts once."""
    return output.loc[output["driver"] < output["teammate"]].copy()


def sensitivity_tables(outputs):
    index = ["round_number", "race", "team", "driver", "teammate"]
    details = pd.concat({
        tolerance: pair_view(output).set_index(index)[["gap_pct", "matched_laps", "reason_code"]]
        for tolerance, output in outputs.items()
    }, axis=1)
    details.columns = [f"{name}_tol_{tolerance}" for tolerance, name in details.columns]
    base = details["gap_pct_tol_3"]
    summaries = []
    for tolerance in [2, 3, 5]:
        gap = details[f"gap_pct_tol_{tolerance}"]
        common = gap.notna() & base.notna()
        delta = gap - base
        details[f"change_vs_3_pp_tol_{tolerance}"] = delta
        absolute = delta.loc[common].abs()
        summaries.append({
            "tyre_age_tolerance": tolerance,
            "pairs_with_gap": int(gap.notna().sum()), "blank_pairs": int(gap.isna().sum()),
            "new_pairs_vs_3": int((gap.notna() & base.isna()).sum()),
            "lost_pairs_vs_3": int((gap.isna() & base.notna()).sum()),
            "common_pairs_vs_3": int(common.sum()),
            "changed_gap_pairs_vs_3": int(absolute.gt(1e-9).sum()),
            "mean_abs_change_pp": absolute.mean(),
            "median_abs_change_pp": absolute.median(), "max_abs_change_pp": absolute.max(),
            "sign_flips_vs_3": int(((gap * base < 0) & common).sum()),
            "median_matched_laps_with_gap": details.loc[gap.notna(), f"matched_laps_tol_{tolerance}"].median(),
        })
    return pd.DataFrame(summaries), details.reset_index()


def print_summary(output, tolerance, show_blanks=False):
    pairs = pair_view(output)
    available = pairs["gap_pct"].notna()
    print(f"\nTyre-age tolerance {tolerance}: {available.sum()}/{len(pairs)} pairs have a gap; {(~available).sum()} blank.")
    for reason, count in pairs.loc[~available, "reason_code"].value_counts().items():
        print(f"  {reason}: {count} pairs")
    if show_blanks:
        for _, pair in pairs.loc[~available].iterrows():
            print(f"  {pair['race']} | {pair['driver']}/{pair['teammate']}: {pair['blank_gap_reason']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Use only previously cached FastF1 data")
    parser.add_argument("--tyre-age-tolerance", type=int, default=3)
    parser.add_argument("--sensitivity", action="store_true", help="Calculate tolerances 2, 3, and 5; compare with 3")
    parser.add_argument("--show-blanks", action="store_true", help="List every blank pair and its reason")
    args = parser.parse_args()
    if args.tyre_age_tolerance < 0:
        parser.error("--tyre-age-tolerance must be nonnegative")
    project = Path(__file__).resolve().parent
    cache, data = project / "cache", project / "data"
    cache.mkdir(exist_ok=True)
    data.mkdir(exist_ok=True)
    fastf1.Cache.enable_cache(str(cache))
    fastf1.Cache.offline_mode(args.offline)
    fastf1.set_log_level("WARNING")
    schedule = fastf1.get_event_schedule(YEAR, include_testing=False)
    if len(schedule) != 24:
        raise ValueError("Expected 24 races on the 2025 calendar")
    tolerances = [2, 3, 5] if args.sensitivity else [args.tyre_age_tolerance]
    collected = {tolerance: [] for tolerance in tolerances}
    fatal = []
    print("Mode: offline, cached data only" if args.offline else "Mode: online", flush=True)
    for _, event in schedule.iterrows():
        print(f"Processing race {int(event['RoundNumber']):02}/24: {event['EventName']}", flush=True)
        try:
            race = load_race(event)
            event_rows = {tolerance: paired_rows(race, tolerance) for tolerance in tolerances}
            for tolerance, rows in event_rows.items():
                collected[tolerance].extend(rows)
        except Exception as error:
            fatal.append(event["EventName"])
            print(f"FAILED: {error}", flush=True)
    if fatal:
        print("Season CSVs not written. Failed races: " + ", ".join(fatal))
        return 1
    outputs = {}
    for tolerance, rows in collected.items():
        output = pd.DataFrame(rows).sort_values(["round_number", "team", "driver"])
        outputs[tolerance] = output
        suffix = "" if tolerance == 3 else f"_tyre_age_{tolerance}"
        target = data / f"{YEAR}_race_pace_teammate_gaps{suffix}.csv"
        output.to_csv(target, index=False, float_format="%.6f")
        print_summary(output, tolerance, args.show_blanks)
        print(f"Saved {target}")
    if args.sensitivity:
        summary, details = sensitivity_tables(outputs)
        summary.to_csv(data / f"{YEAR}_race_pace_sensitivity_summary.csv", index=False, float_format="%.6f")
        details.to_csv(data / f"{YEAR}_race_pace_sensitivity_pairs.csv", index=False, float_format="%.6f")
        print("\nSensitivity: gap changes are percentage points, measured on pairs available in both runs.")
        print(summary.to_string(index=False, float_format=lambda value: f"{value:.6f}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
