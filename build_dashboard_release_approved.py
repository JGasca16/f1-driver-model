"""Apply the owner's exact column approvals and package saved results offline.

This addition leaves the earlier builder, metadata and preflight report intact.
Run without arguments to create the release once, or --check-only to inspect
all planned publication bytes without writing them. It never runs a pipeline.
"""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import build_dashboard_release as base

QUALIFYING = 'data/2025_qualifying_gaps_by_round.csv'
KEPT_TIMES = frozenset((QUALIFYING, column) for column in (
    'driver_time_seconds', 'teammate_time_seconds',
    'driver_best_qualifying_time_seconds', 'teammate_best_qualifying_time_seconds',
    'q1_driver_time_seconds', 'q1_teammate_time_seconds',
    'q2_driver_time_seconds', 'q2_teammate_time_seconds',
    'q3_driver_time_seconds', 'q3_teammate_time_seconds',
))
# Each approval is a full source path plus one exact field, never a pattern.
SAFE_FIELDS = frozenset({
    ('data/driver_rating_run_summary.json', '$.runtime_seconds'),
    ('data/race_pace_dry_final.csv', 'matched_laps'),
    ('data/race_pace_dry_final.csv', 'driver_clean_laps'),
    ('data/race_pace_dry_final.csv', 'teammate_clean_laps'),
    ('data/runs/prediction_001/metrics.csv', 'pair_count'),
    ('data/runs/prediction_001/metrics.csv', 'ties'),
    ('data/runs/prediction_001/comparisons.csv', 'pair_count'),
    ('data/runs/prediction_001/counts.csv', 'initial_training_rows'),
    ('data/runs/prediction_001/counts.csv', 'main_rows'),
    ('data/runs/prediction_001/summary.json', '$.runtime_seconds'),
    ('data/runs/prediction_001/summary.json', '$.counts[].initial_training_rows'),
    ('data/runs/prediction_001/summary.json', '$.counts[].main_rows'),
    ('data/runs/prediction_001/summary.json', '$.status_counts.Lapped'),
    ('data/runs/prediction_001/prediction_test_config.json', '$.bootstrap.percentiles[]'),
    ('data/runs/prediction_001/group_stability.csv', 'remaining_pairs'),
    ('data/runs/prediction_001/predictions.csv', 'training_rows'),
})
LOCAL_MARKERS = ('/Users/', '/home/', 'C:\\', '~/', 'joseenriquegasca')
ADMIN_FILES = frozenset({'releases.json', 'COLUMN_INVENTORY.md',
                        'source_to_package.json', 'SHA256_MANIFEST.json'})


class PublicationBlocked(ValueError):
    """Report every offending file and field without rewriting its contents."""


def decision(file, field):
    key = (file, field)
    if key in KEPT_TIMES:
        return 'kept by owner decision'
    if key in SAFE_FIELDS:
        return 'approved safe'
    return 'blocked: not approved'


def reviewed_flags(entries):
    # Detection is the original builder's unchanged inventory and time rule.
    return [dict(e, decision=decision(e['file'], e['column']))
            for e in entries if e['flags']]


def require_approved(flags):
    blocked = [e for e in flags if e['decision'] == 'blocked: not approved']
    if blocked:
        lines = ['Unapproved flagged fields; packaging stopped:']
        lines += [e['file'] + ' | ' + e['column'] + ' | ' + '; '.join(e['flags']) for e in blocked]
        raise PublicationBlocked('\n'.join(lines))


