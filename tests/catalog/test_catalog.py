import hashlib

import pytest

from jevdrill.catalog import catalog_digest
from jevdrill.contracts import ContractError


def test_catalog_digest_is_order_independent_and_rejects_duplicate_revisions():
    first = {
        "resource_id": "r",
        "revision": "1",
        "content_hash": hashlib.sha256(b"synthetic").hexdigest(),
        "rights": "allowed",
        "admission": "policy_admitted",
        "source_occurrences": ["synthetic"],
        "aliases": [],
        "domain": "test",
        "specialty": "test",
        "task_family": "test",
        "facets": [],
        "benchmark_protocol": None,
        "benchmark_split": None,
        "benchmark_effort": None,
        "instructions": "synthetic",
        "conflicts": [],
    }
    second = first | {"resource_id": "s"}
    assert catalog_digest([first, second]) == catalog_digest([second, first])
    with pytest.raises(ContractError, match="duplicate resource revision"):
        catalog_digest([first, first])
    for field, value in (
        ("rights", "changed"),
        ("aliases", ["alias"]),
        ("benchmark_split", "holdout"),
    ):
        assert catalog_digest([first | {field: value}]) != catalog_digest([first])
    with pytest.raises(ContractError, match="hash mismatch"):
        catalog_digest([first | {"instructions": "tampered"}])
