# Dashboard column inventory — owner-reviewed release

Flags: 10 kept by owner decision; 16 approved safe; 0 still blocked.

The 10 named qualifying columns hold recorded qualifying lap times in seconds. Their contents are kept byte-for-byte, with no removal or transformation. Finishing positions and statuses in predictions.csv are also kept unchanged.

The original detection rule remains in force. Approvals match the exact source path and exact column or JSON path; every other flagged field blocks packaging.

| Source file | Column / JSON path | Owner decision | Detection flag |
| --- | --- | --- | --- |
| data/driver_rating_run_summary.json | $.runtime_seconds | approved safe | time-like header |
| data/2025_qualifying_gaps_by_round.csv | driver_time_seconds | kept by owner decision | time-like header; numeric value in inclusive 60–130 range; examples: 76.863000, 76.112000, 76.453000 |
| data/2025_qualifying_gaps_by_round.csv | teammate_time_seconds | kept by owner decision | time-like header; numeric value in inclusive 60–130 range; examples: 76.112000, 76.863000, 76.483000 |
| data/2025_qualifying_gaps_by_round.csv | driver_best_qualifying_time_seconds | kept by owner decision | time-like header; numeric value in inclusive 60–130 range; examples: 76.315000, 75.980000, 76.288000 |
| data/2025_qualifying_gaps_by_round.csv | teammate_best_qualifying_time_seconds | kept by owner decision | time-like header; numeric value in inclusive 60–130 range; examples: 75.980000, 76.315000, 76.369000 |
| data/2025_qualifying_gaps_by_round.csv | q1_driver_time_seconds | kept by owner decision | time-like header; numeric value in inclusive 60–130 range; examples: 76.315000, 76.328000, 76.288000 |
| data/2025_qualifying_gaps_by_round.csv | q1_teammate_time_seconds | kept by owner decision | time-like header; numeric value in inclusive 60–130 range; examples: 76.328000, 76.315000, 76.369000 |
| data/2025_qualifying_gaps_by_round.csv | q2_driver_time_seconds | kept by owner decision | time-like header; numeric value in inclusive 60–130 range; examples: 76.863000, 76.112000, 76.453000 |
| data/2025_qualifying_gaps_by_round.csv | q2_teammate_time_seconds | kept by owner decision | time-like header; numeric value in inclusive 60–130 range; examples: 76.112000, 76.863000, 76.483000 |
| data/2025_qualifying_gaps_by_round.csv | q3_driver_time_seconds | kept by owner decision | time-like header; numeric value in inclusive 60–130 range; examples: 75.980000, 75.973000, 75.755000 |
| data/2025_qualifying_gaps_by_round.csv | q3_teammate_time_seconds | kept by owner decision | time-like header; numeric value in inclusive 60–130 range; examples: 75.980000, 75.755000, 75.973000 |
| data/race_pace_dry_final.csv | matched_laps | approved safe | numeric value in inclusive 60–130 range; examples: 63, 61 |
| data/race_pace_dry_final.csv | driver_clean_laps | approved safe | numeric value in inclusive 60–130 range; examples: 60, 61 |
| data/race_pace_dry_final.csv | teammate_clean_laps | approved safe | numeric value in inclusive 60–130 range; examples: 61, 62 |
| data/runs/prediction_001/metrics.csv | pair_count | approved safe | numeric value in inclusive 60–130 range; examples: 95 |
| data/runs/prediction_001/metrics.csv | ties | approved safe | numeric value in inclusive 60–130 range; examples: 95, 113, 111 |
| data/runs/prediction_001/comparisons.csv | pair_count | approved safe | numeric value in inclusive 60–130 range; examples: 95 |
| data/runs/prediction_001/counts.csv | initial_training_rows | approved safe | numeric value in inclusive 60–130 range; examples: 73, 72 |
| data/runs/prediction_001/counts.csv | main_rows | approved safe | numeric value in inclusive 60–130 range; examples: 95, 113, 111 |
| data/runs/prediction_001/summary.json | $.runtime_seconds | approved safe | time-like header |
| data/runs/prediction_001/summary.json | $.counts[].initial_training_rows | approved safe | numeric value in inclusive 60–130 range; examples: 73, 72 |
| data/runs/prediction_001/summary.json | $.counts[].main_rows | approved safe | numeric value in inclusive 60–130 range; examples: 95, 113, 111 |
| data/runs/prediction_001/summary.json | $.status_counts.Lapped | approved safe | numeric value in inclusive 60–130 range; examples: 89 |
| data/runs/prediction_001/prediction_test_config.json | $.bootstrap.percentiles[] | approved safe | numeric value in inclusive 60–130 range; examples: 97.5 |
| data/runs/prediction_001/group_stability.csv | remaining_pairs | approved safe | numeric value in inclusive 60–130 range; examples: 87, 88, 83 |
| data/runs/prediction_001/predictions.csv | training_rows | approved safe | numeric value in inclusive 60–130 range; examples: 64 |

## Saved-file validation

```json
{
  "drivers": 21,
  "groups": 9,
  "notes_json": 21,
  "period_signal_rows": 78,
  "main_pair_races": 95,
  "main_weekends": 12,
  "main_exclusions": 25,
  "primary_metrics": [
    "accuracy",
    "brier",
    "log_loss"
  ],
  "source_hashes": "agree with saved summaries",
  "source_bytes": 1701233,
  "spec_bytes": 1701233,
  "byte_difference_from_spec": 0
}
```

The source-byte total covers the 17 saved result/config files only. The four administrative files are additional: this inventory, releases.json, source_to_package.json and SHA256_MANIFEST.json.

Before writing, all source CSV cells, JSON values and all generated publication text are scanned. After writing, every package file is rescanned and compared with the validated bytes. A successful builder run confirms both checks. The SHA-256 manifest records all 17 source copies.

## Complete inventory


CSV headers are listed first; embedded JSON and JSON files include nested paths and containers. [] means an array item. Empty containers are retained. No raw values other than a few flagged examples are copied into this report.

Classifications: identifier = identity or calendar key; derived gap = saved relative pace; rating = saved rating, score, probability or uncertainty; count = saved evidence amount or coverage fraction; label = setting/category/flag; text = prose, structured provenance or time values requiring review.

### data/driver_rating_2025.csv

