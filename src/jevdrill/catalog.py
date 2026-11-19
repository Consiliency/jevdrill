"""Exact resource identity, provenance and bounded metadata-first retrieval."""

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any

from .contracts import ContractError, canonical_digest, parse_contract


def resource_revision(value: Mapping[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = parse_contract("CatalogResource", value).payload()
    if hashlib.sha256(row["instructions"].encode()).hexdigest() != row["content_hash"]:
        raise ContractError("resource hash mismatch")
    if not row["rights"] or not row["source_occurrences"]:
        raise ContractError("missing resource provenance or rights")
    return row


def catalog_digest(resources: Sequence[Mapping[str, Any]]) -> str:
    revisions = [resource_revision(value) for value in resources]
    identities = [(row["resource_id"], row["revision"]) for row in revisions]
    if len(identities) != len(set(identities)):
        raise ContractError("duplicate resource revision")
    return canonical_digest(
        sorted(revisions, key=lambda row: (row["resource_id"], row["revision"]))
    )


def narrow(
    resources: Sequence[Mapping[str, Any]],
    domain: str,
    specialty: str,
    task_family: str,
    facets: Sequence[str],
    limit: int = 8,
) -> list[dict[str, Any]]:
    if limit < 1:
        raise ContractError("invalid catalog frontier")
    rows = [resource_revision(row) for row in resources]
    ranked = sorted(
        rows,
        key=lambda row: (
            -(
                int(row["domain"] == domain)
                + int(row["specialty"] == specialty)
                + int(row["task_family"] == task_family)
                + len(set(row["facets"]) & set(facets))
            ),
            row["resource_id"],
            row["revision"],
        ),
    )
    return ranked[:limit]


def retrieve(resources: Sequence[Mapping[str, Any]], guidance: Mapping[str, Any]) -> str:
    matches = [
        row
        for row in resources
        if (row["resource_id"], row["revision"], row["content_hash"])
        == (guidance["resource_id"], guidance["revision"], guidance["content_hash"])
    ]
    if len(matches) != 1:
        raise ContractError("missing exact guidance revision")
    row = resource_revision(matches[0])
    if row["admission"] not in {"policy_admitted", "explicitly_enabled"}:
        raise ContractError("unadmitted guidance")
    if row["admission"] != guidance["admission"]:
        raise ContractError("guidance admission mismatch")
    return str(row["instructions"])
