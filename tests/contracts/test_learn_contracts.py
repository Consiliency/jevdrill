import json
from pathlib import Path

import pytest

from jevdrill.contracts import ContractError, parse_contract

ROWS = json.loads((Path(__file__).parent / "fixtures/learn.json").read_text())


@pytest.mark.parametrize("row", ROWS, ids=lambda row: row["id"])
def test_learning_shared_contract(row):
    if row["accepted"]:
        assert parse_contract(row["contract"], row["payload"]).payload() == row["payload"]
    else:
        with pytest.raises(ContractError):
            parse_contract(row["contract"], row["payload"])
