"""BAML judgments bound to offered candidates, explicit budgets and one deadline."""

import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from decimal import Decimal
from time import monotonic
from typing import Any
from uuid import uuid4

from baml_bridge.errors import BamlError

from baml_sdk import (
    JevUsageObservation,
    ObserveDiscoveryOption,
    candidate_request_shape,
    development_discovery_request_shape,
    development_task_request_shape,
    discovery_request_shape,
)
from baml_sdk import ObserveCandidate as JudgeCandidate

from ..contracts import ContractError, canonical_digest, jev_usage_measurements, parse_contract

JUDGMENT_FUNCTION_REVISION = "JudgeCandidate-v2"
JUDGMENT_PROJECTION_VERSION = "selected-execution-profile-v2"
JUDGMENT_CANDIDATE_FIELDS = frozenset(
    {
        "candidate_id",
        "model_id",
        "resolved_model_revision",
        "provider",
        "access_route",
        "local",
        "native_effort",
        "declared_capabilities",
        "runtime_capabilities",
        "required_capabilities",
        "effective_capabilities",
        "available",
        "context_token_limit",
        "output_token_limit",
        "execution_token_limits",
        "quality_sufficient",
        "satisfied_requirements",
        "completion_time_ms",
        "completion_time_limit_ms",
        "evidence_strength",
        "evidence_refs",
        "required_guidance",
        "optional_guidance",
        "guidance_instructions",
        "verified_at",
        "expires_at",
    }
)


def judgment_template_binding() -> dict[str, Any]:
    return {
        "function_revision": JUDGMENT_FUNCTION_REVISION,
        "projection_version": JUDGMENT_PROJECTION_VERSION,
        "candidate_fields": sorted(JUDGMENT_CANDIDATE_FIELDS),
        "request_template_digest": canonical_digest(
            json.loads(candidate_request_shape("<task>", "<candidate>"))
        ),
    }


def development_judgment_template_binding() -> dict[str, Any]:
    return {
        "judgment_template": judgment_template_binding(),
        "task_request_template_digest": canonical_digest(
            json.loads(development_task_request_shape("<task>", "<candidate>", "jev-1.13.0"))
        ),
        "discovery_request_template_digest": canonical_digest(
            json.loads(development_discovery_request_shape("<task>", "<option>", "jev-1.13.0"))
        ),
    }


