#!/usr/bin/env python3
"""Publish provenance-preserving catalog snapshots without validated admission."""
import argparse
import copy
import hashlib
import html
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote

from catalog_domain_review import GROUPS
from catalog_ingest import atomic_write
from catalog_review import schema, digest


def hash_value(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def markdown_text(value):
    text = html.escape(' '.join(str(value).split()), quote=False)
    return re.sub(r'([\\`*_{}\[\]()#+.!|>-])', r'\\\1', text)


def human_catalog(rows, taxonomy, summary):
    lines = ['# Advisor research catalog', '',
             '**All candidates are unvalidated.** Shortlists identify research priorities, not proven advisor quality or professional suitability. Browse links may be mutable; observed content is pinned separately by the pinned-evidence links.', '',
             f"This snapshot contains **{len(rows):,} source paths**; **{summary['effective_review_count']:,}** have applicable completed triage reviews. **Zero validated admissions.**", '',
             'Triage states: ' + '; '.join(f'{markdown_text(k)}: {v:,}' for k, v in sorted(summary['triage_status_counts'].items())) + '.', '',
             'Browse [all records, exclusions, errors, rejections, and evidence](ranked-catalog.json), [effective routing reviews](effective-reviews.json), and [snapshot statistics](summary.json).', '',
             'Domain counts use effective mappings after editorial quarantines. Multi-domain candidates count in each matching domain. Tool and workflow candidates remain counted separately from advisor shortlists. Ordering follows research priority and curation confidence; it does not estimate effectiveness or choose models.', '',
             '| Domain | Needs evaluation | Deeper review | Pending | Unresolved | Excluded | Rejected | Tool/workflow paths |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    domain_rows = {}
    for domain in taxonomy['domains']:
        selected = [r for r in rows if domain['id'] in {d.split('.')[0] for d in r['effective_domain_ids']}]
        domain_rows[domain['id']] = selected
        counts = Counter(r['effective_admission'] for r in selected)
        tooling = sum((r.get('original_triage') or {}).get('kind') in ('tool', 'workflow') for r in selected)
        lines.append(f"| {markdown_text(domain['name'])} | {counts['needs_evaluation']} | {counts['deeper_review']} | {counts['pending']} | {counts['unresolved']} | {counts['excluded']} | {counts['reject']} | {tooling} |")
    root_ids = {d['id'] for d in taxonomy['domains']}
    unknown = sum(not root_ids.intersection(d.split('.')[0] for d in r['effective_domain_ids']) for r in rows)
    lines.extend(['', f'**Unknown / no effective domain:** {unknown:,} paths. These include pending, failed, excluded, and unmapped records; they are not silently assigned to a domain.', ''])
    for domain in taxonomy['domains']:
        selected = domain_rows[domain['id']]
        advisors = [r for r in selected if r['effective_admission'] == 'needs_evaluation' and (r.get('original_triage') or {}).get('kind') in ('advisor', 'mixed')]
        advisors.sort(key=lambda r: (-(r['research_priority']['curation_confidence'] or 0), r['source_id']))
        lines.extend(['## ' + markdown_text(domain['name']), ''])
        if not advisors:
            lines.extend(['**Gap:** no currently eligible advisor/mixed research priority in this snapshot.', ''])
            continue
        lines.extend([f'Up to five unvalidated advisor/mixed research priorities ({len(advisors)} eligible paths in this domain):', ''])
        for row in advisors[:5]:
            source = row['source']
            review = row['original_triage']
            name = source.get('metadata', {}).get('name') or source.get('path') or row['source_id']
            pinned = quote(row.get('pinned_source_url') or '', safe=':/?=&%')
            url = quote(next(iter(source.get('original_urls', [])), row.get('pinned_source_url') or ''), safe=':/?=&%')
            title = f'[{markdown_text(name)}]({url})' if url.startswith('https://') else markdown_text(name)
            rationale = ' '.join(review.get('rationale', '').split())[:260]
            evidence_link = f' [Pinned evidence]({pinned}).' if pinned.startswith('https://') else ''
            lines.append(f"- {title} — **unvalidated; {markdown_text(review['kind'])}**. {markdown_text(rationale)}{evidence_link} Source: {markdown_text(row['source_id'])}.")
        lines.append('')
    return '\n'.join(lines) + '\n'


def matches(review, source):
    return review.get('source_id') == source['id'] and review.get('content_sha') == source.get('sha256')


def apply_domain_expansion(rows, effective, taxonomy, mappings):
    valid_ids = {d['id'] for d in taxonomy['domains']}
    valid_ids.update(s['id'] for d in taxonomy['domains'] for s in d.get('subdomains', []))
    by_id = {r['source_id']: r for r in rows}
    effective_by_id = {r['source_id']: r for r in effective}
    for mapping in mappings:
        row = by_id.get(mapping.get('source_id'))
        if row is None:
            continue
        ids = mapping.get('domain_ids', [])
        blocked_roots = {root for c in row['routing_corrections'] if c['applied'] for root in GROUPS[c['correction']['requested_group']]}
        accepted = bool(mapping.get('source_content_sha') == row['content_sha'] and isinstance(ids, list) and ids
                        and all(isinstance(d, str) and d in valid_ids and d.split('.')[0] not in blocked_roots for d in ids))
        row.setdefault('taxonomy_expansion_evidence', []).append({'applied': accepted, 'mapping': mapping})
        if not accepted:
            row['stale_evidence_notes'].append('taxonomy mapping hash/ID mismatch or conflict with applied quarantine')
            continue
        row['effective_domain_ids'] = sorted(set(row['effective_domain_ids']) | set(ids))
        review = effective_by_id.get(row['source_id'])
        if review is not None:
            review['domain_ids'] = list(row['effective_domain_ids'])
            review.setdefault('taxonomy_expansion_evidence', []).append(mapping)


def consolidate(manifest, queue, results, independent, corrections, evaluations, expected_schema, domain_rubrics):
    queue_rows = {r['source_id']: r for r in queue['rows']}
    exact = defaultdict(list)
    normalized = defaultdict(list)
    for source in manifest['records']:
        exact[source.get('sha256')].append(source['id'])
        normalized[source.get('normalized_sha256')].append(source['id'])
    published, effective = [], []
    for source in manifest['records']:
        rid = source['id']
        queued = queue_rows.get(rid, {})
        result = results.get(rid)
        triage = result.get('review') if result else None
        stale = []
        applied = []
        valid = bool(triage and queued.get('status') == 'complete' and matches(triage, source)
                     and queued.get('content_sha') == source.get('sha256')
                     and result.get('metadata', {}).get('schema_sha256') == expected_schema
                     and result.get('metadata', {}).get('rubric_sha') == queue['rubric_sha'])
        if triage and not valid:
            stale.append('triage hash, schema, rubric, or completion state does not match current evidence')
        review = copy.deepcopy(triage) if valid else None
        domains = list(review.get('domain_ids', [])) if review else []
        independent_rows = []
        for observation in independent:
            other = observation.get('review', {})
            if other.get('source_id', observation.get('source_id')) != rid:
                continue
            metadata = observation.get('metadata', {})
            accepted = bool(matches(other, source) and metadata.get('schema_sha256') == expected_schema
                            and metadata.get('rubric_sha') == domain_rubrics.get((rid, observation.get('group'))))
            independent_rows.append({'applies_to_current_content': accepted, 'observation': observation,
                                     'rubric_scope_caveat': 'Independent model domain-suitability rubric differs from initial triage; conservative downgrade is a routing policy, not an empirical finding of ineffectiveness.'})
            if not accepted:
                stale.append('independent review hash/schema/rubric mismatch or failed review')
            elif review:
                if other.get('admission') == 'reject':
                    review['admission'] = 'reject'
                elif other.get('admission') == 'deeper_review' and review.get('admission') != 'reject':
                    review['admission'] = 'deeper_review'
        quarantine_rows = []
        for correction in corrections:
            if correction.get('source_id') != rid:
                continue
            group = correction.get('requested_group')
            accepted = (correction.get('source_content_sha') == source.get('sha256') and group in GROUPS
                        and correction.get('action') == 'quarantine_requested_group_mapping_pending_review')
            quarantine_rows.append({'applied': accepted, 'correction': correction})
            if accepted:
                roots = GROUPS[group]
                removed = [d for d in domains if d.split('.')[0] in roots]
                domains = [d for d in domains if d.split('.')[0] not in roots]
                applied.append({'group': group, 'removed_domain_ids': removed, 'reason': correction.get('reason')})
            else:
                stale.append('editorial correction hash/action/group mismatch')
        if review:
            review['domain_ids'] = domains
            review['effective_policy'] = {'validated': False, 'original_admission': triage['admission'], 'editorial_quarantines': applied,
                                         'independent_review_count': sum(r['applies_to_current_content'] for r in independent_rows),
                                         'rubric_scope_caveat': 'Independent suitability and initial triage use different rubrics; conservative downgrade does not establish ineffectiveness.'}
            effective.append(review)
        observations = [{'applies_to_current_content': e.get('source_sha256') == source.get('sha256'), 'observation': e,
                         'admission_effect': 'none; small synthetic pilot does not establish validation'} for e in evaluations if e.get('source_id') == rid]
        if review:
            admission = review['admission']
        elif queued.get('status') == 'excluded':
            admission = 'excluded'
        elif queued.get('status') in ('error', 'complete') or triage:
            admission = 'unresolved'
        else:
            admission = 'pending'
        row = {'source_id': rid, 'source': source, 'source_aliases': source.get('original_urls', []),
               'pinned_source_url': source.get('pinned_source_url'), 'content_sha': source.get('sha256'),
               'version_history': source.get('versions', []), 'triage_status': queued.get('status', 'not_queued'),
               'triage_reason': queued.get('reason'), 'original_triage': triage, 'triage_provenance': result.get('metadata') if result else None,
               'current_triage_applies': valid, 'independent_domain_reviews': independent_rows, 'routing_corrections': quarantine_rows,
               'evaluation_observations': observations, 'effective_domain_ids': domains, 'effective_admission': admission,
               'validated_admission': False, 'stale_evidence_notes': stale,
               'duplicate_provenance': {'exact_source_ids': exact[source.get('sha256')], 'normalized_source_ids': normalized[source.get('normalized_sha256')], 'queue_duplicate_of': queued.get('canonical_source_id', queued.get('duplicate_of'))},
               'research_priority': {'category': admission, 'curation_confidence': triage.get('curation_confidence') if valid else None,
                                     'meaning': 'Research ordering only, never measured effectiveness or validated admission.'}}
        published.append(row)
    order = {'needs_evaluation': 0, 'deeper_review': 1, 'unresolved': 2, 'pending': 3, 'excluded': 4, 'reject': 5}
    published.sort(key=lambda r: (order.get(r['effective_admission'], 2), -(r['research_priority']['curation_confidence'] or 0), r['source_id']))
    return published, sorted(effective, key=lambda r: r['source_id'])


def read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=Path('research/ingestion/manifest.json'))
    parser.add_argument('--review', type=Path, default=Path('research/review'))
    parser.add_argument('--domain', type=Path, default=Path('research/domain-review'))
    parser.add_argument('--additional-domain', type=Path, action='append', default=[])
    parser.add_argument('--supplemental-manifest', type=Path)
    parser.add_argument('--supplemental-review', type=Path)
    parser.add_argument('--expanded-taxonomy', type=Path)
    parser.add_argument('--domain-mappings', type=Path)
    parser.add_argument('--evaluation', type=Path, default=Path('research/evaluation'))
    parser.add_argument('--output', type=Path, default=Path('research/published'))
    args = parser.parse_args()
    manifest = read(args.manifest)
    queue = read(args.review / 'queue.json')
    results = {}
    for row in queue['rows']:
        path = args.review / 'results' / (row['cache_key'] + '.json')
        if path.exists():
            results[row['source_id']] = read(path)
    independent = []
    domain_rubrics = {}
    for domain_root in [args.domain] + args.additional_domain:
        independent.extend(read(domain_root / 'summary.json', {}).get('results', []))
        selection = read(domain_root / 'selection.json', {})
        domain_rubrics.update({(t['row']['source_id'], t['row']['review_group']): t['rubric_sha'] for t in selection.get('tasks', [])})
    corrections = read(args.domain / 'routing-corrections.json', {}).get('rows', [])
    evaluations = []
    for path in sorted((args.evaluation / 'runs').glob('*/metadata.json')):
        meta = read(path)
        source = meta.get('source', {})
        evaluations.append({'source_id': source.get('source_id'), 'source_sha256': source.get('sha256'),
                            'run_metadata': meta, 'report': read(path.parent / 'report.json'), 'evidence_directory': str(path.parent)})
    expected_schema = digest(json.dumps(schema(queue['taxonomy']), sort_keys=True))
    rows, effective = consolidate(manifest, queue, results, independent, corrections, evaluations, expected_schema, domain_rubrics)
    primary_count = len(rows)
    combined_sources = [dict(r, text_path=str((args.manifest.parent / r['text_path']).resolve())) if r.get('text_path') else r for r in manifest['records']]
    supplemental_evidence = None
    if bool(args.supplemental_manifest) != bool(args.supplemental_review):
        parser.error('supplemental manifest and review must be supplied together')
    if args.supplemental_manifest:
        extra_manifest = read(args.supplemental_manifest)
        extra_queue = read(args.supplemental_review / 'queue.json')
        if {r['id'] for r in combined_sources} & {r['id'] for r in extra_manifest['records']}:
            raise ValueError('supplemental source IDs overlap primary epoch')
        extra_results = {}
        for row in extra_queue['rows']:
            path = args.supplemental_review / 'results' / (row['cache_key'] + '.json')
            if path.exists():
                extra_results[row['source_id']] = read(path)
        extra_schema = digest(json.dumps(schema(extra_queue['taxonomy']), sort_keys=True))
        extra_rows, extra_effective = consolidate(extra_manifest, extra_queue, extra_results, independent, corrections, evaluations, extra_schema, domain_rubrics)
        rows.extend(extra_rows)
        effective.extend(extra_effective)
        combined_sources.extend(dict(r, text_path=str((args.supplemental_manifest.parent / r['text_path']).resolve())) if r.get('text_path') else r for r in extra_manifest['records'])
        supplemental_evidence = {'manifest': extra_manifest, 'queue': extra_queue, 'results': extra_results}
        rows.sort(key=lambda r: ({'needs_evaluation': 0, 'deeper_review': 1, 'unresolved': 2, 'pending': 3, 'excluded': 4, 'reject': 5}.get(r['effective_admission'], 2), -(r['research_priority']['curation_confidence'] or 0), r['source_id']))
        effective.sort(key=lambda r: r['source_id'])
    if args.domain_mappings and not args.expanded_taxonomy:
        parser.error('domain mappings require expanded taxonomy')
    display_taxonomy = read(args.expanded_taxonomy) if args.expanded_taxonomy else queue['taxonomy']
    expansion = read(args.domain_mappings) if args.domain_mappings else {'rows': []}
    apply_domain_expansion(rows, effective, display_taxonomy, expansion.get('rows', []))
    version = hash_value({'manifest': manifest, 'queue': queue, 'results': results, 'independent': independent, 'corrections': corrections, 'display_taxonomy': display_taxonomy, 'expansion': expansion,
                          'evaluations': evaluations, 'supplemental': supplemental_evidence, 'expected_schema': expected_schema, 'domain_rubrics': sorted((a, b, v) for (a, b), v in domain_rubrics.items())})
    summary = {'schema_version': 1, 'evidence_version': version, 'original_candidate_count': primary_count, 'total_candidate_count': len(rows), 'supplemental_candidate_count': len(rows) - primary_count, 'effective_review_count': len(effective),
               'triage_status_counts': dict(Counter(r['triage_status'] for r in rows)),
               'effective_admission_counts': dict(Counter(r['effective_admission'] for r in rows)), 'validated_admissions': 0,
               'applied_quarantine_count': sum(c['applied'] for r in rows for c in r['routing_corrections']),
               'applied_taxonomy_mapping_count': sum(e['applied'] for r in rows for e in r.get('taxonomy_expansion_evidence', [])),
               'stale_evidence_record_count': sum(bool(r['stale_evidence_notes']) for r in rows),
               'snapshot_note': ('Queue is complete with no pending or running reviews.' if not any(r['triage_status'] in {'pending', 'running'} for r in rows)
                                 else 'Queue captured once; active workers may complete additional reviews after this snapshot.'),
               'ranking_note': 'Research priority only. No model or effort selection inferred from benchmarks.'}
    args.output.mkdir(parents=True, exist_ok=True)
    cache_roots = sorted({str(Path(r['text_path']).parent) for r in combined_sources if r.get('text_path')})
    for name, data in [('ranked-catalog.json', rows), ('effective-reviews.json', effective), ('summary.json', summary), ('source-manifest.json', {'schema_version': 1, 'cache_roots': cache_roots, 'records': combined_sources})]:
        atomic_write(args.output / name, (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode())
    atomic_write(args.output / 'CATALOG.md', human_catalog(rows, display_taxonomy, summary).encode())
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
