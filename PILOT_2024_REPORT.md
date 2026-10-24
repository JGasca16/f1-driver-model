# 2024 two-round network pilot

**Stopped on repeated HTTP 401 errors. No qualifying or race session completed.**
The pilot did not calculate gaps, classify races, rate drivers, run predictions
on pilot data, or change the season manifest. There is no full-season export
approval and no further download was attempted after the failure.

## Scope and preflight

FastF1's 2024 schedule verified the first two non-testing events as:

1. Round 1: **Bahrain Grand Prix**.
2. Round 2: **Saudi Arabian Grand Prix**.

The schedule was obtained through `fastf1.get_event_schedule(2024,
include_testing=False, backend="fastf1")`. The schedule metadata necessarily
contains the season calendar; no session outside the approved first two rounds
was requested. No 2026 data was accessed.

Before downloading, `git check-ignore cache/season_2024/` returned
`cache/season_2024/`. Free disk space was **888,837,554,176 bytes
(888.84 GB)**, above the fixed 2 GB minimum. The new cache
was empty before initialization. Both FastF1's parsed cache and its HTTP/status
SQLite were pointed only at `cache/season_2024/`.

The command ran in a fresh shell with the old network tripwire removed:

```sh
env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B season_pilot_export.py --download
```

The new pilot-specific request guard permitted only the FastF1 2024 schedule,
main Q/R timing feeds for the two verified rounds, and their FastF1
Ergast/Jolpica qualifying/results/first-lap endpoints. The latter first-lap
endpoint is part of the approved race loader. No hand-written HTTP data request
was used. Downloads were sequential. Requests had at most three retries, with
1-, 2- and 4-second backoff; adapter-level retries were disabled. The script
checked the 200,000,000-byte cache limit and 900-second session limit every
quarter-second and at request boundaries.

Qualifying's intended parameters were `laps=True, telemetry=False,
weather=False, messages=True`. Races used `laps=True, telemetry=False,
weather=True, messages=True`, matching the dry loader and covering the wet
loader's required inputs too. No telemetry, position, practice or sprint data
was requested. Qualifying weather is intentionally not requested by the
approved qualifying loader; this pilot does not silently change that setting.

## Download measurements

The first session request was Bahrain qualifying's `SessionInfo.jsonStream`.
It returned **HTTP 401 Unauthorized on the initial attempt and all three
retries**. The script then stopped, rather than attempting an alternative
endpoint or continuing to race data. The cause of the authorization response
was not established. No credentials were supplied or changed.

| Step | Cache growth before raw exports/log | Elapsed time | Outcome |
| --- | ---: | ---: | --- |
| Empty SQLite initialization | 24,576 bytes | Not timed separately | Local cache overhead |
| 2024 schedule | 12,288 bytes | 0.115 s | Loaded and checked |
| Round 1 Bahrain Q | 0 retained bytes | About 7.356 s | Four failed HTTP attempts; stopped |
| Round 1 Bahrain R | Not attempted | Not measured | Stopped before this session |
| Round 2 Saudi Arabia Q | Not attempted | Not measured | Stopped before this session |
| Round 2 Saudi Arabia R | Not attempted | Not measured | Stopped before this session |

Total measured pilot elapsed time was **7.471 seconds**.
The partial Bahrain duration is total time minus schedule time and therefore
also includes the small session-construction overhead; it is not a successful
session-download benchmark. No round completed, so neither round has a valid
completed-round timing.

The cache occupied **36,864 bytes before writing the run record**:
24,576 bytes of initial SQLite overhead + 12,288 bytes of schedule
cache growth + 0 retained session bytes. After writing the run record, its
size was **39,495 bytes (0.039495 MB)**. The additional
2,631 bytes are local diagnostic JSON, not downloaded timing data.
Neither the size limit nor the time limit was reached.

These figures use directory growth as requested. They are **not wire-byte
measurements**: HTTP headers, failed-response bodies, compression, SQLite
allocation and parsed/exported copies make network transfer differ from disk
growth. In particular, zero retained session bytes does not mean the four
failed requests transferred zero bytes.

The exact request attempts and timings are retained locally in
`cache/season_2024/pilot_exports/2024_pilot_run.json`. Only the schedule request
succeeded. No Jolpica result/status request was reached.

## Completeness results and named issues

**0 of 4 sessions loaded; 0 of 2 rounds completed.** The counts file
[data/2024/pilot_completeness.csv](data/2024/pilot_completeness.csv) contains the
schema header and **zero audit rows**. An empty audit is not a clean-data result:
none of the session checks below could run. Missing pilot evidence must not be
reported as zero missing fields or zero affected drivers.

| Required check | Pilot result |
| --- | --- |
| Opening-round calendar | Verified: Bahrain, Saudi Arabia, rounds 1 and 2 |
| Actual Q/R session data presence | Unverified: first session load failed |
| Entrants per team in each Q and R | Unverified; no driver/result feed loaded |
| Unique driver identities and driver/lap keys | Unverified |
| Lap-time positivity and finite values | Unverified |
| Q1/Q2/Q3 partitions, overlap and unpartitioned laps | Unverified |
| Required lap fields and session boundaries | Unverified |
| Track-status and race-control-message fields | Unverified |
| Deleted-lap flag coverage | Unverified |
| Compound, tyre-age and stint missingness | Unverified |
| Race weather at both ends and internal gaps | Unverified |
| Official finishing status cache format and contents | Reader layout inspected in code; no pilot status response available to validate |
| Race-result/status driver and position agreement | Unverified |
| Substitutes or session/round seat changes | Unverified; cannot conclude that there were none |

The script retains every loaded lap before filtering and, on a successful
future attempt, counts the required fields, duplicates, missing/invalid values,
qualifying partitions, weather coverage and result/status agreement. Weather
coverage counts use the existing 120-second edge and 180-second internal-gap
limits, without classifying the race. Natural blanks such as pit timestamps
on a non-pit lap or untimed qualifying attempts are not automatically declared
errors. No lap filter was run in this attempt.

No entrant list can be supplied from this download. Neither qualifying-to-race
changes nor round-1-to-round-2 changes can be established. These require actual
session entrants, not guesses from the opening-season lineup.

Named issues are: (1) repeated HTTP 401 on Bahrain Q session info; (2) all four
session completeness audits unavailable; (3) finishing statuses/cache-layout
compatibility not verified on pilot data; and (4) the pre-existing test's
no-2024-directory assumption conflicts with an authorized pilot, as below.

## Estimate for the remaining season

**A measured estimate cannot be revised from this attempt.** There are zero
completed round downloads, and the schedule is shared overhead rather than a
representative weekend payload. The intended arithmetic after a successful
pilot is:

- Mean weekend bytes = successful two-round cache/export growth / 2.
- Remaining 22-round storage estimate = 22 × mean weekend bytes.
- Mean weekend elapsed time = sum of the two completed-round durations / 2.
- Remaining time estimate = 22 × mean weekend elapsed time.
- Full-season estimate = schedule/initialization overhead + 24 × mean weekend cost.

Here the number of completed rounds is **0**, so a measured mean would divide
by zero. Multiplying the 7.47-second failure or the schedule's 12,288 bytes by
12 would be misleading. Moreover, all 24 rounds' session data still needs
exporting; the nominal “remaining 22” projection assumes two successful pilot
rounds, which did not occur.

The earlier planning allowance of roughly 0.1–1 GB transfer, 0.3–1 GB storage
and 20–90 minutes remains an **unvalidated planning range**, not a new pilot
finding. This failed pilot provides no basis to narrow it. Even a successful
two-round pilot would not prove availability, roster handling, weather quality,
source corrections, Miami eligibility or throughput for the other 22 rounds.
A retry or a full export is not being run as part of this report.

## Requirements and tests

Created [requirements.txt](requirements.txt); no requirements file existed,
so `requirements_pinned.txt` was unnecessary. `pip freeze` and installed-package
metadata confirmed all requested versions: FastF1 3.8.3, pandas 2.3.3, NumPy
2.5.4, SciPy 1.18.1 and matplotlib 3.11.2. Python is 3.14.7, also named in the
requirements comment. Nothing was installed or upgraded.

The complete existing test suite was run with the offline socket/DNS tripwire:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/cache/_parity/offline_guard" .venv/bin/python -B -m unittest discover -v
```