class JevAdapter:
    def __init__(
        self,
        policy: Mapping[str, Any] | None = None,
        on_event: Callable[[object], None] | None = None,
    ) -> None:
        self.policy = None if policy is None else parse_contract("JudgmentPolicy", policy).payload()
        self.on_event = on_event

    def bounded_candidates(
        self, task: str, candidates: tuple[Mapping[str, Any], ...]
    ) -> tuple[Mapping[str, Any], ...]:
        if self.policy is None:
            return ()
        remaining = self.policy["max_input_tokens"]
        selected = []
        for row in candidates[: min(self.policy["max_calls"], self.policy["max_candidates"])]:
            wire = candidate_request_shape(task, json.dumps(dict(row), sort_keys=True))
            tokens = len(wire.encode())
            if tokens <= remaining:
                selected.append(row)
                remaining -= tokens
        return tuple(selected)

    def judge(
        self, task: str, candidates: tuple[Mapping[str, Any], ...], deadline: float
    ) -> Mapping[str, Any]:
        if deadline <= monotonic():
            raise ContractError("judgment deadline expired")
        policy = self.policy
        if policy is None or not policy["enabled"] or not policy["cloud_allowed"]:
            raise ContractError("judgment not authorized")
        if policy["function_revision"] != JUDGMENT_FUNCTION_REVISION:
            raise ContractError("legacy judgment policy cannot dispatch current template")
        if (
            policy["model_revision"] != "jev-latest"
            or policy["token_counter_revision"] != "utf8-bytes-upper-bound-v1"
        ):
            raise ContractError("unsupported judgment model or token counter revision")
        if len(candidates) > min(policy["max_calls"], policy["max_candidates"]):
            raise ContractError("judgment call budget exceeded")
        offered = [row["candidate_id"] for row in candidates]
        if len(set(offered)) != len(offered):
            raise ContractError("duplicate judgment candidate")
        wires = [
            candidate_request_shape(task, json.dumps(dict(row), sort_keys=True))
            for row in candidates
        ]
        token_bound = sum(len(wire.encode()) for wire in wires)
        if token_bound > policy["max_input_tokens"]:
            raise ContractError("judgment context budget exceeded")
        rates, ceiling = policy["rates"], policy["spending_ceiling"]
        if ceiling is not None:
            if (
                rates is None
                or rates["input_rate"] is None
                or rates["output_rate"] is None
                or rates["currency"] != ceiling["currency"]
            ):
                raise ContractError("unknown judgment cost")
            if Decimal(rates["output_rate"]) > 0:
                raise ContractError("provider output spend bound unavailable")
            estimate = Decimal(token_bound) * Decimal(rates["input_rate"]) + Decimal(
                policy["max_output_tokens"]
            ) * Decimal(rates["output_rate"]) * len(candidates)
            if estimate > Decimal(ceiling["amount"]):
                raise ContractError("judgment spend budget exceeded")
        results: dict[str, bool] = {}
        measurements: dict[str, list[dict[str, Any]]] = {}

        def observer(invocation_id: str) -> Callable[[object], None]:
            previous: JevUsageObservation | None = None

            def observe(event: object) -> None:
                nonlocal previous
                if isinstance(event, JevUsageObservation):
                    event = event.model_copy(update={"invocation_id": invocation_id})
                    if previous is not None:
                        for metric in ("input_tokens", "output_tokens"):
                            flag = metric.removesuffix("_tokens") + "_invalid"
                            counts = [
                                getattr(item, field)
                                for item in (previous, event)
                                for field in (metric, "call_" + metric)
                            ]
                            known = {count for count in counts if type(count) is int and count >= 0}
                            invalid = (
                                getattr(previous, flag) or getattr(event, flag) or len(known) > 1
                            )
                            invalid = invalid or any(
                                count is not None and (type(count) is not int or count < 0)
                                for count in counts
                            )
                            setattr(event, metric, next(iter(known)) if len(known) == 1 else None)
                            setattr(event, "call_" + metric, None)
                            setattr(event, flag, invalid)
                    previous = event
                    measurements[invocation_id] = jev_usage_measurements(event)
                if self.on_event is not None:
                    self.on_event(event)

            return observe

        for row in candidates:
            observe = observer(str(uuid4()))
            remaining = int((deadline - monotonic()) * 1000)
            if remaining <= 0:
                raise ContractError("judgment deadline expired")
            try:
                result = JudgeCandidate(
                    task, json.dumps(dict(row), sort_keys=True), remaining, on_event=observe
                )
            except BamlError as error:
                raise ContractError("provider judgment failed") from error
            if type(result) is not bool:
                raise ContractError("invalid judgment scalar")
            results[row["candidate_id"]] = result
        if deadline <= monotonic():
            raise ContractError("judgment deadline expired")
        document = parse_contract(
            "JudgmentRecord",
            {
                "schema_version": "1",
                "function_revision": policy["function_revision"],
                "model_revision": policy["model_revision"],
                "candidate_digest": canonical_digest([dict(row) for row in candidates]),
                "judgments": results,
                "measurements": [
                    measurement for call in measurements.values() for measurement in call
                ],
            },
        )
        return dict(document.payload())


