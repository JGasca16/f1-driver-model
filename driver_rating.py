"""Teammate season ratings. Fixed choices: DRIVER_RATING_METHOD.md.

The log-round correction changes qualifying combination only: its input is
already in log-percentage points and is read directly for each named driver.
Dry/wet percentage conversion and every other approved rule stay unchanged.
"""
import argparse
from collections import Counter
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd

from qualifying_gaps_combined import (
    InvalidGap, combine_table, is_blank, read_csv, valid_gap, write_csv_new,
    FILENAME as QUALIFYING_FILENAME,
)

from season_config import DEFAULT, add_season_arguments, from_args

ROOT = Path(__file__).resolve().parent
YEAR = DEFAULT.year
SIGNALS = ("qualifying", "dry", "wet")
WET_ROUNDS = {int(n) for n in DEFAULT.facts["wet_races"]}
DRY_ROUNDS = set(DEFAULT.facts["dry_rounds"])
RESAMPLES = 2000
SEED = 42
MIN_CI_WEEKENDS = 6
MIN_BOOTSTRAP_FRACTION = 0.95
ARITHMETIC_TOLERANCE = 1e-12
METHOD_VERSION = DEFAULT.facts["method_id"]
SOURCES = DEFAULT.sources()
COLUMNS = "season driver teams teammates comparison_group teammate_changed season_appearances qualifying_rating dry_rating wet_rating combined_rating rating_units rating_status qualifying_weight dry_weight wet_weight qualifying_valid qualifying_eligible qualifying_effective_races dry_valid dry_eligible dry_effective_races wet_valid wet_eligible wet_effective_races races_included confidence combined_ci_low combined_ci_high bootstrap_valid qualifying_median dry_median wet_median dry_strict_count dry_linear_count monaco_included notes method_version source_files".split()
OUTPUT_KEYS = ["qualifying", "ratings", "sensitivity", "signal_diagnostics",
               "teammate_periods", "input_audit", "rating_summary"]
OUTPUT_NAMES = [DEFAULT.filename(k) for k in OUTPUT_KEYS]


@dataclass(frozen=True)
class Settings:
    signal_weights: tuple = (0.45, 0.45, 0.10)
    reference_races: tuple = (8, 8, 3)
    monaco_multiplier: float = 0.5


def log_pair(gap, se=None):
    """Only one orientation enters; both drivers share one uncertainty."""
    gap = valid_gap(gap)
    if gap is None:
        return np.nan, np.nan, np.nan
    contribution = float(100 * np.log1p(gap / 100))
    converted_se = np.nan
    if not is_blank(se):
        try:
            number = float(se)
            if np.isfinite(number) and number >= 0:
                converted_se = number / (1 + gap / 100)
        except (TypeError, ValueError):
            pass
    return contribution, -contribution, converted_se


def observation_weight(signal, se_log, race, settings=Settings()):
    """Monaco changes dry evidence weight, never the measured gap."""
    if signal == "qualifying":
        return 1.0
    weight = max(0.25, 1 / (1 + (se_log / 0.15) ** 2)) if np.isfinite(se_log) else 0.25
    if signal == "dry" and race == "Monaco Grand Prix":
        weight *= settings.monaco_multiplier
    return float(weight)


def effective_races(weights):
    weights = np.asarray(weights, dtype=float)
    return float(weights.sum() ** 2 / np.square(weights).sum()) if weights.size and weights.sum() else 0.0


def evidence_factor(effective, reference):
    return np.minimum(1.0, np.asarray(effective) / reference)


def support_met(effective, coverage, minimum, fraction):
    return effective + ARITHMETIC_TOLERANCE >= minimum and coverage + ARITHMETIC_TOLERANCE >= fraction


def rating_status(qualifying, dry, q_effective, d_effective, q_coverage, d_coverage):
    if not np.isfinite(qualifying) and not np.isfinite(dry):
        return "unavailable"
    if support_met(q_effective, q_coverage, 6, .50) and support_met(d_effective, d_coverage, 6, .50):
        return "established"
    return "provisional"


