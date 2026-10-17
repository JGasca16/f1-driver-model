"""Combine main qualifying rounds. See DRIVER_RATING_METHOD.md for choices."""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
ROUND_WEIGHTS = {"q1": 0.20, "q2": 0.30, "q3": 0.50}
IDENTITY = ["round_number", "race", "team", "driver", "teammate"]
COLUMNS = IDENTITY + ["combined_gap", "rounds_used", "q1_gap", "q2_gap", "q3_gap", "reason_code"]
FILENAME = "2025_qualifying_gaps_combined.csv"


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


def combine_rounds(gaps):
    """Keep the fixed ratio of whichever round weights are available."""
    available = {}
    for name in ROUND_WEIGHTS:
        try:
            gap = valid_gap(gaps.get(name))
        except InvalidGap as exc:
            return np.nan, "", str(exc)
        if gap is not None:
            available[name] = gap
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
    records = []
    for row in source.to_dict("records"):
        gap, used, reason = combine_rounds({name: row[f"{name}_gap"] for name in ROUND_WEIGHTS})
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
    parser.add_argument("--input", type=Path, default=ROOT / "data/2025_qualifying_gaps_by_round.csv")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data")
    args = parser.parse_args()
    output = args.output_dir / FILENAME
    if output.exists():
        raise FileExistsError(f"Output exists: {output}. Use a new --output-dir.")
    combined = combine_table(read_csv(args.input))
    write_csv_new(combined, output)
    pairs = combined.loc[combined.driver < combined.teammate]
    print(f"Qualifying: {pairs.combined_gap.notna().sum()} of {len(pairs)} pairs have a combined gap.")
    print(f"Saved {output}")


if __name__ == "__main__":
    main()