class DiscoveryJevAdapter:
    def __init__(
        self, policy: Mapping[str, Any], on_event: Callable[[object], None] | None = None
    ) -> None:
        self.policy = parse_contract("DiscoveryJudgmentPolicy", policy).payload()
        self.on_event = on_event

    def _authorize(self) -> None:
        policy = self.policy
        if not policy["enabled"] or not policy["cloud_allowed"]:
            raise ContractError("discovery judgment not authorized")
        if (
            policy["model_revision"] != "jev-latest"
            or policy["provider"] != "typesafeai"
            or policy["token_counter_revision"] != "utf8-bytes-upper-bound-v1"
        ):
            raise ContractError("unsupported discovery judgment identity")
        if policy["hard_output_token_limit"] is not None:
            raise ContractError("provider output token enforcement unavailable")
        rates, ceiling = policy["rates"], policy["spending_ceiling"]
        if ceiling is not None and (
            rates is None
            or rates["input_rate"] is None
            or rates["output_rate"] is None
            or rates["currency"] != ceiling["currency"]
            or Decimal(rates["output_rate"]) != 0
            or not datetime.fromisoformat(rates["verified_at"])
            <= datetime.now(UTC)
            < datetime.fromisoformat(rates["expires_at"])
        ):
            raise ContractError("discovery spending enforcement unavailable")

    def prepare_option(
        self,
        objective: str,
        context: str,
        question: Mapping[str, Any],
        option: Mapping[str, Any],
    ) -> tuple[str, str, dict[str, Any]]:
        self._authorize()
        policy = self.policy
        if option["feasible"] is not True or option["option_id"] not in {
            row["option_id"] for row in question["options"]
        }:
            raise ContractError("unoffered discovery option")
        task = json.dumps({"objective": objective, "authorized_context": context}, sort_keys=True)
        offered = json.dumps(
            {
                "question_digest": question["question_digest"],
                "level": question["level"],
                "option_id": option["option_id"],
                "label": option["label"],
                "description": option["description"],
                "description_unknown": option["description"] is None,
            },
            sort_keys=True,
        )
        tokens = len(discovery_request_shape(task, offered).encode())
        rates = policy["rates"]
        cost, currency = None, None
        if (
            rates is not None
            and rates["input_rate"] is not None
            and rates["output_rate"] is not None
            and Decimal(rates["output_rate"]) == 0
            and datetime.fromisoformat(rates["verified_at"])
            <= datetime.now(UTC)
            < datetime.fromisoformat(rates["expires_at"])
        ):
            cost, currency = str(Decimal(tokens) * Decimal(rates["input_rate"])), rates["currency"]
        return (
            task,
            offered,
            {
                "input_tokens": tokens,
                "output_tokens": policy["output_planning_reservation"],
                "reserved_spend": cost,
                "currency": currency,
            },
        )

    def observe_option(
        self,
        task: str,
        offered: str,
        question_digest: str,
        option_id: str,
        deadline: float,
    ) -> dict[str, Any]:
        self._authorize()
        remaining = int((deadline - monotonic()) * 1000)
        if remaining <= 0:
            raise ContractError("discovery judgment deadline expired")
        measurements: list[dict[str, Any]] = []
        invocation_id = str(uuid4())

        def observe(event: object) -> None:
            if isinstance(event, JevUsageObservation):
                event = event.model_copy(update={"invocation_id": invocation_id})
                measurements[:] = jev_usage_measurements(event)
                if self.on_event is not None:
                    self.on_event(event)

        try:
            answer = ObserveDiscoveryOption(task, offered, remaining, observe)
        except BamlError:
            answer = None
        if answer is not None and type(answer) is not bool:
            raise ContractError("invalid discovery judgment scalar")
        if monotonic() >= deadline:
            answer = None
        return dict(
            parse_contract(
                "DiscoveryJudgmentRecord",
                {
                    "schema_version": "1",
                    "function_revision": "ObserveDiscoveryOption-v1",
                    "model_revision": self.policy["model_revision"],
                    "question_digest": question_digest,
                    "judgments": {} if answer is None else {option_id: answer},
                    "measurements": measurements,
                },
            ).payload()
        )
