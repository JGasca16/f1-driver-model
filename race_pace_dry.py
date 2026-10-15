"""Standalone dry race pace. Method and limitations: METHOD_DRY_RACEPACE.md."""
import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path

import fastf1
import numpy as np
import pandas as pd

YEAR = 2025
MIN_MATCHED_LAPS = 10
MIN_CLEAN = 10
MIN_SHARED_COMPOUND = 8
MAX_CONDITION = 1000
BLOCK = 5
RESAMPLES = 2000
SEED = 42
NAN = float("nan")
SLICKS = {"SOFT", "MEDIUM", "HARD"}
WEATHER_EDGE_TOLERANCE = pd.to_timedelta(120, unit="s")
WEATHER_MAX_GAP = pd.to_timedelta(180, unit="s")
COLUMNS = "round_number race team driver teammate matched_laps driver_clean_laps teammate_clean_laps strict_gap strict_se_pp strict_ci_low strict_ci_high linear_gap linear_se_pp linear_ci_low linear_ci_high final_gap method_used final_se_pp final_confidence disagreement_flag track_reliability_flag smallest_error_gap smallest_error_method reason_code".split()

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

def stint_blocks(frame):
    """Keep short stints and short final chunks; never cross driver/stint."""
    groups = []
    for _, group in frame.groupby(["DriverNumber", "Stint"], sort=True):
        positions = group.sort_values("LapNumber").index.to_numpy()
        groups.append([positions[i:i+BLOCK] for i in range(0, len(positions), BLOCK)])
    return groups

def linear_arrays(frame, first):
    columns = [np.ones(len(frame)), frame.DriverNumber.eq(first).astype(float).to_numpy()]
    columns += [frame.Compound.eq(c).astype(float).to_numpy() for c in sorted(frame.Compound.unique())[1:]]
    columns += [frame[c].to_numpy(dtype=float) for c in ["TyreLife", "LapNumber"]]
    x = np.column_stack(columns)
    means, scales = x[:, 1:].mean(axis=0), x[:, 1:].std(axis=0)
    if (scales == 0).any():
        raise ValueError("Original accepted model has a constant required term")
    z = np.column_stack([x[:, 0], (x[:, 1:] - means) / scales])
    return z, frame.lap_seconds.to_numpy(), frame.DriverNumber.eq(first).to_numpy(), means[0], scales[0]

def refit_percentage(z, y, is_first, indicator_mean, indicator_scale):
    """Algebraically the same seconds model and reference as the original fit, without pandas."""
    if len(y) <= z.shape[1] or not is_first.any() or is_first.all():
        return NAN, "effects_not_identifiable"
    try:
        beta, _, rank, _ = np.linalg.lstsq(z, y, rcond=None)
    except np.linalg.LinAlgError:
        return NAN, "numerical_failure"
    if rank < z.shape[1]:
        return NAN, "effects_not_identifiable"
    reference = (z[is_first].mean(axis=0) + z[~is_first].mean(axis=0)) / 2
    reference[1] = -indicator_mean / indicator_scale
    denominator = float(reference @ beta)
    difference = float(beta[1] / indicator_scale)
    if not np.isfinite([denominator, difference]).all() or min(denominator, denominator+difference) <= 0:
        return NAN, "invalid_reference_time"
    return 100 * difference / denominator, ""


def strategy_reason(frame, first, second):
    a = frame.loc[frame.DriverNumber.eq(first)]
    b = frame.loc[frame.DriverNumber.eq(second)]
    shared = set(a.Compound) & set(b.Compound)
    if not any(a.Compound.eq(c).sum() >= MIN_SHARED_COMPOUND
               and b.Compound.eq(c).sum() >= MIN_SHARED_COMPOUND for c in shared):
        return "strategy_confounded"
    if min(len(a), len(b)) < MIN_CLEAN:
        return "too_few_clean_laps"
    return ""


