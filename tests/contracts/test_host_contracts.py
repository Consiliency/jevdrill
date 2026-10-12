import json
from pathlib import Path

import pytest

from jevdrill.contracts import ContractError, parse_contract

ROWS = json.loads((Path(__file__).parent / "fixtures/host.json").read_text())


@pytest.mark.parametrize("row", ROWS, ids=lambda row: row["id"])
def test_host_shared_contract(row):
    if row["accepted"]:
        document = parse_contract(row["contract"], row["payload"])
        assert document.payload() == row["payload"]
        assert document.digest == row.get("digest", document.digest)
    else:
        with pytest.raises(ContractError):
            parse_contract(row["contract"], row["payload"])
