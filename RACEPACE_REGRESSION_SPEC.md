# Race-pace specification: dry regression and wet comparisons

Specification only, 14 October 2026. No model implementation or existing data
changes. Thresholds below are proposed in advance, not selected from wet-gap
results. They are starting rules, not statistically validated cutoffs.

## Race classification and shared exclusions

Use the actual teammates in each race, including driver swaps. For this new
method, dry means all non-generated race-lap compound records are confirmed
SOFT, MEDIUM or HARD, after verified recovery. Ignore weather-feed rain when
all tyres are confirmed slick. Any INTERMEDIATE or WET observation routes the
whole race to the separate wet/mixed method. Otherwise missing compound
evidence means unknown; do not silently assume dry. This is a tyre-based
classification, not proof that the surface was dry.

Both methods exclude lap 1, invalid/nonpositive times, generated or duplicate
records, pit-in/out laps and the next lap after an out-lap, SC/VSC/VSC-ending/red
laps and the first fully green lap afterward, yellow laps, deleted laps, and
laps failing FastF1 accuracy checks. Require known clear status for the whole
lap, known compound and valid tyre age. Missing exclusion flags do not pass.
Determine buffers before filtering. Exclude race-disqualified pairs. A DNF can
still contribute valid earlier laps; do not infer fault.

## 1. Dry races: regression

Fit a separate regression for each race/team pair, using all individual clean
laps from its two drivers, without exact lap, compound or age matching. Explain
log lap time using a baseline, a driver term, separate compound terms, a linear
tyre-age term and a linear lap-number term. Both teammates share the compound
adjustments and slopes; use reference categories to avoid redundant terms.
Give retained laps equal weight.

The driver term estimates the remaining proportional pace difference after
those adjustments. Convert a driver difference d to 100 × (exp(d) − 1) percent;
negative is faster. Reverse direction uses −d, not simply the negative percent.
This estimates adjusted typical pace, not pure skill or an arithmetic mean gap.
Lap number approximates fuel burn and track evolution together.

Different strategies contribute laps because the model adjusts their tyre
compound, tyre age and race stage. Safeguards before publishing a gap:

- At least **10 clean laps per driver**, preserving a modest minimum sample.
- At least one shared compound with **5 laps per driver inside overlapping
  tyre-age and lap-number ranges** for that compound. Compute both ranges from
  that compound's laps, then count laps inside their intersection together.
  This demands some evidence of comparable conditions without exact matching.
- All terms must be separately estimable, with positive residual degrees of
  freedom. Perfect driver/compound or tyre-age/lap-number confounding is blank.
- After centring and scaling nonconstant design columns to unit standard
  deviation (retain an intercept), a matrix condition number above **1,000**
  flags an unstable fit and leaves the gap blank. This is an engineering guard
  against near-confounding, not a confidence threshold.

Use all clean laps in accepted fits, including those outside the overlap used
for the safeguard. Report each driver's count, overlap counts and conditioning.
Inspect residual trends and stint sensitivity as diagnostics; do not silently
remove requested terms or tune thresholds to produce more gaps.

## 2. Wet/mixed races: matched laps only

No regression or cross-compound conversion. A comparison must pass all stages:

1. Both drivers have a valid clean lap with the **same lap number**.
2. Both use the **same compound**, including slicks, intermediates or wets.
   Retain the existing **three-lap maximum tyre-age difference** to reduce wear
   differences. Require known age; do not estimate it from lap number alone.
3. Neither has traffic at their own lap start: exclude if the time gap to the
   nearest car physically ahead is **under 1.5 seconds**. Exactly 1.5 passes.
   Include lapped cars, not merely the next classified position. Require a
   validated, synchronised timing/position headway at the start line; the latest
   observation at/before the start must be at most **1 second old**. Missing,
   stale, negative or ambiguous gaps do not pass. A race leader is not
   automatically traffic-free. Only a verified absence of a car ahead passes.
4. Conditions must be stable according to the field test below.

**Field test:** for lap n, use the same set of at least **8 drivers** with valid
laps n−1, n and n+1 after the shared exclusions. Each reference driver must stay
on the same compound across those three laps. Different reference drivers can
use different compounds. Do not apply teammate matching or the traffic filter
to this reference set. Compute its median lap time separately for each number.
Require both |median(n) − median(n−1)| / median(n−1) and
|median(n) − median(n+1)| / median(n+1) to be **at most 2%**. A larger change in
either direction fails. Missing neighbours or fewer than eight reference
drivers makes the test unknown, so exclude that comparison. Do not substitute
a one-sided test on the first/last available lap.

Why these choices: 1.5 seconds is the requested traffic boundary; the one-second
freshness limit avoids relying on old traffic positions. A 2% field change is
roughly 1.8–2.4 seconds on 90–120 second laps: large enough to target material
changes while allowing small fluctuations. Eight drivers provides a useful
field sample; the same drivers and unchanged compounds reduce jumps caused by
changing sample composition or tyre switches. These are deliberately fixed
before evaluating coverage or gap results.

Require **10 surviving matched laps**, as in the existing matched-lap method.
Report the median of 100 × (driver time − teammate time) / teammate time,
computed separately in each direction. No comparisons across different laps
are substituted when a wet pair fails.

## 3. Separate outputs

Future outputs: `data/2025_dry_race_regression_gaps_v1.csv` and
`data/2025_wet_race_matched_gaps_v1.csv`. Never append wet gaps to the dry file.
One row per driver/race, with race, team, driver, teammate, gap_pct, method,
sample counts, reason_code and explanation. The wet file has `wet_flag=True`
even for retained slick laps within a wet/mixed race. Dry rows have False.
Unknown-classification races go into a separate exclusions report, not either
performance dataset. Miami stays there while its recovery gate is unresolved.

