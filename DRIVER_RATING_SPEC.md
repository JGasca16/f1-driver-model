# Proposed 2025 driver season rating

**Proposal only.** No driver ratings have been calculated and no pipeline or
source data has been changed. All numerical choices below are suggested
starting values for review, not values fitted to produce a preferred ranking.
No points, wins or finishing positions would be inputs.

## Inputs checked

Read METHOD.md, QUALIFYING.md, METHOD_DRY_RACEPACE.md and METHOD_WET_RACEPACE.md.
The requested `data/qualifying_gaps.csv` does not exist. The documented file is
`data/2025_qualifying_teammate_gaps.csv`, which was inspected instead. A future
implementation should use that explicit path, not silently guess a filename.

| Signal | File | Observed coverage |
| --- | --- | --- |
| Qualifying | `data/2025_qualifying_teammate_gaps.csv` | 466 of 480 driver rows; 233 of 240 unique pairs |
| Dry race pace | `data/race_pace_dry_final.csv` | 168 of 200 unique pairs |
| Wet race pace | `data/race_pace_wet_final.csv` | 6 of 30 unique pairs; only one pair labelled high confidence |

There are **21 drivers** in the qualifying roster. Qualifying already contains
both directions of each pair; the race files contain one direction. These are
different row conventions, not different numbers of independent observations.
Use the dry `final_gap` and its `final_se_pp`, retaining its strict-first method
choice. Use the wet primary `wet_gap_2pct` and its error. Do not choose alternative
dry estimates or wet thresholds based on which makes a driver's rating better.
Miami qualifying is available; Miami race pace remains absent from both race
signals. Missing race-pace coverage must not erase its qualifying observation.

## 1. Sign and direction

**Recommendation: give both drivers equal and opposite contributions on a
symmetric time-ratio scale, with negative always meaning faster.**

The existing percentage uses the teammate's time as its denominator. Merely
flipping its sign is not an exact reversal: 90.0 versus 90.3 seconds is about
−0.332226%, while the reverse is +0.333333%. If ordinary percentages were kept,
the reciprocal percentage would be `−100 × g / (100 + g)`, not simply `−g`.

For aggregation, propose a symmetric conversion:

`driver contribution = 100 × ln(1 + g / 100)`

`teammate contribution = −driver contribution`

Here `g` is the stored percentage gap. This is a change of units that makes
orientation consistent. Near the small gaps seen in this project, the value
is close to an ordinary percentage. For 90.0 versus 90.3 seconds the two
contributions are approximately −0.332779 and +0.332779. Call the units
**log-percentage points**, and describe them as approximately percentage pace
differences for small values. Lower is better; zero means level with the
observed teammates. Do not turn them into an arbitrary 0–100 score in version 1.

Use the full contribution for each driver's own teammate-relative record, not
half of it. These are individual records of outperformance, not latent ability
parameters whose difference reconstructs the original gap. In particular,
subtracting the two season scores is not a new predicted head-to-head gap.

For qualifying, keep one canonical pair observation per race/team, preferably
using the named comparison times to calculate the ratio, then create the two
driver contributions. Check the second source row agrees; do not count it as
additional evidence. Do not use the overall best times when the comparison
used a particular shared qualifying round. For race pace, transform the
published pair summary and assign its opposite to the teammate. This defines
a new symmetric summary; it does not reconstruct a separately calculated
reverse median from the unavailable individual lap gaps.

A blank stays blank. Nonfinite gaps or values at or below −100% are invalid
inputs and should stop that observation from entering the rating. Approximate
error conversion is `SE_log = SE_percentage / (1 + g / 100)`; both drivers share
the same error for the canonical comparison. Their errors are linked, not two
independent measurements.

## 2. Combining races within each signal

**Recommendation: calculate a separate weighted mean for qualifying, dry pace
and wet pace, with one contribution per driver per race per signal.** Use the
weights described below and divide the weighted sum by the sum of weights.
This keeps the score interpretable as average teammate-relative outperformance
on the available evidence. It also avoids letting a race with 40 retained laps
count as four races compared with a race with ten laps.

A plain mean is a useful reference but treats weak and precise race estimates
alike. A median resists unusual races but ignores much of the size of an
advantage and can be unstable with very few observations. Propose the weighted
mean as the reported estimate and an ordinary median as a review statistic.
Show both when they tell different stories. Do not remove a large gap solely
because it is large, or select the mean/median after seeing which ranking looks
more plausible. No recency weighting is proposed: the target is the whole
2025 season rather than end-of-season form.

