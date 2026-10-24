"""Read-only reuse of the counting rule in MIAMI_COMPOUND_INVESTIGATION.md.

This is an eligibility diagnostic, not a repair. No reconstructed lap is sent
to a pace calculation. Ambiguous boundaries require review, never a guess.
"""
import numpy as np
import pandas as pd


def compound_pit_audit(laps, timing):
    """Compare explicit stint totals with pit boundaries and derived labels."""
    actual = pd.DataFrame(laps).loc[laps.FastF1Generated.eq(False)]
    rows, unresolved = [], []
    for driver, own in actual.groupby("DriverNumber", sort=True):
        own = own.sort_values("LapNumber")
        source = timing.loc[timing.Driver.eq(driver)]
        stints = []
        reason = ""
        # A red-flag tyre change cannot be established by this pit-only check.
        if own.TrackStatus.astype(str).str.contains("5").any():
            reason = "red_flag_boundary_requires_review"
        if own.LapNumber.tolist() != list(range(1, len(own) + 1)):
            reason = "incomplete_or_duplicate_lap_sequence"
        for stint, records in source.groupby("Stint", sort=True):
            compounds = records.Compound.dropna().loc[lambda x: x.ne("")].unique()
            starts = records.StartLaps.dropna().unique()
            total = records.TotalLaps.max()
            if len(compounds) != 1 or len(starts) != 1 or not np.isfinite(total):
                reason = "ambiguous_source_stint"
                break
            count = total - starts[0]
            if count <= 0 or count != int(count):
                reason = "invalid_source_stint_total"
                break
            stints.append((int(stint), compounds[0], float(starts[0]), int(count)))
        if not stints or [s[0] for s in stints] != list(range(len(stints))):
            reason = reason or "missing_source_stint"
        if sum(s[3] for s in stints) != len(own):
            reason = reason or "source_total_disagrees_with_laps"
        # Only a pit-in with the next lap's pit-out is a completed stop.
        # A pit-lane start and a final retirement pit-in create no new stint.
        indexed = own.set_index("LapNumber")
        completed_stops = []
        for lap in own.loc[own.PitInTime.notna(), "LapNumber"]:
            if lap + 1 in indexed.index and pd.notna(indexed.loc[lap + 1, "PitOutTime"]):
                completed_stops.append(int(lap))
        boundaries = np.cumsum([s[3] for s in stints]).tolist()[:-1]
        if boundaries != completed_stops:
            reason = reason or "pit_boundaries_disagree_or_extra_stop"
        if reason:
            unresolved.append({"driver_number": driver, "reason_code": reason})
            continue
        start = 0
        for stint, compound, age, count in stints:
            for row in own.iloc[start:start + count].itertuples():
                # FastF1 can store the literal string "nan", not just a null.
                known = row.Compound in {"SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET"}
                expected_age = age + row.LapNumber - start
                rows.append(dict(driver_number=driver, driver=row.Driver,
                    lap_number=int(row.LapNumber), source_stint=stint,
                    original_compound=row.Compound, pit_aligned_compound=compound,
                    unknown_compound=not known,
                    compound_conflict=bool(known and row.Compound != compound),
                    original_tyre_age=row.TyreLife, pit_aligned_tyre_age=expected_age,
                    tyre_age_conflict=bool(pd.notna(row.TyreLife) and row.TyreLife != expected_age),
                    boundary_verified=True, applied_to_pace=False))
            start += count
    evidence = pd.DataFrame(rows)
    conflicts = int(evidence.compound_conflict.sum()) if len(evidence) else 0
    return evidence, {"compound_conflicts": conflicts,
        "affected_drivers": sorted(evidence.loc[evidence.compound_conflict, "driver"].unique()) if len(evidence) else [],
        "unknown_compounds": int(evidence.unknown_compound.sum()) if len(evidence) else 0,
        "tyre_age_conflicts": int(evidence.tyre_age_conflict.sum()) if len(evidence) else 0,
        "unresolved": unresolved,
        "audit_status": "review_required" if unresolved else "conflict_found" if conflicts else "conflict_absent",
        "exclude_for_compound_conflict": True if conflicts else None if unresolved else False}
