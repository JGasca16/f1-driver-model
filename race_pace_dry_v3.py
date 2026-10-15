"""Stint block uncertainty for the official linear estimate; preserve v1 gaps."""
import argparse
import json
import time
from pathlib import Path

import fastf1
import numpy as np
import pandas as pd

import race_pace_gaps as laps_v1
import race_pace_regression as regression_v1
import race_pace_dry_v2 as v2
from diagnose_race_pace_blocked import failure_flags

RESAMPLES = 2000
SEED = 42
LINEAR_BLOCK = 5
SHORT_BLOCK = 2
MAX_SECONDS = 900
NAN = float("nan")


class BootstrapClock:
    """Stop conservatively 15 minutes after the first bootstrap starts."""
    def __init__(self):
        self.start = None
        self.compute_seconds = 0.

    def check(self):
        now = time.perf_counter()
        if self.start is None:
            self.start = now
        if now - self.start > MAX_SECONDS:
            raise TimeoutError(f"Bootstrap window exceeded {MAX_SECONDS} seconds: {now-self.start:.3f}s")


def stint_blocks(frame):
    """Keep short stints and short final chunks; never cross driver/stint."""
    groups = []
    for _, group in frame.groupby(["DriverNumber", "Stint"], sort=True):
        positions = group.sort_values("LapNumber").index.to_numpy()
        groups.append([positions[i:i+LINEAR_BLOCK] for i in range(0, len(positions), LINEAR_BLOCK)])
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
    """Algebraically the same seconds model and reference as v1, without pandas."""
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


def regression_bootstrap(frame, first, second, seed=SEED, clock=None):
    result = dict(regression_gap_linear_se_block_pp=NAN, regression_gap_linear_ci_low=NAN,
                  regression_gap_linear_ci_high=NAN, resamples_attempted=0, resamples_skipped=0,
                  resamples_valid=0, resample_skip_reasons="", regression_block_reason_code="")
    if frame.Stint.isna().any():
        result["regression_block_reason_code"] = "stint_unknown"
        return result
    check = regression_v1.fit_pair(frame, first, second)
    if check["reason_code"]:
        raise ValueError(f"Accepted v1 model changed: {check['reason_code']}")
    frame = frame.reset_index(drop=True)
    z, y, is_first, mean, scale = linear_arrays(frame, first)
    original, reason = refit_percentage(z, y, is_first, mean, scale)
    assert not reason and abs(original - check["gap_pct"]) < 1e-8
    groups = stint_blocks(frame)
    rng = np.random.default_rng(seed)
    choices = [rng.integers(0, len(group), size=(RESAMPLES, len(group))) for group in groups]
    values, skips = [], {}
    for i in range(RESAMPLES):
        if clock:
            clock.check()
        indexes = np.concatenate([block_group[j] for block_group, draws in zip(groups, choices)
                                  for j in draws[i]])
        gap, reason = refit_percentage(z[indexes], y[indexes], is_first[indexes], mean, scale)
        if reason:
            skips[reason] = skips.get(reason, 0) + 1
        else:
            values.append(gap)
    result.update(resamples_attempted=RESAMPLES, resamples_skipped=RESAMPLES-len(values),
                  resamples_valid=len(values), resample_skip_reasons=json.dumps(skips, sort_keys=True))
    if len(values) < 2:
        result["regression_block_reason_code"] = "too_few_valid_resamples"
    else:
        low, high = np.percentile(values, [2.5, 97.5], method="linear")
        result.update(regression_gap_linear_se_block_pp=float(np.std(values, ddof=1)),
                      regression_gap_linear_ci_low=float(low), regression_gap_linear_ci_high=float(high))
    return result


