import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('router', Path(__file__).parents[1] / 'scripts/catalog_router.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class RouterTests(unittest.TestCase):
    def setUp(self):
        self.source = {'id': 'source', 'status': 'ok', 'sha256': 'abc', 'path': 'SKILL.md', 'pinned_source_url': 'https://example.org/pinned'}
        self.review = {'source_id': 'source', 'content_sha': 'abc', 'admission': 'needs_evaluation', 'kind': 'advisor', 'domain_ids': ['a.1', 'b'], 'tasks': ['audit'], 'rationale': 'test'}
        self.taxonomy = {'domains': [{'id': 'a', 'name': 'A', 'subdomains': [{'id': 'a.1', 'name': 'A1'}]}, {'id': 'b', 'name': 'B', 'subdomains': []}]}

    def test_multi_parent_and_determinism(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            report = m.build({'records': [self.source]}, [self.review], self.taxonomy, out)
            index = json.loads((out / 'index.json').read_text())
            self.assertEqual([d['candidate_count'] for d in index['domains']], [1, 1])
            self.assertEqual(report['evidence_version'], m.build({'records': [self.source]}, [self.review], self.taxonomy, out)['evidence_version'])
            self.assertTrue(index['unknown_none'])

    def test_pending_reject_missing_and_mismatch_excluded(self):
        self.assertFalse(m.eligible(None, self.source))
        for change in ({'admission': 'reject'}, {'admission': 'deeper_review'}, {'kind': 'template'}, {'content_sha': 'wrong'}, {'admission': 'approved'}):
            self.assertFalse(m.eligible(dict(self.review, **change), self.source))
        self.assertTrue(m.eligible(self.review, self.source))

    def test_unicode_byte_cap(self):
        pages = m.paginate([{'description': '科学' * 100} for _ in range(100)], {'validation': 'unvalidated'}, cap=1000)
        self.assertEqual(sum(len(p['candidates']) for p in pages), 100)
        self.assertTrue(all(len(m.encoded(p)) <= 1000 for p in pages))
        with self.assertRaises(ValueError):
            m.paginate([{'description': '科学' * 1000}], {}, cap=100)

    def test_unknown_domain_and_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            m.build({'records': [self.source]}, [dict(self.review, domain_ids=['absent'])], self.taxonomy, out)
            index = json.loads((out / 'index.json').read_text())
            self.assertEqual(len(index['unknown_none']['pages']), 1)
            self.assertEqual(m.lookup('missing', {'records': []}, [], out)['status'], 'unknown_none')


if __name__ == '__main__':
    unittest.main()
