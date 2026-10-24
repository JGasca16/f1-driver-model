"""Combine qualifying in log-percentage points, with exact reverse symmetry.

combined_gap is already in log units. The q1/q2/q3 source columns remain
ordinary percentages. All approved round weights and missing-round rules stay
the same. The six-decimal source gaps need a symmetric rounding adjustment:
for each round use half of (this driver's log gap - their teammate's log gap).
This removes only their reciprocal-rounding residual, with no reference driver.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from season_config import DEFAULT, add_season_arguments, from_args

ROOT = Path(__file__).resolve().parent
ROUND_WEIGHTS = {"q1": 0.20, "q2": 0.30, "q3": 0.50}
# Same source-serialization tolerance used by the original rating calculation.
ROUND_TRIP_TOLERANCE = 0.0000011
IDENTITY = ["round_number", "race", "team", "driver", "teammate"]
COLUMNS = IDENTITY + ["combined_gap", "rounds_used", "q1_gap", "q2_gap", "q3_gap", "reason_code"]
FILENAME = DEFAULT.filename("qualifying")


class InvalidGap(ValueError):
    """An invalid recorded number is different from an empty cell."""


def read_csv(path):
    # Keep literal NaN/inf strings so invalid numbers cannot look like blanks.
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def is_blank(value):
    return value is None or (isinstance(value, str) and not value.strip())


def valid_gap(value):
    """Return None for a blank; reject impossible and nonfinite percentages."""
    if is_blank(value):
        return None
    try:
        number = float(value)
    except (ValueError, TypeError) as exc:
        raise InvalidGap("invalid_gap_not_numeric") from exc
    if not np.isfinite(number):
        raise InvalidGap("invalid_gap_nonfinite")
    if number <= -100:
        raise InvalidGap("invalid_gap_at_or_below_minus_100")
    return number


def combine_rounds(gaps, teammate_gaps=None):
    """Log-convert first; keep the fixed ratio of available round weights."""
    available = {}
    for name in ROUND_WEIGHTS:
        try:
            gap = valid_gap(gaps.get(name))
            opposite = valid_gap(teammate_gaps.get(name)) if teammate_gaps is not None else None
        except InvalidGap as exc:
            return np.nan, "", str(exc)
        if teammate_gaps is not None:
            if (gap is None) != (opposite is None):
                raise ValueError("Qualifying directions disagree on round availability")
            if gap is not None and abs(opposite - (-100 * gap / (100 + gap))) > ROUND_TRIP_TOLERANCE:
                raise ValueError("Qualifying reverse percentage fails reciprocal check")
        if gap is not None:
            log_gap = float(100 * np.log1p(gap / 100))
            if teammate_gaps is not None:
                # Do this for each named driver independently. Reversing the
                # names reverses the subtraction exactly, even after rounding.
                log_gap = (log_gap - float(100 * np.log1p(opposite / 100))) / 2
            available[name] = log_gap
    if not available:
        return np.nan, "", "no_valid_round"
    denominator = sum(ROUND_WEIGHTS[name] for name in available)
    result = sum(ROUND_WEIGHTS[name] * gap for name, gap in available.items()) / denominator
    used = [name.upper() for name in reversed(ROUND_WEIGHTS) if name in available]
    label = used[0] + " only" if len(used) == 1 else "+".join(used)
    return result, label, ""


def combine_table(source):
    required = IDENTITY + [f"{name}_gap" for name in ROUND_WEIGHTS]
    if not set(required).issubset(source):
        raise ValueError("Qualifying input is missing required columns")
    if source.duplicated(["round_number", "driver"]).any():
        raise ValueError("Duplicate qualifying driver/weekend")
    indexed = source.set_index(["round_number", "driver"])
    records = []
    for row in source.to_dict("records"):
        key = (row["round_number"], row["teammate"])
        if key not in indexed.index:
            raise ValueError("Qualifying pair is missing its reverse row")
        opposite = indexed.loc[key]
        if opposite.teammate != row["driver"] or opposite.team != row["team"] or opposite.race != row["race"]:
            raise ValueError("Qualifying reverse row has different identities")
        gap, used, reason = combine_rounds(
            {name: row[f"{name}_gap"] for name in ROUND_WEIGHTS},
            {name: opposite[f"{name}_gap"] for name in ROUND_WEIGHTS})
        records.append({**{key: row[key] for key in required},
                        "combined_gap": gap, "rounds_used": used, "reason_code": reason})
    return pd.DataFrame(records, columns=COLUMNS)


def write_csv_new(frame, path, three_decimals=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", newline="") as handle:
        frame.to_csv(handle, index=False, na_rep="",
                     float_format="%.3f" if three_decimals else "%.17g")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output-dir", type=Path)
    add_season_arguments(parser)
    parser.add_argument("--offline", action="store_true", help="CSV-only stage; never uses the network")
    args = parser.parse_args()
    cfg = from_args(args)
    output = cfg.output("qualifying", args.output_dir)
    source = cfg.checked(args.input) if args.input else cfg.input("qualifying_rounds")
    if output.exists():
        raise FileExistsError(f"Output exists: {output}. Use a new --output-dir.")
    combined = combine_table(read_csv(source))
    write_csv_new(combined, output)
    pairs = combined.loc[combined.driver < combined.teammate]
    print(f"Qualifying: {pairs.combined_gap.notna().sum()} of {len(pairs)} pairs have a combined gap.")
    print("combined_gap units: log-percentage points.")
    print(f"Saved {output}")


if __name__ == "__main__":
    main()
