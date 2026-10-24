# Proposed 2024 season extension

This is a proposal for review, not an implementation or permission to download data. Only this document is new. No pipeline was run, no existing file was changed, and no 2026 data was read, downloaded or processed. The review used local documents and source code, plus file-size metadata for the existing 2025 cache. No network request was made.

**Recommendation:** add explicit season and input/output settings to the current approved scripts, retain their 2025 defaults, and require exact 2025 result parity before accepting the extension. Keep the statistical method fixed. Put 2024 data, results, charts and run records in separate year-labelled locations. Review the 2024 roster, race classifications and disqualification evidence before calculating ratings.

The current scripts cannot safely run a new season merely by changing `YEAR`. Some season facts are embedded inside validation and reporting functions, and several output names omit the year. A wrapper that changes only paths would miss these dependencies.

## 1. Inventory of assumptions tied to 2025

This inventory covers the requested production scripts, their current command-line interfaces, the export script, the supplied method documents and the prediction config. Historical versions remain evidence for the 2025 tests; they are not additional production stages to port.

### Race-result export: test_fastf1.py

- Despite its name, this is the FastF1 race-result exporter, not a unit-test class. `main` sets `year = 2025` and has no argument parser.
- It reads the non-testing schedule for that year, loads each main `R` session, and writes `data/{year}_{round:02d}_{race}.csv`. The loop follows the schedule rather than requiring 24 rounds or a season-wide driver count.
- Its cache and output roots are fixed relative to the script: `cache/` and `data/`. The CSV includes only `Abbreviation`, `TeamName`, `GridPosition` and `Position`.
- It does not export laps, weather or finishing status. It checks nonempty results and nonmissing positions, but not a complete expected roster. It catches per-race failures and continues.
- Unlike the protected downstream writers, its `to_csv` call can overwrite an existing same-named result. This must be addressed before any future reuse.

### qualifying_gaps_by_round.py

- `YEAR = 2025`; `main` requires a 24-event schedule and uses `cache/`. The only arguments are `--offline` and `--output-dir`; the latter changes neither the season nor the input baseline.
- `prepare_times` requires 20 distinct qualifying entries; `compare_teammates` requires two per team. These checks must be reconciled with a verified season/session roster, not replaced with an assumed 2024 driver total.
- `DISQUALIFIED_2025` contains round/driver-number keys `(17, "31")`, `(18, "23")` and `(18, "55")`. Its default is used whenever no explicit disqualification mapping is supplied. Reusing it for the same round numbers in another year would be wrong.
- The round structure and advancement inference are Q1/Q2/Q3, with 15 advancing from Q1 and 10 from Q2. These are method/format assumptions, not season-size values. Keep them unless a verified session-format exception requires review.
- Output basenames are `2025_qualifying_gaps_by_round.csv` and `2025_qualifying_round_session_evidence.csv`. The default parent is `data/`.
- `main` always reads `data/2025_qualifying_teammate_gaps.csv` and checks every preserved legacy column against it. There is no corresponding saved 2024 baseline yet. The 2025 parity requirement must remain; a first 2024 run needs separate extraction validation, not comparison with 2025 rows.
- `print_summary` identifies Miami using round 6. Recovery itself is general: it prefers classified round times and recovers eligible missing times from that round's laps. The summary must identify an event by its season manifest, not assume round 6 means Miami.

### qualifying_gaps_combined.py

- The calculation is already largely independent of season: `combine_table` accepts a table, and `combine_rounds` applies the approved symmetric log conversion and fixed round weights.
- `FILENAME` is `2025_qualifying_gaps_combined.csv`. `--input` defaults to `data/2025_qualifying_gaps_by_round.csv`; `--output-dir` defaults to `data/`. There is no season argument.
- There is no hard-coded season driver roster or 24-round check here. The imported `FILENAME` also becomes the rating script's qualifying-output name.

### race_pace_dry.py

- `YEAR = 2025`; `dry_races` requires 24 scheduled events and uses `cache/`. Arguments are only `--offline` and `--output-dir`.
- `load_race` expects 20 entries and two per team. If race results do not meet that condition, it loads qualifying results to fill missing entries; `build_roster` gives race entries precedence. The final roster still must contain 20 drivers.
- `dry_races` excludes every event named “Miami Grand Prix” before loading it, without checking the year. This is a 2025 exclusion embedded as if it applied to all seasons.
- Other events are classified by the weather-and-tyre rule. The observed 20 dry races are an output of the 2025 classification, not a separate `20 dry races` constant.
- `output_paths` writes yearless `race_pace_dry_final.csv` and `race_pace_dry_run_summary.json`, initially in `data/` and on repeats in `runs/dry_NNN/` below the destination. Output protection does not select the correct input year.
- Monaco is identified by event name for its reliability flag. That is a retained method rule, not a 2025-only round-number mapping.

