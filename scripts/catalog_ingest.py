#!/usr/bin/env python3
"""Versioned, content-addressed public skill ingestion; never executes sources."""
import argparse
import concurrent.futures
import fcntl
import hashlib
import io
import json
import os
import re
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path

SCOPE_VERSION = 'supported-artifacts-v1'


def reusable_refresh(previous, rows, tree_sha, out):
    if not previous or previous.get('status') != 'ok' or previous.get('scope_version') != SCOPE_VERSION or previous.get('tree_sha') != tree_sha:
        return False
    active = [r for r in rows if r['status'] != 'removed']
    if len(active) != previous.get('artifact_count'):
        return False
    for row in active:
        if row['status'] != 'ok' or not row.get('text_path') or not row.get('metadata'):
            return False
        path = (out / row['text_path']).resolve()
        if not path.is_relative_to(out.resolve()):
            return False
        try:
            if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
                return False
        except OSError:
            return False
    return True


def atomic_write(path, data):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.' + path.name + '.', delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def cache_content(path, data, expected_sha):
    if hashlib.sha256(data).hexdigest() != expected_sha:
        raise ValueError('replacement content hash mismatch')
    if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        atomic_write(path, data)


@contextmanager
def output_lock(out):
    out.mkdir(parents=True, exist_ok=True)
    with (out / '.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError('another ingestion owns this output directory') from exc
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def identity(repo, path):
    if path.startswith('/') or '..' in path.split('/'):
        raise ValueError('invalid repository-relative path')
    return 'github:' + repo.lower() + ':' + path


def blob_hash(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def normalized_hash(text):
    return hashlib.sha256(' '.join(text.lower().split()).encode()).hexdigest()


def fetch(url):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'jev-catalog-ingest/1', 'Accept': 'application/vnd.github+json'}), timeout=60) as response:
                data = response.read(256 * 1024 * 1024 + 1)
                if len(data) > 256 * 1024 * 1024:
                    raise ValueError('download exceeds 256 MiB limit')
                return data
        except urllib.error.HTTPError as exc:
            if exc.code not in (403, 429, 500, 502, 503, 504) or attempt == 3:
                raise
            time.sleep(min(30, max(2 ** attempt, int(exc.headers.get('Retry-After', '0')) if exc.headers.get('Retry-After', '0').isdigit() else 0)))
        except (TimeoutError, urllib.error.URLError):
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def supported(path):
    name = path.rsplit('/', 1)[-1]
    return name == 'SKILL.md' or name in ('system.md', 'user.md') or name.endswith(('.agent.md', '.prompt.md', '.instructions.md', '.chatmode.md'))


def archive(repo, revision):
    files = {}
    data = fetch('https://codeload.github.com/' + repo + '/tar.gz/' + revision)
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as tar:
        total = 0
        for member in tar:
            if not member.isfile():
                continue
            parts = member.name.split('/', 1)
            if len(parts) != 2 or '..' in parts[1].split('/') or parts[1].startswith('/'):
                continue
            path = parts[1]
            if supported(path) and member.size > 4 * 1024 * 1024:
                raise ValueError('supported artifact exceeds member limit: ' + path)
            # Only textual artifacts, nearby templates, and licenses are read.
            if member.size > 4 * 1024 * 1024 or not (path.lower().endswith(('.md', '.txt', '.yaml', '.yml', '.json')) or Path(path).name.lower().startswith(('license', 'copying', 'notice'))):
                continue
            total += member.size
            if total > 256 * 1024 * 1024:
                raise ValueError('unpacked text exceeds 256 MiB limit')
            files[path] = tar.extractfile(member).read()
    return files


