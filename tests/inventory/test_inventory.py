import copy
import json
from pathlib import Path
from time import monotonic

import pytest

from jevdrill.contracts import ContractError
from jevdrill.inventory import validate_snapshot


def snapshot():
    rows = json.loads(
        (Path(__file__).parents[1] / "contracts/fixtures/route-inputs.json").read_text()
    )
    return copy.deepcopy(rows[0]["payload"])


def test_snapshot_intersects_declared_and_runtime_capabilities():
    value = snapshot()
    value["candidates"][0]["declared_capabilities"] = ["route", "report"]
    value["candidates"][0]["runtime_capabilities"] = ["report", "inspect"]
    result = validate_snapshot(value, "fixture", monotonic() + 1)
    assert result["candidates"][0]["effective_capabilities"] == ["report"]
    assert not result["candidates"][0]["available"]


def test_stale_price_does_not_fabricate_cost_or_expire_capability():
    value = snapshot()
    value["candidates"][0]["rates"]["expires_at"] = "2000-01-01T00:00:00Z"
    result = validate_snapshot(value, "fixture", monotonic() + 1)
    assert result["candidates"][0]["rates"] is None
    assert result["candidates"][0]["available"]


def test_expired_candidate_and_unsupported_native_effort():
    for change in (
        {"expires_at": "2000-01-01T00:00:00Z"},
        {"native_effort": {"kind": "explicit", "native_value": "unsupported"}},
    ):
        value = snapshot()
        value["candidates"][0].update(change)
        assert not validate_snapshot(value, "fixture", monotonic() + 1)["candidates"][0][
            "available"
        ]


def test_snapshot_rechecks_after_host_setup():
    value = snapshot()
    value["candidates"][0]["runtime_capabilities"] = []
    assert not validate_snapshot(value, "fixture", monotonic() + 1)["candidates"][0]["available"]
    value["candidates"][0]["runtime_capabilities"] = ["text"]
    assert validate_snapshot(value, "fixture", monotonic() + 1)["candidates"][0]["available"]
    value["expires_at"] = "2000-01-01T00:00:00Z"
    with pytest.raises(ContractError, match="stale"):
        validate_snapshot(value, "fixture", monotonic() + 1)
