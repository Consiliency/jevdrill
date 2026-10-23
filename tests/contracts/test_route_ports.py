import inspect
import json
import subprocess
from pathlib import Path

import pytest

from jevdrill.contracts import (
    ContractError,
    InventoryPort,
    JudgmentPort,
    StoragePort,
    TokenCounter,
    parse_contract,
)

FIXTURES = Path(__file__).parent / "fixtures" / "route-inputs.json"


@pytest.mark.parametrize(
    "row", json.loads(FIXTURES.read_text(encoding="utf-8")), ids=lambda row: row["id"]
)
def test_route_input_contracts(row):
    if row["accepted"]:
        document = parse_contract(row["contract"], row["payload"])
        assert document.digest == row["digest"]
    else:
        with pytest.raises(ContractError):
            parse_contract(row["contract"], row["payload"])


def test_route_input_node_parity(tmp_path):
    (tmp_path / "boundary.json").write_bytes(FIXTURES.read_bytes())
    subprocess.run(
        ["node", "scripts/contract_consumer.mjs", str(tmp_path)],
        cwd=Path(__file__).resolve().parents[2],
        check=True,
        capture_output=True,
    )


def test_route_input_snapshot_is_immutable():
    row = next(row for row in json.loads(FIXTURES.read_text()) if row["id"] == "inventory-valid")
    document = parse_contract(row["contract"], row["payload"])
    row["payload"]["candidates"][0]["model_id"] = "mutated"
    document.payload()["candidates"].clear()
    assert document.digest == row["digest"]


def test_route_port_signatures_are_frozen():
    assert list(inspect.signature(StoragePort.commit_decision).parameters) == [
        "self",
        "scope",
        "key",
        "digest",
        "bundle",
    ]
    assert list(inspect.signature(StoragePort.ingest_report).parameters) == [
        "self",
        "scope",
        "key",
        "digest",
        "event",
    ]
    assert list(inspect.signature(StoragePort.load_replay).parameters) == [
        "self",
        "scope",
        "decision_id",
    ]
    assert list(inspect.signature(StoragePort.delete_task).parameters) == [
        "self",
        "scope",
        "task_id",
    ]
    assert list(inspect.signature(InventoryPort.snapshot).parameters) == [
        "self",
        "target",
        "deadline",
    ]
    assert list(inspect.signature(TokenCounter.count).parameters) == [
        "self",
        "text",
        "model_revision",
    ]
    assert list(inspect.signature(JudgmentPort.judge).parameters) == [
        "self",
        "task",
        "candidates",
        "deadline",
    ]