def fit_linear(frame, first, second):
    """The driver coefficient is a seconds difference at shared conditions."""
    reason = strategy_reason(frame, first, second)
    if reason:
        return NAN, reason
    a = frame.loc[frame.DriverNumber.eq(first)]
    b = frame.loc[frame.DriverNumber.eq(second)]
    frame = pd.concat([a, b], ignore_index=True)
    columns = [np.ones(len(frame)), frame.DriverNumber.eq(first).astype(float).to_numpy()]
    columns += [frame.Compound.eq(c).astype(float).to_numpy()
                for c in sorted(frame.Compound.unique())[1:]]
    for name in ["TyreLife", "LapNumber"]:
        values = frame[name].to_numpy(dtype=float)
        columns.append(values - values.mean())
    x, y = np.column_stack(columns), frame.lap_seconds.to_numpy(dtype=float)
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        return NAN, "fit_failed"
    means, scales = x[:, 1:].mean(axis=0), x[:, 1:].std(axis=0)
    if (scales == 0).any() or len(x) <= x.shape[1]:
        return NAN, "effects_not_identifiable"
    z = np.column_stack([np.ones(len(x)), (x[:, 1:] - means) / scales])
    transform = np.eye(x.shape[1])
    transform[0, 1:] = -means / scales
    transform[1:, 1:] = np.diag(1 / scales)
    try:
        scaled_beta, _, rank, singular = np.linalg.lstsq(z, y, rcond=None)
    except np.linalg.LinAlgError:
        return NAN, "fit_failed"
    if rank < z.shape[1]:
        return NAN, "effects_not_identifiable"
    if singular[0] / singular[-1] > MAX_CONDITION:
        return NAN, "fit_ill_conditioned"
    beta = transform @ scaled_beta
    reference = (x[:len(a)].mean(axis=0) + x[len(a):].mean(axis=0)) / 2
    reference[1] = 0
    denominator = float(reference @ beta)
    if not np.isfinite(denominator) or min(denominator, denominator + beta[1]) <= 0:
        return NAN, "invalid_reference_time"
    gap = float(100 * beta[1] / denominator)
    return (gap, "") if np.isfinite(gap) else (NAN, "fit_failed")


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


def bootstrap_arrays(frame, arrays, seed=SEED):
    """Resample chunks inside each stint; keep short chunks as in v3."""
    empty = dict(se=NAN, low=NAN, high=NAN, attempted=0, skipped=0,
                 valid=0, skip_reasons={}, reason="")
    if frame.Stint.isna().any():
        return dict(empty, reason="stint_unknown")
    z, y, is_first, mean, scale = arrays
    groups = stint_blocks(frame.reset_index(drop=True))
    rng = np.random.default_rng(seed)
    # Draw each group's choices first, preserving the original random sequence.
    choices = [rng.integers(0, len(group), size=(RESAMPLES, len(group))) for group in groups]
    values, skips = [], {}
    for i in range(RESAMPLES):
        indexes = np.concatenate([group[j] for group, draws in zip(groups, choices)
                                  for j in draws[i]])
        gap, reason = refit_percentage(z[indexes], y[indexes], is_first[indexes], mean, scale)
        if reason:
            skips[reason] = skips.get(reason, 0) + 1
        else:
            values.append(gap)
    result = dict(empty, attempted=RESAMPLES, skipped=RESAMPLES-len(values),
                  valid=len(values), skip_reasons=skips)
    if len(values) < 2:
        return dict(result, reason="too_few_valid_resamples")
    se, low, high = bootstrap_summary(values)
    return dict(result, se=se, low=low, high=high)


def linear_bootstrap(frame, first, seed=SEED):
    frame = frame.reset_index(drop=True)
    return bootstrap_arrays(frame, linear_arrays(frame, first), seed)


