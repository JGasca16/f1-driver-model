# Dashboard local review

The four views are Overview, Drivers, Prediction test and How it works.
Race-by-race gaps remain deferred. Only files in this directory changed in
this redesign. Saved data, calculations and the release package are unchanged.

Serve the existing docs directory from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m http.server 8765 --bind 127.0.0.1 --directory docs
```

Visit `http://127.0.0.1:8765/dashboard/`. Stop the server with Ctrl-C.
Use an HTTP server instead of opening the HTML directly, so the local data
requests and SHA-256 checks work. The relative data URLs also work below a
project prefix.

## Files and saved inputs

| File | Purpose |
| --- | --- |
| index.html | Navigation, dark default, theme control and accessible data dialog |
| styles.css | Graphite and light palettes, mobile layout, focus states and charts |
| content.js | Owner copy deck with a source document and section for every block; original exact excerpts |
| data.js | Unchanged file and column allowlist, parser, hashes and saved-data validation |
| views.js | Saved-value tables, group charts, prose, source references and data previews |
| app.js | Navigation, guarded theme storage and on-demand data previews |
| test_dashboard.cjs | 31 offline JavaScript checks |
| test_dashboard.py | 8 offline file, source, scope and package checks |
| test_pages_subpath.py | 3 unchanged relative-path and landing-page checks |

All data comes from the fixed sibling release package. Initial loading reads
release metadata, ratings, teammate periods, signal diagnostics, rating summary,
metrics, comparisons, counts, prediction summary, configuration and baseline
winners. The exclusions and prediction audit load only when opened. Group
stability remains an explicit download as requested in the copy deck.

Data buttons now open readable tables or JSON in a dialog, with a separate
Download file link. CSV previews show only the columns already allowed for the
pages. Ratings, period and diagnostic previews use separate alphabetical tables
for each comparison group. No recorded qualifying lap-time columns are read. Downloads preserve the
original file. The dialog uses native keyboard focus handling and Escape.

| View | Saved files |
| --- | --- |
| Overview | driver_rating_2025.csv, driver_rating_run_summary.json, comparisons.csv, counts.csv, releases.json |
| Drivers | driver_rating_2025.csv, driver_rating_teammate_periods.csv, driver_rating_signal_diagnostics.csv |
| Prediction test | metrics.csv, comparisons.csv, counts.csv, baseline_winners.csv, summary.json, prediction_test_config.json; eligibility.csv and predictions.csv on demand |
| How it works | rating and prediction summaries, saved configuration and prose from the method documents |

The by-round qualifying and race-gap files remain outside the page input list.
Manifest paths are provenance text, never paths supplied to the loader.

## Copy and evidence

The owner supplied the first-person copy deck. Each paragraph in content.js
records its supporting document and section, and each rendered paragraph has
a source tag. Sources are grouped at section ends instead of attached to every
sentence. The dashboard specification is not yet tracked, so it is named as a
source without offering a GitHub link that might fail. Existing method documents
retain their repository links; those remote destinations were not checked.

The only approved correction to the deck is:

> Every 95% range for the differences includes zero, so this could be chance.

Score intervals themselves do not all include zero. Difference intervals do.
The source difference, including its interval, is displayed directly; rounded
scores are never subtracted to create a new result.

Original technical excerpts remain unchanged in content.js and are checked
against their local documents. Formulas and thresholds are in Exact rules;
technical names and JSON sit inside nested Exact values. Raw filenames occur
only in Data lines or Exact values. The full source map is in content.js.

## Interpretation rules retained

Group selection filters before alphabetical ordering. Charts reject mixed
groups, and each ratings table belongs to one comparison group. There are no
rank numbers. Inclusive zero-crossing ranges display No clear gap. Saved status,
confidence, interval endpoints, weights and coverage remain unchanged. Doohan
stays provisional. The caution for the larger groups precedes their charts.

