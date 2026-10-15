# Blocked race-pace comparisons: offline audit

This audit reads METHOD.md, RACEPACE.md, race_pace_gaps.py and the cached 2025
race sessions. It preserves the current three-lap tyre-age tolerance and the
minimum of ten matched laps. No existing script, CSV or document was changed.
No regression model was implemented.

## New outputs

- `data/race_pace_blocked_diagnostics.csv`: all 88 blocked pairs, their matched
  counts, and a full accounting of filters.
- `data/race_pace_dry_rule_diagnostics.csv`: all 24 races under the current and
  two tyre-only interpretations, with coverage counts.
- `data/race_pace_returning_pairs_diagnostics.csv`: all ten Miami pairs under
  the no-observed-wet-tyres interpretation, including remaining blank reasons.
- `diagnose_race_pace_blocked.py`: the audit, not a regression model. It uses
  cached data only and refuses to overwrite any of its three output CSVs.

## What the filter counts mean

Each row represents one race/team pair, with drivers ordered alphabetically.
The unit of a filter removal is one **potential same-numbered lap comparison**,
not two separate driver laps. If both drivers pit on lap 20, that removes one
comparison. Individual raw-record and clean-lap counts are included separately.

The `removed_` columns are a sequential accounting. A comparison is charged
to the first filter it fails in the order below. Therefore these columns add
up without double-counting. This is an audit attribution order; the production
code applies the individual-lap conditions together, so it has no unique
causal ordering for overlapping failures.

1. Start with the union of both drivers' recorded lap numbers.
2. Remove lap numbers without a record from both drivers.
3. Remove lap 1 or invalid lap numbers.
4. Remove missing/nonpositive/nonfinite times.
5. Remove generated/unknown-generation records and duplicate driver/lap numbers.
6. Remove pit-in/out laps and the next numbered lap after an out-lap (`pit`).
7. Remove SC/VSC/VSC-ending/red-flag laps, including the first fully green lap
   after such a period (`sc_vsc_red`).
8. Remove laps containing yellow status (`yellow`). A lap with both yellow
   and SC status is charged to SC in this order.
9. Remove any remaining non-clear/unknown track status.
10. Remove deleted/unknown-deletion records, then inaccurate/unknown-accuracy records.
11. Remove unknown/non-slick compounds and invalid/missing tyre ages.
12. From the surviving shared clean laps, remove compound mismatches.
13. From same-compound laps, remove tyre-age differences greater than three laps.

Buffers are determined from the original lap sequence, exactly as in the
production function. The `affected_*_overlapping` columns also count each
individual-lap condition independently over the original shared lap numbers.
These overlapping counts must not be summed. They show, for example, a yellow
lap even if the sequential accounting already removed it as a pit lap.

For every pair, these checks passed:

- The independently reconstructed clean-lap set equals `filter_clean_laps`.
- Shared clean, same-compound and final matched counts equal the existing CSV.
- Union lap numbers minus all sequential removals equals matched laps.

## Results for the 88 pairs

| Matched laps | Pairs |
| --- | ---: |
| 5–9 | 10 |
| 1–4 | 2 |
| 0 | 76 |

Exact distribution: 0 (76 pairs), 4 (2), 5 (1), 6 (3), 7 (3), 8 (1), 9 (2).
All individual pair counts are in the requested diagnostics CSV.

Across the 88 pairs, the sequential accounting removes:

| Reason | Potential lap comparisons removed |
| --- | ---: |
| No record from both teammates | 568 |
| Lap 1 / invalid lap number | 88 |
| Invalid lap time | 30 |
| Pit laps and warm-up buffer | 707 |
| SC/VSC/red flags and restart buffer | 187 |
| Yellow flags | 95 |
| Deleted / unknown deletion status | 93 |
| Compound mismatch after cleaning | 2,033 |
| Tyre-age mismatch after compound matching | 1,460 |

Other sequential filter categories remove zero additional comparisons in this
specific subset. Zero additional removals does not mean the condition never
occurred: earlier filters may already have removed those laps. These counts
are comparison opportunities, not counts of races or drivers.

Of the 76 zero-match pairs, 5 have no shared clean lap numbers, 8 have no
same-compound shared clean laps, and 63 lose all same-compound matches to the
tyre-age tolerance. Of all 88 blocked pairs, 80 have at least ten individual
clean laps for each driver. Strict strategy matching is therefore a major
coverage constraint, although regression is not guaranteed to solve every case.