### Teammate changes actually present in 2025

| Driver/team situation | Rounds | Comparison |
| --- | --- | --- |
| Lawson at Red Bull Racing | 1–2 | Verstappen |
| Tsunoda at Racing Bulls | 1–2 | Hadjar |
| Tsunoda at Red Bull Racing | 3–24 | Verstappen |
| Lawson at Racing Bulls | 3–24 | Hadjar |
| Gasly at Alpine | 1–6 | Doohan |
| Gasly at Alpine | 7–24 | Colapinto |

These assignments are in the inspected data. Doohan has six qualifying
appearances and Colapinto has eighteen; the other nineteen drivers have 24.
Verstappen, Hadjar and Gasly also change comparison partners even though they
stay with their teams.

Use whoever was the driver's actual teammate in each race. Pool race
observations with the same weighting rules across these periods, and also
report a breakdown by team/teammate period. Do not give a two-race period the
same total weight as a 22-race period merely because they are two distinct
teammates. A change in average gap can reflect a different opponent or car,
not a change in the driver's own ability.

**Do not claim to correct for teammate strength in version 1.** The 2025
teammate links form nine disconnected comparison groups: the four Red
Bull/Racing Bulls drivers, the three Alpine drivers, and seven other teammate
pairs. Within-season comparisons alone cannot establish a common ability
baseline across those groups. Even a model that adjusts for opponents would
need extra assumptions or evidence to compare those disconnected groups.
The proposed overall score therefore ranks observed outperformance against
actual teammates, not absolute strength against every driver on the grid.

## 3. Relative qualifying, dry and wet weights

**Recommended full-evidence weights: 50% qualifying, 45% dry pace, 5% wet pace.**

Qualifying has almost complete coverage and supplies a consistent repeated
comparison. Dry pace deserves almost as much weight because it measures race
performance, although its coverage and methods vary. Wet pace gets a small
share because only six pairs have a result and its traffic/weather selection
has substantial limitations. The weights express the proposed purpose of the
rating; coverage alone cannot prove they are optimal.

Combine signal scores only after computing each separately. Do not pool all
raw rows: that would let row conventions and the number of available sessions
quietly choose the relative signal weights. Keep all three component scores
visible next to the overall score. Do not standardise each signal to unit
spread across drivers: doing so would estimate the wet scale from very little
data and remove the direct pace interpretation.

Reduce the influence of a signal with very little evidence before combining:

- Qualifying and dry evidence factor: `min(1, effective_races / 8)`.
- Wet evidence factor: `min(1, effective_races / 3)`.

Multiply the base signal weight by its evidence factor, then normalise the
available signal weights to sum to one. A missing signal has no contribution;
it is not given a zero pace score. Report the actual weights for every driver.
For example, with full qualifying/dry evidence and no wet result, the weights
become approximately 52.63% qualifying and 47.37% dry. With those same inputs
and just one wet race, they become approximately 51.72%, 46.55% and 1.72%.
Thus the proposed 5% wet share is a full-evidence allocation, not an automatic
five-percent influence for a single race.

This normalisation means drivers with different missing signals have somewhat
different rating mixtures. That is a limitation to show, not hide. It should
also be possible to inspect a common qualifying-plus-dry score for comparison.
The eight- and three-race reference sizes are proposed safeguards, not validated
thresholds and not promises that three wet races establish typical wet skill.

## 4. Confidence and sample size within a signal

**Recommendation: equal race weights for qualifying; bounded precision weights
for dry and wet pace.** For a race-pace observation, propose:

`weight = max(0.25, 1 / (1 + (SE_log / 0.15)^2))`

This gives more weight to smaller errors without the extreme influence that
uncapped inverse-variance weighting can give one apparently precise race.
The precision weight ranges from 0.25 to 1, so its maximum ratio is four to
one. The 0.15 reference value follows the existing high-confidence boundary;
its use here remains a proposed choice. If an accepted gap lacks an SE, use
weight 0.25 and explicitly flag missing uncertainty. A reported zero SE should
also be flagged for review; it does not prove zero real uncertainty.

Keep the existing high/medium/low labels as readable diagnostics. Do not also
multiply by a label weight or by the number of laps: error, labels and sample
size overlap, so applying all three would repeatedly reward the same evidence.
The existing per-race eligibility rules still enforce minimum lap counts.
Report matched counts for strict/wet estimates and the smaller driver's clean
count for regression. These counts let readers see what underlies the error.

