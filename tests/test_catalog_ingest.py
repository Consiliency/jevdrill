import importlib.util
import hashlib
import json
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

spec = importlib.util.spec_from_file_location('ingest', Path(__file__).parents[1] / 'scripts/catalog_ingest.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class IngestionTests(unittest.TestCase):
    def setUp(self):
        self.c = {'repository': 'Owner/Repo', 'path': 'a/SKILL.md', 'url': 'https://example.org', 'blob_sha': 'a', 'source_tree_sha': 'tree'}
        self.rid = m.identity('Owner/Repo', 'a/SKILL.md')
        self.obs = {self.rid: {'sha256': 'hash', 'text_path': 'texts/hash.txt'}}

    def test_identity(self):
        self.assertEqual(self.rid, m.identity('owner/repo', 'a/SKILL.md'))
        self.assertNotEqual(self.rid, m.identity('owner/repo', 'A/SKILL.md'))
        with self.assertRaises(ValueError):
            m.identity('owner/repo', '../SKILL.md')

    def test_corrupt_cache_repaired_and_bad_replacement_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = b'verified pinned source'
            sha = hashlib.sha256(data).hexdigest()
            path = Path(tmp) / (sha + '.txt')
            path.write_bytes(b'truncated')
            m.cache_content(path, data, sha)
            self.assertEqual(path.read_bytes(), data)
            with self.assertRaises(ValueError):
                m.cache_content(path, b'unverified', sha)
            self.assertEqual(path.read_bytes(), data)

    def test_refresh_skips_only_verified_complete_same_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            inventory = out / 'inventory.json'
            data = b'---\nname: Example\n---\n# Content'
            candidate = dict(self.c, blob_sha=m.blob_hash(data))
            inventory.write_text(json.dumps({'sources': [{'repository': 'Owner/Repo'}], 'candidates': [candidate]}))
            args = SimpleNamespace(output=tmp, inventory=str(inventory), command='refresh', workers=1)
            def fetch_result(url):
                return json.dumps({'sha': 'commit', 'commit': {'tree': {'sha': 'tree'}}} if '/commits/' in url else {'default_branch': 'main'}).encode()
            with patch.object(m, 'fetch', side_effect=fetch_result), patch.object(m, 'archive', return_value={'a/SKILL.md': data}) as archive:
                m.run(args)
                self.assertEqual(archive.call_count, 1)
                m.run(args)
                self.assertEqual(archive.call_count, 1)
                manifest = json.loads((out / 'manifest.json').read_text())
                row = manifest['records'][0]
                previous = manifest['sources'][0]
                self.assertFalse(m.reusable_refresh(dict(previous, scope_version='discovery-inventory-v1'), [row], 'tree', out))
                self.assertFalse(m.reusable_refresh(previous, [row], 'changed-tree', out))
                self.assertFalse(m.reusable_refresh(dict(previous, status='fetch_error'), [row], 'tree', out))
                (out / row['text_path']).write_bytes(b'corrupt')
                m.run(args)
                self.assertEqual(archive.call_count, 2)
                self.assertEqual((out / row['text_path']).read_bytes(), data)

    def test_atomic_failure_preserves_previous_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'manifest.json'
            path.write_bytes(b'{"prior":true}')
            with patch.object(m.os, 'replace', side_effect=OSError('interrupted before rename')):
                with self.assertRaises(OSError):
                    m.atomic_write(path, b'{"new":true}')
            self.assertEqual(path.read_bytes(), b'{"prior":true}')
            self.assertEqual(list(Path(tmp).iterdir()), [path])
            m.atomic_write(path, b'{"new":true}')
            self.assertEqual(path.read_bytes(), b'{"new":true}')

    def test_output_lock_excludes_second_writer_and_releases(self):
        with tempfile.TemporaryDirectory() as tmp:
            with m.output_lock(Path(tmp)):
                with self.assertRaises(RuntimeError):
                    with m.output_lock(Path(tmp)):
                        self.fail('second writer acquired lock')
            with m.output_lock(Path(tmp)):
                pass

    def test_idempotence_and_changes(self):
        rows, change = m.integrate([], [self.c], self.obs, 't1')
        self.assertEqual(len(change['added']), 1)
        again, change = m.integrate(rows, [self.c], self.obs, 't2')
        self.assertEqual(len(again), 1)
        self.assertEqual(len(again[0]['versions']), 1)
        self.assertEqual(again[0]['first_seen'], 't1')
        self.assertEqual(len(change['unchanged']), 1)
        changed = dict(self.c, blob_sha='b')
        later, change = m.integrate(again, [changed], {self.rid: {'sha256': 'new', 'text_path': 'texts/new.txt'}}, 't3')
        self.assertEqual(len(change['changed']), 1)
        self.assertEqual(len(later[0]['versions']), 2)
        removed, change = m.integrate(later, [], {}, 't4', ['Owner/Repo'])
        self.assertEqual(removed[0]['status'], 'removed')
        self.assertEqual(len(change['removed']), 1)

    def test_failure_is_not_removal(self):
        rows, _ = m.integrate([], [self.c], self.obs, 't1')
        again, change = m.integrate(rows, [], {}, 't2')
        self.assertEqual(again[0]['status'], 'ok')
        self.assertFalse(change['removed'])
        failed, change = m.integrate(rows, [self.c], {self.rid: {'error': 'network'}}, 't2')
        self.assertEqual(failed[0]['sha256'], 'hash')
        self.assertFalse(change['removed'])

    def test_dedup_hashes(self):
        self.assertEqual(m.normalized_hash('A  B\n'), m.normalized_hash('a b'))
        self.assertNotEqual(m.blob_hash(b'A B'), m.blob_hash(b'a b'))
        self.assertEqual(m.blob_hash(b''), 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391')

    def test_metadata(self):
        result = m.metadata('---\nname: Test\ndescription: hello\n---\n# Title\n[Link](https://example.org)\npip install x\n{{template}}', 'SKILL.md', {'LICENSE': b'MIT'})
        self.assertEqual(result['name'], 'Test')
        self.assertEqual(result['headings'], ['Title'])
        self.assertEqual(result['license']['nearby_files'][0]['path'], 'LICENSE')
        self.assertTrue(result['dependency_hints'])
        self.assertTrue(result['template_hints'])


if __name__ == '__main__':
    unittest.main()
