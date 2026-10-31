# Proposed public dashboard for the 2025 results

This is a proposal for review, not an implementation. It preserves the saved
ratings, intervals, prediction results and approved methods. No app, chart,
result file or deployment was created for this proposal, and no network was used.

The recommendation is a small static HTML/JavaScript site on GitHub Pages,
with charts prepared from the saved results, accessible tables and shareable
filters. Its purpose is to explain the work and its limits in about a minute,
then let interested readers inspect the evidence.

This proposal follows [README.md](README.md), the
[rating method](DRIVER_RATING_METHOD.md), the
[prediction method](PREDICTION_TEST_METHOD.md) and
[chart inspection notes](SANITY_CHECKS.md), checked against the saved files
listed in Section 5 and the four existing charts.

## 1. Audience and the first screen

Use the title **“2025 F1 teammate pace and prediction”** and this introduction:

> How did drivers perform relative to their actual teammates, and did earlier
> ratings add information beyond the next race weekend's qualifying?

Immediately below it, say **“One season. Nine separate teammate groups.
No cross-team ranking.”** The saved rating summary reports 21 drivers and nine
groups; show these as scope counts, not performance achievements.

The first screen should have two entry points:

- **Explore teammate ratings:** a group selector and a compact interval chart
  for one group. Default to the alphabetically first group, ALB+SAI, rather
  than choosing the largest apparent performance difference. Keep the sign
  explanation and “no clear gap” labels visible.
- **Inspect the prediction test:** the headline **“Inconclusive, leaning
  positive”**, the 95-pair/12-weekend sample, and the primary Brier difference
  **−0.0083 [95% interval −0.0257 to +0.0083]**. Explain that the interval includes
  zero and the target requires both teammates to finish.

For a recruiter, this communicates the question, the output and the uncertainty
without needing to read formulas. For a technical reader, put **Method and
limits**, **Source results** and **Repository** links in the same screen. Explain
that predictions use earlier rounds plus the current weekend's qualifying;
they are retrospective results, not live forecasts.

On a phone, stack these entry points vertically. Keep the limitations beside
their figures rather than hiding them in a tooltip. Use neutral colours,
system fonts and driver codes from the files; do not add portraits or badges
requiring additional data sources.

## 2. Pages and their saved fields

Use five navigation views within one site. Filters change presentation only;
they never refit a model, recalculate a gap, or change an interval. The precise
file allowlist is in Section 5. Here, **ratings**, **periods**, **diagnostics**
and **rating summary** mean the four corresponding `data/driver_rating_*`
files there. Prediction filenames refer only to `data/runs/prediction_001/`.

Every view also reads the proposed release metadata described in Section 5
for its season, source links, method identifiers and last-updated date.

### Overview

Show the two entry points above, with brief links to the other views. Use:

- Ratings: `season`, `driver`, `comparison_group`, `combined_rating`,
  `combined_ci_low`, `combined_ci_high`, `rating_units`, `confidence`,
  `rating_status`, `method_version`.
- Rating summary: `drivers`, `comparison_groups`, `confidence_counts`,
  `rating_status_counts`, `method_version`.
- Prediction `counts.csv`: `target`, `main_rows`, `main_weekends`,
  `main_exclusions`.
- Prediction `comparisons.csv`: `target`, `period`, `candidate`, `baseline`,
  `comparison`, `metric`, `difference`, `ci_low`, `ci_high`, `pair_count`,
  `weekend_count`.

Select `target=main_both_finish`, `period=main`, `comparison=primary`,
`candidate=M3`, `baseline=M2`, `metric=brier`. Do not calculate this difference
from rounded scores.

### Drivers within a teammate group

Show a separate group chart and a driver detail panel. Include the combined
interval, component ratings, actual signal weights and evidence counts. Keep
provisional status separate from confidence and direction.

Read these ratings fields in addition to the Overview fields:
`teams`, `teammates`, `teammate_changed`, `season_appearances`,
`qualifying_rating`, `dry_rating`, `wet_rating`, `qualifying_weight`,
`dry_weight`, `wet_weight`, `qualifying_valid`, `qualifying_eligible`,
`qualifying_effective_races`, `dry_valid`, `dry_eligible`,
`dry_effective_races`, `wet_valid`, `wet_eligible`, `wet_effective_races`,
`races_included`, `bootstrap_valid`, `dry_strict_count`, `dry_linear_count`,
`monaco_included`, `notes`, `source_files`.

