import json
import subprocess
from pathlib import Path

import pytest

from jevdrill.contracts import ContractError, canonical_digest, parse_contract

ROWS = [
    row
    for name in ("discovery.json", "discovery-links.json")
    for row in json.loads((Path(__file__).parent / "fixtures" / name).read_text())
]


@pytest.mark.parametrize("row", ROWS, ids=lambda row: row["id"])
def test_discovery_contract_parity(row):
    if row["accepted"]:
        document = parse_contract(row["contract"], row["payload"])
        assert document.digest == canonical_digest(row["payload"])
    else:
        with pytest.raises(ContractError):
            parse_contract(row["contract"], row["payload"])


def test_shared_discovery_node_fixtures(tmp_path):
    (tmp_path / "boundary.json").write_text(json.dumps(ROWS))
    result = subprocess.run(
        ["node", "scripts/contract_consumer.mjs", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert [row["accepted"] for row in json.loads(result.stdout)] == [
        row["accepted"] for row in ROWS
    ]


def test_policy_families_reject_each_other(discovery_inputs):
    policy = discovery_inputs["judgment_policy"]
    with pytest.raises(ContractError):
        parse_contract("JudgmentPolicy", policy)
    invalid = dict(policy, function_revision="JudgeCandidate-v1")
    with pytest.raises(ContractError):
        parse_contract("DiscoveryJudgmentPolicy", invalid)
