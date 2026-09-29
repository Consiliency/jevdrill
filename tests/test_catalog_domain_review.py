import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import catalog_domain_review as domain


class DomainReviewTests(unittest.TestCase):
    def source(self, name, domains, kind='advisor', admission='needs_evaluation', confidence=0.8):
        return {'source_id': name, 'domain_ids': domains, 'kind': kind, 'admission': admission,
                'curation_confidence': confidence}

    def test_selection_caps_groups_excludes_tools_rejects_and_incomplete(self):
        reviews = [self.source(str(i), ['health']) for i in range(5)]
        reviews += [self.source('tool', ['security'], 'tool'), self.source('reject', ['science'], admission='reject'),
                    self.source('pending', ['education'])]
        queue = {'rows': [{'source_id': r['source_id'], 'status': 'pending' if r['source_id']=='pending' else 'complete'} for r in reviews]}
        result = domain.shortlist(queue, reviews)
        self.assertEqual(len(result), 12)
        self.assertEqual(len(result['health']), 2)
        self.assertEqual(result['security'], [])
        self.assertEqual(result['education'], [])

    def test_preferred_evaluated_source_and_subdomains(self):
        preferred = domain.PREFERRED['security']
        reviews = [self.source('other', ['security.1'], confidence=1), self.source(preferred, ['security.1'], confidence=.5)]
        queue = {'rows': [{'source_id': r['source_id'], 'status': 'complete'} for r in reviews]}
        self.assertEqual(domain.shortlist(queue, reviews)['security'][0]['source_id'], preferred)

    def test_rubric_stays_independent_and_no_validated_admission(self):
        for group in domain.GROUPS:
            rubric = domain.domain_rubric(group)
            self.assertIn(domain.CHECKS[group], rubric)
            self.assertIn('No prior reviewer', rubric)
            self.assertIn('not professional validation', rubric)

    def test_candidate_not_reused_across_groups(self):
        r=self.source('multi', ['computing', 'security'])
        selected=domain.shortlist({'rows':[{'source_id':'multi','status':'complete'}]},[r])
        self.assertEqual(sum(len(rows) for rows in selected.values()),1)


if __name__ == '__main__':
    unittest.main()
