"""Discover explicit VoltAgent directory entries; never treat listings as leaf reviews."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone
from urllib.parse import quote
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

import catalog_sources
import catalog_ingest


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fetch(url):
    with urlopen(Request(url, headers={'User-Agent': 'jev-directory-discovery/1'}), timeout=30) as response:
        raw = response.read(4_000_001)
        if len(raw) > 4_000_000:
            raise ValueError('Response exceeds4MB bound')
        return raw, response.url


def extract(text, pin):
    section, subsection, group, non_skill = '', '', 'official', False
    entries, exclusions = [], []
    for number, line in enumerate(text.splitlines(), 1):
        heading = re.search(r'<summary><h3[^>]*>(.*?)</h3></summary>', line)
        if heading:
            section, subsection, non_skill = html.unescape(heading.group(1)), '', False
        if line.startswith('### Community Skills'):
            group = 'community'
        elif line.startswith('### ') and section:
            subsection = line[4:]
        if 'not skills, but they pair with them' in line:
            non_skill = True
        match = re.match(r'^- \*\*\[([^\]]+)\]\((https?://[^)]+)\)\*\*\s*(?:-|:)?\s*(.*)$', line)
        table = re.match(r'^\| \[([^\]]+)\]\((https://github.com/[^)]+)\) \| (.*?) \|$', line)
        if table and 'skills add' in table.group(3):
            match = table
        if not match:
            continue
        name, url, description = match.groups()
        row = {'name': name, 'description': description, 'original_url': url,
               'section': section if not table else 'Additional skill collection table',
               'subsection': subsection if not table else '', 'directory_group': group,
               'line': number, 'discovery_origin': pin['raw_url'], 'directory_commit': pin['commit'],
               'directory_sha256': pin['sha256'], 'id': catalog_sources.source_key(url),
               'evidence_level': 'directory_listing_only', 'review_status': 'not_reviewed'}
        if non_skill and not table:
            exclusions.append(dict(row, exclusion_reason='Directory explicitly labels this block not skills'))
        else:
            entries.append(row)
    unique = {}
    for row in entries:
        if row['id'] not in unique:
            unique[row['id']] = dict(row, occurrences=[])
        unique[row['id']]['occurrences'].append({k: row[k] for k in ('name', 'description', 'section', 'subsection', 'line')})
    return list(unique.values()), exclusions, len(entries)


def github_target(url):
    p = urlsplit(url)
    parts = p.path.strip('/').split('/')
    if p.hostname != 'github.com' or len(parts) < 2:
        return None
    repo = '/'.join(parts[:2])
    if len(parts) == 2:
        return {'repository': repo, 'scope': 'repository_hub', 'path': None}
    if len(parts) >= 5 and parts[2] in ('tree', 'blob'):
        return {'repository': repo, 'scope': 'file' if parts[2] == 'blob' else 'directory',
                'ref': parts[3], 'path': '/'.join(parts[4:])}
    return {'repository': repo, 'scope': 'other_github_url', 'path': None}


def resolve(row, root, refresh=False):
    row = dict(row)
    url = row['original_url']
    if urlsplit(url).hostname == 'officialskills.sh':
        key = sha(url.encode())
        cache = root / 'upstream-pages' / (key + '.html')
        cache.parent.mkdir(parents=True, exist_ok=True)
        try:
            if cache.exists() and not refresh:
                raw = cache.read_bytes()
            else:
                raw, _ = fetch(url)
                cache.write_bytes(raw)
            links = sorted(set(html.unescape(u).rstrip('\\') for u in re.findall(r'https://github\.com/[^\s"<>]+', raw.decode())))
            parts = urlsplit(url).path.strip('/').split('/')
            repo_prefix = 'https://github.com/' + '/'.join(parts[:2]) + '/'
            paths = [u for u in links if u.lower().startswith(repo_prefix.lower()) and ('/tree/' in u or '/blob/' in u)]
            if not paths:
                paths = [u for u in links if '/tree/' in u or '/blob/' in u]
            if not paths:
                paths = [u for u in links if (github_target(u) or {}).get('scope') == 'repository_hub'
                         and urlsplit(u).path.strip('/').split('/')[0].lower() == parts[0].lower()]
            if len(paths) == 1:
                url = paths[0]
                row['resolution_status'] = 'upstream_link_observed'
            else:
                row['resolution_status'] = 'ambiguous_or_missing_upstream'
                row['upstream_candidates'] = paths
            immutable = cache.parent / ('content-' + sha(raw) + '.html')
            if not immutable.exists():
                immutable.write_bytes(raw)
            row['resolution_evidence'] = {'page_path': str(immutable.resolve()), 'page_sha256': sha(raw), 'original_url': row['original_url']}
        except Exception as exc:
            row['resolution_status'] = 'fetch_error'
            row['resolution_error'] = type(exc).__name__
    else:
        row['resolution_status'] = 'direct_source_link' if github_target(url) else 'external_unresolved'
    row['canonical_url'] = url
    row['canonical_id'] = catalog_sources.source_key(url)
    row['upstream'] = github_target(url)
    return row


def compare(entries, manifest, registry):
    existing = {r['id']: r for r in manifest['records']}
    repos = {r['repository'].lower() for r in manifest['records']}
    registered = {r['id'] for r in registry['sources']}
    for row in entries:
        target = row['upstream']
        exact = row['canonical_id']
        if target and target['scope'] == 'directory':
            exact += '/SKILL.md'
        row['existing_leaf_id'] = exact if exact in existing else None
        row['existing_repository'] = bool(target and target['repository'].lower() in repos)
        row['existing_registered_source'] = row['canonical_id'] in registered
        row['overlap_status'] = 'existing_exact_leaf' if row['existing_leaf_id'] else 'existing_repository_only' if row['existing_repository'] else 'not_in_existing_corpus'
    return entries


def fetch_leaves(root, manifest_path, workers, refresh=False):
    """Only the explicit referenced path's SKILL.md, or root SKILL.md for hubs."""
    entries = json.loads((root / 'entries.json').read_text())['entries']
    known = {r['id']: r for r in json.loads(manifest_path.read_text())['records']}
    pin_path = root / 'repository-pins.json'
    pins = json.loads(pin_path.read_text()) if pin_path.exists() else {}
    targets = {}
    for row in entries:
        target = row['upstream']
        if not target or target['scope'] not in ('directory', 'file', 'repository_hub'):
            continue
        path = target.get('path') or ''
        if target['scope'] != 'file' and not path.endswith('/SKILL.md') and path != 'SKILL.md':
            path = (path + '/' if path else '') + 'SKILL.md'
        if not catalog_ingest.supported(path):
            continue
        source_id = catalog_ingest.identity(target['repository'], path)
        item = targets.setdefault(source_id, {'source_id': source_id, 'repository': target['repository'],
                                  'path': path, 'ref': target.get('ref', 'HEAD'), 'entries': []})
        item['entries'].append(row['id'])
    needed = {(t['repository'], t['ref']) for t in targets.values()}
    def pin_one(target):
        repo, ref = target
        key = repo.lower() + '@' + ref
        if key in pins and not refresh:
            return key, pins[key]
        try:
            result = subprocess.run(['gh', 'api', 'repos/' + repo + '/commits/' + quote(ref, safe='')],
                                    capture_output=True, text=True, timeout=45)
            if result.returncode:
                return key, {'status': 'metadata_fetch_error'}
            record = json.loads(result.stdout)
            return key, {'status': 'ok', 'commit': record['sha'], 'commit_url': record['html_url'],
                         'repository': repo, 'ref': ref, 'tree_sha': record['commit']['tree']['sha']}
        except Exception as exc:
            return key, {'status': 'metadata_fetch_error', 'error_type': type(exc).__name__}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for key, value in pool.map(pin_one, sorted(needed)):
            pins[key] = value
    pin_path.write_text(json.dumps(pins, indent=2) + '\n')
    out = root / 'leaf-ingestion'
    (out / 'texts').mkdir(parents=True, exist_ok=True)
    previous = json.loads((out / 'manifest.json').read_text())['records'] if (out / 'manifest.json').exists() else []
    cached = {r['id']: r for r in previous}
    now = datetime.now(timezone.utc).isoformat()
    def retrieve(item):
        sid = item['source_id']
        pin = pins.get(item['repository'].lower() + '@' + item['ref'], {})
        if pin.get('status') != 'ok':
            return dict(item, status='repository_pin_unresolved'), None
        old = cached.get(sid)
        if old and old.get('source_commit_sha', old.get('source_tree_sha')) == pin['commit']:
            path = out / old['text_path']
            if path.exists() and sha(path.read_bytes()) == old['sha256']:
                old.update(source_tree_sha=pin['tree_sha'], tree_sha=pin['tree_sha'], source_commit_sha=pin['commit'], verified_git_blob=False)
                if not old.get('versions'):
                    old['versions'] = [{'observed_at': old['first_seen'], 'blob_sha': old['blob_sha'],
                                        'source_tree_sha': pin['tree_sha'], 'source_commit_sha': pin['commit'],
                                        'sha256': old['sha256'], 'text_path': old['text_path']}]
                return {'source_id': sid, 'entry_ids': item['entries'], 'status': 'unchanged_cached_leaf'}, old
        url = 'https://raw.githubusercontent.com/' + item['repository'] + '/' + pin['commit'] + '/' + quote(item['path'], safe='/')
        try:
            raw, resolved_url = fetch(url)
            text = raw.decode('utf-8')
            digest = sha(raw)
            if sid in known and known[sid]['sha256'] == digest:
                return {'source_id': sid, 'entry_ids': item['entries'], 'status': 'existing_body_verified_unchanged',
                        'sha256': digest, 'source_tree_sha': pin['tree_sha'], 'source_commit_sha': pin['commit'], 'tree_sha': pin['tree_sha'],
                        'blob_sha': catalog_ingest.blob_hash(raw), 'pinned_source_url': url}, None
            path = out / 'texts' / (digest + '.txt')
            catalog_ingest.cache_content(path, raw, digest)
            record = {'id': sid, 'repository': item['repository'], 'path': item['path'],
                      'kind': 'skill' if item['path'].endswith('SKILL.md') else 'prompt',
                      'original_urls': [r['original_url'] for r in entries if r['id'] in item['entries']],
                      'source_tree_sha': pin['tree_sha'], 'tree_sha': pin['tree_sha'], 'source_commit_sha': pin['commit'],
                      'blob_sha': catalog_ingest.blob_hash(raw), 'sha256': digest,
                      'normalized_sha256': catalog_ingest.normalized_hash(text),
                      'text_path': str(path.relative_to(out)), 'pinned_source_url': url,
                      'resolved_url': resolved_url, 'metadata': catalog_ingest.metadata(text, item['path'], {}),
                      'first_seen': old.get('first_seen', now) if old else now, 'last_seen': now,
                      'last_attempt': now, 'status': 'ok', 'discovery_entry_ids': item['entries'],
                      'verification': 'Raw body fetched at GitHub API-resolved commit, SHA256 and computed Git blob hash recorded; not independently tree-blob verified.',
                      'verified_git_blob': False,
                      'versions': (old.get('versions', []) if old else []) + [{'sha256': digest, 'blob_sha': catalog_ingest.blob_hash(raw), 'text_path': str(path.relative_to(out)), 'source_commit_sha': pin['commit'], 'source_tree_sha': pin['tree_sha'], 'observed_at': now}],
                      'review_status': 'not_reviewed'}
            return {'source_id': sid, 'entry_ids': item['entries'], 'status': 'new_leaf' if not old else 'changed_leaf'}, record
        except Exception as exc:
            return {'source_id': sid, 'entry_ids': item['entries'], 'status': 'leaf_fetch_error', 'error_type': type(exc).__name__,
                    'http_status': getattr(exc, 'code', None), 'attempted_url': url}, None
    records, observations = [], []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for observation, record in pool.map(retrieve, sorted(targets.values(), key=lambda t: t['source_id'])):
            observations.append(observation)
            if record:
                records.append(record)
    payload = {'schema_version': 1, 'records': records, 'scope': 'Only explicit directory-entry path SKILL.md or direct supported file; root SKILL.md probe for repository hubs'}
    (out / 'manifest.json').write_text(json.dumps(payload, indent=2) + '\n')
    report = {'targets': len(targets), 'new_pinned_leaf_records': len(records), 'statuses': dict(Counter(r['status'] for r in observations)),
              'observations': observations, 'limits': 'No recursive repository discovery. Missing root SKILL.md does not mean a collection is empty. Unresolved entries remain directory-only; newly fetched bodies are unreviewed.'}
    (root / 'leaf-report.json').write_text(json.dumps(report, indent=2) + '\n')
    return {k: v for k, v in report.items() if k != 'observations'}


