# Wet field-minimum diagnostics

**Insufficient field size causes all weather-check removals at the official
8-driver minimum. Lowering the minimum to 4, 5 or 6 adds no teammate gaps.**
All four runs return the same six gaps, matched-lap counts, bootstrap errors,
intervals and confidence labels for all 30 pairs. No setting is selected here.

## Scope and counting

Run `.venv/bin/python race_pace_wet_diagnostics.py --offline`.
The script imports the official wet functions and gives the analysis a private
settings dictionary. Only `MIN_FIELD_DRIVERS` changes: **8, 4, 5, 6**, fixed
before inspecting results. The official module's setting remains 8. Cleaning,
1.5-second traffic rule, 2% weather threshold, ten-match minimum, bootstrap
(5 observations, 2,000 resamples, seed 42) and labels are unchanged.

The 30 eligible pairs are Australia, Britain and Belgium. Miami stays excluded
under the existing method; its counts are **not evaluated**, not zero. It was
not loaded or reclassified, and it contributes neither pairs nor totals.

A driver-lap reaches this weather audit after ordinary cleaning and traffic.
Each rejected driver-lap receives exactly one reason:

- `insufficient_field`: at least one of n−1, n, n+1 has fewer than the required
  number of distinct drivers with clean times. A missing lap number has zero.
- `measured_jump`: all three counts meet the minimum, but at least one median
  change exceeds 2%, using the unchanged neighbouring-median denominator.

Insufficient reference takes precedence: a jump cannot be diagnosed unless all
three references pass. There is no extra unknown category or double counting.
Reference counts use clean field laps **before traffic**, as in the official
method. Traffic does not reduce the reference pool.

Driver-laps and pair-laps are different units. Pair-laps are same-number,
same-compound teammate comparisons after both pass traffic. The requested
pair CSV counts rejected **pair-laps**, not both drivers separately. Externally
excluded pairs contribute zero pair-lap removals and retain their exclusion
reason. Driver-lap totals can include a driver's laps with no usable teammate.

## Exact baseline breakdown

| Race | Insufficient field: driver-laps | Measured jump: driver-laps | Insufficient field: pair-laps | Measured jump: pair-laps |
| --- | ---: | ---: | ---: | ---: |
| Australia | 39 | 0 | 8 | 0 |
| Miami | Not evaluated | Not evaluated | Not evaluated | Not evaluated |
| Britain | 69 | 0 | 12 | 0 |
| Belgium | 29 | 0 | 1 | 0 |
| Overall eligible races | **137** | **0** | **21** | **0** |

Thus category (a), insufficient field, accounts for **100%** of baseline
weather removals. Zero measured jumps does not establish stable conditions on
the excluded laps: their weather comparisons were not measurable under that rule.

## Four fixed runs side by side

H/M/L/U means high/medium/low/unavailable confidence. All weather counts below
are after traffic. No threshold or exclusion was relaxed beyond the field minimum.

| Field minimum | Gaps / 30 | New pairs vs 8 | Driver-laps insufficient | Driver-laps jump | Pair-laps insufficient | Pair-laps jump | H / M / L / U |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 8 (official baseline) | 6 | 0 | 137 | 0 | 21 | 0 | 1 / 5 / 0 / 24 |
| 4 | 6 | 0 | 108 | 25 | 16 | 5 | 1 / 5 / 0 / 24 |
| 5 | 6 | 0 | 127 | 10 | 19 | 2 | 1 / 5 / 0 / 24 |
| 6 | 6 | 0 | 137 | 0 | 21 | 0 | 1 / 5 / 0 / 24 |

Each eligible race's driver-lap breakdown is shown as **insufficient / jump**:

| Race | Minimum 8 | Minimum 4 | Minimum 5 | Minimum 6 |
| --- | ---: | ---: | ---: | ---: |
| Australia | 39 / 0 | 39 / 0 | 39 / 0 | 39 / 0 |
| Miami | Not evaluated | Not evaluated | Not evaluated | Not evaluated |
| Britain | 69 / 0 | 44 / 25 | 59 / 10 | 69 / 0 |
| Belgium | 29 / 0 | 25 / 0 | 29 / 0 | 29 / 0 |
| Overall eligible races | 137 / 0 | 108 / 25 | 127 / 10 | 137 / 0 |

**There are no new pairs at any minimum**, so there are no new-pair lap counts
or gaps to list. The CSV has all 120 candidate pair/minimum rows, including
blanks, and `new_pair_vs_8=False` throughout. Every matched-lap count and
available estimate is identical across these four runs, not just availability.

## Why lowering the minimum barely changes the filtering

The gate demands three consecutive usable field medians, not just a good
sample on the lap being assessed. The inherited exclusions can leave holes
in that sequence. For example, Australia's lap 9 has clean reference counts
**0 / 17 / 17** for before/current/after, and lap 57 has **14 / 14 / 0**.
Both fail despite a large current-lap field. Lowering eight to four cannot
supply the missing neighbouring evidence.

Of the 137 baseline rejected driver-laps, the smallest reference count across
the three lap numbers is:

| Smallest count | Rejected driver-laps |
| --- | ---: |
| 0 | 73 |
| 2 | 26 |
| 3 | 9 |
| 4 | 19 |
| 5 | 10 |

There are no rejected cases with a smallest reference count of six or seven.
That explains why minimum six changes nothing. **108 of 137** still lack
four reference drivers somewhere in their three-lap window.

At minimum five, ten British driver-laps become measurable but fail the 2%
jump rule. At minimum four, 25 British driver-laps become measurable but fail
that rule. Four Belgian individual laps become acceptable, but yield no
additional valid teammate comparisons. At pair level the five comparisons
newly measurable at minimum four, and two at minimum five, all become measured
jump failures. Hence the unchanged 21 rejected pair-laps and unchanged gaps.

## What this says about trust

A four- or five-car median is not automatically meaningless. It is, however,
more sensitive to which cars remain, their compounds and their pace. The
reference drivers can change between neighbouring laps, so a measured jump may
reflect field composition or strategy rather than weather. Smaller reference
samples do not fix those assumptions.

This experiment provides **no evidence that lowering the minimum creates useful
additional teammate comparisons**: none appear. It also does not validate four,
five, six or eight as a reliable weather detector. The existing confidence
labels measure bootstrap variation in the retained pair gaps, not uncertainty
in field medians or the accuracy of the weather filter. A small gap SE cannot
establish that the reference field is representative. No winner or production
change is recommended from these counts alone.

## Files and checks

- `race_pace_wet_diagnostics.py`: reproducible fixed comparison; refuses to
  overwrite diagnostic outputs. Use a new `--output-dir` to rerun.
- `data/race_pace_wet_diagnostics.csv`: 120 pair/minimum rows, with matched
  counts, signed gaps, bootstrap errors/intervals, labels, exclusion reasons,
  exclusive weather-removal counts and new-pair flags.
- `data/race_pace_wet_field_race_diagnostics.csv`: per-race driver-lap counts
  for each minimum, with explicit Miami exclusion rows.
- `data/race_pace_wet_weather_removed_laps.csv`: every rejected driver-lap at
  each minimum, its exclusive reason, all three driver counts and the median
  changes where measurable. This preserves the exact classification evidence.

The eight-driver calculation matches every official primary point estimate,
matched count, error, interval and label exactly. Pair-level rejected counts
reconcile with the official analysis at each minimum. Synthetic checks cover
exclusive reasons, the exact 2% boundary and preservation of the official
setting. **All 81 existing tests passed.** Runtime: **2.60 seconds**.
No official wet or dry result, script, test or existing document was changed.