Read diagnostics fields: `season`, `driver`, `signal`, `valid`, `eligible`,
`missing`, `coverage`, `effective_races`, `rating`, `median`, `missing_reasons`,
`warnings`, `single_race_ci_low`, `single_race_ci_high`, `single_race_round`,
`season_ci_low`, `season_ci_high`, `season_ci_reason`. These explain blanks
and whether an interval describes one wet race or a season. Do not invent an
interval for a component without one.

Parse `notes` as JSON, not as prose to scrape. All 21 current rows contain valid
JSON. Use `comparison_scope`, `ci_reason`, optional `wet_warning`, and
`coverage[signal].coverage`, `.missing`, `.missing_reasons`, `.warnings`.
Use `teammate_periods[]` for the visible seat-history breakdown:
`season`, `driver`, `period`, `team`, `teammate`, `round_start`, `round_end`,
and `signals[qualifying|dry|wet].mean`, `.valid`, `.eligible`.

The periods CSV supplies the matching detailed table through `season`,
`driver`, `period`, `team`, `teammate`, `round_start`, `round_end`, `signal`,
`valid`, `eligible`, `missing`, `coverage`, `effective_races`, `rating`,
`median`, `missing_reasons`, `warnings`. It has 78 signal rows for 26 directed
driver/team/teammate periods. The notes retain more precision than its displayed
three-decimal `rating`; validate agreement after rounding, not by exact equality
of the serialized numbers. Do not silently substitute one source for another.

For example, Lawson's panel shows rounds 1–2 at Red Bull Racing against VER,
then rounds 3–24 at Racing Bulls against HAD. Gasly's shows DOO in rounds 1–6
and COL in rounds 7–24. Each period shows separate qualifying, dry and wet
means and valid/eligible counts. There is no saved combined period rating or
period confidence interval; do not create one.

Doohan must visibly say **“Provisional: only 1 usable dry race out of 4 eligible
dry appearances.”** His saved interval does not upgrade that status.

### Race-by-race gaps

Offer group, actual teammate pair and signal selectors. Use separate qualifying,
dry and wet panels; never draw one continuous line mixing their units or methods.
Keep missing observations as breaks, with their saved reason available in the
table. Mark non-pairing rounds separately from a missing gap for an entered pair.

- Combined qualifying file: `round_number`, `race`, `team`, `driver`,
  `teammate`, `combined_gap`, `rounds_used`, `q1_gap`, `q2_gap`, `q3_gap`,
  `reason_code`. `combined_gap` is already in log-percentage points; read the
  named driver's row directly. Q1/Q2/Q3 gaps remain ordinary percentages.
- By-round qualifying file, for the round-details table: `round_number`,
  `race`, `team`, `driver`, `teammate`, `q1_gap`, `q1_reason_code`, `q2_gap`,
  `q2_reason_code`, `q3_gap`, `q3_reason_code`. Do not fall back to its older
  selected-gap columns. Its full roster also distinguishes entry from a blank.
- Dry final file: `round_number`, `race`, `team`, `driver`, `teammate`,
  `matched_laps`, `driver_clean_laps`, `teammate_clean_laps`, `final_gap`,
  `method_used`, `final_se_pp`, `final_confidence`, `reason_code`,
  `track_reliability_flag`, `disagreement_flag`. Use `strict_ci_low` and
  `strict_ci_high` when `method_used=strict`, or `linear_ci_low` and
  `linear_ci_high` when `method_used=linear`.
- Wet final file: `round_number`, `race`, `team`, `driver`, `teammate`,
  `matched_laps_2pct`, `wet_gap_2pct`, `wet_gap_se_pp_2pct`,
  `wet_gap_ci_low_2pct`, `wet_gap_ci_high_2pct`, `final_confidence`,
  `reason_code`, `wet_flag`. A labelled sensitivity drawer can also read
  `wet_gap_1pct`, `matched_laps_1pct`, `wet_gap_3pct`, `matched_laps_3pct`;
  it cannot replace the 2% primary result.

