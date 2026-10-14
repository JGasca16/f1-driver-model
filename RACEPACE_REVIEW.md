# Race-pace coverage review and regression proposal

2025 cached FastF1 data; offline analysis. No existing CSV, Python file, or documentation was changed. Regression is a proposal only; no regression has been fitted.

## The 88 pairs below the matching threshold

Source: `data/2025_race_pace_teammate_gaps.csv`, default tyre-age tolerance 3, minimum 10 matched laps. One row per race/team pair, alphabetically oriented. Clean counts below are individual retained laps; shared counts require the same lap number.

76 pairs have zero matched laps. The other counts are: 4 laps (2 pairs), 5 (1), 6 (3), 7 (3), 8 (1), 9 (2). There are no pairs with 1–3 matched laps.

Among the 76 zero-match pairs: 5 have no shared clean lap numbers; 8 have shared clean laps but no shared same-compound laps; 63 have same-compound shared laps but none within the tyre-age tolerance. Of all 88 blocked pairs, 80 have at least 10 individual clean laps for each driver; 8 do not. These counts motivate regression, but do not establish that it can identify a reliable gap for those 80 pairs.

| Round | Race | Team | Driver / teammate | Matched laps | Individual clean laps, same order | Shared clean laps | Shared same-compound laps |
| ---: | --- | --- | --- | ---: | --- | ---: | ---: |
| 2 | Chinese Grand Prix | Aston Martin | ALO / STR | 0 | 0 / 49 | 0 | 0 |
| 2 | Chinese Grand Prix | Haas F1 Team | BEA / OCO | 0 | 49 / 49 | 46 | 12 |
| 2 | Chinese Grand Prix | Kick Sauber | BOR / HUL | 0 | 48 / 48 | 45 | 30 |
| 2 | Chinese Grand Prix | Red Bull Racing | LAW / VER | 0 | 46 / 50 | 43 | 26 |
| 3 | Japanese Grand Prix | Alpine | DOO / GAS | 0 | 49 / 48 | 45 | 26 |
| 3 | Japanese Grand Prix | Aston Martin | ALO / STR | 0 | 49 / 45 | 42 | 3 |
| 3 | Japanese Grand Prix | Ferrari | HAM / LEC | 0 | 49 / 49 | 46 | 6 |
| 3 | Japanese Grand Prix | Haas F1 Team | BEA / OCO | 0 | 49 / 49 | 46 | 6 |
| 3 | Japanese Grand Prix | Kick Sauber | BOR / HUL | 0 | 49 / 49 | 46 | 6 |
| 4 | Bahrain Grand Prix | Haas F1 Team | BEA / OCO | 6 | 46 / 45 | 40 | 8 |
| 4 | Bahrain Grand Prix | Racing Bulls | HAD / LAW | 0 | 43 / 47 | 39 | 5 |
| 4 | Bahrain Grand Prix | Red Bull Racing | TSU / VER | 7 | 45 / 42 | 38 | 10 |
| 5 | Saudi Arabian Grand Prix | Aston Martin | ALO / STR | 0 | 42 / 41 | 37 | 16 |
| 5 | Saudi Arabian Grand Prix | Haas F1 Team | BEA / OCO | 0 | 43 / 46 | 43 | 30 |
| 5 | Saudi Arabian Grand Prix | McLaren | NOR / PIA | 0 | 42 / 43 | 39 | 11 |
| 5 | Saudi Arabian Grand Prix | Racing Bulls | HAD / LAW | 0 | 41 / 41 | 37 | 9 |
| 5 | Saudi Arabian Grand Prix | Red Bull Racing | TSU / VER | 0 | 0 / 43 | 0 | 0 |
| 7 | Emilia Romagna Grand Prix | Alpine | COL / GAS | 5 | 45 / 43 | 40 | 30 |
| 7 | Emilia Romagna Grand Prix | Ferrari | HAM / LEC | 0 | 48 / 45 | 45 | 25 |
| 7 | Emilia Romagna Grand Prix | Kick Sauber | BOR / HUL | 0 | 45 / 47 | 44 | 22 |
| 7 | Emilia Romagna Grand Prix | Mercedes | ANT / RUS | 0 | 39 / 45 | 35 | 14 |
| 7 | Emilia Romagna Grand Prix | Red Bull Racing | TSU / VER | 0 | 47 / 49 | 46 | 0 |
| 8 | Monaco Grand Prix | Alpine | COL / GAS | 0 | 60 / 2 | 2 | 0 |
| 8 | Monaco Grand Prix | Ferrari | HAM / LEC | 0 | 61 / 61 | 54 | 42 |
| 8 | Monaco Grand Prix | Haas F1 Team | BEA / OCO | 0 | 61 / 61 | 57 | 8 |
| 8 | Monaco Grand Prix | Kick Sauber | BOR / HUL | 0 | 61 / 58 | 53 | 11 |
| 8 | Monaco Grand Prix | Racing Bulls | HAD / LAW | 4 | 61 / 61 | 55 | 39 |
| 8 | Monaco Grand Prix | Williams | ALB / SAI | 0 | 60 / 60 | 54 | 5 |
| 9 | Spanish Grand Prix | Haas F1 Team | BEA / OCO | 6 | 49 / 51 | 43 | 29 |
| 9 | Spanish Grand Prix | Kick Sauber | BOR / HUL | 7 | 51 / 51 | 45 | 37 |
| 9 | Spanish Grand Prix | Red Bull Racing | TSU / VER | 4 | 47 / 49 | 38 | 16 |
| 10 | Canadian Grand Prix | Alpine | COL / GAS | 0 | 59 / 57 | 54 | 34 |
| 10 | Canadian Grand Prix | Aston Martin | ALO / STR | 0 | 57 / 56 | 52 | 28 |
| 10 | Canadian Grand Prix | Ferrari | HAM / LEC | 0 | 57 / 55 | 49 | 27 |
| 10 | Canadian Grand Prix | Haas F1 Team | BEA / OCO | 0 | 56 / 59 | 53 | 32 |
| 10 | Canadian Grand Prix | Kick Sauber | BOR / HUL | 0 | 59 / 60 | 56 | 26 |
| 10 | Canadian Grand Prix | Racing Bulls | HAD / LAW | 0 | 57 / 46 | 42 | 22 |
| 10 | Canadian Grand Prix | Red Bull Racing | TSU / VER | 0 | 59 / 57 | 52 | 36 |
| 10 | Canadian Grand Prix | Williams | ALB / SAI | 0 | 42 / 58 | 42 | 21 |
| 11 | Austrian Grand Prix | Alpine | COL / GAS | 7 | 57 / 58 | 55 | 7 |
| 11 | Austrian Grand Prix | Haas F1 Team | BEA / OCO | 0 | 57 / 57 | 50 | 14 |
| 11 | Austrian Grand Prix | Kick Sauber | BOR / HUL | 0 | 58 / 58 | 52 | 27 |
| 14 | Hungarian Grand Prix | Alpine | COL / GAS | 0 | 60 / 63 | 55 | 15 |
| 14 | Hungarian Grand Prix | Ferrari | HAM / LEC | 0 | 64 / 63 | 59 | 17 |
| 14 | Hungarian Grand Prix | Kick Sauber | BOR / HUL | 0 | 66 / 59 | 58 | 31 |
| 15 | Dutch Grand Prix | Alpine | COL / GAS | 0 | 45 / 49 | 44 | 19 |
| 15 | Dutch Grand Prix | Aston Martin | ALO / STR | 6 | 43 / 46 | 40 | 33 |
| 16 | Italian Grand Prix | Alpine | COL / GAS | 0 | 44 / 43 | 39 | 12 |
| 16 | Italian Grand Prix | Aston Martin | ALO / STR | 0 | 19 / 46 | 18 | 1 |
| 16 | Italian Grand Prix | Haas F1 Team | BEA / OCO | 0 | 48 / 48 | 45 | 29 |
| 16 | Italian Grand Prix | Racing Bulls | HAD / LAW | 0 | 46 / 47 | 42 | 19 |
| 16 | Italian Grand Prix | Williams | ALB / SAI | 0 | 47 / 46 | 42 | 7 |
| 17 | Azerbaijan Grand Prix | Alpine | COL / GAS | 0 | 41 / 39 | 38 | 16 |
| 17 | Azerbaijan Grand Prix | Ferrari | HAM / LEC | 0 | 40 / 40 | 37 | 14 |
| 17 | Azerbaijan Grand Prix | Mercedes | ANT / RUS | 0 | 41 / 39 | 38 | 18 |
| 17 | Azerbaijan Grand Prix | Williams | ALB / SAI | 0 | 41 / 39 | 37 | 30 |
| 18 | Singapore Grand Prix | Alpine | COL / GAS | 0 | 53 / 50 | 45 | 7 |
| 18 | Singapore Grand Prix | Racing Bulls | HAD / LAW | 0 | 55 / 55 | 52 | 0 |
| 19 | United States Grand Prix | Aston Martin | ALO / STR | 0 | 46 / 46 | 43 | 0 |
| 19 | United States Grand Prix | Ferrari | HAM / LEC | 0 | 42 / 45 | 39 | 6 |
| 19 | United States Grand Prix | Haas F1 Team | BEA / OCO | 0 | 46 / 46 | 42 | 3 |
| 19 | United States Grand Prix | Kick Sauber | BOR / HUL | 0 | 40 / 48 | 39 | 32 |
| 19 | United States Grand Prix | Williams | ALB / SAI | 0 | 45 / 4 | 4 | 0 |
| 20 | Mexico City Grand Prix | Alpine | COL / GAS | 0 | 61 / 61 | 58 | 17 |
| 20 | Mexico City Grand Prix | Kick Sauber | BOR / HUL | 0 | 62 / 21 | 21 | 0 |
| 20 | Mexico City Grand Prix | Racing Bulls | HAD / LAW | 0 | 62 / 0 | 0 | 0 |
| 21 | São Paulo Grand Prix | Alpine | COL / GAS | 0 | 56 / 56 | 50 | 34 |
| 21 | São Paulo Grand Prix | Ferrari | HAM / LEC | 0 | 21 / 0 | 0 | 0 |
| 21 | São Paulo Grand Prix | Haas F1 Team | BEA / OCO | 0 | 56 / 58 | 52 | 46 |
| 21 | São Paulo Grand Prix | Racing Bulls | HAD / LAW | 8 | 56 / 59 | 55 | 55 |
| 21 | São Paulo Grand Prix | Red Bull Racing | TSU / VER | 0 | 56 / 56 | 50 | 35 |
| 21 | São Paulo Grand Prix | Williams | ALB / SAI | 0 | 56 / 56 | 50 | 29 |
| 22 | Las Vegas Grand Prix | Ferrari | HAM / LEC | 0 | 40 / 40 | 36 | 2 |
| 22 | Las Vegas Grand Prix | Haas F1 Team | BEA / OCO | 9 | 41 / 39 | 37 | 30 |
| 22 | Las Vegas Grand Prix | Kick Sauber | BOR / HUL | 0 | 0 / 40 | 0 | 0 |
| 22 | Las Vegas Grand Prix | Mercedes | ANT / RUS | 0 | 43 / 41 | 40 | 31 |
| 22 | Las Vegas Grand Prix | Racing Bulls | HAD / LAW | 0 | 40 / 39 | 35 | 24 |
| 22 | Las Vegas Grand Prix | Red Bull Racing | TSU / VER | 0 | 40 / 40 | 37 | 0 |
| 22 | Las Vegas Grand Prix | Williams | ALB / SAI | 0 | 25 / 40 | 20 | 9 |
| 23 | Qatar Grand Prix | Kick Sauber | BOR / HUL | 0 | 48 / 5 | 5 | 0 |
| 24 | Abu Dhabi Grand Prix | Aston Martin | ALO / STR | 0 | 54 / 53 | 50 | 22 |
| 24 | Abu Dhabi Grand Prix | Ferrari | HAM / LEC | 0 | 48 / 49 | 41 | 26 |
| 24 | Abu Dhabi Grand Prix | Kick Sauber | BOR / HUL | 0 | 52 / 48 | 43 | 21 |
| 24 | Abu Dhabi Grand Prix | McLaren | NOR / PIA | 0 | 51 / 53 | 49 | 20 |
| 24 | Abu Dhabi Grand Prix | Mercedes | ANT / RUS | 0 | 51 / 54 | 48 | 12 |
| 24 | Abu Dhabi Grand Prix | Racing Bulls | HAD / LAW | 9 | 50 / 51 | 46 | 42 |
| 24 | Abu Dhabi Grand Prix | Red Bull Racing | TSU / VER | 0 | 52 / 52 | 47 | 6 |
| 24 | Abu Dhabi Grand Prix | Williams | ALB / SAI | 0 | 48 / 53 | 45 | 12 |

