"""Independent, bounded domain suitability review of completed triage candidates."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import catalog_review as worker

GROUPS = {
    'science': ['physical-sciences', 'life-sciences'], 'engineering': ['engineering', 'energy'],
    'computing': ['computing', 'ai-data'], 'security': ['security'], 'health': ['health'],
    'finance-accounting': ['finance', 'accounting', 'economics'],
    'law-governance': ['law', 'governance'], 'business': ['business', 'operations', 'people', 'commercial'],
    'education': ['education'], 'humanities': ['humanities', 'social-sciences'],
    'arts-language': ['arts', 'language'], 'personal-hospitality': ['personal', 'hospitality', 'sport'],
}
CHECKS = {
    'science': 'Check causal versus associational claims, uncertainty, study design, reproducibility, and evidence quality.',
    'engineering': 'Check explicit assumptions, units, constraints, failure modes and safety verification; distinguish equipment operation from engineering judgment.',
    'computing': 'Check architecture tradeoffs, correctness, maintainability, verification and applicability; distinguish tool documentation from reusable reasoning.',
    'security': 'Check threat assumptions, authorization boundaries, evidence-backed findings, false positives and responsible scope.',
    'health': 'Check evidence quality, uncertainty, escalation, professional oversight and unsupported diagnosis or treatment authority.',
    'finance-accounting': 'Check reconciliation/audit trails, numerical assumptions, jurisdiction/date dependencies and unsupported financial advice.',
    'law-governance': 'Check jurisdiction, facts, authority/citation reliability, policy versus law, professional review and unsupported legal conclusions.',
    'business': 'Check realistic decision criteria, stakeholders, incentives, measurable outcomes and unsupported business generalizations.',
    'education': 'Check learner context, pedagogical rationale, assessment alignment, accessibility and unsupported learning-outcome claims.',
    'humanities': 'Check source criticism, interpretive alternatives, cultural/historical context and avoidance of fabricated evidence or universal claims.',
    'arts-language': 'Check audience, craft criteria, meaning preservation, revision rationale and distinction between guidance and a mere style persona.',
    'personal-hospitality': 'Check user preferences, practical constraints, accessibility, uncertainty and inappropriate high-stakes advice.',
}
PREFERRED = {
    'science': 'github:k-dense-ai/scientific-agent-skills:skills/scientific-critical-thinking/SKILL.md',
    'security': 'github:trailofbits/skills:plugins/differential-review/skills/differential-review/SKILL.md',
    'finance-accounting': 'github:anthropics/knowledge-work-plugins:finance/skills/reconciliation/SKILL.md',
    'law-governance': 'github:anthropics/knowledge-work-plugins:small-business/skills/contract-review/SKILL.md',
}


def shortlist(queue, reviews):
    rows = {r['source_id']: r for r in queue['rows'] if r['status'] == 'complete'}
    output = {}
    used = set()
    for group, domains in GROUPS.items():
        plausible = [r for r in reviews if r['source_id'] in rows and r['source_id'] not in used
                     and (r['source_id'] not in PREFERRED.values() or r['source_id'] == PREFERRED.get(group))
                     and r['admission'] in ('needs_evaluation', 'deeper_review')
                     and r['kind'] in ('advisor', 'mixed', 'workflow')
                     and any(d.split('.')[0] in domains for d in r['domain_ids'])]
        plausible.sort(key=lambda r: (r['source_id'] != PREFERRED.get(group),
                                     r['admission'] != 'needs_evaluation', r['kind'] != 'advisor',
                                     -r['curation_confidence'], r['source_id']))
        selected = plausible[:2]
        used.update(r['source_id'] for r in selected)
        output[group] = [dict(rows[r['source_id']], review_group=group,
                              selection_note='Completed triage; promising domain-matched candidate. Prior judgment omitted from reviewer prompt.')
                         for r in selected]
    return output


def domain_rubric(group):
    return worker.RUBRIC + '\nIndependent domain suitability pass. Requested group: ' + group + '. ' + CHECKS[group] + '''
Assess the actual source content, not publisher reputation. Explicitly address suitability for the requested
group, concrete reusable reasoning, limits and missing facts, license evidence, missing dependency/reference
materials, prompt-injection or unsupported authority claims, and what empirical task would test usefulness.
Put these findings in rationale and dependencies using the supplied schema. Treat absent supporting materials
as unreviewed, not verified. Do not infer efficacy from confidence. Quote one or two short source passages
under 120 characters each. This is an independent model pass, not professional validation. No prior reviewer
decisions or test outcomes are supplied. Allowed conclusions remain reject, deeper_review, needs_evaluation.'''


def prepare(triage, root):
    queue_bytes = (triage / 'queue.json').read_bytes()
    queue = json.loads(queue_bytes)
    reviews = []
    result_hashes = {}
    for row in queue['rows']:
        result = triage / 'results' / (row['cache_key'] + '.json')
        if row['status'] == 'complete' and result.exists():
            raw = result.read_bytes()
            review = json.loads(raw)['review']
            if review['source_id'] == row['source_id'] and review['content_sha'] == row['content_sha']:
                reviews.append(review)
                result_hashes[row['source_id']] = worker.hashlib.sha256(raw).hexdigest()
    selection = shortlist(queue, reviews)
    tasks = []
    for group, rows in selection.items():
        rubric = domain_rubric(group)
        rubric_sha = worker.digest(rubric + json.dumps(queue['taxonomy'], sort_keys=True))
        for row in rows:
            row.update(cache_key=worker.cache_key(row, rubric_sha), attempts=1, status='pending')
            tasks.append({'row': row, 'rubric': rubric, 'rubric_sha': rubric_sha})
    payload = {'schema_version': 1, 'stage': 'independent_domain_suitability', 'model': worker.MODEL,
               'selection_scope': 'partial-sweep snapshot, not globally best candidates',
               'triage_queue_sha256': worker.hashlib.sha256(queue_bytes).hexdigest(),
               'completed_triage_at_selection': len(reviews),
               'selection_evidence_hashes': {task['row']['source_id']: result_hashes[task['row']['source_id']] for task in tasks},
               'triage_root': str(triage.resolve()), 'taxonomy': queue['taxonomy'], 'tasks': tasks,
               'groups': {g: {'source_ids': [r['source_id'] for r in rs],
                              'status': 'selected' if rs else 'gap_no_eligible_candidate'} for g, rs in selection.items()},
               'limits': 'At most two candidates per group; independent model pass, not professional validation or empirical admission.'}
    if (root / 'selection.json').exists():
        raise ValueError('Existing selection is immutable; use a new output root')
    worker.atomic_json(root / 'selection.json', payload)
    return payload


def run(root, workers=8):
    if not 1 <= workers <= 8:
        raise ValueError('workers must be between1 and8')
    payload = json.loads((root / 'selection.json').read_text())
    executable, env = worker.preflight()
    results = []
    def one(task):
        row = task['row']
        path = root / 'results' / (row['cache_key'] + '.json')
        if path.exists():
            return json.loads(path.read_text())
        batch_id = worker.digest(row['cache_key'])
        if (root / 'batches' / batch_id / 'metadata.json').exists():
            row = dict(row, attempts=2)
        if (root / 'batches' / (batch_id + '-retry2') / 'metadata.json').exists():
            raise ValueError('Two attempts exhausted; inspect archived evidence')
        queue = {'taxonomy': payload['taxonomy'], 'rubric': task['rubric'], 'rubric_sha': task['rubric_sha']}
        reviews, metadata = worker.review_batch([row], queue, root, 600, executable, env)
        result = {'group': row['review_group'], 'review': reviews[0], 'metadata': metadata,
                  'stage': 'independent_domain_suitability', 'prior_decisions_in_prompt': False,
                  'source_url': row['source_url'], 'validated': False}
        worker.atomic_json(path, result)
        return result
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(one, task): task for task in payload['tasks']}
        for future in as_completed(futures):
            task = futures[future]
            try:
                results.append(future.result())
            except Exception as error:
                results.append({'group': task['row']['review_group'], 'source_id': task['row']['source_id'],
                                'error': type(error).__name__ + ': ' + str(error)[:200]})
    report = {'stage': payload['stage'], 'groups': payload['groups'], 'results': results,
              'completed': sum('review' in r for r in results), 'errors': sum('error' in r for r in results),
              'validated_admissions': 0, 'limits': payload['limits']}
    worker.atomic_json(root / 'summary.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'run'])
    parser.add_argument('--triage', type=Path, default=Path('research/review'))
    parser.add_argument('--root', type=Path, default=Path('research/domain-review'))
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    result = prepare(args.triage, args.root) if args.command == 'prepare' else run(args.root, args.workers)
    print(json.dumps({k: v for k, v in result.items() if k not in ('tasks', 'taxonomy', 'results')}, indent=2))
