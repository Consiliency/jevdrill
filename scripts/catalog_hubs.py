#!/usr/bin/env python3
"""Pinned, bounded skill-bundle inventory and selective text retrieval for directory hubs."""
import argparse
import concurrent.futures
import hashlib
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote
import catalog_ingest as ingest

EXCLUDED = {'vendor', 'vendored', 'node_modules', '.venv', 'venv', 'fixtures', '__fixtures__', 'testdata', 'tests', 'test', 'examples', 'example', 'dist', 'build', 'out', '.next', 'target', '.git', '__pycache__'}


def read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    ingest.atomic_write(path, (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode())


def api(repo, suffix):
    response = subprocess.run(['gh', 'api', '/repos/' + repo + suffix], capture_output=True, text=True, timeout=60)
    if response.returncode:
        raise RuntimeError('authenticated GitHub metadata request failed: ' + response.stderr.strip()[:300])
    return json.loads(response.stdout)


def path_exclusion(path):
    parts = path.split('/')[:-1]
    return next((part for part in parts if part.lower() in EXCLUDED), None)


def exclude_recovered_lane(sources, candidates):
    recovery = read(Path('research/collection-expansion/directory/path-recovery.json'), {})
    recovered = {c['source_id']: c['blob_sha'] for row in recovery.get('rows', []) for c in row.get('candidates', [])}
    by_repo = {s['repository']: s for s in sources}
    selected = []
    for c in candidates:
        rid = ingest.identity(c['repository'], c['path'])
        if recovered.get(rid) == c['blob_sha']:
            source = by_repo[c['repository']]
            source['excluded'].append({'path': c['path'], 'blob_sha': c['blob_sha'], 'reason': 'same_identity_blob_owned_by_direct_recovered_lane', 'source_id': rid})
            source['selected_count'] -= 1
        else:
            selected.append(c)
    return selected


def discover(root, entries_path=Path('research/collection-expansion/directory/hub-entries.json')):
    entries = read(entries_path)['entries']
    pins = read(Path('research/collection-expansion/directory/repository-pins.json'))
    known = {}
    for path in ['research/collection-expansion/combined-manifest.json', 'research/collection-expansion/directory/leaf-ingestion/manifest.json']:
        known.update({r['id']: r for r in read(Path(path))['records']})
    grouped = {}
    for entry in entries:
        repo = entry['upstream']['repository']
        grouped.setdefault(repo.lower(), {'repository': repo, 'entries': []})['entries'].append(entry)
    def inspect(group):
        repo = group['repository']
        safe = hashlib.sha256(repo.lower().encode()).hexdigest()
        tree_path = root / 'trees' / (safe + '.json')
        try:
            pin = pins.get(repo.lower() + '@HEAD') or next((p for k, p in pins.items() if k.split('@')[0] == repo.lower() and p.get('status') == 'ok'), None)
            if not pin or pin.get('status') != 'ok':
                commit = api(repo, '/commits/HEAD')
                pin = {'commit': commit['sha'], 'tree_sha': commit['commit']['tree']['sha'], 'status': 'ok'}
            cached = read(tree_path)
            if cached and cached.get('sha') == pin['tree_sha']:
                tree = cached
            else:
                tree = api(repo, '/git/trees/' + pin['tree_sha'] + '?recursive=1')
                write(tree_path, tree)
            if tree.get('truncated'):
                raise ValueError('tree truncated; no complete enumeration claim')
            files = [f for f in tree['tree'] if f['type'] == 'blob' and f.get('mode') != '120000']
            skills = [f for f in files if f['path'].rsplit('/', 1)[-1] == 'SKILL.md']
            selected, excluded, reused = [], [], []
            blobs = {}
            for item in sorted(skills, key=lambda f: (f['path'].startswith('.'), len(f['path']), f['path'])):
                path = item['path']
                why = path_exclusion(path)
                rid = ingest.identity(repo, path)
                if why:
                    excluded.append({'path': path, 'blob_sha': item['sha'], 'reason': 'excluded_path_segment:' + why})
                    continue
                old = known.get(rid)
                if old and old.get('blob_sha') == item['sha']:
                    reused.append({'source_id': rid, 'blob_sha': item['sha'], 'reason': 'known_same_identity_and_blob'})
                    blobs[item['sha']] = rid
                    continue
                if item['sha'] in blobs:
                    excluded.append({'path': path, 'blob_sha': item['sha'], 'reason': 'exact_blob_alias_within_repository', 'canonical_source_id': blobs[item['sha']]})
                    continue
                blobs[item['sha']] = rid
                selected.append({'repository': repo, 'path': path, 'url': 'https://github.com/' + repo + '/blob/' + pin['commit'] + '/' + quote(path), 'blob_sha': item['sha'], 'source_tree_sha': pin['tree_sha'], 'source_commit_sha': pin['commit'], 'kind': 'skill', 'discovery_entries': group['entries'], 'review_status': 'path_discovered_only'})
            roots = {str(Path(c['path']).parent) for c in selected}
            licenses = [f for f in files if Path(f['path']).name.lower().startswith(('license', 'copying', 'notice')) and any(Path(f['path']).parent in Path(c['path']).parents for c in selected)]
            return {'repository': repo, 'status': 'ok', 'classification': 'skill_collection_bundle' if len(skills) > 1 else ('single_skill_repository' if skills else 'repository_without_supported_skill'), 'commit_sha': pin['commit'], 'tree_sha': pin['tree_sha'], 'all_skill_paths': len(skills), 'selected_count': len(selected), 'reused': reused, 'excluded': excluded, 'license_files': licenses, 'directory_entries': group['entries']}, selected
        except Exception as exc:
            return {'repository': repo, 'status': 'discovery_error', 'error': type(exc).__name__ + ': ' + str(exc), 'directory_entries': group['entries']}, []
    sources, candidates = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(inspect, group) for group in grouped.values()]
        for f in concurrent.futures.as_completed(futures):
            source, rows = f.result()
            sources.append(source)
            candidates.extend(rows)
            if len(sources) % 20 == 0:
                print('inventoried repositories', len(sources), 'new candidates', len(candidates), flush=True)
    sources.sort(key=lambda s: s['repository'].lower())
    candidates.sort(key=lambda c: ingest.identity(c['repository'], c['path']))
    candidates = exclude_recovered_lane(sources, candidates)
    inventory = {'schema_version': 1, 'scope': 'Only SKILL.md in directory-referenced repository hubs; no recursive repository discovery.', 'excluded_path_segments': sorted(EXCLUDED), 'alias_rule': 'Identical Git blob within one repository retained as explicit alias, one canonical body selected.', 'sources': sources, 'candidates': candidates}
    write(root / 'inventory.json', inventory)
    summary = {'directory_hub_entries': len(entries), 'unique_repositories': len(sources), 'new_candidate_bodies': len(candidates), 'known_same_path_reused': sum(len(s.get('reused', [])) for s in sources), 'excluded_or_alias_paths': sum(len(s.get('excluded', [])) for s in sources), 'discovery_errors': [s for s in sources if s['status'] != 'ok'], 'classifications': {key: sum(s.get('classification') == key for s in sources) for key in ['skill_collection_bundle', 'single_skill_repository', 'repository_without_supported_skill']}, 'largest_bundles': sorted([{'repository': s['repository'], 'new_candidates': s.get('selected_count', 0)} for s in sources], key=lambda x: -x['new_candidates'])[:15]}
    write(root / 'discovery-summary.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k != 'discovery_errors'}, indent=2))


def fetch_bodies(root):
    inventory = read(root / 'inventory.json')
    out = root / 'ingestion'
    (out / 'texts').mkdir(parents=True, exist_ok=True)
    previous = read(out / 'manifest.json', {}).get('records', [])
    now = datetime.now(timezone.utc).isoformat()
    sources = {s['repository']: s for s in inventory['sources']}
    licenses = {repo: {} for repo in sources}
    license_tasks = [(repo, item) for repo, source in sources.items() for item in source.get('license_files', [])]
    unique_license_tasks = {}
    for task in license_tasks:
        unique_license_tasks.setdefault(task[1]['sha'], task)
    license_reports = []
    license_results = {}
    def license_body(task):
        repo, item = task
        try:
            if item.get('size', 0) > 1024 * 1024:
                raise ValueError('license exceeds 1MiB limit')
            data = ingest.fetch('https://raw.githubusercontent.com/' + repo + '/' + sources[repo]['commit_sha'] + '/' + quote(item['path']))
            if ingest.blob_hash(data) != item['sha']:
                raise ValueError('license Git blob mismatch')
            return repo, item, data, None
        except Exception as exc:
            return repo, item, None, type(exc).__name__ + ': ' + str(exc)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for repo, item, data, error in pool.map(license_body, unique_license_tasks.values()):
            license_results[item['sha']] = (data, error)
    for repo, item in license_tasks:
        data, error = license_results[item['sha']]
        license_reports.append({'repository': repo, 'path': item['path'], 'blob_sha': item['sha'], 'status': 'fetch_error' if error else 'ok', 'error': error})
        if data is not None:
            licenses[repo][item['path']] = data
    write(out / 'license-fetch-report.json', license_reports)
    previous_by_id = {r['id']: r for r in previous}
    def one(c):
        rid = ingest.identity(c['repository'], c['path'])
        try:
            old = previous_by_id.get(rid)
            if old and old.get('blob_sha') != c['blob_sha']:
                old = None
            data = (out / old['text_path']).read_bytes() if old and (out / old['text_path']).exists() else None
            if data is None or ingest.blob_hash(data) != c['blob_sha']:
                data = ingest.fetch('https://raw.githubusercontent.com/' + c['repository'] + '/' + c['source_commit_sha'] + '/' + quote(c['path']))
            if len(data) > 4 * 1024 * 1024 or ingest.blob_hash(data) != c['blob_sha']:
                raise ValueError('source Git hash mismatch or source exceeds 4MiB')
            sha = hashlib.sha256(data).hexdigest()
            ingest.cache_content(out / 'texts' / (sha + '.txt'), data, sha)
            text = data.decode('utf-8', 'replace')
            return rid, {'sha256': sha, 'normalized_sha256': ingest.normalized_hash(text), 'text_path': 'texts/' + sha + '.txt', 'verified_git_blob': True, 'metadata': ingest.metadata(text, c['path'], licenses[c['repository']]), 'directory_provenance': c['discovery_entries'], 'source_commit_sha': c['source_commit_sha'], 'curation_scope': 'repository_listed; individual skill was not separately directory-curated', 'review_status': 'not_reviewed'}
        except Exception as exc:
            return rid, {'error': type(exc).__name__ + ': ' + str(exc)}
    with ingest.output_lock(out):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            observations = dict(pool.map(one, inventory['candidates']))
        records, changes = ingest.integrate(previous, inventory['candidates'], observations, now)
        write(out / 'manifest.json', {'schema_version': 1, 'updated_at': now, 'sources': inventory['sources'], 'records': records})
        report = {'counts': {k: len(v) for k, v in changes.items()}, 'changes': changes}
        write(out / 'change-report.json', report)
        write(out / 'runs' / (now.replace(':', '-') + '.json'), report)
        print(json.dumps(report['counts']))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['discover', 'fetch'])
    p.add_argument('--root', type=Path, default=Path('research/collection-expansion/hubs'))
    p.add_argument('--entries', type=Path, default=Path('research/collection-expansion/directory/hub-entries.json'))
    a = p.parse_args()
    discover(a.root, a.entries) if a.command == 'discover' else fetch_bodies(a.root)
