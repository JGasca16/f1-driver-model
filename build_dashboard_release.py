"""Validate and package saved dashboard results only. No pipeline or network calls.

Run with --check-only for an inventory and saved-file checks. Any possible
lap-time column blocks packaging, including numeric-range matches in counts.
There is deliberately no command-line override for that review gate.
"""
import argparse
from collections import Counter, defaultdict
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re

ROOT = Path(__file__).resolve().parent
RUN = 'data/runs/prediction_001/'
ALLOWLIST = (
    'data/driver_rating_2025.csv',
    'data/driver_rating_teammate_periods.csv',
    'data/driver_rating_signal_diagnostics.csv',
    'data/driver_rating_run_summary.json',
    'data/2025_qualifying_gaps_combined.csv',
    'data/2025_qualifying_gaps_by_round.csv',
    'data/race_pace_dry_final.csv',
    'data/race_pace_wet_final.csv',
    *(RUN + name for name in ('metrics.csv', 'comparisons.csv', 'counts.csv',
        'summary.json', 'prediction_test_config.json', 'baseline_winners.csv',
        'group_stability.csv', 'eligibility.csv', 'predictions.csv')),
)
RELEASE_PATH = 'docs/data/2025/release_2025_001'
METADATA_PATH = 'dashboard_data/releases.json'
INVENTORY_PATH = 'dashboard_data/COLUMN_INVENTORY.md'
EXPECTED_BYTES = 1701233
DISCLAIMER = ('This is an unofficial, independent project. It is not affiliated with '
    'or endorsed by Formula 1, the FIA or any team. Formula 1 and team names are '
    'trademarks of their respective owners.')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(content):
    return hashlib.sha256(content).hexdigest()


def checked_path(root, name):
    """Accept one exact local name, with no alternate spelling or symlinks."""
    require(isinstance(name, str) and bool(name), 'Path must be a nonempty string')
    parts = name.split('/')
    require(not PurePosixPath(name).is_absolute() and
            not PureWindowsPath(name).is_absolute(), 'Absolute path blocked')
    require(not any(part in ('', '.', '..') for part in parts), 'Traversal or alias blocked')
    require(not any(c in name for c in '\\:*?[]%\x00'), 'URL, glob or encoded path blocked')
    root = Path(root).resolve()
    path = root
    for part in parts:
        path = path / part
        require(not path.is_symlink(), 'Symlink blocked')
    require(path.resolve().is_relative_to(root), 'Path leaves repository')
    return path


def load_allowed(root, name):
    path = checked_path(root, name)
    require(name in ALLOWLIST, 'File is not in the exact 17-file allowlist')
    return path.read_bytes()


def load_sources(root):
    return {name: load_allowed(root, name) for name in ALLOWLIST}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON key: ' + key)
        result[key] = value
    return result


def decode_json(content):
    return json.loads(content, object_pairs_hook=unique_object)


def csv_rows(content):
    reader = csv.DictReader(io.StringIO(content.decode('utf-8')))
    require(reader.fieldnames and len(reader.fieldnames) == len(set(reader.fieldnames)),
            'Missing or duplicate CSV headers')
    rows = list(reader)
    require(all(None not in row and None not in row.values() for row in rows),
            'CSV row does not match its header')
    return reader.fieldnames, rows


