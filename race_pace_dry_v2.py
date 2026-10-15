"""Add uncertainty and audits without changing v1 point estimates."""
import argparse
import itertools
import json
from pathlib import Path

import fastf1
import numpy as np
import pandas as pd

import race_pace_gaps as laps_v1
import race_pace_regression as regression_v1

BLOCK_LENGTH = 5
RESAMPLES = 2000
SEED = 42
NAN = float("nan")
METHOD_ERRORS = {
    "strict_gap": "strict_gap_se_pp",
    "regression_gap_linear": "regression_gap_linear_se_cluster_pp",
    "regression_gap_curved": "regression_gap_curved_se_cluster_pp",
    "lowconf_gap": "lowconf_gap_se_pp",
}


def bootstrap_gap(values, seed=SEED):
    """Resample overlapping blocks of five retained observations."""
    values = np.asarray(values, dtype=float)
    if len(values) < 2 * BLOCK_LENGTH:
        return NAN, NAN, NAN, "too_few_laps_for_two_blocks"
    if not np.isfinite(values).all():
        raise ValueError("Invalid percentage observations")
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, len(values) - BLOCK_LENGTH + 1,
                          size=(RESAMPLES, int(np.ceil(len(values) / BLOCK_LENGTH))))
    indexes = (starts[:, :, None] + np.arange(BLOCK_LENGTH)).reshape(RESAMPLES, -1)
    medians = np.median(values[indexes[:, :len(values)]], axis=1)
    low, high = np.percentile(medians, [2.5, 97.5], method="linear")
    return float(medians.std(ddof=1)), float(low), float(high), ""


def confidence(gap, se, count):
    if pd.isna(gap):
        return "unavailable"
    if pd.notna(se) and se <= .15 and count >= 20:
        return "high"
    if pd.notna(se) and se <= .30 and count >= 10:
        return "medium"
    return "low"


def available_errors(row):
    return [(name, float(row[name]), float(row[error])) for name, error in METHOD_ERRORS.items()
            if pd.notna(row[name]) and pd.notna(row[error]) and np.isfinite(row[error])
            and row[error] >= 0]


def uncertainty_disagreement(row):
    choices = available_errors(row)
    comparisons = list(itertools.combinations(choices, 2))
    if not comparisons:
        return None, 0
    flag = any(abs(a[1] - b[1]) > 2 * np.hypot(a[2], b[2]) for a, b in comparisons)
    return bool(flag), len(comparisons)


def smallest_error(row):
    choices = available_errors(row)
    if not choices:
        return NAN, "unavailable", NAN
    name, gap, se = min(choices, key=lambda x: x[2])
    return gap, name, se


def design_fit(frame, first, second, curved):
    """Reuse v1's gates; rebuild its design to expose residuals and predictions."""
    check = regression_v1.fit_pair(frame, first, second, curved)
    if check["reason_code"]:
        return None, check["reason_code"]
    compounds = sorted(frame.Compound.unique())
    centres = {c: frame[c].mean() for c in ["TyreLife", "LapNumber"]}

    def raw_design(data):
        if not set(data.Compound).issubset(compounds):
            raise ValueError("unseen_compound")
        columns = [np.ones(len(data)), data.DriverNumber.eq(first).astype(float).to_numpy()]
        columns += [data.Compound.eq(c).astype(float).to_numpy() for c in compounds[1:]]
        for name in centres:
            values = data[name].to_numpy(dtype=float) - centres[name]
            columns.append(values)
            if curved:
                columns.append(values ** 2)
        return np.column_stack(columns)

    x = raw_design(frame)
    means, scales = x[:, 1:].mean(axis=0), x[:, 1:].std(axis=0)
    z = np.column_stack([x[:, 0], (x[:, 1:] - means) / scales])
    beta, _, rank, _ = np.linalg.lstsq(z, frame.lap_seconds, rcond=None)
    assert rank == z.shape[1]
    u, singular, vt = np.linalg.svd(z, full_matrices=False)
    bread = (vt.T * (1 / singular ** 2)) @ vt
    reference = (z[frame.DriverNumber.eq(first)].mean(axis=0)
                 + z[frame.DriverNumber.eq(second)].mean(axis=0)) / 2
    reference[1] = -means[0] / scales[0]
    contrast = np.zeros(len(beta))
    contrast[1] = 1 / scales[0]
    delta, denominator = float(contrast @ beta), float(reference @ beta)
    gradient = 100 * contrast / denominator - 100 * delta * reference / denominator ** 2
    assert np.isclose(100 * delta / denominator, check["gap_pct"], atol=1e-8, rtol=0)

    def predict(test):
        raw = raw_design(test)
        return np.column_stack([raw[:, 0], (raw[:, 1:] - means) / scales]) @ beta

    return dict(z=z, beta=beta, bread=bread,
                residual=frame.lap_seconds.to_numpy() - z @ beta,
                contrast=contrast, gradient=gradient, predict=predict), ""


