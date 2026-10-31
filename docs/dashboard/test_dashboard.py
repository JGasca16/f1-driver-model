"""Offline file and saved-data checks. No server, pipeline or network calls.

Run separately from the repository suite: unittest discover -s docs/dashboard.
JavaScript behavior tests live beside this file in test_dashboard.cjs.
"""
import csv
import hashlib
import json
from pathlib import Path
import re
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PACKAGE = HERE.parent / 'data' / '2025' / 'release_2025_001'


class DashboardFilesTests(unittest.TestCase):
    def test_only_local_scripts_and_styles(self):
        html = (HERE / 'index.html').read_text()
        for value in re.findall(r'(?:src|href)="([^"]+)"', html):
            if value.startswith(('#', 'data:')):
                continue
            self.assertNotIn('://', value)
            self.assertTrue((HERE / value).is_file(), value)
        self.assertIn("connect-src 'self'", html)
        self.assertIn("font-src 'none'", html)
        self.assertNotIn('style=', html)

    def test_four_routes_without_race_gap_view(self):
        html = (HERE / 'index.html').read_text()
        self.assertEqual(re.findall(r'data-view="([^"]+)"', html),
                         ['overview', 'drivers', 'prediction', 'method'])
        self.assertNotIn('race_gaps', (HERE / 'app.js').read_text())

    def test_keyboard_and_theme_support(self):
        html = (HERE / 'index.html').read_text()
        css = (HERE / 'styles.css').read_text()
        self.assertIn('Skip to content', html)
        self.assertIn('lang="en"', html)
        self.assertIn('prefers-color-scheme:dark', css)
        self.assertIn(':focus-visible', css)
        self.assertIn('@media(max-width:600px)', css)
        self.assertIn('prefers-reduced-motion', css)
        self.assertNotIn('@import', css)
        self.assertNotIn('url(', css)

    def test_all_copy_has_source_tags_and_exact_rules_stay_verbatim(self):
        def normalize(s):
            s = re.sub(r'^>\s?', '', s, flags=re.MULTILINE)
            s = re.sub(r'(?<=-)\n\s*', '', s)
            return re.sub(r'\s+', ' ', s.replace('**', '').replace('`', '')).strip()
        text = (HERE / 'content.js').read_text()
        blocks = json.loads(re.search(r'const blocks = (.*?);\n', text, re.S)[1])
        exact = json.loads(re.search(r'const exact = (.*?);\n', text, re.S)[1])
        self.assertGreaterEqual(len(blocks), 41)
        for file, section, copy in blocks.values():
            self.assertTrue((ROOT / file).is_file())
            self.assertTrue(section)
            self.assertTrue(copy)
        self.assertEqual(len(exact), 46)
        for file, section, copy in exact.values():
            self.assertIn(normalize(copy), normalize((ROOT / file).read_text()), file)
        self.assertIn('data-copy=', (HERE / 'views.js').read_text())
        self.assertIn('data-origin=', (HERE / 'views.js').read_text())
        self.assertIn('for the differences includes zero', blocks['reading'][2])
        dry = (ROOT / 'METHOD_DRY_RACEPACE.md').read_text()
        wet = (ROOT / 'METHOD_WET_RACEPACE.md').read_text()
        self.assertRegex(dry, r'200 dry-race pairs, 32')
        self.assertRegex(wet, r'6 of (?:the )?30')

    def test_no_local_paths_in_any_new_file(self):
        markers = ['/' + 'Users/', '/' + 'home/', 'C' + ':', '~' + '/', 'joseenrique' + 'gasca']
        for path in HERE.rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts:
                continue
            text = path.read_text().casefold()
            for marker in markers:
                self.assertNotIn(marker.casefold(), text, str(path.relative_to(HERE)))

    def test_every_packaged_source_hash_still_matches(self):
        release = json.loads((PACKAGE / 'releases.json').read_text())['releases'][0]
        for source in release['sources']:
            file = PACKAGE / Path(source['package_path']).name
            self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(), source['source_sha256'])

    def test_saved_scopes_and_periods(self):
        def rows(name):
            with (PACKAGE / name).open() as f:
                return list(csv.DictReader(f))
        ratings = rows('driver_rating_2025.csv')
        self.assertEqual(len(ratings), 21)
        self.assertEqual(len({r['comparison_group'] for r in ratings}), 9)
        self.assertEqual(len(rows('driver_rating_teammate_periods.csv')), 78)
        scores = [r for r in rows('metrics.csv') if r['target'] == 'main_both_finish' and r['period'] == 'main']
        self.assertEqual(len(scores), 8)
        self.assertTrue(all((r['pair_count'], r['weekend_count'], r['excluded_pair_count']) == ('95', '12', '25') for r in scores))

    def test_no_pipeline_or_external_library_imports(self):
        for name in ['content.js', 'data.js', 'views.js', 'app.js']:
            text = (HERE / name).read_text()
            self.assertNotRegex(text, r'\bimport\s|require\(')
            self.assertNotIn('XMLHttpRequest', text)
            self.assertNotIn('WebSocket', text)
            self.assertNotIn('sendBeacon', text)
        app = (HERE / 'app.js').read_text()
        self.assertEqual(app.count('loader.load(\'predictions\')'), 1)
        self.assertLess(app.index("on('audit-drawer','toggle'"), app.index("loader.load('predictions')"))


if __name__ == '__main__':
    unittest.main()
