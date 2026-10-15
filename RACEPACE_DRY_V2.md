# Dry race pace v2: uncertainty and audit

These choices are fixed before running v2. Points and wins are never inputs.
Existing files stay untouched. Import v1's cleaning, dry classification and fit
checks; no wet method or Miami pace is included. V1 final gaps and fallback
order remain unchanged. All v1 columns remain in the new combined file.

## Fixed values and definitions

- Moving-block bootstrap: chronological matched-lap percentage observations,
  block length **5**, **2,000** resamples, NumPy generator seed **42** restarted
  for each pair. Use every overlapping five-observation block, sample blocks
  with replacement, concatenate and truncate to the original sample length.
  No circular wrapping. Require at least **10 observations** (two full blocks).
  Statistic: median percentage gap. SE: sample standard deviation of the
  bootstrap medians (ddof=1). Interval: **2.5th/97.5th** percentiles with linear
  interpolation. Blocks are successive retained observations and may span
  gaps in actual race lap numbers; this approximates dependence after filtering.
- All low-confidence samples have 3–9 laps, so their bootstrap SE is blank
  with `too_few_laps_for_two_blocks`. Strict gaps get the same calculation,
  never a different statistic. Gap absent: `gap_unavailable`.
- Clusters: **driver number + stint number**, using every clean lap in the
  original fitted pair. Never combine two drivers' same-numbered stints.
  CR1 multiplier: G/(G−1) × (N−1)/(N−K), with clusters G, laps N and fitted
  coefficients K. Use the cluster sandwich covariance and the same v1 delta
  method for the percentage denominator. Also report the driver coefficient
  cluster SE in seconds. Preserve all OLS SE columns.
- Cluster SE unavailable with missing stint labels, fewer than two clusters,
  a failed model or nonpositive residual degrees of freedom; record a reason.
  `cluster_se_unreliable=True` when **G < 6**, even if a numerical SE exists.
  No points are dropped and this flag does not override the requested labels.
- High: final SE **≤0.15 pp** and count **≥20**. Otherwise medium: SE **≤0.30
  pp** and count **≥10**. Otherwise low for a gap, including missing SE.
  No gap: unavailable. Count is matched laps for matched methods or the smaller
  driver's clean-lap count for regression. Preserve `final_confidence_v1`.
- New disagreement: any two published estimates with finite SEs differ by
  **more than 2 × sqrt(SEa² + SEb²)**. Equality does not flag. Use bootstrap
  and cluster errors; never substitute OLS errors or unreliable point estimates.
  Keep the old flag in `disagreement_flag_fixed_0p3`. With fewer than two
  evaluable estimates, the new flag is blank (`insufficient_standard_errors`).
  Also report the number of evaluable method comparisons per pair.
- Smallest-error selection: only published estimates with finite SEs. Exact
  ties use strict, linear, curved, low-confidence order. Small-cluster SEs are
  allowed, with their warning flag retained. No available SE means no selection.
  Keep `final_gap` unchanged. Count numerical differences greater than **1e-9
  pp** to avoid export noise; report method switches separately. Sign flips
  require opposite nonzero signs. Mean absolute differences include unchanged
  pairs, on pairs with both final and smallest-error gaps; also report the
  changed-only mean. Confidence and disagreement use unrounded new SEs.
- Monaco alone receives `low_overtaking_limited`; all other track flags are
  blank. No numbers or confidence labels change because of this track flag.

## Leave-one-stint-out prediction check

Use pairs with both v1 regression estimates published and known stint labels.
Hold out each whole driver/stint cluster in turn. Refit both versions on all
remaining pair laps. Apply v1's fixed gates to the training data: **10 clean
laps per driver**, one shared compound with **8 per driver**, full column rank,
positive residual degrees of freedom and scaled condition number **≤1,000**.
Estimate centring/scaling and compound categories only from training data.
Reject folds with a held-out compound absent from training; do not invent a
compound effect. No threshold is relaxed to obtain a prediction.

Score both versions only on the same held-out laps in folds where both fits
pass. Save every attempted fold, its exclusion reasons and each available
model's MAE in seconds. Per-race and overall comparisons pool absolute errors
over common held-out laps, weighting every lap equally. One common valid fold
is the minimum to report a race comparison; show fold/lap counts so a tiny
sample is visible. No valid fold means blank error, not zero. Overall is lap-
weighted, not an unweighted average of race means. Report the lower-MAE model
and difference; do not select it for the final gap automatically.