def confidence_label(score, q_effective, d_effective, q_coverage, d_coverage, usable_ci):
    if not np.isfinite(score):
        return "unavailable"
    if usable_ci:
        if support_met(q_effective, q_coverage, 12, .75) and support_met(d_effective, d_coverage, 12, .75):
            return "high"
        if support_met(q_effective, q_coverage, 6, .50) and support_met(d_effective, d_coverage, 6, .50):
            return "medium"
    return "low/provisional"


def check_roster(qualifying, season_settings=None):
    """Qualifying, including blanks, defines appearances and teammate periods."""
    cfg = season_settings or DEFAULT
    roster = qualifying[["round_number", "race", "team", "driver", "teammate"]].copy()
    roster["round_number"] = roster.round_number.astype(int)
    if (set(roster.round_number) != set(range(1, cfg.facts["round_count"] + 1))
            or len(roster) != cfg.facts["expected_appearances"]
            or roster.driver.nunique() != cfg.facts["expected_unique_drivers"]):
        raise ValueError("Season appearances or driver counts differ from the verified manifest")
    if roster.duplicated(["round_number", "driver"]).any():
        raise ValueError("Repeated driver in qualifying roster")
    for (_, _), group in roster.groupby(["round_number", "team"]):
        if len(group) != cfg.facts["team_size"] or set(group.driver) != set(group.teammate):
            raise ValueError("Incomplete or asymmetric teammate roster")
    for number, group in roster.groupby("round_number"):
        if len(group) != cfg.facts["expected_entries"] or group.race.nunique() != 1:
            raise ValueError(f"Invalid roster for round {number}")
        teammate_map = dict(zip(group.driver, group.teammate))
        expected = {p["driver"]: p["teammate"] for p in cfg.facts["roster_periods"]
                    if p["first"] <= number <= p["last"]}
        for driver, teammate in expected.items():
            if teammate_map.get(driver) != teammate:
                raise ValueError(f"Approved teammate-period table disagrees at round {number}: {driver}")
    roster = roster.sort_values(["driver", "round_number"]).reset_index(drop=True)
    # A new period begins when the driver's team or opponent changes.
    roster["period"] = 0
    for _, group in roster.groupby("driver", sort=True):
        changed = group.team.ne(group.team.shift()) | group.teammate.ne(group.teammate.shift())
        roster.loc[group.index, "period"] = changed.cumsum().to_numpy()
    return roster


def comparison_groups(roster):
    neighbours = {driver: set() for driver in roster.driver.unique()}
    for row in roster.itertuples():
        neighbours[row.driver].add(row.teammate)
    groups = {}
    for driver in sorted(neighbours):
        if driver in groups:
            continue
        members, pending = set(), [driver]
        while pending:
            current = pending.pop()
            if current not in members:
                members.add(current)
                pending.extend(neighbours[current] - members)
        label = "+".join(sorted(members))
        groups.update({member: label for member in members})
    return groups


def validate_qualifying_rows(source, combined):
    """Check both already-symmetric rows without choosing a reference driver."""
    keys = ["round_number", "driver"]
    indexed = combined.set_index(keys)
    if not indexed.index.is_unique or set(indexed.index) != set(source.set_index(keys).index):
        raise ValueError("Combined qualifying roster differs from the source")
    discrepancies = []
    seen = set()
    for row in combined.to_dict("records"):
        number, driver, teammate = row["round_number"], row["driver"], row["teammate"]
        reverse = indexed.loc[(number, teammate)]
        if reverse.teammate != driver or reverse.team != row["team"] or reverse.race != row["race"]:
            raise ValueError("Combined qualifying reverse identities differ")
        if row["reason_code"] != reverse.reason_code:
            raise ValueError("Combined qualifying reasons differ between teammates")
        if not row["reason_code"]:
            value, opposite = float(row["combined_gap"]), float(reverse.combined_gap)
            if not np.isfinite(value) or not np.isfinite(opposite) or value != -opposite:
                raise ValueError("Combined qualifying log gaps are not exact opposites")
            pair = (number, frozenset([driver, teammate]))
            if pair not in seen:
                discrepancies.append(abs(value + opposite))
                seen.add(pair)
    return discrepancies