### race_pace_wet.py

- `YEAR = 2025` and `RACES = {1: Australia, 12: Britain, 13: Belgium}` select specific 2025 events. `main` checks a 24-event calendar and exact event names at those numbers.
- Miami is absent from `RACES`, and `print_summary` always says it was excluded. There is no general season-wide wet-candidate discovery step.
- `load_race` and `build_roster` have the same 20-entry/two-per-team assumptions and qualifying fallback as dry pace.
- Arguments are only `--offline` and `--output-dir`; cache is `cache/`.
- `save_output` writes yearless `race_pace_wet_final.csv` both canonically and under `runs/wet_NNN/`. It preserves any existing canonical file. Neither filename identifies the season.

### driver_rating.py

- Header, `YEAR`, `METHOD_VERSION = "2025_teammate_rating_1_log_round_fix"`, and the `season` fields written by `build_ratings` identify 2025.
- `WET_ROUNDS = {1, 12, 13}`; `DRY_ROUNDS = set(range(1, 25)) - WET_ROUNDS - {6}`. `make_observations` uses these sets, and `range(1, 25)` for qualifying, to validate expected appearances.
- `check_roster` requires rounds 1–24, 480 appearances, 21 unique drivers, 20 entries per weekend, reciprocal pairs and one race name per round.
- That function also hard-codes VER/LAW and HAD/TSU before round 3, VER/TSU and HAD/LAW thereafter, and GAS/DOO before round 7 versus GAS/COL thereafter.
- `SOURCES` contains `data/2025_qualifying_gaps_by_round.csv` plus the yearless dry and wet canonical files. The only argument is `--output-dir`; it cannot redirect those inputs.
- `OUTPUT_NAMES` and the publication loop include `driver_rating_2025.csv`, the imported qualifying filename, and yearless `driver_rating_sensitivity.csv`, `driver_rating_signal_diagnostics.csv`, `driver_rating_teammate_periods.csv`, `driver_rating_input_audit.csv` and `driver_rating_run_summary.json`.
- `build_ratings` defaults its provenance path to `data/2025_qualifying_gaps_combined.csv`. `main` records source hashes and the generated qualifying source path.
- The bootstrap helper already takes the observed number of weekends; it does not independently force 24 draws per resample. The fixed roster check currently makes that observed number 24.
- Comparison groups and periods are calculated from teammate links after validation. They should remain data-derived. Monaco's name-based evidence multiplier is a fixed method setting to retain.

### prediction_test.py and prediction_test_config.json

- The script has `--config`, not `--season`. `path_for` expands `{season}` from config; `load_inputs` checks all rounds 1 through `config["rounds"]`. The status-cache URL matcher uses the configured year, rather than a literal 2025.
- Config sets `season: 2025`, `rounds: 24`, initial training rounds 5–12 and main scoring rounds 13–24. `specification` and `rating.method_version` contain 2025 in their names.
- Rating, qualifying, per-round qualifying, result-glob and status-output paths have year templates. Dry/wet inputs do not: they point to the existing yearless canonical files. The cache path is the existing `cache/fastf1_http_cache.sqlite`.
- Outputs use shared `data/runs/` and `prediction_NNN`, with yearless run-local basenames. Those include predictions, metrics, bootstrap draws, comparisons, group stability, baseline winners, coefficients, counts, eligibility, excluded pairs, missing qualifying, prior ratings, features, full-slice validation, status, config, config hash and summary.
- `load_config` compares the config method ID and qualifying weights with imported modules. `validate_full_slice` also checks the saved rating version. A cosmetic version rename can therefore break validation.
- `rebuild_prior` already slices before the feature round and calls lower-level rating functions rather than the 2025-specific full-roster validator. This is useful reuse, but does not make the upstream season rating generic.
- `build_pairs` takes pairs from qualifying, then joins race results/statuses. `pair_id` contains round and driver codes but no year; it must remain qualified by season when combining separate outputs later.
- `read_status_cache` assumes the current requests-cache serialization, matching Jolpica URLs and the configured status vocabulary. It stops on unknown statuses, duplicate records or roster/position disagreement. These are source-format dependencies that need a 2024 audit, not permission to guess a mapping.

