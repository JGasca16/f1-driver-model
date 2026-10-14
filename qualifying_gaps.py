"""Export signed teammate qualifying gaps for the 2025 season."""

import argparse
from pathlib import Path

import fastf1
import pandas as pd


YEAR = 2025
ROUNDS = ["Q1", "Q2", "Q3"]
# The qualifying results do not expose these post-session disqualifications
# as a status. Their raw lap records still exist and must not be restored.
# Sources and the scope of these 2025-only decisions are in QUALIFYING.md.
DISQUALIFIED_2025 = {
    (17, "31"): "rear-wing deflection infringement",
    (18, "23"): "rear-wing/DRS technical infringement",
    (18, "55"): "rear-wing/DRS technical infringement",
}


def prepare_times(results, parts, round_number=None, disqualified=None):
    """Prefer result times; recover eligible missing times from valid laps."""
    results = pd.DataFrame(results).set_index("DriverNumber", drop=False)
    if len(results) != 20 or results.index.has_duplicates:
        raise ValueError("Expected 20 distinct qualifying entries for a 2025 race")
    if results["Abbreviation"].eq("").any() or results["TeamName"].eq("").any():
        raise ValueError("Driver or team information is missing")
    if results[["Abbreviation", "TeamName"]].isna().any().any():
        raise ValueError("Driver or team information is missing")

    lap_times = pd.DataFrame(float("nan"), index=results.index, columns=ROUNDS)
    valid_parts = []
    if len(parts) != 3:
        raise ValueError("Expected Q1, Q2, and Q3 lap data")
    for number, part in enumerate(parts, start=1):
        if part is None or part.empty:
            raise ValueError(f"Q{number} lap data is unavailable")
        if part["Deleted"].isna().any():
            raise ValueError("Lap deletion information is unavailable")
        # Race-control messages identify deleted laps. Out-laps and in-laps
        # are not representative qualifying attempts.
        valid = part.loc[
            part["LapTime"].notna()
            & part["Deleted"].eq(False)
            & part["LapTime"].gt(pd.Timedelta(0))
            & part["PitOutTime"].isna()
            & part["PitInTime"].isna()
            & part.get("FastF1Generated", pd.Series(False, index=part.index)).eq(False)
        ]
        # For equal times, the driver who recorded the time first ranks first.
        best = valid.sort_values(["LapTime", "Time"]).drop_duplicates("DriverNumber")
        lap_times[f"Q{number}"] = best.set_index("DriverNumber")["LapTime"].dt.total_seconds()
        valid_parts.append(valid)

    official_times = pd.DataFrame({
        name: pd.to_timedelta(results[name]).dt.total_seconds() for name in ROUNDS
    })
    official_times = official_times.where(official_times.gt(0) & official_times.lt(float("inf")))
    reached = pd.Series(1, index=results.index)
    for number, name in enumerate(ROUNDS, start=1):
        drivers = official_times.index[official_times[name].notna()]
        reached.loc[drivers] = reached.loc[drivers].clip(lower=number)
        if number == 3:
            continue

        # Infer advancement even when a driver never left the pits in the next
        # round. Prefer classified times, which include later lap deletions.
        # Retain raw times for excluded drivers in this ordering: a later
        # disqualification does not retroactively let a Q1 loser run in Q2.
        ranking_times = official_times[name].combine_first(lap_times[name])
        ranking = pd.DataFrame({"seconds": ranking_times})
        ranking["first_set"] = pd.Timedelta.max
        valid = valid_parts[number - 1]
        for driver, seconds in ranking_times.dropna().items():
            matching = valid.loc[
                valid["DriverNumber"].eq(driver)
                & valid["LapTime"].eq(pd.to_timedelta(seconds, unit="s")), "Time"
            ]
            if not matching.empty:
                ranking.loc[driver, "first_set"] = matching.min()
        ranking = ranking.loc[reached.ge(number)].dropna(subset=["seconds"])
        ranking = ranking.sort_values(["seconds", "first_set"], kind="stable")
        cutoff = 15 if number == 1 else 10
        advancing = ranking.head(cutoff).index
        reached.loc[advancing] = reached.loc[advancing].clip(lower=number + 1)

    if disqualified is None:
        disqualified = {
            driver: reason for (event_round, driver), reason in DISQUALIFIED_2025.items()
            if event_round == round_number
        }
    times = official_times.copy()
    sources = pd.DataFrame("missing", index=times.index, columns=ROUNDS)
    sources = sources.mask(times.notna(), "results")
    for number, name in enumerate(ROUNDS, start=1):
        recover = times[name].isna() & lap_times[name].notna() & reached.ge(number)
        times.loc[recover, name] = lap_times.loc[recover, name]
        sources.loc[recover, name] = "laps"
    for driver in results.index.intersection(list(disqualified)):
        times.loc[driver, :] = float("nan")
        sources.loc[driver, :] = "excluded"

    return results, times, lap_times, reached, sources, disqualified


