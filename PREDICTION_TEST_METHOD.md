# Approved 2025 teammate prediction test

This implements the final pasted approval, which takes precedence over
PREDICTION_TEST_SPEC.md. The main target is **both teammates finishing**, including
lapped finishers. The history gate is **four earlier calendar rounds**, plus
three earlier valid qualifying comparisons for each driver. No setting was
changed after seeing prediction results.

## Counts first

All methods use identical complete cases within each target and report.
Rounds 5–12 supply initial training; rounds 13–24 supply the main expanding-window
score. Every main score below covers 12 weekends.

| Target | Eligible rows, rounds 5–24 | Initial training rows / weekends | Main scored rows | Main exclusions out of 120 | Early first round | Early rows / weekends | Earlier fallback rows |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Main: both finish | 149 | 54 / 8 | 95 | 25 | 8 | 34 / 5 | 20 |
| Sensitivity: all starters | 186 | 73 / 8 | 113 | 7 | 7 | 53 / 6 | 20 |
| Sensitivity: no double retirement | 183 | 72 / 8 | 111 | 9 | 7 | 52 / 6 | 20 |

Before qualifying and history gates, 185 season pairs have both finishers,
232 have both starters without a disqualification, and 229 also exclude double
retirements. Those are outcome counts, not prediction sample sizes. Seven pairs
lack a current qualifying gap and are listed in missing_qualifying_pairs.csv;
none receives a rating-only fallback. All reasons, including overlapping reasons,
are retained in eligibility.csv. Primary exclusion counts are mutually exclusive.

The main 95 scored pairs exclude 25 of the 120 possible pairs in rounds 13–24:
19 involving a retirement, one non-start, one DQ pair, and four additional pairs
without qualifying. The all-starters sensitivity excludes seven (one non-start,
one DQ pair and five missing qualifying); the no-double-retirement sensitivity
excludes nine, adding two double retirements. These totals describe the scoring
window, not the whole season.

## Frozen configuration and inputs

The script reads prediction_test_config.json. It records the season, input paths,
status definitions, history gates, schedule, all model choices, rating weights,
baseline conventions, metric settings, bootstrap settings and output rules.
The exact bytes and SHA-256 hash are copied into every new numbered run folder.
The completed run is [prediction_001](data/runs/prediction_001/).

Configuration SHA-256: `ea1bfd32b92d1f80f00bd791a77b3d1425c89db20810881de32ef62ed032a2dd`.

Inputs are the approved combined and per-round qualifying files, dry and wet
final race-pace files, and the 24 race-result CSVs. Only explicitly named columns
are read. Points and race-win columns are never read or passed to any model.
The requested head-to-head baseline counts earlier pair outcomes; these are not
race-win totals. The full-season rating file is used only for validation and,
after all predictions are fixed, to label the nine group diagnostics.

The existing FastF1 HTTP cache is opened through SQLite with
`mode=ro&immutable=1`. There is no session loading, cache update, HTTP request or
network-dependent package installation. The script extracts the cached Jolpica
status records and matches their positions and roster against the race CSVs.
The new [status file](data/2025_race_finish_status.csv) contains 479 records, all
with matching positions and a source URL and source note. Status counts are
330 Finished, 89 Lapped, 51 Retired, six Disqualified and three Did not start.
Stroll's absent Spanish result stays absent; it is not guessed to be a status.
A missing, duplicate, unknown or conflicting cached record stops publication.

## Target, orientation and history

The outcome is whether A has a lower official Position than B. A is the
alphabetically first driver code only to label the row. The three targets are:

- Main: both drivers have Finished or Lapped status, neither is disqualified,
  and a current qualifying gap is available.
- All-starters sensitivity: retain single and double retirements, excluding
  non-starters, disqualifications and missing results.
- No-double-retirement sensitivity: the preceding rule, also excluding pairs
  where both retired.

Each uses the same four-round and three-prior-qualifying-comparison history
requirements and complete-case qualifying requirement. There is no fault
classification or inferred responsibility for a retirement.

**The main target conditions on surviving the race, something known only after
it happens. Its accuracy is conditional on both drivers finishing and must not
be read as unconditional pre-race accuracy.** Status and finishing positions
select labels and scoring rows; they are not model features. Sensitivities are
separate analyses and are never pooled into the main score.

