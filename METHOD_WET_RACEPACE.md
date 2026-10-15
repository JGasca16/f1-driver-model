# Wet and mixed-race teammate pace

These rules are fixed before calculating season results. The latest task takes
precedence over the older proposed wet method in RACEPACE_REGRESSION_SPEC.md.
This is one standalone script, `race_pace_wet.py`. It imports no dry or historical
project scripts. It uses no points or wins. Existing files stay unchanged.

## Run and files

```sh
.venv/bin/python race_pace_wet.py --offline
```

Each successful run writes one result CSV inside a newly reserved folder:
`data/runs/wet_001/race_pace_wet_final.csv`, then `wet_002`, and so on.
The first run also creates **`data/race_pace_wet_final.csv`**, the canonical
file that other scripts should read. To obey the no-overwrite rule, subsequent
runs preserve that canonical file and print whether their results match it.
If later results differ, promoting them to the canonical file requires a
separate approved change. The canonical file is not a silently updated latest-run
pointer. `--output-dir` changes the parent of both the canonical file and runs.
Files use exclusive creation; no previous CSV is overwritten. Failed session
loading or invalid rosters stop publication, rather than hiding a failed race.

The schema is exactly the requested 17 columns. One row represents one
race/team pair, with driver abbreviations in alphabetical order. `wet_flag`
is always True, even when the retained matched laps used slick tyres in a
mixed race. All gap percentages use the named teammate as denominator.
Negative means the named driver was faster.

**Wet gaps are not merged with dry gaps anywhere in this codebase.** This
addition reads no dry output, writes no dry output and adds no merge operation.
Earlier documents saying there is no wet implementation describe their earlier
versions and are left unchanged. The wet and dry measurements should not be
combined into a ranking without a separately approved method.

## Race selection

Use the unchanged excluded-race list: Australia (round 1), Miami (6), Britain
(12), Belgium (13). **Miami is excluded entirely**: do not load its session,
recover compounds or calculate its pace. Load only Australia, Britain and Belgium,
and require the expected event names/numbers on the 24-race 2025 calendar.

For each candidate, check non-generated raw laps for INTERMEDIATE or WET tyres.
If observed, retain the race as wet/mixed. If all observed compounds are known
slicks, report `no_wet_tyres_recorded`, leave it outside this output and do not
reclassify it as dry. If evidence is empty or compounds are unknown and no wet
tyres are observed, report `wet_tyre_evidence_unknown` and also hold it out.
No weather-feed rule changes and no other race is newly classified here.

Use actual teammates for each weekend, including mid-season driver swaps.
Race entries take priority; qualifying only fills a withdrawn/missing roster
entry. Require 20 identifiable drivers, two per team and no duplicates.
Qualifying times, race positions, points and wins do not enter the calculation.
Exclude a pair if either driver was disqualified, then if either has no
non-generated race-lap records. Retired drivers can contribute earlier valid
laps. Do not infer fault from a retirement.

## Clean laps

Copy the standard cleaning logic, with the compound list expanded to SOFT,
MEDIUM, HARD, INTERMEDIATE and WET. Compute buffers on raw chronological laps
before filtering. Remove:

- Lap 1; nonpositive, missing or infinite lap times.
- Pit-in/out laps and the immediately following lap after a pit-out lap.
- Any track status other than exactly `1` (fully green), including yellow,
  safety car, VSC, red and unknown status. Status containing `4`, `5`, `6` or
  `7` also removes the next fully green lap, even after intervening yellows.
- Deleted laps, generated laps, laps failing FastF1 accuracy checks and unknown
  values of those flags. Require explicit False, False and True respectively.
- Unknown compounds, nonfinite/missing tyre age or tyre age below 1 lap.
- All copies of duplicate driver/lap-number records.

Session laps, track status, race-control messages and usable deletion information
must be available. There is no arbitrary slow-lap cutoff. Clean does not mean
maximum effort. Unknown age still fails the inherited validity check, but
**there is no pairwise tyre-age tolerance** in this requested wet method.

## Traffic at lap start

Exclude a lap if its estimated gap to the closest car ahead at its own lap
start is **under 1.5 seconds**. Exactly 1.5 passes. Neither teammate may fail.

Use session-relative timing: `LapStartTime` for the driver's start and `Time`
for other cars' recorded lap-end/start-line crossings. Find the latest crossing
by another driver at or before that start and subtract the times. Consider
all drivers and all lap numbers, so a lapped car can be ahead. Do not just
select the next car in the classification. Candidate crossings must have a
positive finite recorded lap time, a known crossing timestamp, an explicit
non-generated record, no duplicate driver/lap record and no pit-in timestamp.
Crossings need not pass the pace filters: a yellow, deleted or slow lap can
still locate a real car at the line. A driver's own crossings are never used
as their car-ahead observation. Equal timestamps give a zero gap and fail.

