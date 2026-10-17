"""Separate Q1/Q2/Q3 teammate gaps; see QUALIFYING_BY_ROUND.md."""
import argparse
import io
import time
from pathlib import Path

import fastf1
import pandas as pd

YEAR = 2025
ROUNDS = ["Q1", "Q2", "Q3"]
# Whole-session exclusions copied from the verified 2025 registry.
# Sources, assumptions and review questions are in QUALIFYING_BY_ROUND.md.
DISQUALIFIED_2025 = {
    (17, "31"): "rear-wing deflection infringement",
    (18, "23"): "rear-wing/DRS technical infringement",
    (18, "55"): "rear-wing/DRS technical infringement",
}
KEYS = ["round_number", "race", "team", "driver", "teammate"]

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


def driver_round_reason(driver, name, times, reached, exclusions):
    if driver in exclusions:
        return "dsq"
    if pd.notna(times.loc[driver, name]):
        return ""
    if reached[driver] < ROUNDS.index(name) + 1:
        return "eliminated_prior_round"
    return "no_valid_lap"


def compare_by_round(round_number, race, results, parts, disqualified=None):
    # Keep every legacy column, calculated with exactly the original method.
    rows = compare_teammates(round_number, race, results, parts, disqualified)
    results, times, raw, reached, sources, exclusions = prepare_times(
        results, parts, round_number, disqualified)
    numbers = results.set_index("Abbreviation").DriverNumber
    for row in rows:
        driver, teammate = numbers[row["driver"]], numbers[row["teammate"]]
        row["selected_gap"] = row["gap_pct"]
        row["selected_round"] = row["qualifying_round"]
        for name in ROUNDS:
            prefix = name.lower()
            dr = driver_round_reason(driver, name, times, reached, exclusions)
            tr = driver_round_reason(teammate, name, times, reached, exclusions)
            # One primary pair reason, plus both individual reasons for review.
            reason = next((r for r in ["dsq", "eliminated_prior_round", "no_valid_lap"] if r in [dr, tr]), "")
            dt, tt = times.loc[driver, name], times.loc[teammate, name]
            row[f"{prefix}_gap"] = float("nan") if reason else 100 * (dt-tt) / tt
            row[f"{prefix}_reason_code"] = reason
            row[f"{prefix}_driver_reason"] = dr
            row[f"{prefix}_teammate_reason"] = tr
            row[f"{prefix}_driver_time_seconds"] = dt
            row[f"{prefix}_teammate_time_seconds"] = tt
            row[f"{prefix}_driver_time_source"] = sources.loc[driver, name]
            row[f"{prefix}_teammate_time_source"] = sources.loc[teammate, name]
            # Flag the specific case where laps exist but advancement forbids recovery.
            row[f"{prefix}_driver_recovery_blocked"] = bool(pd.isna(dt) and pd.notna(raw.loc[driver, name]) and reached[driver] < ROUNDS.index(name)+1)
            row[f"{prefix}_teammate_recovery_blocked"] = bool(pd.isna(tt) and pd.notna(raw.loc[teammate, name]) and reached[teammate] < ROUNDS.index(name)+1)
    return rows


def load_qualifying(event):
    # A sprint weekend still has a main Q session. Never ask for SQ or SS.
    session = event.get_session("Q")
    session.load(laps=True, telemetry=False, weather=False, messages=True)
    return session


def session_evidence(event, session):
    messages = pd.DataFrame(session.race_control_messages)
    rows = []
    for _, message in messages.iterrows():
        wording = str(message.get("Message", ""))
        flag = str(message.get("Flag", ""))
        if flag == "RED" or wording.strip().upper() == "RED FLAG":
            category = "red_flag"
        elif any(term in wording.upper() for term in ["PENALTY", "PENALTIES", "GRID", "DISQUALIF", "DELETED", "REINSTATED", "STEWARDS", "INVESTIGAT", "RESUME", "RESUMPTION", "WILL NOT"]):
            category = "penalty_or_lap_decision"
        else:
            continue
        rows.append(dict(round_number=int(event.RoundNumber), race=event.EventName,
                         category=category, time=str(message.get("Time", "")),
                         driver_number=str(message.get("RacingNumber", "")), message=wording))
    return rows