## Tyre-only dry-race experiment

Experimental rule: a race is eligible if at least one non-generated race lap has a known slick compound and no non-generated race lap reports INTERMEDIATE or WET. Weather is ignored. If there are no known slick observations and no wet observations, classify it as unknown. Missing or unrecognised compounds are never filled or assumed slick: those individual laps fail the unchanged clean-lap filter. This tests an absence-of-observed-wet-tyres rule, not proof of dry asphalt.

All 24 races were loaded offline. Their tyre observations were checked, and the unchanged matching calculation was evaluated with the alternative classification. All other settings stay fixed, including the three-lap tyre-age tolerance, ten-lap minimum, disqualification exclusions, and lap filters. Results were held in memory; no production CSV was exported.

| Round | Race | Current rule | Tyre-only rule | Current pairs with gaps | Tyre-only pairs with gaps |
| ---: | --- | --- | --- | ---: | ---: |
| 1 | Australian Grand Prix | wet | wet | 0 | 0 |
| 2 | Chinese Grand Prix | dry | dry | 4 | 4 |
| 3 | Japanese Grand Prix | dry | dry | 5 | 5 |
| 4 | Bahrain Grand Prix | dry | dry | 6 | 6 |
| 5 | Saudi Arabian Grand Prix | dry | dry | 4 | 4 |
| 6 | Miami Grand Prix | wet | dry | 0 | 3 |
| 7 | Emilia Romagna Grand Prix | dry | dry | 5 | 5 |
| 8 | Monaco Grand Prix | dry | dry | 4 | 4 |
| 9 | Spanish Grand Prix | dry | dry | 6 | 6 |
| 10 | Canadian Grand Prix | dry | dry | 2 | 2 |
| 11 | Austrian Grand Prix | dry | dry | 4 | 4 |
| 12 | British Grand Prix | wet | wet | 0 | 0 |
| 13 | Belgian Grand Prix | wet | wet | 0 | 0 |
| 14 | Hungarian Grand Prix | dry | dry | 7 | 7 |
| 15 | Dutch Grand Prix | dry | dry | 8 | 8 |
| 16 | Italian Grand Prix | dry | dry | 4 | 4 |
| 17 | Azerbaijan Grand Prix | dry | dry | 5 | 5 |
| 18 | Singapore Grand Prix | dry | dry | 8 | 8 |
| 19 | United States Grand Prix | dry | dry | 5 | 5 |
| 20 | Mexico City Grand Prix | dry | dry | 7 | 7 |
| 21 | São Paulo Grand Prix | dry | dry | 3 | 3 |
| 22 | Las Vegas Grand Prix | dry | dry | 1 | 1 |
| 23 | Qatar Grand Prix | dry | dry | 9 | 9 |
| 24 | Abu Dhabi Grand Prix | dry | dry | 2 | 2 |

