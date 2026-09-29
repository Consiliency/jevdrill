import copy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "verification", ROOT / "scripts/verify_contract_phase.py"
)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def manifests():
    return [
        {
            "schema_version": 1,
            "execution_kind": "native",
            "os": os_name,
            "python_minor": minor,
            "input_digest": "fixture",
            "bridge_version": "0.20.1",
            "compiler_version": "baml-cli 0.20.1",
            "runner_identity": "synthetic-unit-test",
            "architecture": "synthetic-unit-test",
            "tests": {"total": 1, "skipped": 0},
            "checks": [
                {"name": name, "command": ["unit-test-fixture"], "exit_code": 0}
                for name in runner.CHECKS | ({"catalog"} if os_name == "Linux" else set())
            ],
        }
        for os_name, minor in runner.MATRIX
    ]


def test_reducer_requires_all_platforms():
    assert runner.reduce_manifests(manifests(), "fixture") == []
    assert runner.reduce_manifests(manifests()[:1], "fixture")


@pytest.mark.parametrize(
    "key,value",
    [
        ("input_digest", "stale"),
        ("compiler_version", "0"),
        ("bridge_version", "0"),
        ("python_minor", "3.12"),
        ("execution_kind", "proxy"),
        ("runner_identity", ""),
        ("checks", []),
        ("tests", {"total": 1, "skipped": 1}),
    ],
)
def test_reducer_rejects_invalid_evidence(key, value):
    rows = copy.deepcopy(manifests())
    rows[0][key] = value
    assert runner.reduce_manifests(rows, "fixture")


def test_reducer_aggregates_independent_failures():
    rows = manifests()
    rows[0]["checks"][0]["exit_code"] = 1
    rows[1]["input_digest"] = "stale"
    errors = runner.reduce_manifests(rows, "fixture")
    assert "failed check" in errors
    assert "stale input digest" in errors