Dry and wet files contain one perspective per pair. Keep the stored `driver`
versus `teammate` direction and name it on every plot and row. The current
files consistently retain one direction for each pair. Do not negate a
percentage to manufacture the other direction, or calculate a reciprocal
inside the dashboard. A selected driver's detail may therefore link to a
race chart explicitly labelled from the other driver's saved perspective.
If a future file switches directions mid-series, break the series and flag
the source for review instead of silently joining it.

Prefer the saved 95% interval endpoints for new public race charts. If only
an SE is available, show **“SE: … percentage points; interval unavailable”**;
do not approximate a 95% interval. Qualifying has no saved per-race interval,
so its direction is a point estimate without an uncertainty claim.

### Prediction test

Use the content and field selections in Section 4. Default to the main target
and main scoring period. Put early results and retirement sensitivities in
clearly separate expandable areas, with a source link for group-stability checks.

### Method and limits

Use short, approved explanations linked to the repository's method documents.
These explanations are page content, not instructions to run the pipeline.
Read rating-summary `method_version`, `settings.signal_weights`,
`settings.reference_races`, `settings.monaco_multiplier`, `settings.resamples`,
`settings.seed`, `sources_sha256`; and prediction-config `specification`,
`season`, `rounds`, `target_rules`, `finisher_statuses`, `history`, `schedule`,
`models`, `rating`, `bootstrap`. Show precision-weight and eligibility details
from the approved method text without providing sliders to change them.
Read prediction-summary `config_sha256`, `source_sha256`, `script_sha256`,
`rating_script_sha256`, `qualifying_script_sha256`, `feature_correlation` for
the provenance drawer. Paths inside these objects are text, not files to open.

Keep these limitations visible: actual car and teammate affect the rating;
groups lack an opponent-strength adjustment; this is one exploratory season;
missing races are not zero gaps; Monaco is discounted but retained; wet evidence
is sparse; Miami has qualifying but no race-pace contribution; and the main
prediction sample selects both finishers. Link to the fuller method documents.

## 3. Sign, uncertainty and ordering rules

Every rating chart, table, tooltip and shareable view needs this local caption:

> Negative = faster than the actual teammate(s); positive = slower.
> Season ratings use log-percentage points and the teammate history shown.

For race-gap panels, replace the second sentence with the named driver's
perspective and the panel's units. A footer alone is insufficient: screenshots
and deep links must preserve the explanation.

Recommend alphabetical group order and alphabetical driver-code order within
each group. This is a deliberate presentation change from the inspection
chart's score order. It avoids turning a larger group's unequal opponent
histories into a local skill ranking. Do not show rank numbers, “best driver”
cards, a global score sort, or an all-driver rating chart sharing one ordering.
Search may take a visitor to a driver's group, not to a new global results list.

Use saved interval endpoints inclusively: when `low <= 0 <= high`, the primary
label must be **“No clear gap”**, regardless of the sign or confidence label.
For example:

> **NOR relative to PIA: No clear gap.** Rating −0.063 log-percentage points;
> 95% interval −0.189 to +0.042. Coverage confidence: high.

Do not describe Norris as faster in that case. The current crossing-zero
groups are ALB+SAI, BEA+OCO, BOR+HUL and NOR+PIA. High coverage confidence and
an unresolved direction can coexist.

When the interval is wholly negative, a two-driver group can say:

> **LEC relative to HAM: faster by about 0.27% in the combined pace measure.**
> Rating −0.270 log-percentage points; 95% interval −0.383 to −0.172.

Wholly positive intervals use “slower.” The plain-English percent is explicitly
approximate: small log-percentage values are approximately ordinary percentages.
Keep the exact saved log-unit number next to it. Do not present the approximation
as a measured lap or a predicted finishing margin. For missing intervals, say
**“Direction uncertain: interval unavailable”** and retain the point estimate;
for blank scores, **“Rating unavailable”**, never zero.

In three- or four-driver groups, refer to **“actual teammates in the periods
below”** rather than assigning the season score to a chosen opponent. Keep
this caution above the chart and period table:

> These ratings pool different teammate periods without adjusting for opponent
> strength. Do not subtract two season ratings to estimate a head-to-head gap.

Show the actual links for COL+DOO+GAS and HAD+LAW+TSU+VER. A connection through
another driver does not mean every pair raced as teammates. The notes-based
period cards are visible by default in those groups, not buried in a tooltip.