def make_observations(source, combined, dry, wet, roster, season_settings=None):
    """Read each qualifying driver directly; expand the one-row race pairs."""
    cfg = season_settings or DEFAULT
    discrepancies = validate_qualifying_rows(source, combined)
    audit, records = [], []
    roster_map = roster.set_index(["round_number", "driver"])
    audited_qualifying = set()
    for row in combined.to_dict("records"):
        number, driver, teammate = int(row["round_number"]), row["driver"], row["teammate"]
        identity = roster_map.loc[(number, driver)]
        if identity.teammate != teammate or identity.team != row["team"] or identity.race != row["race"]:
            raise ValueError("Combined qualifying roster disagreement")
        reason = row["reason_code"]
        # This value is already in log units. Do not transform it again and do
        # not generate the other driver's contribution by flipping this row.
        value = np.nan if reason else float(row["combined_gap"])
        pair = (number, frozenset([driver, teammate]))
        if reason.startswith("invalid_gap") and pair not in audited_qualifying:
            audit.append({"signal": "qualifying", "round_number": number, "driver": driver,
                          "teammate": teammate, "field": "combined_gap",
                          "value": str(row["combined_gap"]), "reason_code": reason})
            audited_qualifying.add(pair)
        records.append({"signal": "qualifying", "round_number": number, "race": row["race"],
                        "team": row["team"], "driver": driver, "teammate": teammate,
                        "contribution": value, "se_log": np.nan, "reason_code": reason,
                        "warnings": "", "method_used": "", "race_ci_low": np.nan,
                        "race_ci_high": np.nan, "matched_laps": "", "clean_laps_min": ""})
    for signal, table, gap_column, se_column in [
        ("dry", dry, "final_gap", "final_se_pp"),
        ("wet", wet, "wet_gap_2pct", "wet_gap_se_pp_2pct"),
    ]:
        seen = set()
        for row in table.to_dict("records"):
            number = int(row["round_number"])
            driver, teammate = row["driver"], row["teammate"]
            key = (number, tuple(sorted((driver, teammate))))
            if key in seen:
                raise ValueError(f"Duplicate pair in {signal}: {key}")
            seen.add(key)
            for a, b in [(driver, teammate), (teammate, driver)]:
                identity = roster_map.loc[(number, a)]
                if identity.teammate != b or identity.team != row["team"] or identity.race != row["race"]:
                    raise ValueError(f"Source roster disagreement: {signal} {key}")
            reason = row.get("reason_code", "")
            warnings = []
            try:
                a, b, se = log_pair(row[gap_column], row[se_column])
            except InvalidGap as exc:
                a, b, se = np.nan, np.nan, np.nan
                reason = str(exc)
                audit.append({"signal": signal, "round_number": number, "driver": driver,
                              "teammate": teammate, "field": gap_column,
                              "value": str(row[gap_column]), "reason_code": reason})
            if not np.isfinite(a):
                if not reason:
                    reason = "missing_gap"
            else:
                if reason:
                    raise ValueError(f"Usable gap carries a blank reason: {signal} {key}")
                if signal != "qualifying":
                    if not np.isfinite(se):
                        warnings.append("missing_or_invalid_se")
                    elif se == 0:
                        warnings.append("zero_se_review")
                    for warning in warnings:
                        audit.append({"signal": signal, "round_number": number, "driver": driver,
                                      "teammate": teammate, "field": se_column,
                                      "value": str(row[se_column]), "reason_code": warning})
            # Wet's single-race interval is preserved separately from a season CI.
            low, high = np.nan, np.nan
            if signal == "wet" and np.isfinite(a):
                try:
                    lo = valid_gap(row["wet_gap_ci_low_2pct"])
                    hi = valid_gap(row["wet_gap_ci_high_2pct"])
                    if lo is not None and hi is not None and lo <= hi:
                        low, high = 100 * np.log1p(lo / 100), 100 * np.log1p(hi / 100)
                    else:
                        warnings.append("wet_interval_unavailable")
                except InvalidGap:
                    warnings.append("wet_interval_invalid")
            for person, opponent, value, ci_low, ci_high in [
                (driver, teammate, a, low, high), (teammate, driver, b, -high, -low)
            ]:
                records.append({"signal": signal, "round_number": number, "race": row["race"],
                    "team": row["team"], "driver": person, "teammate": opponent,
                    "contribution": value, "se_log": se, "reason_code": reason,
                    "warnings": ";".join(warnings), "method_used": row.get("method_used", ""),
                    "race_ci_low": ci_low, "race_ci_high": ci_high,
                    "matched_laps": row.get("matched_laps", row.get("matched_laps_2pct", "")),
                    "clean_laps_min": min(int(row["driver_clean_laps"]), int(row["teammate_clean_laps"])) if signal == "dry" else ""})
    for signal in SIGNALS:
        expected_rounds = (set(range(1, cfg.facts["round_count"] + 1)) if signal == "qualifying"
                           else set(cfg.facts["dry_rounds"]) if signal == "dry"
                           else {int(n) for n in cfg.facts["wet_races"]})
        expected = roster.loc[roster.round_number.isin(expected_rounds)]
        actual = {(record["round_number"], record["driver"]) for record in records if record["signal"] == signal}
        if actual != set(zip(expected.round_number, expected.driver)):
            raise ValueError(f"Incomplete or out-of-scope {signal} appearances")
    observations = pd.DataFrame(records).merge(roster[["round_number", "driver", "period"]],
                                                on=["round_number", "driver"], validate="many_to_one")
    return observations, pd.DataFrame(audit, columns=["signal", "round_number", "driver", "teammate", "field", "value", "reason_code"]), discrepancies


