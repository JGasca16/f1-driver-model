# 2025 teammate race-pace gaps, version 1

We compare teammates on the same numbered race lap, on the same tyre compound
and with similar tyre ages. We remove interrupted laps and take the median of
the signed percentage gaps on the remaining matched laps. This describes
observed pace in the matched portions of the race; it is not an estimate of
unrestricted driver ability.

## Running it

```bash
.venv/bin/python race_pace_gaps.py --offline
.venv/bin/python race_pace_gaps.py --offline --sensitivity
.venv/bin/python race_pace_gaps.py --offline --tyre-age-tolerance 2
.venv/bin/python race_pace_gaps.py --offline --show-blanks
.venv/bin/python -m unittest -v test_race_pace_gaps
```

Default tyre-age tolerance is 3 laps; at least 10 matched laps are required.
`--sensitivity` calculates independent results at tolerances 2, 3, and 5 using
the same loaded inputs and compares each with 3. Each race is loaded once.
`--show-blanks` prints each blank pair and its reason; otherwise the terminal
prints counts by reason. Every blank driver row always has a reason in the CSV.

`--offline` reads the existing FastF1 cache without refreshing it. Before the
first race-pace run, only Monza had complete race data. The missing race laps,
weather, and race-control data were downloaded into the cache, then all three
analyses were executed offline with FastF1 3.8.3. Subsequent offline runs need
that populated cache. Remove `--offline` to populate or refresh missing data.
Qualifying code, documentation, tests, and exported data are not modified.

## Output files

All outputs are under `data/`:

- `2025_race_pace_teammate_gaps.csv`: default tolerance 3.
- `2025_race_pace_teammate_gaps_tyre_age_2.csv`: tolerance 2.
- `2025_race_pace_teammate_gaps_tyre_age_5.csv`: tolerance 5.
- `2025_race_pace_sensitivity_summary.csv`: coverage and changes versus 3.
- `2025_race_pace_sensitivity_pairs.csv`: one row per pair with all three
  gaps, matched-lap counts, blank reason codes, and gap changes.

The main CSVs have one row per driver per race: 480 rows, representing 240
teammate-pair/race combinations. Required columns are `race`, `driver`,
`teammate`, `gap_pct`, `matched_laps`, and `blank_gap_reason`.
Additional columns identify the round, team, tolerance, minimum sample size,
dry classification and its explanation, both drivers' result statuses, and
how many clean, same-lap, and same-compound matches were available.

`matched_laps` is the count after all matching filters, even if it is below
10. It is zero when the pair is excluded before matching, such as a wet race
or a disqualification; this does not mean the drivers completed zero laps.
`driver_clean_laps` and `teammate_clean_laps` are zero for races skipped before
lap filtering. The `reason_code` explains why those stages were skipped.

## Which races count as dry?

The whole race must meet both conditions:

1. No non-generated race-lap record has compound `INTERMEDIATE` or `WET`.
2. All available weather observations covering the race report `Rainfall=False`.

The race window runs from the first session `Started` timestamp to the later
of the last `Finished` timestamp and the final recorded lap-end timestamp.
This includes red-flag pauses and cars finishing after the leader. We include
the most recent weather observation at/before the start if it is at most 120
seconds old, plus observations after the start through the end. Observations
after the end are ignored.

Weather must cover both ends within 120 seconds, have no gaps over 180 seconds,
and have recognised, non-missing rainfall values. The observations are normally
about a minute apart. These coverage tolerances are practical data-quality
choices, not physical weather thresholds.

Any rain observation or use of intermediate/wet tyres excludes the entire
race as `wet_race`, even if most laps were dry. Missing or incomplete weather
coverage gives `dry_status_unknown`, never an assumed dry race. Missing tyre
compound information excludes individual laps; it does not prove a wet race.

