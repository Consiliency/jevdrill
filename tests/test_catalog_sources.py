import importlib.util
from pathlib import Path
import unittest
from urllib.error import HTTPError

spec = importlib.util.spec_from_file_location('catalog_sources', Path(__file__).resolve().parents[1] / 'scripts/catalog_sources.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SourcesTest(unittest.TestCase):
    def test_github_blob_and_raw_share_identity(self):
        self.assertEqual(module.source_key('https://github.com/Owner/Repo/blob/main/Skills/A.md'),
                         module.source_key('https://raw.githubusercontent.com/owner/repo/pinned/Skills/A.md'))
        self.assertNotEqual(module.source_key('https://github.com/owner/repo/blob/main/A.md'),
                            module.source_key('https://github.com/owner/repo/blob/main/a.md'))

    def test_sync_preserves_history_and_deduplicates_additions(self):
        sources = [{'url': 'https://example.org/library', 'catalog_record_id': 'one'}]
        registry, added = module.reconcile({}, sources, 'first')
        registry['sources'][0]['versions'].append({'sha256': 'existing'})
        result, added_again = module.reconcile(registry, sources * 2, 'second')
        self.assertEqual(len(added), 1)
        self.assertEqual(added_again, [])
        self.assertEqual(result['sources'][0]['first_seen'], 'first')
        self.assertEqual(result['sources'][0]['versions'], [{'sha256': 'existing'}])
        self.assertEqual(result['sources'][0]['catalog_record_ids'], ['one'])

    def test_fetch_failure_is_not_removal(self):
        record = {'url': 'https://example.org/a', 'sha256': 'old', 'versions': []}
        def fail(*args, **kwargs):
            raise HTTPError(record['url'], 503, 'unavailable', {}, None)
        self.assertEqual(module.scan(record, 'now', fail), 'fetch_error')
        self.assertEqual(record['sha256'], 'old')

    def test_not_modified_preserves_content(self):
        record = {'url': 'https://example.org/a', 'scan_url': 'https://example.org/a',
                  'fingerprint_kind': 'raw_http_body', 'sha256': 'old', 'etag': 'tag', 'versions': []}
        def cached(request, **kwargs):
            self.assertEqual(request.get_header('If-none-match'), 'tag')
            raise HTTPError(record['url'], 304, 'not modified', {}, None)
        self.assertEqual(module.scan(record, 'now', cached), 'unchanged')
        self.assertEqual(record['sha256'], 'old')

    def test_github_file_scan_avoids_dynamic_html(self):
        record = {'url': 'https://github.com/owner/repo/blob/main/SKILL.md', 'versions': []}
        def failed_fetch(request, **kwargs):
            self.assertEqual(request.full_url, 'https://raw.githubusercontent.com/owner/repo/main/SKILL.md')
            raise HTTPError(request.full_url, 503, 'unavailable', {}, None)
        self.assertEqual(module.scan(record, 'now', failed_fetch), 'fetch_error')


if __name__ == '__main__':
    unittest.main()
