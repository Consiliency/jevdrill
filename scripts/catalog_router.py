#!/usr/bin/env python3
"""Build bounded hierarchical retrieval packs and inspect pinned source evidence."""
import argparse
import hashlib
import json
from pathlib import Path

CAP = 24000
ELIGIBLE = {'needs_evaluation'}
EXCLUDED_KINDS = {'template', 'unknown'}


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def eligible(review, source):
    return bool(review and source and source.get('status') == 'ok'
                and review.get('admission') in ELIGIBLE
                and review.get('kind') not in EXCLUDED_KINDS
                and review.get('kind') in {'advisor', 'mixed', 'tool', 'workflow', 'persona'}
                and review.get('content_sha') == source.get('sha256'))


def paginate(items, context, cap=CAP):
    pages = []
    current = []
    for item in items:
        candidate = dict(context, candidates=current + [item])
        if len(encoded(candidate)) > cap:
            if not current:
                raise ValueError('single candidate exceeds byte cap')
            pages.append(dict(context, candidates=current))
            current = [item]
            if len(encoded(dict(context, candidates=current))) > cap:
                raise ValueError('single candidate exceeds byte cap')
        else:
            current.append(item)
    if current:
        pages.append(dict(context, candidates=current))
    return pages


def build(manifest, reviews, taxonomy, out, cap=CAP):
    sources = {r['id']: r for r in manifest['records']}
    review_map = {r['source_id']: r for r in reviews}
    source_evidence = [{'id': r['id'], 'sha256': r.get('sha256'), 'status': r['status'], 'pinned_source_url': r.get('pinned_source_url')} for r in sorted(sources.values(), key=lambda r: r['id'])]
    version = digest({'sources': source_evidence, 'reviews': sorted(reviews, key=lambda r: r['source_id']), 'taxonomy': taxonomy, 'format_version': 1, 'cap': cap})
    directory = out / 'packs' / version
    directory.mkdir(parents=True, exist_ok=True)
    roots = {d['id']: d for d in taxonomy['domains']}
    parents = {s['id']: d['id'] for d in roots.values() for s in d.get('subdomains', [])}
    groups = {key: [] for key in [*roots, *parents, 'unknown']}
    lookup = {}
    selected = []
    for rid, review in sorted(review_map.items()):
        source = sources.get(rid)
        if not eligible(review, source):
            continue
        selected.append(rid)
        key = hashlib.sha256(rid.encode()).hexdigest()
        detail_path = 'details/' + key + '.json'
        descriptor = ' '.join((review.get('rationale') or source.get('metadata', {}).get('description') or source['path']).split())[:200]
        entry = {'id': rid, 'description': descriptor, 'sha256': source['sha256'], 'source_url': source['pinned_source_url'], 'kind': review['kind'], 'admission': review['admission'], 'validation': 'unvalidated', 'domain_ids': review.get('domain_ids', []), 'tasks': review.get('tasks', []), 'detail_ref': detail_path}
        mapped = {domain for domain in review.get('domain_ids', []) if domain in groups and domain != 'unknown'}
        if not mapped:
            mapped = {'unknown'}
        for domain in sorted(mapped):
            groups[domain].append(entry)
        detail = {'source_id': rid, 'validation': 'unvalidated', 'source': source, 'review': review, 'text_loading': 'Read source.text_path relative to the ingestion directory; verify source.sha256 before use.', 'rights': source.get('metadata', {}).get('license'), 'dependencies': review.get('dependencies', []), 'evidence_version': version}
        target = directory / detail_path
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(encoded(detail))
        lookup[rid] = {'detail_ref': str(target.relative_to(out)), 'sha256': source['sha256']}
    pack_sizes = {}
    def write(path, value):
        data = encoded(value)
        if len(data) > cap:
            raise ValueError('pack exceeds byte cap: ' + path)
        target = directory / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        pack_sizes[path] = len(data)
    refs = {}
    for domain, entries in groups.items():
        refs[domain] = []
        pages = paginate(entries, {'domain': domain, 'validation': 'unvalidated', 'unknown_none': True, 'evidence_version': version}, cap)
        for number, page in enumerate(pages, 1):
            path = 'leaves/' + domain + '-' + str(number) + '.json'
            write(path, page)
            refs[domain].append(path)
    root_entries = []
    for domain, definition in roots.items():
        specialties = [{'id': s['id'], 'name': s['name'], 'candidate_count': len(groups[s['id']]), 'pages': refs[s['id']]} for s in definition.get('subdomains', [])]
        all_ids = {e['id'] for key in [domain] + [s['id'] for s in definition.get('subdomains', [])] for e in groups[key]}
        menu = {'id': domain, 'name': definition['name'], 'validation': 'unvalidated', 'evidence_version': version, 'specialties': specialties, 'general_pages': refs[domain], 'unknown_none': True, 'candidate_count': len(all_ids)}
        path = 'domains/' + domain + '.json'
        write(path, menu)
        root_entries.append({'id': domain, 'name': definition['name'], 'menu': path, 'candidate_count': len(all_ids)})
    index = {'format_version': 1, 'evidence_version': version, 'pack_base': 'packs/' + version + '/', 'validation': 'unvalidated', 'instructions': 'Select zero, one, or multiple domains, then specialties and candidate pages. Unknown/none is valid. Replace the current menu at each step; retain only selected IDs, route path, and task facets. Do not append root, domain, and leaf packs into cumulative routing context. The byte cap applies per pack, not to a whole route. Fetch details and pinned source text outside Jev routing state after narrowing. Actual Jev token budget remains unmeasured; no candidate has been professionally validated.', 'domains': root_entries, 'unknown_none': {'id': 'unknown', 'name': 'Unknown / none / insufficient evidence', 'pages': refs['unknown']}, 'task_facets': taxonomy.get('task_facets', []), 'byte_cap': cap, 'token_measurement': 'UTF-8 byte bound only; actual Jev token count unmeasured'}
    if len(encoded(index)) > cap:
        raise ValueError('root exceeds byte cap')
    (out / 'index.json').write_bytes(encoded(index))
    (out / 'lookup-index.json').write_bytes(encoded(lookup))
    report = {'evidence_version': version, 'source_records': len(sources), 'reviewed_records': len(review_map), 'eligible_unvalidated_records': len(selected), 'excluded_or_pending_source_records': len(sources) - len(selected), 'root_domains': len(roots), 'specialties': len(parents), 'pack_count_including_root': len(pack_sizes) + 1, 'maximum_pack_utf8_bytes': max([len(encoded(index))] + list(pack_sizes.values())), 'byte_cap': cap, 'root_utf8_bytes': len(encoded(index)), 'actual_jev_calls': 0, 'actual_jev_tokens': None, 'pack_sizes': pack_sizes, 'all_candidates_unvalidated': True}
    (out / 'packing-report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def lookup(source_id, manifest, reviews, ingestion_dir, include_text=False):
    source = next((r for r in manifest['records'] if r['id'] == source_id), None)
    if source is None:
        return {'source_id': source_id, 'status': 'unknown_none'}
    review = next((r for r in reviews if r['source_id'] == source_id), None)
    result = {'source_id': source_id, 'eligible_unvalidated': eligible(review, source), 'validation': 'unvalidated', 'pinned_source_url': source.get('pinned_source_url'), 'sha256': source.get('sha256'), 'rights': source.get('metadata', {}).get('license'), 'review_provenance': review, 'text_path': None}
    if source.get('text_path'):
        path = (ingestion_dir / source['text_path']).resolve()
        cache_roots = [Path(root).resolve() for root in manifest.get('cache_roots', [str(ingestion_dir.resolve())])]
        if not any(path.is_relative_to(root) for root in cache_roots):
            raise ValueError('text cache path outside ingestion directory')
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != source['sha256']:
            raise ValueError('cached source hash mismatch')
        result['text_path'] = str(path)
        if include_text:
            result['text'] = data.decode('utf-8', 'replace')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('build', 'lookup'))
    parser.add_argument('source_id', nargs='?')
    parser.add_argument('--manifest', default='research/ingestion/manifest.json')
    parser.add_argument('--reviews', default='research/review/ranked-catalog.json')
    parser.add_argument('--taxonomy', default='research/taxonomy.json')
    parser.add_argument('--output', default='research/router')
    parser.add_argument('--include-text', action='store_true')
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text())
    reviews = json.loads(Path(args.reviews).read_text())
    if args.command == 'build':
        result = build(manifest, reviews, json.loads(Path(args.taxonomy).read_text()), Path(args.output))
        result = {k: v for k, v in result.items() if k != 'pack_sizes'}
    else:
        if not args.source_id:
            parser.error('lookup requires source_id')
        result = lookup(args.source_id, manifest, reviews, Path(args.manifest).parent, args.include_text)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