Keep actual team and teammate histories. Lawson and Tsunoda change teams after
round 2. Gasly switches from Doohan to Colapinto after round 6. Colapinto has no
invented earlier history and passes the three-comparison gate in round 10.
Provisional ratings are allowed. A missing wet signal contributes no observation;
it does not become a zero gap.

## Rating rebuild and leakage safeguards

For a feature round n, all four rating input tables are cut to rounds strictly
less than n **before** calculating anything. The adapter rebuilds each driver's
appearances and eligible signal records from that slice. It calls the existing
qualifying combination and driver_rating calculation functions in memory:
log_pair, add_weights, season_arrays, summarize_signal and rating_status.
Their publishing entry points and the original full-season roster checker are
not called. This avoids its hard-coded whole-season roster requirement while
preserving the calculation and recomputing coverage, support and actual histories.

The retained method is `2025_teammate_rating_1_log_round_fix`: per-round symmetric
log conversion before weighting Q3 0.50, Q2 0.30 and Q1 0.20, renormalized over
available rounds. Saved combined qualifying values are checked against the
recombination; this weekend's stored combined log gap is read directly as a
separate feature and is never log-converted again or put into the prior rating.

Signal weights remain 45% qualifying / 45% dry / 10% wet, multiplied by
`min(1, effective_races / reference)` with references 8, 8 and 3, then normalized.
Qualifying observations have equal weight. Race precision weights stay
`max(0.25, 1 / (1 + (SE_log / 0.15)^2))`; missing SE uses 0.25. Monaco dry weight
is multiplied by 0.5. Existing gap conversion, missing-signal handling and
provisional-status rules are retained. Counts, coverage, effective races,
component ratings and actual signal weights are exported in prior_ratings.csv.

Full-slice validation used all 24 rounds only in a separate validation call.
Every rebuilt combined score rounds to the saved three-decimal score. The
maximum absolute difference is **0.000499049683** log-percentage points.
The predeclared tolerance is 0.000500000001, half the CSV's last displayed unit
plus a tiny arithmetic allowance. This is a serialization tolerance, not a
change to the rating method. Failure stops the run before predictions.

Models never receive full-season ratings, group labels, confidence labels,
future roster changes, points, wins, or current-race dry/wet evidence, finishing
positions, statuses or laps completed. Historical training features stay fixed
at what was available before their own races. No normalization or coefficient
fit uses future rows. The feature export includes outcome/status fields for
auditing only; the model function selects its one or two named feature columns.

These are saved historical snapshots: later corrections can appear in exports.
Consequently this is an earlier-round retrospective test, not proof that every
source record was available in exactly this form on the actual prediction date.

## Models, baselines and fitting schedule

All models use logistic regression with **no intercept, C=1 and an L2 penalty**:

- M1: B's earlier combined rating minus A's.
- M2: negative of A's current combined qualifying log gap.
- M3: both features.

Positive features favour A. No identities, teams, interactions, track terms or
feature scaling are included. SciPy 1.18.1 was already installed and fits the
objective `sum(logistic loss) + sum(coefficients squared) / (2*C)`. The fixed
solver is L-BFGS-B, maximum 1,000 iterations, gradient tolerance 1e-10 and
function tolerance 1e-12. These are numerical convergence settings, not tuned
model choices. Swapping A and B reverses the features exactly. A symmetric
sigmoid implementation returns exact floating-point complementary probabilities.

Before each weekend, fit only eligible examples from earlier weekends for that
target. Predict every pair at that weekend before allowing any of its outcomes
into later fitting. All three models use the same rows and fitting schedule.
A fit failure or fewer than 15 earlier eligible examples uses the smoothed
qualifying baseline probability and carries an explicit fallback reason.
There were no fit failures or model fallback cases in the main scoring windows.