All pages have a compact visible provenance strip: **season, source file(s),
rating method version, prediction specification where relevant, and “Results
release last updated: YYYY-MM-DD.”** Expand it for run ID and hashes. Repeat
the relevant source and version in chart captions and downloadable views.

## 4. Present the prediction test honestly

Use **“Inconclusive, leaning positive”** as the result heading, followed by:

> The point estimates favour adding the earlier rating, but every primary
> difference interval includes zero. This test does not establish an improvement.

Put **“Main target: both teammates finished, including lapped finishers”**
beside the sample and every main-result chart. Add **“Conditional on both
finishing; not unconditional pre-race accuracy.”** Qualifying is already known
when these predictions are made. There are 95 scored pair-races across 12
weekends in rounds 13–24, with 25 exclusions from 120 possible pairs. These
are sample counts, not estimates needing invented confidence intervals.

The primary view shows M2 (current qualifying) beside M3 (earlier rating plus
current qualifying), then their saved paired difference:

| Metric | M2 [95% interval] | M3 [95% interval] | M3 minus M2 [95% interval] |
| --- | --- | --- | --- |
| Brier score; lower is better | 0.1748 [0.1501, 0.1986] | 0.1665 [0.1391, 0.1938] | −0.0083 [−0.0257, +0.0083] |
| Accuracy; higher is better | 72.6% [65.2%, 78.9%] | 75.8% [70.5%, 81.8%] | +3.16 pp [−3.06, +10.47] |
| Log loss; lower is better | 0.5208 [0.4562, 0.5805] | 0.4968 [0.4276, 0.5652] | −0.0240 [−0.0621, +0.0129] |

Every score or difference displayed, including overview cards and sensitivity
tables, keeps its interval beside it. A difference chart has a zero line and
labels which direction favours M3. Do not use an improvement badge or choose
a more favourable metric as the headline. Explain Brier as a probability-error
score; accuracy alone discards probability quality.

Exact source selections and fields:

- `metrics.csv`: filter `target=main_both_finish`, `period=main`. Read
  `method`, `pair_count`, `weekend_count`, `excluded_pair_count`,
  `exclusion_reasons`, `ties`, `fallback_rows`, `brier`, `brier_ci_low`,
  `brier_ci_high`, `accuracy`, `accuracy_ci_low`, `accuracy_ci_high`,
  `log_loss`, `log_loss_ci_low`, `log_loss_ci_high`. Default to M2 and M3;
  the expanded table also shows M1, qualifying, grid, previous, head_to_head
  and chance. Distinguish M2's gap-based probability from the simple qualifying
  pick; the latter is not official qualifying position.
- `comparisons.csv`: select the primary M3/M2 rows as on the Overview, for
  `metric=brier`, `accuracy`, `log_loss`. Read the fields listed there.
  Display stored differences, not subtractions of rounded metric levels.
- `counts.csv`: `target`, `eligible_rows`, `initial_training_rows`,
  `initial_training_weekends`, `main_rows`, `main_weekends`, `main_exclusions`,
  `early_first_round`, `early_rows`, `early_weekends`, `early_fallback_rows`.
- `baseline_winners.csv`: `target`, `period`, `metric`,
  `best_simple_baselines`, `value`, `exploratory`. It supplies names for the
  expanded baseline discussion, not standalone score cards without intervals.
  Any winning baseline's scores still come from `metrics.csv`. Best observed
  baseline selection is exploratory, not the primary M3/M2 comparison.
- `group_stability.csv`: offer the original file as a source download only;
  read no fields into a numerical figure or table. It contains exploratory
  scoring omissions without refitting, and no saved uncertainty intervals.
  Explain that limitation beside the link rather than inventing intervals or
  displaying its point estimates as interval-bearing evidence.
- `eligibility.csv`: `target`, `pair_id`, `round_number`, `driver_a`,
  `driver_b`, `eligible`, `reason_code`, `all_reasons`. Use this for the
  exclusion browser. Multiple `all_reasons` may overlap; do not sum them as
  disjoint counts. The main exclusion counts already appear in `metrics.csv`.
