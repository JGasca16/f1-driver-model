# Dry regression results

Offline run of the fixed rules in RACEPACE_REGRESSION_METHOD.md. There are 20
dry races and 200 race/team pairs. Australia, Miami, Britain and Belgium are
not in these outputs. No points or wins were used. Both regression versions
are retained; neither was selected over the other.

| Final method | Pairs |
| --- | ---: |
| Existing strict gap | 99 |
| Added by linear regression | 69 |
| Added by low-confidence matching | 0 |
| Still blank | 32 |

There are 12 available low-confidence gaps (3–9 matched laps). All already have
a published linear regression estimate, so none wins the fixed fallback order.
The combined table publishes 168 final gaps. Labels high/medium/low follow the
requested method order and are not calibrated probabilities.

## Blank final gaps

| Primary reason | Pairs |
| --- | ---: |
| `effects_not_identifiable` | 10 |
| `strategy_confounded` | 9 |
| `no_race_laps` | 9 |
| `race_disqualification` | 4 |

Both regressions publish 159 gaps. Across all dry pairs, 19 fits in each version
fail identifiability without a strategy flag; nine of those pairs still have a
strict gap. The nine strategy-confounded pairs have blank published regression
gaps. Two have identifiable estimates retained in the unreliable columns; seven
also have rank-deficient designs, so there is no unique estimate to retain.

## Linear versus curved

Use the same 159 pairs with both published estimates:

| Measure | Value |
| --- | ---: |
| Mean absolute linear gap | 0.491959% |
| Mean absolute curved gap | 0.511693% |
| Curved minus linear mean absolute gap | +0.019734 percentage points |
| Mean absolute difference between their estimates | 0.088398 percentage points |

There are **31 pairs** where at least two available methods differ by more than
0.3 percentage points. Unreliable estimates are not included in this count.
These flags do not change the requested fallback order or confidence label.

## Files and interpretation

- `data/race_pace_dry_combined.csv`: one alphabetical driver/teammate row per
  dry-race pair, all methods, fallback result, reasons and disagreement flag.
- `data/race_pace_regression_linear.csv` and
  `data/race_pace_regression_curved.csv`: estimates, driver coefficients in
  seconds, coefficient standard errors, gap standard errors in percentage
  points, reference teammate times, shared-compound counts and fit checks.
- `data/race_pace_regression_comparison.csv`: same-pair aggregate comparison.

Strict and low-confidence standard errors are blank because these matched
medians have no standard-error estimator in this version. Regression errors
are conventional OLS errors and do not account for correlated laps. Do not
interpret them as established precision about underlying driver ability.

Miami remains excluded. Its report, MIAMI_COMPOUND_INVESTIGATION.md, finds 54
known compound-label conflicts across 12 drivers, separate from 354 recovered
missing compounds. Sixteen conflicting labels survive the clean-lap filter.
The source stint sequence and pit-stop boundaries agree; delayed derived tyre
labels should not determine the change boundary. No Miami data was repaired
or used for pace in this run.
