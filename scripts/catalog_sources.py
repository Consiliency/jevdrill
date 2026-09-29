"""Track discovery URLs separately from versioned candidate content."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import fcntl
import hashlib
import json
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def source_key(url):
    parts = urlsplit(url)
    path = parts.path.rstrip('/')
    segments = path.strip('/').split('/')
    host = parts.hostname.lower()
    if host == 'github.com' and len(segments) >= 2:
        repo = '/'.join(segments[:2]).lower().removesuffix('.git')
        if len(segments) > 4 and segments[2] in ('blob', 'tree'):
            return 'github:' + repo + ':' + '/'.join(segments[4:])
        if len(segments) == 2:
            return 'github:' + repo
    if host == 'raw.githubusercontent.com' and len(segments) >= 4:
        return 'github:' + '/'.join(segments[:2]).lower() + ':' + '/'.join(segments[3:])
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ''))


def reconcile(registry, sources, now):
    records = {r['id']: r for r in registry.get('sources', [])}
    added = []
    for item in sources:
        key = source_key(item['url'])
        if key not in records:
            records[key] = {'id': key, 'url': item['url'], 'aliases': [],
                            'catalog_record_ids': [], 'first_seen': now,
                            'versions': [], 'scan_status': 'not_scanned'}
            added.append(key)
        record = records[key]
        record['last_seen'] = now
        record['aliases'] = sorted(set(record['aliases'] + [item['url']]))
        if item.get('catalog_record_id'):
            record['catalog_record_ids'] = sorted(set(record['catalog_record_ids'] + [item['catalog_record_id']]))
        record['source_kind'] = item.get('source_kind', record.get('source_kind', 'artifact'))
    return {'schema_version': 1, 'updated_at': now, 'sources': sorted(records.values(), key=lambda r: r['id'])}, added


def scan(record, now, opener=urlopen):
    key = record['id'] if 'id' in record else source_key(record['url'])
    target = record['url']
    kind = 'raw_http_body'
    if key.startswith('github:'):
        repo_path = key[len('github:'):].split(':', 1)
        if len(repo_path) == 1:
            target = 'https://api.github.com/repos/' + repo_path[0] + '/commits/HEAD'
            kind = 'git_commit'
        else:
            parts = urlsplit(record['url'])
            segments = parts.path.strip('/').split('/')
            if parts.hostname.lower() == 'github.com' and len(segments) > 4 and segments[2] == 'blob':
                target = 'https://raw.githubusercontent.com/' + '/'.join(segments[:2] + segments[3:])
                kind = 'git_file_body'
            elif parts.hostname.lower() == 'raw.githubusercontent.com':
                kind = 'git_file_body'
    headers = {'User-Agent': 'jev-advisor-catalog/1'}
    same_representation = record.get('fingerprint_kind') == kind and record.get('scan_url') == target
    if same_representation and record.get('etag'):
        headers['If-None-Match'] = record['etag']
    if same_representation and record.get('last_modified'):
        headers['If-Modified-Since'] = record['last_modified']
    try:
        with opener(Request(target, headers=headers), timeout=25) as response:
            body = response.read(2_000_001)
            if len(body) > 2_000_000:
                raise ValueError('source exceeds 2MB scan limit')
            if kind == 'git_commit':
                body = json.loads(body)['sha'].encode()
            digest = hashlib.sha256(body).hexdigest()
            changed = not same_representation or digest != record.get('sha256')
            status = 'new_snapshot' if not same_representation or not record.get('sha256') else ('changed' if changed else 'unchanged')
            if changed:
                record['versions'].append({'observed_at': now, 'sha256': digest,
                                           'resolved_url': response.url, 'fingerprint_kind': kind})
            record.update(sha256=digest, resolved_url=response.url,
                          scan_url=target, fingerprint_kind=kind,
                          http_status=getattr(response, 'status', 200),
                          etag=response.headers.get('ETag'),
                          last_modified=response.headers.get('Last-Modified'))
            record.pop('error_type', None)
    except HTTPError as error:
        status = 'unchanged' if error.code == 304 else 'fetch_error'
        record['http_status'] = error.code
        error.close()
    except Exception as error:
        status = 'fetch_error'
        record['error_type'] = type(error).__name__
    record.update(scan_status=status, last_checked=now)
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['sync', 'scan'])
    parser.add_argument('--limit', type=int, default=20)
    parser.add_argument('--workers', type=int, choices=range(1, 9), default=4)
    parser.add_argument('--additional-catalog', type=Path, action='append', default=[])
    args = parser.parse_args()
    path = ROOT / 'research/source-registry.json'
    with path.with_suffix('.lock').open('w') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        run(args, path)


def run(args, path):
    registry = json.loads(path.read_text()) if path.exists() else {}
    now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    if args.command == 'sync':
        catalog = json.loads((ROOT / 'research/catalog.json').read_text())
        benchmarks = json.loads((ROOT / 'research/benchmark-sources.json').read_text())
        inventory = json.loads((ROOT / 'research/discovery-inventory.json').read_text())
        sources = [{'url': r['url'], 'catalog_record_id': r['id'], 'source_kind': r['kind']} for r in catalog + benchmarks]
        sources += [{'url': 'https://github.com/' + r['repository'], 'source_kind': 'repository'} for r in inventory['sources']]
        for extra_path in args.additional_catalog:
            extra = json.loads(extra_path.read_text())
            sources += [{'url': r['url'], 'catalog_record_id': r['id'],
                         'source_kind': r.get('kind', 'skill_lead')} for r in extra]
        registry, added = reconcile(registry, sources, now)
        report = {'sources': len(registry['sources']), 'new_sources': len(added)}
    else:
        if not registry:
            raise ValueError('Run sync first')
        if args.limit < 1:
            raise ValueError('--limit must be positive')
        pending = sorted(registry['sources'], key=lambda r: (r.get('last_checked', ''), r['id']))[:args.limit]
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            results = list(pool.map(lambda r: {'id': r['id'], 'status': scan(r, now)}, pending))
        report = {'checked': len(results), 'results': results}
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(registry, indent=2) + '\n')
    temporary.replace(path)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