### make_sanity_charts.py

- Header and plot titles/axis labels say 2025. `make_charts` reads `driver_rating_2025.csv`, `2025_qualifying_gaps_combined.csv` and the two yearless pace files.
- Its Python function accepts `data_dir`, but its CLI exposes only `--output-dir`, defaulting to `charts/`. The four PNG names do not contain a year.
- `pair_series`, `chart_races`, `coverage_data` and `chart_coverage` use `range(1,25)`, a 24-column matrix, 24-round ticks or limits ending at 24.5.
- Selected pairs are TSU/VER, NOR/PIA and HAM/LEC. Monaco is marked at round 8. The provisional caption names Doohan. Scatter-label offsets list the 2025 driver codes. These are presentation choices that cannot be carried over blindly.

### Documents and historical expectations

| Document | Assumptions that describe 2025, not a reusable 2024 fixture |
| --- | --- |
| `METHOD.md` | Explicit “2025 season only”; its early plans include hand-labelled DNF fault, driver/team regression and finishing-position prediction. Those are not all implemented approved methods. Follow the later method documents, not those aspirations. |
| `METHOD_DRY_RACEPACE.md` | Calendar/roster requirements, Miami exception, named excluded races, 20 dry races/200 pairs, yearless paths and all completed-run counts/parity references. Its early “No wet-race method is implemented” sentence is historical, superseded by the wet document. The historical-version inventory remains 2025 evidence. |
| `METHOD_WET_RACEPACE.md` | Named race/round map, Miami exclusion, 20-entry assumption, yearless paths, 30 eligible pairs and completed-run coverage/removal counts. Its prohibition on merging raw dry/wet gap files does not undo the later separately approved season-rating combination. |
| `QUALIFYING_BY_ROUND.md` | Year-labelled paths, 24/480/240 totals, original-export parity, 2025 DQ registry and Miami recovery/red-flag examples. Counts and historical audit examples are not expected 2024 results. |
| `DRIVER_RATING_METHOD.md` | Year/method ID, roster and swap table, eligible race sets, example output paths and all support/group/driver counts. Numerical weighting and confidence rules are reusable; those counts are not. |
| `PREDICTION_TEST_METHOD.md` | 2025 run/config references, input counts, swap examples, status totals, main 95-case result, group diagnostics and all measured metrics. The fixed history/scoring schedule is retained; actual sample counts must be recomputed. Its statement that another season can be configured requires changed paths and upstream season-ready inputs, not just one year edit. |
| `README.md` | 2025 rating/prediction tables, named groups/driver examples, chart links, current commands and all reported coverage. Preserve it as the existing report until a later documentation task explicitly adds 2024. |

Existing tests also read saved 2025/historical fixtures and assert these results. Preserve them; add season-isolation and roster-exception tests later. Do not replace expected counts to make failures disappear.

Sources: the named scripts, their headers and argument parsers, [prediction config](prediction_test_config.json), and the seven method/report documents listed above.

## 2. Safe implementation options

| Option | Future file changes | Benefit | Main risk |
| --- | --- | --- | --- |
| A: explicit season arguments and settings — recommended | Update `test_fastf1.py`, `qualifying_gaps_by_round.py`, `qualifying_gaps_combined.py`, `race_pace_dry.py`, `race_pace_wet.py`, `driver_rating.py`, `prediction_test.py` and `make_sanity_charts.py`. Add a small season manifest/path layer, new 2024 config/manifest files and parity tests. Add a season-extension run guide; existing result documents and root config can remain historical. | One implementation of each approved calculation; year-specific inputs, exceptions and output destinations become explicit. | Refactoring can change defaults, order of operations, rosters or random-number order. Exact 2025 parity is a release gate. |
| B: keep approved scripts untouched and add wrappers | Add corresponding `*_season.py` entry points for export, qualifying extraction/combination, dry, wet, rating, prediction and charts; add manifests, tests and a guide. No existing source/config/doc needs editing. | Existing code files remain byte-identical. Pure functions such as qualifying combination are easy to reuse. | Several functions read module globals or enforce 2025 facts internally. Wrappers would need replacement orchestration/validation/reporting, or fragile global mutation. That is substantially more than changing paths and can become a second implementation. |

