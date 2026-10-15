# Standard dry race pace

This is the current method for 2025 dry races. `race_pace_dry.py` is standalone:
it reads the FastF1 cache and imports no historical project scripts. Earlier
scripts, tests, documents and CSVs remain unchanged. No points or wins are
inputs. The curved experiment is separate and cannot change the standard file.
No wet-race method is implemented.

## Run and outputs

```sh
.venv/bin/python race_pace_dry.py --offline
```

This writes `data/race_pace_dry_final.csv` and
`data/race_pace_dry_run_summary.json`. The JSON includes per-pair linear
bootstrap attempts, skips and reasons. The CSV has exactly the 25 requested
columns. One row represents one race/team pair, with driver abbreviations in
alphabetical order. A negative gap means the named driver was faster; positive
means slower. Gaps are percentages; errors and differences between gaps are
percentage points (pp).

Outputs are never overwritten. If either output already exists, repeating the
same command automatically saves both new files under `data/runs/dry_001/`,
then `dry_002/`, and so on. The script prints the new location. The original
`data/race_pace_dry_final.csv` remains the original result. With `--output-dir`,
numbered repeat folders are created inside that directory instead. You can also
choose a new directory explicitly:

```sh
.venv/bin/python race_pace_dry.py --offline --output-dir /tmp/dry-repeat-new
```

Offline mode uses the existing cache only. Without `--offline`, FastF1 may
request online data. There is no dependence on the historical CSVs to compute
the standard output. The separate parity tests read them to verify continuity.
Incomplete race data, an unknown dry classification, an invalid roster or an
unexpected processing error stops publication instead of silently losing races.

## Inputs and dry classification

The calendar must contain the 24 races of 2025. Use each weekend's race roster,
so driver swaps follow actual teammates. Qualifying results only fill missing
race entries, such as a withdrawal; qualifying times are not model inputs.
Require 20 identifiable entries, exactly two per team, without duplicate driver
numbers or abbreviations. Race disqualifications exclude both drivers' pair.
A pair with either driver having no non-generated race records is also excluded.

Miami is explicitly excluded, even if its cache changes. For every other race,
use the unchanged weather-and-tyre rule:

- Any recorded INTERMEDIATE or WET tyre on a non-generated race lap makes the
  race non-dry. Unknown compounds do not themselves exclude the entire race;
  they cannot enter the clean-lap sample.
- Check weather from the first session `Started` time through the later of the
  last `Finished` time and last lap-end timestamp. Include the latest pre-start
  weather sample if it is no more than 120 seconds before the start.
- Any rain report in that window makes the race non-dry. All included rainfall
  flags must explicitly be false. Missing or unrecognised flags mean unknown.
- The first and last observations must cover the window edges within 120
  seconds; gaps between observations must be no longer than 180 seconds.
  Missing/invalid timestamps or insufficient coverage mean unknown.

This run excludes Australia, Miami, Britain and Belgium, leaving 20 dry races
and 200 teammate pairs. Weather and tyre records are proxies for conditions,
not proof that every part of the track was dry.

## Clean laps: unchanged rules

Apply these checks separately to each driver, before matching or regression.
Compute buffers on the raw chronological records before removing laps.

- Remove lap 1, nonpositive/missing/nonfinite lap times, pit-in and pit-out laps,
  and the lap immediately after every recorded pit-out lap.
- Require track status exactly `1` (fully green). This excludes yellow flags,
  safety car, VSC, red flags and unknown or combined non-green statuses.
  A status containing `4`, `5`, `6` or `7` starts a restart buffer: remove the
  next fully green lap too, even if other non-green laps occur first.
- Require `Deleted=False`, `FastF1Generated=False`, `IsAccurate=True`, a SOFT,
  MEDIUM or HARD compound and a finite tyre age of at least 1 lap. Unknown
  deletion/accuracy/generated flags are not assumed to pass.
- Remove every copy of a duplicate driver/lap-number record.

Require lap data, track status, race-control messages and usable deletion
information when loading sessions. There is no traffic exclusion or arbitrary
slow-lap cutoff. A slow but otherwise eligible lap remains in the sample.