| Column / JSON path | Classification | Plain description |
| --- | --- | --- |
| season | identifier | Season year. |
| driver | identifier | Driver whose perspective this row uses. |
| teams | identifier | Teams the driver represented. |
| teammates | identifier | Actual teammates faced. |
| comparison_group | identifier | Connected teammate group; not a global ranking. |
| teammate_changed | label | Saved teammate changed value or metadata for this record. |
| season_appearances | count | Saved evidence/sample amount or eligibility marker: season appearances. |
| qualifying_rating | rating | Saved qualifying rating in the stated rating method. |
| dry_rating | rating | Saved dry rating in the stated rating method. |
| wet_rating | rating | Saved wet rating in the stated rating method. |
| combined_rating | rating | Saved combined season rating; negative means faster than actual teammates. |
| rating_units | label | Units of the saved season rating. |
| rating_status | label | Established, provisional or unavailable status. |
| qualifying_weight | label | Saved weight or coverage fraction: qualifying weight. |
| dry_weight | label | Saved weight or coverage fraction: dry weight. |
| wet_weight | label | Saved weight or coverage fraction: wet weight. |
| qualifying_valid | count | Saved evidence/sample amount or eligibility marker: qualifying valid. |
| qualifying_eligible | count | Saved evidence/sample amount or eligibility marker: qualifying eligible. |
| qualifying_effective_races | count | Saved evidence/sample amount or eligibility marker: qualifying effective races. |
| dry_valid | count | Saved evidence/sample amount or eligibility marker: dry valid. |
| dry_eligible | count | Saved evidence/sample amount or eligibility marker: dry eligible. |
| dry_effective_races | count | Saved evidence/sample amount or eligibility marker: dry effective races. |
| wet_valid | count | Saved evidence/sample amount or eligibility marker: wet valid. |
| wet_eligible | count | Saved evidence/sample amount or eligibility marker: wet eligible. |
| wet_effective_races | count | Saved evidence/sample amount or eligibility marker: wet effective races. |
| races_included | count | Saved evidence/sample amount or eligibility marker: races included. |
| confidence | label | Saved evidence confidence label, not a finding about direction. |
| combined_ci_low | rating | Saved interval endpoint for combined ci low; no interval is computed here. |
| combined_ci_high | rating | Saved interval endpoint for combined ci high; no interval is computed here. |
| bootstrap_valid | count | Number of usable saved bootstrap draws. |
| qualifying_median | label | Saved qualifying median value or metadata for this record. |
| dry_median | label | Saved dry median value or metadata for this record. |
| wet_median | label | Saved wet median value or metadata for this record. |
| dry_strict_count | count | Saved evidence/sample amount or eligibility marker: dry strict count. |
| dry_linear_count | count | Saved evidence/sample amount or eligibility marker: dry linear count. |
| monaco_included | label | Saved monaco included value or metadata for this record. |
| notes | text | JSON evidence notes and actual teammate-period records. |
| notes.ci_reason | label | Saved interpretation or provenance label: ci reason. |
| notes.comparison_scope | label | Saved notes.comparison scope value or metadata for this record. |
| notes.coverage | count | Saved fraction of eligible observations with a usable gap. |
| notes.coverage.dry | label | Saved notes.coverage.dry value or metadata for this record. |
| notes.coverage.dry.coverage | count | Saved fraction of eligible observations with a usable gap. |
| notes.coverage.dry.missing | label | Number of eligible observations without a usable gap. |
| notes.coverage.dry.missing_reasons | label | Saved missing-observation counts by reason. |
| notes.coverage.dry.missing_reasons.no_race_laps | count | Saved evidence/sample amount or eligibility marker: no race laps. |
| notes.coverage.dry.missing_reasons.strategy_confounded | label | Saved notes.coverage.dry.missing reasons.strategy confounded value or metadata for this record. |
| notes.coverage.dry.warnings | text | Saved warnings for interpretation. |
| notes.coverage.qualifying | label | Saved notes.coverage.qualifying value or metadata for this record. |
| notes.coverage.qualifying.coverage | count | Saved fraction of eligible observations with a usable gap. |
| notes.coverage.qualifying.missing | label | Number of eligible observations without a usable gap. |
| notes.coverage.qualifying.missing_reasons | label | Saved missing-observation counts by reason. |
| notes.coverage.qualifying.missing_reasons.no_valid_round | count | Saved evidence/sample amount or eligibility marker: no valid round. |
| notes.coverage.qualifying.warnings | text | Saved warnings for interpretation. |
| notes.coverage.wet | label | Saved notes.coverage.wet value or metadata for this record. |
| notes.coverage.wet.coverage | count | Saved fraction of eligible observations with a usable gap. |
| notes.coverage.wet.missing | label | Number of eligible observations without a usable gap. |
| notes.coverage.wet.missing_reasons | label | Saved missing-observation counts by reason. |
| notes.coverage.wet.missing_reasons.no_race_laps | count | Saved evidence/sample amount or eligibility marker: no race laps. |
| notes.coverage.wet.missing_reasons.too_few_traffic_qualified_laps | count | Saved evidence/sample amount or eligibility marker: too few traffic qualified laps. |
| notes.coverage.wet.warnings | text | Saved warnings for interpretation. |
| notes.teammate_periods | label | Saved notes.teammate periods value or metadata for this record. |
| notes.teammate_periods[] | label | Saved notes.teammate periods[] value or metadata for this record. |
| notes.teammate_periods[].driver | identifier | Driver whose perspective this row uses. |
| notes.teammate_periods[].period | label | Teammate period number, or prediction scoring window label. |
| notes.teammate_periods[].round_end | identifier | Last round of this teammate period. |
| notes.teammate_periods[].round_start | identifier | First round of this teammate period. |
| notes.teammate_periods[].season | identifier | Season year. |
| notes.teammate_periods[].signals | label | Saved notes.teammate periods[].signals value or metadata for this record. |
| notes.teammate_periods[].signals.dry | label | Saved notes.teammate periods[].signals.dry value or metadata for this record. |
| notes.teammate_periods[].signals.dry.eligible | count | Eligible observation count, or saved eligibility flag. |
| notes.teammate_periods[].signals.dry.mean | rating | Saved mean signal contribution for this actual teammate period; not recomputed here. |
| notes.teammate_periods[].signals.dry.valid | count | Number of usable observations. |
| notes.teammate_periods[].signals.qualifying | label | Saved notes.teammate periods[].signals.qualifying value or metadata for this record. |
| notes.teammate_periods[].signals.qualifying.eligible | count | Eligible observation count, or saved eligibility flag. |
| notes.teammate_periods[].signals.qualifying.mean | rating | Saved mean signal contribution for this actual teammate period; not recomputed here. |
| notes.teammate_periods[].signals.qualifying.valid | count | Number of usable observations. |
| notes.teammate_periods[].signals.wet | label | Saved notes.teammate periods[].signals.wet value or metadata for this record. |
| notes.teammate_periods[].signals.wet.eligible | count | Eligible observation count, or saved eligibility flag. |
| notes.teammate_periods[].signals.wet.mean | rating | Saved mean signal contribution for this actual teammate period; not recomputed here. |
| notes.teammate_periods[].signals.wet.valid | count | Number of usable observations. |
| notes.teammate_periods[].team | identifier | Team for this race or period. |
| notes.teammate_periods[].teammate | identifier | Actual teammate in this comparison. |
| notes.wet_warning | label | Saved notes.wet warning value or metadata for this record. |
| notes.coverage.dry.missing_reasons.effects_not_identifiable | label | Saved notes.coverage.dry.missing reasons.effects not identifiable value or metadata for this record. |
| notes.coverage.wet.missing_reasons.too_few_same_number_laps | count | Saved evidence/sample amount or eligibility marker: too few same number laps. |
| notes.coverage.wet.missing_reasons.too_few_stable_condition_laps | count | Saved evidence/sample amount or eligibility marker: too few stable condition laps. |
| notes.coverage.dry.missing_reasons.race_disqualification | label | Saved notes.coverage.dry.missing reasons.race disqualification value or metadata for this record. |
| notes.coverage.wet.missing_reasons.too_few_same_compound_laps | count | Saved evidence/sample amount or eligibility marker: too few same compound laps. |
| method_version | label | Version identifier of the saved rating method. |
| source_files | text | Provenance path text only; never followed by the loader. |

### data/driver_rating_teammate_periods.csv