This is a conservative proxy for dry conditions, not proof that the whole
track surface was dry. Rain can be light or local, and a track can remain damp
after rain stops. The current cache excludes Australia, Miami, Britain, and
Belgium. Miami is excluded because the race-period weather feed reports rain,
despite its lap records using slick tyres. That exclusion follows the rule
and is not a judgement that all of Miami's laps were wet.

## Lap filtering and matching

Keep a lap only when all of these are true:

- Lap number is greater than 1 and the lap time is finite and positive.
- There is neither a pit-in timestamp nor a pit-out timestamp.
- It is not the next numbered lap after an out-lap. This extra lap is a
  conservative tyre warm-up buffer, including pit-lane starts where recorded.
- `TrackStatus` is exactly `1` (clear for the full lap). This rejects any
  yellow, safety-car, VSC, VSC-ending, red-flag, mixed, or unknown status.
- It is not the first fully green lap after a safety-car, VSC, or red-flag
  period. The buffer waits through intervening non-green laps. A yellow flag
  on its own does not create an additional restart buffer.
- `Deleted=False`, `FastF1Generated=False`, and `IsAccurate=True`.
- Compound is SOFT, MEDIUM, or HARD, and tyre age is known, finite, and at
  least one lap. All duplicate driver/lap-number records are excluded.

Buffers are determined from the original lap sequence, before other laps are
removed. Both teammates must pass the filters independently. A clear lap for
one driver is not sufficient if the other driver's matching lap was affected.
The timing accuracy flag is a basic FastF1 consistency check, not a guarantee
that the lap was free of traffic, damage, or deliberate pace management.

Join teammates by identical `LapNumber`, require identical compounds, then
require the absolute difference in `TyreLife` to be no larger than the chosen
tolerance. Each lap is used at most once for each pair. `TyreLife` includes
the recorded age of a used set when fitted; it is not simply laps since the
latest pit stop. No compound conversion or tyre-degradation regression is used.
We do not reject a lap merely for being unusually slow or use a fastest-lap
percentage cutoff.

## Driver entries, retirements, and exclusions

Use the team attached to each driver in that race, so mid-season swaps are
handled separately for each event. Race entries take precedence. If an entry
is absent, use that event's qualifying roster to identify the missing weekend
teammate, without calculating anything from qualifying lap times. This keeps
Alonso/Stroll at Spain explicit even though Stroll withdrew before the race.

DNFs do not automatically exclude all earlier laps: usable laps before the
retirement can still contribute. If a driver has no non-generated lap records
(including some first-lap retirements and non-starters), the pair is blank.
This does not assert that every such driver failed to start.

A `Disqualified` race result excludes that driver's pair from the pace metric.
This is a conservative choice: a technically non-compliant car should not be
used to infer relative pace. It adds four excluded dry-race pairs in this run:
Ferrari and Alpine in China, Sauber in Bahrain, and McLaren in Las Vegas.
Race disqualifications are read from race results; qualifying exclusions are
not carried over to a driver's race performance.

## Calculation and blank gaps

For each matched lap:

```text
gap_pct = 100 * (driver_lap_time - teammate_lap_time) / teammate_lap_time
race_gap_pct = median of the matched lap gap_pct values
```

Negative means faster, positive means slower. The 90.0 vs 90.3 second example
is -0.3322259136%; the reverse comparison is +0.3333333333%. Each driver's
denominator is their teammate's time, so the two gaps need not have equal
magnitudes. For an even number of laps, the median averages the middle two
gap values. Compute both driver directions separately on exactly the same laps.

Require at least 10 matched laps. This threshold and the default three-lap
tyre-age tolerance are initial design choices, not validated statistical
cutoffs. Fewer than 10 produces a blank, never zero. Zero is reserved for
an actual zero median gap. Export numeric values to six decimal places.

Each blank has one primary reason, with this priority: unavailable timing or
control data; wet/unknown-dry race; race disqualification; no non-generated race
laps; too few matched laps. Several issues can apply, so the summary counts
are mutually exclusive primary reasons rather than counts of every problem.
Available driver statuses, dry reasons, and matching counts provide context.