For option B, do not temporarily change `YEAR`/`ROOT` globals in a shared process or relabel 2024 files as 2025 to fool validators. Import pure calculation functions and explicitly test every adapter. If an adapter needs to copy a substantial calculation, reconsider option A.

For option A, keep the current 2025 command defaults and numerical behavior. Pass season facts into validators/loaders/writers rather than teaching calculations about individual years. A manifest would identify schedule, session rosters, driver identities, race classifications, verified DQs, exceptional exclusions and physical file paths. Changes to those facts must have recorded evidence; they are not adjustable performance thresholds.

### Proposed storage

All locations here are proposals; none has been created.

- Raw season exports: `data/2024/raw/2024_01_<race>.csv`, year-labelled qualifying results, lap/weather/status/message exports, and an explicit session/entry manifest.
- Derived season files: `data/2024/2024_qualifying_gaps_by_round.csv`, `2024_qualifying_gaps_combined.csv`, `2024_race_pace_dry_final.csv`, `2024_race_pace_wet_final.csv` and `driver_rating_2024.csv`. Prefix or suffix every diagnostics/status/summary filename with 2024 too.
- Runs: `data/2024/runs/2024_prediction_NNN/2024_metrics.csv` and corresponding year-prefixed files; use the same pattern for other stages. Charts: `charts/2024/2024_<chart>.png`. No run writes into existing `data/runs/` or overwrites root `charts/`.
- A season-specific cache root: `cache/season_2024/`. FastF1 may create an internal year/session hierarchy beneath it. Its HTTP database is separate from the existing one.
- Exclusive writes, reserved new run folders, resolved-path checks and an explicit input/output allowlist prevent accidental access to a 2025 destination. No silent fallback to `data/race_pace_dry_final.csv` or another old canonical file. Preserve first-published 2024 canonical results on repeats too.

### What parity must prove

Before loading 2024, freeze hashes of existing 2025 inputs, scripts, settings and outputs, plus library versions. Run the original and adapted 2025 pipeline offline in isolated output locations against the same frozen cache snapshot. Cache-backed extraction may write internal cache files even offline, so use an isolated copy for this future proof rather than risk the original cache.

Compare all saved scientific fields exactly: race/pair keys, both qualifying directions and selected-round columns, gaps, errors, confidence intervals, flags, blank reasons, eligible/valid counts, season ratings, sensitivities, prediction features, probabilities, coefficients, metrics and bootstrap draws. Keep original serialization precision and random-call ordering. Preserve stable sorting and 2025 exception handling. A mismatch stops the extension; do not relax tolerances or overwrite reference outputs.

CSV bytes should match when serialization and logical provenance are identical. Physical output folders, runtime measurements, new source/config hashes and run identifiers naturally differ; enumerate those metadata differences separately rather than claiming whole-run byte identity. Record logical source references consistently so path differences cannot conceal a numerical mismatch. Chart inputs/order must match; pixel parity additionally needs the same renderer/font environment.

The prediction full-slice tolerance of `0.000500000001` remains solely the existing check against the three-decimal saved rating. It is not a new tolerance for comparing old versus refactored results. The full current test suite and new season/path/exception tests must pass. Post-run hashes must prove all original 2025 files unchanged.

## 3. Data export, completeness and download planning

### Required datasets and current producers