| Column / JSON path | Classification | Plain description |
| --- | --- | --- |
| season | identifier | Season year. |
| driver | identifier | Driver whose perspective this row uses. |
| period | label | Teammate period number, or prediction scoring window label. |
| team | identifier | Team for this race or period. |
| teammate | identifier | Actual teammate in this comparison. |
| round_start | identifier | First round of this teammate period. |
| round_end | identifier | Last round of this teammate period. |
| signal | label | Qualifying, dry pace or wet pace. |
| valid | count | Number of usable observations. |
| eligible | count | Eligible observation count, or saved eligibility flag. |
| missing | label | Number of eligible observations without a usable gap. |
| coverage | count | Saved fraction of eligible observations with a usable gap. |
| effective_races | count | Saved weight-adjusted evidence count. |
| rating | rating | Saved signal rating in log-percentage points. |
| median | rating | Saved median signal contribution. |
| missing_reasons | label | Saved missing-observation counts by reason. |
| missing_reasons.no_valid_round | count | Saved evidence/sample amount or eligibility marker: no valid round. |
| missing_reasons.no_race_laps | count | Saved evidence/sample amount or eligibility marker: no race laps. |
| missing_reasons.strategy_confounded | label | Saved missing reasons.strategy confounded value or metadata for this record. |
| missing_reasons.too_few_traffic_qualified_laps | count | Saved evidence/sample amount or eligibility marker: too few traffic qualified laps. |
| missing_reasons.effects_not_identifiable | label | Saved missing reasons.effects not identifiable value or metadata for this record. |
| missing_reasons.too_few_same_number_laps | count | Saved evidence/sample amount or eligibility marker: too few same number laps. |
| missing_reasons.too_few_stable_condition_laps | count | Saved evidence/sample amount or eligibility marker: too few stable condition laps. |
| missing_reasons.race_disqualification | label | Saved missing reasons.race disqualification value or metadata for this record. |
| missing_reasons.too_few_same_compound_laps | count | Saved evidence/sample amount or eligibility marker: too few same compound laps. |
| warnings | text | Saved warnings for interpretation. |

### data/driver_rating_signal_diagnostics.csv

| Column / JSON path | Classification | Plain description |
| --- | --- | --- |
| season | identifier | Season year. |
| driver | identifier | Driver whose perspective this row uses. |
| signal | label | Qualifying, dry pace or wet pace. |
| valid | count | Number of usable observations. |
| eligible | count | Eligible observation count, or saved eligibility flag. |
| missing | label | Number of eligible observations without a usable gap. |
| coverage | count | Saved fraction of eligible observations with a usable gap. |
| effective_races | count | Saved weight-adjusted evidence count. |
| rating | rating | Saved signal rating in log-percentage points. |
| median | rating | Saved median signal contribution. |
| missing_reasons | label | Saved missing-observation counts by reason. |
| missing_reasons.no_valid_round | count | Saved evidence/sample amount or eligibility marker: no valid round. |
| missing_reasons.no_race_laps | count | Saved evidence/sample amount or eligibility marker: no race laps. |
| missing_reasons.strategy_confounded | label | Saved missing reasons.strategy confounded value or metadata for this record. |
| missing_reasons.too_few_traffic_qualified_laps | count | Saved evidence/sample amount or eligibility marker: too few traffic qualified laps. |
| missing_reasons.effects_not_identifiable | label | Saved missing reasons.effects not identifiable value or metadata for this record. |
| missing_reasons.too_few_same_number_laps | count | Saved evidence/sample amount or eligibility marker: too few same number laps. |
| missing_reasons.too_few_stable_condition_laps | count | Saved evidence/sample amount or eligibility marker: too few stable condition laps. |
| missing_reasons.race_disqualification | label | Saved missing reasons.race disqualification value or metadata for this record. |
| missing_reasons.too_few_same_compound_laps | count | Saved evidence/sample amount or eligibility marker: too few same compound laps. |
| warnings | text | Saved warnings for interpretation. |
| single_race_ci_low | rating | Saved interval endpoint for single race ci low; no interval is computed here. |
| single_race_ci_high | rating | Saved interval endpoint for single race ci high; no interval is computed here. |
| single_race_round | label | Saved single race round value or metadata for this record. |
| season_ci_low | rating | Saved interval endpoint for season ci low; no interval is computed here. |
| season_ci_high | rating | Saved interval endpoint for season ci high; no interval is computed here. |
| season_ci_reason | label | Saved interpretation or provenance label: season ci reason. |

### data/driver_rating_run_summary.json

| Column / JSON path | Classification | Plain description |
| --- | --- | --- |
| $ | label | Saved $ value or metadata for this record. |
| $.method_version | label | Version identifier of the saved rating method. |
| $.drivers | label | Saved $.drivers value or metadata for this record. |
| $.confidence_counts | count | Saved evidence/sample amount or eligibility marker: confidence counts. |
| $.confidence_counts.high | count | Number of drivers with the saved confidence label high. |
| $.confidence_counts.medium | count | Number of drivers with the saved confidence label medium. |
| $.confidence_counts.low/provisional | count | Number of drivers with the saved confidence label low/provisional. |
| $.confidence_counts.unavailable | count | Number of drivers with the saved confidence label unavailable. |
| $.rating_status_counts | count | Saved rating status counts in the stated rating method. |
| $.rating_status_counts.established | count | Number of drivers with the saved rating status established. |
| $.rating_status_counts.provisional | count | Number of drivers with the saved rating status provisional. |
| $.rating_status_counts.unavailable | count | Number of drivers with the saved rating status unavailable. |
| $.sensitivity_over_two | label | Saved $.sensitivity over two value or metadata for this record. |
| $.sensitivity_over_two.monaco_1p0 | label | Saved $.sensitivity over two.monaco 1p0 value or metadata for this record. |
| $.sensitivity_over_two.reference_6_2 | label | Saved $.sensitivity over two.reference 6 2 value or metadata for this record. |
| $.sensitivity_over_two.weights_50_45_5 | label | Saved weight or coverage fraction: weights 50 45 5. |
| $.sensitivity_summary | label | Saved $.sensitivity summary value or metadata for this record. |
| $.sensitivity_summary.monaco_1p0 | label | Saved $.sensitivity summary.monaco 1p0 value or metadata for this record. |
| $.sensitivity_summary.monaco_1p0.maximum_absolute_rating_change | rating | Largest saved rating change in this sensitivity check. |
| $.sensitivity_summary.monaco_1p0.maximum_absolute_rank_change | label | Saved research sensitivity rank-change diagnostic; never a dashboard rank. |
| $.sensitivity_summary.monaco_1p0.rank_changes | label | Count of saved research sensitivity rank changes; never a dashboard ranking. |
| $.sensitivity_summary.reference_6_2 | label | Saved $.sensitivity summary.reference 6 2 value or metadata for this record. |
| $.sensitivity_summary.reference_6_2.maximum_absolute_rating_change | rating | Largest saved rating change in this sensitivity check. |
| $.sensitivity_summary.reference_6_2.maximum_absolute_rank_change | label | Saved research sensitivity rank-change diagnostic; never a dashboard rank. |
| $.sensitivity_summary.reference_6_2.rank_changes | label | Count of saved research sensitivity rank changes; never a dashboard ranking. |
| $.sensitivity_summary.weights_50_45_5 | label | Saved weight or coverage fraction: weights 50 45 5. |
| $.sensitivity_summary.weights_50_45_5.maximum_absolute_rating_change | rating | Largest saved rating change in this sensitivity check. |
| $.sensitivity_summary.weights_50_45_5.maximum_absolute_rank_change | label | Saved research sensitivity rank-change diagnostic; never a dashboard rank. |
| $.sensitivity_summary.weights_50_45_5.rank_changes | label | Count of saved research sensitivity rank changes; never a dashboard ranking. |
| $.sensitivity_drivers_over_two_any | label | Saved $.sensitivity drivers over two any value or metadata for this record. |
| $.input_audit_rows | count | Saved evidence/sample amount or eligibility marker: input audit rows. |
| $.comparison_groups | label | Saved $.comparison groups value or metadata for this record. |
| $.qualifying_log_orientation_difference_max | label | Saved $.qualifying log orientation difference max value or metadata for this record. |
| $.qualifying_log_orientation_difference_mean | label | Saved $.qualifying log orientation difference mean value or metadata for this record. |
| $.qualifying_combined_gap_units | label | Saved qualifying combined gap units; qualifying combined values use log units, race and individual-round gaps use ordinary percent. |
| $.qualifying_round_combination | label | Saved $.qualifying round combination value or metadata for this record. |
| $.settings | label | Saved $.settings value or metadata for this record. |
| $.settings.signal_weights | label | Saved weight or coverage fraction: signal weights. |
| $.settings.signal_weights[] | label | Saved weight or coverage fraction: signal weights. |
| $.settings.reference_races | count | Saved evidence/sample amount or eligibility marker: reference races. |
| $.settings.reference_races[] | count | Saved evidence/sample amount or eligibility marker: reference races. |
| $.settings.monaco_multiplier | label | Saved $.settings.monaco multiplier value or metadata for this record. |
| $.settings.resamples | count | Saved $.settings.resamples value or metadata for this record. |
| $.settings.seed | label | Saved $.settings.seed value or metadata for this record. |
| $.sources_sha256 | text | Stored source-file hashes; referenced paths are not opened. |
| $.sources_sha256.data/2025_qualifying_gaps_by_round.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.sources_sha256.data/race_pace_dry_final.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.sources_sha256.data/race_pace_wet_final.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.runtime_seconds | text | Recorded script runtime in seconds, not a lap time; still flagged by the header rule. |

