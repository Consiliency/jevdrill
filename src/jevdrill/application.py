"""Validated orchestration connecting routing inputs, provider budgets and durable storage."""

import copy
import itertools
import json
from collections.abc import Callable, Mapping
from decimal import Decimal
from pathlib import Path
from time import monotonic, time
from typing import Any

from .analysis import (
    PolicyAuthority,
    PolicyEvidencePort,
    PolicyLifecycle,
    aggregate_observations,
    assess_objectives,
)
from .catalog import catalog_digest, narrow, retrieve
from .context import collect_context, excluded_reference, redact
from .contracts import (
    ContractError,
    DiscoveryJudgmentPort,
    InventoryPort,
    JudgmentPort,
    canonical_digest,
    parse_contract,
)
from .costing import ConservativeTokenCounter, estimate_attempt_cost
from .discovery import (
    apply_answers,
    complete,
    initial_state,
    metadata_question,
    metadata_state,
    next_question,
    reference,
    replay_trace,
    select_resources,
)
from .evaluation import evaluate_policy
from .experiments import ExperimentAuthority, ExperimentRunner, Experiments, ExperimentSettings
from .guidance import select_guidance
from .integrations.jev import (
    JUDGMENT_CANDIDATE_FIELDS,
    JUDGMENT_FUNCTION_REVISION,
    DiscoveryJevAdapter,
    JevAdapter,
    judgment_template_binding,
)
from .inventory import fresh, validate_snapshot
from .routing import decision_details, select_plan
from .settings import resolve_settings
from .storage import SQLiteStorage
from .telemetry import retain_jev_call


def _scope(envelope: Mapping[str, Any], operation: str) -> dict[str, str]:
    return {
        "project_id": envelope["project_id"],
        "workspace_id": envelope["workspace_id"],
        "producer": envelope["harness_id"],
        "operation": operation,
    }


def _sanitize(value: Any) -> Any:
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize(item) for key, item in value.items()}
    return value


