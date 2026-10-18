# 2025 driver-rating sanity charts

These are inspection plots, not a global driver ranking. Negative ratings and
gaps mean faster than the named teammate. The script reads the saved numbers;
it does not recalculate ratings, adjust weights, or fill missing observations.
Season ratings use log-percentage points; per-race dry gaps use ordinary percent.
The correlation uses the three-decimal ratings stored in the CSV.

Inputs are `data/driver_rating_2025.csv`,
`data/race_pace_dry_final.csv`, and
`data/2025_qualifying_gaps_combined.csv`, plus the explicitly approved fourth
input, `data/race_pace_wet_final.csv`, for round-level wet coverage. Season wet
totals alone cannot tell us which rounds had usable wet observations.
Matplotlib 3.11.2 was already installed in `.venv`; no installation was needed.
All PNGs are saved at 150 dpi.

## 1. Ratings within comparison groups

[Open chart](charts/rating_by_group.png). Bars show `combined_rating`; whiskers
show the saved `combined_ci_low` and `combined_ci_high` endpoints. The 21 drivers
stay in their nine comparison groups, with groups ordered alphabetically and
ratings ordered only inside each group. Doohan's provisional bar is hatched.
Look for wide intervals, intervals crossing zero, and differences in support.
Even inside a connected group, changing teammates are not calibrated to one
common opponent strength. Do not read the vertical order as a global ranking.

## 2. Qualifying versus dry pace

[Open chart](charts/qualifying_vs_dry.png). Each labelled point is a driver;
the diagonal means equal qualifying and dry ratings. **0 of 21 drivers have
opposite signs. Pearson correlation is 0.913945.** Zero would not count as an
opposite sign. Look for points far from the diagonal: agreement in direction
does not mean agreement in magnitude. Tsunoda, Verstappen and Doohan are clear
examples. Teammate observations are related, so this correlation is descriptive,
not a significance test or evidence of 21 independent measurements.

## 3. Selected pairs across races

[Open chart](charts/gap_by_race_selected_pairs.png). The three panels show
TSU relative to VER, NOR relative to PIA, and HAM relative to LEC. Circles mean
strict matched laps; squares mean linear regression. Error bars are plus/minus
one `final_se_pp`, not 95% intervals. Missing rounds break each line; TSU/VER
also has no pairing in rounds 1–2. The panels have different vertical scales.
Look for changes in sign, isolated extremes, wide errors, and changes of method.
Monaco (round 8) is labelled and its raw gap is retained without a season-weight
adjustment. TSU/VER at Monaco is **+3.523612%**, with SE **0.957715 pp**;
NOR/PIA in Mexico (round 20) is **−1.048195%**, with SE **0.090265 pp**.
These deserve inspection, not automatic correction.

The requested pairs already use the requested orientation in this input. If a
future source row reverses a pair, the script uses the reciprocal percentage
formula and transforms its SE with the corresponding derivative. It never
simply negates an ordinary percentage.

## 4. Coverage by driver and round

[Open chart](charts/data_coverage.png). Colours show which saved gaps are
available, regardless of their confidence label. The qualifying roster defines
who entered each round, including drivers without a valid qualifying gap.
Crosses mark not-entered rounds. Look for missing race-pace evidence, sparse wet
coverage, and the Doohan/Colapinto seat change. The palette uses distinguishable
colour-blind-safe colours and includes separate dry-only and wet-only categories
so missing qualifying observations are not silently treated as present.
A race is either wet or dry, so a driver-round cannot have all three signals and the chart has no "All three" category.

| Available signals | Driver-rounds |
| --- | ---: |
| None (entered, but all signals missing) | 2 |
| Qualifying only | 130 |
| Dry only | 10 |
| Qualifying + dry | 326 |
| Wet only | 2 |
| Qualifying + wet | 10 |
| Dry + wet | 0 |
| Not entered | 24 |

There are **480 entered driver-rounds**, plus **24 not-entered cells**, across
21 drivers and 24 rounds. Signal totals are **466 qualifying, 336 dry and 12
wet driver-rounds**. Dry and wet use separate race selections, so no cell has
both dry and wet evidence. A missing gap is not a zero or a performance penalty.

## Things to inspect

- At the initial charting, the method document still described the old
  alphabetical qualifying-reference choice as unresolved. Its stale text has
  now been corrected to describe `2025_teammate_rating_1_log_round_fix`.
- Ten driver-rounds have dry data without qualifying data: TSU/VER in round 7,
  ALO/STR in round 15, BEA/OCO in round 17, ALB/SAI in round 18, and HAD/LAW in
  round 19. BEA/OCO also have wet-only data in round 1. These are coverage
  mismatches, not proof of an error in the ratings.
- BOR/HUL in round 21 are the two entered driver-rounds with no usable signal.
- Doohan has only one usable dry race out of four eligible dry appearances.
  His saved combined interval is [0.015, 0.588], but that does not remove his
  provisional status or make his evidence comparable to a full season.
- Monaco's TSU/VER gap stands out, and the method already warns about Monaco's
  limited reliability. The number and its uncertainty were plotted unchanged.
- Every driver with wet evidence has only one usable wet observation. The
  coverage chart shows how little evidence contributes to that signal.

## Running and checking

The initial run was:

```sh
.venv/bin/python -B make_sanity_charts.py
```

Existing chart names are protected. For another run, choose a new folder:

```sh
.venv/bin/python -B make_sanity_charts.py --output-dir charts_review_002
```

The new tests generate and open all four PNGs in a temporary directory, check
150 dpi and overwrite protection, verify group-local ordering with an example
that would fail a global score sort, and check pair orientation, missing-round
breaks, and coverage categories. Run the complete suite with:

```sh
.venv/bin/python -B -m unittest discover
```

Validation: **112 tests passed (108 existing + 4 new)**. Existing dependency
deprecation warnings were nonfatal. All 122 pre-existing scripts, documents
and CSVs checked retained identical content hashes.