def time_flags(driver, times, lap_times, reached, disqualified):
    """Distinguish no timed lap from a time omitted from the classification."""
    flags = []
    if driver in disqualified:
        return ["disqualified"]
    for name in ROUNDS[:int(reached[driver])]:
        if pd.isna(times.loc[driver, name]):
            reason = "no_time" if pd.isna(lap_times.loc[driver, name]) else "time_absent_from_results"
            flags.append(f"{reason}_{name}")
    return flags


def compare_teammates(round_number, race_name, results, parts, disqualified=None):
    results, times, lap_times, reached, sources, disqualified = prepare_times(
        results, parts, round_number, disqualified,
    )
    rows = []
    for team, drivers in results.groupby("TeamName", sort=True):
        if len(drivers) != 2:
            raise ValueError(f"Expected two teammates for {team}; found {len(drivers)}")
        first, second = drivers.index
        common_round = next((
            name for name in reversed(ROUNDS)
            if pd.notna(times.loc[first, name]) and pd.notna(times.loc[second, name])
        ), "")
        blank_reasons = []
        if not common_round:
            for driver in [first, second]:
                abbreviation = results.loc[driver, "Abbreviation"]
                if driver in disqualified:
                    blank_reasons.append(f"{abbreviation}: disqualified ({disqualified[driver]})")
                elif times.loc[driver].isna().all():
                    blank_reasons.append(f"{abbreviation}: no valid qualifying lap time in Q1, Q2, or Q3")
            if not blank_reasons:
                blank_reasons.append("No qualifying round has a valid time for both teammates")
        for driver, teammate in [(first, second), (second, first)]:
            driver_time = times.loc[driver, common_round] if common_round else float("nan")
            teammate_time = times.loc[teammate, common_round] if common_round else float("nan")
            driver_source = sources.loc[driver, common_round] if common_round else ""
            teammate_source = sources.loc[teammate, common_round] if common_round else ""
            source = driver_source if driver_source == teammate_source else "mixed"
            missing = not common_round
            if not missing and (driver_time <= 0 or teammate_time <= 0):
                raise ValueError("Qualifying lap times must be positive")
            gap = float("nan") if missing else 100 * (driver_time - teammate_time) / teammate_time
            flags = [f"driver_{flag}" for flag in time_flags(driver, times, lap_times, reached, disqualified)]
            flags += [f"teammate_{flag}" for flag in time_flags(teammate, times, lap_times, reached, disqualified)]
            if missing:
                flags.append("no_shared_valid_round")
            rows.append({
                "round_number": round_number,
                "race": race_name,
                "team": team,
                "driver": results.loc[driver, "Abbreviation"],
                "teammate": results.loc[teammate, "Abbreviation"],
                "qualifying_round": common_round,
                "driver_time_seconds": driver_time,
                "teammate_time_seconds": teammate_time,
                "gap_pct": gap,
                "driver_best_qualifying_time_seconds": times.loc[driver].min(),
                "teammate_best_qualifying_time_seconds": times.loc[teammate].min(),
                "driver_reached_round": f"Q{reached[driver]}",
                "teammate_reached_round": f"Q{reached[teammate]}",
                "missing_time": bool(missing),
                "flag": ";".join(flags) if flags else "ok",
                "time_source": source,
                "driver_time_source": driver_source,
                "teammate_time_source": teammate_source,
                "blank_gap_reason": "; ".join(blank_reasons),
            })
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Use previously downloaded FastF1 data")
    parser.add_argument("--show-flags", action="store_true", help="Print the flagged driver rows after the summary")
    args = parser.parse_args()
    project = Path(__file__).resolve().parent
    cache = project / "cache"
    data = project / "data"
    cache.mkdir(exist_ok=True)
    data.mkdir(exist_ok=True)
    fastf1.Cache.enable_cache(str(cache))
    fastf1.Cache.offline_mode(args.offline)
    fastf1.set_log_level("WARNING")

    schedule = fastf1.get_event_schedule(YEAR, include_testing=False)
    if len(schedule) != 24:
        raise ValueError("Expected 24 races on the 2025 calendar")
    print(
        "Mode: offline (cached FastF1 data only)." if args.offline
        else "Mode: online (FastF1 may download or refresh cached data).",
        flush=True,
    )
    rows = []
    failed = []
    for _, event in schedule.iterrows():
        race = event["EventName"]
        print(f"Processing qualifying {int(event['RoundNumber']):02d}/24: {race}", flush=True)
        try:
            session = event.get_session("Q")
            session.load(laps=True, telemetry=False, weather=False, messages=True)
            rows.extend(compare_teammates(
                int(event["RoundNumber"]), race, session.results,
                session.laps.split_qualifying_sessions(),
            ))
            print(f"Processed {race}: 20 driver rows", flush=True)
        except Exception as error:
            failed.append(race)
            print(f"Failed {race}: {error}", flush=True)

    if failed:
        print(f"Finished: {len(schedule) - len(failed)}/24 races loaded. Season CSV not written.")
        print("Races to retry: " + ", ".join(failed))
        return 1

    output = pd.DataFrame(rows).sort_values(["round_number", "team", "driver"])
    target = data / f"{YEAR}_qualifying_teammate_gaps.csv"
    output.to_csv(target, index=False, float_format="%.6f")
    available = output["gap_pct"].notna()
    flagged = output["flag"].ne("ok")
    pair_columns = ["round_number", "team"]
    total_pairs = output.groupby(pair_columns).ngroups
    available_pairs = output.loc[available].groupby(pair_columns).ngroups
    missing_pairs = output.loc[output["missing_time"]].groupby(pair_columns).ngroups
    print(
        f"\nFinished {YEAR}: processed {len(schedule)}/24 qualifying sessions; "
        f"{len(output)} driver rows ({total_pairs} teammate pairs)."
    )
    print(f"Calculated gaps: {available.sum()} driver rows ({available_pairs} pairs).")
    print(
        f"Missing comparison times: {output['missing_time'].sum()} driver rows "
        f"({missing_pairs} pairs); their gap cells are blank."
    )
    print(
        f"Flagged rows: {flagged.sum()} total; "
        f"{(flagged & output['missing_time']).sum()} have blank gaps, "
        f"{(flagged & available).sum()} have valid gaps with a flag in another round."
    )
    from_laps = output["driver_time_source"].eq("laps") | output["teammate_time_source"].eq("laps")
    if from_laps.any():
        recovered = output.loc[from_laps, "race"].drop_duplicates()
        print("Times recovered from lap data: " + ", ".join(recovered))
    blank_pairs = output.loc[output["missing_time"]].drop_duplicates(pair_columns)
    if not blank_pairs.empty:
        print("\nPairs with no shared valid qualifying time:")
        for _, pair in blank_pairs.iterrows():
            print(
                f"- {pair['race']} | {pair['team']} | "
                f"{pair['driver']} / {pair['teammate']}: {pair['blank_gap_reason']}"
            )
    print(f"Saved {target}")
    if args.show_flags:
        print("\nFlagged driver rows (driver = this row; teammate = the other driver):")
        print(output.loc[flagged, [
            "race", "driver", "teammate", "qualifying_round", "missing_time", "flag",
        ]].to_string(index=False))
    else:
        print("Add --show-flags to list the flagged driver rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