| Dataset | Current producer/consumer | What a later 2024 export needs |
| --- | --- | --- |
| Non-testing calendar and main session identifiers | FastF1 schedule calls in the exporter and qualifying/dry/wet scripts | Year, round, event name and main Q/R session identities, including rescheduled session dates. Do not substitute sprint sessions. |
| Race classification and weekend entrants | `test_fastf1.py` creates the four-column result CSVs; race-pace loaders read richer `session.results` | Preserve the four-column downstream contract; separately retain stable driver IDs/numbers, team, status and entries needed to audit withdrawals/substitutes. No points or wins become inputs. |
| Qualifying classified Q1/Q2/Q3 times | `qualifying_gaps_by_round.py.load_qualifying` loads Q with laps/messages | Classified times, round partitions, driver/team identities, valid lap evidence and later corrections. The script currently exports derived gaps/evidence, not a full raw qualifying-results dataset. |
| Main Q and R lap data | Qualifying loader; `race_pace_dry.py.load_race`; `race_pace_wet.py.load_race` | LapTime, DriverNumber, LapNumber, Compound, TyreLife, Stint, PitInTime, PitOutTime, Time, LapStartTime, TrackStatus, Deleted, FastF1Generated and IsAccurate, plus session identity. Retain all raw laps before filters. |
| Race weather and session boundaries | Dry loader with `weather=True`; `session_status` | Timestamped Rainfall and session Started/Finished times, plus last lap-end time. Weather is needed for classification even if the eventual wet gap uses only its field-median proxy. |
| Track status and race-control messages | Q/R loaders with `messages=True` and timing feeds | Safety car/VSC/red/yellow information, deletion/reinstatement evidence and interruptions. Track status alone cannot justify a missing deletion flag. |
| Finishing status for prediction | `prediction_test.py.read_status_cache` extracts cached Jolpica results, joins the result CSVs and publishes a status table | Matching year/round/driver, normalized status, official position, source URL and evidence. The four-column result CSV alone is insufficient. The prediction stage remains offline. |
| DQ and roster exceptions | Qualifying's manual registry; race results/status; current method audits | A separately verified 2024 exception registry. Race-control investigation messages are not final decisions. Any necessary official-source checks belong to the later network-approved audit. |
| Derived inputs | Qualifying combination, dry/wet and rating scripts | Year-specific qualifying, dry, wet and season-rating tables; these feed prediction and charts. Keep wet/dry race-level exports separate. |

The existing loaders mostly store raw feeds/parsed sessions in FastF1's cache; there is no current standalone export of every raw dataset above. A later approved export step should freeze both the cache and an auditable manifest of these inputs. Reopening a live cache is not a substitute for knowing which snapshot produced a rating.

No telemetry or position stream is required: the approved wet traffic rule uses timing-line crossings. Load only the main qualifying and race sessions. Where the same session supplies results and laps, reuse it rather than download it again.

### Size and time estimate

Local metadata gives a useful scale, not a measured 2024 download:

- `cache/2025/` contains 386 files occupying 100,432,964 bytes, about 100 MB, across the cached main qualifying/race session directories.
- The existing shared HTTP database occupies 195,190,784 bytes, about 195 MB. Its size is not attributed wholly to those sessions; its payloads were not opened for this estimate.
- The individual 2025 race-result CSVs total only 12,501 bytes. Result tables are tiny compared with the cache.

**Planning estimate:** allow roughly 0.1–1 GB of network transfer and 0.3–1 GB of cache/export storage without telemetry; reserve about 2 GB for cache, frozen inputs and run artifacts. These are broad engineering allowances, not a verified wire-size measurement. A first uncached season may take roughly 20–90 minutes of elapsed download/parsing time, with retries, source throttling and machine speed potentially making it longer. No local transfer log supports a narrower promise. Offline analysis should be budgeted separately; the existing dry-method document reports a roughly 21-second standard run, not a season-download benchmark.

After network approval, time and measure a small pilot of two weekends, retain those downloads, then revise the remaining-work estimate without changing any analysis rule. Request approval again only for a genuinely new scope such as telemetry or another season.

### Which 2024 rounds may be incomplete?

**No specific 2024 round is confirmed incomplete by the supplied files.** No 2024 session was loaded in this review, so a named list would be a guess. Treat every round as unverified until the approved export audit. Particular risks are missing entire Q segments, postponed/interrupted sessions, fewer actual entrants, replacements between sessions, early retirements, missing deletion/status feeds, weather gaps and unavailable compound/age records. A red flag or retirement is not itself proof that FastF1 data is incomplete.

The first export report must name every round/session with an issue and separate legitimate no-performance cases from missing feeds. Check expected session presence, actual roster, unique driver/lap keys, time positivity, round partitions, lap/status/message availability, deletion coverage, compound/age/stint missingness, weather coverage at both edges and internally, and matching result/status positions. Report counts before cleaning and after each exclusion.

Do not require every driver to finish or set a time. Preserve a genuine untimed round as a blank; never manufacture performance. Entirely missing required session data, unknown race classification, unresolved DQs or ambiguous rosters stop publication pending review. A race-only replacement without qualifying evidence cannot borrow another driver's qualifying gap.

Keep `cache/season_2024/` out of git under the existing `cache` rule in [.gitignore](.gitignore). No gitignore change is needed. Verify that future cache files are ignored before export, record package/source provenance, and verify a complete offline replay before analysis. The network export is a later task requiring your explicit approval.

