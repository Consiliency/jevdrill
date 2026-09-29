import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import catalog_directory as directory


class DirectoryTests(unittest.TestCase):
    def test_entries_exclude_explicit_non_skills_and_deduplicate(self):
        text = '''<summary><h3>Skills by Example</h3></summary>
- **[one](https://github.com/org/repo/tree/main/skills/one)** - Real skill
More from Example (not skills, but they pair with them):
- **[cli](https://github.com/org/cli)** - CLI
<summary><h3>Community</h3></summary>
- **[one-again](https://github.com/org/repo/tree/main/skills/one)**: Same entry
| [org/bundle](https://github.com/org/bundle) | Skill bundle. `npx skills add org/bundle` |
'''
        rows, excluded, count = directory.extract(text, {'raw_url': 'pin', 'commit': 'abc', 'sha256': 'hash'})
        self.assertEqual(count, 3)
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(rows[0]['occurrences']), 2)
        self.assertEqual(len(excluded), 1)
        self.assertEqual(rows[0]['line'], 2)

    def test_observed_canonical_link_can_have_different_repository(self):
        row = {'id': 'x', 'original_url': 'https://officialskills.sh/org/skills/foo'}
        body = b'<a href="https://github.com/Org/actual-plugin/tree/main/skills/foo">source</a>'
        with tempfile.TemporaryDirectory() as tmp, patch.object(directory, 'fetch', return_value=(body, row['original_url'])):
            resolved = directory.resolve(row, Path(tmp))
        self.assertEqual(resolved['canonical_url'], 'https://github.com/Org/actual-plugin/tree/main/skills/foo')
        self.assertEqual(resolved['resolution_status'], 'upstream_link_observed')

    def test_multiple_observed_targets_remain_unresolved(self):
        row = {'id': 'x', 'original_url': 'https://officialskills.sh/org/skills/foo'}
        body = b'https://github.com/org/skills/tree/main/foo https://github.com/org/skills/tree/main/bar'
        with tempfile.TemporaryDirectory() as tmp, patch.object(directory, 'fetch', return_value=(body, row['original_url'])):
            resolved = directory.resolve(row, Path(tmp))
        self.assertEqual(resolved['resolution_status'], 'ambiguous_or_missing_upstream')
        self.assertEqual(resolved['canonical_url'], row['original_url'])

    def test_exact_leaf_overlap_not_repo_coverage_claim(self):
        rows = [{'canonical_id':'github:org/repo:skills/one', 'upstream': {'scope':'directory','repository':'org/repo'}},
                {'canonical_id':'github:org/repo:skills/two', 'upstream': {'scope':'directory','repository':'org/repo'}}]
        result = directory.compare(rows, {'records':[{'id':'github:org/repo:skills/one/SKILL.md','repository':'org/repo'}]}, {'sources':[]})
        self.assertEqual(result[0]['overlap_status'],'existing_exact_leaf')
        self.assertEqual(result[1]['overlap_status'],'existing_repository_only')


if __name__ == '__main__':
    unittest.main()