def metadata_for(sources):
    """Copy approved facts and saved scope; do not calculate ratings or metrics."""
    summary = decode_json(sources['data/driver_rating_run_summary.json'])
    prediction = decode_json(sources[RUN + 'summary.json'])
    config = decode_json(sources[RUN + 'prediction_test_config.json'])
    _, ratings = csv_rows(sources['data/driver_rating_2025.csv'])
    counts = next(row for row in prediction['counts'] if row['target'] == 'main_both_finish')
    groups = sorted({row['comparison_group'] for row in ratings})
    repository = 'https://github.com/JGasca16/f1-driver-model'
    return {'schema_version': 1, 'releases': [{
        'season': 2025, 'release_id': 'release_2025_001', 'published_at': '',
        'results_last_updated': '2026-10-23', 'release_state': 'candidate',
        'rating_method_version': summary['method_version'],
        'prediction_specification': config['specification'],
        'prediction_run_id': 'prediction_001', 'rounds': config['rounds'],
        'groups': groups,
        'scope_counts': {'drivers': summary['drivers'], 'groups': summary['comparison_groups'],
            'main_pair_races': counts['main_rows'], 'main_weekends': counts['main_weekends'],
            'main_exclusions': counts['main_exclusions'],
            'confidence_counts': summary['confidence_counts'],
            'rating_status_counts': summary['rating_status_counts']},
        'sources': [{'source': name, 'package_path': RELEASE_PATH + '/' + Path(name).name,
                     'source_sha256': sha256(sources[name]), 'bytes': len(sources[name])}
                    for name in ALLOWLIST],
        'source_sha256': {name: sha256(sources[name]) for name in ALLOWLIST},
        'method_links': {name: repository + '/blob/main/' + name for name in (
            'DRIVER_RATING_METHOD.md', 'PREDICTION_TEST_METHOD.md',
            'QUALIFYING_BY_ROUND.md', 'METHOD_DRY_RACEPACE.md', 'METHOD_WET_RACEPACE.md')},
        'repository_url': repository, 'license_url': repository + '/blob/main/LICENSE',
        'data_credit': {'text': 'FastF1 and the official timing feeds it wraps.',
            'url': 'https://docs.fastf1.dev/',
            'license_scope': 'MIT covers repository code only, not underlying race and timing data.'},
        'unofficial_project_disclaimer': DISCLAIMER,
        'hosting': {'provider': 'GitHub Pages', 'branch': 'main', 'folder': 'docs/'},
        'views': ['overview', 'drivers', 'race_gaps', 'prediction_test', 'method_and_limits'],
        'display_rules': {'group_order': 'alphabetical', 'driver_order': 'alphabetical',
            'rank_numbers': False, 'global_leaderboard': False,
            'sign_explanation': 'Negative = faster than the actual teammate(s); positive = slower.',
            'zero_inclusive_interval_label': 'No clear gap'},
        'teaching_examples': {'purpose': 'teaching examples, not top results', 'examples': [
            {'group': 'HAM+LEC', 'label': 'Clear gap', 'state': 'clear_gap'},
            {'group': 'NOR+PIA', 'label': 'No clear gap', 'state': 'no_clear_gap'}]},
        'date_provenance': {'date_kind': 'repository commit dates',
            'ratings': {'date': '2026-10-16', 'commit': '7388c24'},
            'prediction_run': {'date': '2026-10-23', 'commit': '86a922d'},
            'note': 'Owner-approved repository commit dates, not session dates or data-generation timestamps. '
                    'published_at stays empty until deployment.'},
    }]}


def validate_metadata(metadata, sources):
    require(json.dumps(metadata, sort_keys=True, allow_nan=False) ==
            json.dumps(metadata_for(sources), sort_keys=True, allow_nan=False),
            'Release metadata differs from approved schema, facts or source hashes')


