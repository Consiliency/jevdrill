#!/usr/bin/env python3
"""Discover immutable first-level collection candidates without executing sources."""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote
import catalog_ingest as ingest

REPOSITORIES = ['mattpocock/skills', 'anthropics/skills', 'Egonex-AI/Understand-Anything', 'K-Dense-AI/scientific-agent-skills', 'wshobson/agents', 'VoltAgent/awesome-agent-skills', 'pbakaus/impeccable', 'addyosmani/agent-skills', 'alirezarezvani/claude-skills', 'shanraisshan/draw-json-architecture-skill']
DIRECTORY = 'VoltAgent/awesome-agent-skills'
ORIGIN = 'shanraisshan/claude-code-best-practice'


def github(repo, suffix=''):
    return json.loads(ingest.fetch('https://api.github.com/repos/' + repo + suffix))


def pinned_tree(repo):
    info = github(repo)
    commit = github(repo, '/commits/' + quote(info['default_branch'], safe=''))
    tree = github(repo, '/git/trees/' + commit['commit']['tree']['sha'] + '?recursive=1')
    if tree.get('truncated'):
        raise ValueError('recursive tree truncated; incomplete discovery is not accepted')
    return info['default_branch'], commit['sha'], tree


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('research/collection-expansion'))
    parser.add_argument('--known-manifest', type=Path, default=Path('research/ingestion/refresh-check/manifest.json'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    evidence = args.output / 'ingestion'
    evidence.mkdir(exist_ok=True)
    known = json.loads(args.known_manifest.read_text())
    known_rows = {r['id']: r for r in known['records']}
    now = datetime.now(timezone.utc).isoformat()
    branch, revision, tree = pinned_tree(ORIGIN)
    readme = next(r for r in tree['tree'] if r['path'].lower() == 'readme.md')
    readme_bytes = ingest.fetch('https://raw.githubusercontent.com/' + ORIGIN + '/' + revision + '/' + readme['path'])
    if ingest.blob_hash(readme_bytes) != readme['sha']:
        raise ValueError('referring README Git hash mismatch')
    ingest.atomic_write(evidence / 'referring-README.md', readme_bytes)
    origin = {'repository': ORIGIN, 'commit_sha': revision, 'tree_sha': tree['sha'], 'blob_sha': readme['sha'], 'sha256': hashlib.sha256(readme_bytes).hexdigest(), 'source_url': 'https://github.com/' + ORIGIN + '/blob/' + revision + '/' + readme['path'] + '#-skill-collections', 'section': 'Skill Collections', 'direct_collection_urls': ['https://github.com/' + r for r in REPOSITORIES]}
    def discover(repo):
        try:
            branch, revision, tree = pinned_tree(repo)
            matching = [r for r in tree['tree'] if r['type'] == 'blob' and r.get('mode') != '120000' and ingest.supported(r['path'])]
            unchanged, changed, candidates = [], [], []
            for item in matching:
                rid = ingest.identity(repo, item['path'])
                old = known_rows.get(rid)
                if old and old.get('blob_sha') == item['sha']:
                    unchanged.append(rid)
                    continue
                if old:
                    changed.append(rid)
                candidates.append({'repository': repo, 'path': item['path'], 'url': 'https://github.com/' + repo + '/blob/' + revision + '/' + quote(item['path']), 'blob_sha': item['sha'], 'source_tree_sha': tree['sha'], 'source_commit_sha': revision, 'kind': 'skill' if item['path'].endswith('SKILL.md') else 'prompt', 'review_status': 'path_discovered_only', 'retrieved_at': now, 'discovery_origin': origin['source_url']})
            status = 'directory_handled_separately' if repo == DIRECTORY else ('new_or_changed_candidates' if candidates else ('known_unchanged_reused' if unchanged else 'no_supported_artifacts'))
            coverage = {'repository': repo, 'source_url': 'https://github.com/' + repo, 'default_branch': branch, 'commit_sha': revision, 'tree_sha': tree['sha'], 'status': status, 'supported_artifact_count': len(matching), 'new_candidate_count': len(candidates) - len(changed), 'changed_existing_count': len(changed), 'reused_unchanged_count': len(unchanged), 'reused_source_ids': unchanged, 'changed_source_ids': changed, 'discovery_origin': origin['source_url']}
            if repo == DIRECTORY:
                candidates = []
            return coverage, candidates
        except Exception as exc:
            return {'repository': repo, 'status': 'discovery_error', 'error': type(exc).__name__ + ': ' + str(exc), 'discovery_origin': origin['source_url']}, []
    coverage, candidates = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for result, rows in pool.map(discover, REPOSITORIES):
            coverage.append(result)
            candidates.extend(rows)
            print(result['repository'], result['status'], len(rows), flush=True)
    inventory = {'created_at': now, 'scope': 'New/changed supported bodies in ten first-level collections; unchanged known artifacts reused, directory outbound links handled separately.', 'discovery_origin': origin, 'sources': [{'repository': r['repository'], 'tree_sha': r['tree_sha'], 'commit_sha': r['commit_sha'], 'status': 'ok', 'tree_truncated': False, 'artifact_count': sum(c['repository'] == r['repository'] for c in candidates)} for r in coverage if any(c['repository'] == r['repository'] for c in candidates)], 'candidates': candidates}
    ingest.atomic_write(args.output / 'inventory.json', (json.dumps(inventory, indent=2) + '\n').encode())
    ingest.atomic_write(evidence / 'collection-coverage.json', (json.dumps({'observed_at': now, 'origin': origin, 'collections': coverage}, indent=2) + '\n').encode())
    print('Candidates', len(candidates), 'discovery_errors', sum(r['status'] == 'discovery_error' for r in coverage))


if __name__ == '__main__':
    main()
