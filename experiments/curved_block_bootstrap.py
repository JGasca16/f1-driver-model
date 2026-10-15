"""Separate curved-model experiment. Never updates the standard dry output."""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import race_pace_dry as dry


def curved_arrays(frame, first):
    columns = [np.ones(len(frame)), frame.DriverNumber.eq(first).astype(float).to_numpy()]
    columns += [frame.Compound.eq(c).astype(float).to_numpy()
                for c in sorted(frame.Compound.unique())[1:]]
    for name in ["TyreLife", "LapNumber"]:
        values = frame[name].to_numpy(dtype=float)
        centred = values - values.mean()
        columns.extend([centred, centred ** 2])
    x = np.column_stack(columns)
    means, scales = x[:, 1:].mean(axis=0), x[:, 1:].std(axis=0)
    if (scales == 0).any():
        raise ValueError("effects_not_identifiable")
    z = np.column_stack([np.ones(len(x)), (x[:, 1:] - means) / scales])
    return z, frame.lap_seconds.to_numpy(), frame.DriverNumber.eq(first).to_numpy(), means[0], scales[0]


def fit_curved(frame, first, second):
    reason = dry.strategy_reason(frame, first, second)
    if reason:
        return dry.NAN, reason
    # Keep the historical order of observations for the point estimate.
    frame = pd.concat([frame.loc[frame.DriverNumber.eq(first)],
                       frame.loc[frame.DriverNumber.eq(second)]], ignore_index=True)
    try:
        arrays = curved_arrays(frame, first)
        z, y = arrays[:2]
        _, _, rank, singular = np.linalg.lstsq(z, y, rcond=None)
        if len(y) <= z.shape[1] or rank < z.shape[1]:
            return dry.NAN, "effects_not_identifiable"
        if singular[0] / singular[-1] > dry.MAX_CONDITION:
            return dry.NAN, "fit_ill_conditioned"
        return dry.refit_percentage(*arrays)
    except ValueError:
        return dry.NAN, "effects_not_identifiable"
    except np.linalg.LinAlgError:
        return dry.NAN, "fit_failed"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--standard", type=Path, default=ROOT / "data/race_pace_dry_final.csv")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/experiments")
    args = parser.parse_args()
    targets = [args.output_dir / name for name in ["curved_block_bootstrap.csv", "curved_block_bootstrap_summary.json"]]
    if any(p.exists() for p in targets):
        raise FileExistsError("Choose a new --output-dir; existing files are never overwritten")
    started = time.perf_counter()
    standard = pd.read_csv(args.standard, float_precision="round_trip")
    rows = []
    for race in dry.dry_races(args.offline):
        clean = dry.filter_clean_laps(race.laps)
        for row in standard.loc[standard.round_number.eq(race.round_number)].to_dict("records"):
            roster = race.roster.set_index("Abbreviation")
            first, second = roster.loc[row["driver"], "DriverNumber"], roster.loc[row["teammate"], "DriverNumber"]
            frame = clean.loc[clean.DriverNumber.isin([first, second])].reset_index(drop=True)
            members = [roster.loc[row["driver"]].to_dict(), roster.loc[row["teammate"]].to_dict()]
            reason = dry.external_reason(race, members)
            gap, reason = (dry.NAN, reason) if reason else fit_curved(frame, first, second)
            error = dict(se=dry.NAN, low=dry.NAN, high=dry.NAN, attempted=0, skipped=0, valid=0,
                         skip_reasons={}, reason="not_accepted")
            if np.isfinite(gap):
                gap = float(f"{gap:.9f}")
                error = dry.bootstrap_arrays(frame, curved_arrays(frame, first))
            smallest, method = dry.smallest_error([
                ("strict", row["strict_gap"], row["strict_se_pp"]),
                ("linear", row["linear_gap"], row["linear_se_pp"]), ("curved", gap, error["se"])])
            keys = {name: row[name] for name in ["round_number", "race", "team", "driver", "teammate"]}
            rows.append(dict(**keys, strict_gap=row["strict_gap"], strict_se_pp=row["strict_se_pp"],
                linear_gap=row["linear_gap"], linear_se_pp=row["linear_se_pp"], curved_gap=gap,
                curved_se_pp=error["se"], curved_ci_low=error["low"], curved_ci_high=error["high"],
                curved_reason_code=reason, bootstrap_reason=error["reason"],
                resamples_attempted=error["attempted"], resamples_skipped=error["skipped"],
                resamples_valid=error["valid"], resample_skip_reasons=json.dumps(error["skip_reasons"], sort_keys=True),
                final_gap=row["final_gap"], smallest_error_gap=smallest, smallest_error_method=method))
        print(f"Experiment: {race.race}", flush=True)
    output = pd.DataFrame(rows)
    common = output.final_gap.notna() & output.smallest_error_gap.notna()
    delta = (output.loc[common, "smallest_error_gap"] - output.loc[common, "final_gap"]).abs()
    summary = dict(pairs=len(output), curved_available=int(output.curved_gap.notna().sum()),
                   smallest_error_counts=output.smallest_error_method.value_counts().to_dict(),
                   common_pairs=int(common.sum()), changed_gaps=int(delta.gt(1e-9).sum()),
                   mean_absolute_change_pp=float(delta.mean()),
                   mean_absolute_change_changed_only_pp=float(delta.loc[delta.gt(1e-9)].mean()),
                   sign_flips=int((output.loc[common, "smallest_error_gap"] * output.loc[common, "final_gap"] < 0).sum()),
                   resamples_attempted=int(output.resamples_attempted.sum()),
                   resamples_skipped=int(output.resamples_skipped.sum()),
                   runtime_seconds=time.perf_counter()-started)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with targets[0].open("x") as stream:
        output.to_csv(stream, index=False)
    with targets[1].open("x") as stream:
        json.dump(summary, stream, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