**Only Miami changes: wet → eligible under the tyre-only rule.** Australia, Britain, and Belgium remain wet; the other 20 races remain dry. Season totals become 102 pairs with gaps and 138 blank (94 too few matched laps, 30 wet-race exclusions, 10 no-race-lap exclusions, 4 disqualifications). Existing numeric gaps from the other races agree with the stored CSV to its six-decimal export precision.

Miami has 354 non-generated lap records with missing/unrecognised compounds in the current cache. The experiment excludes those laps. A stricter tyre-only rule requiring every non-generated lap to have a known slick compound instead classifies Miami as unknown, adds no gaps, and leaves the season at 99 available / 141 blank. Both definitions are plausible, so this missing-data choice must be stated when reporting coverage. No compound or tyre-age recovery was attempted.

| Miami pair | Matched laps | Experimental signed gap, first driver (%) | Blank reason |
| --- | ---: | ---: | --- |
| DOO / GAS | 0 |  | No non-generated race lap records: DOO |
| ALO / STR | 5 |  | Only 5 matched laps; need 10 (27 shared clean laps, 5 on the same compound, tyre-age tolerance 3) |
| HAM / LEC | 0 |  | Only 0 matched laps; need 10 (27 shared clean laps, 0 on the same compound, tyre-age tolerance 3) |
| BEA / OCO | 2 |  | Only 2 matched laps; need 10 (2 shared clean laps, 2 on the same compound, tyre-age tolerance 3) |
| BOR / HUL | 0 |  | Only 0 matched laps; need 10 (4 shared clean laps, 4 on the same compound, tyre-age tolerance 3) |
| NOR / PIA | 27 | -0.125365 |  |
| ANT / RUS | 0 |  | Only 0 matched laps; need 10 (24 shared clean laps, 0 on the same compound, tyre-age tolerance 3) |
| HAD / LAW | 4 |  | Only 4 matched laps; need 10 (5 shared clean laps, 4 on the same compound, tyre-age tolerance 3) |
| TSU / VER | 24 | +0.545597 |  |
| ALB / SAI | 23 | -0.087040 |  |