- `predictions.csv`, loaded only on opening the audit table: `target`,
  `period`, `method`, `pair_id`, `round_number`, `race`, `team`, `driver_a`,
  `driver_b`, `probability`, `outcome`, `status_a`, `status_b`,
  `prior_rating_a`, `prior_rating_b`, `rating_difference`,
  `qualifying_advantage`, `feature_source_max_round`, `training_rows`,
  `training_max_round`, `fallback_reason`. Label the stored probability as
  **“Probability A finishes ahead of B.”** Do not reverse its perspective.

The last table is an audit, not a live prediction tool. The saved feature
differences use positive values to favour A; that differs from the negative-is-
faster rating display and must be stated in the technical column help.
Historical outcomes and statuses are audit fields, not evidence of model inputs.

Target and period selectors must filter all tables consistently. Keep
`all_starters`, `no_double_retirement`, `early` and `early_fallback` separate
from the main result. Never pool their samples or choose a target after seeing
its score. Use the saved intervals for each corresponding selection.

Explain the earlier-round rebuild, current qualifying feature, 2,000 whole-
weekend bootstrap draws with seed 42, and that models were not refit inside
those draws. The intervals do not capture every source of training uncertainty
or persistent teammate-group dependence. This is one exploratory season with
roughly nine teammate groups, not 95 independent driver-skill experiments.

## 5. Saved-data layer and release process

Bundle exactly these 17 existing result/config files for the initial release:

1. `data/driver_rating_2025.csv`
2. `data/driver_rating_teammate_periods.csv`
3. `data/driver_rating_signal_diagnostics.csv`
4. `data/driver_rating_run_summary.json`
5. `data/2025_qualifying_gaps_combined.csv`
6. `data/2025_qualifying_gaps_by_round.csv`
7. `data/race_pace_dry_final.csv`
8. `data/race_pace_wet_final.csv`
9. `data/runs/prediction_001/metrics.csv`
10. `data/runs/prediction_001/comparisons.csv`
11. `data/runs/prediction_001/counts.csv`
12. `data/runs/prediction_001/summary.json`
13. `data/runs/prediction_001/prediction_test_config.json`
14. `data/runs/prediction_001/baseline_winners.csv`
15. `data/runs/prediction_001/group_stability.csv`
16. `data/runs/prediction_001/eligibility.csv`
17. `data/runs/prediction_001/predictions.csv`

These total **1,701,233 bytes** before compression. The optional prediction
audit table is most of that bundle and should load on demand. No file glob or
recursive copy of `data/` belongs in the site build.

Do not bundle raw timing feeds, lap exports, telemetry, position data, race
results exports, status-cache extracts, SQLite databases, anything under
`cache/`, the full bootstrap draws, superseded research outputs, or the
experimental 2024 pilot. Source paths in summaries and `source_files` are
provenance labels, never permission to load those files. No FastF1 package,
pipeline import, model fit or network data fetch is needed in the app.

Filtering, joining saved rows, reading JSON notes, choosing a saved interval,
formatting units and drawing chart positions are presentation operations.
The app and its presentation build must not calculate ratings, gaps, SEs,
intervals, prediction probabilities, performance metrics, correlations,
alternative confidence labels or new aggregate results. Missing values stay
missing. No points or wins are inputs.

For a future implementation, propose one additional, small editorial metadata
file, `dashboard_data/releases.json`, created only after approval. It is not
created by this task. It would list each available release's `season`,
`release_id`, `published_at`, `results_last_updated`, `rating_method_version`,
`prediction_specification`, `prediction_run_id`, `rounds`, `groups`, `sources`,
`source_sha256`, `method_links`, `repository_url`, `license_url`, `data_credit`
and approved explanatory text. The group list and scope counts must be checked
against the saved summaries. It adds provenance, not new analytical results.

Neither current run summary contains a generation date. Therefore do not label
a filesystem modification time, today's date, season-end date or runtime as the
data-update date. Until the owner verifies a release date, show **“Results last
updated: not recorded; release date pending confirmation.”** Once confirmed,
show that date everywhere, separately from the website's publication date.

Package byte-identical copies of the allowed source files under an immutable
season/release folder, keeping their filenames and a source-to-package path
mapping. A future release adds another folder and metadata entry. The site
discovers its season selector from that entry, without editing page code or
assuming 24 rounds, 21 drivers, particular groups, or particular run numbers.
If prediction results are absent for a season, say so and disable that panel.