Qualifying has no comparable per-race SE. Give each valid comparison weight 1
rather than inventing errors. Track Q1/Q2/Q3 counts and timing-source flags.
Do not automatically penalise a recovered time or a valid earlier-round gap
because another round has a flag. Any round-specific weight would need a
separate justification; the latest shared valid round remains the source rule.

Propose a further **0.5 multiplier for Monaco dry pace** because a precise
traffic-constrained gap can still be a poor measure of unrestricted pace.
This changes its contribution to a future season summary only, not the
published race gap. Do not add other track multipliers without review. Report
how much this multiplier affects a score as a sensitivity check before adoption.

Use the same pair weight for both drivers, preserving symmetry. Calculate
**effective races** as `(sum of weights)^2 / sum of squared weights`. In plain
language, this is the number of equally weighted races giving similar support.
It cannot exceed the number of contributing races. It is a useful warning
about uneven weights, not a correction for dependence between races.

## 5. Missing data and provisional ratings

**Recommendation: use available valid observations without a pace penalty for
missing races, and lower the strength of the claim when evidence is thin.**

A blank can arise from a disqualification, retirement, no usable teammate lap,
incompatible strategy or filtering. Replacing it with zero would manufacture
a tie. Giving it a negative performance penalty would turn a pace rating into
an undocumented mixture of pace, availability and reliability. Conversely,
ignoring blanks without reporting coverage could make two or three unusually
good races look like a well-established season advantage.

For each driver/signal, show valid races, eligible appearances, missing count,
coverage fraction, effective races and missing reasons. Eligible appearances
mean races the driver entered within that signal's existing scope, including
those whose gaps are blank. They are not always 24: Doohan and Colapinto have
partial seasons; dry excludes wet races and Miami; wet covers only Australia,
Britain and Belgium. Miami remains excluded from race eligibility rather than
counted as a driver-specific failure. Also show total season appearances so
100% coverage of a short career segment is not mistaken for a full season.

Allow a descriptive component score with one observation, but label it as
single-race evidence. An overall score can be provisional if at least one of
qualifying or dry pace is available; wet-only evidence should leave the overall
season score blank. Propose withholding a formal season rank unless **both
qualifying and dry have at least six effective races and at least 50% coverage**.
Still show provisional numbers and their limitations rather than dropping the
driver from the table. A formal rank, if later approved, would remain a rank
of teammate outperformance rather than proven absolute skill.

Suggested overall confidence labels describe support, not probabilities:

- **High:** qualifying and dry each have at least 12 effective races and 75%
  coverage, with a usable season uncertainty range.
- **Medium:** both have at least six effective races and 50% coverage, with a
  usable season uncertainty range, but the high rule is not met.
- **Low/provisional:** an overall score exists but neither rule above is met.
- **Unavailable:** neither qualifying nor dry provides a usable component.

Sparse wet data cannot upgrade overall confidence. Report its own support
separately. These safeguards do not remove selection bias: missing races may
systematically be the difficult races, not a random sample of opportunities.
There is no proposed imputation, shrinkage toward zero or missing-race penalty
in the initial version. Any such adjustment would add an assumption about what
the missing performance would have been and needs separate approval.

## 6. Uncertainty on the season score

**Recommendation: a race-weekend bootstrap, with a clearly labelled approximate
range and an explicit warning for small samples.** Propose 2,000 resamples,
seed 42, and the 2.5th/97.5th percentiles of the resulting season scores.

Resample the 24 whole race weekends with replacement. Carry each sampled
weekend's qualifying, dry/wet results, blanks, driver roster and both sides of
every pair together. Recompute component means, evidence factors and overall
weights in each resample. Repeated draws of one weekend do not create new
underlying evidence. Keeping the whole weekend together preserves the link
between teammates and between qualifying and race pace at that event; treating
all driver rows as independent would overstate the sample size.

This captures observed variation between race weekends and sensitivity to
which races are included. Keep per-race SEs in the weighting and display them
in diagnostics. Do not add independent random noise from those SEs by default:
the variation across observed race estimates already contains measurement noise,
and adding it again can double-count uncertainty. This bootstrap still does
not fully capture within-race uncertainty, changing car development or the
systematic effects of filtering and teammate strength.