def add_weights(observations, settings=Settings()):
    observations = observations.copy()
    observations["weight"] = [observation_weight(row.signal, row.se_log, row.race, settings)
                              if np.isfinite(row.contribution) else 0.0
                              for row in observations.itertuples()]
    return observations


def summarize_signal(group):
    valid = group.loc[np.isfinite(group.contribution)]
    eligible, count = len(group), len(valid)
    return {"valid": count, "eligible": eligible, "missing": eligible - count,
            "coverage": count / eligible if eligible else 0.0,
            "effective_races": effective_races(valid.weight.to_numpy()),
            "rating": float(np.average(valid.contribution, weights=valid.weight)) if count else np.nan,
            "median": float(np.median(valid.contribution)) if count else np.nan,
            "missing_reasons": dict(Counter(group.loc[~np.isfinite(group.contribution), "reason_code"])),
            "warnings": sorted(set(filter(None, group.warnings))) }


def weekend_draws(n_weekends, resamples=RESAMPLES, seed=SEED):
    """One shared draw matrix keeps every driver's same weekend together."""
    sampled = np.random.default_rng(seed).integers(0, n_weekends, size=(resamples, n_weekends))
    return np.array([np.bincount(row, minlength=n_weekends) for row in sampled], dtype=float)


def season_arrays(observations, drivers, settings=Settings(), multiplicities=None):
    """The first axis indexes whole-weekend resamples, not driver rows."""
    weekends = sorted(observations.round_number.unique())
    counts = np.ones((1, len(weekends))) if multiplicities is None else np.asarray(multiplicities)
    if counts.ndim != 2 or counts.shape[1] != len(weekends):
        raise ValueError("Invalid whole-weekend bootstrap counts")
    scores = np.full((len(counts), len(drivers), 3), np.nan)
    effective = np.zeros_like(scores)
    for di, driver in enumerate(drivers):
        for si, signal in enumerate(SIGNALS):
            group = observations.loc[(observations.driver == driver) & (observations.signal == signal)]
            valid = group.loc[np.isfinite(group.contribution)].set_index("round_number")
            weight = valid.weight.reindex(weekends, fill_value=0).to_numpy()
            weighted_values = (valid.weight * valid.contribution).reindex(weekends, fill_value=0).to_numpy()
            total, squares = counts @ weight, counts @ np.square(weight)
            scores[:, di, si] = np.divide(counts @ weighted_values, total,
                out=np.full(len(counts), np.nan), where=total > 0)
            effective[:, di, si] = np.divide(np.square(total), squares,
                out=np.zeros(len(counts)), where=squares > 0)
    factors = evidence_factor(effective, np.asarray(settings.reference_races))
    raw_weights = factors * np.asarray(settings.signal_weights)
    total = raw_weights.sum(axis=2, keepdims=True)
    weights = np.divide(raw_weights, total, out=np.zeros_like(raw_weights), where=total > 0)
    overall = (np.nan_to_num(scores, nan=0) * weights).sum(axis=2)
    usable = np.isfinite(scores[:, :, 0]) | np.isfinite(scores[:, :, 1])
    overall[~usable] = np.nan
    weights[~usable] = 0
    return overall, scores, effective, weights