def validate_saved(sources, metadata):
    """Compare saved records only; counts and rounding checks are not new estimates."""
    require(set(sources) == set(ALLOWLIST) and len(sources) == 17, 'Exactly 17 sources required')
    validate_metadata(metadata, sources)
    release = metadata['releases'][0]
    _, ratings = csv_rows(sources['data/driver_rating_2025.csv'])
    summary = decode_json(sources['data/driver_rating_run_summary.json'])
    prediction = decode_json(sources[RUN + 'summary.json'])
    config = decode_json(sources[RUN + 'prediction_test_config.json'])
    require(sha256(sources[RUN + 'prediction_test_config.json']) == prediction['config_sha256'],
            'Prediction config hash mismatch')
    for name in ('data/driver_rating_2025.csv', 'data/2025_qualifying_gaps_combined.csv',
                 'data/race_pace_dry_final.csv', 'data/race_pace_wet_final.csv',
                 'data/2025_qualifying_gaps_by_round.csv'):
        require(sha256(sources[name]) == prediction['source_sha256'][name], 'Prediction source hash mismatch: ' + name)
    for name, digest in summary['sources_sha256'].items():
        require(name in sources and sha256(sources[name]) == digest, 'Rating source hash mismatch: ' + name)
    require(len(ratings) == len({r['driver'] for r in ratings}) == summary['drivers'] == 21, 'Driver count mismatch')
    require(len(release['groups']) == summary['comparison_groups'] == 9, 'Group count mismatch')
    for r in ratings:
        require(r['season'] == '2025' and r['method_version'] == release['rating_method_version'], 'Rating season/version mismatch')
    for field, key in [('confidence', 'confidence_counts'), ('rating_status', 'rating_status_counts')]:
        actual = Counter(r[field] for r in ratings)
        require(all(actual[k] == v for k, v in summary[key].items()) and set(actual) <= set(summary[key]), 'Saved label counts differ')
    require(config['season'] == 2025 and config['rounds'] == 24, 'Season/round count mismatch')
    _, qualifying = csv_rows(sources['data/2025_qualifying_gaps_combined.csv'])
    require({int(r['round_number']) for r in qualifying} == set(range(1, 25)), 'Qualifying round coverage mismatch')
    require({r['driver'] for r in qualifying} == {r['driver'] for r in ratings}, 'Roster mismatch')
    require(set(release['groups']) == {r['comparison_group'] for r in ratings}, 'Group identities mismatch')
    for example in release['teaching_examples']['examples']:
        members = [r for r in ratings if r['comparison_group'] == example['group']]
        require(len(members) == 2, 'Teaching example group missing')
        for r in members:
            crosses = Decimal(r['combined_ci_low']) <= 0 <= Decimal(r['combined_ci_high'])
            require(crosses == (example['state'] == 'no_clear_gap'), 'Teaching example interval state differs')
    _, periods = csv_rows(sources['data/driver_rating_teammate_periods.csv'])
    period_keys = lambda r: (str(r['season']), r['driver'], str(r['period']), r['team'], r['teammate'], r['signal'])
    by_key = {period_keys(r): r for r in periods}
    require(len(by_key) == len(periods), 'Duplicate period record')
    expected = set()
    for r in ratings:
        note = decode_json(r['notes'])
        require(isinstance(note, dict), 'Notes must be a JSON object')
        for p in note['teammate_periods']:
            require(p['driver'] == r['driver'] and p['season'] == 2025, 'Period identity mismatch')
            for signal, values in p['signals'].items():
                key = period_keys(dict(p, signal=signal))
                require(key not in expected and key in by_key, 'Missing/duplicate notes period')
                expected.add(key)
                row = by_key[key]
                for field in ('round_start', 'round_end'):
                    require(int(row[field]) == p[field], 'Period bounds mismatch')
                for field in ('valid', 'eligible'):
                    require(int(row[field]) == values[field], 'Period count mismatch')
                mean = values['mean']
                require((row['rating'] == '') if mean is None else
                        Decimal(row['rating']) == Decimal(str(mean)).quantize(Decimal('.001')),
                        'Period mean differs after three-decimal rounding')
    require(expected == set(by_key), 'Extra periods absent from notes')
    _, counts = csv_rows(sources[RUN + 'counts.csv'])
    main = [r for r in counts if r['target'] == 'main_both_finish']
    require(len(main) == 1, 'Main count record missing or duplicated')
    saved_main = [r for r in prediction['counts'] if r['target'] == 'main_both_finish']
    require(len(saved_main) == 1, 'Summary main record missing or duplicated')
    for key, expected_count in [('main_rows', 95), ('main_weekends', 12), ('main_exclusions', 25)]:
        require(int(main[0][key]) == saved_main[0][key] == expected_count, 'Main sample count mismatch')
    _, metrics = csv_rows(sources[RUN + 'metrics.csv'])
    main_metrics = [r for r in metrics if r['target'] == 'main_both_finish' and r['period'] == 'main']
    methods = {'M1', 'M2', 'M3', 'qualifying', 'grid', 'previous', 'head_to_head', 'chance'}
    require(len(main_metrics) == 8 and {r['method'] for r in main_metrics} == methods, 'Main metric methods missing/duplicated')
    for r in main_metrics:
        require((int(r['pair_count']), int(r['weekend_count']), int(r['excluded_pair_count'])) == (95, 12, 25), 'Metric sample mismatch')
    _, comparisons = csv_rows(sources[RUN + 'comparisons.csv'])
    primary = [r for r in comparisons if (r['target'], r['period'], r['comparison'], r['candidate'], r['baseline']) ==
               ('main_both_finish', 'main', 'primary', 'M3', 'M2')]
    require(len(primary) == 3 and {r['metric'] for r in primary} == {'brier', 'accuracy', 'log_loss'}, 'Primary comparison rows missing/duplicated')
    require(all((int(r['pair_count']), int(r['weekend_count'])) == (95, 12) for r in primary), 'Comparison sample mismatch')
    _, predictions = csv_rows(sources[RUN + 'predictions.csv'])
    for method in methods:
        rows = [r for r in predictions if (r['target'], r['period'], r['method']) == ('main_both_finish', 'main', method)]
        require(len(rows) == len({r['pair_id'] for r in rows}) == 95 and len({r['round_number'] for r in rows}) == 12, 'Prediction row count mismatch')
    _, eligible = csv_rows(sources[RUN + 'eligibility.csv'])
    window = [r for r in eligible if r['target'] == 'main_both_finish' and 13 <= int(r['round_number']) <= 24]
    require(len(window) == len({r['pair_id'] for r in window}) == 120 and
            sum(r['eligible'] == 'False' for r in window) == 25, 'Eligibility count mismatch')
    total = sum(len(content) for content in sources.values())
    return {'drivers': len(ratings), 'groups': len(release['groups']), 'notes_json': len(ratings),
            'period_signal_rows': len(periods), 'main_pair_races': 95, 'main_weekends': 12,
            'main_exclusions': 25, 'primary_metrics': sorted(r['metric'] for r in primary),
            'source_hashes': 'agree with saved summaries', 'source_bytes': total,
            'spec_bytes': EXPECTED_BYTES, 'byte_difference_from_spec': total - EXPECTED_BYTES,
            'packaged_hashes': 'not checked until package exists'}