The four current PNGs in `charts/` were inspected as layout references. Keep
them in the repository, but do not embed them unchanged as the public interface:
the group chart lacks explicit “no clear gap” labels, the all-driver scatter
does not keep drivers inside separate group views, and the race plot uses
one-SE bars rather than the proposed saved 95% endpoints. Prepare new
presentation-only chart assets from the allowlisted values during the later
build. Their accessible tables and captions must pass the same checks as the
interactive view. No old PNG or source file needs editing.

## 6. Technology and hosting

The comparison below is a planning recommendation based on the saved-data
requirements. Hosting plans, prices and limits were not checked online in
this task; confirm them before deployment.

| Consideration | Streamlit | Static HTML/JavaScript with prepared charts on GitHub Pages |
| --- | --- | --- |
| Setup effort | Fast for an initial Python prototype; requires a Python environment and hosted app service. | More initial work for layout, chart preparation and browser filters; then a simple file-based release. |
| Hosting cost | A free community-hosting option may suffice, subject to current limits; paid hosting is another option. | Expect no hosting charge for a public repository using standard Pages hosting, subject to current terms. A custom domain is optional and may cost money. |
| Load speed | A running server can be responsive; startup or sleeping-app delays are a possible first-visit cost. | HTML and prepared charts can appear immediately without a Python server; defer the audit CSV. Actual speed must be measured after building. |
| Mobile layout | Built-in responsive elements help, though dense widgets and wide tables need care. | More control over stacking, labels and chart sizing; that also means more layout work. |
| Sharing | A public URL works; preserving the exact selection needs URL-state support rather than session state alone. | A public URL plus hash/query parameters can preserve season, page, group, driver and pair. Hash routes avoid separate-page routing requirements. |
| Interactivity | Convenient Python widgets and callbacks, but every callback would still have to be read-only presentation. | Group/driver selection, tooltips, tables and filtering work locally. Pre-built chart variants can be selected without an analytics backend; arbitrary new analyses are outside scope. |
| Future season selector | Read release metadata and select the corresponding saved tables; no model work in the app. | Read the same release metadata and load that season's assets/results; no change to page code for a compatible release. |

Recommend the **static option** because the audience opens a portfolio link,
the result set is small, and the dashboard has no permitted server-side
analysis. A fast initial explanation, stable links and reproducible publication
matter more here than rapid experimentation with Python widgets.

Use a small amount of local JavaScript, local chart assets and system fonts;
avoid third-party chart CDNs or live APIs. For chart preparation, emit accessible
SVG/HTML from saved values, not newly calculated statistics. URL filters must
select allowlisted content, never accept arbitrary file paths. Provide an HTML
table alternative and text explanations when a chart cannot load. Streamlit
remains a reasonable alternative if faster initial development matters more
than first-visit speed and layout control.

## 7. Disclaimer, credit and repository links

Put **“Unofficial, independent project”** near the title. Every page's footer
should include the full existing disclaimer:

> This is an unofficial, independent project. It is not affiliated with or
> endorsed by Formula 1, the FIA or any team. Formula 1 and team names are
> trademarks of their respective owners.

Credit **FastF1 and the official timing feeds it wraps** in that footer and
the Method and limits page. Link to `https://docs.fastf1.dev/`. Use neutral
text and colours; no official logos, team badges, official typefaces or
branding assets.

Link the header and footer to the repository,
`https://github.com/JGasca16/f1-driver-model`, and link **MIT code license**
to its `LICENSE` file. The address is taken from the local Git remote; it was
not checked over the network. Repeat the existing scope statement: the MIT
license covers the code only and grants no rights to the underlying race and
timing data, which remain subject to their own terms. Review publication of
the proposed derived-data bundle before a public deployment.

## 8. Proposed automated checks

These are future build requirements, not tests implemented by this proposal:

- Every rendered rating/gap container, tooltip, prepared chart and shared view
  has its sign, units, named perspective and source explanation. Check direct
  links as well as navigation from the home page.
- Every driver appears inside the correct saved comparison group. No global
  rating sort or rank column is rendered. Use a fixture whose scores would
  produce a different global order to catch accidental flattening.
- Zero-crossing and zero-touching intervals show exactly **“No clear gap”**
  and no driver-specific faster/slower claim. Missing intervals and missing
  scores use their separate labels. Test high-confidence crossing-zero cases
  and Doohan's provisional case.
