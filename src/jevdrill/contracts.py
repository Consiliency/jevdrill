"""Strict immutable JSON boundary over BAML-generated Pydantic contracts."""

import hashlib
import json
import math
import struct
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from typing import Any, cast

from jsonschema import Draft202012Validator, FormatChecker
from pydantic import BaseModel, TypeAdapter

import baml_sdk as _generated


class ContractError(ValueError):
    """An external value violates a public contract."""


@lru_cache
def schema_bundle() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads(
            files(_generated).joinpath("_boundary_schemas.json").read_text(encoding="utf-8")
        ),
    )


def _walk(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ContractError("nonfinite numeric value")
    if (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value == math.trunc(value)
        and abs(value) > 2**53 - 1
    ):
        raise ContractError("integer exceeds portable exact range")
    if isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as error:
            raise ContractError("invalid Unicode scalar") from error
    if isinstance(value, list):
        for item in value:
            _walk(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ContractError("object keys must be strings")
            _walk(key)
            _walk(item)
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise ContractError("value is not JSON")


def _semantics(value: Any) -> None:
    if isinstance(value, list):
        for item in value:
            _semantics(item)
    if not isinstance(value, dict):
        return
    if "envelope" in value:
        operation = "report" if "event" in value else "route"
        if value["envelope"]["operation"] != operation:
            raise ContractError("request_operation")
    if value.get("code") == "capability_mismatch" and "effective" in value:
        allowed = set(value["declared"]) & set(value["runtime"])
        if not set(value["effective"]) <= allowed:
            raise ContractError("effective_capabilities")
    if "optional_guidance" in value:
        guidance = value["optional_guidance"]
        identities = [
            (g["resource_id"], g["revision"]) for g in guidance + value["required_guidance"]
        ]
        roles = [g["role"] for g in guidance]
        if (
            len(identities) != len(set(identities))
            or len(roles) != len(set(roles))
            or (value["guidance_action"] == "none") != (not guidance)
        ):
            raise ContractError("guidance_consistency")
    if value.get("counting_semantics") == "subset" and value.get("parent_metric_id") is None:
        raise ContractError("measurement_subset")
    if "experiment_state" in value:
        if value["experiment_state"] in {
            "accepted",
            "queued",
            "running",
            "completed",
            "incomplete",
        }:
            if not value["authorization_revision"]:
                raise ContractError("experiment_authority")
            if value["execution_path"] == "harness_assisted" and not value["host_accepted"]:
                raise ContractError("experiment_authority")
        plans = value["candidate_plans"]
        if len(plans) > value["limits"]["max_candidates"]:
            raise ContractError("experiment_authority")
        ids = [p["execution_plan_id"] for p in plans]
        probabilities = value["assignment_probabilities"]
        if len(ids) != len(set(ids)):
            raise ContractError("experiment_authority")
        if probabilities and (
            set(probabilities) != set(ids)
            or not math.isclose(sum(probabilities.values()), 1.0, abs_tol=1e-12)
        ):
            raise ContractError("experiment_authority")
    if value.get("supersedes_event_id") is not None and value.get(
        "supersedes_event_id"
    ) == value.get("event_id"):
        raise ContractError("event_correction")
    for item in value.values():
        _semantics(item)


def _tag(value: Any) -> Any:
    if value is None:
        return ["null"]
    if isinstance(value, bool):
        return ["boolean", value]
    if isinstance(value, (int, float)):
        number = 0.0 if value == 0 else float(value)
        return ["number", struct.pack(">d", number).hex()]
    if isinstance(value, str):
        return ["string", value]
    if isinstance(value, list):
        return ["array", [_tag(item) for item in value]]
    return ["object", [[key, _tag(value[key])] for key in sorted(value)]]


def canonical_digest(value: Any) -> str:
    """Version-1 tagged JSON digest; numbers use IEEE-754 big-endian hex."""
    _walk(value)
    encoded = json.dumps(_tag(value), ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class ValidatedDocument:
    contract_name: str
    payload_json: str

    def payload(self) -> Any:
        return json.loads(self.payload_json)

    def model(self) -> BaseModel:
        # Fresh views cannot mutate the stored immutable JSON snapshot.
        value: BaseModel = TypeAdapter(getattr(_generated, self.contract_name)).validate_json(
            self.payload_json
        )
        return value

    @property
    def digest(self) -> str:
        return canonical_digest(self.payload())


def parse_contract(name: str, payload: Any) -> ValidatedDocument:
    bundle = schema_bundle()
    if name not in bundle["boundary.json"]["contracts"]:
        raise ContractError("unknown contract")
    _walk(payload)
    validator = Draft202012Validator(bundle[name + ".json"], format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(payload), key=lambda error: str(error.path))
    if errors:
        # Never echo task content, credential-like data, or invalid values in errors.
        raise ContractError(f"{name}: schema violation ({errors[0].validator})")
    _semantics(payload)
    serialized = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    return ValidatedDocument(name, serialized)


def valid_transition(kind: str, previous: str, following: str) -> bool:
    key = {"event": "event_transitions", "experiment": "experiment_transitions"}.get(kind)
    if key is None:
        raise ContractError("unknown transition family")
    return following in schema_bundle()["boundary.json"][key].get(previous, [])