def metadata(text, path, files):
    match = re.match(r'\A---\s*\n(.*?)\n---(?:\s*\n|$)', text, re.S)
    fm = match.group(1) if match else ''
    def field(key):
        m = re.search(r'^' + key + r':\s*(.*)$', fm, re.M)
        if not m:
            return None
        value = m.group(1).strip().strip('\"\'')
        if value in ('>', '|', '>-', '|-'):
            tail = fm[m.end():]
            value = ' '.join(re.findall(r'^\s+(.+)$', tail.split('\n\n')[0], re.M))
        return value
    parents = list(Path(path).parents)
    licenses = []
    for parent in parents:
        for candidate in files:
            if Path(candidate).parent == parent and Path(candidate).name.lower().startswith(('license', 'copying')):
                data = files[candidate]
                licenses.append({'path': candidate, 'sha256': hashlib.sha256(data).hexdigest(), 'excerpt': data.decode('utf-8', 'replace')[:1200]})
    return {'name': field('name'), 'description': field('description'), 'frontmatter_raw': fm,
            'headings': re.findall(r'^#{1,6}\s+(.+)$', text, re.M),
            'links': sorted(set(re.findall(r'\[[^\]]*\]\(([^)]+)\)', text))),
            'license': {'declared': field('license'), 'nearby_files': licenses, 'assessment': 'unverified; nearby license does not establish artifact reuse rights'},
            'dependency_hints': [line[:500] for line in text.splitlines() if re.search(r'\b(pip install|npm install|uv add|npx |requires?|dependencies|API.key|MCP)\b', line, re.I)][:40],
            'template_hints': [line[:500] for line in text.splitlines() if re.search(r'template|\{\{[^}]+\}\}|\$\{', line, re.I)][:30]}


def integrate(old, candidates, observations, now, refreshed_repos=()):
    records = {r['id']: dict(r) for r in old}
    changes = {key: [] for key in ('added', 'changed', 'removed', 'unchanged', 'failed')}
    seen = set()
    for c in candidates:
        rid = identity(c['repository'], c['path'])
        seen.add(rid)
        prev = records.get(rid)
        obs = observations[rid]
        row = dict(prev or {})
        row.update({'id': rid, 'repository': c['repository'], 'path': c['path'], 'kind': c.get('kind', 'skill' if c['path'].endswith('SKILL.md') else 'prompt'), 'original_urls': sorted(set((prev or {}).get('original_urls', []) + [c['url']])), 'first_seen': (prev or {}).get('first_seen', now), 'last_seen': now})
        row['last_attempt'] = now
        if obs.get('error'):
            row.update(status='fetch_error', error=obs['error'])
            changes['failed'].append(rid)
        else:
            row.pop('error', None)
            row.update(obs)
            row.update(status='ok', blob_sha=c['blob_sha'], source_tree_sha=c['source_tree_sha'], pinned_source_url='https://api.github.com/repos/' + c['repository'] + '/git/blobs/' + c['blob_sha'])
            versions = list((prev or {}).get('versions', []))
            if not versions or versions[-1]['blob_sha'] != c['blob_sha']:
                versions.append({'observed_at': now, 'blob_sha': c['blob_sha'], 'source_tree_sha': c['source_tree_sha'], 'sha256': obs['sha256'], 'text_path': obs['text_path']})
            row['versions'] = versions
            change = 'added' if prev is None or not prev.get('sha256') else ('changed' if prev['sha256'] != obs['sha256'] or prev['status'] == 'removed' else 'unchanged')
            changes[change].append(rid)
        records[rid] = row
    for rid, row in records.items():
        if row['repository'] in refreshed_repos and rid not in seen and row['status'] != 'removed':
            row['status'] = 'removed'
            row['removed_at'] = now
            changes['removed'].append(rid)
    return sorted(records.values(), key=lambda r: r['id']), changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('ingest', 'refresh'))
    parser.add_argument('--inventory', default='research/discovery-inventory.json')
    parser.add_argument('--output', default='research/ingestion')
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    with output_lock(Path(args.output)):
        run(args)


