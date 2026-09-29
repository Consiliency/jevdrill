import copy
import json
from decimal import Decimal
from pathlib import Path

import pytest

from jevdrill.contracts import ContractError, parse_contract
from jevdrill.evaluation import (
    cost_per_accepted,
    elapsed_union_ms,
    require_comparable,
    token_total,
    validate_splits,
)


def test_cost_includes_failed_attempts_and_unknowns():
    assert cost_per_accepted([Decimal(2), Decimal(3)], [False, True]) == Decimal(5)
    assert cost_per_accepted([Decimal(2)], [False]) is None
    assert cost_per_accepted([None], [True]) is None
    assert cost_per_accepted([Decimal(0)], [None]) is None


def test_parallel_elapsed_not_sum():
    assert elapsed_union_ms([(0, 100), (50, 150), (200, 250)]) == 200
    with pytest.raises(ValueError):
        elapsed_union_ms([(1, 0)])


def test_token_subsets_not_double_counted():
    assert token_total(100, 50, 75, 25) == 150
    assert token_total(None, 50) is None
    with pytest.raises(ValueError):
        token_total(100, 50, 101)


def test_metric_definition_and_unknown_rejection():
    fixtures = json.loads(
        (Path(__file__).parents[1] / "contracts/fixtures/boundary.json").read_text(encoding="utf-8")
    )
    payload = copy.deepcopy(next(x["payload"] for x in fixtures if x["id"] == "Measurement-0"))
    a = parse_contract("Measurement", payload)
    require_comparable(a, a)
    payload["metric_version"] = "changed"
    with pytest.raises(ContractError):
        require_comparable(a, parse_contract("Measurement", payload))
    payload["metric_version"] = a.payload()["metric_version"]
    payload["measurement_value"] = {"kind": "unknown", "reason": "not_reported"}
    with pytest.raises(ContractError):
        require_comparable(a, parse_contract("Measurement", payload))


def test_dataset_leakage_and_exposure():
    validate_splits(
        {"development": ["a"], "release_holdout": ["b"]}, {"a": "group-a", "b": "group-b"}, set()
    )
    with pytest.raises(ValueError):
        validate_splits(
            {"development": ["a"], "release_holdout": ["b"]}, {"a": "same", "b": "same"}, set()
        )
    with pytest.raises(ValueError):
        validate_splits({"release_holdout": ["b"]}, {"b": "group-b"}, {"b"})
