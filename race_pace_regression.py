"""Dry race pace using two fixed regressions; see RACEPACE_REGRESSION_METHOD.md."""
import argparse
from pathlib import Path

import fastf1
import numpy as np
import pandas as pd

import race_pace_gaps as matched


MIN_CLEAN = 10
MIN_SHARED_COMPOUND = 8
MAX_CONDITION = 1000
DISAGREEMENT_PP = 0.3
NAN = float("nan")


def fit_pair(clean, driver_number, teammate_number, curved=False):
    """Fit seconds, then standardise both drivers to the same conditions."""
    a = clean.loc[clean.DriverNumber.eq(driver_number)]
    b = clean.loc[clean.DriverNumber.eq(teammate_number)]
    frame = pd.concat([a, b], ignore_index=True)
    common = sorted(set(a.Compound) & set(b.Compound))
    counts = [(c, int(a.Compound.eq(c).sum()), int(b.Compound.eq(c).sum())) for c in common]
    confounded = not any(x >= MIN_SHARED_COMPOUND and y >= MIN_SHARED_COMPOUND
                         for _, x, y in counts)
    reasons = []
    if confounded:
        reasons.append("strategy_confounded")
    if min(len(a), len(b)) < MIN_CLEAN:
        reasons.append("too_few_clean_laps")
    result = dict(gap_pct=NAN, gap_se_pp=NAN, unreliable_gap_pct=NAN,
                  unreliable_gap_se_pp=NAN, driver_term_seconds=NAN,
                  driver_term_se_seconds=NAN, reference_teammate_seconds=NAN,
                  driver_clean_laps=len(a), teammate_clean_laps=len(b),
                  shared_compound_counts="; ".join(f"{c}:{x}/{y}" for c, x, y in counts),
                  strategy_confounded=confounded, condition_number=NAN,
                  residual_df=NAN, residual_sd_seconds=NAN, reason_code="", all_reason_codes="")

    def finish(extra=None):
        if extra:
            reasons.append(extra)
        result["reason_code"] = reasons[0] if reasons else ""
        result["all_reason_codes"] = ";".join(reasons)
        return result

    if a.empty or b.empty:
        return finish("effects_not_identifiable")
    # A driver value of one means the first named driver; zero is their teammate.
    columns = [np.ones(len(frame)), frame.DriverNumber.eq(driver_number).astype(float).to_numpy()]
    compounds = sorted(frame.Compound.unique())
    columns += [frame.Compound.eq(c).astype(float).to_numpy() for c in compounds[1:]]
    for name in ["TyreLife", "LapNumber"]:
        values = frame[name].to_numpy(dtype=float)
        centred = values - values.mean()
        columns.append(centred)
        if curved:
            columns.append(centred ** 2)
    x = np.column_stack(columns)
    y = frame.lap_seconds.to_numpy(dtype=float)
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        return finish("fit_failed")
    means, scales = x[:, 1:].mean(axis=0), x[:, 1:].std(axis=0)
    if (scales == 0).any() or len(x) <= x.shape[1]:
        return finish("effects_not_identifiable")
    # Fit on a scaled matrix and transform coefficients back into seconds.
    z = np.column_stack([np.ones(len(x)), (x[:, 1:] - means) / scales])
    transform = np.eye(x.shape[1])
    transform[0, 1:] = -means / scales
    transform[1:, 1:] = np.diag(1 / scales)
    try:
        scaled_beta, _, rank, singular = np.linalg.lstsq(z, y, rcond=None)
        if rank < z.shape[1]:
            return finish("effects_not_identifiable")
        condition = float(singular[0] / singular[-1])
        result["condition_number"] = condition
        if condition > MAX_CONDITION:
            reasons.append("fit_ill_conditioned")
        beta = transform @ scaled_beta
        residual = y - z @ scaled_beta
        df = len(y) - rank
        variance = float(residual @ residual / df)
        # The usual OLS covariance does not correct serially correlated laps.
        _, s, vt = np.linalg.svd(z, full_matrices=False)
        scaled_covariance = variance * (vt.T * (1 / s ** 2)) @ vt
        covariance = transform @ scaled_covariance @ transform.T
        reference = (x[:len(a)].mean(axis=0) + x[len(a):].mean(axis=0)) / 2
        reference[1] = 0
        denominator = float(reference @ beta)
        result.update(driver_term_seconds=float(beta[1]),
                      driver_term_se_seconds=float(np.sqrt(max(0, covariance[1, 1]))),
                      reference_teammate_seconds=denominator, residual_df=df,
                      residual_sd_seconds=float(np.sqrt(variance)))
        if not np.isfinite(denominator) or denominator <= 0 or denominator + beta[1] <= 0:
            return finish("invalid_reference_time")
        gap = float(100 * beta[1] / denominator)
        gradient = -100 * beta[1] * reference / denominator ** 2
        gradient[1] += 100 / denominator
        gap_se = float(np.sqrt(max(0, gradient @ covariance @ gradient)))
        if not np.isfinite([gap, gap_se]).all():
            return finish("fit_failed")
        if reasons:
            result.update(unreliable_gap_pct=gap, unreliable_gap_se_pp=gap_se)
        else:
            result.update(gap_pct=gap, gap_se_pp=gap_se)
    except np.linalg.LinAlgError:
        return finish("fit_failed")
    return finish()