def bootstrap_ci(samples, distinct_weekends, minimum=MIN_CI_WEEKENDS):
    samples = np.asarray(samples)
    valid = samples[np.isfinite(samples)]
    if distinct_weekends < minimum or len(valid) < MIN_BOOTSTRAP_FRACTION * len(samples):
        return np.nan, np.nan, len(valid), "insufficient_evidence"
    low, high = np.percentile(valid, [2.5, 97.5], method="linear")
    return float(low), float(high), len(valid), ""


def build_ratings(observations, roster, settings=Settings(), resamples=RESAMPLES, seed=SEED,
                  combined_source=None, season_settings=None):
    cfg = season_settings or DEFAULT
    if combined_source is None:
        combined_source = cfg.input("qualifying").relative_to(cfg.root)
    observations = add_weights(observations, settings)
    drivers = sorted(roster.driver.unique())
    overall, _, _, normalized = season_arrays(observations, drivers, settings)
    draws = weekend_draws(roster.round_number.nunique(), resamples, seed)
    sampled, sampled_signals, _, _ = season_arrays(observations, drivers, settings, draws)
    groups = comparison_groups(roster)
    records, diagnostics, periods = [], [], []
    for di, driver in enumerate(drivers):
        appearances = roster.loc[roster.driver == driver]
        own = observations.loc[observations.driver == driver]
        valid = own.loc[np.isfinite(own.contribution)]
        contributing = valid.round_number.nunique()
        low, high, bootstrap_valid, ci_reason = bootstrap_ci(sampled[:, di], contributing)
        row = {"season": cfg.year, "driver": driver, "teams": ";".join(sorted(appearances.team.unique())),
            "teammates": ";".join(sorted(appearances.teammate.unique())),
            "comparison_group": groups[driver], "teammate_changed": appearances.teammate.nunique() > 1,
            "season_appearances": len(appearances), "combined_rating": overall[0, di],
            "rating_units": "log-percentage points", "races_included": contributing,
            "combined_ci_low": low, "combined_ci_high": high, "bootstrap_valid": bootstrap_valid,
            "dry_strict_count": len(valid.loc[(valid.signal == "dry") & (valid.method_used == "strict")]),
            "dry_linear_count": len(valid.loc[(valid.signal == "dry") & (valid.method_used == "linear")]),
            "monaco_included": bool(((valid.signal == "dry") & (valid.race == "Monaco Grand Prix")).any()),
            "method_version": cfg.facts["method_id"],
            "source_files": ";".join(cfg.sources() + (str(combined_source),))}
        summaries = {}
        for si, signal in enumerate(SIGNALS):
            group = own.loc[own.signal == signal]
            summary = summarize_signal(group)
            summaries[signal] = summary
            for key in ["rating", "valid", "eligible", "effective_races", "median"]:
                row[f"{signal}_{key}"] = summary[key]
            row[f"{signal}_weight"] = normalized[0, di, si]
            detail = {"season": cfg.year, "driver": driver, "signal": signal, **summary}
            detail["missing_reasons"] = json.dumps(summary["missing_reasons"], sort_keys=True)
            detail["warnings"] = ";".join(summary["warnings"])
            detail["single_race_ci_low"], detail["single_race_ci_high"] = np.nan, np.nan
            detail["single_race_round"] = ""
            detail["season_ci_low"], detail["season_ci_high"], detail["season_ci_reason"] = np.nan, np.nan, "not_requested"
            if signal == "wet":
                accepted = group.loc[np.isfinite(group.contribution)]
                if len(accepted) == 1:
                    only = accepted.iloc[0]
                    detail.update(single_race_ci_low=only.race_ci_low, single_race_ci_high=only.race_ci_high,
                                  single_race_round=int(only.round_number), season_ci_reason="single_race_evidence")
                else:
                    a, b, _, reason = bootstrap_ci(sampled_signals[:, di, si], len(accepted), minimum=2)
                    detail.update(season_ci_low=a, season_ci_high=b, season_ci_reason=reason)
            diagnostics.append(detail)
        q, d = summaries["qualifying"], summaries["dry"]
        row["rating_status"] = rating_status(q["rating"], d["rating"], q["effective_races"], d["effective_races"], q["coverage"], d["coverage"])
        row["confidence"] = confidence_label(row["combined_rating"], q["effective_races"], d["effective_races"], q["coverage"], d["coverage"], not ci_reason)
        period_notes = []
        for period, entries in appearances.groupby("period", sort=True):
            period_own = own.loc[own.period == period]
            identity = {"season": cfg.year, "driver": driver, "period": int(period),
                        "team": entries.team.iloc[0], "teammate": entries.teammate.iloc[0],
                        "round_start": int(entries.round_number.min()), "round_end": int(entries.round_number.max())}
            note = {**identity, "signals": {}}
            for signal in SIGNALS:
                summary = summarize_signal(period_own.loc[period_own.signal == signal])
                periods.append({**identity, "signal": signal, **summary,
                    "missing_reasons": json.dumps(summary["missing_reasons"], sort_keys=True),
                    "warnings": ";".join(summary["warnings"])})
                note["signals"][signal] = {"mean": summary["rating"] if np.isfinite(summary["rating"]) else None,
                                          "valid": summary["valid"], "eligible": summary["eligible"]}
            period_notes.append(note)
        notes = {"comparison_scope": "only within shared-teammate group; no opponent-strength adjustment",
                 "ci_reason": ci_reason, "coverage": {s: {k: summaries[s][k] for k in ["missing", "coverage", "missing_reasons", "warnings"]} for s in SIGNALS},
                 "teammate_periods": period_notes}
        if summaries["wet"]["valid"] == 1:
            notes["wet_warning"] = "single-race evidence; wet season interval unavailable; see signal diagnostics"
        row["notes"] = json.dumps(notes, sort_keys=True, allow_nan=False)
        records.append(row)
    return pd.DataFrame(records, columns=COLUMNS), pd.DataFrame(diagnostics), pd.DataFrame(periods)


