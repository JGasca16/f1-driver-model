"""Exact parity checks. A mismatch fails; there is no numerical tolerance."""
import csv
import json
from pathlib import Path


def compare_csv(original, adapted):
    """Check bytes as well as every serialized cell, including blank cells."""
    a, b = Path(original).read_bytes(), Path(adapted).read_bytes()
    left = list(csv.reader(a.decode().splitlines()))
    right = list(csv.reader(b.decode().splitlines()))
    differences = sum(x != y for x, y in zip(left, right)) + abs(len(left) - len(right))
    if a != b:
        raise AssertionError(f"CSV parity failed: {original}; {differences} differing rows")
    return {"rows": max(0, len(left) - 1), "mismatches": 0, "byte_match": True}


def compare_json(original, adapted, metadata=()):
    """Only declared metadata fields may differ; all scientific values are exact."""
    left = json.loads(Path(original).read_text())
    right = json.loads(Path(adapted).read_text())
    differences = {}
    for key in metadata:
        if left.get(key) != right.get(key):
            differences[key] = {"original": left.get(key), "adapted": right.get(key)}
        left.pop(key, None)
        right.pop(key, None)
    # A canonical serialization handles JSON's permitted NaN tokens consistently.
    if json.dumps(left, sort_keys=True) != json.dumps(right, sort_keys=True):
        raise AssertionError(f"JSON scientific parity failed: {original}")
    return differences


def chart_data(module, data):
    """Capture plotted inputs and transformed order, without comparing pixels."""
    import pandas as pd
    data = Path(data)
    ratings = pd.read_csv(data / "driver_rating_2025.csv")
    qualifying = pd.read_csv(data / "2025_qualifying_gaps_combined.csv")
    dry = pd.read_csv(data / "race_pace_dry_final.csv")
    wet = pd.read_csv(data / "race_pace_wet_final.csv")
    drivers, matrix = module.coverage_data(ratings, qualifying, dry, wet)
    return {
        "group_order_and_values": module.grouped_driver_order(ratings).to_csv(index=False),
        "scatter_values": ratings[["driver", "qualifying_rating", "dry_rating"]].to_csv(index=False),
        "scatter_statistics": module.scatter_statistics(ratings),
        "pair_series": {f"{a}/{b}": module.pair_series(dry, a, b).to_csv()
                        for a, b in [("TSU", "VER"), ("NOR", "PIA"), ("HAM", "LEC")]},
        "coverage_driver_order": drivers, "coverage_matrix": matrix.tolist(),
    }


def compare_chart_data(original, adapted):
    if json.dumps(original, sort_keys=True) != json.dumps(adapted, sort_keys=True):
        raise AssertionError("Chart input, transformed values or ordering mismatch")