### data/2025_qualifying_gaps_combined.csv

| Column / JSON path | Classification | Plain description |
| --- | --- | --- |
| round_number | identifier | Race round in the season. |
| race | identifier | Race name. |
| team | identifier | Team for this race or period. |
| driver | identifier | Driver whose perspective this row uses. |
| teammate | identifier | Actual teammate in this comparison. |
| combined_gap | derived gap | Saved combined qualifying gap in log-percentage points. |
| rounds_used | label | Saved rounds used value or metadata for this record. |
| q1_gap | derived gap | Saved q1 gap; qualifying combined values use log units, race and individual-round gaps use ordinary percent. |
| q2_gap | derived gap | Saved q2 gap; qualifying combined values use log units, race and individual-round gaps use ordinary percent. |
| q3_gap | derived gap | Saved q3 gap; qualifying combined values use log units, race and individual-round gaps use ordinary percent. |
| reason_code | label | Saved reason for an unavailable or excluded record. |

### data/2025_qualifying_gaps_by_round.csv

| Column / JSON path | Classification | Plain description |
| --- | --- | --- |
| round_number | identifier | Race round in the season. |
| race | identifier | Race name. |
| team | identifier | Team for this race or period. |
| driver | identifier | Driver whose perspective this row uses. |
| teammate | identifier | Actual teammate in this comparison. |
| q1_gap | derived gap | Saved q1 gap; qualifying combined values use log units, race and individual-round gaps use ordinary percent. |
| q1_reason_code | label | Saved interpretation or provenance label: q1 reason code. |
| q2_gap | derived gap | Saved q2 gap; qualifying combined values use log units, race and individual-round gaps use ordinary percent. |
| q2_reason_code | label | Saved interpretation or provenance label: q2 reason code. |
| q3_gap | derived gap | Saved q3 gap; qualifying combined values use log units, race and individual-round gaps use ordinary percent. |
| q3_reason_code | label | Saved interpretation or provenance label: q3 reason code. |
| selected_gap | derived gap | Legacy gap from the selected qualifying round, in ordinary percent. |
| selected_round | label | Saved selected round value or metadata for this record. |
| qualifying_round | label | Saved qualifying round value or metadata for this record. |
| driver_time_seconds | text | Recorded qualifying lap time in seconds for driver time seconds; kept by owner decision. |
| teammate_time_seconds | text | Recorded qualifying lap time in seconds for teammate time seconds; kept by owner decision. |
| gap_pct | derived gap | Legacy selected qualifying gap, in ordinary percent. |
| driver_best_qualifying_time_seconds | text | Recorded qualifying lap time in seconds for driver best qualifying time seconds; kept by owner decision. |
| teammate_best_qualifying_time_seconds | text | Recorded qualifying lap time in seconds for teammate best qualifying time seconds; kept by owner decision. |
| driver_reached_round | label | Saved driver reached round value or metadata for this record. |
| teammate_reached_round | label | Saved teammate reached round value or metadata for this record. |
| missing_time | label | Saved missing time value or metadata for this record. |
| flag | label | Saved interpretation or provenance label: flag. |
| time_source | label | Saved interpretation or provenance label: time source. |
| driver_time_source | label | Saved interpretation or provenance label: driver time source. |
| teammate_time_source | label | Saved interpretation or provenance label: teammate time source. |
| blank_gap_reason | label | Saved blank gap reason; qualifying combined values use log units, race and individual-round gaps use ordinary percent. |
| q1_driver_reason | label | Saved interpretation or provenance label: q1 driver reason. |
| q1_teammate_reason | label | Saved interpretation or provenance label: q1 teammate reason. |
| q1_driver_time_seconds | text | Recorded qualifying lap time in seconds for q1 driver time seconds; kept by owner decision. |
| q1_teammate_time_seconds | text | Recorded qualifying lap time in seconds for q1 teammate time seconds; kept by owner decision. |
| q1_driver_time_source | label | Saved interpretation or provenance label: q1 driver time source. |
| q1_teammate_time_source | label | Saved interpretation or provenance label: q1 teammate time source. |
| q1_driver_recovery_blocked | label | Saved q1 driver recovery blocked value or metadata for this record. |
| q1_teammate_recovery_blocked | label | Saved q1 teammate recovery blocked value or metadata for this record. |
| q2_driver_reason | label | Saved interpretation or provenance label: q2 driver reason. |
| q2_teammate_reason | label | Saved interpretation or provenance label: q2 teammate reason. |
| q2_driver_time_seconds | text | Recorded qualifying lap time in seconds for q2 driver time seconds; kept by owner decision. |
| q2_teammate_time_seconds | text | Recorded qualifying lap time in seconds for q2 teammate time seconds; kept by owner decision. |
| q2_driver_time_source | label | Saved interpretation or provenance label: q2 driver time source. |
| q2_teammate_time_source | label | Saved interpretation or provenance label: q2 teammate time source. |
| q2_driver_recovery_blocked | label | Saved q2 driver recovery blocked value or metadata for this record. |
| q2_teammate_recovery_blocked | label | Saved q2 teammate recovery blocked value or metadata for this record. |
| q3_driver_reason | label | Saved interpretation or provenance label: q3 driver reason. |
| q3_teammate_reason | label | Saved interpretation or provenance label: q3 teammate reason. |
| q3_driver_time_seconds | text | Recorded qualifying lap time in seconds for q3 driver time seconds; kept by owner decision. |
| q3_teammate_time_seconds | text | Recorded qualifying lap time in seconds for q3 teammate time seconds; kept by owner decision. |
| q3_driver_time_source | label | Saved interpretation or provenance label: q3 driver time source. |
| q3_teammate_time_source | label | Saved interpretation or provenance label: q3 teammate time source. |
| q3_driver_recovery_blocked | label | Saved q3 driver recovery blocked value or metadata for this record. |
| q3_teammate_recovery_blocked | label | Saved q3 teammate recovery blocked value or metadata for this record. |

### data/race_pace_dry_final.csv