def descriptive_ranks(table):
    # Formal-support scores only. This ordering cannot establish absolute skill.
    return table.combined_rating.where(table.rating_status.eq("established")).rank(method="min", ascending=True)


def sensitivity_runs(observations, roster, baseline, season_settings=None):
    variants = {"monaco_1p0": replace(Settings(), monaco_multiplier=1.0),
                "reference_6_2": replace(Settings(), reference_races=(6, 6, 2)),
                "weights_50_45_5": replace(Settings(), signal_weights=(.50, .45, .05))}
    baseline = baseline.set_index("driver")
    base_rank = descriptive_ranks(baseline)
    records, headlines = [], {}
    for variant, settings in variants.items():
        table, _, _ = build_ratings(observations, roster, settings, season_settings=season_settings)
        table = table.set_index("driver")
        rank = descriptive_ranks(table)
        moved = []
        for driver, row in table.iterrows():
            change = rank[driver] - base_rank[driver]
            delta = row.combined_rating - baseline.loc[driver, "combined_rating"]
            over_two = bool(np.isfinite(change) and abs(change) > 2)
            if over_two:
                moved.append(driver)
            records.append({"variant": variant, "driver": driver, "comparison_group": row.comparison_group,
                "baseline_rating": baseline.loc[driver, "combined_rating"], "variant_rating": row.combined_rating,
                "rating_change": delta, "baseline_rank": base_rank[driver], "variant_rank": rank[driver],
                "rank_change": change, "moved_over_two": over_two,
                "baseline_status": baseline.loc[driver, "rating_status"], "variant_status": row.rating_status,
                "variant_confidence": row.confidence, "variant_ci_low": row.combined_ci_low,
                "variant_ci_high": row.combined_ci_high, "variant_bootstrap_valid": row.bootstrap_valid,
                "qualifying_weight": row.qualifying_weight, "dry_weight": row.dry_weight, "wet_weight": row.wet_weight,
                "ranking_scope": "descriptive grid ordering of established teammate-outperformance scores; no cross-group ability comparison"})
        headlines[variant] = moved
    return pd.DataFrame(records), headlines