def run(args):
    out = Path(args.output)
    (out / 'texts').mkdir(parents=True, exist_ok=True)
    inventory = json.loads(Path(args.inventory).read_text())
    old_manifest = json.loads((out / 'manifest.json').read_text()) if (out / 'manifest.json').exists() else {}
    old = old_manifest.get('records', [])
    prior_sources = {s['repository']: s for s in old_manifest.get('sources', [])}
    now = datetime.now(timezone.utc).isoformat()
    grouped = {s['repository']: [c for c in inventory['candidates'] if c['repository'] == s['repository']] for s in inventory['sources']}
    candidates, observations, sources, refreshed = [], {}, [], []
    def process(item):
        repo, discovered = item
        revision = discovered[0]['source_tree_sha']
        source_state = {'tree_sha': revision, 'scope_version': 'discovery-inventory-v1', 'default_branch': None, 'archive_downloaded': True}
        try:
            if args.command == 'refresh':
                info = json.loads(fetch('https://api.github.com/repos/' + repo))
                commit = json.loads(fetch('https://api.github.com/repos/' + repo + '/commits/' + urllib.parse.quote(info['default_branch'], safe='')))
                revision = commit['sha']
                source_state.update(tree_sha=commit['commit']['tree']['sha'], default_branch=info['default_branch'], scope_version=SCOPE_VERSION)
                prior_rows = [r for r in old if r['repository'] == repo]
                if reusable_refresh(prior_sources.get(repo), prior_rows, source_state['tree_sha'], out):
                    active = [r for r in prior_rows if r['status'] != 'removed']
                    discovered = [{'repository': repo, 'path': r['path'], 'kind': r['kind'], 'blob_sha': r['blob_sha'], 'source_tree_sha': source_state['tree_sha'], 'url': r['original_urls'][0]} for r in active]
                    result = {r['id']: {key: r[key] for key in ('sha256', 'text_path', 'normalized_sha256', 'metadata', 'verified_git_blob')} for r in active}
                    return discovered, result, dict(source_state, repository=repo, revision=revision, status='ok', artifact_count=len(discovered), archive_downloaded=False)
            files = archive(repo, revision)
            if args.command == 'refresh':
                discovered = [{'repository': repo, 'path': p, 'blob_sha': blob_hash(data), 'source_tree_sha': commit['commit']['tree']['sha'], 'url': 'https://github.com/' + repo + '/blob/' + revision + '/' + urllib.parse.quote(p)} for p, data in files.items() if supported(p)]
            result = {}
            for c in discovered:
                rid = identity(repo, c['path'])
                data = files.get(c['path'])
                if data is None or blob_hash(data) != c['blob_sha']:
                    result[rid] = {'error': 'artifact missing from pinned archive or Git blob hash mismatch'}
                    continue
                sha = hashlib.sha256(data).hexdigest()
                text = data.decode('utf-8', 'replace')
                dest = out / 'texts' / (sha + '.txt')
                cache_content(dest, data, sha)
                result[rid] = {'sha256': sha, 'text_path': 'texts/' + sha + '.txt', 'normalized_sha256': normalized_hash(text), 'metadata': metadata(text, c['path'], files), 'verified_git_blob': True}
            return discovered, result, dict(source_state, repository=repo, revision=revision, status='ok', artifact_count=len(discovered))
        except Exception as exc:
            return discovered, {identity(repo, c['path']): {'error': type(exc).__name__ + ': ' + str(exc)} for c in discovered}, {'repository': repo, 'revision': revision, 'status': 'fetch_error', 'error': type(exc).__name__ + ': ' + str(exc)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(8, args.workers))) as pool:
        for cs, obs, source in pool.map(process, grouped.items()):
            candidates.extend(cs)
            observations.update(obs)
            sources.append(source)
            if args.command == 'refresh' and source['status'] == 'ok':
                refreshed.append(source['repository'])
            print(source['repository'], source['status'], len(cs), flush=True)
    records, changes = integrate(old, candidates, observations, now, refreshed)
    duplicate_groups = {}
    for field in ('sha256', 'normalized_sha256'):
        groups = {}
        for row in records:
            if row.get(field) and row['status'] != 'removed':
                groups.setdefault(row[field], []).append(row['id'])
        duplicate_groups[field] = {key: ids for key, ids in groups.items() if len(ids) > 1}
    manifest = {'schema_version': 1, 'updated_at': now, 'sources': sources, 'records': records}
    report = {'generated_at': now, 'command': args.command, 'counts': {k: len(v) for k, v in changes.items()}, 'changes': changes, 'source_errors': [s for s in sources if s['status'] != 'ok'], 'archives_skipped': sum(s.get('archive_downloaded') is False for s in sources)}
    for name, obj in [('manifest.json', manifest), ('duplicates.json', duplicate_groups), ('change-report.json', report)]:
        atomic_write(out / name, (json.dumps(obj, indent=2, ensure_ascii=False) + '\n').encode())
    (out / 'runs').mkdir(exist_ok=True)
    atomic_write(out / 'runs' / (now.replace(':', '-') + '.json'), (json.dumps(report, indent=2) + '\n').encode())
    print(json.dumps(report['counts']))


if __name__ == '__main__':
    main()
