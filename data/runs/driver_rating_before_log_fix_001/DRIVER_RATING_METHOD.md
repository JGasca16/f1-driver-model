# 2025 season teammate ratings

This implements DRIVER_RATING_SPEC.md with the approved changes: qualifying
combines rounds, and the full-evidence signal weights are 45% qualifying,
45% dry pace and 10% wet pace. All choices below are fixed before running the
ratings. No points, wins or finishing positions enter this calculation.

## Fixed choices

- Qualifying round weights: Q1 0.20, Q2 0.30, Q3 0.50. Drop missing rounds
  and divide by the sum of the remaining weights. No valid round gives
  `no_valid_round`. Sprint qualifying is absent from the input.
- Log contribution: `100 * ln(1 + gap/100)`. The other driver receives its
  exact negative. Errors become `SE / (1 + gap/100)` for both drivers.
  Nonfinite values and gaps at or below -100 are rejected and audited.
- Each qualifying race has weight 1. Dry and wet use
  `max(0.25, 1 / (1 + (SE_log/0.15)^2))`. An absent/invalid error uses 0.25
  and a warning. Zero errors get a review warning. Monaco's dry observation
  weight is multiplied by 0.5; its gap is unchanged. Other signals and tracks
  receive no track multiplier.
- Effective races: `(sum(weights)^2) / sum(weights^2)`. Signal evidence factors
  are `min(1, effective_races/8)` for qualifying/dry and
  `min(1, effective_races/3)` for wet. Multiply 0.45/0.45/0.10 by these factors
  and normalize. Wet alone cannot produce an overall score.
- Formal status `established` requires qualifying and dry each to have at
  least 6 effective races and 50% coverage. Otherwise an available score is
  `provisional`; without qualifying or dry it is `unavailable`.
- Confidence `high` requires qualifying and dry each to have at least 12
  effective races and 75% coverage, plus a usable combined interval. `medium`
  requires 6 effective races and 50% coverage for both, plus that interval.
  Other available scores are `low/provisional`; absent scores `unavailable`.
- Bootstrap: 2,000 draws, NumPy default_rng seed 42, each draw sampling 24
  entire weekends with replacement. Use identical draws for every driver and
  sensitivity variant. Retain rosters, blanks, both pair sides and all signals.
  Recompute means, effective races and signal weights in every draw. Do not
  inject extra per-race noise. Publish the 2.5th/97.5th percentiles only with
  at least 1,900 usable draws and 6 distinct contributing original weekends.
- Display rating-table floats to 3 decimals; use full precision for all
  weighting, intervals, eligibility decisions and sensitivity ordering.
- Sensitivities change one setting each: Monaco multiplier 1.0; reference
  races 6 qualifying/dry and 2 wet; signal weights 0.50/0.45/0.05.

## Input and interpretation decisions for review

Qualifying has two rows per pair. Its combined-round export retains both
perspectives, but season aggregation selects the alphabetically first driver
once per race/team and makes equal/opposite log contributions. Validate the
round-by-round reverse percentages against the reciprocal formula, allowing
0.0000011 pp for the source's six-decimal rounding. This tolerance checks
serialization, not performance or inclusion quality.

A weighted average of ordinary percentages is not exactly reciprocal to the
reverse row's weighted average. The alphabetical choice therefore matters
slightly. This is an explicit default for review, not two independent pieces
of evidence or an average of opposite source rows. The run summary measures
the discrepancy. Neither source row is modified. Invalid values in either
direction reject and flag that pair/signal observation.

The Monaco instruction is implemented as a multiplier on the precision weight,
after calculating that weight, as proposed in Section 4 of the approved spec.
It does not halve the measured gap or the error. An exact effective-race boundary
uses a 1e-12 arithmetic tolerance to avoid rejecting a mathematical boundary
through floating-point roundoff. This is not a change to an approved cutoff.

`combined_rating` also contains a provisional descriptive number when evidence
falls short; `rating_status` makes that distinction explicit. Establishment is
based on coverage and effective races; a missing interval can still prevent a
high/medium confidence label. An unavailable score stays blank.