def refresh_directory(root):
    snapshots = root / 'snapshots'
    snapshots.mkdir(exist_ok=True)
    for name in ('pin.json', 'README.pinned.md', 'entries.json', 'repository-pins.json'):
        path = root / name
        if path.exists():
            raw = path.read_bytes()
            (snapshots / (sha(raw) + '-' + name)).write_bytes(raw)
    result = subprocess.run(['gh', 'api', 'repos/VoltAgent/awesome-agent-skills/commits/HEAD'], capture_output=True, text=True, timeout=45, check=True)
    commit = json.loads(result.stdout)['sha']
    url = f'https://raw.githubusercontent.com/VoltAgent/awesome-agent-skills/{commit}/README.md'
    raw = fetch(url)[0]
    (root / 'README.pinned.md').write_bytes(raw)
    (root / 'pin.json').write_text(json.dumps({'repository': 'VoltAgent/awesome-agent-skills', 'commit': commit, 'sha256': sha(raw), 'raw_url': url}, indent=2) + '\n')


def export_source_catalog(root, rows):
    catalog = []
    for row in rows:
        catalog.append({'id': row['id'], 'url': row.get('canonical_url', row['original_url']), 'kind': 'directory_entry',
                        'metadata': {k: row.get(k) for k in ('name', 'description', 'original_url', 'canonical_url', 'resolution_status', 'discovery_origin', 'line')}})
        if row.get('canonical_url', row['original_url']) != row['original_url']:
            catalog.append({'id': row['id'], 'url': row['original_url'], 'kind': 'directory_entry_alias',
                            'metadata': {'canonical_url': row['canonical_url'], 'discovery_origin': row['discovery_origin']}})
    for folder in ('leaf-ingestion', 'recovered-leaf-ingestion', 'external-leaf-ingestion'):
        path = root / folder / 'manifest.json'
        if path.exists():
            for record in json.loads(path.read_text())['records']:
                catalog.append({'id': record['id'], 'url': record.get('raw_pinned_url', record.get('source_url', record['pinned_source_url'])),
                                'kind': 'skill_source', 'metadata': {'discovery_entry_ids': record.get('discovery_entry_ids', []), 'sha256': record['sha256']}})
    (root / 'source-catalog.json').write_text(json.dumps(catalog, indent=2) + '\n')
    return len(catalog)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('research/collection-expansion/directory'))
    parser.add_argument('--resolve', action='store_true')
    parser.add_argument('--fetch-leaves', action='store_true')
    parser.add_argument('--refresh-pins', action='store_true', help='Re-resolve live refs; archive prior directory evidence before updating')
    parser.add_argument('--manifest', type=Path, default=Path('research/collection-expansion/combined-manifest.json'))
    parser.add_argument('--workers', type=int, choices=range(1, 9), default=8)
    args = parser.parse_args()
    if args.fetch_leaves:
        print(json.dumps(fetch_leaves(args.root, args.manifest, args.workers, args.refresh_pins), indent=2))
        return
    if args.refresh_pins:
        refresh_directory(args.root)
    pin = json.loads((args.root / 'pin.json').read_text())
    raw = (args.root / 'README.pinned.md').read_bytes()
    if sha(raw) != pin['sha256']:
        raise ValueError('README pin hash mismatch')
    rows, excluded, total = extract(raw.decode(), pin)
    if args.resolve:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            rows = list(pool.map(lambda row: resolve(row, args.root, args.refresh_pins), rows))
        rows = compare(rows, json.loads(args.manifest.read_text()), json.loads(Path('research/source-registry.json').read_text()))
        external = args.root / 'external-resolution.json'
        if external.exists():
            observed = {r['entry_id']: r for r in json.loads(external.read_text())['rows']}
            for row in rows:
                ext = observed.get(row['id'])
                if ext:
                    row['external_resolution'] = ext
                    if ext.get('canonical_url'):
                        row.update(canonical_url=ext['canonical_url'], canonical_id=catalog_sources.source_key(ext['canonical_url']),
                                   upstream=github_target(ext['canonical_url']), resolution_status=ext['resolution_status'])
                    else:
                        row['resolution_status'] = ext['resolution_status']
    previous = json.loads((args.root / 'entries.json').read_text())['entries'] if (args.root / 'entries.json').exists() else []
    old = {r['id'] for r in previous}
    previous_by_id = {r['id']: r for r in previous}
    compare_fields = ('name', 'description', 'original_url', 'canonical_url', 'section', 'subsection')
    changed = [r['id'] for r in rows if r['id'] in previous_by_id and any(r.get(k) != previous_by_id[r['id']].get(k) for k in compare_fields)]
    summary = {'listing_occurrences': total, 'unique_entries': len(rows), 'excluded_non_skills': len(excluded),
               'new_entry_identities': len({r['id'] for r in rows} - old), 'removed_entry_identities': len(old - {r['id'] for r in rows}),
               'changed_entry_identities': len(changed),
               'identity_changes': {'added': sorted({r['id'] for r in rows} - old), 'changed': sorted(changed), 'removed': sorted(old - {r['id'] for r in rows})},
               'link_hosts': dict(Counter(urlsplit(r['original_url']).hostname for r in rows)),
               'upstream_scopes': dict(Counter((r.get('upstream') or {}).get('scope', 'http_file' if r.get('resolution_status') == 'standalone_http_skill_body_retrieved' else 'unresolved') for r in rows)),
               'resolution_statuses': dict(Counter(r.get('resolution_status', 'not_attempted') for r in rows)),
               'overlap': dict(Counter(r.get('overlap_status', 'not_compared') for r in rows)),
               'limits': 'Directory entries and resolved source links only. No leaf content review or validated admission implied.'}
    (args.root / 'entries.json').write_text(json.dumps({'pin': pin, 'entries': rows, 'excluded': excluded}, indent=2) + '\n')
    summary['source_catalog_rows'] = export_source_catalog(args.root, rows)
    (args.root / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
