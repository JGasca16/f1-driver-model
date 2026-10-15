# Dry race pace v3

Rules fixed before the run. Existing scripts, tests and CSVs are read-only.
No points or wins are inputs. Linear is the official regression; curved is
comparison-only. Every final gap and its method stays exactly as in v1:
strict, then accepted linear regression, then low-confidence matching.
Miami remains excluded and no wet method is implemented.

## Bootstrap rules

For each accepted linear pair, order clean laps within **driver + stint** by
lap number. Split them into non-overlapping chunks of **5 retained laps**.
Keep the last shorter chunk; a stint shorter than five is one block. Draw the
same number of blocks with replacement separately within each stint, then
combine them. This follows the requested “split / same number of blocks” rule;
it differs from sampling every overlapping window. A block never crosses a
stint boundary, but successive retained observations can skip actual lap numbers.
Unequal last-block sizes mean the sampled lap count may vary.

Keep original compound, tyre age and race lap number on every sampled record.
Refit ordinary least squares in seconds with the original driver, compound,
tyre-age and lap-number terms. Keep the original compound columns, even if a
resample loses a category: an unidentifiable design is skipped, not simplified.
Centre/scale for numerical stability. Use the same signed percentage conversion
as v1, with equal-driver mean reference predictions over the resampled laps.
Check that the unresampled numerical implementation reproduces v1's estimate.

Use **2,000 attempts, seed 42** restarted for each pair. Skip rank-deficient
fits or nonpositive residual degrees of freedom; also record numerical failures
or invalid nonpositive reference predictions separately. Do not redraw until
2,000 successes. Original sample acceptance gates (ten clean laps, eight on a
shared compound, condition number at most 1,000) remain those of v1; do not
reapply sample-selection gates to bootstrap draws. Report attempted, valid,
skipped and skip reasons per pair. Two valid draws are the mathematical minimum
for an SE; fewer leaves SE/interval blank with a reason. This is not a guarantee
that a handful of successful draws provides useful uncertainty.

For each low-confidence gap, sample overlapping **two-observation** moving
blocks from its chronological matched-lap percentage sequence. Sample enough
blocks to reach the original length and truncate. Use **2,000 resamples, seed
42**, no circular wrapping, statistic = median. The minimum is **3 observations**,
matching the low-confidence definition; do not retain v2's two-full-block gate.
Record `lowconf_se_method=block2`. Short-sample errors can be wide and unstable
by nature; an empirically narrow SE is not proof of precision, since very short
samples cannot represent unseen conditions.

Both SEs are the sample standard deviation of valid bootstrap estimates
(ddof=1). Intervals are **2.5th and 97.5th percentiles**, linear interpolation.
Missing stint labels stop that pair's linear bootstrap with `stint_unknown`.
No accepted gap gives `gap_unavailable`. Strict bootstrap results from v2 and
curved cluster errors remain unchanged. No OLS/cluster fallback replaces a
missing linear block SE.

Stop when the bootstrap time window exceeds **900 seconds (15 minutes)**,
checking during resampling. The window starts at the first bootstrap and
includes intervening work, a conservative interpretation of the total limit.
Report both summed bootstrap compute time and full script runtime. On timeout,
save a new timeout report and do not publish partial combined results. Never
reduce 2,000 attempts to meet the limit.

## Labels, disagreement and inspection columns

Use strict bootstrap SE, new linear block SE, unchanged curved cluster SE and
new short-lap SE for comparisons. Preserve all v2 columns and point estimates;
save replaced v2 labels/flags/inspection values under `_v2` names. The existing
low-confidence v2 SE stays in its column; the new SE is `lowconf_gap_se_pp_v3`.
Fill the requested low-confidence interval columns, preserving their v2 values.

- High: final SE **≤0.15 pp**, count **≥20**. Otherwise medium: SE **≤0.30 pp**,
  count **≥10**. Otherwise low if a gap exists, including missing SE; unavailable
  if no gap. Regression count is the smaller driver's clean-lap count; matched
  methods use matched laps. Preserve `final_confidence_v2`.