def scan_file(name, content):
    """Scan lines and decoded cells/values, including escaped JSON inside CSV."""
    text = content.decode('utf-8')
    matches = []

    def check(location, value):
        if not isinstance(value, str):
            return
        lower = value.casefold()
        for marker in LOCAL_MARKERS:
            if marker.casefold() in lower:
                matches.append({'file': name, 'location': location, 'marker': marker})

    def walk(value, location):
        if isinstance(value, dict):
            for key, child in value.items():
                check(location + ' (key)', key)
                walk(child, location + '.' + key)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f'{location}[{index}]')
        elif isinstance(value, str):
            check(location, value)
            # A CSV notes cell or a JSON value may itself contain encoded JSON.
            if value.lstrip().startswith(('{', '[')):
                try:
                    embedded = base.decode_json(value)
                except (ValueError, TypeError):
                    return
                walk(embedded, location + ' (embedded JSON)')

    # Also scan headers, keys and prose, so no content is skipped by parsing.
    for number, line in enumerate(text.splitlines(), 1):
        check(f'line {number}', line)
    suffix = Path(name).suffix
    if suffix == '.csv':
        _, rows = base.csv_rows(content)
        for number, row in enumerate(rows, 2):
            for field, value in row.items():
                walk(value, f'CSV row {number}, column {field}')
    elif suffix == '.json':
        walk(base.decode_json(content), '$')
    else:
        base.require(suffix == '.md', 'Unrecognized publication format: ' + name)
    return matches


def scan_files(files):
    return [match for name, content in files.items() for match in scan_file(name, content)]


def require_no_paths(matches, stage):
    if matches:
        lines = [stage + ': local-path matches; packaging stopped. No data was rewritten.']
        lines += [m['file'] + ' | ' + m['location'] + ' | marker ' + m['marker'] for m in matches]
        raise PublicationBlocked('\n'.join(lines))


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()


def approved_metadata(original):
    metadata = deepcopy(original)
    release = metadata['releases'][0]
    release['owner_column_decisions'] = {
        'qualifying_time_description': 'These columns hold recorded qualifying lap times in seconds. '
            'They are kept as recorded, with no removal or transformation.',
        'approvals': [
            {'source': file, 'field': field, 'decision': decision(file, field)}
            for file, field in sorted(KEPT_TIMES | SAFE_FIELDS)
        ],
        'scope': 'Only the exact source-file and field pairs listed here are approved. '
                 'Any other detected field still blocks packaging. The detection rule is unchanged.',
        'prediction_audit_fields': 'Finishing positions and statuses in predictions.csv are kept unchanged.',
        'local_path_policy': 'Every source and planned publication file must pass the local-path scan. '
                             'Every written package file is scanned again. Matches block completion; nothing is stripped.',
    }
    return metadata


def approved_inventory(entries, flags, validation):
    counts = Counter(e['decision'] for e in flags)
    lines = ['# Dashboard column inventory — owner-reviewed release', '',
        f"Flags: {counts['kept by owner decision']} kept by owner decision; "
        f"{counts['approved safe']} approved safe; {counts['blocked: not approved']} still blocked.", '',
        'The 10 named qualifying columns hold recorded qualifying lap times in seconds. '
        'Their contents are kept byte-for-byte, with no removal or transformation. '
        'Finishing positions and statuses in predictions.csv are also kept unchanged.', '',
        'The original detection rule remains in force. Approvals match the exact source path '
        'and exact column or JSON path; every other flagged field blocks packaging.', '',
        '| Source file | Column / JSON path | Owner decision | Detection flag |',
        '| --- | --- | --- | --- |']
    for e in flags:
        cells = [e['file'], e['column'], e['decision'], '; '.join(e['flags'])]
        lines.append('| ' + ' | '.join(c.replace('|', '\\|') for c in cells) + ' |')
    saved = dict(validation)
    saved.pop('packaged_hashes')
    lines += ['', '## Saved-file validation', '', '```json', json.dumps(saved, indent=2), '```', '',
        'The source-byte total covers the 17 saved result/config files only. '
        'The four administrative files are additional: this inventory, releases.json, '
        'source_to_package.json and SHA256_MANIFEST.json.', '',
        'Before writing, all source CSV cells, JSON values and all generated publication '
        'text are scanned. After writing, every package file is rescanned and compared '
        'with the validated bytes. A successful builder run confirms both checks. '
        'The SHA-256 manifest records all 17 source copies.', '']
    # Update review wording in this new report only; detection stays unchanged.
    published_entries = deepcopy(entries)
    for entry in published_entries:
        if (entry['file'], entry['column']) in KEPT_TIMES:
            entry['description'] = entry['description'].replace(
                '; requires review.', '; kept by owner decision.')
    complete = base.inventory_markdown(published_entries, validation).split('## Complete inventory', 1)[1]
    lines += ['## Complete inventory', complete]
    return '\n'.join(lines).encode()


