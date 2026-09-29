import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "coverage_check", ROOT / "scripts/check_contract_coverage.py"
)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.document = json.loads(
            (ROOT / "evidence/CONTRACT/coverage.json").read_text(encoding="utf-8")
        )

    def test_repository_mapping(self):
        self.assertEqual(checker.check(ROOT, self.document), [])

    def test_missing_and_duplicate_requirements(self):
        self.document["requirements"].pop()
        self.document["requirements"].append(copy.deepcopy(self.document["requirements"][0]))
        errors = checker.check(ROOT, self.document)
        self.assertTrue(any("unmapped source" in e for e in errors))
        self.assertTrue(any("duplicate requirement" in e for e in errors))

    def test_wrong_criterion_text(self):
        row = self.document["requirements"][0]
        row["criteria"][0]["required_text"] = "silently invent successful verification"
        self.assertTrue(any("no longer verifies" in e for e in checker.check(ROOT, self.document)))

    def test_stale_source_and_fabricated_completion(self):
        row = self.document["requirements"][0]
        row["source_sha256"] = "0" * 64
        row["status"] = "complete"
        errors = checker.check(ROOT, self.document)
        self.assertTrue(any("stale source" in e for e in errors))
        self.assertTrue(any("completion claim" in e for e in errors))

    def test_deferral_requires_reason_owner_phase(self):
        row = self.document["requirements"][0]
        row.update(status="deferred", owner="", phase="", reason="")
        self.assertGreaterEqual(len(checker.check(ROOT, self.document)), 2)

    def test_unknown_criterion_and_missing_review(self):
        self.document["requirements"][0]["criteria"][0]["id"] = "EC-UNKNOWN-1"
        self.document["review_items"].pop()
        errors = checker.check(ROOT, self.document)
        self.assertTrue(any("unknown criterion" in e for e in errors))
        self.assertTrue(any("review inventory" in e for e in errors))
