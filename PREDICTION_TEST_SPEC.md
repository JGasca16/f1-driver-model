# Proposed 2025 teammate finishing-order prediction test

**Proposal only.** This document recommends a test; it does not fit a model,
make predictions, or change any rating or source file. All new choices below
need approval before implementation. The question is whether an earlier-races
driver rating helps predict a teammate result **after this weekend's qualifying
information is already known**.

## Inputs and counts checked

Read DRIVER_RATING_SPEC.md, DRIVER_RATING_METHOD.md, METHOD.md,
data/driver_rating_2025.csv, all 24 data/2025_NN_* race-result CSVs, and
data/2025_qualifying_gaps_combined.csv. The approved method document takes
precedence over the older proposal's suggested weights. METHOD.md describes
fault labels as a project intention; those labels do not exist yet.

There are 240 teammate pair-races, not 480 independent observations. The
qualifying file supplies both driver perspectives and the actual teammates at
each event. It has 233 usable pair gaps. The race files contain 479 driver
results and 239 complete pair outcomes with distinct, positive positions.
Stroll is absent from the Spanish result file, so Alonso/Stroll has no label.
There are 232 pairs with both a recorded outcome and a qualifying gap before
any retirement exclusions or warm-up.

The race CSVs contain only Abbreviation, TeamName, GridPosition and Position.
They cannot identify retirements from Position alone. To count the retirement
options, I also read the already-existing cache/fastf1_http_cache.sqlite in
read-only, immutable mode. Its cached Jolpica responses for
`https://api.jolpi.ca/ergast/f1/2025/{round}/results.json` contain finishing
statuses. All 479 cached positions matched the CSV positions. No network
refresh or cache write was made. These counts describe that saved snapshot;
an eventual implementation must preserve its status provenance explicitly.

The cached statuses are Finished (330 drivers), Lapped (89), Retired (51),
Disqualified (6), and Did not start (3). **Lapped counts as finishing**, not
retiring. The absent Spanish result is a separate missing-result case, not a
retirement inferred from its absence. Six disqualified drivers affect four
pair-races. The 21 season drivers form nine teammate comparison groups; the
full-season rating file is inspected for context only, never used as a
prediction feature.

## 1. Target and retirements

**Recommendation: predict the lower official Position among teammates who both
started, excluding any pair with a disqualification or missing result. Keep
retirements, including double retirements, in this main target.** A retirement
still has an official classification position; that determines who finished
ahead for this outcome. Do not replace a retiree's position with an invented
last place, or infer who caused an incident.

This tests finishing order, which includes reliability, incidents and strategy.
It does not isolate pace or driver fault. Exclude non-starters because a
comparison with someone who never started answers a different question, and
exclude disqualifications because their ordering can be dominated by technical
decisions. Define the prediction time as after qualifying and before the race;
these outcome exclusions are applied later for scoring, never supplied as
features. This is a test conditional on both drivers starting, not a model of
the chance that both will start.

| Outcome handling | All-season usable pair-races | What it measures or risks |
| --- | ---: | --- |
| Use every distinct recorded Position, including non-starters and DQs | 239 | Broad classification order, but technical exclusions and failure to start can decide the answer |
| Both starters, no DQ; retain one or two retirements — recommended main target | 232 | Finishing order including reliability and incidents, with no claim about fault |
| Both starters, no DQ; keep a single retirement but exclude double retirements | 229 | Removes three results largely decided by retirement order |
| Both finish, including lapped finishers | 185 | A cleaner pace-related sensitivity, conditional on surviving the race |
| Keep driver-fault retirements but remove car-fault retirements | Not countable yet | Requires fault classification that the project does not have |

The main target's 232 consist of 185 both-finish pairs, 44 single-retirement
pairs, and three double-retirement pairs. The double retirements are
Hadjar/Lawson in Britain and Hamilton/Leclerc in the Netherlands and São Paulo.
Across the original 240, exclusions are three recorded non-starting pairs,
one missing-result pair, and four DQ pairs; these categories do not overlap.

**Also report the both-finish sensitivity and the no-double-retirement
sensitivity.** Neither becomes the winner after looking at model performance.
Both-finish selection uses something only known after the race and can favour
survivors; its result cannot be presented as unconditional pre-race accuracy.
Do not guess mechanical versus driver responsibility from the word Retired.

## 2. Earlier-races features and the prediction schedule