| Column / JSON path | Classification | Plain description |
| --- | --- | --- |
| round_number | identifier | Race round in the season. |
| race | identifier | Race name. |
| team | identifier | Team for this race or period. |
| driver | identifier | Driver whose perspective this row uses. |
| teammate | identifier | Actual teammate in this comparison. |
| matched_laps | count | Saved evidence/sample amount or eligibility marker: matched laps. |
| driver_clean_laps | count | Saved evidence/sample amount or eligibility marker: driver clean laps. |
| teammate_clean_laps | count | Saved evidence/sample amount or eligibility marker: teammate clean laps. |
| strict_gap | derived gap | Saved strict gap; qualifying combined values use log units, race and individual-round gaps use ordinary percent. |
| strict_se_pp | rating | Saved standard error in percentage points for strict se pp. |
| strict_ci_low | rating | Saved interval endpoint for strict ci low; no interval is computed here. |
| strict_ci_high | rating | Saved interval endpoint for strict ci high; no interval is computed here. |
| linear_gap | derived gap | Saved linear gap; qualifying combined values use log units, race and individual-round gaps use ordinary percent. |
| linear_se_pp | rating | Saved standard error in percentage points for linear se pp. |
| linear_ci_low | rating | Saved interval endpoint for linear ci low; no interval is computed here. |
| linear_ci_high | rating | Saved interval endpoint for linear ci high; no interval is computed here. |
| final_gap | derived gap | Saved selected dry-race gap in ordinary percent. |
| method_used | label | Saved selected dry method, or unavailable. |
| final_se_pp | rating | Saved standard error in percentage points for final se pp. |
| final_confidence | label | Saved interpretation or provenance label: final confidence. |
| disagreement_flag | label | Saved interpretation or provenance label: disagreement flag. |
| track_reliability_flag | label | Saved interpretation or provenance label: track reliability flag. |
| smallest_error_gap | derived gap | Saved smallest error gap; qualifying combined values use log units, race and individual-round gaps use ordinary percent. |
| smallest_error_method | label | Saved smallest error method value or metadata for this record. |
| reason_code | label | Saved reason for an unavailable or excluded record. |

### data/race_pace_wet_final.csv

| Column / JSON path | Classification | Plain description |
| --- | --- | --- |
| round_number | identifier | Race round in the season. |
| race | identifier | Race name. |
| team | identifier | Team for this race or period. |
| driver | identifier | Driver whose perspective this row uses. |
| teammate | identifier | Actual teammate in this comparison. |
| matched_laps_2pct | count | Saved evidence/sample amount or eligibility marker: matched laps 2pct. |
| wet_gap_2pct | derived gap | Saved wet gap 2pct; qualifying combined values use log units, race and individual-round gaps use ordinary percent. |
| wet_gap_se_pp_2pct | derived gap | Saved standard error in percentage points for wet gap se pp 2pct. |
| wet_gap_ci_low_2pct | derived gap | Saved interval endpoint for wet gap ci low 2pct; no interval is computed here. |
| wet_gap_ci_high_2pct | derived gap | Saved interval endpoint for wet gap ci high 2pct; no interval is computed here. |
| wet_gap_1pct | derived gap | Saved wet gap 1pct; qualifying combined values use log units, race and individual-round gaps use ordinary percent. |
| matched_laps_1pct | count | Saved evidence/sample amount or eligibility marker: matched laps 1pct. |
| wet_gap_3pct | derived gap | Saved wet gap 3pct; qualifying combined values use log units, race and individual-round gaps use ordinary percent. |
| matched_laps_3pct | count | Saved evidence/sample amount or eligibility marker: matched laps 3pct. |
| final_confidence | label | Saved interpretation or provenance label: final confidence. |
| reason_code | label | Saved reason for an unavailable or excluded record. |
| wet_flag | label | Saved interpretation or provenance label: wet flag. |

### data/runs/prediction_001/metrics.csv

| Column / JSON path | Classification | Plain description |
| --- | --- | --- |
| target | label | Saved outcome-selection rule. |
| period | label | Teammate period number, or prediction scoring window label. |
| method | label | Saved prediction method or baseline name. |
| pair_count | count | Saved evidence/sample amount or eligibility marker: pair count. |
| weekend_count | count | Saved evidence/sample amount or eligibility marker: weekend count. |
| excluded_pair_count | count | Saved evidence/sample amount or eligibility marker: excluded pair count. |
| exclusion_reasons | label | Saved interpretation or provenance label: exclusion reasons. |
| exclusion_reasons.driver_history_gate | label | Saved exclusion reasons.driver history gate value or metadata for this record. |
| exclusion_reasons.missing_current_qualifying | label | Saved exclusion reasons.missing current qualifying value or metadata for this record. |
| exclusion_reasons.one_or_both_retired | label | Saved exclusion reasons.one or both retired value or metadata for this record. |
| exclusion_reasons.did_not_start | label | Saved exclusion reasons.did not start value or metadata for this record. |
| exclusion_reasons.missing_result | label | Saved exclusion reasons.missing result value or metadata for this record. |
| exclusion_reasons.disqualified | label | Saved exclusion reasons.disqualified value or metadata for this record. |
| exclusion_reasons.double_retirement | label | Saved exclusion reasons.double retirement value or metadata for this record. |
| ties | count | Saved evidence/sample amount or eligibility marker: ties. |
| fallback_rows | count | Saved evidence/sample amount or eligibility marker: fallback rows. |
| brier | rating | Saved squared probability-error score; lower is better. |
| brier_ci_low | rating | Saved interval endpoint for brier ci low; no interval is computed here. |
| brier_ci_high | rating | Saved interval endpoint for brier ci high; no interval is computed here. |
| accuracy | rating | Saved fraction of correct predictions, with the approved tie credit. |
| accuracy_ci_low | rating | Saved interval endpoint for accuracy ci low; no interval is computed here. |
| accuracy_ci_high | rating | Saved interval endpoint for accuracy ci high; no interval is computed here. |
| log_loss | rating | Saved probability loss; lower is better. |
| log_loss_ci_low | rating | Saved interval endpoint for log loss ci low; no interval is computed here. |
| log_loss_ci_high | rating | Saved interval endpoint for log loss ci high; no interval is computed here. |

### data/runs/prediction_001/comparisons.csv

| Column / JSON path | Classification | Plain description |
| --- | --- | --- |
| target | label | Saved outcome-selection rule. |
| period | label | Teammate period number, or prediction scoring window label. |
| candidate | label | Method being compared. |
| baseline | label | Reference method for a saved comparison. |
| comparison | label | Primary or exploratory comparison label. |
| metric | label | Metric named for this saved score or difference. |
| difference | rating | Saved candidate-minus-baseline difference in the row metric. |
| ci_low | rating | Saved interval endpoint for ci low; no interval is computed here. |
| ci_high | rating | Saved interval endpoint for ci high; no interval is computed here. |
| pair_count | count | Saved evidence/sample amount or eligibility marker: pair count. |
| weekend_count | count | Saved evidence/sample amount or eligibility marker: weekend count. |

### data/runs/prediction_001/counts.csv

| Column / JSON path | Classification | Plain description |
| --- | --- | --- |
| target | label | Saved outcome-selection rule. |
| eligible_rows | count | Saved evidence/sample amount or eligibility marker: eligible rows. |
| initial_training_rows | count | Saved evidence/sample amount or eligibility marker: initial training rows. |
| initial_training_weekends | count | Saved evidence/sample amount or eligibility marker: initial training weekends. |
| main_rows | count | Saved evidence/sample amount or eligibility marker: main rows. |
| main_weekends | count | Saved evidence/sample amount or eligibility marker: main weekends. |
| main_exclusions | count | Saved evidence/sample amount or eligibility marker: main exclusions. |
| early_first_round | label | Saved early first round value or metadata for this record. |
| early_rows | count | Saved evidence/sample amount or eligibility marker: early rows. |
| early_weekends | count | Saved evidence/sample amount or eligibility marker: early weekends. |
| early_fallback_rows | count | Saved evidence/sample amount or eligibility marker: early fallback rows. |

### data/runs/prediction_001/summary.json