The early-season language has two parts: report from the first weekend with
15 earlier training rows, but flag fallback predictions before that. Accordingly,
all eligible rounds 5–12 have saved predictions; `early` contains only the
requested scored window beginning at the 15-row gate, while `early_fallback`
contains the preceding flagged predictions. These are never pooled. Main-target
early scoring begins in round 8; both sensitivities begin in round 7. There are
20 earlier fallback cases for each target. This interpretation was frozen in
the config before results. Early outcomes later become legitimate past training
examples for the main test, so the two reports are not independent experiments.

Baseline rules are fixed as follows:

- Qualifying picks the lower current combined log gap; grid picks the lower
  GridPosition. A tied/nonfinite/nonpositive/duplicated grid value produces
  probability 0.5 and a flag. No scored grid value required that flag here.
- Previous race uses only the immediately preceding calendar round for these
  exact teammates, and only a main-target-usable outcome (both finish and valid
  qualifying). Otherwise it is 0.5, with no look-back to an older race.
- Head-to-head uses `(earlier successes + 1) / (earlier comparisons + 2)` for
  the current teammate period; no history gives 0.5. For consistency with the
  previous-race baseline, usable historical outcomes follow the main target
  before its history gate, including rounds 1–4. This convention is held fixed
  for the sensitivity targets; changing target does not redefine historical
  pair success. A change in team or teammate resets the period.
- Chance is 0.5.

For each hard-pick rule, its probability of being right is
`(earlier correct picks + 1) / (earlier usable picks + 2)`, calibrated on that
target's earlier eligible training rows from round 5. A missing or tied hard
pick is excluded from that calibration and predicts 0.5. Probabilities are
assigned to the picked driver and complemented for the other driver. There is
no calibration on the weekend being predicted. Qualifying pace and starting
grid are distinct: weighted round pace is not official qualifying position.

## Metrics and paired uncertainty

Primary metric is Brier score; accuracy and log loss are also reported. Lower
Brier/log loss is better; higher accuracy is better. Exactly 0.5 gets half
accuracy credit, with tie counts exported. Only log-loss computation clips
probabilities to [0.000001, 0.999999]; Brier and accuracy use the original values.

There are 2,000 whole-scored-weekend resamples, seed 42. Each draw carries all
pair outcomes and all methods together; every candidate-minus-baseline
comparison uses identical draws. Intervals are the 2.5th and 97.5th percentiles.
Rows and teammate directions are never independently resampled; models are not
refit on a shuffled or bootstrapped chronology. The intervals condition on the
observed fitted prediction path and do not include every source of training
uncertainty. Main, early and fallback periods, and all three targets, remain
separate. Very short early/fallback windows have particularly weak intervals.

M3 versus M2 is predeclared as the primary comparison. M1 and M3 are additionally
compared against every simple baseline. The best observed simple baseline is
reported separately for Brier, accuracy and log loss and labelled exploratory;
selecting the best after scoring is not a preselected significance comparison.

## Main results: both finish, rounds 13–24

All rows below have 95 pairs and 12 weekends, with the same 25 exclusions.
Brackets show weekend-bootstrap intervals. Accuracy is in percent.

| Method | Brier [95% interval] | Accuracy % [95% interval] | Log loss [95% interval] | Ties |
| --- | --- | --- | --- | --- |
| M1 | 0.1977 [0.1711, 0.2230] | 66.3 [59.6, 73.4] | 0.5714 [0.5145, 0.6261] | 0 |
| M2 | 0.1748 [0.1501, 0.1986] | 72.6 [65.2, 78.9] | 0.5208 [0.4562, 0.5805] | 0 |
| M3 | 0.1665 [0.1391, 0.1938] | 75.8 [70.5, 81.8] | 0.4968 [0.4276, 0.5652] | 0 |
| qualifying | 0.2029 [0.1814, 0.2280] | 72.6 [65.2, 78.9] | 0.5964 [0.5515, 0.6485] | 0 |
| grid | 0.2030 [0.1806, 0.2273] | 72.6 [65.6, 79.5] | 0.5967 [0.5501, 0.6472] | 0 |
| previous | 0.2344 [0.2134, 0.2530] | 61.6 [55.2, 69.3] | 0.6617 [0.6187, 0.6999] | 21 |
| head_to_head | 0.2078 [0.1720, 0.2442] | 65.8 [57.3, 74.5] | 0.5989 [0.5107, 0.6857] | 5 |
| chance | 0.2500 [0.2500, 0.2500] | 50.0 [50.0, 50.0] | 0.6931 [0.6931, 0.6931] | 95 |