## Proposed regression: explain first, implement later

Fit a separate model for each race/team pair, using all individual clean laps from its two actual teammates. A lap does not need a corresponding teammate lap, equal compound, or similar tyre age to enter. Keep the existing clean-lap filters and exclusions. Test the two dry definitions separately rather than silently replacing the current definition. Mid-season swaps use that race's roster.

The starting model is ordinary least squares on log lap time:

```text
log(lap_seconds) = intercept
                + driver_effect
                + compound_effect
                + tyre_age_slope × centred_tyre_age
                + race_progress_slope × centred_lap_number
                + unexplained_difference
```

One driver and one observed compound are reference categories. Only compounds present in the pair's data get columns. Each coefficient is estimated jointly from the same laps. Centring subtracts the pair's mean age/lap number; it changes the reference point, not the fitted predictions. All retained laps have equal weight in this first model.

- Driver: the remaining consistent pace difference between the teammates after the model's adjustments. This includes any unmodelled difference between their cars or conditions.
- Compound: a separate baseline adjustment for soft, medium, or hard, where observed. Do not encode these as a numeric softness scale.
- Tyre age: an estimated change per extra lap on the tyre set. For the simple first model this slope is linear and common across compounds and both teammates.
- Lap number: an estimated linear change as the race progresses, accounting approximately for fuel burn and track evolution together. It cannot separate those mechanisms.