No opponent-strength adjustment is made. Comparison groups are connected
components of observed teammate links. Comparisons are only valid within a
shared-teammate group, and even there changing opponents are not calibrated to
one common strength. The requested sensitivity ranks sort established scores
across the grid only as descriptive teammate-outperformance ordering. They are
not absolute-skill ranks. Provisional scores remain visible without ranks.

Bootstrap copies count as repeated sampled observations when recomputing
effective races. They are not new original evidence: the six-distinct-weekend
gate and reported support/confidence use the original sample. No retries fill
unsuccessful draws. Wet season intervals require more than one observed wet
weekend and 95% usable wet draws; a single wet race instead shows its original
interval transformed to log units, with the teammate endpoints reversed.

## Eligibility and teammate periods

The qualifying input defines the entered roster, including partial seasons.
Expect 21 drivers and 24 main qualifying weekends. Dry includes the 20 existing
dry races. Wet includes only Australia (1), Britain (12) and Belgium (13).
Miami (6) contributes qualifying only. Validate the race files against the
qualifying roster rather than silently adding or losing appearances.

Verify the actual assignments against the approved table: Lawson/Verstappen
and Tsunoda/Hadjar in rounds 1-2, Tsunoda/Verstappen and Lawson/Hadjar from
round 3, Gasly/Doohan in rounds 1-6, Gasly/Colapinto from round 7. Pool individual
race observations normally across periods. Also export weighted signal means
and medians per driver/team/teammate period. Short periods do not get equal
weight to long periods. Doohan has 6 appearances and Colapinto 18.

Blanks never become zero or a pace penalty. Report eligible, valid, missing,
coverage, effective races and missing reasons for each signal, including
periods with no valid gap. Confidence labels do not change observation weights.

## Files and running

The scripts and generated files are additions. Existing files are never
overwritten. Run the full calculation, including the round-combined qualifying
export, with:

```sh
.venv/bin/python driver_rating.py
```

It reads the three CSV inputs listed at the start of the request. It needs no
FastF1 session load or network access. Repeats require an entirely new output
folder. For example:

```sh
.venv/bin/python driver_rating.py --output-dir data/runs/driver_rating_002
```

For only the qualifying combination, the separate entry point is:

```sh
.venv/bin/python qualifying_gaps_combined.py --output-dir /tmp/quali-combined-review
```

The full calculation produces its own identical qualifying combination from
the source rounds in memory, then uses that `combined_gap` for ratings and
writes it alongside the rating files. It does not use `selected_gap`. Run the
full command instead of first creating a qualifying export in the same output
folder: the shared output filename is protected like every other output.
All intended names are checked before computation, and writes use exclusive
creation. A prior result is never silently replaced or promoted.

| New output | Contents |
| --- | --- |
| `data/2025_qualifying_gaps_combined.csv` | Requested 12 columns, both driver perspectives; 480 rows / 240 pairs |
| `data/driver_rating_2025.csv` | Exactly the 39 Section 8 columns, in the requested order; 21 driver rows |
| `data/driver_rating_signal_diagnostics.csv` | 63 driver/signal rows: support, missing counts/reasons, coverage, means, medians and wet intervals |
| `data/driver_rating_teammate_periods.csv` | 78 rows: three signals for each of 26 driver/team/teammate periods, including empty signals |
| `data/driver_rating_sensitivity.csv` | All 21 drivers for each of three changes, with rating changes, descriptive ranks and uncertainty |
| `data/driver_rating_input_audit.csv` | Invalid gaps and missing/zero/invalid SE warnings; header only when no flags exist |
| `data/driver_rating_run_summary.json` | Counts, fixed settings, input SHA-256 hashes, orientation discrepancy, sensitivity summary and runtime |

`notes` also carries missing counts/reasons, coverage, a brief period breakdown
and comparison restrictions, preserving the main table's exact schema. Coverage
is a fraction, not a percentage; normalized signal weights are fractions too.
The dry counts count only the selected final method. Original gap files retain
their own confidence labels and lap counts; season weighting uses the final SE
without a second confidence-label or lap-count multiplier.

