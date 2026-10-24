# Season extension parity report

**PASS: exact 2025 parity.** All 29 generated CSVs are byte-for-byte identical between the original and adapted pipelines. All 41 output/data checks have zero scientific mismatches. No tolerance was introduced or relaxed. All 140 tests passed: the unchanged 126 existing tests and 14 new tests, with no skips.

## What was run

The baseline was frozen before editing. The original eight scripts were exported from git HEAD `86a922db68254fa2982c2414b7a6464061977a28` into `cache/_parity/original_src/`. They were run without editing their source. The final adapted run is in `cache/_parity/adapted_src_002/`. Both used only `cache/_parity/cache_copy/`, with separate output trees and the same initial 2025 race-result and legacy qualifying CSVs. The first adapted run was also exact and remains preserved; the second verifies an added check of repeat-run paths before folder creation. No reference output was overwritten.

Both runs completed qualifying by round, qualifying combination, dry pace, wet pace, ratings including all sensitivity variants, the prediction test and four charts. The exporter was not run on a live season: its write function was tested with a temporary fixture. All adapted commands used `--offline`. Original FastF1 commands used `--offline`; the original CSV-only commands do not accept that flag and were run unchanged under the same network block. A process-wide socket/DNS tripwire in `cache/_parity/offline_guard/sitecustomize.py` blocked network connections for both runs and the tests. No network request was made. No 2024 or 2026 data was read, created, or downloaded. The new 2024 JSON files contain configuration only.

For rating runs, the original and adapted commands both used a fresh `rating/` destination to avoid colliding with the qualifying-combination output. Each new rating CSV was then copied to its absent canonical input location inside its isolated workspace. This preserves identical logical provenance in both runs.

## Exact output checks

Paths below are relative to each isolated workspace. CSV equality includes headers, row order, identities, both qualifying directions, selected-round columns, all gaps, errors, intervals, flags, blanks, reason codes, counts, ratings, sensitivity results, features, predictions, coefficients, metrics and all 144,000 prediction-bootstrap rows. No columns were removed from CSV comparisons.

| Output or data check | Rows | Result | Scientific mismatches |
| --- | ---: | --- | ---: |
| `data/2025_qualifying_gaps_by_round.csv` | 480 | Exact bytes | 0 |
| `data/2025_qualifying_gaps_combined.csv` | 480 | Exact bytes | 0 |
| `data/2025_qualifying_round_session_evidence.csv` | 407 | Exact bytes | 0 |
| `data/2025_race_finish_status.csv` | 479 | Exact bytes | 0 |
| `data/driver_rating_2025.csv` | 21 | Exact bytes | 0 |
| `data/race_pace_dry_final.csv` | 200 | Exact bytes | 0 |
| `data/race_pace_wet_final.csv` | 30 | Exact bytes | 0 |
| `data/runs/prediction_001/baseline_winners.csv` | 27 | Exact bytes | 0 |
| `data/runs/prediction_001/bootstrap.csv` | 144000 | Exact bytes | 0 |
| `data/runs/prediction_001/coefficients.csv` | 180 | Exact bytes | 0 |
| `data/runs/prediction_001/comparisons.csv` | 351 | Exact bytes | 0 |
| `data/runs/prediction_001/counts.csv` | 3 | Exact bytes | 0 |
| `data/runs/prediction_001/eligibility.csv` | 720 | Exact bytes | 0 |
| `data/runs/prediction_001/excluded_pairs.csv` | 202 | Exact bytes | 0 |
| `data/runs/prediction_001/features.csv` | 200 | Exact bytes | 0 |
| `data/runs/prediction_001/full_slice_validation.csv` | 21 | Exact bytes | 0 |
| `data/runs/prediction_001/group_stability.csv` | 81 | Exact bytes | 0 |
| `data/runs/prediction_001/metrics.csv` | 72 | Exact bytes | 0 |
| `data/runs/prediction_001/missing_qualifying_pairs.csv` | 7 | Exact bytes | 0 |
| `data/runs/prediction_001/predictions.csv` | 4144 | Exact bytes | 0 |
| `data/runs/prediction_001/prior_ratings.csv` | 417 | Exact bytes | 0 |
| `data/runs/prediction_001/race_finish_status.csv` | 479 | Exact bytes | 0 |
| `data/runs/wet_001/race_pace_wet_final.csv` | 30 | Exact bytes | 0 |
| `rating/2025_qualifying_gaps_combined.csv` | 480 | Exact bytes | 0 |
| `rating/driver_rating_2025.csv` | 21 | Exact bytes | 0 |
| `rating/driver_rating_input_audit.csv` | 0 | Exact bytes | 0 |
| `rating/driver_rating_sensitivity.csv` | 63 | Exact bytes | 0 |
| `rating/driver_rating_signal_diagnostics.csv` | 63 | Exact bytes | 0 |
| `rating/driver_rating_teammate_periods.csv` | 78 | Exact bytes | 0 |
| `data/race_pace_dry_run_summary.json` | — | Exact values; metadata below | 0 |
| `rating/driver_rating_run_summary.json` | — | Exact values; metadata below | 0 |
| `data/runs/prediction_001/summary.json` | — | Exact values; metadata below | 0 |
| `data/runs/prediction_001/prediction_test_config.json` | — | Exact bytes | 0 |
| `data/runs/prediction_001/config.sha256` | — | Exact bytes | 0 |
| `chart data: group_order_and_values` | — | Exact values and order | 0 |
| `chart data: scatter_values` | — | Exact values and order | 0 |
| `chart data: scatter_statistics` | — | Exact values and order | 0 |
| `chart data: pair_series` | — | Exact values and order | 0 |
| `chart data: coverage_driver_order` | — | Exact values and order | 0 |
| `chart data: coverage_matrix` | — | Exact values and order | 0 |
| `rating: 2000 whole-weekend bootstrap draw vectors` | 2000 | Exact values and order | 0 |