## Strict matched-lap method

Match the teammates on the same race lap number, same compound and a tyre-age
difference of at most **3 laps**, inclusive. Require **10 matched laps**.
For each match compute:

`100 * (driver_seconds - teammate_seconds) / teammate_seconds`

The strict gap is the median of these percentages. For example, 90.0 versus
90.3 seconds is about -0.332226%; reversing the denominator gives +0.333333%.
Opposite orientations therefore need not be exact negatives.

For uncertainty, sort matches by lap number. Sample overlapping moving blocks
of **5 retained matches**, with replacement, from every possible non-wrapping
window. Draw `ceil(n/5)` blocks and truncate to the original `n` observations.
Take the median percentage in each of **2,000 resamples**, restarting NumPy's
`default_rng` with **seed 42 for each pair**. Require at least two full blocks,
which is the same ten-lap gate. SE is the sample standard deviation (`ddof=1`);
the interval is the **2.5th and 97.5th percentiles**, with linear interpolation.
These are blocks of retained observations, which can skip actual race laps or
cross stint boundaries after filtering.

## Linear regression method

Fit each teammate pair separately within each race, using all their clean
laps. Every retained lap has equal weight. Predict seconds with an intercept,
a driver indicator, compound indicators, straight-line tyre age and straight-line
race lap number. The alphabetically first compound is the reference category.
There are no squared terms or interactions in the standard model.

Both drivers must have **at least 10 clean laps**. At least one same compound
must have **8 clean laps for each driver**; several smaller compound samples
are not added together. Otherwise the model is `strategy_confounded`.
Do not add a tyre-age or race-stage overlap requirement.

Centre and scale non-intercept columns using their population standard deviation
for numerical stability. Require no constant required columns, full column rank,
more observations than fitted coefficients and scaled condition number **at most
1,000**. Rank uses NumPy's `lstsq(rcond=None)` rule. Do not drop terms to force a
fit when tyre age, lap number or driver effects cannot be separated.

The driver indicator is 1 for the named driver and 0 for their teammate. Its
coefficient is their adjusted difference in seconds. To convert to a percentage,
predict the teammate's time at every observed compound/age/lap-number combination,
setting the driver indicator to zero. Average predictions for each driver's
sample separately, then average those two means equally. Divide the driver
coefficient by that reference teammate time and multiply by 100. Require both
reference driver and teammate times to be positive and finite.

For parity with established outputs, strict point gaps are saved to **6 decimal
places** and linear point gaps to **9**. Bootstrap fits use unrounded values.
Errors and interval endpoints retain floating-point precision. This script
computes its own estimates; it does not copy old CSV values.

### Regression block bootstrap

Preserve v3's exact resampling rule and random-number order. Within each
**driver + stint**, sort clean laps by lap number and split into consecutive,
**non-overlapping chunks of 5 retained laps**. Keep the final shorter chunk;
a stint shorter than five is one block. Draw the same number of chunks with
replacement separately within each stint, then combine them. This is v3's
within-stint block method; it does not sample every overlapping window like the
strict moving-block calculation. Preserving that distinction is necessary for
exact parity. Unequal final chunks let the resampled lap count vary.

Use **2,000 attempts, seed 42 per pair**. Process driver/stint groups in sorted
order and draw all choices for each group before looping over attempts. Retain
original covariates and compound columns; centre/scale from the original sample.
Refit the seconds model and recompute the equal-driver reference over the sampled
laps. Do not reapply the original ten/eight-lap or condition-number acceptance
gates to bootstrap draws. Skip unidentifiable fits, insufficient residual degrees
of freedom, numerical failures and invalid reference predictions; do not redraw
until 2,000 successes. Report skips. At least **2 valid draws** are needed for
SE and interval, calculated with the same standard deviation and percentiles as
strict. This minimum is mathematical, not evidence of reliable uncertainty.