def main():
    started = time.perf_counter()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    add_season_arguments(parser)
    parser.add_argument("--offline", action="store_true", help="CSV-only stage; never uses the network")
    args = parser.parse_args()
    cfg = from_args(args)
    args.output_dir = cfg.checked(args.output_dir) if args.output_dir else cfg.path("data")
    sources = cfg.sources()
    # Check all output names before starting. Exclusive writes protect races too.
    existing = [str(cfg.output(key, args.output_dir)) for key in OUTPUT_KEYS
                if cfg.output(key, args.output_dir).exists()]
    if existing:
        raise FileExistsError("Outputs exist; use a new --output-dir: " + ", ".join(existing))
    qualifying, dry, wet = [read_csv(cfg.root / name) for name in sources]
    combined = combine_table(qualifying)
    roster = check_roster(qualifying, cfg)
    observations, audit, discrepancy = make_observations(qualifying, combined, dry, wet, roster, cfg)
    combined_source = cfg.output("qualifying", args.output_dir).resolve()
    if combined_source.is_relative_to(ROOT):
        combined_source = combined_source.relative_to(ROOT)
    table, diagnostics, periods = build_ratings(observations, roster, combined_source=combined_source, season_settings=cfg)
    sensitivity, headlines = sensitivity_runs(observations, roster, table, cfg)
    summary = {"method_version": cfg.facts["method_id"], "drivers": len(table),
        "confidence_counts": {label: int(table.confidence.eq(label).sum()) for label in ["high", "medium", "low/provisional", "unavailable"]},
        "rating_status_counts": {label: int(table.rating_status.eq(label).sum()) for label in ["established", "provisional", "unavailable"]},
        "sensitivity_over_two": headlines,
        "sensitivity_summary": {name: {"maximum_absolute_rating_change": float(group.rating_change.abs().max()),
                                       "maximum_absolute_rank_change": float(group.rank_change.abs().max()),
                                       "rank_changes": int(group.rank_change.fillna(0).ne(0).sum())}
                                for name, group in sensitivity.groupby("variant")},
        "sensitivity_drivers_over_two_any": sorted(set().union(*map(set, headlines.values()))),
        "input_audit_rows": len(audit), "comparison_groups": roster.assign(group=roster.driver.map(comparison_groups(roster))).group.nunique(),
        "qualifying_log_orientation_difference_max": max(discrepancy, default=0),
        "qualifying_log_orientation_difference_mean": float(np.mean(discrepancy)) if discrepancy else 0,
        "qualifying_combined_gap_units": "log-percentage points",
        "qualifying_round_combination": "log-convert each round; remove reciprocal rounding residual equally; weighted mean",
        "settings": {"signal_weights": Settings().signal_weights, "reference_races": Settings().reference_races,
                     "monaco_multiplier": Settings().monaco_multiplier, "resamples": RESAMPLES, "seed": SEED},
        "sources_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sources}}
    for frame, key, display in [(combined, "qualifying", False),
        (table, "ratings", True), (diagnostics, "signal_diagnostics", True),
        (periods, "teammate_periods", True), (audit, "input_audit", False),
        (sensitivity, "sensitivity", True)]:
        write_csv_new(frame, cfg.output(key, args.output_dir), display)
    summary["runtime_seconds"] = time.perf_counter() - started
    with cfg.output("rating_summary", args.output_dir).open("x") as handle:
        json.dump(summary, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(f"Drivers: {len(table)}")
    print("Confidence:", summary["confidence_counts"])
    print("Rating status:", summary["rating_status_counts"])
    print("Drivers moving more than 2 places in any variant:", len(summary["sensitivity_drivers_over_two_any"]))
    for variant, names in headlines.items():
        print(f"  {variant}: {', '.join(names) or 'none'}")
    print(f"Input audit: {len(audit)} flags")
    print(f"Runtime: {summary['runtime_seconds']:.2f} seconds. Saved new files under {args.output_dir}")


if __name__ == "__main__":
    main()