def choose_final(row):
    """Use the requested order, including a valid zero gap."""
    for name, confidence in [("strict_gap", "high"), ("regression_gap_linear", "medium"),
                             ("lowconf_gap", "low")]:
        if pd.notna(row[name]):
            return row[name], name, confidence
    return NAN, "unavailable", "unavailable"


def disagreement(row):
    values = [row[name] for name in ["strict_gap", "lowconf_gap", "regression_gap_linear",
                                   "regression_gap_curved"] if pd.notna(row[name])]
    return len(values) >= 2 and max(values) - min(values) > DISAGREEMENT_PP


def comparison_summary(table):
    both = table.regression_gap_linear.notna() & table.regression_gap_curved.notna()
    linear = table.loc[both, "regression_gap_linear"]
    curved = table.loc[both, "regression_gap_curved"]
    return {
        "common_pairs": int(both.sum()),
        "linear_mean_absolute_gap_pct": float(linear.abs().mean()),
        "curved_mean_absolute_gap_pct": float(curved.abs().mean()),
        "curved_minus_linear_mean_absolute_gap_pp": float(curved.abs().mean() - linear.abs().mean()),
        "mean_absolute_between_model_difference_pp": float((curved - linear).abs().mean()),
    }


def analyse_race(race, existing):
    clean = matched.filter_clean_laps(race.laps)
    strict = matched.pair_view(pd.DataFrame(matched.paired_rows(race)))
    relaxed = matched.pair_view(pd.DataFrame(matched.paired_rows(race, min_matched_laps=3)))
    combined, models = [], {"linear": [], "curved": []}
    roster = race.roster.set_index("Abbreviation")
    for row in strict.itertuples():
        keys = dict(round_number=race.round_number, race=race.race, team=row.team,
                    driver=row.driver, teammate=row.teammate)
        old = existing.loc[(existing.round_number == race.round_number)
                           & (existing.driver == row.driver) & (existing.teammate == row.teammate)]
        if len(old) != 1:
            raise ValueError(f"Missing or duplicate baseline pair: {keys}")
        old = old.iloc[0]
        assert old.matched_laps == row.matched_laps
        assert pd.isna(old.gap_pct) == pd.isna(row.gap_pct)
        if pd.notna(old.gap_pct):
            assert abs(old.gap_pct - row.gap_pct) <= 0.00000051
        small = relaxed.loc[relaxed.driver.eq(row.driver)].iloc[0]
        entry = dict(**keys, matched_laps=row.matched_laps, strict_gap=old.gap_pct,
                     strict_gap_se_pp=NAN, lowconf_gap=small.gap_pct if 3 <= row.matched_laps <= 9 else NAN,
                     lowconf_gap_se_pp=NAN, driver_clean_laps=row.driver_clean_laps,
                     teammate_clean_laps=row.teammate_clean_laps)
        external_reason = row.reason_code if row.reason_code in ["race_disqualification", "no_race_laps"] else ""
        for label in models:
            if external_reason:
                result = dict(gap_pct=NAN, gap_se_pp=NAN, unreliable_gap_pct=NAN,
                              unreliable_gap_se_pp=NAN, driver_term_seconds=NAN,
                              driver_term_se_seconds=NAN, reason_code=external_reason,
                              all_reason_codes=external_reason)
            else:
                result = fit_pair(clean, roster.loc[row.driver, "DriverNumber"],
                                  roster.loc[row.teammate, "DriverNumber"], curved=label == "curved")
            models[label].append(dict(**keys, model=label, **result))
            entry[f"regression_gap_{label}"] = result["gap_pct"]
            entry[f"regression_gap_{label}_se_pp"] = result["gap_se_pp"]
            entry[f"regression_{label}_driver_term_se_seconds"] = result["driver_term_se_seconds"]
            entry[f"regression_{label}_reason_code"] = result["reason_code"]
            entry[f"regression_{label}_unreliable_gap"] = result["unreliable_gap_pct"]
        entry["final_gap"], entry["method_used"], entry["final_confidence"] = choose_final(entry)
        entry["reason_code"] = (external_reason or entry["regression_linear_reason_code"]
                                or "too_few_matched_laps") if pd.isna(entry["final_gap"]) else ""
        entry["disagreement_flag"] = disagreement(entry)
        combined.append(entry)
    return combined, models


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, help="Use a new directory for another run")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    destination = args.output_dir or root / "data"
    names = ["race_pace_dry_combined.csv", "race_pace_regression_linear.csv",
             "race_pace_regression_curved.csv", "race_pace_regression_comparison.csv"]
    targets = [destination / name for name in names]
    if any(p.exists() for p in targets):
        raise FileExistsError("Refusing to overwrite outputs. Choose a new --output-dir.")
    existing = pd.read_csv(root / "data/2025_race_pace_teammate_gaps.csv")
    fastf1.Cache.enable_cache(str(root / "cache"))
    fastf1.Cache.offline_mode(True)
    fastf1.set_log_level("ERROR")
    all_rows, all_models = [], {"linear": [], "curved": []}
    for _, event in fastf1.get_event_schedule(2025, include_testing=False).iterrows():
        # Miami is excluded explicitly, including if the cache later changes.
        if event.EventName == "Miami Grand Prix":
            continue
        race = matched.load_race(event)
        if race.issue:
            raise ValueError(f"{race.race}: {race.issue}")
        dry, reason = matched.dry_race_status(race.laps, race.weather, race.start, race.end)
        if dry == "unknown":
            raise ValueError(f"Unknown race classification: {race.race}: {reason}")
        if dry != "dry":
            continue
        rows, models = analyse_race(race, existing)
        all_rows.extend(rows)
        for label in all_models:
            all_models[label].extend(models[label])
        print(f"Analysed {race.race}", flush=True)
    output = pd.DataFrame(all_rows)
    comparison = comparison_summary(output)
    frames = [output, pd.DataFrame(all_models["linear"]), pd.DataFrame(all_models["curved"]),
              pd.DataFrame([comparison])]
    destination.mkdir(parents=True, exist_ok=True)
    for target, frame in zip(targets, frames):
        with target.open("x") as stream:
            frame.to_csv(stream, index=False, float_format="%.9f")
    print(f"\nDry races: {output.round_number.nunique()}; pairs: {len(output)}")
    for name in ["strict_gap", "regression_gap_linear", "lowconf_gap", "unavailable"]:
        print(f"{name}: {output.method_used.eq(name).sum()}")
    print("Blank reasons:", output.loc[output.final_gap.isna(), "reason_code"].value_counts().to_dict())
    print("Disagreement flags:", int(output.disagreement_flag.sum()))
    print("Linear available:", output.regression_gap_linear.notna().sum(),
          "Curved available:", output.regression_gap_curved.notna().sum())
    print("Model comparison:", comparison)


if __name__ == "__main__":
    main()