Keep per-filter rejection counts and all applicable reason codes; choose the
first failing stage below as the primary reason. A blank is never zero.

## 4. Miami recovery gate

Audit cached race laps and original lap/stint tyre records before inclusion.
Recover only where an explicit, unambiguous compound record covers that driver
and tyre stint, with verified stint boundaries. Never fill across a pit stop,
guess from a teammate, or infer that missing means slick. Preserve original
records and save proposed recoveries separately with driver, lap, stint, source
and reason. Conflicting evidence remains unknown.

Report original missing count, confidently recovered count and remaining unknown
count. **Do not count Miami in either pace dataset until all missing compound
records are resolved and the race is classified.** Even after recovery it must
pass the relevant method's ordinary checks; recovery does not guarantee a gap.

**Offline audit:** 354 originally unknown non-generated lap compounds; **354
recoverable, 0 remaining unknown** among those records. Original timing-app
records explicitly identify each driver's starting compound. For all 15
affected drivers, recorded total tyre laps minus starting tyre age equals the
covered opening race laps, with no intervening pit stop or red flag. These
are supported recoveries, not forward/backward fills from adjacent lap labels.
The separate `data/miami_compound_recovery_spec_audit.csv` records the evidence
for each lap. Original lap data and existing CSVs remain untouched.

The audit also found inconsistent timing of existing compound/stint labels:
for example, Verstappen pits on lap 26, but the lap table changes from MEDIUM
to HARD on lap 33. **Miami remains excluded until the complete tyre timeline,
including tyre ages and existing labels, is reconciled to the original stint
records and pit boundaries.** Resolving the 354 missing compounds alone is not
enough to trust a regression requiring tyre age. No Miami pace was calculated.

## 5. Assumptions and blank reasons

Assumptions: timing, tyre identities/ages, stint boundaries and track flags are
accurate enough; tyre-based dry classification is an acceptable proxy; retained
laps describe only the sampled race portions. Missing laps and retirements are
not random. Both cars are sufficiently comparable for a teammate contrast,
although setups, upgrades and damage can differ.

Dry assumptions: a constant driver advantage, linear age/progress effects on
log time and shared slopes/compound effects are adequate. Overlap checks reduce
but cannot eliminate extrapolation. Traffic, DRS, fuel saving, damage and team
orders can still be absorbed into the driver term; dry traffic correction is
not included in this first model.

Wet assumptions: similar compound/age and lap number give a useful comparison;
start-line headway represents traffic sufficiently well, though traffic can
arise later in the lap. Equal lap numbers can occur at different clock times,
especially for lapped cars. A stable field median is only a proxy for stable
conditions: local rain, gradual changes, different conditions for different
cars, and common pace management can escape it. It can also reject a lap for
reasons other than weather. Tyre wear and temperature are not fully controlled.

For both methods, consecutive laps are correlated; sample thresholds are not
confidence guarantees. Do not present ordinary independent-lap uncertainty as
reliable. Wet and dry outputs estimate different quantities and must not be
pooled into one ranking without a separately approved method. These are
retrospective measurements; future prediction features use only earlier races.

Primary blank reasons, checked in this order where applicable:

| Code | When no gap is published |
| --- | --- |
| `data_unavailable` | Required session/timing/control data cannot be loaded or validated. |
| `roster_unresolved` | Two teammates cannot be identified for that race. |
| `miami_recovery_pending` | Miami still has unresolved compound records. |
| `tyre_timeline_unverified` | Compound/age/stint records conflict with pit boundaries or a recovered timeline has not been validated; currently applies to Miami. |
| `race_classification_unknown` | Tyre evidence cannot establish dry or wet/mixed. |
| `race_disqualification` | Either teammate was disqualified from the race. |
| `no_race_laps` | Either driver has no non-generated race lap records. |
| `too_few_clean_laps` | Dry: either driver has fewer than ten clean laps. |
| `strategy_overlap_insufficient` | Dry: no shared compound meets the five-laps-each overlap test. |
| `effects_not_identifiable` | Dry: requested terms are redundant or residual degrees of freedom are insufficient. |
| `fit_ill_conditioned` | Dry: scaled condition number exceeds 1,000. |
| `fit_failed` | Dry: numerical fitting fails or yields nonfinite output. |
| `too_few_same_number_laps` | Wet: fewer than ten shared clean lap numbers. |
| `too_few_same_compound_laps` | Wet: fewer than ten remain after compound matching. |
| `too_few_similar_age_laps` | Wet: fewer than ten remain after the age limit. |
| `too_few_traffic_qualified_laps` | Wet: fewer than ten remain after verified traffic checks. |
| `too_few_stable_condition_laps` | Wet: fewer than ten remain after the field-median test. |

Lap-level audit codes explain these shortages: `lap1`, `invalid_lap_time`,
`generated_lap`, `duplicate_lap`, `pit_lap`, `pit_warmup`, `sc_vsc_red`,
`restart_buffer`, `yellow_flag`, `track_status_unknown`, `deleted_lap`,
`deletion_status_unknown`, `inaccurate_lap`, `accuracy_unknown`,
`compound_unknown`, `tyre_age_unknown_or_invalid`, `teammate_lap_missing`,
`compound_mismatch`, `tyre_age_mismatch`, `traffic_under_1_5s`,
`traffic_data_unknown`, `field_reference_insufficient`, `field_neighbour_missing`
and `field_median_jump`. Record all applicable failures, not just the first.
Unrecognised or missing generation flags count as `generated_lap` with a
clarifying detail. Unexpected errors stop output publication rather than
silently turning a failed analysis into successful blank rows.