Per-round qualifying source gaps retain their input precision, and its combined
gap is exported at full precision. Human-facing rating and diagnostic floats
are written to three decimal places. Embedded notes and the machine-readable
run summary retain calculation precision. Displayed weights may sum to 0.999
or 1.001 after rounding; full-precision weights sum to one. An empty numeric
cell means unavailable. The main CSV is sorted by driver abbreviation.

Missing qualifying rounds produce `no_valid_round`; invalid inputs produce
`invalid_gap_not_numeric`, `invalid_gap_nonfinite`, or
`invalid_gap_at_or_below_minus_100`. Dry and wet blanks keep their source reason
codes. Incomplete rosters, reciprocal-check failures or missing eligible
appearances stop publication. A rejected gap remains an eligible missing
appearance and an audit flag. Missing/invalid SE uses the approved 0.25 weight
and `missing_or_invalid_se`; zero SE gets `zero_se_review` without rejection.
Missing combined uncertainty uses `insufficient_evidence` in notes. A single
wet result has `single_race_evidence` for its unavailable season interval.

## Known limitations

These are 2025 performances relative to actual teammates and cars. Different
opponents, setups, upgrades, damage and strategies can change a score. Connected
groups still lack a common cross-team ability baseline. Subtracting two scores
does not predict their head-to-head gap. One season cannot establish lasting
driver quality.

The dry strict-first choice is retained. Strict and regression measure related
but different quantities. Their error estimates and Monaco's discount do not
remove traffic or strategy bias. Wet evidence is sparse and may describe one
race rather than usual wet performance. Qualifying round weights favor later
rounds when both drivers reach them, so the qualifying mixture can vary by race.

The weekend bootstrap measures variation in observed weekends, conditional on
these sources and choices. It does not correct selection bias, opponent
strength, correlation across weekends or unseen wet conditions. Missing races
may systematically be difficult ones. A narrow interval is not a calibrated
guarantee about skill. Full-season ratings must not be used to predict races
that contributed to them.

## Completed run and checks

The approved values were retained without tuning. The run produced **21 driver
rows: 20 established, 1 provisional and 0 unavailable**. Confidence is **16
high, 4 medium, 1 low/provisional and 0 unavailable**. Doohan is provisional:
6 qualifying observations but only 1 usable dry observation out of 4 eligible
dry appearances. The component is still reported; the other three dry blanks
are not ties or penalties.

Qualifying has 233 usable pairs / 466 driver rows. Dry has 168 pairs, wet 6.
There are nine disconnected comparison groups and 26 teammate periods. Every
driver with wet evidence has exactly one usable wet race: 12 drivers have a
single-race interval, and none has a usable wet season interval. Their actual
wet signal weight is about 0.036, rather than the full-evidence 0.100. No input
gap or SE needed an audit flag in this run.

All 21 drivers meet the combined-interval gates. Doohan has 1,998 usable draws
out of 2,000; everyone else has 2,000. His interval does not overcome the thin
dry evidence or upgrade his provisional status. The orientation check found
that using the reverse qualifying combined row would differ by a mean
**0.000324** and maximum **0.004503 log-percentage points per race/pair**.
These values describe the explicitly documented reference-direction choice,
which remains flagged for review.

None of the sensitivity changes moved anyone more than two places. The maximum
move was one position, and the largest absolute score change was 0.031
log-percentage points. See SENSITIVITY_NOTES.md for the separate variants.
The full calculation, including all three sensitivity bootstraps, took **0.65
seconds** on this machine, excluding tests and documentation work.

All **105 tests passed: 91 existing and 14 new**. New checks include every
missing-round combination, exact pair symmetry, SE conversion, evidence factors,
Monaco scope, confidence boundaries, whole-weekend repeatability, wet-only
unavailability, invalid-source auditing, approved swap periods, sparse wet
intervals, CI support and overwrite protection. Independent scalar calculations
also matched the means, weights and effective races for all 21 drivers, and an
explicit sampled-weekend expansion matched the vectorized bootstrap.

```sh
.venv/bin/python -m unittest discover
```

Existing dependency timedelta deprecation warnings are nonfatal. All 95
pre-existing scripts, tests, documents and CSVs kept identical content hashes.
The rating proposal and source CSVs remain unchanged.
