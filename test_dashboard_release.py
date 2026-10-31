"""Read-only result checks and synthetic packaging tests; no pipeline runs."""
import ast
import copy
import csv
import io
import json
from pathlib import Path
import re
import socket
import tempfile
import unittest
from unittest.mock import patch

import build_dashboard_release as release

ROOT = Path(__file__).resolve().parent


def csv_bytes(fields, rows):
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode()


def synthetic_sources():
    # These are fixture bytes, not any real timing values or result records.
    return {name: b'{"fixture": "synthetic"}\n' if name.endswith('.json')
            else b'fixture_label\nsynthetic\n' for name in release.ALLOWLIST}


class DashboardReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = release.load_sources(ROOT)
        cls.metadata = release.decode_json((ROOT / release.METADATA_PATH).read_bytes())

    def test_exact_allowlist_matches_seventeen_spec_files(self):
        expected = re.findall(r'^\d+\. `(data/[^`]+)`$', (ROOT / 'DASHBOARD_SPEC.md').read_text(), re.M)
        self.assertEqual(len(expected), 17)
        self.assertEqual(tuple(expected), release.ALLOWLIST)
        self.assertEqual(set(self.sources), set(expected))
        for name in expected:
            self.assertEqual(release.load_allowed(ROOT, name), (ROOT / name).read_bytes())

    def test_traversal_absolute_url_glob_and_aliases_are_blocked(self):
        allowed = release.ALLOWLIST[0]
        bad = ['../' + allowed, 'data/../' + allowed, './' + allowed,
               str(ROOT / allowed), '/tmp/file.csv', 'C:\\data\\file.csv',
               'https://example.invalid/file.csv', 'file:///tmp/file.csv',
               'data/*.csv', 'data/[a-z].csv', 'data/?.csv', 'data//driver_rating_2025.csv',
               'data/%2e%2e/driver_rating_2025.csv', 'data\\driver_rating_2025.csv', '', None]
        for name in bad:
            with self.subTest(name=name), self.assertRaises(ValueError):
                release.load_allowed(ROOT, name)

    def test_forbidden_files_never_enter_allowlist_or_loader(self):
        forbidden = ['cache/fastf1_http_cache.sqlite', 'data/runs/prediction_001/bootstrap.csv',
                     'data/runs/prediction_001/race_finish_status.csv',
                     'data/2024/pilot_completeness.csv', 'PILOT_2024_REPORT.md',
                     'data/race_pace_dry_combined.csv', 'data/raw_laps.csv',
                     'data/2025_01_Australian_Grand_Prix.csv', 'README.md']
        for name in forbidden:
            self.assertNotIn(name, release.ALLOWLIST)
            with self.assertRaises(ValueError):
                release.load_allowed(ROOT, name)
        self.assertFalse(any('cache' in Path(p).parts or '2024' in p or 'pilot' in p
                             or Path(p).name in {'bootstrap.csv', 'race_finish_status.csv'}
                             for p in release.ALLOWLIST))

    def test_symlink_sources_and_output_parents_are_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'real').mkdir()
            (root / 'data').symlink_to(root / 'real', target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'Symlink'):
                release.load_allowed(root, release.ALLOWLIST[0])
            (root / 'docs').symlink_to(root / 'real', target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'Symlink'):
                release.checked_path(root, release.RELEASE_PATH)

    def test_metadata_schema_dates_provenance_and_decisions(self):
        release.validate_metadata(self.metadata, self.sources)
        r = self.metadata['releases'][0]
        self.assertEqual(r['season'], 2025)
        self.assertEqual(r['release_id'], 'release_2025_001')
        self.assertEqual(r['published_at'], '')
        self.assertEqual(r['results_last_updated'], '2026-10-23')
        self.assertEqual(r['date_provenance']['date_kind'], 'repository commit dates')
        self.assertEqual(r['date_provenance']['ratings'], {'date': '2026-10-16', 'commit': '7388c24'})
        self.assertEqual(r['date_provenance']['prediction_run'], {'date': '2026-10-23', 'commit': '86a922d'})
        self.assertEqual(r['hosting'], {'provider': 'GitHub Pages', 'branch': 'main', 'folder': 'docs/'})
        self.assertEqual(len(r['views']), 5)
        self.assertEqual(r['groups'], sorted(r['groups']))
        self.assertFalse(r['display_rules']['global_leaderboard'])
        self.assertFalse(r['display_rules']['rank_numbers'])
        self.assertEqual(r['display_rules']['driver_order'], 'alphabetical')
        self.assertEqual(r['teaching_examples']['purpose'], 'teaching examples, not top results')
        self.assertEqual([e['group'] for e in r['teaching_examples']['examples']], ['HAM+LEC', 'NOR+PIA'])
        self.assertEqual(len(r['sources']), 17)
        self.assertEqual(r['unofficial_project_disclaimer'], release.DISCLAIMER)
        for key in ('results_last_updated', 'groups', 'sources', 'published_at'):
            bad = copy.deepcopy(self.metadata)
            del bad['releases'][0][key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                release.validate_metadata(bad, self.sources)

    def test_saved_counts_notes_periods_primary_rows_hashes_and_size(self):
        result = release.validate_saved(self.sources, self.metadata)
        self.assertEqual([result[k] for k in ('drivers', 'groups', 'notes_json', 'period_signal_rows',
                                            'main_pair_races', 'main_weekends', 'main_exclusions')],
                         [21, 9, 21, 78, 95, 12, 25])
        self.assertEqual(result['primary_metrics'], ['accuracy', 'brier', 'log_loss'])
        self.assertEqual(result['source_bytes'], 1701233)
        self.assertEqual(result['byte_difference_from_spec'], 0)
        self.assertEqual(result['packaged_hashes'], 'not checked until package exists')

    def test_changed_rating_bytes_fail_saved_prediction_hash(self):
        bad = dict(self.sources)
        bad['data/driver_rating_2025.csv'] += b'\n'
        with self.assertRaisesRegex(ValueError, 'Prediction source hash'):
            release.validate_saved(bad, release.metadata_for(bad))

    def test_period_disagreement_is_rejected(self):
        bad = dict(self.sources)
        name = 'data/driver_rating_teammate_periods.csv'
        fields, rows = release.csv_rows(bad[name])
        rows[0]['rating'] = '123.000'
        bad[name] = csv_bytes(fields, rows)
        with self.assertRaisesRegex(ValueError, 'Period mean'):
            release.validate_saved(bad, release.metadata_for(bad))

    def test_missing_primary_metric_is_rejected(self):
        bad = dict(self.sources)
        name = release.RUN + 'comparisons.csv'
        fields, rows = release.csv_rows(bad[name])
        rows = [r for r in rows if not (r['target'] == 'main_both_finish' and r['period'] == 'main'
                and r['comparison'] == 'primary' and r['metric'] == 'brier')]
        bad[name] = csv_bytes(fields, rows)
        with self.assertRaisesRegex(ValueError, 'Primary comparison'):
            release.validate_saved(bad, release.metadata_for(bad))

    def test_time_header_clock_range_and_counts_all_require_review(self):
        for field, values in [('lap_time', ['']), ('driver_time_seconds', ['45']),
                              ('value', ['1:20.123']), ('sample', ['60', '130']),
                              ('pair_count', ['95'])]:
            with self.subTest(field=field):
                self.assertTrue(release.possible_time_flags(field, values))
        self.assertFalse(release.possible_time_flags('rating', ['-.1', '', '59.99', '130.01']))
        sources = synthetic_sources()
        sources[release.ALLOWLIST[0]] = b'notes\n"{""lap_time"": ""1:20.123""}"\n'
        flagged = [e for e in release.inventory(sources) if e['flags']]
        self.assertTrue(any(e['column'] == 'notes.lap_time' for e in flagged))

    def test_inventory_covers_every_column_and_json_field(self):
        entries = release.inventory(self.sources)
        keys = {(e['file'], e['column']) for e in entries}
        for name, data in self.sources.items():
            if name.endswith('.csv'):
                for field in release.csv_rows(data)[0]:
                    self.assertIn((name, field), keys)
            else:
                for field, _ in release.json_fields(release.decode_json(data)):
                    self.assertIn((name, field), keys)
        self.assertTrue(all(e['description'] and e['classification'] in
            {'identifier', 'derived gap', 'rating', 'count', 'label', 'text'} for e in entries))
        time_fields = [e for e in entries if e['file'].endswith('qualifying_gaps_by_round.csv')
                       and 'time_seconds' in e['column']]
        self.assertEqual(len(time_fields), 10)
        self.assertTrue(all(e['flags'] for e in time_fields))

    def test_review_gate_creates_no_release_or_source_copies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / release.METADATA_PATH
            path.parent.mkdir()
            path.write_text(json.dumps(self.metadata))
            with patch.object(release, 'load_sources', return_value=self.sources):
                with self.assertRaises(release.ReviewRequired):
                    release.prepare(root)
            self.assertFalse((root / 'docs').exists())
            self.assertEqual({p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()},
                             {release.METADATA_PATH, release.INVENTORY_PATH})
            self.assertIn('preflight, not a published package', (root / release.INVENTORY_PATH).read_text())

    def test_synthetic_packaging_copies_exactly_seventeen_files_and_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / 'release'
            sources = synthetic_sources()
            manifest = release._copy_bundle(sources, destination)
            self.assertEqual(set(manifest), {Path(p).name for p in release.ALLOWLIST})
            self.assertEqual(len(manifest), 17)
            self.assertEqual({p.name for p in destination.iterdir()},
                set(manifest) | {'source_to_package.json', 'SHA256_MANIFEST.json'})
            mapping = json.loads((destination / 'source_to_package.json').read_text())
            for name, data in sources.items():
                filename = Path(name).name
                self.assertEqual((destination / filename).read_bytes(), data)
                self.assertEqual(manifest[filename]['sha256'], release.sha256(data))
                self.assertEqual(manifest[filename]['bytes'], len(data))
                self.assertEqual(mapping[name], release.RELEASE_PATH + '/' + filename)
            self.assertEqual(json.loads((destination / 'SHA256_MANIFEST.json').read_text()), manifest)

    def test_overwrite_refused_and_existing_folder_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            destination = root / release.RELEASE_PATH
            release._copy_bundle(synthetic_sources(), destination)
            before = {p.name: p.read_bytes() for p in destination.iterdir()}
            with self.assertRaises(FileExistsError):
                release._copy_bundle(synthetic_sources(), destination)
            with self.assertRaises(FileExistsError):
                release.prepare(root)
            self.assertEqual(before, {p.name: p.read_bytes() for p in destination.iterdir()})

    def test_extra_source_cannot_be_copied(self):
        with tempfile.TemporaryDirectory() as directory:
            sources = synthetic_sources()
            sources['cache/raw.csv'] = b'no'
            destination = Path(directory) / 'release'
            with self.assertRaises(ValueError):
                release._copy_bundle(sources, destination)
            self.assertFalse(destination.exists())

    def test_network_never_used_and_no_pipeline_imports(self):
        with patch.object(socket, 'create_connection', side_effect=AssertionError('network')) as connection, \
             patch.object(socket, 'getaddrinfo', side_effect=AssertionError('DNS')) as dns, \
             patch.object(socket.socket, 'connect', side_effect=AssertionError('connect')) as connect, \
             patch.object(socket.socket, 'connect_ex', side_effect=AssertionError('connect_ex')) as connect_ex:
            loaded = release.load_sources(ROOT)
            release.validate_saved(loaded, self.metadata)
            release.inventory(loaded)
            with tempfile.TemporaryDirectory() as directory:
                release._copy_bundle(synthetic_sources(), Path(directory) / 'release')
            for mocked in (connection, dns, connect, connect_ex):
                mocked.assert_not_called()
        tree = ast.parse((ROOT / 'build_dashboard_release.py').read_text())
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add(node.module)
        self.assertLessEqual(imports, {'argparse', 'collections', 'csv', 'decimal', 'hashlib',
                                      'io', 'json', 'pathlib', 're'})


if __name__ == '__main__':
    unittest.main()