## Tyre-only dry classification

The literal, conservative interpretation of “everyone ran slick tyres” requires
all non-generated race-lap records to have a known SOFT, MEDIUM or HARD compound.
Any intermediate/wet observation makes the race wet. Missing compound records
without wet observations make it unknown. Weather is ignored.

Under that interpretation, **no excluded race can be confirmed eligible from
this cache**. Miami changes from wet to unknown, because 354 non-generated lap
records have missing/unrecognised compounds. It adds zero confirmed pair gaps.
This is incomplete evidence, not evidence that Miami used wet tyres.

The practical alternative is “slick tyres observed and no intermediate/wet
tyres recorded.” Missing compounds are not filled; those individual laps still
fail the unchanged clean-lap filter. Under this explicitly weaker definition:

- Only Miami returns. Australia, Britain and Belgium remain excluded.
- Three extra pairs have gaps: NOR/PIA (27 matched laps), TSU/VER (24), and
  ALB/SAI (23). The season goes from 99 to 102 available pairs, and 141 to 138 blanks.
- Miami's six other matching failures have 0–5 laps; Alpine has no usable
  non-generated race records for Doohan, so its gap also remains blank.
- The other 20 eligible races' numeric gaps agree with the existing CSV to its
  six-decimal export precision.

Do not label this weaker rule proof that every driver used slicks throughout.
No missing tyre information was recovered in this audit. Neither experimental
rule replaced the current production definition.

## Regression proposal, awaiting approval

Fit one model for each teammate pair in each race. Feed it every individual
clean lap from those two drivers. Keep the existing individual-lap filters and
race exclusions, but remove the requirement to find a matching teammate lap.
Use that race's actual teammate roster, including mid-season swaps.

The model explains log lap time with four terms:

- **Driver:** a constant remaining pace difference between the teammates.
- **Compound:** a separate baseline adjustment for each observed slick compound.
- **Tyre age:** a straight-line adjustment for an extra lap on the tyre set.
- **Lap number:** a straight-line adjustment as the race progresses, approximating
  the combined influence of fuel burn and changing track conditions.

Fit the terms together using least squares. Using log time makes the driver
difference proportional: a fitted difference d becomes 100 × (exp(d) − 1)
percent. Negative means faster. The reverse comparison uses −d and a different
denominator. This estimates a ratio of adjusted typical times; it is not the
old median of matched-lap gaps and is not a direct measure of pure driver skill.

### Different strategies

A driver's lap on an older medium tyre and a teammate's lap on a newer hard
tyre can both enter. The model uses the compound, age and race-stage terms to
estimate the expected effect of those differences. It then estimates the
remaining driver difference. The laps need not share a number, compound or age.

This depends on having enough varied and overlapping conditions to learn the
adjustments. If one driver only used mediums and the other only hards, the
data may not distinguish a compound difference from a driver difference. If
tyre age always rises in lockstep with lap number, it may not distinguish wear
from race progress. More laps alone do not solve either problem.

### Assumptions and limits

1. The driver advantage is approximately constant during the race.
2. Tyre-age and race-progress effects are approximately linear on the log scale.
3. Both teammates share the same compound effects and age/progress slopes.
   This first model does not estimate compound-specific degradation slopes.
4. There is enough variation to estimate the effects separately, with meaningful
   overlap in both drivers' conditions. Otherwise leave the estimate unreliable
   or blank rather than force a number.
5. Traffic, damage, DRS, fuel saving and team orders are not fully measured.
   Persistent differences can be incorrectly assigned to the driver term.
6. Consecutive laps share conditions. Treating them as independent observations
   would exaggerate the precision of the estimate.
7. Clean laps describe the retained race portions; missing laps and retirements
   are not random. Using all clean laps does not remove that selection problem.

Initially require ten individual clean laps per driver, rather than ten matched
laps. Check whether coefficients are identifiable, whether conditions overlap,
and whether leaving out a stint changes the gap sharply. Inspect prediction
errors for curved tyre-age trends and persistent time patterns. A larger number
of nonblank results alone would not establish that the model is better.

No model code has been written. Implementation will wait for approval.