# Descriptions cover numeric meaning without computing any new result.
DESCRIPTIONS = {
    'season': 'Season year.', 'driver': 'Driver whose perspective this row uses.',
    'teammate': 'Actual teammate in this comparison.', 'driver_a': 'Driver A in the saved prediction orientation.',
    'driver_b': 'Driver B in the saved prediction orientation.', 'team': 'Team for this race or period.',
    'teams': 'Teams the driver represented.', 'teammates': 'Actual teammates faced.',
    'comparison_group': 'Connected teammate group; not a global ranking.',
    'round_number': 'Race round in the season.', 'race': 'Race name.',
    'period': 'Teammate period number, or prediction scoring window label.',
    'round_start': 'First round of this teammate period.', 'round_end': 'Last round of this teammate period.',
    'signal': 'Qualifying, dry pace or wet pace.', 'notes': 'JSON evidence notes and actual teammate-period records.',
    'rating': 'Saved signal rating in log-percentage points.', 'median': 'Saved median signal contribution.',
    'mean': 'Saved mean signal contribution for this actual teammate period; not recomputed here.',
    'maximum_absolute_rank_change': 'Saved research sensitivity rank-change diagnostic; never a dashboard rank.',
    'rank_changes': 'Count of saved research sensitivity rank changes; never a dashboard ranking.',
    'maximum_absolute_rating_change': 'Largest saved rating change in this sensitivity check.',
    'combined_rating': 'Saved combined season rating; negative means faster than actual teammates.',
    'combined_gap': 'Saved combined qualifying gap in log-percentage points.',
    'selected_gap': 'Legacy gap from the selected qualifying round, in ordinary percent.',
    'gap_pct': 'Legacy selected qualifying gap, in ordinary percent.',
    'final_gap': 'Saved selected dry-race gap in ordinary percent.',
    'outcome': 'Saved indicator that A finished ahead of B; an audit outcome, not a model feature.',
    'probability': 'Saved probability that A finishes ahead of B.',
    'brier': 'Saved squared probability-error score; lower is better.',
    'accuracy': 'Saved fraction of correct predictions, with the approved tie credit.',
    'log_loss': 'Saved probability loss; lower is better.',
    'difference': 'Saved candidate-minus-baseline difference in the row metric.',
    'metric': 'Metric named for this saved score or difference.',
    'value': 'Saved value of the metric named in the row.',
    'qualifying_advantage': 'Saved current qualifying feature; positive favours A.',
    'rating_difference': 'Saved prior-rating feature; positive favours A.',
    'position_a': 'Saved official finishing position for A; audit only.',
    'position_b': 'Saved official finishing position for B; audit only.',
    'valid': 'Number of usable observations.', 'eligible': 'Eligible observation count, or saved eligibility flag.',
    'missing': 'Number of eligible observations without a usable gap.',
    'coverage': 'Saved fraction of eligible observations with a usable gap.',
    'effective_races': 'Saved weight-adjusted evidence count.',
    'reason_code': 'Saved reason for an unavailable or excluded record.',
    'all_reasons': 'All saved exclusion reasons; reasons may overlap.',
    'missing_reasons': 'Saved missing-observation counts by reason.',
    'warnings': 'Saved warnings for interpretation.',
    'source_files': 'Provenance path text only; never followed by the loader.',
    'runtime_seconds': 'Recorded script runtime in seconds, not a lap time; still flagged by the header rule.',
    'method_version': 'Version identifier of the saved rating method.',
    'specification': 'Identifier of the approved prediction specification.',
    'confidence': 'Saved evidence confidence label, not a finding about direction.',
    'rating_status': 'Established, provisional or unavailable status.',
    'rating_units': 'Units of the saved season rating.',
    'bootstrap_valid': 'Number of usable saved bootstrap draws.',
    'pair_id': 'Identifier for this race and teammate pair.',
    'method': 'Saved prediction method or baseline name.',
    'method_used': 'Saved selected dry method, or unavailable.',
    'target': 'Saved outcome-selection rule.', 'comparison': 'Primary or exploratory comparison label.',
    'candidate': 'Method being compared.', 'baseline': 'Reference method for a saved comparison.',
    'source_sha256': 'Stored source-file hashes; referenced paths are not opened.',
    'sources_sha256': 'Stored source-file hashes; referenced paths are not opened.',
}