M3 minus M2 is **−0.008274 Brier** [−0.025746, +0.008340],
**+3.16 accuracy points** [−3.06, +10.47], and **−0.023980 log loss**
[−0.062065, +0.012944]. M3 made 72 correct predictions versus M2's 69.
All three paired intervals include zero. The simple qualifying rule wins Brier
among simple baselines; qualifying and grid tie for best simple-baseline
accuracy. M2 has the same hard choices as the qualifying rule here, but its
probabilities use gap size rather than a single smoothed success rate.

The M3 rating coefficient stays positive across the main refits, from 0.993595
to 1.258084; that is not a statistical test of its importance. The qualifying
coefficient ranges from 1.435089 to 2.108053. Every model's coefficients, prior
training-row counts, maximum training round and fallback reasons are in
[coefficients.csv](data/runs/prediction_001/coefficients.csv). Main M3 refits are:

| Predicted round | Earlier training rows | Rating coefficient | Qualifying coefficient |
| --- | --- | --- | --- |
| 13 | 54 | 1.258084 | 1.435089 |
| 14 | 64 | 1.113024 | 1.577642 |
| 15 | 73 | 0.993595 | 1.837115 |
| 16 | 80 | 0.998612 | 1.711379 |
| 17 | 88 | 1.120542 | 1.754181 |
| 18 | 96 | 1.114267 | 1.720602 |
| 19 | 105 | 1.163759 | 1.846599 |
| 20 | 113 | 1.166106 | 1.891948 |
| 21 | 119 | 1.157844 | 1.885178 |
| 22 | 127 | 1.083446 | 2.082086 |
| 23 | 133 | 1.107569 | 2.108053 |
| 24 | 139 | 1.014513 | 2.035721 |

## Sensitivities and exploratory early results

These reports use their own target-specific earlier training rows and remain
separate. Differences below are M3 minus M2; negative Brier favours adding the
rating. Every displayed paired interval includes zero.

| Target | Report | Pairs | M2 Brier | M3 Brier | Brier difference [95%] | Accuracy-point difference [95%] |
| --- | --- | --- | --- | --- | --- | --- |
| Main: both finish | early | 34 | 0.2013 | 0.1813 | -0.0200 [-0.0700, +0.0327] | +5.88 [-5.71, +21.88] |
| Sensitivity: all starters | main | 113 | 0.1987 | 0.1917 | -0.0070 [-0.0204, +0.0060] | +3.54 [-1.74, +8.85] |
| Sensitivity: all starters | early | 53 | 0.2254 | 0.2121 | -0.0134 [-0.0480, +0.0229] | +7.55 [-1.89, +17.65] |
| Sensitivity: no double retirement | main | 111 | 0.1967 | 0.1897 | -0.0070 [-0.0194, +0.0049] | +3.60 [-1.77, +8.93] |
| Sensitivity: no double retirement | early | 52 | 0.2268 | 0.2147 | -0.0121 [-0.0473, +0.0242] | +7.69 [-1.96, +18.00] |

All-starters main accuracy is 68.14% for M2 and 71.68% for M3; excluding double
retirements gives 68.47% and 72.07%. Head-to-head is the best simple baseline
by Brier for these sensitivities, while grid and qualifying tie on accuracy.
The early main-target accuracies are 70.59% and 76.47%; early all-starters are
62.26% and 69.81%; early no-double-retirement are 61.54% and 69.23%.
Full metric levels, intervals, ties, exclusions and all baseline comparisons
are saved in metrics.csv, comparisons.csv and baseline_winners.csv, including
the flagged fallback periods. The fallback model comparisons are identical by
construction and provide no evidence that one model is better.

## Leave-one-teammate-group-out stability

Omit each group from the scored summary only; do not refit or remove its earlier
training history. The full-season group mapping is used only here, after
predictions are fixed. These are correlated checks, not nine independent tests.
For the main report:

