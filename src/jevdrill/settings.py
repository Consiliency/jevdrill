"""Resolve validated settings in precedence order without weakening restrictions."""

from collections.abc import Mapping, Sequence
from typing import Any

from .contracts import ContractError, canonical_digest, parse_contract

PRECEDENCE = ("product", "user", "project", "directory", "personal_project", "request")


def resolve_settings(layers: Sequence[tuple[str, Mapping[str, Any]]]) -> dict[str, Any]:
    sources = [source for source, _ in layers]
    if len(set(sources)) != len(sources) or any(source not in PRECEDENCE for source in sources):
        raise ContractError("unknown or duplicate settings source")
    validated = [
        parse_contract("SettingsLayer", {"source": source, "values": dict(values)}).payload()
        for source, values in layers
    ]
    result: dict[str, Any] = {
        "schema_version": "1",
        "settings_revision": "",
        "routing_cost_basis": "raw",
        "retain_raw_tasks": False,
        "retain_raw_outputs": False,
        "local_analysis_enabled": False,
        "experiment_enabled": False,
        "model_analysis_enabled": False,
        "default_plan_id": None,
        "routing_deadline_ms": 5000,
        "excluded_paths": [],
        "setting_sources": {},
        "max_description_utf8_bytes": 2048,
    }
    restrictive = {
        "retain_raw_tasks",
        "retain_raw_outputs",
        "local_analysis_enabled",
        "experiment_enabled",
        "model_analysis_enabled",
    }
    denied: set[str] = set()
    for layer in sorted(validated, key=lambda row: PRECEDENCE.index(row["source"])):
        for key, value in layer["values"].items():
            if value is None and key != "default_plan_id":
                continue
            if key in denied:
                continue
            if key in restrictive and value is False:
                denied.add(key)
            if key == "excluded_paths":
                value = sorted(set(result[key]) | set(value))
            if key == "routing_deadline_ms":
                value = min(result[key], value)
            if key == "max_description_utf8_bytes":
                value = min(result[key], value)
            result[key] = value
            result["setting_sources"][key] = layer["source"]
    result["settings_revision"] = canonical_digest(
        sorted(validated, key=lambda row: PRECEDENCE.index(row["source"]))
    )
    return dict(parse_contract("Settings", result).payload())


def effective_permissions(declared: Sequence[str], runtime: Sequence[str]) -> list[str]:
    if len(set(declared)) != len(declared) or len(set(runtime)) != len(runtime):
        raise ContractError("duplicate capability")
    return sorted(set(declared) & set(runtime))