Log lap time expresses effects proportionally. If the fitted driver effect relative to the teammate is d, report `100 × (exp(d) − 1)`. The reverse uses `−d`, so the two percentages are not exact negatives. This is a ratio of modelled typical (geometric-scale) times, not the old median of matched-lap percentages or an arithmetic mean-time prediction. Constant identical-condition times of 90.0 and 90.3 seconds imply −0.332226% and +0.333333%. A synthetic full-model test also needs varied ages/lap numbers to make the other coefficients identifiable.

### Assumptions in plain language

1. After the adjustments, each driver has one approximately constant pace advantage during this race. Different advantages on different compounds or late versus early race are not represented.
2. Tyre wear and race progress can each be approximated by a straight line on the log-time scale. Real warm-up, degradation cliffs, changing weather and non-linear fuel effects can break this approximation.
3. Both teammates share the same compound offsets and age/progress slopes. Driver-specific tyre management, setup, and degradation remain in the unexplained portion. A later extension could add compound-specific age slopes, only where the data supports them.
4. Enough varied strategies and overlapping conditions exist to distinguish driver pace from tyres and race progress. Within a stint, tyre age and lap number increase together. If one driver only uses one compound and the other only another, compound and driver effects can be inseparable. More rows alone do not solve this.
5. Unmeasured traffic, DRS, damage, team orders and fuel saving do not systematically favour one teammate after adjustment. This is a strong assumption. The estimated driver effect remains adjusted observed pace, not proof of underlying skill.
6. Clean recorded laps represent the usable race portions. Missing laps, retirements and excluded laps are not random; regression does not restore information that was never observed.
7. Laps close together can share the same traffic or tyre issue. Ordinary independent-lap confidence intervals would therefore be overconfident. Do not present them as reliable uncertainty estimates.

### Reporting safeguards and checks before trusting results

- Replace the ten-matched-lap gate with a provisional minimum of ten individual clean laps per driver. Use every clean lap in an eligible fit; no lap-to-lap join. This is a starting sample-size choice, not a statistical guarantee.
- Require enough independent information to estimate all included terms (full column rank and positive residual degrees of freedom). Centre/scale predictors for condition checks; flag near-collinearity and do not treat an unstable coefficient as a reliable gap. Do not silently drop requested terms or add regularisation just to force a result.
- Check both drivers' compound coverage and lap-number/tyre-age ranges. Require at least a shared compound and overlapping ranges as initial extrapolation safeguards. Even overlapping marginal ranges do not guarantee comparable joint conditions; report thin joint support. This is a pair-level reliability check, not exact lap matching.
- Inspect prediction errors against lap number, tyre age, compound, and stint. Look for curved patterns and persistent errors for one driver. Test sensitivity to leaving out individual stints or contiguous lap blocks; mark estimates that change greatly or reverse sign. Too few stints prevents strong uncertainty claims.
- Compare available regression gaps against the existing matched-lap metric, and explain large disagreements. Do not assume filling more blanks is itself evidence of improvement.
- Test known synthetic driver offsets with tyre/progress effects, the 90.0/90.3 conversion, race-specific driver swaps, unequal sample counts, too few laps, perfect driver/compound confounding, age/lap collinearity, and serially correlated errors.
- Future prediction evaluation must use earlier races to predict later ones; a race's own fitted gap cannot be an input for predicting that race.

NIST explains why correlated predictors can make coefficients unstable and why residual plots should check non-linearity and autocorrelation: [Regression Diagnostics](https://www.itl.nist.gov/div898/software/dataplot/refman1/auxillar/regrdiag.htm).

This proposal deliberately stops before regression implementation. It may recover comparisons lost by strict matching, but cannot promise a reliable result for every one of the 88 pairs.