This is a **start-line headway estimate from lap timing**, not a telemetry-based
reconstruction of car positions. It cannot detect an overtake between the
crossings, guarantee the preceding car is still ahead, or measure traffic later
in the lap. A timing gap can hide a close car. No telemetry interpolation or
additional freshness cutoff is introduced. A large observed headway passes.

If the driver's start timestamp is missing, there is no earlier usable crossing
by another car, or the headway otherwise cannot be computed, treat the lap as
**not in traffic**, as requested. Report these unknown-headway laps separately.
This is permission to retain unknown traffic, not evidence that the lap was
clear. A leader is not automatically clear; lapped cars are considered too.
The older spec's rule that missing traffic evidence must fail is superseded.

## Field-median weather-change proxy

Interpret “8 valid lap times on that lap number” as **8 distinct drivers with
one valid lap each**, since one driver cannot supply eight times for a single
lap number. For each race lap number, compute the median of clean individual
lap times, before traffic or teammate matching. At least eight distinct drivers
must contribute at that number. Use the whole field, not just a teammate pair.

For lap n, require a valid median at **n−1, n and n+1**. Use actual adjacent lap
numbers, not the preceding/next available record. Missing neighbours, including
the first/last valid boundary, or fewer than eight drivers make the weather
check unknown and the comparison is excluded. Never substitute a one-sided
check. Compute:

- `100 * abs(median(n) - median(n-1)) / median(n-1)`
- `100 * abs(median(n) - median(n+1)) / median(n+1)`

Both must be **at most** the chosen threshold. Run **1%, 2%, 3%** independently
on the same clean data. **2% is primary**, fixed before results. Equality passes.
These thresholds correspond to roughly 1, 2 and 3 seconds on a 100-second lap.
Do not choose whichever gives the most coverage.

Reference drivers can differ across the three lap numbers; no additional
same-driver or unchanged-compound reference gate is imposed. This implements
the latest per-lap field-median request, instead of the older proposed common
reference panel. Changing field composition or tyre mix can change the median
without weather changing. Missing reference evidence is reported separately
from an observed jump; both fail the weather check.

## Matching, gaps and uncertainty

Match the two clean laps at the same lap number, require the same compound,
then require both to pass traffic and the lap number to pass the field check.
A wet/mixed race can contain valid slick comparisons. Do not compare different
compounds, different lap numbers or substitute a regression. Require **10
surviving pair-laps** for each threshold separately, with no short-sample tier.
The gap is the median of:

`100 * (driver_seconds - teammate_seconds) / teammate_seconds`

For example, 90.0 versus 90.3 seconds gives approximately −0.332226%.
Reversing the denominator need not give the exact negative. Retain floating-point
precision in the CSV; do not round before calculating errors or labels.

Copy the standard strict moving-block bootstrap: order pair-laps by lap number,
use all overlapping, non-wrapping **5-observation** windows, sample with
replacement, draw `ceil(n/5)` blocks and truncate to n. Compute the median
percentage in **2,000 resamples**, restarting NumPy `default_rng` at **seed 42**
for each pair/threshold. Require **10 observations**, giving two full blocks.
SE is the sample standard deviation (`ddof=1`); the interval uses the **2.5th
and 97.5th percentiles** with linear interpolation. Only the primary 2% SE and
interval are exported in the requested schema. No OLS or cluster errors exist.

Use the primary gap, SE in percentage points and primary matched-lap count:

| Label | Rule |
| --- | --- |
| high | SE ≤ 0.15 pp and at least 20 matched laps |
| medium | Otherwise SE ≤ 0.30 pp and at least 10 matched laps |
| low | Any other available gap, including missing SE |
| unavailable | Primary gap is blank |

The comparison columns do not replace a blank primary gap or affect its label.

## Reasons and removal counts

`reason_code` explains a blank **primary 2% gap**. An available primary gap has
an empty reason. Use the first failing stage, even when later stages also fail:

| Reason | Meaning |
| --- | --- |
| race_disqualification | Either teammate was disqualified |
| no_race_laps | Either teammate has no non-generated race records |
| too_few_same_number_laps | Fewer than ten shared clean lap numbers |
| too_few_same_compound_laps | Fewer than ten after compound matching |
| too_few_traffic_qualified_laps | Fewer than ten after traffic checks |
| too_few_stable_condition_laps | Fewer than ten after measured jumps or missing field reference are excluded |

For each race, print **individual driver-lap counts** after ordinary cleaning:
traffic removals first, then weather-jump removals and missing-reference removals
among the remaining laps, separately for 1%, 2%, 3%. Also print weather counts
independently of traffic so overlapping failures are visible. Individual counts
include clean field laps even if their teammate has none to match.

Print **pair-lap counts** as a second breakdown: same-number/same-compound
comparisons, traffic removals, measured-weather-jump removals, unknown-weather
removals, retained comparisons. One comparison represents two driver-laps;
never add these units together. Pair-level disqualifications/no-race-lap pairs
are outside this breakdown. Sequential removals do not double-count a pair-lap.
Field medians are calculated once before traffic and do not change by threshold.
Counts include retained samples below ten even though their gaps remain blank.