## Zero-clean-lap audit

Audit every v1 pair with either driver's clean count zero. One audit row per
zero-clean driver; both teammates can therefore produce separate rows. Verify
the count against fresh cached cleaning. Report all raw records, non-generated
records, valid timed completed laps, maximum recorded lap number (including
generated laps), status and source. A generated lap is not proof of completion.

The individual race-result CSVs may not contain a status column. If absent,
leave `race_results_csv_status` blank and say so. Use the status already saved
in the existing 2025 race-pace CSV (it came from race results), and check it
against cached race results; never infer finishing status from position.

Cause codes, in order: `real_early_dnf` for explicit retirement, at most one
recorded lap and no more than one valid non-generated completed lap;
`all_laps_filtered` for existing non-generated lap records but none clean;
`missing_data` for a recorded finish/classified lapped result with no raw laps;
otherwise `unknown`. DNS/withdrawal is not labelled DNF: leave `unknown` and
explain the explicit non-start/withdrawal status. No causal fault attribution.
This is a data audit, not a repair or change to performance results.

## Assumptions and limits

All v1 model assumptions still apply: constant driver effect, shared compound
effects and age/progress slopes, linear or quadratic trends, equal lap weights,
and equal-driver weighting of reference predictions. Traffic, damage, team
orders, tyre temperature and strategy selection remain unmodelled. Missing
laps and retirements are not random. Dry classification is the existing weather
and tyre rule; Miami remains explicitly excluded.

Bootstrap assumes the retained sequence and five-observation blocks represent
dependence well enough; breaks and changing stints can violate this. Two blocks
are a minimal check, not proof of adequate uncertainty estimation. CR1 allows
correlation within a stint but assumes clusters are independent. Few clusters,
cross-driver shared conditions and dependence across stints limit reliability.

**The disagreement formula treats estimates as independent even though they
use the same laps. This is a simplification, not a calibrated significance
test.** Confidence labels are fixed heuristics, not probabilities. Choosing
the smallest SE may favour an overconfident model and does not prove accuracy.
Holdout error describes predictions for other stints in the same race, often
with extrapolation in tyre age or race stage; it is not future-race validation
or proof of a causal driver effect. Only common successful folds are compared,
which introduces selection bias. Use only earlier races for future predictions.

## Files and execution

Run `.venv/bin/python race_pace_dry_v2.py`. It reads cached sessions offline,
imports existing scripts and refuses to overwrite its outputs. Use a new
`--output-dir` for another run. Outputs:

- `data/race_pace_dry_combined_v2.csv`
- `data/race_pace_stint_holdout_v2.csv`
- `data/race_pace_prediction_check_v2.csv`
- `data/race_pace_zero_lap_audit.csv`
- `data/race_pace_dry_v2_summary.json`

Results and verification will be appended after the fixed analysis completes.

## Completed run

All 200 dry-race pairs retain exactly their v1 final gaps and method choices. All existing scripts, tests and CSVs remain untouched. The v2 output has 168 gaps and 32 blanks.

| Confidence label | Pairs |
| --- | ---: |
| High | 100 |
| Medium | 58 |
| Low | 10 |
| Unavailable | 32 |

All 99 strict gaps have bootstrap SEs and percentile intervals. All 12 available low-confidence gaps have blank SEs because they contain fewer than two five-observation blocks. All 159 published linear and curved regressions have cluster SEs. **91 of the 159 regression pairs have fewer than six clusters.** Their warning flags remain visible, but the requested confidence rule does not downgrade them automatically.

The fixed 0.3 pp disagreement rule flags 31 pairs; the uncertainty rule flags 33; 16 pairs are flagged by both. For 41 pairs fewer than two estimates have usable SEs, so the new flag is blank rather than a claim of agreement.

### Stint holdout results

There are 816 attempted folds and 470 common successful folds, containing 7,799 held-out laps. Linear has lower overall lap-weighted MAE by **0.019073 seconds** (linear 0.801640 s, curved 0.820713 s). Linear has lower MAE in eight races and curved in six. Six races have no common successful folds. These results do not choose a model for the final table.