| Column / JSON path | Classification | Plain description |
| --- | --- | --- |
| $ | label | Saved $ value or metadata for this record. |
| $.config_sha256 | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.runtime_seconds | text | Recorded script runtime in seconds, not a lap time; still flagged by the header rule. |
| $.counts | count | Saved evidence/sample amount or eligibility marker: counts. |
| $.counts[] | count | Saved evidence/sample amount or eligibility marker: counts. |
| $.counts[].target | label | Saved outcome-selection rule. |
| $.counts[].eligible_rows | count | Saved evidence/sample amount or eligibility marker: eligible rows. |
| $.counts[].initial_training_rows | count | Saved evidence/sample amount or eligibility marker: initial training rows. |
| $.counts[].initial_training_weekends | count | Saved evidence/sample amount or eligibility marker: initial training weekends. |
| $.counts[].main_rows | count | Saved evidence/sample amount or eligibility marker: main rows. |
| $.counts[].main_weekends | count | Saved evidence/sample amount or eligibility marker: main weekends. |
| $.counts[].main_exclusions | count | Saved evidence/sample amount or eligibility marker: main exclusions. |
| $.counts[].early_first_round | label | Saved $.counts[].early first round value or metadata for this record. |
| $.counts[].early_rows | count | Saved evidence/sample amount or eligibility marker: early rows. |
| $.counts[].early_weekends | count | Saved evidence/sample amount or eligibility marker: early weekends. |
| $.counts[].early_fallback_rows | count | Saved evidence/sample amount or eligibility marker: early fallback rows. |
| $.status_counts | count | Saved evidence/sample amount or eligibility marker: status counts. |
| $.status_counts.Finished | count | Number of saved race-result records with status Finished. |
| $.status_counts.Lapped | count | Number of saved race-result records with status Lapped. |
| $.status_counts.Retired | count | Number of saved race-result records with status Retired. |
| $.status_counts.Disqualified | count | Number of saved race-result records with status Disqualified. |
| $.status_counts.Did not start | count | Number of saved race-result records with status Did not start. |
| $.position_matches | label | Saved $.position matches value or metadata for this record. |
| $.full_slice_max_difference | label | Saved $.full slice max difference value or metadata for this record. |
| $.source_sha256 | text | Stored source-file hashes; referenced paths are not opened. |
| $.source_sha256.data/2025_qualifying_gaps_by_round.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.data/2025_qualifying_gaps_combined.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.data/race_pace_dry_final.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.data/race_pace_wet_final.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.data/driver_rating_2025.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.cache/fastf1_http_cache.sqlite | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.data/2025_01_Australian_Grand_Prix.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.data/2025_02_Chinese_Grand_Prix.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.data/2025_03_Japanese_Grand_Prix.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.data/2025_04_Bahrain_Grand_Prix.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.data/2025_05_Saudi_Arabian_Grand_Prix.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.data/2025_06_Miami_Grand_Prix.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.data/2025_07_Emilia_Romagna_Grand_Prix.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.data/2025_08_Monaco_Grand_Prix.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.data/2025_09_Spanish_Grand_Prix.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.data/2025_10_Canadian_Grand_Prix.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.data/2025_11_Austrian_Grand_Prix.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.data/2025_12_British_Grand_Prix.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.data/2025_13_Belgian_Grand_Prix.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.data/2025_14_Hungarian_Grand_Prix.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.data/2025_15_Dutch_Grand_Prix.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.data/2025_16_Italian_Grand_Prix.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.data/2025_17_Azerbaijan_Grand_Prix.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.data/2025_18_Singapore_Grand_Prix.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.data/2025_19_United_States_Grand_Prix.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.data/2025_20_Mexico_City_Grand_Prix.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.data/2025_21_São_Paulo_Grand_Prix.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.data/2025_22_Las_Vegas_Grand_Prix.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.data/2025_23_Qatar_Grand_Prix.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.source_sha256.data/2025_24_Abu_Dhabi_Grand_Prix.csv | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.script_sha256 | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.rating_script_sha256 | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.qualifying_script_sha256 | text | Stored SHA-256 fingerprint for the named source or script; provenance only. |
| $.feature_correlation | label | Saved $.feature correlation value or metadata for this record. |
| $.feature_correlation.main_both_finish | label | Saved $.feature correlation.main both finish value or metadata for this record. |
| $.feature_correlation.all_starters | label | Saved $.feature correlation.all starters value or metadata for this record. |
| $.feature_correlation.no_double_retirement | label | Saved $.feature correlation.no double retirement value or metadata for this record. |
| $.exclusion_counts | count | Saved evidence/sample amount or eligibility marker: exclusion counts. |
| $.exclusion_counts.all_starters/calendar_history_gate | count | Saved $.exclusion counts.all starters/calendar history gate value or metadata for this record. |
| $.exclusion_counts.all_starters/did_not_start | count | Saved $.exclusion counts.all starters/did not start value or metadata for this record. |
| $.exclusion_counts.all_starters/disqualified | count | Saved $.exclusion counts.all starters/disqualified value or metadata for this record. |
| $.exclusion_counts.all_starters/driver_history_gate | count | Saved $.exclusion counts.all starters/driver history gate value or metadata for this record. |
| $.exclusion_counts.all_starters/missing_current_qualifying | count | Saved $.exclusion counts.all starters/missing current qualifying value or metadata for this record. |
| $.exclusion_counts.all_starters/missing_result | count | Saved $.exclusion counts.all starters/missing result value or metadata for this record. |
| $.exclusion_counts.main_both_finish/calendar_history_gate | count | Saved $.exclusion counts.main both finish/calendar history gate value or metadata for this record. |
| $.exclusion_counts.main_both_finish/did_not_start | count | Saved $.exclusion counts.main both finish/did not start value or metadata for this record. |
| $.exclusion_counts.main_both_finish/disqualified | count | Saved $.exclusion counts.main both finish/disqualified value or metadata for this record. |
| $.exclusion_counts.main_both_finish/driver_history_gate | count | Saved $.exclusion counts.main both finish/driver history gate value or metadata for this record. |
| $.exclusion_counts.main_both_finish/missing_current_qualifying | count | Saved $.exclusion counts.main both finish/missing current qualifying value or metadata for this record. |
| $.exclusion_counts.main_both_finish/missing_result | count | Saved $.exclusion counts.main both finish/missing result value or metadata for this record. |
| $.exclusion_counts.main_both_finish/one_or_both_retired | count | Saved $.exclusion counts.main both finish/one or both retired value or metadata for this record. |
| $.exclusion_counts.no_double_retirement/calendar_history_gate | count | Saved $.exclusion counts.no double retirement/calendar history gate value or metadata for this record. |
| $.exclusion_counts.no_double_retirement/did_not_start | count | Saved $.exclusion counts.no double retirement/did not start value or metadata for this record. |
| $.exclusion_counts.no_double_retirement/disqualified | count | Saved $.exclusion counts.no double retirement/disqualified value or metadata for this record. |
| $.exclusion_counts.no_double_retirement/double_retirement | count | Saved $.exclusion counts.no double retirement/double retirement value or metadata for this record. |
| $.exclusion_counts.no_double_retirement/driver_history_gate | count | Saved $.exclusion counts.no double retirement/driver history gate value or metadata for this record. |
| $.exclusion_counts.no_double_retirement/missing_current_qualifying | count | Saved $.exclusion counts.no double retirement/missing current qualifying value or metadata for this record. |
| $.exclusion_counts.no_double_retirement/missing_result | count | Saved $.exclusion counts.no double retirement/missing result value or metadata for this record. |

### data/runs/prediction_001/prediction_test_config.json

