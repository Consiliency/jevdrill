"""Exact ordered guidance admission, role and context checks."""

from collections.abc import Mapping, Sequence
from typing import Any

from .contracts import ContractError


def select_guidance(
    required: Sequence[Mapping[str, Any]], optional: Sequence[Mapping[str, Any]], limit: int
) -> dict[str, list[dict[str, Any]]]:
    if limit < 0 or len(optional) > 2:
        raise ContractError("invalid guidance limit")
    rows = [dict(row) for row in required] + [dict(row) for row in optional]
    identities = [(row["resource_id"], row["revision"]) for row in rows]
    if len(set(identities)) != len(identities):
        raise ContractError("duplicate guidance revision")
    roles = [row["role"] for row in optional]
    if len(set(roles)) != len(roles):
        raise ContractError("conflicting guidance roles")
    if any(row["admission"] not in {"policy_admitted", "explicitly_enabled"} for row in rows):
        raise ContractError("unadmitted guidance")
    if any(type(row["token_count"]) is not int or row["token_count"] < 0 for row in rows):
        raise ContractError("unknown guidance token count")
    if sum(row["token_count"] for row in rows) > limit:
        raise ContractError("guidance exceeds context limit")
    return {
        "required": [dict(row) for row in required],
        "optional": [dict(row) for row in optional],
    }