| Race | Common folds | Held-out laps | Linear MAE (s) | Curved MAE (s) | Lower-error model | Advantage (s) |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| Chinese Grand Prix | 11 | 141 | 1.838299 | 2.849687 | linear | 1.011388 |
| Japanese Grand Prix | 0 | 0 | — | — | unavailable | — |
| Bahrain Grand Prix | 50 | 714 | 0.654431 | 0.678855 | linear | 0.024423 |
| Saudi Arabian Grand Prix | 0 | 0 | — | — | unavailable | — |
| Emilia Romagna Grand Prix | 52 | 820 | 0.706804 | 0.613953 | curved | 0.092851 |
| Monaco Grand Prix | 33 | 553 | 2.388506 | 2.307730 | curved | 0.080776 |
| Spanish Grand Prix | 65 | 836 | 0.557694 | 0.615842 | linear | 0.058148 |
| Canadian Grand Prix | 28 | 517 | 0.411801 | 0.435950 | linear | 0.024148 |
| Austrian Grand Prix | 27 | 545 | 0.523184 | 0.523095 | curved | 0.000089 |
| Hungarian Grand Prix | 31 | 736 | 1.201497 | 1.150925 | curved | 0.050572 |
| Dutch Grand Prix | 37 | 534 | 0.853976 | 0.865894 | linear | 0.011918 |
| Italian Grand Prix | 0 | 0 | — | — | unavailable | — |
| Azerbaijan Grand Prix | 0 | 0 | — | — | unavailable | — |
| Singapore Grand Prix | 0 | 0 | — | — | unavailable | — |
| United States Grand Prix | 5 | 88 | 0.491301 | 0.737689 | linear | 0.246388 |
| Mexico City Grand Prix | 27 | 563 | 0.670922 | 0.609261 | curved | 0.061661 |
| São Paulo Grand Prix | 43 | 829 | 0.485826 | 0.536914 | linear | 0.051088 |
| Las Vegas Grand Prix | 0 | 0 | — | — | unavailable | — |
| Qatar Grand Prix | 45 | 634 | 0.453675 | 0.415828 | curved | 0.037847 |
| Abu Dhabi Grand Prix | 16 | 289 | 0.723759 | 0.979807 | linear | 0.256049 |
| Overall | 470 | 7799 | 0.801640 | 0.820713 | linear | 0.019073 |

Training failures are retained in the fold CSV. Per-model reasons (one fold can appear under both models):

| Reason | Linear folds | Curved folds |
| --- | ---: | ---: |
| effects_not_identifiable | 260 | 260 |
| strategy_confounded | 38 | 38 |
| too_few_clean_laps | 12 | 12 |
| unseen_compound | 36 | 36 |

### Smallest-error comparison

All 168 pairs with a final gap also have a smallest-error choice. It selects a different method and gap for **105 pairs**, with **10 sign flips**. The mean absolute change is **0.079949 pp across all 168 pairs**, or **0.127918 pp among the 105 changed pairs**. The selected estimate is only an inspection column; final_gap is unchanged.

### Zero-clean-lap audit

Fourteen zero-clean drivers in fourteen pairs were audited: the nine no-race-lap pairs plus five strategy-confounded pairs with a zero-clean driver. Counts: **7 real_early_dnf, 4 all_laps_filtered, 0 missing_data, 3 unknown**. The unknown entries are Stroll in Spain (absent from race results), Sainz in Austria (did not start), and Hülkenberg in Italy (did not start). Their statuses are explicit; the allowed cause vocabulary has no DNS code, so they are not incorrectly called retirements.

The individual race CSVs have no Status column. The audit shows that missing field and uses driver_status from the existing race-pace CSV, verified against cached race results, with source provenance. No status is inferred from position.

### Verification

All **45 tests passed**, including every existing test and eight new uncertainty/integration tests. The saved-file test compares every final_gap and method_used exactly against v1, along with every other v1 column not explicitly replaced. CR1 is checked against an independently assembled matrix formula; the bootstrap seed, two-block boundary, confidence thresholds and disagreement boundary have focused tests.

CR1 reference: [statsmodels cluster covariance documentation](https://www.statsmodels.org/v0.14.0/generated/statsmodels.stats.sandwich_covariance.cov_cluster.html). Implementation uses NumPy directly; no new dependency was installed.
