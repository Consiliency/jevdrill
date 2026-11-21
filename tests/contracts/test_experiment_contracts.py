import json
import subprocess
from pathlib import Path

import pytest

from jevdrill.contracts import ContractError, parse_contract

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = json.loads((ROOT / "tests/contracts/fixtures/experiment.json").read_text())


@pytest.mark.parametrize("row", FIXTURES, ids=lambda row: row["id"])
def test_experiment_boundary(row):
    if row["accepted"]:
        assert parse_contract(row["contract"], row["payload"]).payload() == row["payload"]
    else:
        with pytest.raises(ContractError):
            parse_contract(row["contract"], row["payload"])


def test_experiment_node_parity(tmp_path):
    (tmp_path / "boundary.json").write_text(json.dumps(FIXTURES))
    result = subprocess.run(
        ["node", "scripts/contract_consumer.mjs", str(tmp_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert [(r["id"], r["accepted"]) for r in json.loads(result.stdout)] == [
        (r["id"], r["accepted"]) for r in FIXTURES
    ]