| Column / JSON path | Classification | Plain description |
| --- | --- | --- |
| $ | label | Saved $ setting in the frozen prediction configuration. |
| $.specification | label | Identifier of the approved prediction specification. |
| $.season | identifier | Season year. |
| $.rounds | label | Saved $.rounds setting in the frozen prediction configuration. |
| $.inputs | label | Saved $.inputs setting in the frozen prediction configuration. |
| $.inputs.ratings | rating | Saved ratings in the stated rating method. |
| $.inputs.qualifying | label | Saved $.inputs.qualifying setting in the frozen prediction configuration. |
| $.inputs.qualifying_rounds | label | Saved $.inputs.qualifying rounds setting in the frozen prediction configuration. |
| $.inputs.dry | label | Saved $.inputs.dry setting in the frozen prediction configuration. |
| $.inputs.wet | label | Saved $.inputs.wet setting in the frozen prediction configuration. |
| $.inputs.results_glob | label | Saved $.inputs.results glob setting in the frozen prediction configuration. |
| $.inputs.cache | label | Saved $.inputs.cache setting in the frozen prediction configuration. |
| $.outputs | label | Saved $.outputs setting in the frozen prediction configuration. |
| $.outputs.status | label | Saved interpretation or provenance label: status. |
| $.outputs.runs | label | Saved $.outputs.runs setting in the frozen prediction configuration. |
| $.outputs.run_prefix | label | Saved $.outputs.run prefix setting in the frozen prediction configuration. |
| $.target_rules | label | Saved $.target rules setting in the frozen prediction configuration. |
| $.target_rules.main_both_finish | label | Saved $.target rules.main both finish setting in the frozen prediction configuration. |
| $.target_rules.all_starters | label | Saved $.target rules.all starters setting in the frozen prediction configuration. |
| $.target_rules.no_double_retirement | label | Saved $.target rules.no double retirement setting in the frozen prediction configuration. |
| $.finisher_statuses | label | Saved interpretation or provenance label: finisher statuses. |
| $.finisher_statuses[] | label | Saved interpretation or provenance label: finisher statuses. |
| $.retired_status | label | Saved interpretation or provenance label: retired status. |
| $.excluded_statuses | label | Saved interpretation or provenance label: excluded statuses. |
| $.excluded_statuses[] | label | Saved interpretation or provenance label: excluded statuses. |
| $.history | label | Saved $.history setting in the frozen prediction configuration. |
| $.history.calendar_rounds | label | Saved $.history.calendar rounds setting in the frozen prediction configuration. |
| $.history.valid_qualifying_per_driver | count | Saved evidence/sample amount or eligibility marker: valid qualifying per driver. |
| $.schedule | label | Saved $.schedule setting in the frozen prediction configuration. |
| $.schedule.initial_training_first | label | Saved $.schedule.initial training first setting in the frozen prediction configuration. |
| $.schedule.initial_training_last | label | Saved $.schedule.initial training last setting in the frozen prediction configuration. |
| $.schedule.main_first | label | Saved $.schedule.main first setting in the frozen prediction configuration. |
| $.schedule.main_last | label | Saved $.schedule.main last setting in the frozen prediction configuration. |
| $.schedule.minimum_training_rows | count | Saved evidence/sample amount or eligibility marker: minimum training rows. |
| $.schedule.early_fallback_policy | label | Saved $.schedule.early fallback policy setting in the frozen prediction configuration. |
| $.models | label | Saved $.models setting in the frozen prediction configuration. |
| $.models.M1 | label | Saved $.models.M1 setting in the frozen prediction configuration. |
| $.models.M1[] | label | Saved $.models.M1[] setting in the frozen prediction configuration. |
| $.models.M2 | label | Saved $.models.M2 setting in the frozen prediction configuration. |
| $.models.M2[] | label | Saved $.models.M2[] setting in the frozen prediction configuration. |
| $.models.M3 | label | Saved $.models.M3 setting in the frozen prediction configuration. |
| $.models.M3[] | label | Saved $.models.M3[] setting in the frozen prediction configuration. |
| $.logistic | label | Saved $.logistic setting in the frozen prediction configuration. |
| $.logistic.intercept | label | Saved $.logistic.intercept setting in the frozen prediction configuration. |
| $.logistic.C | label | Saved $.logistic.C setting in the frozen prediction configuration. |
| $.logistic.solver | label | Saved $.logistic.solver setting in the frozen prediction configuration. |
| $.logistic.maxiter | label | Saved $.logistic.maxiter setting in the frozen prediction configuration. |
| $.logistic.gtol | label | Saved $.logistic.gtol setting in the frozen prediction configuration. |
| $.logistic.ftol | label | Saved $.logistic.ftol setting in the frozen prediction configuration. |
| $.logistic.feature_scaling | label | Saved $.logistic.feature scaling setting in the frozen prediction configuration. |
| $.logistic.objective | label | Saved $.logistic.objective setting in the frozen prediction configuration. |
| $.rating | rating | Saved signal rating in log-percentage points. |
| $.rating.method_version | label | Version identifier of the saved rating method. |
| $.rating.round_weights | label | Saved weight or coverage fraction: round weights. |
| $.rating.round_weights.q1 | label | Saved $.rating.round weights.q1 setting in the frozen prediction configuration. |
| $.rating.round_weights.q2 | label | Saved $.rating.round weights.q2 setting in the frozen prediction configuration. |
| $.rating.round_weights.q3 | label | Saved $.rating.round weights.q3 setting in the frozen prediction configuration. |
| $.rating.signal_weights | label | Saved weight or coverage fraction: signal weights. |
| $.rating.signal_weights[] | label | Saved weight or coverage fraction: signal weights. |
| $.rating.reference_races | count | Saved evidence/sample amount or eligibility marker: reference races. |
| $.rating.reference_races[] | count | Saved evidence/sample amount or eligibility marker: reference races. |
| $.rating.precision_floor | label | Saved $.rating.precision floor setting in the frozen prediction configuration. |
| $.rating.precision_se_scale | label | Saved $.rating.precision se scale setting in the frozen prediction configuration. |
| $.rating.monaco_multiplier | label | Saved $.rating.monaco multiplier setting in the frozen prediction configuration. |
| $.rating.missing_signal | label | Saved $.rating.missing signal setting in the frozen prediction configuration. |
| $.rating.full_slice_tolerance | label | Saved $.rating.full slice tolerance setting in the frozen prediction configuration. |
| $.rating.qualifying_export_tolerance | label | Saved $.rating.qualifying export tolerance setting in the frozen prediction configuration. |
| $.rating.provisional_allowed | label | Saved $.rating.provisional allowed setting in the frozen prediction configuration. |
| $.baselines | label | Saved $.baselines setting in the frozen prediction configuration. |
| $.baselines.methods | label | Saved $.baselines.methods setting in the frozen prediction configuration. |
| $.baselines.methods[] | label | Saved $.baselines.methods[] setting in the frozen prediction configuration. |
| $.baselines.pseudo_success | label | Saved $.baselines.pseudo success setting in the frozen prediction configuration. |
| $.baselines.pseudo_failure | label | Saved $.baselines.pseudo failure setting in the frozen prediction configuration. |
| $.baselines.uninformed_probability | rating | Saved $.baselines.uninformed probability setting in the frozen prediction configuration. |
| $.baselines.historical_outcome_rule | label | Saved $.baselines.historical outcome rule setting in the frozen prediction configuration. |
| $.baselines.calibration_rows | count | Saved evidence/sample amount or eligibility marker: calibration rows. |
| $.baselines.previous_race | label | Saved $.baselines.previous race setting in the frozen prediction configuration. |
| $.baselines.head_to_head | label | Saved $.baselines.head to head setting in the frozen prediction configuration. |
| $.baselines.invalid_grid | count | Saved evidence/sample amount or eligibility marker: invalid grid. |
| $.metrics | label | Saved $.metrics setting in the frozen prediction configuration. |
| $.metrics.primary | label | Saved $.metrics.primary setting in the frozen prediction configuration. |
| $.metrics.secondary | label | Saved $.metrics.secondary setting in the frozen prediction configuration. |
| $.metrics.secondary[] | label | Saved $.metrics.secondary[] setting in the frozen prediction configuration. |
| $.metrics.decision_threshold | label | Saved $.metrics.decision threshold setting in the frozen prediction configuration. |
| $.metrics.tie_credit | label | Saved $.metrics.tie credit setting in the frozen prediction configuration. |
| $.metrics.log_loss_clip | rating | Saved $.metrics.log loss clip setting in the frozen prediction configuration. |
| $.metrics.log_loss_clip[] | rating | Saved $.metrics.log loss clip[] setting in the frozen prediction configuration. |
| $.bootstrap | label | Saved $.bootstrap setting in the frozen prediction configuration. |
| $.bootstrap.resamples | count | Saved $.bootstrap.resamples setting in the frozen prediction configuration. |
| $.bootstrap.seed | label | Saved $.bootstrap.seed setting in the frozen prediction configuration. |
| $.bootstrap.percentiles | label | Saved $.bootstrap.percentiles setting in the frozen prediction configuration. |
| $.bootstrap.percentiles[] | label | Saved $.bootstrap.percentiles[] setting in the frozen prediction configuration. |
| $.bootstrap.unit | label | Saved $.bootstrap.unit setting in the frozen prediction configuration. |
| $.bootstrap.refit | label | Saved $.bootstrap.refit setting in the frozen prediction configuration. |
| $.comparisons | label | Saved $.comparisons setting in the frozen prediction configuration. |
| $.comparisons.primary | label | Saved $.comparisons.primary setting in the frozen prediction configuration. |
| $.comparisons.primary[] | label | Saved $.comparisons.primary[] setting in the frozen prediction configuration. |
| $.comparisons.against_simple_baselines | label | Saved $.comparisons.against simple baselines setting in the frozen prediction configuration. |
| $.comparisons.against_simple_baselines[] | label | Saved $.comparisons.against simple baselines[] setting in the frozen prediction configuration. |
| $.comparisons.best_baseline_selection | label | Saved $.comparisons.best baseline selection setting in the frozen prediction configuration. |
| $.comparisons.group_stability | label | Saved $.comparisons.group stability setting in the frozen prediction configuration. |
| $.orientation | label | Saved $.orientation setting in the frozen prediction configuration. |
| $.missing_current_qualifying | label | Saved $.missing current qualifying setting in the frozen prediction configuration. |
| $.points_and_race_wins | label | Saved $.points and race wins setting in the frozen prediction configuration. |
| $.network | label | Saved $.network setting in the frozen prediction configuration. |
| $.cache_mode | label | Saved $.cache mode setting in the frozen prediction configuration. |
| $.overwrite | label | Saved $.overwrite setting in the frozen prediction configuration. |

