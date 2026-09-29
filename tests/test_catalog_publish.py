import importlib.util
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import catalog_publish as m


class PublishTests(unittest.TestCase):
    def test_excluded_and_exhausted_errors_are_not_pending(self):
        source, review, queue, result = self.setup_data()
        for status, expected in [('excluded', 'excluded'), ('error', 'unresolved'), ('complete', 'unresolved'), ('running', 'pending'), ('pending', 'pending')]:
            queue['rows'][0]['status'] = status
            rows, effective = m.consolidate({'records': [source]}, queue, {}, [], [], [], 'schema', {})
            self.assertEqual(rows[0]['effective_admission'], expected)
            self.assertEqual(effective, [])

    def setup_data(self):
        source = {'id': 'one', 'sha256': 'content', 'normalized_sha256': 'normalized', 'versions': [{'sha256': 'content'}]}
        review = {'source_id': 'one', 'content_sha': 'content', 'admission': 'needs_evaluation', 'domain_ids': ['computing.4', 'finance.2'], 'curation_confidence': .9}
        queue = {'rubric_sha': 'rubric', 'rows': [{'source_id': 'one', 'content_sha': 'content', 'status': 'complete'}]}
        result = {'one': {'review': review, 'metadata': {'schema_sha256': 'schema', 'rubric_sha': 'rubric'}}}
        return source, review, queue, result

    def test_quarantine_removes_only_mapped_group_preserves_original(self):
        source, review, queue, result = self.setup_data()
        correction = {'source_id': 'one', 'source_content_sha': 'content', 'requested_group': 'computing', 'action': 'quarantine_requested_group_mapping_pending_review', 'possible_alternative_domains': ['law']}
        rows, effective = m.consolidate({'records': [source]}, queue, result, [], [correction], [], 'schema', {})
        self.assertEqual(effective[0]['domain_ids'], ['finance.2'])
        self.assertEqual(review['domain_ids'], ['computing.4', 'finance.2'])
        self.assertFalse(rows[0]['validated_admission'])

    def test_stale_evidence_and_schema_do_not_apply(self):
        source, review, queue, result = self.setup_data()
        correction = {'source_id': 'one', 'source_content_sha': 'old', 'requested_group': 'computing', 'action': 'quarantine_requested_group_mapping_pending_review'}
        independent = {'group': 'computing', 'review': dict(review, content_sha='old', admission='reject'), 'metadata': {'schema_sha256': 'schema', 'rubric_sha': 'domain'}}
        rows, effective = m.consolidate({'records': [source]}, queue, result, [independent], [correction], [], 'schema', {('one', 'computing'): 'domain'})
        self.assertEqual(effective[0]['admission'], 'needs_evaluation')
        self.assertEqual(effective[0]['domain_ids'], review['domain_ids'])
        _, effective = m.consolidate({'records': [source]}, queue, result, [], [], [], 'new-schema', {})
        self.assertEqual(effective, [])

    def test_independent_downgrade_and_duplicate_retention(self):
        source, review, queue, result = self.setup_data()
        other = dict(source, id='two')
        independent = {'group': 'computing', 'review': dict(review, admission='deeper_review'), 'metadata': {'schema_sha256': 'schema', 'rubric_sha': 'domain'}}
        rows, effective = m.consolidate({'records': [source, other]}, queue, result, [independent], [], [], 'schema', {('one', 'computing'): 'domain'})
        self.assertEqual(len(rows), 2)
        self.assertEqual(effective[0]['admission'], 'deeper_review')
        self.assertEqual(rows[0]['duplicate_provenance']['exact_source_ids'], ['one', 'two'])
        self.assertEqual(next(r for r in rows if r['source_id'] == 'two')['triage_status'], 'not_queued')
        self.assertTrue(rows[0]['independent_domain_reviews'][0]['rubric_scope_caveat'])

    def test_human_catalog_escapes_and_preserves_empty_domains(self):
        source, review, queue, result = self.setup_data()
        source.update(metadata={'name': '<script>[fake](bad)'}, pinned_source_url='https://example.org/pinned')
        review.update(kind='advisor', rationale='unsafe <b>markup</b>\n# injected')
        rows, _ = m.consolidate({'records': [source]}, queue, result, [], [], [], 'schema', {})
        taxonomy = {'domains': [{'id': 'computing', 'name': 'Computing'}, {'id': 'empty', 'name': 'Empty'}]}
        summary = {'effective_review_count': 1, 'triage_status_counts': {'complete': 1}}
        rendered = m.human_catalog(rows, taxonomy, summary)
        self.assertNotIn('<script>', rendered)
        self.assertIn('&lt;script&gt;', rendered)
        self.assertNotIn('\n# injected', rendered)
        self.assertIn('## Empty\n\n**Gap:**', rendered)
        self.assertIn('**unvalidated; advisor**', rendered)
        rows[0]['effective_domain_ids'] = ['unknown-root.1']
        self.assertIn('**Unknown / no effective domain:** 1 paths', m.human_catalog(rows, taxonomy, summary))

    def test_additive_expansion_preserves_admission_and_ignores_stale_hash(self):
        source, review, queue, result = self.setup_data()
        rows, effective = m.consolidate({'records': [source]}, queue, result, [], [], [], 'schema', {})
        taxonomy = {'domains': [{'id': 'new', 'subdomains': [{'id': 'new.1'}]}]}
        mapping = {'source_id': 'one', 'source_content_sha': 'old', 'domain_ids': ['new.1']}
        m.apply_domain_expansion(rows, effective, taxonomy, [mapping])
        self.assertNotIn('new.1', effective[0]['domain_ids'])
        m.apply_domain_expansion(rows, effective, taxonomy, [dict(mapping, source_content_sha='content')])
        self.assertIn('new.1', effective[0]['domain_ids'])
        self.assertEqual(effective[0]['admission'], 'needs_evaluation')
        self.assertEqual(review['domain_ids'], ['computing.4', 'finance.2'])
        self.assertFalse(rows[0]['validated_admission'])


if __name__ == '__main__':
    unittest.main()