Missing stint labels leave linear uncertainty blank with `stint_unknown`.
Fewer than two valid resamples gives `too_few_valid_resamples`. Skip reasons are
`effects_not_identifiable`, `numerical_failure` and `invalid_reference_time`.
The run-summary JSON preserves these details; absent errors are never zero or
replaced by another error method. Missing uncertainty does not remove an
accepted point estimate.

## Final choice, labels and review columns

Use **strict first, then linear, otherwise blank**. Never average or choose the
smallest-error method for `final_gap`. `method_used` is `strict`, `linear` or
`unavailable`; `final_se_pp` follows that method. For strict use matched-lap
count; for linear use the smaller of the two clean-lap counts.

| Label | Fixed rule |
| --- | --- |
| high | SE ≤ 0.15 pp and count ≥ 20 |
| medium | Otherwise SE ≤ 0.30 pp and count ≥ 10 |
| low | Any other pair with a gap, including a missing SE |
| unavailable | No final gap |

Flag disagreement only when **both** strict and linear have finite, nonnegative
errors and `abs(strict - linear) > 2 * sqrt(strict_se² + linear_se²)`.
Equality does not flag. Missing estimates/errors leave the flag blank, not false.
**This treats the estimates as independent even though they share laps. It is a
simplification, not a calibrated significance test.**

`smallest_error_gap` and `smallest_error_method` compare strict and linear only.
An estimate needs a finite nonnegative SE to qualify. Exact ties choose strict.
Neither available means a blank gap and method `unavailable`. These columns are
for inspection only. Monaco alone gets `low_overtaking_limited`; it keeps its
numbers and uses the same confidence rule. All other track flags stay blank.

### Blank gaps and reasons

Individual strict gaps are blank below ten matches or after a pair-level
exclusion. Individual linear gaps are blank after an acceptance failure. The
fixed CSV schema has one `reason_code` for a **blank final gap**; it is empty
when either accepted method supplies the final gap. Thus it does not explain
an absent individual method when the other method succeeds.

| Reason code | Meaning |
| --- | --- |
| race_disqualification | Either teammate was disqualified; takes precedence |
| no_race_laps | Either teammate has no non-generated race records |
| strategy_confounded | No compound has eight clean laps for each driver |
| too_few_clean_laps | A driver has fewer than ten clean laps after the shared-compound gate passes |
| effects_not_identifiable | Constant or dependent required terms, or too few observations to fit them |
| fit_ill_conditioned | Scaled condition number exceeds 1,000 |
| invalid_reference_time | Reference driver/teammate time is nonpositive or invalid |
| fit_failed | Invalid numerical inputs, a numerical fitting failure or a nonfinite gap |
| too_few_matched_laps | Defensive fallback if neither method returns a gap and no more specific reason exists |

The priority is pair-level exclusions first, then the first failed linear gate.
Only the primary reason is published in the standard table; it is not an
exhaustive list of everything wrong with a pair. Unknown dry status or broken
session/roster loading aborts publication rather than appearing as a blank pair.

## Assumptions and limits

The regression assumes a constant driver difference throughout the race and
shared compound effects, tyre-age slopes and lap-number slopes for teammates.
Lap number is a proxy for fuel burn and race evolution, not a measured fuel
load. Compound labels describe the tyres within that race only. Different
strategies can contribute all their clean laps without matching, but the model
must extrapolate when their ages or race stages differ. Eight laps on a shared
compound and full rank do not prove that strategy is separated from driver.

Traffic, team orders, damage, fuel saving, tyre temperature, driver-specific
wear, nonlinear changes and strategy selection remain unmodelled. Missing laps,
retirements and exclusions are not random. Clean does not mean traffic-free or
maximum effort. Slow valid laps are deliberately retained. Dry classification
and lap quality depend on the cached records; later corrections may change
results. Mid-season swaps are handled race by race, not by a season-long team
roster. No repair of Miami compound records enters this calculation.

Strict estimates a median of same-lap percentages; linear estimates an adjusted
mean seconds difference converted at shared reference conditions. They measure
related but different quantities. Neither establishes causal driver ability.

