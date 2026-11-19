"""Strict, freshness-preserving host inventory snapshots."""

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from time import monotonic
from typing import Any

from .contracts import ContractError, parse_contract


def fresh(verified_at: str, expires_at: str, now: datetime | None = None) -> bool:
    current = now or datetime.now(UTC)
    return datetime.fromisoformat(verified_at) <= current < datetime.fromisoformat(expires_at)


def _effective_permissions(declared: Sequence[str], runtime: Sequence[str]) -> list[str]:
    if len(set(declared)) != len(declared) or len(set(runtime)) != len(runtime):
        raise ContractError("duplicate capability")
    return sorted(set(declared) & set(runtime))


def validate_snapshot(snapshot: Mapping[str, Any], target: str, deadline: float) -> dict[str, Any]:
    value: dict[str, Any] = parse_contract("InventorySnapshot", snapshot).payload()
    if deadline <= monotonic() or value["target"] != target:
        raise ContractError("invalid inventory target or deadline")
    if not fresh(value["verified_at"], value["expires_at"]):
        raise ContractError("stale inventory")
    identities = [row["candidate_id"] for row in value["candidates"]]
    if len(identities) != len(set(identities)):
        raise ContractError("duplicate inventory candidate")
    normalized = []
    for row in value["candidates"]:
        item = dict(row)
        item["effective_capabilities"] = _effective_permissions(
            row["declared_capabilities"], row["runtime_capabilities"]
        )
        item["available"] = fresh(row["verified_at"], row["expires_at"])
        effort = row["native_effort"]
        item["available"] &= effort["kind"] != "unsupported" and (
            effort["kind"] != "explicit" or effort["native_value"] in row["supported_efforts"]
        )
        item["available"] &= set(row["required_capabilities"]) <= set(
            item["effective_capabilities"]
        )
        rates = item["rates"]
        if rates is not None and not fresh(rates["verified_at"], rates["expires_at"]):
            item["rates"] = None
        normalized.append(item)
    value["candidates"] = normalized
    return value


class SuppliedInventory:
    def __init__(self, snapshot: Mapping[str, Any]) -> None:
        self.document = parse_contract("InventorySnapshot", snapshot)

    def snapshot(self, target: str, deadline: float) -> Mapping[str, Any]:
        validate_snapshot(self.document.payload(), target, deadline)
        return dict(self.document.payload())


def capability_mismatch(declared: Sequence[str], runtime: Sequence[str]) -> dict[str, list[str]]:
    return {
        "declared": list(declared),
        "runtime": list(runtime),
        "effective": _effective_permissions(declared, runtime),
    }
