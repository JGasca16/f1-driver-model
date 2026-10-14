# 2025 teammate qualifying gaps

Run `.venv/bin/python qualifying_gaps.py` to create
`data/2025_qualifying_teammate_gaps.csv`. After downloading the data once,
add `--offline` to reuse the FastF1 cache without network access.
Add `--show-flags` to display every flagged driver row in the terminal:
`.venv/bin/python qualifying_gaps.py --offline --show-flags`.

The CSV has one row per driver per Grand Prix. The script uses the main
qualifying session (`Q`), including on sprint weekends. Teammates are matched
by their team in that session, so substitutions and mid-season changes are
handled race by race.

## Times and round selection

- `driver_best_qualifying_time_seconds` is the driver's fastest accepted time
  across Q1, Q2, and Q3, including eligible times recovered from laps. The
  corresponding teammate column records the teammate's overall best time.
- The gap uses each driver's best time **in the latest round where both have
  a valid time**. Check Q3 first, then Q2, then Q1; use the first round with
  a valid time for each driver. Reaching a round without setting a valid time
  does not prevent an earlier-round comparison.
  Those times are saved separately as `driver_time_seconds` and
  `teammate_time_seconds`; `qualifying_round` identifies the round.
- `gap_pct = 100 * (driver_time_seconds - teammate_time_seconds) / teammate_time_seconds`.
  Negative means faster; positive means slower. A value of `0.5` means 0.5%.
  Teammates' gaps have different denominators, so their magnitudes need not match.
- The `driver_reached_round` and `teammate_reached_round` columns retain
  advancement estimates for diagnostics. They do not choose the comparison
  round. These estimates use the 2025 format: the fastest 15 in Q1 and fastest 10 in
  Q2 advance, including drivers unable to record a time in the next round.
  Classified round times take precedence over raw timing. Raw times for
  subsequently excluded drivers remain in the advancement ordering, because
  their exclusion does not retroactively let another driver take part.
  Existing later-round classified times also establish that round was reached.
- Final overall positions are not used to infer advancement: disqualifications
  can move a Q1 elimination into the top 15 of the final classification.
- FastF1's positive, finite Q1/Q2/Q3 result times are preferred. For each
  missing driver/round time, recover the fastest eligible lap in that round
  where possible. Recovery requires a positive lap time, `Deleted=False`,
  no pit-in or pit-out timestamp, and no FastF1-generated lap. A raw lap from
  a round the driver did not validly advance to is not restored. This guards
  cases such as Hulkenberg's Bahrain Q2 laps after a Q1 lap deletion removed
  his advancement. Existing classified times are never replaced by a faster
  raw lap that may have been invalidated later.
- The cached Miami results have no Q1/Q2/Q3 times for any driver. This same
  per-driver/per-round recovery rule reconstructs Miami's times from laps;
  recovery is no longer limited to a wholly missing session.
- `driver_time_source` and `teammate_time_source` identify the selected times
  as `results` or `laps`. `time_source` is `results`, `laps`, or `mixed` when
  the two selected times have different sources. These source fields are
  blank when no shared valid round exists.
- Times are in seconds. No adjustment is made for weather, tyres, traffic,
  or changes in track conditions within the same round.

## Missing times

`missing_time` is true only when **no round** has a valid time for both drivers.
The gap, `qualifying_round`, and both comparison-time fields are then blank.
Each driver's overall best time is retained separately if one exists. The
script never fills a missing gap with zero. `blank_gap_reason` identifies
the unavailable driver's time or the qualifying disqualification; both rows
of the pair contain the same explanation. Every remaining blank pair is
also printed once in the terminal.

`flag` is `ok` or a semicolon-separated list identifying the driver or teammate
and affected round. `no_time_Q2`, for example, means there is no classified
time or eligible timed lap in Q2. `time_absent_from_results_Q2` means a raw
timed lap exists but the classified result omits it; this can reflect an
excluded result and is not silently filled in. Confirmed disqualifications
use `driver_disqualified` or `teammate_disqualified`. A pair with no common
valid round also has `no_shared_valid_round`. Recovered times are identified
by the source columns rather than flagged as missing.

Flags cover all rounds reached, including a later round than the comparison.
A row can therefore have a valid gap and still flag a missing later-round time.
Entries without any qualifying time remain in the CSV with blank best times.