| Omitted group | Pairs remaining | M3−M2 Brier | M3−M2 accuracy points |
| --- | --- | --- | --- |
| ALB+SAI | 87 | -0.008521 | +2.30 |
| ALO+STR | 88 | -0.006875 | +3.41 |
| ANT+RUS | 83 | -0.008087 | +3.61 |
| BEA+OCO | 86 | -0.011570 | +3.49 |
| BOR+HUL | 88 | -0.008592 | +3.41 |
| COL+DOO+GAS | 83 | -0.010651 | +3.61 |
| HAD+LAW+TSU+VER | 74 | -0.006103 | +4.05 |
| HAM+LEC | 85 | -0.002414 | +1.18 |
| NOR+PIA | 86 | -0.011379 | +3.49 |

The point estimate still favours M3 after each omission. Removing Hamilton/
Leclerc leaves the smallest Brier advantage. This stability does not remove
the uncertainty in the paired comparison. Group tables for every target and
report are saved in group_stability.csv.

## What this does and does not show

The point estimates suggest that earlier teammate ratings may add information
beyond current qualifying. On this run the improvement is modest and uncertain;
we cannot call it proof of a gain or proof of no gain. Rating alone performs
worse than qualifying alone in the main report. None of these results separates
driver skill from car, strategy, reliability or opponent strength, and none
supports a grid-wide absolute ability ranking.

The method was developed while examining 2025, so this season remains
**exploratory**. The main score covers only 12 weekends and about nine independent
teammate groups, and its both-finish selection creates survivorship bias.
The prior-rating and current-qualifying features correlate at **0.457563** in
the main scored sample (about 0.459–0.460 in the sensitivities). Their information
overlaps; a positive coefficient is not a causal driver-skill effect. Wet
history is sparse, teammate changes can change score meaning, and provisional
histories remain possible. Nine main cases involve at least one provisional
prior rating.

One extra correct prediction changes the main accuracy by about 1.05 points.
Rough planning resolution is on the order of **8–14 accuracy points**, not
1–3; with this smaller 95-case main target, the proposal's independent-pair
illustration with 10%–30% disagreement is about 9–16 points. Dependence and
only 12 weekends can make resolution worse. These are planning approximations,
not measured power guarantees. Weekend bootstrapping does not resolve persistent
teammate-group dependence or later data corrections. A frozen later-season test
is needed before a general predictive claim; no other season was built or run.

## Files, rerunning and verification

New root files are prediction_test.py, test_prediction_test.py,
prediction_test_config.json and this document. The new canonical status export
is data/2025_race_finish_status.csv. Other outputs are confined to the numbered
run folder: predictions.csv (one row per pair-race and method), metrics.csv,
bootstrap.csv (all draws by method), comparisons.csv (paired differences and
intervals), counts.csv, coefficients.csv, group_stability.csv,
baseline_winners.csv, eligibility.csv, excluded_pairs.csv,
missing_qualifying_pairs.csv, features.csv, prior_ratings.csv,
full_slice_validation.csv, a run-local status copy, config copy, config.sha256,
and summary.json with source/script hashes and runtime.

Run from the project directory:

```sh
.venv/bin/python prediction_test.py
```

A rerun reserves the next unused prediction_NNN folder. Existing run outputs
are never overwritten. An existing canonical status file is compared with the
cache extraction and preserved; a conflict stops the run. A later season can
be configured through the season, paths, round count and schedule settings,
using the same approved method; no existing script needs editing.

The requested full suite was run with:

```sh
.venv/bin/python -m unittest discover -v
```

PYTHONDONTWRITEBYTECODE=1 was set to avoid changing bytecode caches.
**126 tests passed: 112 existing and 14 new.** New tests cover prior-feature
invariance to deleted/corrupted current and future data, intentional separation
of current qualifying, exact swap complements, no intercept and the penalized
fit optimum, strict input columns, status counts and lapped finishers,
bootstrap repeatability, tie credit, smoothing, full-slice parity, teammate
changes, current-qualifying exclusions, earlier-only fitting/fallbacks, and
protected output folders. Existing dependency deprecation warnings were nonfatal.
No source data, existing script, test, document, chart or cache was changed.
The single production run took **3.14 seconds**, excluding tests and documentation.
