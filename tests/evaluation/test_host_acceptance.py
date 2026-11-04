import json
import subprocess
import sys
from pathlib import Path

import pytest

from jevdrill.evaluation import evaluate_host_artifact, validate_splits

PROTOCOL = Path(__file__).parents[2] / "research/evaluation/host/protocol.json"
CASES = json.loads(PROTOCOL.read_text())["cases"]


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_independent_controlled_artifact_checks(case):
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-c", case["program"]],
        capture_output=True,
        text=True,
        timeout=5,
        check=True,
    )
    artifact = json.loads(result.stdout)
    assert all(evaluate_host_artifact(case["family"], case["expected"], artifact).values())
    for key in case["expected"]:
        damaged = dict(artifact)
        damaged[key] = None
        assert not all(evaluate_host_artifact(case["family"], case["expected"], damaged).values())


def test_review_false_positive_and_severity_are_not_preferences():
    case = next(case for case in CASES if case["family"] == "review")
    artifact = {"findings": {**case["expected"]["findings"], "invented": {}}}
    checks = evaluate_host_artifact("review", case["expected"], artifact)
    assert checks["defect_recall"] and not checks["false_positives"]
    artifact = {
        "findings": {
            key: {"severity": "low", "action": "ignore"} for key in case["expected"]["findings"]
        }
    }
    assert not evaluate_host_artifact("review", case["expected"], artifact)["severity_action"]


def test_boolean_is_not_accepted_as_a_numeric_result():
    checks = evaluate_host_artifact("implementation", {"results": [0]}, {"results": [False]})
    assert checks["regression_results"] is False


def test_frozen_groups_are_disjoint_and_holdouts_unopened():
    protocol = json.loads(PROTOCOL.read_text())
    assignments = {
        split: [case["id"] for case in CASES if case["split"] == split]
        for split in ("development", "validation")
    }
    groups = {case["id"]: case["ancestry"] for case in CASES}
    validate_splits(assignments, groups, set(groups))
    assert protocol["holdouts_opened"] is False
    assert protocol["promotion_eligible"] is False
    assert protocol["performance_claims"] == "insufficient_evidence"
    groups[assignments["validation"][0]] = groups[assignments["development"][0]]
    with pytest.raises(ValueError, match="related-task leakage"):
        validate_splits(assignments, groups, set(groups))