def publication_plan(sources, metadata):
    require_no_paths(scan_files(sources), 'Source files')
    # Scan the original metadata too, even though only its approved copy is published.
    require_no_paths(scan_file('dashboard_data/releases.json', json_bytes(metadata)), 'Source metadata')
    validation = base.validate_saved(sources, metadata)
    base.require(validation['source_bytes'] == base.EXPECTED_BYTES, 'Source bytes differ from the approved spec')
    entries = base.inventory(sources)
    flags = reviewed_flags(entries)
    require_approved(flags)
    files = {Path(name).name: content for name, content in sources.items()}
    base.require(len(files) == 17, 'Source filenames collide')
    files['releases.json'] = json_bytes(approved_metadata(metadata))
    files['COLUMN_INVENTORY.md'] = approved_inventory(entries, flags, validation)
    files['source_to_package.json'] = json_bytes({name: base.RELEASE_PATH + '/' + Path(name).name
                                               for name in base.ALLOWLIST})
    files['SHA256_MANIFEST.json'] = json_bytes({Path(name).name: {
        'source': name, 'bytes': len(content), 'sha256': base.sha256(content)}
        for name, content in sources.items()})
    require_no_paths(scan_files(files), 'Planned publication files')
    counts = Counter(e['decision'] for e in flags)
    result = dict(validation, kept_fields=counts['kept by owner decision'],
                  approved_safe_fields=counts['approved safe'], blocked_fields=0,
                  source_local_path_matches=0, planned_publication_local_path_matches=0,
                  source_files=17, publication_files=len(files))
    return files, result


def verify_package(destination, planned, sources):
    """Scan every written file, including administrative files, then check bytes."""
    actual = {}
    for path in destination.rglob('*'):
        base.require(not path.is_symlink(), 'Unexpected symlink in package')
        if path.is_file():
            actual[path.relative_to(destination).as_posix()] = path.read_bytes()
    # Scan before rejecting an unexpected file so any local path in it is listed.
    require_no_paths(scan_files(actual), 'Packaged copy')
    base.require(set(actual) == set(planned), 'Unexpected or missing package file')
    for name in planned:
        base.require(actual[name] == planned[name], 'Packaged bytes differ: ' + name)
    for source, content in sources.items():
        base.require(base.sha256(actual[Path(source).name]) == base.sha256(content),
                     'Source/package hash mismatch: ' + source)
    return {'packaged_local_path_matches': 0, 'packaged_hashes': '17 of 17 match their sources',
            'all_publication_bytes_verified': len(actual)}


def prepare(root=base.ROOT, check_only=False):
    destination = base.checked_path(root, base.RELEASE_PATH)
    if destination.exists():
        raise FileExistsError('Existing release folder is never overwritten')
    sources = base.load_sources(root)
    metadata = base.decode_json(base.checked_path(root, base.METADATA_PATH).read_bytes())
    planned, result = publication_plan(sources, metadata)
    if check_only:
        return dict(result, packaged_local_path_matches='not run: check-only', package_created=False)
    destination.mkdir(parents=True, exist_ok=False)
    for name, content in planned.items():
        with (destination / name).open('xb') as handle:
            handle.write(content)
    # On failure, stop and report. Never strip or rewrite the copied evidence.
    result.update(verify_package(destination, planned, sources))
    return dict(result, package_created=True, release_folder=base.RELEASE_PATH)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(check_only=args.check_only), indent=2))
    except (ValueError, OSError) as error:
        parser.exit(2, str(error) + '\n')


if __name__ == '__main__':
    main()