Five-observation blocks approximate lap dependence. Filtering can create time
gaps within blocks, short stints cannot vary internally, and correlation across
stints or between drivers is not fully represented. The regression bootstrap
holds the observed stint structure/strategy fixed; it does not measure variation
from new strategies or missing stints. Failed-draw selection can bias errors.
Percentile intervals need not achieve nominal coverage. Confidence labels are
heuristics, not probabilities. The smallest estimated error can reward
underestimated uncertainty; it does not establish better prediction. Only use
earlier races as inputs when predicting a later race, never its own pace gap.

## Separate curved experiment and historical disagreement export

```sh
.venv/bin/python experiments/curved_block_bootstrap.py --offline
```

The experiment imports only the new standard module, adds centred squared tyre
age and lap number, and keeps the same acceptance gates, reference conversion,
within-stint chunk resampling, 2,000 attempts and seed 42. It reads the standard
file for strict/linear estimates and errors. It writes only
`data/experiments/curved_block_bootstrap.csv` and its summary JSON, refusing to
overwrite. Use `--output-dir` for a repeat run and `--standard` for an alternate
standard CSV. It never feeds results into the standard pipeline.

The inspection comparison uses only accepted estimates with finite block errors.
Exact ties choose strict, then linear, then curved. Changes require more than
**1e-9 pp**, avoiding export noise. A sign flip requires opposite nonzero signs.
Mean absolute change includes unchanged pairs on the common available set;
changed-only mean is also reported.

`data/race_pace_dry_all_rule_disagreements.csv` exports the **12 historical v3
pairs** where fixed-0.3, v2 and v3 flags were all true. Its errors deliberately
retain their v3 meanings: strict moving-block SE, linear within-stint block SE,
and **curved stint-cluster SE**. Its curved error is not the new experiment's
block error. Labels and matched counts are also from v3. This export preserves
the evidence behind those historical flags rather than recomputing them.

## Retired methods

- **Curved regression in the standard table:** the existing held-out-stint check
  favoured linear: **0.8016 s versus 0.8207 s** mean absolute prediction error,
  over **470 common folds and 7,799 laps**, an advantage of about 0.0191 s.
  These are same-race held-out predictions on successful common folds, not
  future-race validation. Curved remains only in the separate experiment.
- **OLS errors and stint-cluster errors:** ordinary OLS errors assume independent,
  constant-variance residuals, which consecutive laps can violate. Cluster errors
  allowed within-stint dependence but **91 of 159 regression pairs had fewer
  than 6 clusters**. Replacing linear cluster errors with block errors changed
  **35 confidence labels** from v2 to v3. This motivates the standard block
  method; it does not prove the bootstrap is perfectly calibrated. Ordinary
  least squares is still how regression coefficients are fitted; its analytical
  standard errors are retired.
- **Fixed 0.3 pp disagreement flag:** an arbitrary cutoff unrelated to estimated
  uncertainty. The standard uses only strict-versus-linear uncertainty.
- **Low-confidence 3–9 matched-lap method:** it added **0 final gaps in v2 and
  v3**. The standard retains matched counts but publishes no such estimate.
- **Version-specific labels, flags and mixed-error smallest-error comparisons:**
  retained only in historical files; no v1/v2/v3 tracking columns enter the
  compact standard CSV.

## Superseded files

These are historical candidates for later archiving, not deletion instructions.
Nothing was moved or modified. The standalone pipeline replaces the production
role of these files, not their usefulness as evidence:

- Scripts: `race_pace_gaps.py`, `race_pace_regression.py`, `race_pace_dry_v2.py`,
  `race_pace_dry_v3.py`.
- Method and result documents: `RACEPACE.md`, `RACEPACE_REVIEW.md`,
  `RACEPACE_REGRESSION_SPEC.md`, `RACEPACE_REGRESSION_METHOD.md`,
  `RACEPACE_REGRESSION_RESULTS.md`, `RACEPACE_DRY_V2.md`, `RACEPACE_DRY_V3.md`.
  The old specification's proposed wet method remains historical only.