def describe(field, filename):
    leaf = field.rsplit('.', 1)[-1].replace('[]', '')
    if leaf in DESCRIPTIONS:
        description = DESCRIPTIONS[leaf]
    elif 'time_seconds' in leaf:
        description = 'Recorded qualifying lap time in seconds for ' + leaf.replace('_', ' ') + '; requires review.'
    elif leaf in ('ci_low', 'ci_high') or leaf.endswith('_ci_low') or leaf.endswith('_ci_high') or 'ci_low_' in leaf or 'ci_high_' in leaf:
        description = 'Saved interval endpoint for ' + leaf.replace('_', ' ') + '; no interval is computed here.'
    elif 'se_pp' in leaf or leaf.endswith('_se'):
        description = 'Saved standard error in percentage points for ' + leaf.replace('_', ' ') + '.'
    elif 'sha256' in field:
        description = 'Stored SHA-256 fingerprint for the named source or script; provenance only.'
    elif leaf.endswith('_gap') or 'gap_' in leaf:
        description = 'Saved ' + leaf.replace('_', ' ') + '; qualifying combined values use log units, race and individual-round gaps use ordinary percent.'
    elif 'confidence_counts.' in field:
        description = 'Number of drivers with the saved confidence label ' + leaf + '.'
    elif 'rating_status_counts.' in field:
        description = 'Number of drivers with the saved rating status ' + leaf + '.'
    elif 'status_counts.' in field:
        description = 'Number of saved race-result records with status ' + leaf + '.'
    elif 'rating' in leaf:
        description = 'Saved ' + leaf.replace('_', ' ') + ' in the stated rating method.'
    elif any(word in leaf for word in ('count', 'rows', 'laps', 'weekends', 'eligible', 'valid', 'races', 'appearances', 'exclusions', 'ties')):
        description = 'Saved evidence/sample amount or eligibility marker: ' + leaf.replace('_', ' ') + '.'
    elif 'weight' in leaf or 'coverage' in leaf:
        description = 'Saved weight or coverage fraction: ' + leaf.replace('_', ' ') + '.'
    elif any(word in leaf for word in ('flag', 'reason', 'status', 'confidence', 'source')):
        description = 'Saved interpretation or provenance label: ' + leaf.replace('_', ' ') + '.'
    else:
        description = 'Saved ' + field.replace('_', ' ') + (' setting in the frozen prediction configuration.' if filename.endswith('config.json') else ' value or metadata for this record.')
    if 'time_seconds' in leaf or leaf == 'runtime_seconds':
        kind = 'text'
    elif leaf.endswith('_units'):
        kind = 'label'
    elif leaf in ('season', 'driver', 'teammate', 'driver_a', 'driver_b', 'team', 'teams', 'teammates', 'race', 'round_number', 'pair_id', 'round_start', 'round_end', 'comparison_group'):
        kind = 'identifier'
    elif 'gap' in leaf and not any(w in leaf for w in ('reason', 'source', 'flag')):
        kind = 'derived gap'
    elif leaf in ('rating_status', 'history_eligible', 'valid_positions', 'valid_qualifying', 'grid_valid', 'main_history_usable') or (leaf == 'eligible' and filename.endswith('eligibility.csv')):
        kind = 'label'
    elif leaf in ('mean', 'median', 'difference', 'value') or any(w in leaf for w in ('rating', 'brier', 'accuracy', 'log_loss', 'probability', 'ci_low', 'ci_high', 'se_pp')) and not any(w in leaf for w in ('status', 'method', 'sha256', 'script')):
        kind = 'rating'
    elif 'counts.' in field or leaf == 'coverage' or any(w in leaf for w in ('count', 'rows', 'laps', 'weekends', 'valid', 'eligible', 'races', 'appearances', 'exclusions', 'ties', 'resamples')):
        kind = 'count'
    elif leaf in ('notes', 'warnings', 'source_files') or 'sha256' in field or isinstance(field, str) and '/' in field:
        kind = 'text'
    else:
        kind = 'label'
    return description, kind


