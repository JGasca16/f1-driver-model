"""Export signed teammate qualifying gaps for the 2025 season."""

import argparse
from pathlib import Path

import fastf1
import pandas as pd


YEAR = 2025
ROUNDS = ["Q1", "Q2", "Q3"]


def prepare_times(results, parts):
    """Find best times and rounds reached, including rounds with no timed lap."""
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
            & part["PitOutTime"].isna()
            & part["PitInTime"].isna()
        ]
        # For equal times, the driver who recorded the time first ranks first.
        best = valid.sort_values(["LapTime", "Time"]).drop_duplicates("DriverNumber")
        lap_times[f"Q{number}"] = best.set_index("DriverNumber")["LapTime"].dt.total_seconds()
        valid_parts.append(valid)

    official_times = pd.DataFrame({
        name: pd.to_timedelta(results[name]).dt.total_seconds() for name in ROUNDS
    })
    # Miami's results feed supplies positions but no Q1/Q2/Q3 times. Recover
    # a wholly missing set of times from laps; preserve individual omissions
    # elsewhere because those can represent excluded/disqualified results.
    use_laps = official_times.isna().all().all()
    times = lap_times.copy() if use_laps else official_times
    if times.isna().all().all():
        raise ValueError("No qualifying times are available")
    reached = pd.Series(1, index=results.index)
    for number, name in enumerate(ROUNDS, start=1):
        drivers = times.index[times[name].notna()]
        reached.loc[drivers] = reached.loc[drivers].clip(lower=number)
        if number == 3:
            continue

        # Infer advancement even when a driver never left the pits in the next
        # round. Prefer classified times, which include later lap deletions.
        # Retain raw times for excluded drivers in this ordering: a later
        # disqualification does not retroactively let a Q1 loser run in Q2.
        ranking_times = times[name].combine_first(lap_times[name])
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

    return results, times, lap_times, reached, "laps" if use_laps else "results"


def time_flags(driver, times, lap_times, reached):
    """Distinguish no timed lap from a time omitted from the classification."""
    flags = []
    for name in ROUNDS[:int(reached[driver])]:
        if pd.isna(times.loc[driver, name]):
            reason = "no_time" if pd.isna(lap_times.loc[driver, name]) else "time_absent_from_results"
            flags.append(f"{reason}_{name}")
    return flags


def compare_teammates(round_number, race_name, results, parts):
    results, times, lap_times, reached, source = prepare_times(results, parts)
    rows = []
    for team, drivers in results.groupby("TeamName", sort=True):
        if len(drivers) != 2:
            raise ValueError(f"Expected two teammates for {team}; found {len(drivers)}")
        first, second = drivers.index
        common_round = f"Q{min(reached[first], reached[second])}"
        for driver, teammate in [(first, second), (second, first)]:
            driver_time = times.loc[driver, common_round]
            teammate_time = times.loc[teammate, common_round]
            missing = pd.isna(driver_time) or pd.isna(teammate_time)
            if not missing and (driver_time <= 0 or teammate_time <= 0):
                raise ValueError("Qualifying lap times must be positive")
            gap = float("nan") if missing else 100 * (driver_time - teammate_time) / teammate_time
            flags = [f"driver_{flag}" for flag in time_flags(driver, times, lap_times, reached)]
            flags += [f"teammate_{flag}" for flag in time_flags(teammate, times, lap_times, reached)]
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
            })
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Use previously downloaded FastF1 data")
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
    rows = []
    failed = []
    for _, event in schedule.iterrows():
        race = event["EventName"]
        try:
            session = event.get_session("Q")
            session.load(laps=True, telemetry=False, weather=False, messages=True)
            rows.extend(compare_teammates(
                int(event["RoundNumber"]), race, session.results,
                session.laps.split_qualifying_sessions(),
            ))
            print(f"Loaded {race}")
        except Exception as error:
            failed.append(race)
            print(f"Failed {race}: {error}")

    if failed:
        print(f"Finished: {len(schedule) - len(failed)}/24 races loaded. Season CSV not written.")
        print("Races to retry: " + ", ".join(failed))
        return 1

    output = pd.DataFrame(rows).sort_values(["round_number", "team", "driver"])
    target = data / f"{YEAR}_qualifying_teammate_gaps.csv"
    output.to_csv(target, index=False, float_format="%.6f")
    print(
        f"\nFinished {YEAR}: {len(schedule)} races, {len(output)} driver rows, "
        f"{output['gap_pct'].notna().sum()} calculated gaps, "
        f"{output['missing_time'].sum()} rows missing a comparison time, "
        f"{output['flag'].ne('ok').sum()} flagged rows."
    )
    print(f"Saved {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