**Recommendation: require six completed calendar rounds before predicting, plus
at least three earlier valid qualifying comparisons for each current driver.**
The first potential prediction is round 7. This offers a small history without
waiting until most of the season has gone. Three qualifying observations are a
minimum support safeguard, not proof of a reliable rating. Ratings may remain
provisional under the existing rules; do not relax those rules or require a
full-season established label to make them usable here.

Colapinto first appears in round 7 and has no earlier 2025 record. The added
driver-support gate excludes Alpine in rounds 7–9, allowing its first
prediction in round 10. Keep the actual earlier teammates when rebuilding
histories: Lawson/Tsunoda change teams after round 2 and Gasly changes partners
after round 6. Do not manufacture Colapinto history or use his later races.

| Outcome rule | Rounds 7–24, before driver-support gate | After both drivers have 3 prior valid qualifying gaps | Also require current qualifying gap |
| --- | ---: | ---: | ---: |
| Every recorded classification | 179 | 176 | 170 |
| Both starters, no DQ — main | 175 | 172 | 166 |
| Also exclude double retirements | 172 | 169 | 163 |
| Both finish | 142 | 140 | 135 |

These are availability counts, not fitted results. Valid earlier qualifying
history guarantees an available qualifying component; dry and wet history can
still be sparse. For the key comparison, use the same **166** complete cases
for every candidate and baseline, rather than give the rating-only candidate
an easier or larger sample. Report the main target's other six cases without
current qualifying separately as unavailable for that comparison. A prospective
extension could fall back to the rating alone; that is a separate test.

**Rebuilding recommendation:** a future, separate test script would read saved
per-race qualifying, dry and wet observations, cut every input to rounds less
than n, and then call the existing rating script's calculation functions in
memory. The existing scripts would remain unchanged, and their publishing
entry points would not run. Validate that no retained feature source has round
n or later. Recompute the roster history, coverage denominators, weighted
means, effective races and signal weights from that earlier slice, rather than
subtracting the current race from a rounded full-season score.

Preserve method_version `2025_teammate_rating_1_log_round_fix`: qualifying
round percentages become symmetric log-percentage points before combining
Q3 0.50, Q2 0.30 and Q1 0.20, renormalized over available rounds. The saved
combined qualifying gap is already in log units and must not be converted
again. Earlier dry/wet gaps retain their approved log conversion, precision
weights `max(0.25, 1 / (1 + (SE_log / 0.15)^2))`, missing-error handling and
Monaco dry multiplier 0.5. Full-evidence weights stay 0.45 qualifying, 0.45 dry,
0.10 wet, with evidence factors capped at one using eight effective races for
qualifying/dry and three for wet. Keep the approved missing-data and status
rules; a missing wet signal is not a zero gap. No recency adjustment is added.

The test would need earlier rows from data/race_pace_dry_final.csv and
data/race_pace_wet_final.csv as well as the qualifying export. These would be
additional read-only implementation inputs; no race-pace calculation is built
in this proposal.

**Must not be used as features:**

- data/driver_rating_2025.csv or any other full-season score, confidence label,
  median, interval, group assignment or season coverage statistic.
- Qualifying or race-pace observations from later rounds; dry or wet gaps,
  lap times, errors, filters or method choices from the race being predicted.
- That race's finishing positions, finishing statuses, retirements, laps
  completed, points or wins. Finishing positions/statuses are labels or scoring
  exclusions only. Points and wins are not model inputs from any round.
- Future teammate changes, future-derived normalisation, a random train/test
  split, or coefficients calibrated using the outcomes being scored.

This weekend's qualifying gap is allowed **only as its own current-weekend
feature**, available at the stated prediction time. It is not folded into the
prior rating. Historical finishing order is allowed for the proposed result
baselines, using earlier races only. Final historical exports may incorporate
later corrections; check their availability timestamps before claiming a
literal real-time backtest. With the present snapshots, call this a
chronological retrospective test. The rating method itself was developed while
examining 2025, so feature-level leakage safeguards do not make 2025 an untouched
research sample.

## 3. Baselines

**Recommendation: compare against all of these, with the qualifying-only model
below as the predeclared main competitor.**

- **Current qualifying pace:** predict the driver with the lower combined
  qualifying log gap. This is the available Q1/Q2/Q3 pace signal, not necessarily
  the driver with the better official qualifying classification: a weighted
  combination of rounds can disagree with classification order.
- **Starting ahead:** predict the lower GridPosition, using a grid snapshot
  known before the start. This is available in the race files, but must not be
  called qualifying position because grid penalties and pit-lane starts can
  change it. Flag ambiguous or nonpositive grid values rather than interpreting
  them as pole. Actual qualifying-classification order would need another field.
