"""Exact owner approvals, privacy scans and unchanged-byte release packaging."""
from copy import deepcopy
import csv
import io
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

import build_dashboard_release as base
import build_dashboard_release_approved as approved


class ApprovedDashboardReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = base.load_sources(base.ROOT)
        cls.metadata = base.decode_json((base.ROOT / base.METADATA_PATH).read_bytes())
        cls.planned, cls.result = approved.publication_plan(cls.sources, cls.metadata)

    def setup_root(self, directory):
        root = Path(directory)
        path = root / base.METADATA_PATH
        path.parent.mkdir()
        path.write_bytes(approved.json_bytes(self.metadata))
        return root

    def write_fixture_package(self, directory):
        destination = Path(directory) / 'package'
        destination.mkdir()
        for name, content in self.planned.items():
            (destination / name).write_bytes(content)
        return destination

    def test_exact_ten_time_columns_and_sixteen_safe_pairs(self):
        times = {'driver_time_seconds', 'teammate_time_seconds',
                 'driver_best_qualifying_time_seconds', 'teammate_best_qualifying_time_seconds',
                 'q1_driver_time_seconds', 'q1_teammate_time_seconds',
                 'q2_driver_time_seconds', 'q2_teammate_time_seconds',
                 'q3_driver_time_seconds', 'q3_teammate_time_seconds'}
        self.assertEqual(approved.KEPT_TIMES,
            {('data/2025_qualifying_gaps_by_round.csv', f) for f in times})
        safe = {
            'data/driver_rating_run_summary.json': ['$.runtime_seconds'],
            'data/race_pace_dry_final.csv': ['matched_laps', 'driver_clean_laps', 'teammate_clean_laps'],
            'data/runs/prediction_001/metrics.csv': ['pair_count', 'ties'],
            'data/runs/prediction_001/comparisons.csv': ['pair_count'],
            'data/runs/prediction_001/counts.csv': ['initial_training_rows', 'main_rows'],
            'data/runs/prediction_001/summary.json': ['$.runtime_seconds', '$.counts[].initial_training_rows',
                                                   '$.counts[].main_rows', '$.status_counts.Lapped'],
            'data/runs/prediction_001/prediction_test_config.json': ['$.bootstrap.percentiles[]'],
            'data/runs/prediction_001/group_stability.csv': ['remaining_pairs'],
            'data/runs/prediction_001/predictions.csv': ['training_rows'],
        }
        self.assertEqual(approved.SAFE_FIELDS, {(p, f) for p, fields in safe.items() for f in fields})
        self.assertEqual(len(approved.SAFE_FIELDS), 16)
        for p, f in approved.KEPT_TIMES:
            self.assertEqual(approved.decision(p, f), 'kept by owner decision')
        for p, f in approved.SAFE_FIELDS:
            self.assertEqual(approved.decision(p, f), 'approved safe')

    def test_wrong_file_field_spelling_and_alias_are_not_approved(self):
        for file, field in approved.KEPT_TIMES | approved.SAFE_FIELDS:
            for p, f in [('other/' + file, field), (file, field + '_extra'),
                         (file, field.upper()), ('./' + file, field)]:
                with self.subTest(file=p, field=f):
                    self.assertEqual(approved.decision(p, f), 'blocked: not approved')
        self.assertEqual(approved.decision('data/runs/prediction_001/summary.json',
                                          '$.counts[0].main_rows'), 'blocked: not approved')

    def test_detection_is_unchanged_and_unapproved_flags_are_listed(self):
        entries = base.inventory(self.sources)
        original = deepcopy(entries)
        flags = approved.reviewed_flags(entries)
        self.assertEqual(entries, original)
        self.assertEqual(len(flags), 26)
        self.assertEqual(sum(f['decision'] == 'kept by owner decision' for f in flags), 10)
        self.assertEqual(sum(f['decision'] == 'approved safe' for f in flags), 16)
        new_entry = {'file': base.ALLOWLIST[0], 'column': 'unapproved_seconds',
                     'flags': base.possible_time_flags('unapproved_seconds', ['90'])}
        self.assertTrue(new_entry['flags'])
        with self.assertRaises(approved.PublicationBlocked) as error:
            approved.require_approved(approved.reviewed_flags(entries + [new_entry]))
        self.assertIn(new_entry['file'], str(error.exception))
        self.assertIn('unapproved_seconds', str(error.exception))
        self.assertTrue(base.possible_time_flags('pair_count', ['95']))

    def test_metadata_and_inventory_record_each_owner_decision(self):
        metadata = base.decode_json(self.planned['releases.json'])
        decisions = metadata['releases'][0].pop('owner_column_decisions')
        self.assertEqual(metadata, self.metadata)
        self.assertIn('recorded qualifying lap times in seconds', decisions['qualifying_time_description'])
        self.assertEqual(len(decisions['approvals']), 26)
        self.assertEqual({(e['source'], e['field']) for e in decisions['approvals']},
                         approved.KEPT_TIMES | approved.SAFE_FIELDS)
        report = self.planned['COLUMN_INVENTORY.md'].decode()
        for file, field in approved.KEPT_TIMES | approved.SAFE_FIELDS:
            self.assertIn('| ' + file + ' | ' + field + ' | ' + approved.decision(file, field) + ' |', report)
        self.assertIn('10 kept by owner decision; 16 approved safe; 0 still blocked', report)

    def test_all_five_markers_are_found_in_csv_json_and_markdown(self):
        for marker in ('/Users/', '/home/', 'C:\\', '~/', 'joseenriquegasca'):
            value = 'prefix ' + marker + 'private suffix'
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['driver', 'notes'])
            writer.writerow(['AAA', value])
            formats = {
                'sample.csv': output.getvalue().encode(),
                'sample.json': approved.json_bytes({'nested': [value]}),
                'sample.md': ('# Report\n' + value + '\n').encode(),
            }
            for name, content in formats.items():
                with self.subTest(marker=marker, file=name):
                    matches = approved.scan_file(name, content)
                    self.assertTrue(matches)
                    self.assertTrue(all(m['file'] == name and m['location'] for m in matches))
                    self.assertTrue(any(m['marker'] == marker for m in matches))
                    if name.endswith('.csv'):
                        self.assertTrue(any(m['location'] == 'CSV row 2, column notes' for m in matches))
                    if name.endswith('.json'):
                        self.assertTrue(any(m['location'] == '$.nested[0]' for m in matches))

    def test_encoded_paths_in_json_and_embedded_csv_json_are_found(self):
        data = br'{"nested":["\u002fUsers\u002fprivate"]}'
        self.assertTrue(any(m['location'] == '$.nested[0]' for m in approved.scan_file('values.json', data)))
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['notes'])
        writer.writerow([data.decode()])
        matches = approved.scan_file('values.csv', output.getvalue().encode())
        self.assertTrue(any('embedded JSON' in m['location'] for m in matches))

    def test_original_metadata_and_planned_markdown_are_scanned(self):
        metadata = deepcopy(self.metadata)
        metadata['releases'][0]['repository_url'] = '/home/private'
        with self.assertRaisesRegex(approved.PublicationBlocked, 'Source metadata'):
            approved.publication_plan(self.sources, metadata)
        with patch.object(approved, 'approved_inventory', return_value=b'# Inventory\n~/private\n'):
            with self.assertRaisesRegex(approved.PublicationBlocked, 'COLUMN_INVENTORY.md'):
                approved.publication_plan(self.sources, self.metadata)

    def test_source_local_path_stops_before_release_creation_without_rewriting(self):
        sources = dict(self.sources)
        name = 'data/driver_rating_teammate_periods.csv'
        fields, rows = base.csv_rows(sources[name])
        rows[0]['warnings'] = '/Users/private'
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
        sources[name] = output.getvalue().encode()
        before = dict(sources)
        with tempfile.TemporaryDirectory() as directory:
            root = self.setup_root(directory)
            with patch.object(base, 'load_sources', return_value=sources):
                with self.assertRaisesRegex(approved.PublicationBlocked, 'column warnings'):
                    approved.prepare(root)
            self.assertFalse((root / 'docs').exists())
        self.assertEqual(before, sources)

    def test_new_unapproved_field_blocks_creation_and_is_reported(self):
        entries = base.inventory(self.sources)
        entries.append({'file': base.ALLOWLIST[0], 'column': 'extra_lap_time',
                        'flags': base.possible_time_flags('extra_lap_time', ['1:20.123'])})
        with tempfile.TemporaryDirectory() as directory:
            root = self.setup_root(directory)
            with patch.object(base, 'load_sources', return_value=self.sources), \
                 patch.object(base, 'inventory', return_value=entries):
                with self.assertRaisesRegex(approved.PublicationBlocked, 'extra_lap_time'):
                    approved.prepare(root)
            self.assertFalse((root / 'docs').exists())

    def test_success_checks_all_publication_files_and_all_source_hashes(self):
        self.assertEqual(len(self.planned), 21)
        self.assertEqual(set(self.planned), {Path(p).name for p in base.ALLOWLIST} | approved.ADMIN_FILES)
        self.assertEqual(approved.scan_files(self.sources), [])
        self.assertEqual(approved.scan_files(self.planned), [])
        with tempfile.TemporaryDirectory() as directory:
            root = self.setup_root(directory)
            with patch.object(base, 'load_sources', return_value=self.sources):
                result = approved.prepare(root)
            self.assertTrue(result['package_created'])
            self.assertEqual(result['source_bytes'], 1701233)
            self.assertEqual(result['all_publication_bytes_verified'], 21)
            self.assertEqual(result['packaged_local_path_matches'], 0)
            destination = root / base.RELEASE_PATH
            for name, data in self.sources.items():
                self.assertEqual(base.sha256((destination / Path(name).name).read_bytes()), base.sha256(data))
            # Full-file equality also preserves all finishing-position/status cells.
            self.assertEqual((destination / 'predictions.csv').read_bytes(), self.sources[base.RUN + 'predictions.csv'])
            before = {p.name: p.read_bytes() for p in destination.iterdir()}
            with self.assertRaises(FileExistsError):
                approved.prepare(root)
            self.assertEqual(before, {p.name: p.read_bytes() for p in destination.iterdir()})

    def test_post_copy_scan_detects_contamination_in_every_file_type(self):
        for name, content in [('metrics.csv', b'notes\n/home/private\n'),
                              ('releases.json', b'{"nested":"C:\\\\private"}'),
                              ('COLUMN_INVENTORY.md', b'# Inventory\n~/private\n'),
                              ('source_to_package.json', b'{"mapping":"/Users/private"}'),
                              ('SHA256_MANIFEST.json', b'{"note":"joseenriquegasca"}')]:
            with self.subTest(file=name), tempfile.TemporaryDirectory() as directory:
                destination = self.write_fixture_package(directory)
                (destination / name).write_bytes(content)
                with self.assertRaises(approved.PublicationBlocked) as error:
                    approved.verify_package(destination, self.planned, self.sources)
                self.assertIn(name, str(error.exception))
                self.assertEqual((destination / name).read_bytes(), content)

    def test_changed_package_bytes_without_local_paths_also_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = self.write_fixture_package(directory)
            path = destination / 'metrics.csv'
            path.write_bytes(path.read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'Packaged bytes differ'):
                approved.verify_package(destination, self.planned, self.sources)

    def test_network_is_unused(self):
        with patch.object(socket, 'create_connection', side_effect=AssertionError('network')) as connection, \
             patch.object(socket, 'getaddrinfo', side_effect=AssertionError('DNS')) as dns, \
             patch.object(socket.socket, 'connect', side_effect=AssertionError('network')) as connect:
            planned, result = approved.publication_plan(self.sources, self.metadata)
            with tempfile.TemporaryDirectory() as directory:
                destination = self.write_fixture_package(directory)
                approved.verify_package(destination, planned, self.sources)
            for mocked in (connection, dns, connect):
                mocked.assert_not_called()
            self.assertEqual(result['blocked_fields'], 0)


if __name__ == '__main__':
    unittest.main()