def cluster_covariance(z, residual, bread, labels):
    """CR1: sum each stint's score before forming the sandwich."""
    groups = np.unique(labels)
    n, k = z.shape
    if len(groups) < 2 or n <= k:
        raise ValueError("insufficient_clusters_or_df")
    scores = np.vstack([z[labels == g].T @ residual[labels == g] for g in groups])
    correction = len(groups) / (len(groups) - 1) * (n - 1) / (n - k)
    return correction * bread @ (scores.T @ scores) @ bread


def cluster_errors(frame, first, second, curved):
    if frame.Stint.isna().any():
        return NAN, NAN, "stint_unknown"
    model, reason = design_fit(frame, first, second, curved)
    if reason:
        return NAN, NAN, reason
    labels = (frame.DriverNumber.astype(str) + ":" + frame.Stint.astype(str)).to_numpy()
    try:
        cov = cluster_covariance(model["z"], model["residual"], model["bread"], labels)
    except ValueError as error:
        return NAN, NAN, str(error)
    term_se = np.sqrt(max(0, model["contrast"] @ cov @ model["contrast"]))
    gap_se = np.sqrt(max(0, model["gradient"] @ cov @ model["gradient"]))
    return float(gap_se), float(term_se), ""


def matched_percentages(clean, first, second):
    columns = ["LapNumber", "lap_seconds", "Compound", "TyreLife"]
    a = clean.loc[clean.DriverNumber.eq(first), columns]
    b = clean.loc[clean.DriverNumber.eq(second), columns]
    shared = a.merge(b, on="LapNumber", suffixes=("_a", "_b"), validate="one_to_one")
    shared = shared.loc[shared.Compound_a.eq(shared.Compound_b)
                        & (shared.TyreLife_a - shared.TyreLife_b).abs().le(3)]
    shared = shared.sort_values("LapNumber")
    return (100 * (shared.lap_seconds_a - shared.lap_seconds_b) / shared.lap_seconds_b).to_numpy()


def holdout_stints(frame, first, second, keys):
    rows = []
    if frame.Stint.isna().any():
        return rows
    for (driver, stint), test in frame.groupby(["DriverNumber", "Stint"]):
        train = frame.loc[~(frame.DriverNumber.eq(driver) & frame.Stint.eq(stint))]
        record = dict(**keys, heldout_driver_number=driver, heldout_stint=stint,
                      test_laps=len(test), train_laps=len(train))
        for label, curved in [("linear", False), ("curved", True)]:
            model, reason = design_fit(train, first, second, curved)
            mae = NAN
            if not reason:
                try:
                    predictions = model["predict"](test)
                    mae = float(np.abs(test.lap_seconds.to_numpy() - predictions).mean())
                except ValueError as error:
                    reason = str(error)
            record[f"{label}_mae_seconds"] = mae
            record[f"{label}_reason_code"] = reason
        record["common_valid_fold"] = not record["linear_reason_code"] and not record["curved_reason_code"]
        rows.append(record)
    return rows


def prediction_summary(folds, races):
    rows = []
    for number, name in list(races) + [(0, "Overall")]:
        subset = folds if number == 0 else folds.loc[folds.round_number.eq(number)]
        common = subset.loc[subset.common_valid_fold]
        count = int(common.test_laps.sum())
        linear = float((common.linear_mae_seconds * common.test_laps).sum() / count) if count else NAN
        curved = float((common.curved_mae_seconds * common.test_laps).sum() / count) if count else NAN
        rows.append(dict(round_number=number, race=name, attempted_folds=len(subset),
                         common_valid_folds=len(common), heldout_laps=count,
                         linear_mae_seconds=linear, curved_mae_seconds=curved,
                         curved_minus_linear_seconds=curved-linear,
                         better_model=("linear" if linear < curved else "curved" if curved < linear else "tie")
                         if count else "unavailable"))
    return pd.DataFrame(rows)