### data/runs/prediction_001/baseline_winners.csv

| Column / JSON path | Classification | Plain description |
| --- | --- | --- |
| target | label | Saved outcome-selection rule. |
| period | label | Teammate period number, or prediction scoring window label. |
| metric | label | Metric named for this saved score or difference. |
| best_simple_baselines | label | Saved best simple baselines value or metadata for this record. |
| value | rating | Saved value of the metric named in the row. |
| exploratory | label | Saved exploratory value or metadata for this record. |

### data/runs/prediction_001/group_stability.csv

| Column / JSON path | Classification | Plain description |
| --- | --- | --- |
| target | label | Saved outcome-selection rule. |
| period | label | Teammate period number, or prediction scoring window label. |
| omitted_group | label | Saved omitted group value or metadata for this record. |
| remaining_pairs | label | Saved remaining pairs value or metadata for this record. |
| remaining_weekends | count | Saved evidence/sample amount or eligibility marker: remaining weekends. |
| M2_brier | rating | Saved M2 brier value or metadata for this record. |
| M2_accuracy | rating | Saved M2 accuracy value or metadata for this record. |
| M2_log_loss | rating | Saved M2 log loss value or metadata for this record. |
| M3_brier | rating | Saved M3 brier value or metadata for this record. |
| M3_accuracy | rating | Saved M3 accuracy value or metadata for this record. |
| M3_log_loss | rating | Saved M3 log loss value or metadata for this record. |
| difference_brier | rating | Saved difference brier value or metadata for this record. |
| difference_accuracy | rating | Saved difference accuracy value or metadata for this record. |
| difference_log_loss | rating | Saved difference log loss value or metadata for this record. |

### data/runs/prediction_001/eligibility.csv

| Column / JSON path | Classification | Plain description |
| --- | --- | --- |
| target | label | Saved outcome-selection rule. |
| pair_id | identifier | Identifier for this race and teammate pair. |
| round_number | identifier | Race round in the season. |
| driver_a | identifier | Driver A in the saved prediction orientation. |
| driver_b | identifier | Driver B in the saved prediction orientation. |
| eligible | label | Eligible observation count, or saved eligibility flag. |
| reason_code | label | Saved reason for an unavailable or excluded record. |
| all_reasons | label | All saved exclusion reasons; reasons may overlap. |

### data/runs/prediction_001/predictions.csv

| Column / JSON path | Classification | Plain description |
| --- | --- | --- |
| round_number | identifier | Race round in the season. |
| race | identifier | Race name. |
| team | identifier | Team for this race or period. |
| driver_a | identifier | Driver A in the saved prediction orientation. |
| driver_b | identifier | Driver B in the saved prediction orientation. |
| pair_id | identifier | Identifier for this race and teammate pair. |
| result_present | label | Saved result present value or metadata for this record. |
| valid_positions | label | Saved evidence/sample amount or eligibility marker: valid positions. |
| status_a | label | Saved interpretation or provenance label: status a. |
| status_b | label | Saved interpretation or provenance label: status b. |
| position_a | label | Saved official finishing position for A; audit only. |
| position_b | label | Saved official finishing position for B; audit only. |
| outcome | label | Saved indicator that A finished ahead of B; an audit outcome, not a model feature. |
| valid_qualifying | label | Saved evidence/sample amount or eligibility marker: valid qualifying. |
| qualifying_advantage | label | Saved current qualifying feature; positive favours A. |
| grid_valid | label | Saved evidence/sample amount or eligibility marker: grid valid. |
| grid_flag | label | Saved interpretation or provenance label: grid flag. |
| grid_pick | label | Saved grid pick value or metadata for this record. |
| main_history_usable | label | Saved main history usable value or metadata for this record. |
| previous_pick | label | Saved previous pick value or metadata for this record. |
| head_to_head_probability | rating | Saved head to head probability value or metadata for this record. |
| head_to_head_comparisons | label | Saved head to head comparisons value or metadata for this record. |
| qualifying_pick | label | Saved qualifying pick value or metadata for this record. |
| prior_rating_a | rating | Saved prior rating a in the stated rating method. |
| prior_qualifying_a | label | Saved prior qualifying a value or metadata for this record. |
| prior_status_a | label | Saved interpretation or provenance label: prior status a. |
| prior_rating_b | rating | Saved prior rating b in the stated rating method. |
| prior_qualifying_b | label | Saved prior qualifying b value or metadata for this record. |
| prior_status_b | label | Saved interpretation or provenance label: prior status b. |
| rating_difference | rating | Saved prior-rating feature; positive favours A. |
| history_eligible | label | Saved evidence/sample amount or eligibility marker: history eligible. |
| feature_source_max_round | label | Saved interpretation or provenance label: feature source max round. |
| target | label | Saved outcome-selection rule. |
| period | label | Teammate period number, or prediction scoring window label. |
| method | label | Saved prediction method or baseline name. |
| probability | rating | Saved probability that A finishes ahead of B. |
| training_rows | count | Saved evidence/sample amount or eligibility marker: training rows. |
| training_max_round | label | Saved training max round value or metadata for this record. |
| fallback_reason | label | Saved interpretation or provenance label: fallback reason. |