def short_bootstrap(values, seed=SEED, clock=None):
    values = np.asarray(values, dtype=float)
    if len(values) < 3 or not np.isfinite(values).all():
        return NAN, NAN, NAN, "insufficient_or_invalid_matched_laps"
    if clock:
        clock.check()
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, len(values)-SHORT_BLOCK+1,
                          size=(RESAMPLES, int(np.ceil(len(values)/SHORT_BLOCK))))
    indexes = (starts[:, :, None] + np.arange(SHORT_BLOCK)).reshape(RESAMPLES, -1)
    medians = np.median(values[indexes[:, :len(values)]], axis=1)
    low, high = np.percentile(medians, [2.5, 97.5], method="linear")
    if clock:
        clock.check()
    return float(medians.std(ddof=1)), float(low), float(high), ""


def new_error_view(row):
    """Use v2's tested comparison rules with v3 errors, without changing v2."""
    view = dict(row)
    view["regression_gap_linear_se_cluster_pp"] = row["regression_gap_linear_se_block_pp"]
    view["lowconf_gap_se_pp"] = row["lowconf_gap_se_pp_v3"]
    return view


def untestable_reason(row, use_v3):
    view = new_error_view(row) if use_v3 else row
    n_estimates = sum(pd.notna(row[name]) for name in v2.METHOD_ERRORS)
    if len(v2.available_errors(view)) >= 2:
        return ""
    if n_estimates == 0:
        return "no_gap_at_all"
    return "only_one_estimate_available" if n_estimates == 1 else "estimate_missing_error"


def apply_labels(row):
    view = new_error_view(row)
    method = row["method_used"]
    row["final_gap_se_pp"] = view[v2.METHOD_ERRORS[method]] if method in v2.METHOD_ERRORS else NAN
    row["final_confidence"] = v2.confidence(row["final_gap"], row["final_gap_se_pp"], row["final_lap_count"])
    row["disagreement_flag"], row["disagreement_comparisons"] = v2.uncertainty_disagreement(view)
    row["disagreement_reason_code"] = "" if row["disagreement_comparisons"] else "insufficient_standard_errors"
    row["smallest_error_gap"], row["smallest_error_method"], row["smallest_error_se_pp"] = v2.smallest_error(view)
    row["untestable_reason_v3"] = untestable_reason(row, True)
    return row


def audit_all_filtered(race, audit_row):
    roster = race.roster.set_index("Abbreviation")
    number = roster.loc[audit_row.driver, "DriverNumber"]
    raw = race.laps.loc[race.laps.DriverNumber.eq(number)]
    flags, ordered = failure_flags(raw)
    assert laps_v1.filter_clean_laps(raw).empty
    order = {"lap1": flags.lap1_or_invalid_number, "pit": flags.pit,
             "sc_vsc_red": flags.sc_vsc_red, "yellow": flags.yellow,
             "deleted": flags.deleted_or_unknown}
    order["other"] = flags.drop(columns="LapNumber").any(axis=1)
    keep = pd.Series(True, index=ordered.index)
    removed_by = pd.Series("", index=ordered.index)
    counts = {}
    for name, failed in order.items():
        removed = keep & failed
        counts[f"removed_{name}"] = int(removed.sum())
        removed_by.loc[removed] = name
        keep &= ~failed
    assert not keep.any() and sum(counts.values()) == len(raw)
    largest = max(counts.values())
    most = ";".join(name.removeprefix("removed_") for name, count in counts.items() if count == largest)
    details = []
    for index, lap in ordered.iterrows():
        details.append(dict(round_number=race.round_number, race=race.race, driver=audit_row.driver,
                            lap_number=lap.LapNumber, charged_filter=removed_by.loc[index],
                            all_failed_checks=";".join(c for c in flags.columns if c != "LapNumber" and flags.loc[index, c]),
                            track_status=lap.TrackStatus, pit_in=str(lap.PitInTime), pit_out=str(lap.PitOutTime),
                            lap_time=str(lap.LapTime), generated=lap.FastF1Generated,
                            accurate=lap.IsAccurate, deleted=lap.Deleted))
    evidence = " | ".join(f"lap {d['lap_number']:g}: {d['charged_filter']} [{d['all_failed_checks']}]" for d in details)
    conclusion = ("Consistent with recorded exclusions during a short retired race; no evidence here of a filter bug. "
                  "Buffers remain conservative; records alone do not establish crash/mechanical cause.")
    if counts["removed_other"]:
        conclusion = ("Most exclusions are explicit in the records, but review the 'other' evidence for accuracy/partial-lap effects. "
                      "The raw sample is too short to justify relaxing filters; no changes made.")
    return dict(round_number=race.round_number, race=race.race, driver=audit_row.driver,
                teammate=audit_row.teammate, finishing_status=audit_row.finishing_status,
                raw_lap_count=len(raw), **counts, clean_laps=0, largest_filter=most,
                evidence=evidence, assessment=conclusion), details