All four PNGs were generated in both isolated chart folders. Pixel equality was not required or used as a gate. The transformed data and ordering behind every chart were checked exactly. The 2,000 rating-bootstrap weekend draw vectors also match exactly. Eleven pace/rating bootstrap function bodies are structurally identical to the originals, preserving draw order, block construction, seeds and calculations.

## Metadata differences

The comparison explicitly permitted only `runtime_seconds` in the dry and rating summary JSONs, and `runtime_seconds`, `script_sha256`, `rating_script_sha256` and `qualifying_script_sha256` in the prediction summary. Those are the only differing JSON fields. Statistical settings, method ID, source-file hashes, config bytes, config hash, counts and reported statistics all match. Absolute workspace paths differ in terminal logs; logical CSV provenance and run IDs are identical. No other path, timestamp or hash difference was silently ignored.

| Summary | Original runtime (seconds) | Adapted runtime (seconds) | Other differing fields |
| --- | ---: | ---: | --- |
| `data/race_pace_dry_run_summary.json` | 13.301081 | 21.984895 | None |
| `rating/driver_rating_run_summary.json` | 0.404261 | 0.723753 | None |
| `data/runs/prediction_001/summary.json` | 2.109919 | 3.246333 | `script_sha256`, `rating_script_sha256`, `qualifying_script_sha256` |

Exact metadata values and hashes are saved in [the comparison record](data/runs/season_extension_parity_comparison.json).

## Environment

| Component | Version |
| --- | --- |
| Python | 3.14.7 (v3.14.7:823f0323ee6, Aug  5 2026, 07:07:01) [Clang 21.0.0 (clang-2100.1.1.101)] |
| pandas | 2.3.3 |
| numpy | 2.5.4 |
| scikit-learn | NOT INSTALLED |
| matplotlib | 3.11.2 |
| fastf1 | 3.8.3 |
| scipy | 1.18.1 |

No package was installed or upgraded. The prediction script uses SciPy directly, so the absent scikit-learn package did not prevent execution. Versions were recorded before edits in [the version record](data/runs/season_extension_versions.json).

## Season settings and protection

The eight approved scripts now accept `--season` (default 2025), `--manifest`, and `--offline`. Existing numerical functions keep their calling conventions through optional season arguments. The new manifest owns calendar size, entrant counts, qualifying advancement counts, the disqualification registry, wet/dry scope, holdouts, roster-period checks, selected chart pairs, labels, output names and paths. The algorithm ID remains `2025_teammate_rating_1_log_round_fix`; it is not a claim that another season is 2025. All statistical thresholds, weights, seeds and sensitivity settings remain unchanged.

Non-2025 input/output paths must stay under their own `data/{season}/`, `charts/{season}/` or `cache/season_{season}/` boundaries, including after resolving symlinks. Published filenames include the year. Shared 2025 locations are refused rather than used as fallbacks. Output writes remain exclusive or use a newly reserved numbered directory. The exporter now uses exclusive creation too. A repeated export reports existing outputs as failures and leaves them intact.

The copied `prediction_test_config_2024.json` differs from the original only in `season` and the added manifest reference. The original config is untouched. The manifest supplies paths; the frozen prediction settings are unchanged, and its round count must agree with the verified manifest.

## Miami audit

The original reconstruction code was not saved in this repository. The new read-only hook in `season_eligibility_audit.py` therefore re-expresses the existing counting rule in [MIAMI_COMPOUND_INVESTIGATION.md](MIAMI_COMPOUND_INVESTIGATION.md), rather than importing an unavailable implementation. It changes no approved pace calculation and applies no recovered or corrected label.