## 4. Teammates, substitutions and race eligibility

**Recommendation: no new minimum number of shared races.** One verified shared weekend can form a per-race comparison if it meets that signal's unchanged validity gates. Season ratings then use all available observations with the existing weights, support rules and provisional labels. Requiring several shared races would introduce a new threshold and discard the short periods already allowed in 2025.

Build pairs from the actual team and driver entries for each session/weekend, not the opening-round lineup. For race pace, race entries take priority; qualifying fills a verified withdrawn entry only. For qualifying, use actual main-Q entries. Reconcile the two before the rating step, whose current roster is qualifying-led. Use stable identity mapping across seasons rather than assuming an abbreviation or car number uniquely identifies a person forever.

A change of team or opponent begins a new teammate period. Pool individual race observations through the current weights; do not average short and long period means equally. This retains the handling of Lawson/Tsunoda's team changes and Gasly's Doohan/Colapinto teammate change. A substitute retains their own observations, history and provisional status. No evidence is transferred from the replaced driver.

Some season facts will require an explicit adapter decision: a genuine singleton team/session, a withdrawn driver absent from both classifications, or a replacement between qualifying and the race. Verify those entries first. Do not pad to 20 with a fictitious entrant, force the 2025 count of 21 unique drivers, or pair a substitute with the driver whose seat they took. Recommend an unpaired-entry audit where no second actual entrant can be established, and blank/missing-signal treatment where one exists but has no performance. Any roster-schema change needed to represent this must be approved and covered by parity/exception tests before the run.

Prediction retains its separate gates: four earlier calendar rounds, at least three earlier valid qualifying comparisons for each driver, current usable qualifying, and target eligibility. A substitute may receive a descriptive season rating yet have no eligible predictions. Earlier ratings use only earlier rounds of the season being tested, with no inherited 2025 history in the 2024 test. Head-to-head and previous-race baselines retain the current teammate-period/reset rules.

### Race classification is a season fact, not a transferable race list

Keep the dry weather-and-tyre rule and the wet method's requirement for recorded intermediate/wet tyres. Recommend creating the 2024 eligibility manifest from an audit of all race sessions before viewing pace estimates. A rain-flagged race with no wet tyres remains held for review, not silently reassigned to dry; unknown evidence also stays pending. Do not reuse Australia/Britain/Belgium round numbers from 2025.

Recommend treating the explicit Miami holdout as a **2025 source-data exception**, not a permanent circuit exclusion. Applying the ordinary fixed rules to 2024 Miami needs your approval because the current code excludes the event by name without a year condition. Do not recover compounds automatically or use a tyre-only dry definition to gain coverage.

After export, report: actual entrants and teams per round/session; unique drivers; all team/teammate periods; shared-weekend and valid-signal counts per pair; substitutions/withdrawals and unresolved identities; dry/wet/held-out races with evidence; blank reasons; support, effective races, confidence and provisional-status counts. No 2024 pair, wet-race or driver count is asserted here.

Sources: [qualifying method](QUALIFYING_BY_ROUND.md), [dry method](METHOD_DRY_RACEPACE.md), [wet method](METHOD_WET_RACEPACE.md), [rating method](DRIVER_RATING_METHOD.md), [prediction method](PREDICTION_TEST_METHOD.md).

## 5. Frozen calculations and the separate 2024 prediction run

Do not tune on 2024. Freeze code, settings and the eligibility/exception procedure before calculating its gaps. A later source repair must be documented as a new input snapshot, never selected because it improves coverage or prediction performance.