An incomplete roster or unexpected processing error prevents replacement of
the season CSVs. Missing timing/control data with an identifiable roster is
represented by `data_unavailable` rows instead of invented gaps.

## Offline results and sensitivity

At tolerance 3: **99 of 240 pairs have gaps; 141 are blank**. The CSV has 198
numeric driver rows and 282 blank driver rows. Reasons for the blank pairs:

| Primary reason | Pairs |
| --- | ---: |
| Fewer than 10 matched laps | 88 |
| Whole race excluded by the dry rule | 40 |
| A driver has no non-generated race lap records | 9 |
| A driver was disqualified from the race | 4 |
| Missing data or unknown dry status | 0 |

Comparison with the default tolerance, using one alphabetical driver orientation
per pair to avoid double-counting:

| Tyre-age tolerance | Pairs with gaps | Blank pairs | Mean absolute change vs 3 (percentage points) | Maximum absolute change | Faster-driver sign flips |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2 | 90 | 150 | 0.008753 | 0.294714 | 3 |
| 3 | 99 | 141 | 0 | 0 | 0 |
| 5 | 105 | 135 | 0.009194 | 0.398203 | 2 |

Changes are calculated only on pairs with a gap in both runs: 90 for tolerance
2 vs 3, and 99 for 5 vs 3. Tightening to 2 loses nine pairs; widening to 5 gains
six. Eight of the common pairs change numerically at tolerance 2 and twelve at
5 (differences above 1e-9 percentage points). The median absolute change is
zero in both comparisons because most common pairs retain their median gap.
The typical usable pair has 26.5, 28, or 30 matched laps at tolerances 2, 3,
or 5 respectively (median count among pairs with reported gaps).

The largest tightening effect is Singapore Ferrari: Hamilton versus Leclerc
changes from -0.130221% at tolerance 3 to +0.164493% at tolerance 2. The largest
widening effect is United States Alpine: Colapinto versus Gasly changes from
+0.239867% at tolerance 3 to -0.158336% at tolerance 5. These are meaningful
sensitivity cases even though the across-pair median change is zero. Full
pair-level changes and sample counts are in the sensitivity CSVs.

## Assumptions and limits

- Equal numbered laps approximately align fuel loads and race conditions.
  Drivers can still cross the same lap at very different clock times,
  especially when lapped. There is no elapsed-time alignment or lapping filter.
- Matching tyre compound and recorded age approximates equal tyre conditions.
  Temperature, heat cycles, previous usage, driving style, and wear can differ.
  Corrected or inaccurate source tyre information can affect matching.
- We assume the retained laps reasonably describe the matched race portions.
  Strategy differences can remove most of a race from comparison, and missing
  comparisons are not random. Do not treat blanks as average performance.
- Consecutive laps are correlated. Ten laps are not ten independent experiments,
  and the three tolerance runs are not confidence intervals or significance tests.
- The median reduces the effect of isolated slow laps, but persistent traffic,
  blue flags, DRS, overtaking, team orders, fuel saving, and damage remain.
  Traffic detection/correction and detailed fuel corrections are left out.
- Warm-up and restart buffers deliberately discard some usable laps; some
  effects may last longer than one lap. Yellow-flag filtering is conservative
  because the lap status does not establish which driver slowed or by how much.
- Wet/mixed races, fitted degradation models, cross-compound conversions, and
  inferred traffic corrections are left out of version 1.
- DNF fault attribution remains a separate manual task in METHOD.md. We do
  not infer fault or remove pre-retirement laps for unlabelled car problems.
- A completed race gap uses information from that race. Future prediction
  features must use only earlier races' gaps, never the target race's result.

Fourteen tests cover the numeric example, current-race teammate changes,
insufficient/exactly-enough laps, filtering and buffers, dry classification,
missing data, absent entries, disqualifications, and tolerance sensitivity.