def confidence(gap, se, laps):
    if not np.isfinite(gap):
        return "unavailable"
    if np.isfinite(se) and 0 <= se <= 0.15 and laps >= 20:
        return "high"
    if np.isfinite(se) and 0 <= se <= 0.30 and laps >= 10:
        return "medium"
    return "low"


def choose_final(strict, linear):
    if np.isfinite(strict):
        return strict, "strict"
    if np.isfinite(linear):
        return linear, "linear"
    return NAN, "unavailable"


def disagreement(strict, strict_se, linear, linear_se):
    if not np.isfinite([strict, strict_se, linear, linear_se]).all() or min(strict_se, linear_se) < 0:
        return None
    return bool(abs(strict-linear) > 2 * np.hypot(strict_se, linear_se))


def smallest_error(estimates):
    """Input order breaks exact ties; an estimate without an error cannot win."""
    available = [(name, gap, se) for name, gap, se in estimates
                 if np.isfinite([gap, se]).all() and se >= 0]
    if not available:
        return NAN, "unavailable"
    name, gap, _ = min(available, key=lambda value: value[2])
    return gap, name


def external_reason(race, members):
    if any(d["Status"] == "Disqualified" for d in members):
        return "race_disqualification"
    if any(not (race.laps.DriverNumber.eq(d["DriverNumber"])
                & race.laps.FastF1Generated.eq(False)).any() for d in members):
        return "no_race_laps"
    return ""


def matched_values(a, b):
    columns = ["LapNumber", "lap_seconds", "Compound", "TyreLife"]
    shared = a[columns].merge(b[columns], on="LapNumber", suffixes=("_a", "_b"), validate="one_to_one")
    shared = shared.loc[shared.Compound_a.eq(shared.Compound_b)
                        & (shared.TyreLife_a - shared.TyreLife_b).abs().le(3)].sort_values("LapNumber")
    return (100 * (shared.lap_seconds_a - shared.lap_seconds_b) / shared.lap_seconds_b).to_numpy()


def analyse_race(race):
    clean = filter_clean_laps(race.laps)
    rows, bootstrap_audit = [], []
    for team, members in race.roster.groupby("TeamName", sort=True):
        first, second = members.sort_values("Abbreviation").to_dict("records")
        d, t = first["DriverNumber"], second["DriverNumber"]
        a, b = clean.loc[clean.DriverNumber.eq(d)], clean.loc[clean.DriverNumber.eq(t)]
        reason = external_reason(race, [first, second])
        values = np.array([]) if reason else matched_values(a, b)
        strict = float(f"{np.median(values):.6f}") if len(values) >= MIN_MATCHED_LAPS else NAN
        strict_se, strict_low, strict_high = strict_bootstrap(values)
        linear, linear_reason = (NAN, reason) if reason else fit_linear(clean, d, t)
        error = dict(se=NAN, low=NAN, high=NAN, reason="not_accepted", attempted=0, skipped=0, valid=0, skip_reasons={})
        if np.isfinite(linear):
            # Keep the established CSV precision; bootstrap uses unrounded fits.
            linear = float(f"{linear:.9f}")
            frame = clean.loc[clean.DriverNumber.isin([d, t])].reset_index(drop=True)
            error = linear_bootstrap(frame, d)
        bootstrap_audit.append(dict(round_number=race.round_number, driver=first["Abbreviation"],
                                    teammate=second["Abbreviation"], **error))
        gap, method = choose_final(strict, linear)
        se = strict_se if method == "strict" else error["se"] if method == "linear" else NAN
        laps = len(values) if method == "strict" else min(len(a), len(b))
        smallest, smallest_method = smallest_error([("strict", strict, strict_se), ("linear", linear, error["se"])])
        rows.append(dict(round_number=race.round_number, race=race.race, team=team,
            driver=first["Abbreviation"], teammate=second["Abbreviation"], matched_laps=len(values),
            driver_clean_laps=len(a), teammate_clean_laps=len(b), strict_gap=strict,
            strict_se_pp=strict_se, strict_ci_low=strict_low, strict_ci_high=strict_high,
            linear_gap=linear, linear_se_pp=error["se"], linear_ci_low=error["low"], linear_ci_high=error["high"],
            final_gap=gap, method_used=method, final_se_pp=se, final_confidence=confidence(gap, se, laps),
            disagreement_flag=disagreement(strict, strict_se, linear, error["se"]),
            track_reliability_flag="low_overtaking_limited" if race.race == "Monaco Grand Prix" else "",
            smallest_error_gap=smallest, smallest_error_method=smallest_method,
            reason_code=(reason or linear_reason or "too_few_matched_laps") if not np.isfinite(gap) else ""))
    return rows, bootstrap_audit


