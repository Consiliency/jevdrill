"""Strict immutable JSON boundary over BAML-generated Pydantic contracts."""

import hashlib
import json
import math
import struct
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from typing import Any, Protocol, cast

from jsonschema import Draft202012Validator, FormatChecker
from pydantic import BaseModel, TypeAdapter

import baml_sdk as _generated


class ContractError(ValueError):
    """An external value violates a public contract."""


class StoragePort(Protocol):
    """Durable, scope-isolated decision and event persistence."""

    def commit_decision(
        self, scope: Mapping[str, str], key: str, digest: str, bundle: Mapping[str, Any]
    ) -> Mapping[str, Any]: ...

    def ingest_report(
        self, scope: Mapping[str, str], key: str, digest: str, event: Mapping[str, Any]
    ) -> Mapping[str, Any]: ...

    def load_replay(
        self, scope: Mapping[str, str], decision_id: str
    ) -> Mapping[str, Any] | None: ...

    def delete_task(self, scope: Mapping[str, str], task_id: str) -> Mapping[str, Any]: ...

    def load_notices(self, scope: Mapping[str, str]) -> list[dict[str, Any]]: ...


class InventoryPort(Protocol):
    """Provides a validated current inventory snapshot."""

    def snapshot(self, target: str, deadline: float) -> Mapping[str, Any]: ...


class TokenCounter(Protocol):
    """Counts a complete payload for one immutable model revision."""

    def count(self, text: str, model_revision: str) -> int: ...


class JudgmentPort(Protocol):
    """Obtains a bounded judgment for offered candidates only."""

    def judge(
        self, task: str, candidates: tuple[Mapping[str, Any], ...], deadline: float
    ) -> Mapping[str, Any]: ...


class DiscoveryJudgmentPort(Protocol):
    def observe_option(
        self, task: str, offered: str, question_digest: str, option_id: str, deadline: float
    ) -> Mapping[str, Any]: ...


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
        operation = (
            "discover"
            if "work_objective_id" in value
            else "report"
            if "event" in value
            else "route"
        )
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
    if (
        "share_user_wide" in value
        and value["share_user_wide"]
        and not value["local_analysis_enabled"]
    ):
        raise ContractError("learning consent conflict")
    if "minimum_batch" in value and (value["action"] == "record") != (value["context"] is not None):
        raise ContractError("learning context action conflict")
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
    if (
        value.get("schema_version") == "2"
        and "route_inputs" in value
        and value["route_inputs"].get("catalog_query") is not None
    ):
        raise ContractError("linked catalog query forbidden")
    if "guidance_refs" in value:
        identities = [(row["resource_id"], row["revision"]) for row in value["guidance_refs"]]
        if len(identities) != len(set(identities)) or len(identities) > 2:
            raise ContractError("discovery guidance consistency")
    if isinstance(value.get("details"), dict) and "discovery_id" in value["details"]:
        details = value["details"]
        if (value["status"] == "selected_guidance") != bool(details["guidance_refs"]):
            raise ContractError("discovery result consistency")
        if value["status"] == "no_optional_guidance" and details["uncertainty"]:
            raise ContractError("incomplete empty discovery")
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


def jev_usage_measurements(event: object) -> list[dict[str, Any]]:
    """Project one internal invocation without exposing provider payloads."""
    if not isinstance(event, _generated.JevUsageObservation):
        return []
    measurements = []
    for metric in ("duration_ms", "input_tokens", "output_tokens"):
        direct = getattr(event, metric)
        values = [direct]
        invalid = False
        if metric != "duration_ms":
            values.append(getattr(event, "call_" + metric))
            invalid = getattr(event, metric.removesuffix("_tokens") + "_invalid")
        invalid = invalid or any(
            value is not None and (type(value) is not int or value < 0) for value in values
        )
        known = {value for value in values if type(value) is int and value >= 0}
        value: dict[str, Any]
        if invalid or len(known) > 1:
            value = {"kind": "unknown", "reason": "incomplete"}
        elif known:
            value = {
                "kind": "known",
                "value": known.pop(),
                "unit": "ms" if metric == "duration_ms" else "tokens",
            }
        else:
            value = {"kind": "unknown", "reason": "not_reported"}
        measurements.append(
            {
                "metric_id": "routing_" + metric,
                "metric_version": "1",
                "measurement_value": value,
                "source": "provider",
                "method": "jev-call-v1",
                "scope": "call",
                "counting_semantics": "disjoint",
                "parent_metric_id": None,
            }
        )
    return measurements