- Matched outputs: `data/2025_race_pace_teammate_gaps.csv`,
  `data/2025_race_pace_teammate_gaps_tyre_age_2.csv`,
  `data/2025_race_pace_teammate_gaps_tyre_age_5.csv`,
  `data/2025_race_pace_sensitivity_summary.csv`,
  `data/2025_race_pace_sensitivity_pairs.csv`.
- Regression outputs: `data/race_pace_regression_linear.csv`,
  `data/race_pace_regression_curved.csv`, `data/race_pace_regression_comparison.csv`.
- Layered tables and summaries: `data/race_pace_dry_combined.csv`,
  `data/race_pace_dry_combined_v2.csv`, `data/race_pace_dry_combined_v3.csv`,
  `data/race_pace_dry_v2_summary.json`, `data/race_pace_dry_v3_summary.json`.

Preserve old tests with these versions. The new parity tests currently read
v1/v3 tables, so moving those tables later will require an explicit test-fixture
plan. Keep the holdout, blocked-pair, zero-lap, all-filtered and Miami audit
files/documents as supporting evidence; this task does not replace their audits.
`METHOD.md`, qualifying files and individual race result CSVs are not superseded.

## Completed offline run and verification

| Result | Pairs |
| --- | ---: |
| Final from strict | 99 |
| Added by linear regression | 69 |
| Final gap available | 168 |
| Final blank | 32 |
| High confidence | 72 |
| Medium confidence | 79 |
| Low confidence | 17 |
| Unavailable | 32 |

Linear itself is accepted for 159 pairs; 90 of those also have strict gaps.
Blanks: **10 effects_not_identifiable, 9 strategy_confounded, 9 no_race_laps,
4 race_disqualification**. All 159 linear bootstraps completed 2,000 valid draws;
none skipped. All 99 strict gaps have errors and intervals.

The new rule flags **5 pairs**, **13 fewer than v3's 18**, with no added flags.
V3 also compared curved and short-lap estimates. Removing those comparisons
leaves 90 evaluable strict/linear pairs and 110 blank disagreement flags.
The five flagged pairs are Japan TSU/VER, Netherlands ALB/SAI, Mexico NOR/PIA,
Qatar BEA/OCO and Abu Dhabi COL/GAS. Fewer flags is a consequence of the narrower
comparison, not improved agreement across all historical methods.

All **200 pairs** match v3 exactly for strict, linear and final gaps. Both SEs
and all interval endpoints also match exactly: maximum absolute difference
**0.0 pp**, better than the requested 1e-6 pp tolerance. Missing-value patterns
match. Final gaps also equal v1 for every pair, and no confidence labels changed
from v3. See `data/race_pace_dry_parity_report.json`.

The standard's inspection-only smallest-error choice selects strict for 74 pairs,
linear for 94, unavailable for 32. With curved added in the separate experiment,
the selection becomes **strict 70, linear 56, curved 42, unavailable 32**.
It changes the gap for **56 of the 168 comparable pairs**. Mean absolute change
is **0.043352 pp** over all 168, or **0.130057 pp** over the 56 changed pairs;
there are **4 sign flips**. The curved point estimates still match historical
v3 exactly; all 318,000 curved bootstrap attempts succeeded. None of these
choices replaces `final_gap`.

Runtime: **21.02 seconds** for the standard offline pipeline and **21.99 seconds**
for the separate curved experiment (about **43.00 seconds** combined, excluding
report writing and tests). These are measurements, not tuning targets.

Run the full test suite with:

```sh
.venv/bin/python -m unittest discover -v
```

**65 tests passed: 53 existing and 12 new**, including exact point parity,
error/interval parity, seed repeatability, short stints, confidence boundaries,
strict-first selection, disagreement boundaries and every v1 final gap.
Existing pandas/NumPy deprecation warnings in historical tests are nonfatal.
All 68 snapshotted pre-existing scripts, tests, documents and CSVs retained
identical content hashes. No historical outputs were overwritten.

### Repeat-run fix

The original output-exists traceback has been replaced by automatic numbered
run folders. Existing CSVs and summaries remain unchanged. A new test covers
both complete and partial prior outputs and successive folder reservations.
After this fix, all **66 tests pass**.
