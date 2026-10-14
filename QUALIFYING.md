# 2025 teammate qualifying gaps

Run `.venv/bin/python qualifying_gaps.py` to create
`data/2025_qualifying_teammate_gaps.csv`. After downloading the data once,
add `--offline` to reuse the FastF1 cache without network access.

The CSV has one row per driver per Grand Prix. The script uses the main
qualifying session (`Q`), including on sprint weekends. Teammates are matched
by their team in that session, so substitutions and mid-season changes are
handled race by race.

## Times and round selection

- `driver_best_qualifying_time_seconds` is the driver's fastest classified
  time across Q1, Q2, and Q3. The corresponding teammate column records the
  teammate's overall best time.
- The gap uses each driver's best time **in the latest round both reached**.
  Those times are saved separately as `driver_time_seconds` and
  `teammate_time_seconds`; `qualifying_round` identifies the round.
- `gap_pct = 100 * (driver_time_seconds - teammate_time_seconds) / teammate_time_seconds`.
  Negative means faster; positive means slower. A value of `0.5` means 0.5%.
  Teammates' gaps have different denominators, so their magnitudes need not match.
- Advancement uses the 2025 format: the fastest 15 in Q1 and fastest 10 in
  Q2 advance, including drivers unable to record a time in the next round.
  Classified round times take precedence over raw timing. Raw times for
  subsequently excluded drivers remain in the advancement ordering, because
  their exclusion does not retroactively let another driver take part.
  Existing later-round classified times also establish that round was reached.
- Final overall positions are not used to infer advancement: disqualifications
  can move a Q1 elimination into the top 15 of the final classification.
- FastF1's Q1/Q2/Q3 result times are preferred. The downloaded Miami results
  contain no round times for any driver, so Miami uses the fastest non-deleted
  lap in each round, excluding pit-in and pit-out laps. `time_source` records
  `results` or `laps`. Individual missing result times elsewhere are preserved.
- Times are in seconds. No adjustment is made for weather, tyres, traffic,
  or changes in track conditions within the same round.

## Missing times

`missing_time` is true if either driver lacks a time in the comparison round.
The gap is then blank; the script does not substitute an earlier round or zero.

`flag` is `ok` or a semicolon-separated list identifying the driver or teammate
and affected round. `no_time_Q2`, for example, means there is no classified
time or eligible timed lap in Q2. `time_absent_from_results_Q2` means a raw
timed lap exists but the classified result omits it; this can reflect an
excluded result and is not silently filled in.

Flags cover all rounds reached, including a later round than the comparison.
A row can therefore have a valid gap and still flag a missing later-round time.
Entries without any qualifying time remain in the CSV with blank best times.

The completed export contains 24 races and 480 driver rows: 454 calculated
gaps, 26 rows missing a comparison time, and 30 flagged rows in total.
The script refuses to replace the season CSV if any race fails to load or
does not have the expected 20 drivers and two drivers per team.

Run the focused calculation checks with
`.venv/bin/python -m unittest -v test_qualifying_gaps`.