def json_fields(value, path='$'):
    """Include containers and empty arrays as well as every nested JSON field."""
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from json_fields(child, path + '.' + key)
    elif isinstance(value, list):
        for child in value:
            yield from json_fields(child, path + '[]')


def possible_time_flags(field, values):
    reasons = []
    if re.search(r'seconds|lap.?time', field, re.I):
        reasons.append('time-like header')
    clock = []; seconds = []
    for value in values:
        if value is None or isinstance(value, (dict, list, bool)):
            continue
        value = str(value).strip()
        if re.fullmatch(r'(?:\d+:)?\d+:[0-5]\d\.\d+', value):
            clock.append(value)
        try:
            number = Decimal(value)
            if number.is_finite() and 60 <= number <= 130:
                seconds.append(value)
        except InvalidOperation:
            pass
    if clock:
        reasons.append('clock-like m:ss.fff value; examples: ' + ', '.join(dict.fromkeys(clock[:3])))
    if seconds:
        reasons.append('numeric value in inclusive 60–130 range; examples: ' + ', '.join(dict.fromkeys(seconds[:3])))
    return reasons


def inventory(sources):
    entries = []
    for name in ALLOWLIST:
        columns = defaultdict(list)
        if name.endswith('.csv'):
            fields, rows = csv_rows(sources[name])
            for field in fields:
                columns[field] = [row[field] for row in rows]
                # Inspect embedded JSON too; do not hide time-like values inside notes.
                for value in columns[field][:]:
                    if value.lstrip().startswith(('{', '[')):
                        for path, child in json_fields(decode_json(value), field):
                            if path != field:
                                columns[path].append(child)
        else:
            for path, value in json_fields(decode_json(sources[name])):
                columns[path].append(value)
        for field, values in columns.items():
            description, kind = describe(field, name)
            entries.append({'file': name, 'column': field, 'description': description,
                            'classification': kind, 'flags': possible_time_flags(field, values)})
    return entries


