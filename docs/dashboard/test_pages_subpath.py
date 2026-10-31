"""Keep the static dashboard usable below a GitHub Pages project path."""

from html.parser import HTMLParser
from pathlib import Path
import re
import unittest


DOCS = Path(__file__).resolve().parents[1]
DASHBOARD = DOCS / 'dashboard'
DATA = DOCS / 'data' / '2025' / 'release_2025_001'
BAD_PREFIXES = ('/', 'http://', 'https://', 'file://', 'computer://')


def bad_url(value):
    """A project asset must stay inside the project's relative URL space."""
    value = value.strip().strip('"\'')
    return value.startswith(BAD_PREFIXES)


class LocalAssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.problems = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for key in ('src', 'href'):
            if key in attrs and bad_url(attrs[key]):
                self.problems.append(f'{tag} {key}={attrs[key]}')
        if tag == 'meta' and attrs.get('http-equiv', '').lower() == 'refresh':
            match = re.search(r'\burl\s*=\s*([^;]+)', attrs.get('content', ''), re.I)
            if match and bad_url(match.group(1)):
                self.problems.append('meta refresh=' + match.group(1))


def unsafe_references(suffix, text):
    """Check references that can load resources; ordinary prose is not a URL."""
    problems = []
    if suffix == '.html':
        parser = LocalAssetParser()
        parser.feed(text)
        problems += parser.problems
    if suffix == '.css':
        if re.search(r'@import\b', text, re.I):
            problems.append('CSS @import')
        for match in re.finditer(r'url\(\s*([^)]*)\)', text, re.I):
            if bad_url(match.group(1)):
                problems.append('CSS url=' + match.group(1))
    if suffix == '.js':
        for match in re.finditer(r'\b(?:fetch|fetcher)\s*\(\s*(["\'`])([^"\'`]*)\1', text):
            if bad_url(match.group(2)):
                problems.append('JavaScript fetch=' + match.group(2))
        for match in re.finditer(r'\b(?:src|href)\s*=\s*(["\'`])([^"\'`]*)\1', text):
            if bad_url(match.group(2)):
                problems.append('JavaScript asset=' + match.group(2))
        for match in re.finditer(r'\b(?:BASE|base)\s*=\s*(["\'`])([^"\'`]*)\1', text):
            if bad_url(match.group(2)):
                problems.append('JavaScript base=' + match.group(2))
    return problems


class PagesSubpathTests(unittest.TestCase):
    def test_all_site_resources_are_relative(self):
        for path in DOCS.rglob('*'):
            if path.suffix not in {'.html', '.css', '.js'}:
                continue
            with self.subTest(path=path.relative_to(DOCS)):
                self.assertEqual(unsafe_references(path.suffix, path.read_text()), [])
        data_script = (DASHBOARD / 'data.js').read_text()
        self.assertIn("const BASE = '../data/2025/release_2025_001/';", data_script)
        self.assertIn("url.origin === new URL(pageURL).origin", data_script)

    def test_guard_rejects_root_paths_and_external_resources(self):
        samples = [
            ('.html', '<script src="/dashboard/app.js"></script>'),
            ('.html', '<link href="https://example.invalid/site.css">'),
            ('.html', '<meta http-equiv="refresh" content="0; url=/dashboard/">'),
            ('.css', 'body{background:url(/image.png)}'),
            ('.css', '@import "https://example.invalid/site.css";'),
            ('.js', 'fetch("/data/results.csv")'),
            ('.js', 'const BASE = "https://example.invalid/data/";'),
        ]
        for suffix, text in samples:
            with self.subTest(text=text):
                self.assertTrue(unsafe_references(suffix, text))

    def test_landing_and_data_layout(self):
        landing = (DOCS / 'index.html').read_text()
        self.assertIn('content="0; url=dashboard/"', landing)
        self.assertIn('href="dashboard/"', landing)
        self.assertTrue((DASHBOARD / 'index.html').is_file())
        self.assertTrue((DATA / 'releases.json').is_file())
        self.assertEqual((DOCS / '.nojekyll').read_bytes(), b'')


if __name__ == '__main__':
    unittest.main()