## Assumptions and limits

Recorded timestamps, flags and compounds must be accurate enough. Same lap
number can occur at different clock times, especially for lapped drivers;
the teammates may therefore experience different rain despite matching.
Same compound does not control tyre age, wear, temperature or pressure.
No age matching, fuel adjustment, traffic later in the lap, damage correction,
team-order correction or car-upgrade adjustment is made.

The field median is only a proxy: gradual/local weather changes can pass, while
pit patterns, compound mix and driver composition can cause a jump. Unknown
traffic is allowed, unknown weather is excluded: these are deliberately different
missing-data rules. Filtering and retirements are not random; gaps describe the
retained race portions, not every lap or causal driver ability.

Five-observation blocks may skip actual laps and cross stints after filtering.
They approximate dependence, not independent observations or guaranteed interval
coverage. Ten laps and a narrow SE do not guarantee precision or represent unseen
conditions. Confidence labels are fixed heuristics, not probabilities. This
retrospective filter uses the following lap; it is not a live lap-start predictor.
Use only earlier races as features for future-race predictions.

## Completed offline run

Australia, Britain and Belgium all have recorded intermediate/wet tyres. No
candidate was held out for missing wet-tyre evidence. Miami was never loaded.
The canonical CSV and `data/runs/wet_001/race_pace_wet_final.csv` are identical.
Runtime was **1.40 seconds**. All thresholds above were fixed before this run.

| Race | Pairs | Gaps at 1% | Gaps at 2% (primary) | Gaps at 3% |
| --- | ---: | ---: | ---: | ---: |
| Australia | 10 | 4 | 4 | 4 |
| Britain | 10 | 1 | 1 | 1 |
| Belgium | 10 | 0 | 1 | 1 |
| Total | 30 | 5 | 6 | 6 |

Primary confidence: **1 high, 5 medium, 0 low, 24 unavailable**.
Primary blank reasons: **12 too_few_traffic_qualified_laps, 5 no_race_laps,
3 too_few_stable_condition_laps, 2 too_few_same_number_laps,
2 too_few_same_compound_laps**. No threshold was relaxed to fill these blanks.

### Individual driver-lap removals

Weather counts below are after traffic; missing reference is shown separately
and is the same at each threshold. These are driver-laps, not teammate pairs.

| Race | Clean laps | Traffic removed | Measured jump at 1% | Measured jump at 2% | Measured jump at 3% | Unknown weather reference removed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Australia | 493 | 148 | 14 | 0 | 0 | 39 |
| Britain | 390 | 143 | 34 | 0 | 0 | 69 |
| Belgium | 624 | 234 | 14 | 0 | 0 | 29 |
| Total | 1,507 | 525 | 62 | 0 | 0 | 137 |

No otherwise-clean driver-laps had unknown headway in this cached run. The
unknown-headway pass rule is nevertheless implemented and tested.

For comparison, applying weather to all clean laps before traffic would remove
**30, 43 and 37** driver-laps for measured 1% jumps in Australia, Britain and
Belgium respectively, plus **80, 110 and 70** for unknown reference. There are
no measured 2% or 3% failures on clean laps. These independent counts overlap
traffic removals and must not be added to the sequential table above.

### Pair-lap removals

These counts start after same-number and same-compound matching. Traffic
removes a whole comparison if either teammate fails. Externally excluded
pairs contribute no comparisons to this table.

| Race | Same-compound comparisons | Traffic removed | Weather jump removed at 1% | Weather unknown removed (all thresholds) | Kept at 1% | Kept at 2% | Kept at 3% |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Australia | 191 | 104 | 2 | 8 | 77 | 79 | 79 |
| Britain | 132 | 73 | 10 | 12 | 37 | 47 | 47 |
| Belgium | 209 | 178 | 1 | 1 | 29 | 30 | 30 |
| Total | 532 | 355 | 13 | 21 | 143 | 156 | 156 |

Measured jumps remove zero pair-laps at 2% and 3%. At the primary threshold,
traffic is the larger filter: **355 pair-laps**, versus **21** excluded because
the weather reference cannot be established. This does not prove conditions
were stable everywhere: the median proxy and its missing-data rule have the
limitations stated above.

### Verification

Run `.venv/bin/python -m unittest discover`.
**All 81 tests passed: 66 existing and 15 new.** Tests cover traffic below and
at the boundary, missing/no-car-ahead cases, future/pit crossings, field jumps,
both neighbours, eight distinct drivers, bootstrap repeatability, the ten-lap
minimum, signed gaps, labels, preserved outputs, wet-tyre evidence, standalone
imports and the saved CSV. The saved comparisons have nondecreasing lap counts
as thresholds widen and no gap below ten laps. Existing dependency deprecation
warnings in historical tests are nonfatal.

Content hashes confirm that all **76 pre-existing scripts, tests, documents
and CSVs** are unchanged. Only the new wet script, tests, this document and the
two copies of its result CSV were created. No dry/wet merge was performed.