- Disagreement: any two published estimates differ by **more than
  2 × sqrt(SEa² + SEb²)**. Curved remains available for this comparison even
  though it is not official. Compare only finite nonnegative SEs; missing is
  not zero. Preserve v2 and fixed 0.3 pp flags. Report every pairwise overlap
  of the three flag rules and the three-way overlap.
- Untestable classification, exclusive and in order: zero published estimates
  = `no_gap_at_all`; one = `only_one_estimate_available`; two or more but fewer
  than two usable errors = `estimate_missing_error`. An unavailable unreliable
  estimate does not count. Two evaluable methods suffice even if another lacks SE.
- Smallest-error choice includes all four published methods, including curved
  for inspection only. Exact ties: strict, linear, curved, low-confidence.
  Missing errors are ineligible. Preserve old selection columns with `_v2`.
  Final gap is never replaced. Count changes exceeding **1e-9 pp** (export
  precision guard), and opposite nonzero signs as flips. Mean absolute change
  includes unchanged pairs on the common available set; also report changed-only
  mean and selection counts by method.
- Retain Monaco's track flag and all existing cluster warnings. They do not
  alter estimates or override the stated label rule.

The disagreement rule assumes independence despite estimates sharing laps. It
is a simplification, not a calibrated significance test. Labels are heuristics,
not probabilities; smallest estimated error need not mean best prediction.

## All-filtered audit

Audit exactly the four `all_laps_filtered` rows in the existing zero-lap audit.
Count individual raw driver-lap records, including generated/partial records,
once each in this order: lap 1; pit-in/out plus next-lap buffer; SC/VSC/red plus
restart buffer; yellow; deleted/unknown deletion; other. “Other” includes invalid
time, generated/duplicate records, accuracy, unknown status/compound/age. Determine
buffers before exclusions. Save per-lap evidence as well as four summary rows.
Counts must reconcile to the raw count and zero clean laps. List all tied largest
filters. Judge legitimacy from recorded status, flags and pit timestamps; do not
claim crash or mechanical causes that these records do not establish. No filter
changes, data repairs or additional performance estimates follow from this audit.

## Limits inherited or added

V1 cleaning and dry classification are unchanged. The model still assumes a
constant driver difference, shared compound/age/progress effects and linear
trends. Traffic, damage, fuel saving, tyre temperatures and strategy selection
remain unmodelled. Missing laps and retirements are not random. Only earlier
races may supply features for predicting later races.

The conditional stint bootstrap holds each driver's strategy/stints fixed. It
does not measure uncertainty from different strategies or missing stints.
One-block stints cannot vary internally. Block length five is fixed, not tuned.
Bootstrap reference conditions vary with sampled laps. Skipping failed draws
can introduce selection bias; inspect skip counts. Short-lap bootstrap support
is especially limited. Curved cluster errors retain the few-cluster and
cross-stint dependence limitations documented in v2. Both bootstraps are
approximations, not guarantees of coverage or causal driver ability.

## New files

Run `.venv/bin/python race_pace_dry_v3.py` offline. It imports existing code
and refuses to overwrite outputs; use a new `--output-dir` for another run.

- `data/race_pace_dry_combined_v3.csv`
- `data/race_pace_all_filtered_audit.csv`
- `data/race_pace_all_filtered_laps_v3.csv`
- `data/race_pace_dry_v3_summary.json`

Results will be appended after the fixed analysis finishes.

## Completed run

All 200 pair rows preserve the v1 final gaps and fallback choices exactly. Linear is the official regression; curved stays in comparison and smallest-error inspection columns only. No existing source/data/test files were modified.

| Confidence | v2 | v3 |
| --- | ---: | ---: |
| High | 100 | 72 |
| Medium | 58 | 79 |
| Low | 10 | 17 |
| Unavailable | 32 | 32 |

**35 pairs changed label.** All 159 accepted linear pairs completed 2,000 resamples (318,000 attempts total), with zero skipped fits. All 12 low-confidence gaps have a two-observation-block SE and interval; none needs a missing-error reason. Strict and curved uncertainty columns are unchanged.

| Disagreement rule | Flagged pairs |
| --- | ---: |
| Fixed 0.3 pp | 31 |
| v2 uncertainty | 33 |
| v3 uncertainty | 18 |