def zero_lap_audit(race, clean, pair, source, root):
    rows = []
    roster = race.roster.set_index("Abbreviation")
    result_path = root / "data" / f"2025_{race.round_number:02}_{race.race.replace(' ', '_')}.csv"
    result_csv = pd.read_csv(result_path)
    for driver, clean_count in [(pair["driver"], pair["driver_clean_laps"]),
                                (pair["teammate"], pair["teammate_clean_laps"])]:
        if clean_count != 0:
            continue
        number = roster.loc[driver, "DriverNumber"]
        assert not clean.DriverNumber.eq(number).any()
        raw = race.laps.loc[race.laps.DriverNumber.eq(number)]
        actual = raw.loc[raw.FastF1Generated.eq(False)]
        timed = actual.loc[actual.LapTime.notna() & actual.LapTime.gt(pd.Timedelta(0))]
        maximum = float(raw.LapNumber.max()) if len(raw) else NAN
        status = source.loc[(source.round_number == race.round_number) & (source.driver == driver), "driver_status"].iloc[0]
        assert status == roster.loc[driver, "Status"]
        cause, detail = "unknown", "Status or records do not establish the cause"
        if status == "Retired" and pd.notna(maximum) and maximum <= 1 and len(timed) <= 1:
            cause, detail = "real_early_dnf", "Retired with at most one recorded lap; generated records are not completions"
        elif len(actual):
            cause, detail = "all_laps_filtered", "Non-generated laps exist, but none pass the clean filters"
        elif not len(raw) and (status == "Finished" or str(status).startswith("+")):
            cause, detail = "missing_data", "Classified finish without raw lap records"
        elif status in ["Did not start", "Absent from race results", "Withdrawn"]:
            detail = "Explicit non-start/absent entry; not labelled a DNF"
        official_row = result_csv.loc[result_csv.Abbreviation.eq(driver)]
        csv_status = official_row.iloc[0]["Status"] if len(official_row) and "Status" in official_row else ""
        rows.append(dict(round_number=race.round_number, race=race.race, team=pair["team"],
                         driver=driver, teammate=pair["teammate"] if driver == pair["driver"] else pair["driver"],
                         clean_laps=0, raw_lap_records=len(raw), non_generated_lap_records=len(actual),
                         completed_valid_timed_laps=len(timed), maximum_recorded_lap_number=maximum,
                         race_results_csv=str(result_path.relative_to(root)),
                         race_results_csv_row_present=bool(len(official_row)), race_results_csv_status=csv_status,
                         status_column_available="Status" in result_csv.columns,
                         finishing_status=status, status_source="data/2025_race_pace_teammate_gaps.csv:driver_status; checked against cached race results",
                         cause_code=cause, explanation=detail))
    return rows


def enhance_pair(pair, frame, first, second):
    result = dict(pair)
    result["final_confidence_v1"] = pair["final_confidence"]
    result["disagreement_flag_fixed_0p3"] = pair["disagreement_flag"]
    observations = matched_percentages(frame, first, second)
    for prefix in ["strict", "lowconf"]:
        if pd.notna(pair[f"{prefix}_gap"]):
            assert len(observations) == pair["matched_laps"]
            assert abs(np.median(observations) - pair[f"{prefix}_gap"]) <= .00000051
            se, low, high, reason = bootstrap_gap(observations)
        else:
            se, low, high, reason = NAN, NAN, NAN, "gap_unavailable"
        result.update({f"{prefix}_gap_se_pp": se, f"{prefix}_gap_ci_low": low,
                       f"{prefix}_gap_ci_high": high, f"{prefix}_gap_se_reason_code": reason})
    result["n_clusters"] = len(frame[["DriverNumber", "Stint"]].dropna().drop_duplicates())
    result["cluster_se_unreliable"] = result["n_clusters"] < 6
    result["stint_labels_complete"] = not frame.Stint.isna().any()
    for label in ["linear", "curved"]:
        if pd.notna(pair[f"regression_gap_{label}"]):
            se, term_se, reason = cluster_errors(frame, first, second, label == "curved")
        else:
            se, term_se, reason = NAN, NAN, "gap_unavailable"
        result[f"regression_gap_{label}_se_cluster_pp"] = se
        result[f"regression_{label}_driver_term_se_cluster_seconds"] = term_se
        result[f"regression_{label}_cluster_se_reason_code"] = reason
    method = pair["method_used"]
    result["final_gap_se_pp"] = result[METHOD_ERRORS[method]] if method in METHOD_ERRORS else NAN
    count = min(pair["driver_clean_laps"], pair["teammate_clean_laps"]) if method.startswith("regression") else pair["matched_laps"]
    result["final_lap_count"] = count
    result["final_confidence"] = confidence(pair["final_gap"], result["final_gap_se_pp"], count)
    flag, comparisons = uncertainty_disagreement(result)
    result["disagreement_flag"] = flag
    result["disagreement_comparisons"] = comparisons
    result["disagreement_reason_code"] = "" if comparisons else "insufficient_standard_errors"
    result["smallest_error_gap"], result["smallest_error_method"], result["smallest_error_se_pp"] = smallest_error(result)
    result["track_reliability_flag"] = "low_overtaking_limited" if pair["race"] == "Monaco Grand Prix" else ""
    return result


