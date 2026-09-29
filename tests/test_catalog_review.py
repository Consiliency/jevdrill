import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('catalog_review', Path(__file__).parents[1] / 'scripts/catalog_review.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'review'
        self.tax = {'domains': [{'id': 'computing', 'subdomains': []}], 'task_facets': ['advise']}
        (self.base / 'taxonomy.json').write_text(json.dumps(self.tax))
        self.records = []
        for i in range(28):
            text = 'Evidence for candidate ' + str(i)
            path = self.base / (str(i) + '.txt')
            path.write_text(text)
            self.records.append(dict(id=str(i), repository='repo' + str(i % 14), path=str(i) + '/SKILL.md',
                                     status='ok', sha256=m.digest(text), text_path=path.name, kind='skill'))
        self.manifest = self.base / 'manifest.json'
        self.manifest.write_text(json.dumps({'records': self.records}))
        m.prepare(self.manifest, self.base / 'taxonomy.json', self.root, 14)

    def queue(self):
        return json.loads((self.root / 'queue.json').read_text())

    def response(self, row):
        return dict(source_id=row['source_id'], content_sha=row['content_sha'], domain_ids=['computing'],
                    tasks=['advise'], kind='advisor', admission='needs_evaluation', rationale='Concrete method',
                    curation_confidence=0.8, dependencies=[], license='unknown',
                    evidence=[{'source_id': row['source_id'], 'quote': Path(row['text_path']).read_text()}])

    def test_pilot_diversity_and_determinism(self):
        rows = self.queue()['rows']
        pilot = [r for r in rows if r['pilot']]
        self.assertEqual(len(set(r['repository'] for r in pilot)), 14)
        m.prepare(self.manifest, self.base / 'taxonomy.json', self.root, 14)
        self.assertEqual(rows, self.queue()['rows'])

    def test_resume_does_no_duplicate_model_work(self):
        def fake(batch, *args):
            return [self.response(row) for row in batch], {}
        with patch.object(m, 'preflight', return_value=('codex', {})), patch.object(m, 'review_batch', side_effect=fake) as call:
            m.run(self.root, 'pilot', False, 2, 7, 60)
            self.assertEqual(call.call_count, 2)
            m.run(self.root, 'pilot', False, 2, 7, 60)
            self.assertEqual(call.call_count, 2)
        m.prepare(self.manifest, self.base / 'taxonomy.json', self.root, 14)
        self.assertEqual(sum(r['status'] == 'complete' for r in self.queue()['rows']), 14)

    def test_malformed_missing_duplicate_and_fabricated_evidence(self):
        row = self.queue()['rows'][0]
        review = self.response(row)
        m.validate_response({'reviews': [review]}, [row], self.tax)
        for bad in ({}, {'reviews': []}, {'reviews': [review, review]}):
            with self.assertRaises(Exception):
                m.validate_response(bad, [row], self.tax)
        review['evidence'][0]['quote'] = 'fabricated'
        with self.assertRaises(ValueError):
            m.validate_response({'reviews': [review]}, [row], self.tax)

    def test_failures_persist_and_require_explicit_retry(self):
        with patch.object(m, 'preflight', return_value=('codex', {})), patch.object(m, 'review_batch', side_effect=ValueError('malformed')) as call:
            m.run(self.root, 'pilot', False, 2, 7, 60)
            self.assertEqual(call.call_count, 2)
            m.run(self.root, 'pilot', False, 2, 7, 60)
            self.assertEqual(call.call_count, 2)
        self.assertEqual(sum(r['status'] == 'error' for r in self.queue()['rows']), 14)

    def test_limit_is_stable_after_resume(self):
        with patch.object(m, 'preflight', return_value=('codex', {})), patch.object(m, 'review_batch', side_effect=lambda batch, *args: ([self.response(r) for r in batch], {})) as call:
            m.run(self.root, 'pilot', False, 2, 7, 60, limit=3)
            m.run(self.root, 'pilot', False, 2, 7, 60, limit=3)
            self.assertEqual(call.call_count, 1)

    def test_cache_separates_models_and_rubrics(self):
        row = self.queue()['rows'][0]
        key = m.cache_key(row, 'v1')
        self.assertNotEqual(key, m.cache_key(row, 'v2'))
        with patch.object(m, 'MODEL', 'gpt-6-luna'):
            self.assertNotEqual(key, m.cache_key(row, 'v1'))

    def test_whitespace_match_preserves_original_but_not_word_changes(self):
        row = self.queue()['rows'][0]
        Path(row['text_path']).write_text('Evidence for\n  candidate 0')
        row['content_sha'] = m.digest('Evidence for\n  candidate 0')
        review = self.response(row)
        review['evidence'][0]['quote'] = 'Evidence for candidate 0'
        result = m.validate_response({'reviews': [review]}, [row], self.tax)
        evidence = result[0]['evidence'][0]
        self.assertEqual(evidence['match_mode'], 'whitespace_only')
        self.assertEqual(evidence['end_line'], 2)
        self.assertEqual(evidence['source_excerpt'], 'Evidence for\n  candidate 0')
        review['evidence'][0]['quote'] = 'Evidence of candidate 0'
        with self.assertRaises(ValueError):
            m.validate_response({'reviews': [review]}, [row], self.tax)

    def test_content_duplicates_keep_reviewed_identity(self):
        rows = self.queue()['rows'][:2]
        rows[1]['content_sha'] = rows[0]['content_sha']
        rows[1]['status'] = 'complete'
        m.deduplicate_content(rows)
        self.assertEqual(rows[0]['reason'], 'content_duplicate')
        self.assertEqual(rows[0]['canonical_source_id'], rows[1]['source_id'])
        self.assertEqual(rows[1]['status'], 'complete')

    def test_metadata_change_invalidates_cache(self):
        row = self.queue()['rows'][0]
        old = m.cache_key(row, 'same-rubric')
        row['metadata'] = {'license': 'newly-discovered-license'}
        self.assertNotEqual(old, m.cache_key(row, 'same-rubric'))

    def test_legacy_cache_migrates_without_review(self):
        queue = self.queue()
        row = queue['rows'][0]
        row['cache_key'] = 'legacy-key'
        row['status'] = 'complete'
        m.atomic_json(self.root / 'queue.json', queue)
        m.atomic_json(self.root / 'results/legacy-key.json', {'review': self.response(row)})
        m.prepare(self.manifest, self.base / 'taxonomy.json', self.root, 14)
        current = self.queue()['rows'][0]
        self.assertEqual(current['status'], 'complete')
        result = json.loads((self.root / 'results' / (current['cache_key'] + '.json')).read_text())
        self.assertEqual(result['cache_migrated_from'], 'legacy-key')

    def test_cli_missing_final_response_is_not_a_success(self):
        queue = self.queue()
        result = m.subprocess.CompletedProcess([], 0, '', '')
        with patch.object(m.subprocess, 'run', return_value=result):
            with self.assertRaisesRegex(ValueError, 'final response missing'):
                m.review_batch(queue['rows'][:1], queue, self.root, 60, 'codex', {})
        metadata = list((self.root / 'batches').glob('*/metadata.json'))
        self.assertEqual(len(metadata), 1)
        self.assertFalse((self.root / 'results').exists())

    def test_cli_timeout_records_elapsed_and_unknown_cost(self):
        queue = self.queue()
        with patch.object(m.subprocess, 'run', side_effect=m.subprocess.TimeoutExpired('codex', 60)):
            with self.assertRaises(m.subprocess.TimeoutExpired):
                m.review_batch(queue['rows'][:1], queue, self.root, 60, 'codex', {})
        metadata = json.loads(next((self.root / 'batches').glob('*/metadata.json')).read_text())
        self.assertEqual(metadata['failure'], 'timeout')
        self.assertIsNone(metadata['cost_usd'])
        self.assertGreaterEqual(metadata['elapsed_seconds'], 0)

    def test_cache_import_reuses_only_matching_metadata_without_model_calls(self):
        queue = self.queue()
        row = queue['rows'][0]
        row['status'] = 'complete'
        m.atomic_json(self.root / 'queue.json', queue)
        m.atomic_json(self.root / 'results' / (row['cache_key'] + '.json'), {'review': self.response(row)})
        receiver = self.base / 'continuation'
        with patch.object(m, 'preflight', side_effect=AssertionError('offline only')):
            m.prepare(self.manifest, self.base / 'taxonomy.json', receiver, cache_sources=[self.root])
        imported = json.loads((receiver / 'queue.json').read_text())['rows'][0]
        self.assertEqual(imported['status'], 'complete')
        records = json.loads(self.manifest.read_text())['records']
        next(r for r in records if r['id'] == row['source_id'])['metadata'] = {'license': 'changed'}
        self.manifest.write_text(json.dumps({'records': records}))
        m.prepare(self.manifest, self.base / 'taxonomy.json', receiver, cache_sources=[self.root])
        changed = json.loads((receiver / 'queue.json').read_text())['rows'][0]
        self.assertEqual(changed['status'], 'pending')

    def test_cache_import_preserves_unresolved_retry_budget(self):
        queue = self.queue()
        row = queue['rows'][0]
        row.update(status='error', attempts=2, reason='unsupported source evidence')
        m.atomic_json(self.root / 'queue.json', queue)
        receiver = self.base / 'continuation'
        m.prepare(self.manifest, self.base / 'taxonomy.json', receiver, cache_sources=[self.root])
        imported = json.loads((receiver / 'queue.json').read_text())['rows'][0]
        self.assertEqual(imported['status'], 'error')
        self.assertEqual(imported['attempts'], 2)
        self.assertEqual(imported['reason'], 'unsupported source evidence')

    def test_empty_sources_excluded_with_prior_failure_history(self):
        row = self.queue()['rows'][0]
        Path(row['text_path']).write_bytes(b' \n')
        row.update(status='error', attempts=2, reason='missing source evidence', content_sha=m.digest(' \n'))
        m.exclude_empty([row])
        self.assertEqual(row['status'], 'excluded')
        self.assertEqual(row['reason'], 'empty_source')
        self.assertEqual(row['attempts'], 2)
        self.assertEqual(row['exclusion_history'][0]['previous_reason'], 'missing source evidence')
        m.exclude_empty([row])
        self.assertEqual(len(row['exclusion_history']), 1)

    def test_corrupt_blank_cache_is_not_an_empty_source(self):
        row = self.queue()['rows'][0]
        Path(row['text_path']).write_bytes(b'')
        with self.assertRaisesRegex(ValueError, 'cached text hash mismatch'):
            m.exclude_empty([row])
        self.assertNotEqual(row['status'], 'excluded')

    def test_full_requires_approval(self):
        with self.assertRaises(ValueError):
            m.run(self.root, 'all', False, 1, 7, 60)


if __name__ == '__main__':
    unittest.main()