def inventory_markdown(entries, validation):
    flagged = [e for e in entries if e['flags']]
    lines = ['# Dashboard column inventory — preflight, not a published package', '',
        '## Flagged columns and fields: review required', '',
        f'{len(flagged)} columns/JSON field paths matched the conservative checks. Packaging is blocked whenever this list is nonempty.', '',
        'Checks: time-like headers (seconds or lap time); whole clock-like values; and any numeric value from 60 through 130 inclusive. Counts and runtimes can match too. None is automatically exempted.', '',
        'The qualifying time-in-seconds fields contain recorded best-lap times, not just gaps. No fields were removed, transformed, or approved for publication. Counts matching the numeric range are flagged for review as well.', '',
        '| File | Column / JSON path | Flag |', '| --- | --- | --- |']
    for e in flagged:
        cells = [e['file'], e['column'], '; '.join(e['flags'])]
        lines.append('| ' + ' | '.join(c.replace('|', '\\|') for c in cells) + ' |')
    # Escape content cell-by-cell in the complete inventory below.
    lines += ['', '## Saved-file validation', '', '```json', json.dumps(validation, indent=2), '```', '',
        'Source bytes exclude metadata, reports and future map/manifest files. No production copies exist while flags remain. Source hash agreement is not a claim of packaged-copy validation.', '',
        '## Complete inventory', '',
        'CSV headers are listed first; embedded JSON and JSON files include nested paths and containers. [] means an array item. Empty containers are retained. No raw values other than a few flagged examples are copied into this report.', '',
        'Classifications: identifier = identity or calendar key; derived gap = saved relative pace; rating = saved rating, score, probability or uncertainty; count = saved evidence amount or coverage fraction; label = setting/category/flag; text = prose, structured provenance or time values requiring review.', '']
    for name in ALLOWLIST:
        lines += ['### ' + name, '', '| Column / JSON path | Classification | Plain description |', '| --- | --- | --- |']
        for e in entries:
            if e['file'] == name:
                cells = [e['column'], e['classification'], e['description']]
                lines.append('| ' + ' | '.join(c.replace('|', '\\|').replace('\n', ' ') for c in cells) + ' |')
        lines.append('')
    return '\n'.join(lines) + '\n'


class ReviewRequired(ValueError):
    pass


def write_new_or_identical(path, content):
    """Repeated checks may read an identical report, but never replace one."""
    if path.exists():
        require(path.read_bytes() == content, 'Existing report differs; choose a new report name')
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(content)


def _copy_bundle(sources, destination):
    """Copy validated bytes; internal primitive tested with synthetic files only."""
    require(set(sources) == set(ALLOWLIST), 'Exactly the allowlisted sources are required')
    filenames = [Path(name).name for name in ALLOWLIST]
    require(len(set(filenames)) == 17, 'Duplicate destination filename')
    destination.mkdir(parents=True, exist_ok=False)
    mapping = {}; manifest = {}
    for name in ALLOWLIST:
        output = destination / Path(name).name
        with output.open('xb') as handle:
            handle.write(sources[name])
        require(sha256(output.read_bytes()) == sha256(sources[name]), 'Packaged copy hash mismatch')
        mapping[name] = RELEASE_PATH + '/' + output.name
        manifest[output.name] = {'source': name, 'bytes': len(sources[name]),
                                 'sha256': sha256(sources[name])}
    for filename, value in [('source_to_package.json', mapping), ('SHA256_MANIFEST.json', manifest)]:
        with (destination / filename).open('x') as handle:
            json.dump(value, handle, indent=2); handle.write('\n')
    return manifest


def prepare(root=ROOT, check_only=False):
    destination = checked_path(root, RELEASE_PATH)
    if destination.exists():
        raise FileExistsError('Release folder already exists; it will never be overwritten')
    sources = load_sources(root)
    metadata = decode_json(checked_path(root, METADATA_PATH).read_bytes())
    validation = validate_saved(sources, metadata)
    entries = inventory(sources)
    report = inventory_markdown(entries, validation).encode()
    write_new_or_identical(checked_path(root, INVENTORY_PATH), report)
    flagged = [e for e in entries if e['flags']]
    if flagged:
        raise ReviewRequired(f'{len(flagged)} flagged columns/fields: see {INVENTORY_PATH}. No release folder created. Source bytes: {validation["source_bytes"]}.')
    if not check_only:
        _copy_bundle(sources, destination)
        with (destination / 'COLUMN_INVENTORY.md').open('xb') as handle:
            handle.write(report)
    return validation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true', help='Validate and inventory without copying a release')
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(check_only=args.check_only), indent=2))
    except (ValueError, OSError) as error:
        parser.exit(2, str(error) + '\n')


if __name__ == '__main__':
    main()