def summary_counts(output, prediction, audit):
    common = output.final_gap.notna() & output.smallest_error_gap.notna()
    delta = (output.loc[common, "final_gap"] - output.loc[common, "smallest_error_gap"]).abs()
    changed = delta.gt(1e-9)
    flags = output.disagreement_flag.fillna(False).astype(bool)
    return dict(confidence_counts=output.final_confidence.value_counts().to_dict(),
                fixed_disagreement=int(output.disagreement_flag_fixed_0p3.sum()),
                uncertainty_disagreement=int(flags.sum()),
                both_disagreement=int((flags & output.disagreement_flag_fixed_0p3).sum()),
                disagreement_unevaluable=int(output.disagreement_flag.isna().sum()),
                regression_pairs_with_small_clusters=int((output.regression_gap_linear.notna() & output.cluster_se_unreliable).sum()),
                smallest_error_common_pairs=int(common.sum()), smallest_error_different_gaps=int(changed.sum()),
                smallest_error_method_switches=int((output.loc[common, "method_used"] != output.loc[common, "smallest_error_method"]).sum()),
                smallest_error_mean_absolute_change_pp=float(delta.mean()),
                smallest_error_changed_only_mean_pp=float(delta.loc[changed].mean()),
                smallest_error_sign_flips=int((output.loc[common, "final_gap"] * output.loc[common, "smallest_error_gap"] < 0).sum()),
                prediction_overall=prediction.iloc[-1].to_dict(),
                audit_cause_counts=audit.cause_code.value_counts().to_dict())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    destination = args.output_dir or root / "data"
    names = ["race_pace_dry_combined_v2.csv", "race_pace_stint_holdout_v2.csv",
             "race_pace_prediction_check_v2.csv", "race_pace_zero_lap_audit.csv", "race_pace_dry_v2_summary.json"]
    if any((destination / name).exists() for name in names):
        raise FileExistsError("Use a new output directory; existing outputs will not be overwritten")
    baseline = pd.read_csv(root / "data/race_pace_dry_combined.csv", float_precision="round_trip")
    source = pd.read_csv(root / "data/2025_race_pace_teammate_gaps.csv")
    fastf1.Cache.enable_cache(str(root / "cache"))
    fastf1.Cache.offline_mode(True)
    fastf1.set_log_level("ERROR")
    schedule = fastf1.get_event_schedule(2025, include_testing=False)
    rows, folds, audits, races = [], [], [], []
    for number, existing in baseline.groupby("round_number", sort=False):
        event = schedule.loc[schedule.RoundNumber.eq(number)].iloc[0]
        race = laps_v1.load_race(event)
        assert not race.issue and race.race != "Miami Grand Prix"
        assert laps_v1.dry_race_status(race.laps, race.weather, race.start, race.end)[0] == "dry"
        clean = laps_v1.filter_clean_laps(race.laps)
        roster = race.roster.set_index("Abbreviation")
        races.append((int(number), race.race))
        for pair in existing.to_dict("records"):
            first, second = [roster.loc[pair[c], "DriverNumber"] for c in ["driver", "teammate"]]
            frame = clean.loc[clean.DriverNumber.isin([first, second])].copy().reset_index(drop=True)
            rows.append(enhance_pair(pair, frame, first, second))
            if pd.notna(pair["regression_gap_linear"]) and pd.notna(pair["regression_gap_curved"]):
                keys = {c: pair[c] for c in ["round_number", "race", "team", "driver", "teammate"]}
                folds.extend(holdout_stints(frame, first, second, keys))
            if min(pair["driver_clean_laps"], pair["teammate_clean_laps"]) == 0:
                audits.extend(zero_lap_audit(race, clean, pair, source, root))
        print(f"Checked {race.race}", flush=True)
    output, fold_table, audit = pd.DataFrame(rows), pd.DataFrame(folds), pd.DataFrame(audits)
    pd.testing.assert_series_equal(output.final_gap, baseline.final_gap, check_exact=True)
    prediction = prediction_summary(fold_table, races)
    summary = summary_counts(output, prediction, audit)
    destination.mkdir(exist_ok=True, parents=True)
    for name, table in zip(names, [output, fold_table, prediction, audit]):
        with (destination / name).open("x") as stream:
            table.to_csv(stream, index=False)
    with (destination / names[-1]).open("x") as stream:
        json.dump(summary, stream, indent=2)
    print(json.dumps(summary, indent=2))
    print(prediction.to_string(index=False))


if __name__ == "__main__":
    main()