def dry_races(offline):
    root = Path(__file__).resolve().parent
    fastf1.Cache.enable_cache(str(root / "cache"))
    fastf1.Cache.offline_mode(offline)
    fastf1.set_log_level("ERROR")
    schedule = fastf1.get_event_schedule(YEAR, include_testing=False)
    if len(schedule) != 24:
        raise ValueError("Expected 24 races on the 2025 calendar")
    for _, event in schedule.iterrows():
        if event.EventName == "Miami Grand Prix":
            print("Excluded Miami Grand Prix (explicit exclusion)", flush=True)
            continue
        race = load_race(event)
        if race.issue:
            raise ValueError(f"{race.race}: {race.issue}")
        status, reason = dry_race_status(race.laps, race.weather, race.start, race.end)
        if status == "unknown":
            raise ValueError(f"{race.race}: {reason}")
        if status == "dry":
            yield race
        else:
            print(f"Excluded {race.race}: {reason}", flush=True)


def output_paths(destination):
    """Keep previous results and give repeat runs their own numbered folder."""
    names = ["race_pace_dry_final.csv", "race_pace_dry_run_summary.json"]
    destination.mkdir(parents=True, exist_ok=True)
    if any((destination / name).exists() for name in names):
        runs = destination / "runs"
        runs.mkdir(exist_ok=True)
        number = 1
        while True:
            candidate = runs / f"dry_{number:03d}"
            try:
                # Creating the folder reserves it, even for simultaneous runs.
                candidate.mkdir()
                break
            except FileExistsError:
                number += 1
        print(f"Previous outputs kept. Saving this run in {candidate}", flush=True)
        destination = candidate
    return [destination / name for name in names]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--output-dir", type=Path, help="Output folder; existing results are preserved in repeat runs")
    args = parser.parse_args()
    destination = args.output_dir or Path(__file__).resolve().parent / "data"
    paths = output_paths(destination)
    started = time.perf_counter()
    rows, audits = [], []
    for race in dry_races(args.offline):
        entries, audit = analyse_race(race)
        rows.extend(entries)
        audits.extend(audit)
        print(f"Analysed {race.race}", flush=True)
    output = pd.DataFrame(rows, columns=COLUMNS)
    summary = dict(dry_races=int(output.round_number.nunique()), pairs=len(output),
                   methods=output.method_used.value_counts().to_dict(),
                   labels=output.final_confidence.value_counts().to_dict(),
                   disagreement_flags=int(output.disagreement_flag.eq(True).sum()),
                   disagreement_untestable=int(output.disagreement_flag.isna().sum()),
                   blank_reasons=output.loc[output.final_gap.isna(), "reason_code"].value_counts().to_dict(),
                   runtime_seconds=time.perf_counter()-started, bootstrap_audit=audits)
    destination.mkdir(parents=True, exist_ok=True)
    with paths[0].open("x") as stream:
        output.to_csv(stream, index=False)
    with paths[1].open("x") as stream:
        json.dump(summary, stream, indent=2)
    print(json.dumps({k: v for k, v in summary.items() if k != "bootstrap_audit"}, indent=2))
    print(f"Saved {paths[0]}")


if __name__ == "__main__":
    main()