Every chart and table block gets one sign caption. Green and amber have arrows
and words; a neutral result has a dot and words. Both theme palettes pass the
4.5:1 text-contrast check on the page surfaces. Theme storage is guarded, so a
browser that disallows storage still works. Auto follows the system palette;
a first visit defaults to Dark.

The legal disclaimer comes unchanged from releases.json. No external fonts,
assets, libraries or background requests were added. Ordinary GitHub, method,
license and FastF1 links require deliberate navigation by the visitor.

## Additional visible strings for review

These short interface labels supplement the supplied deck. Saved values, raw
field headers in Exact values, source section titles and the required legal
disclaimer are copied from their sources rather than new prose.

- Navigation and loading: “Skip to content”; “Main navigation”; “Loading saved results…”;
  “JavaScript required for saved-data views.”; “Saved data could not be loaded.”
- Preview: “Saved data”; “Close”; “Download file”; “Fields used by this page.”
- Source controls: “Data:”; “Where this text comes from”; “License”.
- Source titles: “Dashboard specification”; “Project overview”; “Driver rating method”;
  “Dry race method”; “Wet race method”; “Prediction test method”; “Method document”.
- Chart axes: “faster than teammate”; “slower”; “0 = same as teammate”.
  These were explicitly requested in the appearance instructions.
- Missing interval: “Direction unclear”.
- Components and periods: “Saved values”; “Saved component details”; “{driver} · components”;
  “Rounds {first} to {last}”; “{driver} / {teammate}”; “{group} ratings and 95% ranges”.
- Models: “Earlier ratings (M1)”; “Qualifying pick”; “Grid pick”; “Previous race”;
  “Head-to-head record”; “Chance”.
- Separate reports: “Both finished”; “All starters”; “Exclude double retirements”;
  “Main period”; “Early season”; “Early fallback”; “Race selection”; “Period”.
- Extra tables: “Model”; “Signal”; “Saved scores and 95% ranges”; “Method”; “Metric”;
  “Stored value”; “Stored interval low”; “Stored interval high”; “Saved scores”;
  “Comparison”; “Stored difference”; “Saved differences”; “M3 minus M2”.
- Exclusions: “Round”; “Reason”; “One or both retired”; “No usable qualifying gap”;
  “Did not start”; “Disqualified”; “See exact values”; “Open to view the saved rows.”
- Audit: “Positive feature differences favour the first driver.”;
  “Probability A finishes ahead of B”. The first sentence follows the prediction
  audit orientation described in the dashboard specification.
- Stability download: “Download group_stability.csv”, inside its Data line.
- Document titles: “Overview · 2025 F1 teammate pace”; “Drivers · 2025 F1 teammate pace”;
  “Prediction test · 2025 F1 teammate pace”; “How it works · 2025 F1 teammate pace”.

All added interface strings are under 15 words. The table headers, formula text,
method identifiers and raw JSON inside Exact values are saved technical text.

## Verification commands

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/cache/_parity/offline_guard" .venv/bin/python -B -m unittest discover -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/cache/_parity/offline_guard" .venv/bin/python -B -m unittest discover -s docs/dashboard -v
node docs/dashboard/test_dashboard.cjs
```

The nested Python tests need their own discovery command. JavaScript tests use
only Node built-ins, mocked HTTP and saved package bytes. This environment used
the available Node tool runtime because Node is not on the shell path; nothing
was installed.

Before this redesign: 203 tests, comprising 170 root Python, 11 dashboard Python
and 22 JavaScript. After: 212, comprising the same 181 Python and 31 JavaScript.
All original checks remain, with outdated copy expectations replaced by checks
for the approved text, source tags, saved numbers and interpretation rules.

The local verification returned 25 successful responses: four view URLs, five
assets, fourteen data URLs and the landing/dashboard entries. Response bodies
matched the current files. Native Chrome review checked the four views, the
data dialog, Escape focus return, both palettes and a 390-pixel method layout.
The browser connector was unavailable, so native controls were used instead.
External destinations were not visited.