Do not publish a season range from fewer than six distinct contributing race
weekends. If a resample cannot produce an overall score, record that fact;
propose requiring at least 95% of attempts to be usable before publishing the
range. Otherwise leave the range blank and label it insufficient evidence.
Use the full-sample counts for the reported confidence label. Report valid
bootstrap attempts rather than quietly retrying until enough succeed.

For a driver with only one wet observation, its race-level interval can be
shown, but the wet **season** interval should be unavailable: repeating that
one race cannot reveal normal variation across wet races. A narrow combined
range is conditional on the observed wet evidence and does not establish the
precision of the driver's typical wet ability. Call the range an approximate
sampling range, not a calibrated 95% guarantee of skill or rank. Dependence
across weekends and short teammate periods remain limitations.

## 7. What the rating means

This rating describes how much a driver tended to outperform or trail their
actual teammates in the usable qualifying and race-pace observations from
2025, using the stated signal weights. It is relative to the car and opponents
that driver had. It does not isolate absolute driver quality, establish how
they would perform in another car, or make a large margin over one teammate
equivalent to a smaller margin over a stronger teammate. Different setups,
upgrades, damage, strategies, car development and adaptation can affect the
gaps. Its strict and regression race inputs measure related but different
aspects of pace, and the wet evidence is especially sparse. One season cannot
establish stable ability across years. It does not measure points conversion,
reliability, incident responsibility, overtaking, consistency or luck as separate
skills. For predicting future races, build features only from earlier races;
a full-season score must never be used to predict races that helped create it.

## 8. Proposed output shape

One row per driver who appears in the season roster, including partial-season
drivers and drivers with provisional or unavailable scores. Expected roster:
21 drivers. Preserve the source files; the eventual table would be a new
artifact with an explicit method version and source-file provenance.

| Proposed columns | Meaning |
| --- | --- |
| `season`, `driver`, `teams`, `teammates` | Identity and all observed team/teammate assignments |
| `comparison_group`, `teammate_changed`, `season_appearances` | Disconnected comparison group, partner changes and length of participation |
| `qualifying_rating`, `dry_rating`, `wet_rating` | Separate weighted season means in log-percentage points; lower is faster |
| `combined_rating`, `rating_units`, `rating_status` | Overall mean, explicit units and established/provisional/unavailable status |
| `qualifying_weight`, `dry_weight`, `wet_weight` | Actual normalised weights after evidence factors and missing signals |
| `qualifying_valid`, `qualifying_eligible`, `qualifying_effective_races` | Qualifying support and coverage denominator |
| `dry_valid`, `dry_eligible`, `dry_effective_races` | Dry support and coverage denominator |
| `wet_valid`, `wet_eligible`, `wet_effective_races` | Wet support and coverage denominator |
| `races_included` | Count of distinct contributing weekends, not the sum of signal counts |
| `confidence`, `combined_ci_low`, `combined_ci_high`, `bootstrap_valid` | Support label and approximate sampling range, with missing reasons where needed |
| `qualifying_median`, `dry_median`, `wet_median` | Simple sensitivity summaries alongside the weighted means |
| `dry_strict_count`, `dry_linear_count`, `monaco_included` | Composition of the dry evidence |
| `notes`, `method_version`, `source_files` | Missing reasons, brief team/teammate-period breakdown, warnings and reproducibility |

Keep dry and wet component columns separate. Avoid a single ambiguous
`race_pace_rating` that hides their different coverage. Do not require an
absolute-skill rank column; a descriptive sort of eligible scores would need
an explicit label explaining its limited meaning. Precision in a table should
not exceed what the errors support: propose three decimal places for display,
while retaining full precision in any future calculation.

## Open decisions for approval

1. Use symmetric log-percentage contributions with lower better, or retain
   ordinary percentages with exact reciprocal direction handling?
2. Approve the weighted-mean summary and separate teammate-period reporting,
   without an opponent-strength correction or claim of absolute grid ranking?
3. Approve 50% qualifying / 45% dry / 5% wet, with evidence factors reaching
   full weight at eight effective qualifying/dry races and three wet races?
4. Approve the bounded SE weights, equal qualifying weights and proposed
   Monaco dry multiplier of 0.5, or change these reliability choices?
5. Approve available-case scoring, provisional/rank eligibility rules and the
   proposed six-/12-effective-race and 50%/75%-coverage confidence boundaries?
6. Approve the weekend bootstrap, its six-distinct-weekend and 95%-usable-draw
   safeguards, and the proposed table columns and units?