| Component | Settings and behavior to retain |
| --- | --- |
| Qualifying | Main Q only; classified times preferred; same-round valid-lap recovery and advancement checks; per-round blanks/DQ handling; symmetric log conversion before Q3/Q2/Q1 weights 0.50/0.30/0.20, renormalized; same reciprocal-rounding correction and tolerance 0.0000011. |
| Shared race cleaning | Remove lap 1, pit-in/out and lap after pit-out, non-green status, next fully green lap after SC/VSC/red-status buffer, deleted/generated/inaccurate/invalid laps, unknown compound/age and duplicate records. Same positive-time and tyre-age-at-least-1 requirements. No new slow-lap cutoff. |
| Dry classification | Same rain/tyre rule, 120-second edge tolerance and 180-second maximum weather gap; unknown stops publication. Season-specific exceptions must be explicit. |
| Dry strict | Same lap/compound, tyre-age difference at most 3; at least 10 matches; median per-lap signed percentages. |
| Dry linear | Driver, compound, straight-line age and race-lap terms; 10 clean laps per driver; one shared compound with at least 8 per driver; full rank, nonconstant required columns, residual degrees of freedom and scaled condition number at most 1,000. Same equal-driver reference-time conversion. |
| Final dry choice | Strict, then accepted linear, otherwise blank. No curved or low-confidence fallback. Same reason precedence, Monaco flag, inspection-only smallest-error columns and disagreement rule using twice the combined SE. |
| Race uncertainty | 5-observation blocks, 2,000 attempts/resamples, seed 42 per pair; strict/wet use overlapping nonwrapping matched-observation windows, linear uses the existing separate nonoverlapping chunks within each driver/stint. Same skip handling, at least 2 valid linear draws, sample-standard-deviation SE and 2.5th/97.5th percentiles. Strict points keep 6 decimals, linear points 9; preserve other precision. |
| Wet | Same lap and compound, no pairwise age tolerance; traffic exclusion below 1.5 seconds, missing headway passes; 8 distinct field-reference drivers on current and both adjacent lap numbers; thresholds 1%, 2%, 3%, primary 2%; missing reference fails; at least 10 retained pair-laps. No regression fallback. |
| Race confidence | High: SE at most 0.15 pp and count at least 20; medium: SE at most 0.30 pp and count at least 10; otherwise low if a gap, unavailable if blank. Use matched count or smaller driver's clean count as already specified. |
| Season aggregation | Negative means faster; dry/wet log conversion and SE conversion unchanged. Qualifying observations equally weighted; race weight `max(0.25, 1/(1+(SE_log/0.15)^2))`, missing SE uses 0.25; Monaco dry multiplier 0.5. Signal weights 0.45/0.45/0.10 times evidence factors with reference races 8/8/3, then renormalize. Missing is not zero; wet alone cannot create a combined rating. |
| Season support/uncertainty | Established: qualifying and dry each at least 6 effective races and 50% coverage. High confidence: 12 and 75% plus interval; medium: 6 and 50% plus interval. Other available ratings provisional/low as specified. Whole-weekend bootstrap 2,000, seed 42, 95% usable draws and 6 distinct contributing weekends; same single-wet-race treatment and three-decimal rating display. Retain arithmetic tolerance 1e-12. |
| Rating sensitivities | Keep the same separate variants: Monaco multiplier 1.0; reference races 6/6/2; signal weights 0.50/0.45/0.05. Do not select a new primary setting from their results. |
| Prediction | Same three targets, earlier-round features, history gates, complete-case current qualifying, M1/M2/M3 features, no-intercept L2 logistic model with C=1, no scaling and the same solver settings. Same baseline smoothing, periods, tie credit, clipping, metrics, whole-weekend resampling, seed, comparisons and no-refit group diagnostics. |

The authoritative details remain the method documents and config; this table is a checklist, not permission to change an unlisted behavior. “24 rounds” is a calendar fact to verify in the approved export, not a model parameter to tune.

### Can prediction_test_config.json change only its season?

**Not safely with the current unmodified entry point.** Although `path_for` formats the year in some paths, changing `season` alone would still read the existing dry/wet canonical files and shared cache, and write to the shared run root. It also does not make upstream rating validation or season labelling generic.

To satisfy a season-only change in the statistical config, recommend preserving the original file and creating a new year-labelled copy with only `season: 2024` changed, plus an **explicit separate season manifest** for all physical paths, output basenames and source facts. The adapted path resolver must use that manifest consistently, with no fallback to old paths. Record both config and manifest, their hashes, and every resolved path in the run. Keep the historical method-version ID as an algorithm identifier; the separate `season` field identifies the data year. Do not silently rename the method ID simply because the data year changes.

That requires future path-layer code; it is not a command that works today. The simpler alternative is a new 2024 config whose season and input/output paths change while every statistical setting remains identical. If chosen, list those metadata-only differences explicitly. The original `prediction_test_config.json` remains unchanged in either design.

On the planned 24-round structure, retain rounds 5–12 for initial training and 13–24 for main scoring, updating before each weekend using earlier data only. Keep the 15-training-example gate and early/fallback reporting. If the verified schedule differs, stop for a schedule decision rather than moving the scoring window to improve results.