def formatted_output(frame):
    # The old CSV saved six decimal places. Use that precision for exact parity.
    return pd.read_csv(io.StringIO(frame.to_csv(index=False, float_format="%.6f")), float_precision="round_trip")


def verify_parity(output, baseline):
    new = formatted_output(output).set_index(KEYS).sort_index()
    old = baseline.set_index(KEYS).sort_index()
    if not new.index.is_unique or not new.index.equals(old.index):
        raise ValueError("New and existing qualifying pair/driver rosters differ")
    # Every original column must survive, not only the selected gap.
    pd.testing.assert_frame_equal(new[old.columns], old, check_exact=True)
    pd.testing.assert_series_equal(new.selected_gap, old.gap_pct, check_names=False, check_exact=True)
    pd.testing.assert_series_equal(new.selected_round, old.qualifying_round, check_names=False, check_exact=True)


def print_summary(output):
    pairs = output.loc[output.driver < output.teammate]
    usable = pairs[[f"{name.lower()}_gap" for name in ROUNDS]].notna().sum(axis=1)
    print(f"\n{len(output)} driver rows; {len(pairs)} unique teammate pairs")
    for name in ROUNDS:
        prefix = name.lower()
        print(f"{name}: {pairs[f'{prefix}_gap'].notna().sum()} usable pairs; blanks: "
              f"{pairs.loc[pairs[f'{prefix}_gap'].isna(), f'{prefix}_reason_code'].value_counts().to_dict()}")
    print(f"All three rounds: {usable.eq(3).sum()}; only one: {usable.eq(1).sum()}; "
          f"two: {usable.eq(2).sum()}; none: {usable.eq(0).sum()}")
    print("Selected gap and all legacy columns match the existing CSV exactly.")
    miami = output.loc[output.round_number.eq(6)]
    for name in ROUNDS:
        print(f"Miami {name}: {miami[f'{name.lower()}_driver_time_source'].value_counts().to_dict()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--output-dir", type=Path, help="Use a new folder for a repeat run")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    destination = args.output_dir or root / "data"
    targets = [destination / n for n in ["2025_qualifying_gaps_by_round.csv", "2025_qualifying_round_session_evidence.csv"]]
    if any(p.exists() for p in targets):
        parser.error("Outputs already exist; choose a new --output-dir. Previous files are preserved.")
    started = time.perf_counter()
    fastf1.Cache.enable_cache(str(root / "cache"))
    fastf1.Cache.offline_mode(args.offline)
    fastf1.set_log_level("ERROR")
    schedule = fastf1.get_event_schedule(YEAR, include_testing=False)
    if len(schedule) != 24:
        raise ValueError("Expected 24 main qualifying sessions")
    rows, evidence = [], []
    for _, event in schedule.iterrows():
        print(f"Loading main qualifying: {event.EventName}", flush=True)
        session = load_qualifying(event)
        parts = session.laps.split_qualifying_sessions()
        rows.extend(compare_by_round(int(event.RoundNumber), event.EventName, session.results, parts))
        evidence.extend(session_evidence(event, session))
    output = pd.DataFrame(rows).sort_values(["round_number", "team", "driver"])
    first = KEYS + [c for name in ROUNDS for c in [f"{name.lower()}_gap", f"{name.lower()}_reason_code"]] + ["selected_gap", "selected_round"]
    output = output[first + [c for c in output.columns if c not in first]]
    baseline = pd.read_csv(root / "data/2025_qualifying_teammate_gaps.csv", float_precision="round_trip")
    verify_parity(output, baseline)
    destination.mkdir(parents=True, exist_ok=True)
    with targets[0].open("x") as stream:
        output.to_csv(stream, index=False, float_format="%.6f")
    audit = pd.DataFrame(evidence, columns=["round_number", "race", "category", "time", "driver_number", "message"])
    with targets[1].open("x") as stream:
        audit.to_csv(stream, index=False)
    print_summary(output)
    print("Recorded red flags by race:", audit.loc[audit.category.eq("red_flag"), "race"].value_counts().to_dict())
    print(f"Saved {targets[0]}\nSession evidence: {targets[1]}\nRuntime: {time.perf_counter()-started:.2f}s")


if __name__ == "__main__":
    main()