- Compare every displayed numeric field with the specified source cell after
  its declared display formatting. Ratings use the saved three decimals;
  prediction scores use four decimals, accuracy percentages one decimal and
  accuracy differences two. Expose the original stored value in an accessible
  details table/download. Rounding is not permission to change source values.
- Verify exact selectors for the 95-pair/12-weekend main sample and saved M3/M2
  differences. Every estimated prediction score/difference keeps its matching
  saved interval; no early or sensitivity row leaks into the main view.
- Check period cards against `notes.teammate_periods` and the periods CSV at
  the CSV's precision. Both larger groups always show the subtraction caution.
  Malformed JSON or inconsistent periods stop publication instead of dropping
  the warning or inventing an opponent.
- Dry/wet charts retain the stored driver perspective, use the interval for
  the selected saved method, preserve missing-round breaks and show Monaco's
  warning. No qualifying log gap is converted twice. Wet and dry remain
  separate; no coverage cell is labelled as having both race-pace signals.
- Hash packaged source copies and validate their declared versions. The
  current canonical rating, qualifying, dry and wet files match the hashes
  in the saved prediction summary; this was checked for the proposal. Missing
  or inconsistent sources fail the release rather than choosing a newer file.
- Enforce the explicit data-file allowlist in the loader and package builder.
  Block traversal, absolute paths, arbitrary URLs, glob loading and opening
  provenance paths. Inspect the published artifact for forbidden cache/raw
  files. Block external data requests and mock pipeline entry points to fail
  if called. Permit only local site assets/results and the approved metadata.
- Every page shows source, method version and a verified last-updated date
  or its honest missing-date state. Check keyboard access, readable mobile
  layout, non-colour labels, link targets and copied filter URLs.

## 9. A second season and a later career scale

Keep season, rating type, units, direction, comparison scope and method version
in release metadata. Add 2024 only once its data and approved outputs exist;
it is not runnable from the current pilot. Do not create an empty selector
option that looks like a completed season, carry 2025 roster groups into it,
or suggest ratings across seasons have already been calibrated.

A future career rating should occupy a separate **Career** view and its own
data contract: connected population, score, 0–100 units, direction, uncertainty,
coverage and approved method version. The same card/table framework can be
reused, but its sign text and scope must come from that rating type. Do not
rescale these teammate gaps to 0–100, join disconnected groups, or put a career
leaderboard into the season view before a method supports it. Season ratings
and a future career score are different measures and need separate explanations.

## 10. Suggested build order and effort

Budget **six build prompts**, after the open decisions below are approved:

1. Freeze the allowed-file contract, release metadata, verified date and
   packaging checks. Validate the saved inputs without running any pipeline.
2. Build the static navigation, provenance strip, credit/footer and Overview.
3. Build group/driver views, uncertainty labels, notes-based teammate periods
   and provisional/missing-data states.
4. Build race-by-race charts and accessible tables, retaining saved directions,
   saved intervals and separate signals.
5. Build the prediction page, exact main-row selectors and clearly separated
   audit/sensitivity drawers. Wire shareable filter URLs.
6. Run data/display and browser checks, review phone/desktop screenshots,
   check the complete publication artifact, and prepare a concrete deployment
   preview for approval.

These are work packages, not a guarantee that each takes one interaction.
Allow another one or two prompts if visual or accessibility review finds
issues. Public deployment follows review; this proposal authorizes no build
or publication.

## Open decisions for the project owner

1. Approve the static GitHub Pages recommendation, or prefer Streamlit for
   the faster initial Python build?
2. Approve the five-view scope and alphabetical ordering within groups,
   including the ALB+SAI default example?
3. Approve the approximate percent wording beside exact log-unit ratings,
   the “No clear gap” rule and the visible larger-group period cautions?
4. Approve the 17-file public bundle and the on-demand prediction audit,
   subject to checking publication rights for the derived results?
5. What verified results-release date should appear, and should the site show
   the explicit missing-date state until that is confirmed?
6. Approve fixed saved perspectives for dry/wet race charts, the use of saved
   95% intervals, and separate advanced sensitivity/stability sections?
7. Approve the six-prompt build order and a reviewed preview before any
   public deployment?
