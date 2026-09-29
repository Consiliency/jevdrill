import copy
import json
import subprocess
from pathlib import Path

import pytest

from jevdrill.contracts import ContractError, canonical_digest, parse_contract, valid_transition

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = json.loads((ROOT / "tests/contracts/fixtures/boundary.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda row: row["id"])
def test_public_parser(fixture):
    if fixture["accepted"]:
        result = parse_contract(fixture["contract"], fixture["payload"])
        assert result.digest == fixture["digest"]
        assert result.model().model_dump(mode="json") == fixture["payload"]
    else:
        with pytest.raises(ContractError):
            parse_contract(fixture["contract"], fixture["payload"])


def test_non_python_consumer():
    result = subprocess.run(
        ["node", "scripts/contract_consumer.mjs"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    observations = json.loads(result.stdout)
    assert len(observations) == len(FIXTURES)
    for fixture, observed in zip(FIXTURES, observations, strict=True):
        assert observed["accepted"] == fixture["accepted"]
        if fixture["accepted"]:
            assert observed["digest"] == fixture["digest"]


def test_snapshot_cannot_be_changed_through_generated_view():
    fixture = next(f for f in FIXTURES if f["contract"] == "ExecutionPlan" and f["accepted"])
    original = copy.deepcopy(fixture["payload"])
    document = parse_contract("ExecutionPlan", original)
    digest = document.digest
    original["model_id"] = "changed"
    document.payload()["model_id"] = "also changed"
    document.model().model_id = "mutated view"
    assert document.digest == digest


@pytest.mark.parametrize("value", [float("nan"), float("inf"), 2**54, float(2**54), "\ud800"])
def test_nonportable_values(value):
    with pytest.raises(ContractError):
        canonical_digest({"bad": value})


def test_terminal_events_and_experiment_authority_transitions():
    assert valid_transition("event", "queued", "started")
    assert not valid_transition("event", "completed", "started")
    assert not valid_transition("experiment", "proposed", "running")
    assert valid_transition("experiment", "running", "incomplete")
    with pytest.raises(ContractError):
        valid_transition("other", "queued", "started")