def make_summary(output, old, audit, clock, started):
    fixed = output.disagreement_flag_fixed_0p3.fillna(False).astype(bool)
    prev = output.disagreement_flag_v2.fillna(False).astype(bool)
    new = output.disagreement_flag.fillna(False).astype(bool)
    common = output.final_gap.notna() & output.smallest_error_gap.notna()
    delta = (output.loc[common, "smallest_error_gap"] - output.loc[common, "final_gap"]).abs()
    def breakdown(column):
        values = output[column].value_counts().to_dict()
        return {key: int(values.get(key, 0)) for key in ["only_one_estimate_available", "estimate_missing_error", "no_gap_at_all"]}
    return dict(label_counts=output.final_confidence.value_counts().to_dict(),
                changed_labels=int(output.final_confidence.ne(old.final_confidence).sum()),
                flag_counts=dict(fixed=int(fixed.sum()), v2=int(prev.sum()), v3=int(new.sum())),
                flag_overlaps=dict(fixed_v2=int((fixed & prev).sum()), fixed_v3=int((fixed & new).sum()),
                                   v2_v3=int((prev & new).sum()), all_three=int((fixed & prev & new).sum())),
                untestable_v2=breakdown("untestable_reason_v2"), untestable_v3=breakdown("untestable_reason_v3"),
                smallest_error_counts=output.smallest_error_method.value_counts().to_dict(),
                smallest_error_common_pairs=int(common.sum()),
                smallest_error_changed_gaps=int(delta.gt(1e-9).sum()),
                smallest_error_mean_absolute_change_pp=float(delta.mean()),
                smallest_error_changed_only_mean_pp=float(delta.loc[delta.gt(1e-9)].mean()),
                smallest_error_sign_flips=int((output.loc[common, "smallest_error_gap"] * output.loc[common, "final_gap"] < 0).sum()),
                skipped_resamples=int(output.resamples_skipped.fillna(0).sum()),
                pairs_with_skipped_resamples=int(output.resamples_skipped.fillna(0).gt(0).sum()),
                all_filtered_audit=audit.to_dict("records"),
                bootstrap_compute_seconds=clock.compute_seconds,
                bootstrap_window_seconds=time.perf_counter()-clock.start if clock.start else 0,
                total_runtime_seconds=time.perf_counter()-started)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    started, clock = time.perf_counter(), BootstrapClock()
    root = Path(__file__).resolve().parent
    destination = args.output_dir or root / "data"
    names = ["race_pace_dry_combined_v3.csv", "race_pace_all_filtered_audit.csv",
             "race_pace_all_filtered_laps_v3.csv", "race_pace_dry_v3_summary.json"]
    if any((destination / name).exists() for name in names):
        raise FileExistsError("Existing outputs cannot be overwritten; use a new --output-dir")
    baseline = pd.read_csv(root / "data/race_pace_dry_combined_v2.csv", float_precision="round_trip")
    audit_source = pd.read_csv(root / "data/race_pace_zero_lap_audit.csv")
    audit_source = audit_source.loc[audit_source.cause_code.eq("all_laps_filtered")]
    assert len(audit_source) == 4
    fastf1.Cache.enable_cache(str(root / "cache"))
    fastf1.Cache.offline_mode(True)
    fastf1.set_log_level("ERROR")
    schedule = fastf1.get_event_schedule(2025, include_testing=False)
    rows, audits, details = [], [], []
    try:
        for number, pairs in baseline.groupby("round_number", sort=False):
            race = laps_v1.load_race(schedule.loc[schedule.RoundNumber.eq(number)].iloc[0])
            assert not race.issue and race.race != "Miami Grand Prix"
            assert laps_v1.dry_race_status(race.laps, race.weather, race.start, race.end)[0] == "dry"
            clean = laps_v1.filter_clean_laps(race.laps)
            roster = race.roster.set_index("Abbreviation")
            for original in pairs.to_dict("records"):
                row = dict(original)
                for name in ["final_confidence", "disagreement_flag", "final_gap_se_pp", "disagreement_comparisons",
                             "disagreement_reason_code", "smallest_error_gap", "smallest_error_method",
                             "smallest_error_se_pp", "lowconf_gap_ci_low", "lowconf_gap_ci_high"]:
                    row[name+"_v2"] = original[name]
                row["official_regression_version"] = "linear"
                row["untestable_reason_v2"] = untestable_reason(original, False)
                first, second = [roster.loc[row[c], "DriverNumber"] for c in ["driver", "teammate"]]
                frame = clean.loc[clean.DriverNumber.isin([first, second])].reset_index(drop=True)
                if pd.notna(row["regression_gap_linear"]):
                    clock.check()
                    mark = time.perf_counter()
                    try:
                        row.update(regression_bootstrap(frame, first, second, clock=clock))
                    finally:
                        clock.compute_seconds += time.perf_counter()-mark
                else:
                    row.update(regression_gap_linear_se_block_pp=NAN, regression_gap_linear_ci_low=NAN,
                               regression_gap_linear_ci_high=NAN, resamples_attempted=0, resamples_skipped=0,
                               resamples_valid=0, resample_skip_reasons="", regression_block_reason_code="gap_unavailable")
                if pd.notna(row["lowconf_gap"]):
                    values = v2.matched_percentages(frame, first, second)
                    assert len(values) == row["matched_laps"]
                    assert abs(np.median(values)-row["lowconf_gap"]) <= 1e-8
                    clock.check()
                    mark = time.perf_counter()
                    try:
                        se, low, high, reason = short_bootstrap(values, clock=clock)
                    finally:
                        clock.compute_seconds += time.perf_counter()-mark
                    row["lowconf_se_method"] = "block2"
                else:
                    se, low, high, reason = NAN, NAN, NAN, "gap_unavailable"
                    row["lowconf_se_method"] = ""
                row.update(lowconf_gap_se_pp_v3=se, lowconf_gap_ci_low=low, lowconf_gap_ci_high=high,
                           lowconf_gap_se_reason_code_v3=reason)
                rows.append(apply_labels(row))
            for target in audit_source.loc[audit_source.round_number.eq(number)].itertuples():
                report, evidence = audit_all_filtered(race, target)
                audits.append(report)
                details.extend(evidence)
            print(f"Checked {race.race}; bootstrap compute {clock.compute_seconds:.1f}s", flush=True)
    except TimeoutError as error:
        destination.mkdir(parents=True, exist_ok=True)
        report = dict(error=str(error), total_runtime_seconds=time.perf_counter()-started,
                      bootstrap_compute_seconds=clock.compute_seconds)
        with (destination / "race_pace_dry_v3_timeout.json").open("x") as stream:
            json.dump(report, stream, indent=2)
        print(json.dumps(report))
        return 1
    output, audit = pd.DataFrame(rows), pd.DataFrame(audits)
    pd.testing.assert_series_equal(output.final_gap, baseline.final_gap, check_exact=True)
    summary = make_summary(output, baseline, audit, clock, started)
    destination.mkdir(parents=True, exist_ok=True)
    for name, table in zip(names, [output, audit, pd.DataFrame(details)]):
        with (destination / name).open("x") as stream:
            table.to_csv(stream, index=False)
    summary["total_runtime_seconds"] = time.perf_counter()-started
    with (destination / names[-1]).open("x") as stream:
        json.dump(summary, stream, indent=2)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