The former rule selected the latest round both drivers reached, even if a
time was missing there, and left that gap blank without trying an earlier
round. The new rule reduces missing comparisons from 13 teammate pairs to 7.

The completed export contains 24 races and 480 driver rows: **466 calculated
gaps (233 pairs)**, **14 blank rows (7 pairs)**, and 30 flagged rows in total.
Sixteen flagged rows have valid earlier-round gaps but missing times in later
rounds. Teammate pairs appear twice, once from each driver's perspective.

## Exclusions and remaining blank pairs

"Valid" excludes a qualifying disqualification, even if the timing feed still
contains non-deleted raw laps. FastF1's qualifying result status fields are
blank for these exclusions, so `DISQUALIFIED_2025` explicitly records the
three affected drivers using these official sources:

- [Ocon, Azerbaijan: rear-wing deflection infringement](https://www.formula1.com/en/results/2025/races/1269/azerbaijan/qualifying).
- [Albon and Sainz, Singapore: rear-wing/DRS technical infringements](https://www.formula1.com/en/latest/article/williams-drivers-disqualified-from-singapore-gp-qualifying-for-technical.hk0NFVQ3Wpp2hitKXdUhu).

This registry applies only to the 2025 season. These excluded times remain
unavailable for both the gap and the overall-best-time columns.

| Race | Team | Teammates | Reason the gap remains blank |
| --- | --- | --- | --- |
| Australian GP | Haas | Bearman / Ocon | Bearman has no valid timed qualifying lap. |
| Emilia Romagna GP | Red Bull | Tsunoda / Verstappen | Tsunoda has no valid timed qualifying lap. |
| Dutch GP | Aston Martin | Stroll / Alonso | Stroll has no valid timed qualifying lap; his recorded pit-in lap is excluded. |
| Azerbaijan GP | Haas | Ocon / Bearman | Ocon was disqualified; his raw times are not valid for recovery. |
| Singapore GP | Williams | Albon / Sainz | Both drivers were disqualified; their raw times are not valid for recovery. |
| United States GP | Racing Bulls | Hadjar / Lawson | Hadjar has no valid timed qualifying lap; a generated lap is excluded. |
| São Paulo GP | Sauber | Bortoleto / Hulkenberg | Bortoleto did not take part in qualifying and has no laps. |

The script refuses to replace the season CSV if any race fails to load or
does not have the expected 20 drivers and two drivers per team.

## FastF1 messages in the terminal

The script labels each qualifying session before loading it, so subsequent
FastF1 warnings can be associated with that event. FastF1 messages use car
numbers, not finishing positions: driver 5 is Gabriel Bortoleto in 2025.

`Fixed incorrect tyre stint information` means FastF1 repaired inconsistent
tyre-stint counters in its source data. A stint is a stretch of running between
pit visits. These corrections concern tyre metadata, which this qualifying-gap
calculation does not use.

At São Paulo, `No lap data for driver 5` and the following lap-accuracy warning
refer to Bortoleto, who did not take part in qualifying. The accuracy warning
is generated because there are no laps to check for that driver; it does not
mean every driver's lap times are inaccurate. Both Sauber rows correctly have
blank gaps because a comparison needs a time from each teammate. Bortoleto's
absence is confirmed by the
[official Formula 1 report](https://www.formula1.com/en/latest/article/qualifying-strategies.f8ERFOmm4mkrFEtR2JZNp).

`--offline` reads the existing cache without refreshing it. Missing cache data
may require a later online run. A warning is a diagnostic message, not by
itself a failed export; check the processing summary and the CSV's flags.

Run the focused calculation checks with
`.venv/bin/python -m unittest -v test_qualifying_gaps`.
The 11 checks cover signed denominators, the latest shared valid round,
fallback to Q2 and Q1, individual and whole-session recovery, disqualifications,
lap validity, corrected advancement, missing shared rounds, and teammate changes.

## Known limitations

- Comparisons use the latest qualifying round where both teammates where able to set a valid lap time. Q1 times are weaker signals than Q3 due to track and tyre conditions changing between rounds.

- 7 teammate pairs have no comparison because of disqualifications, no valid time lap from at least one driver, or a pit lap that was the only recorded lap time.

- Missing times were recovered from lap data for some races, such as Miami. Those recovered times ignored deleted, pit, and generated laps.

- Results come from just one season (2025), which is unable to say whether the driver performances we see this year translate to other seasons.