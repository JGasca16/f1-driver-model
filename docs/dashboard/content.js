/* Owner-approved copy. Each block records its supporting document and section. */
(function (root) {
  const blocks = {
  "intro": [
    "DASHBOARD_SPEC.md",
    "1. Audience and the first screen",
    "I compared every 2025 driver with their own teammate using qualifying, dry race pace and wet race pace. Then I tested whether those ratings help predict which teammate finishes ahead, once you already know that weekend's qualifying."
  ],
  "scope": [
    "DASHBOARD_SPEC.md",
    "1. Audience and the first screen",
    "This covers one season. Drivers are only compared with their own teammate, so there is no ranking across teams."
  ],
  "examples": [
    "DASHBOARD_SPEC.md",
    "1. Audience and the first screen",
    "One pair with a clear gap and one without. They are examples, not rankings."
  ],
  "exampleCaption": [
    "DASHBOARD_SPEC.md",
    "1. Audience and the first screen",
    "Negative means faster than the teammate. The dot is the rating and the bar is the 95% range."
  ],
  "prediction": [
    "DASHBOARD_SPEC.md",
    "4. Present the prediction test honestly",
    "Adding the ratings to this weekend's qualifying made the predictions a little better, but the 95% range still includes zero. I can't say the ratings really help."
  ],
  "lower": [
    "DASHBOARD_SPEC.md",
    "4. Present the prediction test honestly",
    "Lower is better, so negative means the ratings helped."
  ],
  "counts": [
    "DASHBOARD_SPEC.md",
    "4. Present the prediction test honestly",
    "{pairs} teammate races from {weekends} race weekends, {excluded} left out."
  ],
  "condition": [
    "DASHBOARD_SPEC.md",
    "4. Present the prediction test honestly",
    "Only races where both teammates finished are counted."
  ],
  "question": [
    "DASHBOARD_SPEC.md",
    "4. Present the prediction test honestly",
    "Once you know this weekend's qualifying, do ratings built from earlier races help predict which teammate finishes ahead?"
  ],
  "models": [
    "DASHBOARD_SPEC.md",
    "4. Present the prediction test honestly",
    "Qualifying only (M2) uses this weekend's qualifying. Qualifying plus ratings (M3) adds the rating from earlier races."
  ],
  "reading": [
    "DASHBOARD_SPEC.md",
    "4. Present the prediction test honestly",
    "Accuracy went from {m2_acc} to {m3_acc} and Brier score improved by {brier_gain}. Every 95% range for the differences includes zero, so this could be chance."
  ],
  "leftOut": [
    "DASHBOARD_SPEC.md",
    "4. Present the prediction test honestly",
    "{excluded} pairs were left out: {n1} had a retirement, {n2} had no usable qualifying gap, {n3} did not start and {n4} was disqualified."
  ],
  "conditional": [
    "DASHBOARD_SPEC.md",
    "4. Present the prediction test honestly",
    "Only races where both teammates finished are counted, so this is not the accuracy you would get before a race."
  ],
  "uncertainty": [
    "DASHBOARD_SPEC.md",
    "4. Present the prediction test honestly",
    "This is one season and about nine teammate groups, so the {pairs} races are not {pairs} independent tests."
  ],
  "brier": [
    "DASHBOARD_SPEC.md",
    "4. Present the prediction test honestly",
    "Brier score measures how far the predicted probabilities were from what happened. Accuracy only counts right or wrong picks and ignores how confident each pick was."
  ],
  "how": [
    "PREDICTION_TEST_METHOD.md",
    "Rating rebuild and leakage safeguards",
    "For each race from round 13 to 24, I rebuild every rating using only earlier rounds, then predict which teammate finishes ahead. Rounds 5 to 12 are used to train the model."
  ],
  "bootstrap": [
    "PREDICTION_TEST_METHOD.md",
    "Metrics and paired uncertainty",
    "To see how much the results could change, I resampled whole race weekends 2,000 times (seed 42) and used the 2.5th and 97.5th percentiles."
  ],
  "stability": [
    "PREDICTION_TEST_METHOD.md",
    "Leave-one-teammate-group-out stability",
    "I dropped each teammate group in turn and rescored. These checks reuse the same races, so they are not nine separate tests. No uncertainty ranges were saved for them."
  ],
  "driverIntro": [
    "DASHBOARD_SPEC.md",
    "3. Sign, uncertainty and ordering rules",
    "Pick a teammate group to see how each driver did against their teammate."
  ],
  "sign": [
    "DASHBOARD_SPEC.md",
    "3. Sign, uncertainty and ordering rules",
    "Negative means faster than the teammate, positive means slower. Numbers are log-percentage points, about 1% of lap time each."
  ],
  "caution": [
    "DASHBOARD_SPEC.md",
    "3. Sign, uncertainty and ordering rules",
    "Ratings in this group mix different teammates, and I did not adjust for how strong each teammate was. Do not subtract two drivers' ratings to get a head-to-head gap."
  ],
  "provisional": [
    "DASHBOARD_SPEC.md",
    "3. Sign, uncertainty and ordering rules",
    "Provisional: only {valid} usable dry race out of {eligible}."
  ],
  "combined": [
    "DASHBOARD_SPEC.md",
    "3. Sign, uncertainty and ordering rules",
    "Combined rating {combined}. 95% range {lo} to {hi}."
  ],
  "noClear": [
    "DASHBOARD_SPEC.md",
    "3. Sign, uncertainty and ordering rules",
    "That range includes zero, so there is no clear gap."
  ],
  "confidenceHelp": [
    "DRIVER_RATING_METHOD.md",
    "Fixed choices",
    "Confidence is about how much data there is, not how big the gap is."
  ],
  "missing": [
    "DRIVER_RATING_METHOD.md",
    "Eligibility and teammate periods",
    "Missing data stays blank. It is never counted as zero."
  ],
  "coverage": [
    "DRIVER_RATING_METHOD.md",
    "Files and running",
    "Coverage is the share of eligible races that had a usable gap."
  ],
  "periods": [
    "DRIVER_RATING_METHOD.md",
    "Eligibility and teammate periods",
    "If a driver changed seats, each stretch is shown on its own. The season rating pools all their races, so a short stretch counts for less than a long one. There is no combined rating for a single stretch."
  ],
  "methodIntro": [
    "DRIVER_RATING_METHOD.md",
    "Known limitations",
    "A rating compares a driver with the teammate in the same car. That is all it measures."
  ],
  "meaning": [
    "DASHBOARD_SPEC.md",
    "3. Sign, uncertainty and ordering rules",
    "A negative number means the driver was faster than their teammate, and positive means slower. The units are log-percentage points, close to a percent of lap time for small gaps. Ratings only compare teammates, so there is no ranking across teams."
  ],
  "qualifyingMethod": [
    "README.md",
    "Method in one screen",
    "I compare each qualifying round and blend them, with Q3 counting most (50%, 30% and 20% for Q3, Q2 and Q1)."
  ],
  "dryMethod": [
    "README.md",
    "Method in one screen",
    "I match laps on the same tyre compound and similar tyre age, so it compares like with like. Where there are not enough matched laps, a regression that adjusts for tyre age and lap number fills in."
  ],
  "wetMethod": [
    "README.md",
    "Method in one screen",
    "Only laps on the same tyres, with a clear gap to the car ahead (at least 1.5 seconds) and steady weather, count."
  ],
  "ratingMethod": [
    "README.md",
    "Method in one screen",
    "The combined rating blends them: 45% qualifying, 45% dry and 10% wet, scaled down when a signal has little data."
  ],
  "sure": [
    "DRIVER_RATING_METHOD.md",
    "Fixed choices",
    "Each rating has a 95% range. When the range includes zero, the page says No clear gap. Status and confidence describe how much data a driver has, not how big the gap is. Missing data stays blank and is never counted as zero."
  ],
  "dryCoverage": [
    "METHOD_DRY_RACEPACE.md",
    "Known limitations",
    "Of {dry_pairs} dry-race pairs, {dry_blank} have no gap. The main reasons: the model could not separate the effects, the teammates did not share enough clean laps on one compound, a driver had no usable laps, or a driver was disqualified."
  ],
  "wetCoverage": [
    "METHOD_WET_RACEPACE.md",
    "Known limitations",
    "Only {wet_gap} of {wet_eligible} eligible wet pairs got a gap, and {wet_high} is high confidence. The weather check removed laps mainly because too few other drivers had clean laps to compare against, not because it measured the weather changing."
  ],
  "miami": [
    "METHOD_DRY_RACEPACE.md",
    "Inputs and dry classification",
    "Miami counts for qualifying only. Its tyre records did not match the pit stops, so I left out its race pace."
  ],
  "monaco": [
    "DRIVER_RATING_METHOD.md",
    "Fixed choices",
    "Overtaking is so hard at Monaco that lap times depend on the car ahead. Its gaps are kept, flagged, and count half."
  ],
  "fault": [
    "PREDICTION_TEST_METHOD.md",
    "Target, orientation and history",
    "I did not label retirements as driver or car fault."
  ],
  "limits": [
    "DRIVER_RATING_METHOD.md",
    "Known limitations",
    "It is one season. Cars, setups, upgrades, damage and strategy all move a gap, so a rating shows how a driver did against their teammate, not how good they are overall. A season rating does not predict any single race."
  ]
};
  const exact = {
  "intro": [
    "DASHBOARD_SPEC.md",
    "1. Audience and the first screen",
    "How did drivers perform relative to their actual teammates, and did earlier ratings add information beyond the next race weekend's qualifying?"
  ],
  "scope": [
    "DASHBOARD_SPEC.md",
    "1. Audience and the first screen",
    "One season. Nine separate teammate groups. No cross-team ranking."
  ],
  "sign": [
    "DASHBOARD_SPEC.md",
    "3. Sign, uncertainty and ordering rules",
    "Negative = faster than the actual teammate(s); positive = slower. Season ratings use log-percentage points and the teammate history shown."
  ],
  "relative": [
    "README.md",
    "What this project is",
    "It is a retrospective test of one season, not a cross-team driver ranking."
  ],
  "caution": [
    "DASHBOARD_SPEC.md",
    "3. Sign, uncertainty and ordering rules",
    "These ratings pool different teammate periods without adjusting for opponent strength. Do not subtract two season ratings to estimate a head-to-head gap."
  ],
  "provisional": [
    "DASHBOARD_SPEC.md",
    "2. Pages and their saved fields",
    "Provisional: only 1 usable dry race out of 4 eligible dry appearances."
  ],
  "prediction": [
    "DASHBOARD_SPEC.md",
    "4. Present the prediction test honestly",
    "The point estimates favour adding the earlier rating, but every primary difference interval includes zero. This test does not establish an improvement."
  ],
  "condition": [
    "DASHBOARD_SPEC.md",
    "4. Present the prediction test honestly",
    "Conditional on both finishing; not unconditional pre-race accuracy."
  ],
  "uncertainty": [
    "DASHBOARD_SPEC.md",
    "4. Present the prediction test honestly",
    "This is one exploratory season with roughly nine teammate groups, not 95 independent driver-skill experiments."
  ],
  "bootstrap": [
    "PREDICTION_TEST_METHOD.md",
    "Metrics and paired uncertainty",
    "There are 2,000 whole-scored-weekend resamples, seed 42. Each draw carries all pair outcomes and all methods together; every candidate-minus-baseline comparison uses identical draws. Intervals are the 2.5th and 97.5th percentiles. Rows and teammate directions are never independently resampled; models are not refit on a shuffled or bootstrapped chronology."
  ],
  "brier": [
    "DASHBOARD_SPEC.md",
    "4. Present the prediction test honestly",
    "accuracy alone discards probability quality."
  ],
  "baseline": [
    "DASHBOARD_SPEC.md",
    "4. Present the prediction test honestly",
    "Best observed baseline selection is exploratory, not the primary M3/M2 comparison."
  ],
  "qualifyingPick": [
    "PREDICTION_TEST_METHOD.md",
    "Baseline rules",
    "Qualifying pace and starting grid are distinct: weighted round pace is not official qualifying position."
  ],
  "stability": [
    "PREDICTION_TEST_METHOD.md",
    "Leave-one-teammate-group-out stability",
    "Omit each group from the scored summary only; do not refit or remove its earlier training history. The full-season group mapping is used only here, after predictions are fixed. These are correlated checks, not nine independent tests."
  ],
  "overlap": [
    "DASHBOARD_SPEC.md",
    "4. Present the prediction test honestly",
    "Multiple `all_reasons` may overlap; do not sum them as disjoint counts."
  ],
  "audit": [
    "DASHBOARD_SPEC.md",
    "4. Present the prediction test honestly",
    "The last table is an audit, not a live prediction tool."
  ],
  "auditDirection": [
    "DASHBOARD_SPEC.md",
    "4. Present the prediction test honestly",
    "The saved feature differences use positive values to favour A; that differs from the negative-is-faster rating display"
  ],
  "auditHistory": [
    "DASHBOARD_SPEC.md",
    "4. Present the prediction test honestly",
    "Historical outcomes and statuses are audit fields, not evidence of model inputs."
  ],
  "missing": [
    "DRIVER_RATING_METHOD.md",
    "Eligibility and teammate periods",
    "Blanks never become zero or a pace penalty."
  ],
  "fractions": [
    "DRIVER_RATING_METHOD.md",
    "Files and running",
    "Coverage is a fraction, not a percentage; normalized signal weights are fractions too."
  ],
  "periods": [
    "DRIVER_RATING_METHOD.md",
    "Eligibility and teammate periods",
    "Pool individual race observations normally across periods. Also export weighted signal means and medians per driver/team/teammate period. Short periods do not get equal weight to long periods."
  ],
  "noPeriodInterval": [
    "DASHBOARD_SPEC.md",
    "2. Pages and their saved fields",
    "There is no saved combined period rating or period confidence interval; do not create one."
  ],
  "singleWet": [
    "DRIVER_RATING_METHOD.md",
    "Completed run and checks",
    "Every driver with wet evidence has exactly one usable wet race: 12 drivers have a single-race interval, and none has a usable wet season interval."
  ],
  "qualifyingMethod": [
    "README.md",
    "Method in one screen",
    "Convert each available round gap to symmetric log-percentage points, then combine Q3, Q2 and Q1 with weights **0.50 / 0.30 / 0.20**, renormalized over the rounds with valid times."
  ],
  "dryMethod": [
    "README.md",
    "Method in one screen",
    "Use a strict median gap from matched clean laps when available, then a linear regression on clean laps as the fallback. Report uncertainty using moving-block bootstrap errors."
  ],
  "wetMethod": [
    "README.md",
    "Method in one screen",
    "Match clean laps at the same lap number and tyre compound; require a start-of-lap traffic gap of at least **1.5 seconds** and apply the field-median weather-change check."
  ],
  "ratingMethod": [
    "README.md",
    "Method in one screen",
    "Start with **45% qualifying, 45% dry pace, 10% wet pace** when fully supported; reduce each signal's weight according to its evidence factor, then renormalize."
  ],
  "settings": [
    "README.md",
    "Method in one screen",
    "These are method settings, not fitted findings."
  ],
  "precision": [
    "DRIVER_RATING_METHOD.md",
    "Fixed choices",
    "Each qualifying race has weight 1. Dry and wet use `max(0.25, 1 / (1 + (SE_log/0.15)^2))`. An absent/invalid error uses 0.25 and a warning. Zero errors get a review warning. Monaco's dry observation weight is multiplied by 0.5; its gap is unchanged. Other signals and tracks receive no track multiplier."
  ],
  "evidence": [
    "DRIVER_RATING_METHOD.md",
    "Fixed choices",
    "Effective races: `(sum(weights)^2) / sum(weights^2)`. Signal evidence factors are `min(1, effective_races/8)` for qualifying/dry and `min(1, effective_races/3)` for wet. Multiply 0.45/0.45/0.10 by these factors and normalize. Wet alone cannot produce an overall score."
  ],
  "status": [
    "DRIVER_RATING_METHOD.md",
    "Fixed choices",
    "Formal status `established` requires qualifying and dry each to have at least 6 effective races and 50% coverage. Otherwise an available score is `provisional`; without qualifying or dry it is `unavailable`."
  ],
  "confidence": [
    "DRIVER_RATING_METHOD.md",
    "Fixed choices",
    "Confidence `high` requires qualifying and dry each to have at least 12 effective races and 75% coverage, plus a usable combined interval. `medium` requires 6 effective races and 50% coverage for both, plus that interval. Other available scores are `low/provisional`; absent scores `unavailable`."
  ],
  "leakage": [
    "PREDICTION_TEST_METHOD.md",
    "Rating rebuild and leakage safeguards",
    "For a feature round n, all four rating input tables are cut to rounds strictly less than n **before** calculating anything."
  ],
  "selection": [
    "PREDICTION_TEST_METHOD.md",
    "Target, orientation and history",
    "The main target conditions on surviving the race, something known only after it happens. Its accuracy is conditional on both drivers finishing and must not be read as unconditional pre-race accuracy."
  ],
  "generalLimits": [
    "DRIVER_RATING_METHOD.md",
    "Known limitations",
    "These are 2025 performances relative to actual teammates and cars. Different opponents, setups, upgrades, damage and strategies can change a score. Connected groups still lack a common cross-team ability baseline. Subtracting two scores does not predict their head-to-head gap. One season cannot establish lasting driver quality."
  ],
  "ratingLimits": [
    "DRIVER_RATING_METHOD.md",
    "Known limitations",
    "The weekend bootstrap measures variation in observed weekends, conditional on these sources and choices. It does not correct selection bias, opponent strength, correlation across weekends or unseen wet conditions. Missing races may systematically be difficult ones. A narrow interval is not a calibrated guarantee about skill. Full-season ratings must not be used to predict races that contributed to them."
  ],
  "dryCoverage": [
    "METHOD_DRY_RACEPACE.md",
    "Known limitations",
    "Of the 200 dry-race pairs, 32 have no gap: 10 because the model cannot separate the requested effects (`effects_not_identifiable`), 9 because the teammates lack enough clean laps on a shared compound (`strategy_confounded`), 9 because at least one driver has no non-generated race-lap records (`no_race_laps`), and 4 because of a race disqualification (`race_disqualification`). These blanks are missing evidence, not zero gaps or proof that the drivers were equally fast."
  ],
  "strictFirst": [
    "METHOD_DRY_RACEPACE.md",
    "Known limitations",
    "An eligible strict matched-lap gap is always used first, even if the linear regression has a smaller standard error. When there are fewer than ten matched laps, an accepted regression supplies the gap instead."
  ],
  "regression": [
    "METHOD_DRY_RACEPACE.md",
    "Known limitations",
    "It assumes that one driver's adjusted advantage stays constant and that tyre-age and lap-number effects follow roughly straight lines shared by both teammates. Real tyre degradation, fuel effects and driver performance can change shape or differ between drivers."
  ],
  "monaco": [
    "METHOD_DRY_RACEPACE.md",
    "Known limitations",
    "Limited overtaking can make a driver's lap times depend heavily on the car ahead and track position. Monaco therefore carries the `low_overtaking_limited` flag, but its gap is still reported."
  ],
  "wetCoverage": [
    "METHOD_WET_RACEPACE.md",
    "Known limitations",
    "Only 6 of the 30 eligible teammate pairs have a primary wet gap, and only 1 is labelled high confidence. The available numbers describe a small, selected set of race portions and drivers."
  ],
  "wetWeather": [
    "METHOD_WET_RACEPACE.md",
    "Known limitations",
    "At the official eight-driver minimum, all 137 driver-laps removed by this check after traffic filtering fail because at least one of the previous, current or following lap numbers has too few clean reference drivers. None is rejected for a measured median change above 2%."
  ],
  "wetTraffic": [
    "METHOD_WET_RACEPACE.md",
    "Known limitations",
    "The fixed 1.5-second rule removes 355 eligible pair-laps, compared with 21 removed by the primary weather check after traffic. Other traffic thresholds were not tested."
  ],
  "miami": [
    "README.md",
    "Known limitations",
    "Miami contributes qualifying but no dry or wet race-pace gap."
  ],
  "year": [
    "METHOD_DRY_RACEPACE.md",
    "Known limitations",
    "Car development, upgrades and how well each driver adapts to them can change the teammate gap through the season. A change in the numbers need not mean a change in driver skill."
  ],
  "sparse": [
    "METHOD_WET_RACEPACE.md",
    "Known limitations",
    "These six retained gaps may sample only a driver's more comparable race portions, so they should not be treated as representative of that driver's typical wet performance or full wet skill."
  ]
};
  root.DashboardCopy = Object.freeze(blocks);
  root.DashboardExact = Object.freeze(exact);
})(globalThis);