With ten complete teammate pairs per weekend, the structural ceilings are 240 season pair-races, 200 in rounds 5–24, 80 initial-training candidates and 120 main candidates across 12 weekends. These are arithmetic ceilings under the stated roster assumption, not exported 2024 counts. The saved 2025 main target retained 95 of 120; the sensitivities retained 113 and 111. That suggests roughly the same order of sample size, not a promise of those counts. Retirements, missing qualifying, substitutions and history gates will determine the actual 2024 sample.

Rebuild each 2024 prior rating only from rounds before the predicted race. The full-season 2024 rating is validation/diagnostic-only, just as for 2025. Never use the predicted race's pace, wet gap, result position/status, points, wins or future roster changes as model features. Current qualifying remains the separately approved feature. Do not pool years for training or choose rules after comparing their scores.

Sources: [prediction config](prediction_test_config.json), [prediction method](PREDICTION_TEST_METHOD.md), [rating method](DRIVER_RATING_METHOD.md), [dry method](METHOD_DRY_RACEPACE.md), [wet method](METHOD_WET_RACEPACE.md), [qualifying method](QUALIFYING_BY_ROUND.md).

## 6. What a second season enables

It provides a separate season-relative rating, uncertainty and coverage record for each observed driver, plus another run of the frozen earlier-round prediction test. It allows us to examine whether the method behaves similarly with different teammate histories and conditions. It is still a retrospective replication, not a prospective prediction claim.

Retaining stable driver identity, team, season, teammate period, signed pair gaps, units, uncertainty, support and missing reasons would supply links across years where drivers change teams or opponents. Those links are useful inputs to a later connected career model. They do not themselves calibrate opponents or produce an absolute cross-team ranking; do not subtract current season scores or simply average them into a career score.

The next spec would need to define a joint comparison model, connected components, team/season and driver-change assumptions, aging or time variation, how sparse substitute links affect uncertainty, dependence between comparisons, and the reference/anchors for a 0–100 display scale. Disconnected groups must remain explicitly uncomparable. A shared driver across years is not proof that their ability stayed constant. Preserve per-race observations and provenance rather than only rounded season summaries.

No 2026 access is needed for this extension, and none is authorized by it.

## 7. Recommended order and effort

Prompt counts below are rough task-sized requests after this proposal, not guarantees. Approval and data quality can change the amount of work.

| Step | Work and stopping point | Rough prompts |
| --- | --- | ---: |
| Approve the extension decisions | Choose architecture, paths, eligibility/exception handling and config design; freeze the method. | 1 |
| Adapt and prove isolation | Add explicit season context, protected writers and exception tests; reproduce 2025 offline exactly; run all tests and inspect hashes. No network yet. | 2–3 |
| Approve and run the export pilot | Explicit network approval for 2024 main Q/R and necessary status/decision evidence only; measure size/time and verify required fields. | 1 |
| Complete export and audit | Finish approved downloads; report named missing sessions, roster changes, DQs and dry/wet/held-out classifications; resolve exceptions before ratings. | 1–2 |
| Run qualifying and race pace offline | Produce year-labelled outputs with unchanged rules; inspect counts and every blank reason; verify offline completeness. | 1–2 |
| Build season ratings | Same weights, confidence, bootstrap and sensitivities; report periods, coverage and provisional drivers. | 1 |
| Run the frozen prediction test | Same schedule/models/targets; publish counts before metrics, uncertainty and leakage checks. | 1 |
| Inspect and document | Year-specific charts with valid actual pair choices, report differences from 2025, verify paths/hashes and full tests. | 1 |

This is roughly **9–12 prompts**, with extra tasks only if data or parity problems need investigation. Do not combine approval of this plan with approval to download: the export is a separate network step.

## Open decisions for the project owner

1. Approve option A, explicit season settings with exact 2025 parity, or prefer the more involved wrapper approach?
2. Approve the proposed `data/2024/`, `charts/2024/` and `cache/season_2024/` layout, with the year in every published output basename?
3. Approve a separate season manifest so the copied prediction-method config changes only its season, or allow explicit path-only changes in the new config instead?
4. Approve deriving 2024 race eligibility from the unchanged rules, treating Miami's explicit holdout as 2025-specific, and holding rain-only/unknown cases for review before analysis?
5. Approve actual-session roster handling without a new shared-race minimum, with explicit review of singleton entries or between-session substitutes rather than invented data?
6. After implementation and 2025 parity pass, approve the separate 2024 network export and its provisional size/time budget?