- **Previous-race winner:** use the preceding calendar race only when these
  exact teammates have a usable outcome under the chosen target rule. Otherwise
  abstain or give probability 0.5; do not compare their positions from different
  teams, or silently jump back several races.
- **Head-to-head so far:** for these exact teammates, use earlier wins with
  one added win and one added loss: `(wins + 1) / (comparisons + 2)`. This avoids
  declaring certainty after one race; no previous comparison gives 0.5. Start
  a new pair history when the teammate changes.
- **Chance:** probability 0.5, a useful reference for probability scores.

I expect the current qualifying information to be strongest because it captures
current car/driver form and relates to starting position. That is a hypothesis,
not a measured baseline result. Historical wins also contain reliability and
incident noise.

Hard picks alone do not supply fair probability scores. For the qualifying,
grid and previous-race rules, propose estimating their pick's success probability
from earlier eligible training predictions only, with one added success and one
added failure. Do not assign probability 1 to a hard pick. Keep coverage and
abstentions visible. The head-to-head baseline already supplies its own smoothed
probability. A 0.5 probability is a tie, not a win for the alphabetically first
driver.

## 4. Small candidate set and honest fitting

Use one row per pair-race. Driver A can be the alphabetically first code purely
to label the row; define the outcome as A finishing ahead. All feature directions
must reverse when A and B swap. The alphabet must never become a predictor.

**Recommended candidates:**

1. **Earlier rating only:** a logistic regression using B's prior combined
   rating minus A's. A positive value favours A because lower ratings mean
   faster. This asks whether prior teammate-relative outperformance predicts
   results. The difference is a predictor, not a physical predicted pace gap;
   these ratings are not calibrated latent abilities.
2. **Current qualifying only:** a logistic regression using the negative of A's
   current combined qualifying log gap. This calibrates qualifying information
   to a probability and is the main comparator.
3. **Both:** the same logistic model with both inputs. Its improvement over
   qualifying only is the central incremental-value test.

Use the same rows, coefficient-fitting schedule and regularisation for all
three. Recommend no intercept so swapping drivers makes the probability its
exact complement. Keep the inputs in their existing log units, with no
full-season scaling, driver identity terms, team identifiers, interactions or
track-specific coefficients. Propose a fixed L2 penalty, such as C=1, approved
before fitting rather than selected for a favourable 2025 result. A learned
rating coefficient could be weak or reverse direction; report that rather than
forcing a preferred answer.

**Recommended scoring schedule:** rounds 1–6 establish feature history. Rounds
7–12 supply initial coefficient training. Score rounds 13–24, predicting the
whole weekend before adding any outcomes from it. Before each later weekend,
refit on eligible earlier training examples only. Historical training rows must
retain the feature values built before their own races; never recompute them
with knowledge available at the later fitting date. Any probability calibration
must obey the same time cutoff. This follows the reasoning behind chronological
validation in the [scikit-learn time-series documentation](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html).

For the recommended target and complete-case gates, that means **53 training
pair-races in rounds 7–12 and 113 scored pair-races across 12 later weekends**.
The broader 166-case availability count is not 166 out-of-sample predictions
under this schedule. The both-finish sensitivity has 40 training and 95 scored
cases; excluding only double retirements gives 52 training and 111 scored cases.
These are small samples even for two coefficients. If training cannot support a
fit, report it and use the predeclared baseline fallback; do not move the start
round after seeing accuracy.

## 5. Metrics, uncertainty and realistic resolution