class Application:
    def __init__(
        self,
        storage: SQLiteStorage,
        inventory: InventoryPort | None = None,
        judgments: JudgmentPort | None = None,
        discovery_judgments: DiscoveryJudgmentPort | None = None,
        experiment_authority: ExperimentAuthority | None = None,
        experiment_runner: ExperimentRunner | None = None,
        experiment_settings: ExperimentSettings | None = None,
        policy_authority: PolicyAuthority | None = None,
        policy_evidence: PolicyEvidencePort | None = None,
        policy_task_group: Callable[[Mapping[str, Any]], str | None] | None = None,
    ) -> None:
        self.storage = storage
        self.inventory = inventory
        self.judgments = judgments
        self.discovery_judgments = discovery_judgments
        self.experiments = Experiments(
            storage, experiment_authority, experiment_runner, settings=experiment_settings
        )
        self.policy_lifecycle = PolicyLifecycle(storage, policy_authority, policy_evidence)
        self.policy_task_group = policy_task_group

    def discover(self, payload: Mapping[str, Any], deadline: float | None = None) -> dict[str, Any]:
        started = monotonic()
        inputs = _sanitize(parse_contract("DiscoveryInputs", payload).payload())
        settings = resolve_settings(
            [(row["source"], row["values"]) for row in inputs["settings_layers"]]
        )
        deadline = min(
            deadline or started + 5,
            started
            + min(
                5000,
                settings["routing_deadline_ms"],
                inputs["hard_constraints"]["total_deadline_ms"],
            )
            / 1000,
        )
        self.storage.deadline = deadline
        context = collect_context(
            inputs["work_objective_text"], inputs["attachment_refs"], settings["excluded_paths"]
        )
        inputs["work_objective_text"] = context["task_representation"]
        inputs["attachment_refs"] = context["attachments"]
        limits = copy.deepcopy(inputs["limits"])
        policy = copy.deepcopy(inputs["judgment_policy"])
        for field in (
            "max_calls",
            "max_candidates",
            "max_input_tokens",
            "output_planning_reservation",
        ):
            limits[field] = min(limits[field], policy[field])
            policy[field] = limits[field]
        limits["max_input_tokens"] = min(
            limits["max_input_tokens"], inputs["hard_constraints"]["context_token_limit"]
        )
        policy["max_input_tokens"] = limits["max_input_tokens"]
        hard_outputs = [
            value
            for value in (limits["hard_output_token_limit"], policy["hard_output_token_limit"])
            if value is not None
        ]
        limits["hard_output_token_limit"] = policy["hard_output_token_limit"] = (
            min(hard_outputs) if hard_outputs else None
        )
        ceilings = [
            value
            for value in (limits["spending_ceiling"], policy["spending_ceiling"])
            if value is not None
        ]
        if len({row["currency"] for row in ceilings}) > 1:
            raise ContractError("incomparable discovery ceilings")
        limits["spending_ceiling"] = policy["spending_ceiling"] = (
            min(ceilings, key=lambda row: Decimal(row["amount"])) if ceilings else None
        )
        limits["max_description_utf8_bytes"] = min(
            limits["max_description_utf8_bytes"], settings.get("max_description_utf8_bytes", 2048)
        )
        constraints = inputs["hard_constraints"]
        if constraints["local_only"] or (
            constraints["allowed_providers"]
            and policy["provider"] not in constraints["allowed_providers"]
        ):
            policy["cloud_allowed"] = False
        state = initial_state(inputs, limits)
        scope = _scope(inputs["envelope"], "discover")
        revisions = {
            "catalog_revision": inputs["catalog"]["revision"],
            "catalog_digest": catalog_digest(inputs["catalog"]["resources"]),
            "taxonomy_revision": inputs["taxonomy_revision"],
            "content_revision": inputs["content_revision"],
            "descriptions_digest": canonical_digest(
                sorted(
                    inputs["descriptions"], key=lambda row: (row["resource_id"], row["revision"])
                )
            ),
            "settings_revision": settings["settings_revision"],
            "policy_digest": canonical_digest(policy),
            "authorization_digest": canonical_digest(
                [scope, constraints, inputs["attachment_refs"], inputs["required_guidance"]]
            ),
        }
        seed = {
            "initial_state": metadata_state(state),
            "revisions": revisions,
            "hard_constraints": constraints,
            "acceptance_requirements": inputs["acceptance_requirements"],
            "excluded_paths": settings["excluded_paths"],
            "required_guidance": inputs["required_guidance"],
            "missing_context": context["unavailable"] or not inputs["work_objective_text"].strip(),
            "guidance_context_limit": max(
                0,
                constraints["context_token_limit"]
                - len(
                    json.dumps(
                        {
                            "objective": inputs["work_objective_text"],
                            "context": inputs["authorized_context"],
                            "attachments": inputs["attachment_refs"],
                            "acceptance": inputs["acceptance_requirements"],
                            "governing": constraints["governing_instruction_refs"],
                        },
                        sort_keys=True,
                    ).encode()
                ),
            ),
        }
        if settings["retain_raw_tasks"]:
            seed["initial_state"] = copy.deepcopy(state)
            seed["raw_objective"] = inputs["work_objective_text"]
            seed["raw_context"] = inputs["authorized_context"]
        digest = canonical_digest([canonical_digest(dict(payload)), inputs, revisions, limits])
        reservation = self.storage.reserve_discovery(
            scope,
            inputs["envelope"]["idempotency_key"],
            digest,
            inputs["work_objective_id"],
            limits,
            seed,
        )
        identity = reservation["discovery_id"]
        existing = self.storage.load_discovery(scope, identity)
        assert existing is not None
        if existing["result"] is not None:
            return dict(existing["result"])
        if not reservation["created"]:
            return self.storage.recover_discovery(
                scope,
                identity,
                lambda recorded: self._discovery_trace(
                    recorded, inputs["catalog"]["resources"], "interrupted"
                ),
            )
        required_error = None
        try:
            for row in inputs["required_guidance"]:
                if row["task_id"] != inputs["work_objective_id"]:
                    raise ContractError("required guidance objective scope mismatch")
            select_resources(
                state,
                inputs["catalog"]["resources"],
                inputs["required_guidance"],
                seed["guidance_context_limit"],
            )
        except ContractError as error:
            required_error = str(error)
        reason = "complete"
        adapter = self.discovery_judgments or DiscoveryJevAdapter(policy)
        if not seed["missing_context"] and required_error is None:
            while not complete(state) and (question := next_question(state)) is not None:
                if monotonic() >= deadline - 0.1:
                    reason = "deadline"
                    break
                saved_question = (
                    question if settings["retain_raw_tasks"] else metadata_question(question)
                )
                round_number = self.storage.begin_discovery_round(
                    scope, identity, saved_question, state["budget"]
                )
                answers: dict[str, bool] = {}
                measurements = []
                budget = copy.deepcopy(state["budget"])
                for option in question["options"]:
                    if option["feasible"] is not True:
                        continue
                    if monotonic() >= deadline - 0.1:
                        reason = "deadline"
                        break
                    try:
                        # The production adapter validates authority and packing even for a synthetic observer.
                        prepare_option = (
                            getattr(adapter, "prepare_option", None)
                            or DiscoveryJevAdapter(policy).prepare_option
                        )
                        task, offered, allowance = prepare_option(
                            inputs["work_objective_text"],
                            inputs["authorized_context"]
                            + json.dumps(inputs["attachment_refs"], sort_keys=True),
                            question,
                            option,
                        )
                        sequence = self.storage.reserve_discovery_call(
                            scope, identity, round_number, option["option_id"], allowance
                        )
                    except ContractError:
                        reason = "allowance_or_authority"
                        continue
                    budget["calls"] += 1
                    budget["input_tokens"] += allowance["input_tokens"]
                    budget["output_tokens"] += allowance["output_tokens"]
                    budget["reserved_spend"] = (
                        None
                        if budget["reserved_spend"] is None or allowance["reserved_spend"] is None
                        else str(
                            Decimal(budget["reserved_spend"]) + Decimal(allowance["reserved_spend"])
                        )
                    )
                    budget["currency"] = allowance["currency"] or budget["currency"]
                    try:
                        observation = parse_contract(
                            "DiscoveryJudgmentRecord",
                            adapter.observe_option(
                                task,
                                offered,
                                question["question_digest"],
                                option["option_id"],
                                deadline - 0.1,
                            ),
                        ).payload()
                        if (
                            observation["question_digest"] != question["question_digest"]
                            or observation["model_revision"] != policy["model_revision"]
                            or not set(observation["judgments"]) <= {option["option_id"]}
                        ):
                            raise ContractError("discovery observation binding mismatch")
                        if not observation["judgments"]:
                            reason = "observation_failed"
                    except (ContractError, OSError):
                        observation = {
                            "schema_version": "1",
                            "function_revision": "ObserveDiscoveryOption-v1",
                            "model_revision": policy["model_revision"],
                            "question_digest": question["question_digest"],
                            "judgments": {},
                            "measurements": [],
                        }
                        reason = "observation_failed"
                    accepted = self.storage.observe_discovery_call(
                        scope, identity, sequence, observation
                    )
                    if not accepted:
                        completed = self.storage.load_discovery(scope, identity)
                        assert completed is not None and completed["result"] is not None
                        return dict(completed["result"])
                    answers.update(observation["judgments"])
                    measurements.extend(observation["measurements"])
                record = {
                    "schema_version": "1",
                    "function_revision": "ObserveDiscoveryOption-v1",
                    "model_revision": policy["model_revision"],
                    "question_digest": question["question_digest"],
                    "judgments": answers,
                    "measurements": measurements,
                }
                state = apply_answers(state, question, record, budget)
        recorded = self.storage.load_discovery(scope, identity)
        assert recorded is not None
        trace = self._discovery_trace(
            recorded, inputs["catalog"]["resources"], reason, required_error
        )
        if len(json.dumps(trace["result"], separators=(",", ":")).encode()) > 1_000_000:
            raise OSError("discovery response too large")
        if monotonic() >= deadline - 0.05:
            raise TimeoutError("discovery commit deadline expired")
        return self.storage.commit_discovery(scope, identity, trace)

    def _discovery_trace(
        self,
        recorded: Mapping[str, Any],
        resources: list[dict[str, Any]],
        reason: str,
        required_error: str | None = None,
    ) -> dict[str, Any]:
        seed = recorded["seed"]
        state = copy.deepcopy(seed["initial_state"])
        transitions = []
        model = "jev-latest"
        for round_row in recorded["rounds"]:
            budget = copy.deepcopy(state["budget"])
            judgments = {}
            measurements = []
            for call in recorded["calls"]:
                if call["round_number"] != round_row["round_number"]:
                    continue
                reservation = call["reservation"]
                for key in ("calls", "input_tokens", "output_tokens"):
                    budget[key] += 1 if key == "calls" else reservation[key]
                budget["reserved_spend"] = (
                    None
                    if budget["reserved_spend"] is None or reservation["reserved_spend"] is None
                    else str(
                        Decimal(budget["reserved_spend"]) + Decimal(reservation["reserved_spend"])
                    )
                )
                budget["currency"] = reservation["currency"] or budget["currency"]
                if call["observation"] is not None:
                    observation = call["observation"]
                    judgments.update(observation["judgments"])
                    measurements.extend(observation["measurements"])
                    model = observation["model_revision"]
            answers = {
                "schema_version": "1",
                "function_revision": "ObserveDiscoveryOption-v1",
                "model_revision": model,
                "question_digest": round_row["question"]["question_digest"],
                "judgments": judgments,
                "measurements": measurements,
            }
            before = copy.deepcopy(state["budget"])
            state = apply_answers(state, round_row["question"], answers, budget)
            transitions.append(
                {
                    "question": round_row["question"],
                    "answers": answers,
                    "budget_before": before,
                    "budget_after": copy.deepcopy(state["budget"]),
                }
            )
        required = seed["required_guidance"]
        refs: list[dict[str, str]] = []
        instructions: list[str] = []
        omitted: list[str] = []
        shortlist = []
        required_refs = {canonical_digest(reference(row)) for row in required}
        supported_refs = {key.removeprefix("resource:") for key in state["supported"]}
        for resource in resources:
            digest = canonical_digest(reference(resource))
            if digest in required_refs or digest in supported_refs:
                shortlist.append(
                    {
                        "reference": reference(resource),
                        "instruction_utf8_bytes": len(resource["instructions"].encode()),
                        "conflicts": resource["conflicts"],
                        "required": digest in required_refs,
                        "admitted": resource["admission"]
                        in {"policy_admitted", "explicitly_enabled"},
                    }
                )
        try:
            if any(row["task_id"] != recorded["work_objective_id"] for row in required):
                raise ContractError("required guidance objective scope mismatch")
            refs, instructions, omitted = select_resources(
                state, resources, required, seed["guidance_context_limit"]
            )
        except ContractError as error:
            required_error = str(error)
        for key in omitted:
            state["supported"].remove(key)
            state["excluded"].append(key)
        uncertainty = list(state["unresolved"])
        if not complete(state):
            uncertainty.append("unexamined candidates")
        details = {
            "discovery_id": recorded["discovery_id"],
            "work_objective_id": recorded["work_objective_id"],
            "guidance_refs": refs,
            "required_guidance": required,
            "assembled_instructions": instructions,
            "alternatives": sorted(
                set(state["supported"]) - {"resource:" + canonical_digest(row) for row in refs}
            ),
            "uncertainty": sorted(set(uncertainty)),
            "termination_reason": "complete"
            if complete(state)
            else reason
            if reason != "complete"
            else "limits_exhausted",
            "trace_digest": "0" * 64,
            "revisions": seed["revisions"],
        }
        if seed["missing_context"]:
            result = {
                "status": "needs_context",
                "details": details,
                "missing_facts": ["authorized objective context"],
            }
        elif required_error:
            result = {
                "status": "constraint_conflict",
                "details": details,
                "conflicting_requirements": [required_error],
            }
        elif refs:
            result = {"status": "selected_guidance", "details": details}
        elif complete(state):
            result = {"status": "no_optional_guidance", "details": details}
        else:
            result = {
                "status": "discovery_failed",
                "details": details,
                "error_code": "interrupted" if reason == "interrupted" else "incomplete_discovery",
            }
        trace = {
            "schema_version": "1",
            "initial_state": seed["initial_state"],
            "transitions": transitions,
            "final_state": state,
            "hard_constraints": seed["hard_constraints"],
            "acceptance_requirements": seed["acceptance_requirements"],
            "excluded_paths": seed["excluded_paths"],
            "result": result,
            "replay_available": True,
            "shortlist": shortlist,
            "missing_context": seed["missing_context"],
            "required_feasible": required_error is None,
            "guidance_context_limit": seed["guidance_context_limit"],
        }
        trace["finalization_exclusions"] = omitted
        # Feasibility exclusions found at shortlist time are recorded, independently of question answers.
        trace["result"]["details"]["trace_digest"] = canonical_digest(trace)
        if len(json.dumps(result, separators=(",", ":")).encode()) > 1_000_000:
            raise OSError("discovery response too large")
        return dict(parse_contract("DiscoveryTrace", trace).payload())

    def inspect_discovery(
        self, scope: Mapping[str, str], discovery_id: str, replay: bool = False
    ) -> dict[str, Any] | None:
        parse_contract(
            "DiscoveryInspectRequest",
            {
                "schema_version": "1",
                "scope": dict(scope),
                "discovery_id": discovery_id,
                "replay": replay,
            },
        )
        recorded = self.storage.load_discovery(scope, discovery_id)
        if recorded is None or recorded["trace"] is None:
            return None
        return replay_trace(recorded["trace"]) if replay else dict(recorded["result"])

    def delete_discovery(self, scope: Mapping[str, str], work_objective_id: str) -> dict[str, Any]:
        parse_contract(
            "DiscoveryDeleteRequest",
            {"schema_version": "1", "scope": dict(scope), "work_objective_id": work_objective_id},
        )
        return self.storage.delete_discovery(scope, work_objective_id)

    def route(self, payload: Mapping[str, Any], deadline: float | None = None) -> dict[str, Any]:
        started = monotonic()
        self.storage.deadline = min(deadline or started + 5, started + 5)
        linked = None
        if payload.get("schema_version") == "2":
            wrapper = parse_contract("DiscoveryRouteInputs", payload).payload()
            inputs, linked = self._linked_inputs(wrapper)
        elif "request" in payload:
            inputs = parse_contract("RouteInputs", payload).payload()
        else:
            inputs = {
                "request": parse_contract("RouteRequest", payload).payload(),
                "inventory": None,
                "catalog": None,
                "settings_layers": [],
                "judgment_policy": None,
            }
        request_digest = (
            canonical_digest(dict(payload))
            if linked is None
            else canonical_digest([dict(payload), linked["result"]["details"]["revisions"]])
        )
        request = _sanitize(inputs["request"])
        settings = resolve_settings(
            [(row["source"], row["values"]) for row in inputs["settings_layers"]]
        )
        if linked is not None:
            settings["excluded_paths"] = sorted(
                set(settings["excluded_paths"]) | set(linked["trace"]["excluded_paths"])
            )
        deadline = min(
            deadline or started + 5,
            started
            + min(settings["routing_deadline_ms"], request["hard_constraints"]["total_deadline_ms"])
            / 1000,
        )
        if request["retry_context"] is not None:
            deadline = min(deadline, started + request["retry_context"]["remaining_time_ms"] / 1000)
        self.storage.deadline = deadline
        scope = _scope(request["envelope"], "route")
        if self.storage.is_deleted(scope, request["task_id"]):
            raise ContractError("task deleted")
        retry = self.storage.lookup_retry(
            scope,
            request["envelope"]["idempotency_key"],
            request_digest,
            None if linked is None else wrapper["discovery_ref"],
        )
        if retry is not None:
            decision: dict[str, Any] = dict(retry["bundle"]["decision"])
            if decision["status"] == "ready" and any(
                row["code"] == "learned_policy_ordering"
                for row in decision["details"]["diagnostics"]
            ):
                group = (
                    self.policy_task_group(copy.deepcopy(request))
                    if self.policy_task_group
                    else None
                )
                ordering = (
                    self.policy_lifecycle.ordering(
                        scope,
                        group,
                        request["optimization_objective"],
                        request["envelope"]["request_id"],
                        request["task_id"],
                    )
                    if group
                    else {"status": "blocked"}
                )
                if (
                    ordering["status"] != "ready"
                    or ordering["policy_revision"]
                    != decision["details"]["versions"]["policy_revision"]
                ):
                    return {
                        "status": "routing_failed",
                        "details": decision["details"],
                        "error_code": "policy_verification_required",
                        "retryable": True,
                    }
            return decision
        cache_inputs = copy.deepcopy(inputs)
        for key in ("request_id", "idempotency_key", "created_at"):
            cache_inputs["request"]["envelope"].pop(key)
        cache_digest = (
            canonical_digest([cache_inputs, judgment_template_binding()])
            if linked is None
            else canonical_digest(
                [
                    cache_inputs,
                    wrapper["discovery_ref"],
                    linked["result"]["details"]["revisions"],
                    judgment_template_binding(),
                ]
            )
        )
        cached = (
            None
            if self.inventory is not None or self.policy_task_group is not None
            else self.storage.lookup_cache(scope, cache_digest)
        )
        if cached is not None and any(
            row["code"] == "learned_policy_ordering"
            for row in cached["decision"]["details"]["diagnostics"]
        ):
            cached = None
        request["versions"]["settings_revision"] = settings["settings_revision"]
        context = collect_context(
            request["task_representation"], request["attachment_refs"], settings["excluded_paths"]
        )
        request["task_representation"] = context["task_representation"]
        request["attachment_refs"] = context["attachments"]
        details = decision_details(request, [])
        judgment_record = None
        if (
            cached is not None
            and cached["decision"]["status"] == "ready"
            and fresh(
                cached["decision"]["readiness"]["verified_at"],
                cached["decision"]["readiness"]["valid_until"],
            )
        ):
            decision = copy.deepcopy(cached["decision"])
            decision["details"].update(
                {key: details[key] for key in ("routing_decision_id", "request_id", "created_at")}
            )
            decision["details"]["reused_decision_id"] = cached["routing_decision_id"]
            judgment_record = cached["judgments"]
        elif context["unavailable"] or not request["task_representation"].strip():
            decision = {
                "status": "needs_context",
                "details": details,
                "missing_facts": ["authorized supplied context"],
            }
        elif (
            request["optimization_objective"]["routing_cost_basis"] == "adjusted"
            and settings["routing_cost_basis"] != "adjusted"
        ):
            decision = {
                "status": "constraint_conflict",
                "details": details,
                "conflicting_requirements": ["subscription adjustment not enabled"],
            }
        else:
            try:
                source = inputs["inventory"]
                if self.inventory is not None:
                    source = self.inventory.snapshot(
                        request["envelope"]["execution_target_id"], deadline - 0.05
                    )
                if source is None:
                    raise ContractError("inventory unavailable")
                if _sanitize(source) != source:
                    raise ContractError("excluded inventory metadata")
                snapshot = validate_snapshot(
                    source, request["envelope"]["execution_target_id"], deadline - 0.05
                )
                if linked is not None:
                    allowed = {
                        canonical_digest(row)
                        for row in linked["result"]["details"]["guidance_refs"]
                    }
                    required_ids = {
                        canonical_digest(reference(row)) for row in request["active_guidance"]
                    }
                    for candidate in snapshot["candidates"]:
                        candidate["guidance_options"] = [
                            row
                            for row in candidate["guidance_options"]
                            if canonical_digest(reference(row)) in allowed
                            and canonical_digest(reference(row)) not in required_ids
                        ]
                        for row in candidate["guidance_options"]:
                            row["task_id"] = request["task_id"]
                capability = request["capabilities"]
                if snapshot["revision"] != capability["inventory_revision"] or not fresh(
                    capability["verified_at"], capability["expires_at"]
                ):
                    raise ContractError("inventory revision or freshness mismatch")
                catalog = inputs["catalog"]
                resources = [] if catalog is None else catalog["resources"]
                if catalog is not None:
                    if _sanitize(catalog) != catalog:
                        raise ContractError("excluded catalog content")
                    catalog_digest(resources)
                    if catalog["revision"] != request["versions"]["catalog_revision"]:
                        raise ContractError("catalog revision mismatch")
                    query = inputs.get("catalog_query")
                    if query is not None:
                        resources = narrow(
                            resources,
                            query["domain"],
                            query["specialty"],
                            query["task_family"],
                            query["facets"],
                            query["max_branches"],
                        )
                prepared = self._prepare(request, snapshot, resources, settings, deadline)
                for row in prepared:
                    row["completion_time_limit_ms"] = inputs.get("completion_time_limit_ms")
                recorded: list[dict[str, object]] = []

                def observe(event: object) -> None:
                    measurement = retain_jev_call(event)
                    if measurement is not None:
                        recorded.append(measurement)

                policy = inputs["judgment_policy"]
                offered = [
                    row
                    for row in prepared
                    if not row["exclusion_reasons"] and row["quality_sufficient"] is None
                ]
                can_judge = (
                    policy
                    and policy["enabled"]
                    and policy["cloud_allowed"]
                    and not request["hard_constraints"]["local_only"]
                    and not request["recursion_bypass"]
                )
                if can_judge and offered:
                    assert policy is not None
                    if policy["function_revision"] != JUDGMENT_FUNCTION_REVISION:
                        raise ContractError(
                            "legacy judgment policy cannot dispatch current template"
                        )
                    if policy["rates"] is not None and not fresh(
                        policy["rates"]["verified_at"], policy["rates"]["expires_at"]
                    ):
                        raise ContractError("stale judgment rates")
                    offered = offered[: min(policy["max_candidates"], policy["max_calls"])]
                    public: tuple[Mapping[str, Any], ...] = tuple(
                        {
                            key: value
                            for key, value in row.items()
                            if key in JUDGMENT_CANDIDATE_FIELDS
                        }
                        for row in offered
                    )
                    judge = self.judgments or JevAdapter(policy, observe)
                    try:
                        task_text = json.dumps(
                            {
                                "task": request["task_representation"],
                                "acceptance": request["optimization_objective"][
                                    "acceptance_requirements"
                                ],
                                "context": request["attachment_refs"],
                                "governing": request["hard_constraints"][
                                    "governing_instruction_refs"
                                ],
                            },
                            sort_keys=True,
                        )
                        public = JevAdapter(policy).bounded_candidates(task_text, public)
                        selected_ids = {row["candidate_id"] for row in public}
                        offered = [row for row in offered if row["candidate_id"] in selected_ids]
                        if not public:
                            raise ContractError("required judgment context exceeds budget")
                        result = judge.judge(task_text, public, deadline - 0.05)
                        judgment_record = parse_contract("JudgmentRecord", dict(result)).payload()
                        if (
                            judgment_record["candidate_digest"] != canonical_digest(list(public))
                            or set(judgment_record["judgments"])
                            != {row["candidate_id"] for row in offered}
                            or judgment_record["function_revision"] != policy["function_revision"]
                            or judgment_record["model_revision"] != policy["model_revision"]
                        ):
                            raise ContractError("judgment binding mismatch")
                        for row in offered:
                            row["quality_sufficient"] = judgment_record["judgments"][
                                row["candidate_id"]
                            ]
                            row["evidence_strength"] = "judgment"
                    except (ContractError, OSError):
                        judgment_record = None
                        # Fallback is restricted to an already feasible configured default.
                        prepared = [
                            dict(row, fallback_used=True)
                            for row in prepared
                            if row["default"] and row["quality_sufficient"] is True
                        ]
                        if not prepared:
                            raise ContractError("judgment failed without verified fallback")
                ordering_policy = None
                if self.policy_task_group is not None and request["execution_mode"] != "dry_run":
                    group = self.policy_task_group(copy.deepcopy(request))
                    if group is not None:
                        ordering = self.policy_lifecycle.ordering(
                            scope,
                            group,
                            request["optimization_objective"],
                            request["envelope"]["request_id"],
                            request["task_id"],
                        )
                        if ordering["status"] == "blocked":
                            raise ContractError("policy_verification_required")
                        if ordering["status"] == "ready":
                            ordering_policy = ordering
                decision = select_plan(request, prepared, policy=ordering_policy)
                for row in snapshot["candidates"]:
                    missing = sorted(
                        set(row["required_capabilities"]) - set(row["effective_capabilities"])
                    )
                    if missing:
                        decision["details"]["setup_proposals"].append(
                            {
                                "candidate_id": row["candidate_id"],
                                "missing_capabilities": missing,
                                "proposed_actions": [
                                    "Host-authorized setup followed by a new inventory snapshot"
                                ],
                                "requires_authorization": True,
                            }
                        )
                for measurement in recorded:
                    for metric in ("duration_ms", "input_tokens", "output_tokens"):
                        value = measurement[metric]
                        decision["details"]["measurements"].append(
                            {
                                "metric_id": "routing_" + metric,
                                "metric_version": "1",
                                "measurement_value": {"kind": "unknown", "reason": "not_reported"}
                                if value is None
                                else {
                                    "kind": "known",
                                    "value": value,
                                    "unit": "ms" if metric == "duration_ms" else "tokens",
                                },
                                "source": "provider",
                                "method": "jev-call-v1",
                                "scope": "call",
                                "counting_semantics": "disjoint",
                                "parent_metric_id": None,
                            }
                        )
                decision["details"]["cost_estimate"]["assumptions"].append(
                    "routing overhead is separate from execution estimate"
                )
            except ContractError as error:
                decision = {
                    "status": "routing_failed",
                    "details": details,
                    "error_code": str(error),
                    "retryable": True,
                }
        if monotonic() >= deadline:
            raise TimeoutError("route deadline expired")
        if linked is not None:
            decision["details"].update(
                discovery_ref=wrapper["discovery_ref"],
                discovery_termination=linked["result"]["details"]["termination_reason"],
                discovery_uncertainty=linked["result"]["details"]["uncertainty"],
            )
        decision["details"]["notices"] = self.storage.load_notices(scope)
        decision = parse_contract("RoutingDecision", decision).payload()
        bundle = parse_contract(
            "ReplayBundle",
            {
                "schema_version": "1",
                "routing_decision_id": decision["details"]["routing_decision_id"],
                "task_id": request["task_id"],
                "request_digest": request_digest,
                "cache_digest": cache_digest,
                "decision": decision,
                "judgments": judgment_record,
            },
        ).payload()
        committed = self.storage.commit_decision(
            scope, request["envelope"]["idempotency_key"], request_digest, bundle
        )
        self.storage.restrict_learning(
            scope,
            request["task_id"],
            settings["local_analysis_enabled"]
            and not any(
                excluded_reference(a["reference"], settings["excluded_paths"])
                for a in inputs["request"]["attachment_refs"]
            ),
        )
        if settings["retain_raw_tasks"]:
            self.storage.stage_artifact(
                scope,
                request["task_id"],
                request["task_representation"].encode(),
                kind="raw_task",
                retention="active",
                encryption="none",
                retain_raw_tasks=True,
            )
        return dict(committed["bundle"]["decision"])

    def _linked_inputs(self, wrapper: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        inputs = copy.deepcopy(wrapper["route_inputs"])
        request = inputs["request"]
        ref = wrapper["discovery_ref"]
        recorded = self.storage.load_discovery(
            _scope(request["envelope"], "discover"), ref["discovery_id"]
        )
        if recorded is None or recorded["result"] is None or recorded["trace"] is None:
            raise ContractError("linked discovery unavailable")
        result = recorded["result"]
        if (
            result["status"] not in {"selected_guidance", "no_optional_guidance"}
            or recorded["work_objective_id"] != ref["work_objective_id"]
            or result["details"]["trace_digest"] != ref["trace_digest"]
        ):
            raise ContractError("linked discovery reference or status invalid")
        catalog = inputs["catalog"]
        revisions = result["details"]["revisions"]
        if (
            catalog is None
            or catalog["revision"] != revisions["catalog_revision"]
            or request["versions"]["catalog_revision"] != catalog["revision"]
            or catalog_digest(catalog["resources"]) != revisions["catalog_digest"]
        ):
            raise ContractError("stale linked discovery revisions")
        self._inherit_constraints(
            recorded["trace"]["hard_constraints"], request["hard_constraints"]
        )
        inherited = {
            row["requirement_id"]: row for row in recorded["trace"]["acceptance_requirements"]
        }
        supplied = request["optimization_objective"]["acceptance_requirements"]
        requirements = {row["requirement_id"]: row for row in supplied}
        if len(requirements) != len(supplied) or any(
            requirements.get(key) != row for key, row in inherited.items()
        ):
            raise ContractError("inherited acceptance requirements changed")
        mandatory: list[dict[str, Any]] = []
        for row in result["details"]["required_guidance"] + request["active_guidance"]:
            guidance = copy.deepcopy(row)
            guidance["task_id"] = request["task_id"]
            matched = next(
                (item for item in mandatory if item["resource_id"] == guidance["resource_id"]), None
            )
            if matched is None:
                mandatory.append(guidance)
            elif any(
                matched[key] != guidance[key]
                for key in (
                    "resource_id",
                    "revision",
                    "content_hash",
                    "role",
                    "authority",
                    "admission",
                )
            ):
                raise ContractError("inherited required guidance conflict")
        request["active_guidance"] = mandatory
        return inputs, recorded

    @staticmethod
    def _inherit_constraints(parent: Mapping[str, Any], child: Mapping[str, Any]) -> None:
        for field in ("total_deadline_ms", "context_token_limit", "max_attempts"):
            if child[field] > parent[field]:
                raise ContractError("inherited constraint weakened")
        if parent["local_only"] and not child["local_only"]:
            raise ContractError("inherited privacy constraint weakened")
        if not set(parent["governing_instruction_refs"]) <= set(
            child["governing_instruction_refs"]
        ):
            raise ContractError("inherited governing instructions weakened")
        if parent["allowed_providers"] and (
            not child["allowed_providers"]
            or not set(child["allowed_providers"]) <= set(parent["allowed_providers"])
        ):
            raise ContractError("inherited provider constraint weakened")
        ceiling = parent["spending_ceiling"]
        current = child["spending_ceiling"]
        if ceiling is not None and (
            current is None
            or current["currency"] != ceiling["currency"]
            or Decimal(current["amount"]) > Decimal(ceiling["amount"])
        ):
            raise ContractError("inherited spending constraint weakened")
        tokens = parent.get("execution_token_limits")
        limits = child.get("execution_token_limits")
        if tokens is not None and (
            limits is None or any(limits[key] > tokens[key] for key in tokens)
        ):
            raise ContractError("inherited execution token constraint weakened")

    def _prepare(
        self,
        request: Mapping[str, Any],
        snapshot: Mapping[str, Any],
        resources: list[dict[str, Any]],
        settings: Mapping[str, Any],
        deadline: float,
    ) -> list[dict[str, Any]]:
        prepared = []
        host_permissions = set(request["capabilities"]["declared"]) & set(
            request["capabilities"]["runtime"]
        )
        for candidate in sorted(snapshot["candidates"], key=lambda row: row["candidate_id"]):
            counter = ConservativeTokenCounter(
                {candidate["resolved_model_revision"]: candidate["token_counter_revision"]}
            )
            options = candidate["guidance_options"]
            combinations = [()] + [
                combo for count in (1, 2) for combo in itertools.combinations(options, count)
            ]
            for optional in combinations:
                if monotonic() >= deadline - 0.05:
                    raise ContractError("candidate preparation deadline expired")
                row = dict(candidate)
                row["candidate_id"] += ":" + canonical_digest(list(optional))[:12]
                row["default"] = (
                    row["default"] or settings["default_plan_id"] == candidate["candidate_id"]
                )
                row["exclusion_reasons"] = []
                row["available"] &= set(row["required_capabilities"]) <= host_permissions
                row["verified_at"] = max(
                    row["verified_at"],
                    snapshot["verified_at"],
                    request["capabilities"]["verified_at"],
                )
                row["expires_at"] = min(
                    row["expires_at"], snapshot["expires_at"], request["capabilities"]["expires_at"]
                )
                required = copy.deepcopy(request["active_guidance"])
                optional_rows = copy.deepcopy(list(optional))
                try:
                    contents = []
                    for guidance in required + optional_rows:
                        if guidance["task_id"] != request["task_id"]:
                            raise ContractError("guidance task scope mismatch")
                        text = retrieve(resources, guidance)
                        guidance["token_count"] = counter.count(
                            text, candidate["resolved_model_revision"]
                        )
                        contents.append(text)
                    identities = {item["resource_id"] for item in required + optional_rows}
                    if any(
                        set(resource["conflicts"]) & identities
                        for resource in resources
                        if resource["resource_id"] in identities
                    ):
                        raise ContractError("guidance conflict")
                    text = json.dumps(
                        {
                            "task": request["task_representation"],
                            "acceptance": request["optimization_objective"][
                                "acceptance_requirements"
                            ],
                            "attachments": request["attachment_refs"],
                            "governing": request["hard_constraints"]["governing_instruction_refs"],
                            "guidance": contents,
                        },
                        sort_keys=True,
                    )
                    tokens = counter.count(text, candidate["resolved_model_revision"])
                    limit = min(
                        candidate["context_token_limit"],
                        request["hard_constraints"]["context_token_limit"],
                    )
                    select_guidance(required, optional_rows, limit)
                    if tokens + candidate["output_token_limit"] > limit:
                        raise ContractError("complete context exceeds limit")
                except ContractError as error:
                    row["exclusion_reasons"].append(str(error))
                    tokens = None
                row["required_guidance"], row["optional_guidance"] = required, optional_rows
                row["guidance_instructions"] = contents
                rates = row["rates"]
                row["cost"] = estimate_attempt_cost(
                    tokens,
                    candidate["output_token_limit"],
                    None if rates is None else rates["input_rate"],
                    None if rates is None else rates["output_rate"],
                    "USD" if rates is None else rates["currency"],
                    "unknown" if rates is None else rates["revision"],
                    rates["subscription_multiplier"]
                    if rates is not None and settings["routing_cost_basis"] == "adjusted"
                    else None,
                )
                retry = request["retry_context"]
                if retry:
                    execution = self.storage.project_run(
                        _scope(request["envelope"], "route"), retry["prior_execution_run_id"]
                    )
                    run_events = [
                        event
                        for event in execution["events"]
                        if event.get("routing_decision_id") == retry["prior_routing_decision_id"]
                        and event["task_id"] == request["task_id"]
                    ]
                    attempts = self.storage.task_attempts(
                        _scope(request["envelope"], "route"), request["task_id"]
                    )
                    if (
                        not run_events
                        or retry["remaining_attempts"]
                        > request["hard_constraints"]["max_attempts"] - attempts
                    ):
                        row["exclusion_reasons"].append("unverified retry run or attempt budget")
                    prior = self.storage.load_replay(
                        _scope(request["envelope"], "route"), retry["prior_routing_decision_id"]
                    )
                    if (
                        prior is None
                        or prior["task_id"] != request["task_id"]
                        or prior["decision"]["status"] != "ready"
                    ):
                        row["exclusion_reasons"].append("invalid retry reference")
                    else:
                        row["predecessor_plan_id"] = prior["decision"]["execution_plan"][
                            "execution_plan_id"
                        ]
                prepared.append(row)
        return prepared

    def report(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        request = parse_contract("ReportRequest", payload).payload()
        event = _sanitize(request["event"])
        response = self.storage.ingest_report(
            _scope(request["envelope"], "report"),
            request["envelope"]["idempotency_key"],
            canonical_digest(event),
            event,
        )
        return dict(
            parse_contract("ReportAcknowledgment", {"schema_version": "1", **response}).payload()
        )

    def notices(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        request = parse_contract("NoticeRequest", payload).payload()
        return dict(
            parse_contract(
                "NoticeInbox",
                {"schema_version": "1", "notices": self.storage.load_notices(request["scope"])},
            ).payload()
        )

    def experiment(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self.experiments.handle(_sanitize(payload))

    def execute_experiment(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self.experiments.execute(_sanitize(payload))

    def policy(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return evaluate_policy(payload)

    def manage_policy(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self.policy_lifecycle.handle(_sanitize(payload))

    def analyze(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        request = parse_contract("AnalysisRequest", payload).payload()
        scope, now = request["scope"], time()
        settings = resolve_settings(
            [(r["source"], r["values"]) for r in request["settings_layers"]]
        )
        enabled = settings["local_analysis_enabled"] and not settings["excluded_paths"]
        if request["action"] == "record":
            context = _sanitize(request["context"])
            if not enabled:
                context.update(local_analysis_enabled=False, share_user_wide=False)
            self.storage.record_learning_context(scope, context)
        observations = (
            self.storage.learning_observations(scope, request["include_user_wide"])
            if enabled
            else []
        )
        groups = aggregate_observations(observations)
        assessments = assess_objectives(groups, request["objectives"])
        history = {
            canonical_digest(o): o
            for o in self.storage.objective_versions(scope) + request["objectives"]
        }
        digest = canonical_digest(observations)
        response = {
            "schema_version": "1",
            "status": "inspected" if enabled else "denied",
            "source_digest": digest,
            "evidence_revision": canonical_digest(
                {
                    "analysis_version": "2",
                    "groups": groups,
                    "assessments": assessments,
                    "objective_history": history,
                }
            ),
            "groups": groups,
            "assessments": assessments,
            "objective_history": [history[k] for k in sorted(history)],
        }
        if request["action"] == "record":
            response["status"] = "recorded"
        elif enabled and request["action"] == "analyze":
            previous = self.storage.latest_evidence(scope)
            previous_refs = (
                set()
                if previous is None
                else {ref for g in previous[1]["groups"] for ref in g["observation_refs"]}
            )
            current_refs = {o["observation_ref"] for o in observations}
            reassess = (
                previous is not None
                and previous[1]["source_digest"] == digest
                and previous[1]["assessments"] != assessments
            )
            due = bool(observations) and (
                len(current_refs - previous_refs) >= request["minimum_batch"]
                or reassess
                or now >= self.storage.analysis_started(scope, now) + request["interval_seconds"]
            )
            response["status"] = "updated" if due else "not_due"
            if due:
                self.storage.save_evidence(
                    scope, response, now, digest, request["include_user_wide"]
                )
        return dict(parse_contract("AnalysisResult", response).payload())

    def maintain(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        from .maintenance import Maintenance

        request = parse_contract("MaintenanceRequest", payload).payload()
        result = Maintenance(self.storage).run(request)
        if request["action"] == "run" and result["status"] == "completed":
            previous = self.storage.latest_evidence(request["scope"])
            self.analyze(
                {
                    "schema_version": "1",
                    "scope": request["scope"],
                    "action": "analyze",
                    "context": None,
                    "objectives": []
                    if previous is None
                    else [a["objective"] for a in previous[1]["assessments"]],
                    "minimum_batch": 5,
                    "interval_seconds": 86400,
                    "include_user_wide": False,
                    "settings_layers": [
                        {"source": "product", "values": {"local_analysis_enabled": True}}
                    ],
                }
            )
        return dict(parse_contract("MaintenanceResult", result).payload())

    def recover(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        from .maintenance import Maintenance

        return dict(
            parse_contract("RecoveryResult", Maintenance(self.storage).recover(payload)).payload()
        )

    def replay(self, scope: Mapping[str, str], decision_id: str) -> dict[str, Any] | None:
        parse_contract(
            "InspectRequest",
            {
                "schema_version": "1",
                "scope": dict(scope),
                "decision_id": decision_id,
                "replay": True,
            },
        )
        bundle = self.storage.load_replay(scope, decision_id)
        return None if bundle is None else dict(bundle["decision"])

    def delete_task(self, scope: Mapping[str, str], task_id: str) -> dict[str, Any]:
        parse_contract(
            "DeleteRequest", {"schema_version": "1", "scope": dict(scope), "task_id": task_id}
        )
        return {"schema_version": "1", **self.storage.delete_task(scope, task_id)}


def open_application(path: Path, deadline: float | None = None) -> Application:
    path.parent.mkdir(parents=True, exist_ok=True)
    return Application(SQLiteStorage(path, deadline))