Overlaps: fixed/v2 = 16, fixed/v3 = 15, v2/v3 = 15, all three = 12. These are intersections, not exclusive groups.

| Untestable reason | v2 | v3 |
| --- | ---: | ---: |
| Only one estimate available | 9 | 9 |
| Estimate missing its error | 0 | 0 |
| No gap at all | 32 | 32 |

Both versions therefore leave 41 pairs untestable. The short-lap errors add comparisons to pairs that already had two regression estimates; they do not create a second estimate for any of those 41 pairs. No rule or fallback was changed to reduce this count.

### Smallest-error inspection

| Selected method | Pairs |
| --- | ---: |
| Strict | 26 |
| Linear regression | 8 |
| Curved regression | 129 |
| Low-confidence matched | 5 |
| Unavailable | 32 |

The smallest-error gap differs from final_gap for **140 of 168 available pairs**, with **9 sign flips**. Mean absolute difference is **0.121545 pp across all 168**, or **0.145854 pp among the 140 changed pairs**. Curved often wins this comparison because its error still uses stint clustering while linear now uses block resampling. This does not establish curved as more accurate, and it does not alter the official version or final_gap. Existing small-cluster warnings remain relevant.

### All-filtered audit

Counts below use the fixed order, so overlapping exclusions are charged once. “Raw” includes generated/partial records and is not necessarily completed race laps.

| Race / driver | Raw | Lap 1 | Pit + buffer | SC/VSC/red + buffer | Yellow | Deleted | Other | Largest filter |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Chinese Grand Prix / ALO | 4 | 1 | 1 | 0 | 2 | 0 | 0 | yellow |
| Mexico City Grand Prix / LAW | 5 | 1 | 4 | 0 | 0 | 0 | 0 | pit |
| São Paulo Grand Prix / LEC | 6 | 1 | 0 | 5 | 0 | 0 | 0 | sc_vsc_red |
| Las Vegas Grand Prix / BOR | 2 | 1 | 1 | 0 | 0 | 0 | 0 | lap1;pit |

- **Alonso, China:** lap 1 is excluded; laps 2 and 3 have yellow-containing statuses (`12`, `21`) while their accuracy flags pass; lap 4 has a pit-in timestamp and the race status is Retired. The exclusions match the stated policy. The yellow rule is conservative: it removes the only two otherwise accurate running laps, but these records alone cannot establish whether Alonso slowed. No coding/data defect is demonstrated.
- **Lawson, Mexico:** lap 2 is a pit-in, lap 3 an out-lap, lap 4 the extra warm-up buffer, and lap 5 another pit-in before retirement. Lap 4 is green and accurate, with neither pit timestamp. Its exclusion is entirely the deliberate one-lap buffer, so that individual removal could be overly conservative. Keeping it would provide just one otherwise clean lap, not justify changing the policy or making a reliable pair comparison. No filter is changed.
- **Leclerc, São Paulo:** after lap 1, laps 2–5 contain safety-car status. Lap 6 is a generated record with no valid lap time and VSC/yellow status. The exclusions look legitimate for a short interrupted race ending in retirement. The raw count of six is not six completed laps. No crash cause is inferred.
- **Bortoleto, Las Vegas:** lap 1 includes pit-in; lap 2 has pit-out and pit-in timestamps, no valid lap time, and VSC/yellow status. Lap-1 and pit exclusions tie for most removals. This looks legitimate for an interrupted early retirement, not usable clean pace. It does not demonstrate a pit-lane start.

The summary CSV contains the filter counts, all failed checks and a general policy assessment. The separate lap-evidence CSV gives track status, timestamps, lap time, accuracy, generated and deletion flags for each record. These conclusions identify conservative choices without retroactively relaxing them.

### Runtime and checks

Full analysis runtime: **19.339 seconds**. Bootstrap compute time: **10.613 seconds**; elapsed bootstrap window including intervening work: **18.893 seconds**. All are below 900 seconds. The fixed 2,000 attempts were not reduced.

All **53 tests passed**, including every existing test and eight new tests. Final-gap equality is checked against v1 for every saved pair. Both bootstraps reproduce with seed 42; short stints, confidence boundaries, low-confidence SE availability, untestable reasons and the runtime guard are tested.
