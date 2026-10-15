# Dry race regression: fixed rules

These rules were written before running either model. They implement the latest
request, which takes precedence over the earlier proposal. No points or wins
are inputs. Miami and all other non-dry races are absent from performance outputs.

## Inputs and checks

Use the existing `dry_race_status` and `filter_clean_laps` functions unchanged.
Fit each actual race/team pair separately, with one row per retained individual
lap. The combined output uses one alphabetical driver/teammate orientation per
pair. Withdrawn entries and mid-season swaps follow the existing race roster.
Race disqualifications and missing race-lap records keep their existing exclusions.

Fix these thresholds before running:

- Ten clean laps per driver for a published regression gap.
- `strategy_confounded` unless at least one compound has **eight clean laps
  for each teammate**. Counts must be on the same shared compound; several
  smaller compound samples are not added together. This replaces the previous
  five-lap overlap rule. No new age/race-stage overlap gate is added.
- Require full column rank, positive residual degrees of freedom, and a design
  condition number at most **1,000**, after centring/scaling all non-intercept
  columns to unit population standard deviation. Do not drop terms to force fits.
- Matched methods retain the three-lap tyre-age tolerance. Strict requires ten
  matched laps; low-confidence requires three through nine inclusive.
- Disagreement means any two published method gaps differ by **more than 0.3
  percentage points**. It includes curved regression but not unreliable estimates.
- Fallback: strict, then linear regression, then low-confidence. Never average.
  Labels are high, medium and low respectively; blank is `unavailable`. These
  labels describe the chosen method, not calibrated statistical certainty.

## Models and percentage conversion

Both models use ordinary least squares with **lap time in seconds**, not log
time. Terms are an intercept, a driver indicator, compound indicators, tyre age
and lap number. The curved version adds squared tyre age and squared lap number;
no interaction or compound-specific slopes. Centre continuous variables before
squaring. Retained laps have equal weight in the fit.

The driver indicator is one for the alphabetical first driver, zero for the
teammate. Its coefficient is their adjusted difference in seconds. The driver
term standard error is reported in seconds using the usual OLS residual
variance and coefficient covariance matrix. This assumes uncorrelated,
constant-variance errors; consecutive laps can violate both assumptions.
These standard errors are descriptive, not reliable confidence guarantees.

Seconds must be divided by a defined teammate reference time. Predict teammate
time at every retained lap's observed compound/age/lap-number combination, with
the driver indicator set to zero. Average each driver's predictions separately,
then average those two means equally, so one driver's longer race does not
dominate the reference. Report this reference time in seconds. The gap is
100 × driver coefficient / reference teammate time. Thus 90.0 versus 90.3 gives
−0.332226%, and the reverse gives +0.333333%. Check reference times are positive.

The gap standard error (percentage points) uses the delta method, including
uncertainty in both the driver coefficient and reference prediction and their
covariance. Matched-median standard errors are unavailable in this version and
are left blank, never set to zero. No unsupported independent-lap bootstrap is
used. Linear and curved estimates share the same reference-lap distribution.

Fit strategy-confounded pairs where the matrix permits it, but leave their
published gap blank and retain `unreliable_gap_pct`, its standard error, the
driver coefficient and its standard error for inspection. Other quality-gate
failures also retain estimable results only in unreliable columns. A rank-
deficient fit has no uniquely identifiable estimate and remains blank even in
those columns. Record both quality failures and numerical failures.

## Combined table and comparison

`data/race_pace_dry_combined.csv` has separate strict, low-confidence, linear
and curved columns, standard errors where available, matched counts, regression
reason codes, unreliable estimates, final gap, method, confidence and disagreement.
Strict values come from the existing CSV and are checked against the current
cached lap calculation. Low-confidence values use exactly the same filtering
and median percentage formula with the smaller fixed sample threshold.

Compare mean absolute linear and curved gaps on the **same pairs with both
published estimates**. Report each mean, curved minus linear, and also the mean
absolute difference between the estimates. Those are distinct quantities.
Report individual-model availability separately; do not choose a winning model.

Final blank reasons retain disqualification/no-race-lap exclusions first, then
the linear model's failed gate if fewer than three matched laps remain. Reason
codes: `too_few_clean_laps`, `strategy_confounded`, `effects_not_identifiable`,
`fit_ill_conditioned`, `invalid_reference_time`, `fit_failed`, plus existing
`race_disqualification` and `no_race_laps`. Additional failures are recorded.
Incomplete data/rosters or unexpected processing errors stop publication.

## Limits

The model assumes shared compound effects and age/race-progress slopes, plus a
constant driver difference. The curved model relaxes the straight-line shape
only. Traffic, fuel saving, tyre temperature, damage, team orders and strategy
selection remain unmeasured. The compound-count gate does not guarantee
overlapping ages/race stages or remove extrapolation. Different strategies may
still be inseparable; condition checks detect only some such problems.
Retirements and missing laps are not random. Correlated laps exaggerate apparent
sample size. Matched medians and adjusted mean-time differences estimate
different things. Disagreement is a review flag, not proof one method is wrong.
Never use a race's own gap to predict that same race. No wet method is implemented.

## Running

`.venv/bin/python race_pace_regression.py` reads the cache offline and writes
new files only, refusing to overwrite an existing output. For another run use
`--output-dir` with a new empty directory. Existing scripts and CSVs are read-only.