The hook reads explicit driver/stint compounds and starting ages from the isolated 2025 timing-app cache. Source total tyre laps minus starting age gives the stint length. Cumulative source lengths must agree exactly with recorded pit-in/following pit-out boundaries and the full non-generated lap sequence. A pit-lane start and a retirement pit-in do not create tyre changes. Inconsistent totals, missing/ambiguous source records, red-flag changes or extra/ambiguous stops return `review_required`; they do not trigger a guessed repair or a claim of eligibility.

On 2025 Miami, the result matches the prior investigation: **54 known compound conflicts across 12 drivers**, **354 unknown compounds**, **403 known tyre-age conflicts**, and **zero unresolved driver timelines**. The affected drivers are ALB, ALO, ANT, HAM, LAW, LEC, NOR, PIA, RUS, SAI, TSU and VER. All 354 initial-stint recoveries in the existing audit agree with the pit-aligned sequence. The individual evidence is [season_extension_miami_verified.csv](data/runs/season_extension_miami_verified.csv), with [its summary](data/runs/season_extension_miami_verified_summary.json).

The earlier new files named `season_extension_miami_audit.csv` and `season_extension_miami_audit_summary.json` are preserved development diagnostics, not the verified result: they initially counted the literal missing-value string `nan` as a known label, giving 408 rather than 54 conflicts. The verified audit recognizes only actual tyre compound names as known. This corrects missing-value handling in the new diagnostic; it changes no pace filter, threshold, source file or reference result.

2025 keeps its documented Miami holdout regardless of this audit. The 2024 holdout registry is empty and its Miami audit is `UNVERIFIED`. After a separately approved export, run the hook on that season’s own lap/timing data and save its evidence. Add a compound-conflict holdout only if a verified conflict recurs; do not exclude by circuit name. An ambiguous audit pauses review rather than proving either presence or absence of the conflict. Ordinary weather/tyre eligibility still applies separately. No 2024 eligibility conclusion is available today.

## Unverified 2024 facts

All eight CLI commands were tested with `--season 2024 --offline`. Each stopped with a message listing unverified facts before opening season data or creating season directories. These fields still need evidence:

- `round_count`
- `expected_entries`
- `team_size`
- `expected_appearances`
- `expected_unique_drivers`
- `registry_verified`
- `roster_verified`
- `wet_races`
- `dry_rounds`
- `qualifying_summary`
- `legacy_parity_required`
- `miami_audit`
- `charts`
- `qualifying_advancement`

The empty disqualification and roster-exception registries are placeholders, not findings that there were no exceptions. Their verification flags remain unverified. No 2025 fact is substituted. The separate later network-export/audit step must establish these facts; do not fill them with guesses just to make a command run.

## Roster schema work deliberately deferred

The current schema still assumes one reciprocal two-driver pairing per team/weekend and a fixed entrant count. Ordinary changes between weekends already work through actual driver/team identities and teammate periods; they need verified manifest records, not a new shared-race minimum or a weighting change.

If the export finds a real singleton entry, a future change would need per-event expected entries, an explicit unpaired entry with a nullable teammate and reason, and eligible-appearance accounting that distinguishes “no teammate” from “missing timed evidence.” It must not invent a second entrant merely to satisfy the pair schema.

If a substitute changes between qualifying and the race, a future change would need session-specific entrant/seat identities and separate qualifying/race pairings, followed by an explicit join for driver ratings and prediction targets. The present union by DriverNumber can create three team entries, while the rating and prediction schemas expect one qualifying-defined pairing per weekend. A replacement with a different number also needs a stable driver identity. A substitute who occupies the same seat for the entire weekend already fits the present pair schema; partial-season evidence rules stay unchanged. These structural changes were not implemented or presumed necessary without an export audit.

## Tests, preservation and limits of the proof

The final command was `.venv/bin/python -B -m unittest discover -v`, with bytecode writes disabled and the offline network tripwire on PYTHONPATH. **140 tests passed, zero failures, zero skips.** The 126 existing tests were not edited. New tests cover manifest facts, protected paths, unverified-run failure, exclusive export writes, unchanged prediction settings, Miami evidence and detection of injected parity mismatches. The final log is `cache/_parity/final_tests.log`.

The before/after hash audit covers **556 existing files**: **548 unchanged**, and exactly the eight authorized scripts changed. All **387 original cache files**, including SQLite, are byte-identical. Existing data, charts, docs, tests, config and `.gitignore` were preserved. See [baseline hashes](data/runs/season_extension_baseline_hashes.csv), [final hashes](data/runs/season_extension_final_hashes.csv), and [hash summary](data/runs/season_extension_hash_summary.json). `SEASON_EXTENSION_SPEC.md` was already untracked when this task began and remains unchanged.

This proves the final adapted 2025 pipeline reproduces fresh runs of the original git-HEAD scripts in the recorded environment. It does not prove another season’s coverage, substitute handling, data quality or Miami eligibility, nor reproducibility across different library versions. Pixel parity and a live exporter run were intentionally not attempted. The unverified 2024 gate stays closed until the separately approved export and audit.
