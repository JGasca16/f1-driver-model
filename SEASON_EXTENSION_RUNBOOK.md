# Running a season safely

The season extension passed exact 2025 parity and all 140 tests. See
[SEASON_PARITY_REPORT.md](SEASON_PARITY_REPORT.md) for the evidence and limits.
The statistical method is unchanged. **2024 is not ready to run:** its manifest
deliberately stops every pipeline command before season data is opened.

## What the manifest holds

`season_config.py` reads `seasons/{year}.json`. The manifest records the verified
calendar and entrant counts, qualifying advancement counts and disqualifications,
wet/dry race scope, explicit holdouts, teammate-period exceptions, chart choices,
and every season input/output location. It does not set new statistical weights
or thresholds. The algorithm identifier remains
`2025_teammate_rating_1_log_round_fix`, even for another data year.

The 2025 default paths and names are unchanged. Other seasons use only
`data/{year}/`, `charts/{year}/` and `cache/season_{year}/`; published filenames
include the year. Paths outside the allowlist, cross-season paths and escaping
symlinks are refused. There is no fallback to the 2025 files.

## Before a new season can run

1. Obtain separate approval for the network export/audit. None was performed
   in this task. The initial ingestion must establish facts before these gated
   pipeline commands can run; do not replace `UNVERIFIED` with guesses.
2. Verify the schedule, session availability, roster counts, session-specific
   entrants/substitutes, qualifying progression and disqualification registry.
   Audit lap times, compounds/ages, pit timing, deletion/status feeds, weather,
   finishing statuses and race-result coverage. Resolve singleton or
   between-session substitution schema needs separately before proceeding.
3. Determine wet/dry scope with the existing rules. Run the read-only
   `season_eligibility_audit.compound_pit_audit(laps, timing)` hook on Miami's
   own season records and save its evidence. Add a compound-conflict holdout
   only for a verified recurrence; an ambiguous audit needs review. The 2024
   holdout list starts empty. Do not apply reconstructed labels to pace inputs.
4. Fill and review every unverified manifest fact, including chart pairs,
   summary-event selection and whether a same-season legacy qualifying
   reference exists. An absent reference must never be replaced with 2025.
   The copied prediction config changes only its season and manifest reference;
   its frozen schedule must agree with the verified calendar.

## Commands and output order

All eight scripts accept `--season` (default `2025`), `--manifest` and `--offline`.
For an already verified, cached season, the order is results, qualifying rounds,
qualifying combination, dry/wet pace, ratings with sensitivity, prediction,
then charts. **These example 2024 commands currently stop at verification; they
are not permission to download data.**

```sh
.venv/bin/python test_fastf1.py --season 2024 --offline
.venv/bin/python qualifying_gaps_by_round.py --season 2024 --offline
.venv/bin/python qualifying_gaps_combined.py --season 2024 --offline --output-dir data/2024/combination_check_001
.venv/bin/python race_pace_dry.py --season 2024 --offline
.venv/bin/python race_pace_wet.py --season 2024 --offline
.venv/bin/python driver_rating.py --season 2024 --offline
.venv/bin/python prediction_test.py --season 2024 --offline --config prediction_test_config_2024.json
.venv/bin/python make_sanity_charts.py --season 2024 --offline
```

The combination check uses a fresh subfolder because the rating script also
combines qualifying and writes the canonical combined file. This avoids an
existing-output collision. The manifest is selected automatically by year;
`--manifest seasons/2024.json` makes that choice explicit.

Never overwrite a completed run. The exporter and qualifying/rating/chart
writers refuse existing files. Dry and wet repeats reserve numbered folders;
prediction always reserves a new run. Use new same-season output directories
where supported and explicitly review which files downstream stages read.
Do not assume an archived rerun silently replaces a canonical result.

## Verify a change

Run `.venv/bin/python -m unittest discover -v` offline. For another code change,
freeze fresh hashes, export its unmodified baseline source, copy the 2025 cache,
and rerun both versions in new isolated folders. `season_parity.py` compares CSV
bytes, declared JSON metadata and chart data without numerical tolerances.
Any mismatch stops release. Preserve all reference runs and the original cache.