**Recommendation: make Brier score the primary probability metric, with accuracy
and log loss alongside it.** Brier score is the average squared difference
between predicted probability and the 0/1 outcome; lower is better and it avoids
the especially large penalties log loss gives overconfident mistakes. Log loss
remains useful for revealing those mistakes. These are proper probability
scores, as described in the [scikit-learn evaluation documentation](https://scikit-learn.org/stable/modules/model_evaluation.html).

For accuracy, pick A above probability 0.5 and B below it; give exact ties half
credit and report their count. For numerical log-loss evaluation only, propose
clipping probabilities to [0.000001, 0.999999]. Do not tune thresholds to improve
accuracy. Report pair count, weekend count, exclusions and a per-weekend summary
next to every score. Give the main target and the two retirement sensitivities
separate results, not a pooled score.

**Paired uncertainty recommendation: 2,000 whole-weekend bootstrap resamples,
seed 42, with 2.5th/97.5th percentiles.** Resample the 12 scored weekends with
replacement. Carry all pair outcomes and every method's stored, earlier-only
predictions together. Calculate each candidate-minus-baseline metric difference
on the same resample. Never bootstrap driver rows independently, count the two
teammate perspectives twice, or shuffle time to refit a forecasting model.
This is uncertainty conditional on the fitted prediction path; it does not
capture every source of model-fitting uncertainty.

Predeclare qualifying-only as the primary comparison. Also report comparisons
with every simple baseline and the one with the best observed score. The latter
is selected after observing results: call its interval exploratory rather than
treating it as a clean, preselected significance test. Report accuracy and Brier
winners separately if they differ. Do not search across models, targets or
warm-up settings and publish only the favourable comparison.

**Do not over-read a few percentage points.** There are at most 113 main scored
pairs under this plan; one different correct prediction changes accuracy by
about 0.885 percentage points. As a planning illustration, suppose two methods
disagree on 20% of cases. Treating pairs as independent would give a paired
accuracy-difference standard error of roughly `sqrt(0.20 / 113)`, or 4.2 pp,
and a 95% half-width around 8.2 pp. A conventional two-sided 5% test with about
80% power would need roughly **11.8 pp** improvement in that illustration.
If disagreement is 10%–30%, the corresponding rough detectable difference is
**8.3–14.4 pp**. These calculations assume a near-zero difference and are planning
approximations, not a measured power result or a promise about the eventual CI.

Even scoring all 166 available complete cases with a separately approved fitting
plan would only reduce that illustrative 20%-disagreement figure to about
9.7 pp. Dependence within weekends and persistent teammate pairs can make the
effective information smaller. Only 12 scored weekends and about nine teammate
groups underpin the main result. Weekend resampling does not remove persistent
group dependence; also show whether the conclusion survives leaving out each
comparison group from the scored summary. That is a stability diagnostic, not
nine new independent validations. A 1–3 pp advantage would generally be weak
evidence here, while a Brier improvement without an accuracy gain may still
indicate useful probability information.

## 6. Interpreting the result

**Positive result:** if adding the prior rating improves genuinely earlier-only
predictions over qualifying alone, with a useful effect size, uncertainty and
reasonable group stability, that supports incremental predictive information
for these 2025 teammate outcomes. It does not establish absolute driver skill,
causal effects, a common ranking across disconnected groups, or performance in
another car or season. Report whether the benefit depends on retirement cases,
one dominant pairing, provisional histories, or the chosen warm-up.

**Negative or unclear result:** the test would not show enough additional value
under these choices. It would not prove that driver ability is irrelevant or
that the descriptive rating is useless. Qualifying may already contain much of
the same information; noisy retirement outcomes, sparse early histories, changing
teammates and the small sample can hide a real but modest benefit. A wide range
including both improvement and harm means inconclusive, not equivalence.

The method was designed on this season and the grid has only about nine
independent teammate groups. Repeat a frozen specification on a later season
before claiming general predictive validation. No performance numbers have been
calculated in this proposal.

## 7. What a grid-wide prediction would need

**Recommendation: keep this test within actual teammate pairs first.** They
share a team/car baseline at that event, so a grid-wide estimate of team
strength is unnecessary for this limited comparison. Upgrades, setups, damage
and strategies can still differ within the team.

To predict finishing order across the grid, a future model would need a common
team/car performance baseline estimated from earlier races, plus current
qualifying or starting-grid information, and a way to represent reliability,
incidents and race conditions. Separating driver strength from car strength
would require stronger assumptions and ideally multiple seasons and driver
moves; one season's disconnected teammate groups cannot identify that split
on their own. A full-order or position model would also need coherent joint
predictions, so several independent pair predictions cannot all claim the same
finishing position. None of that is built or assumed by this teammate test.

## Open decisions for approval

1. Use all starters without DQs as the main target (232 season pairs), with
   both-finish and no-double-retirement sensitivities, or change the target?
2. Approve six earlier calendar rounds and three earlier valid qualifying
   comparisons per driver, allowing provisional prior ratings?
3. Approve rounds 7–12 for initial fitting and rounds 13–24 for expanding-window
   scoring: 113 main complete-case predictions, rather than using all 166 as
   though they were an untouched test set?
4. Approve qualifying-only as the primary comparator, the listed simple
   baselines, and the three no-intercept logistic candidates with fixed C=1?
5. Approve complete-case comparisons, the proposed probability smoothing,
   half-credit ties, and the stated log-loss clipping values?
6. Approve primary Brier score, secondary accuracy/log loss, 2,000 paired
   weekend bootstrap draws with seed 42, and separate retirement/group
   sensitivities, treating the 2025 result as exploratory?