**140 tests ran: 139 passed and 1 failed, with no skips.** The failure is
`test_season_extension.SeasonExtensionTests.test_all_eight_cli_commands_stop_before_unverified_data`,
at its assertion that `data/2024/` must not exist. The next assertion also
assumes `cache/season_2024/` must not exist. Both directory assumptions predate
this explicitly approved pilot. All eight commands still rejected the
unverified manifest before that assertion was reached. Tests were not edited,
expectations were not relaxed, and the pilot directories were not hidden to
make the test pass. A future separately authorized test correction should
check that a rejected command creates or changes no data, instead of asserting
that an authorized pilot's directory cannot exist. The test log is
`/tmp/pilot2024-tests.log`.

## Preservation and git status

SHA-256 hashes were captured before creating the pilot files and checked after
the downloads and tests. **All 13,643 pre-existing files were unchanged**,
including the virtual environment and **1,022 existing cache/parity files**.
Git's internal metadata was excluded from this working-tree hash inventory.
The original `cache/fastf1_http_cache.sqlite` hash remains:

```text
f4e23b81a30692173af8312dc6d7032a46327820ff2d3276d5009914b0fab597
```

Every 2025 file, existing script, test, document, config and `.gitignore` was
preserved. `seasons/2024.json` retains every `UNVERIFIED` value. No full-season
export, analysis or reclassification was performed.

`git ls-files cache` returned no paths: nothing under `cache/` is tracked.
`git check-ignore cache/season_2024/fastf1_http_cache.sqlite` confirmed the new
SQLite is ignored. Final working-tree additions are only:

```text
?? PILOT_2024_REPORT.md
?? data/2024/
?? requirements.txt
?? season_pilot_export.py
```

The `data/2024/` addition contains only `pilot_completeness.csv`. Raw downloads
and the run record stay under the gitignored `cache/season_2024/`. Existing
files have no modifications.
