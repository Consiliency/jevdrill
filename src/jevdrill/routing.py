"""Deterministic complete-plan selection; effects are supplied by application."""

import uuid
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

from .contracts import canonical_digest
from .costing import AttemptCost, estimate_attempt_cost


def candidate_fingerprint(candidate: Mapping[str, Any]) -> str:
    """Pin model, effort and guidance revisions independently of task identities."""
    values = {
        key: candidate.get(key)
        for key in (
            "model_id",
            "resolved_model_revision",
            "provider",
            "access_route",
            "native_effort",
            "required_capabilities",
        )
    }
    for key in ("optional_guidance", "required_guidance"):
        values[key] = [
            {
                field: value
                for field, value in row.items()
                if field not in {"task_id", "token_count"}
            }
            for row in candidate.get(key, [])
        ]
    return canonical_digest(values)


def _money(value: Decimal | None, currency: str) -> dict[str, str] | None:
    return None if value is None else {"amount": format(value, "f"), "currency": currency}


def decision_details(
    request: Mapping[str, Any], exclusions: list[dict[str, Any]], cost: AttemptCost | None = None
) -> dict[str, Any]:
    cost = cost or AttemptCost(None, None, None, "USD", "unknown")
    envelope = request["envelope"]
    details = {
        "schema_version": "1",
        "routing_decision_id": str(
            uuid.uuid5(uuid.UUID(envelope["request_id"]), "routing-decision")
        ),
        "request_id": envelope["request_id"],
        "task_id": request["task_id"],
        "created_at": envelope["created_at"],
        "optimization_objective": request["optimization_objective"],
        "versions": request["versions"],
        "diagnostics": [],
        "capability_mismatches": [],
        "evidence_refs": [],
        "exclusions": exclusions,
        "alternatives": [],
        "close_calls": [],
        "setup_proposals": [],
        "notices": [],
        "human_summary": "Routing assessment; readiness does not authorize execution.",
        "acceptance_rationale": "Feasibility requires sufficient versioned evidence.",
        "cost_estimate": {
            "raw_token_cost": _money(cost.raw, cost.currency),
            "adjusted_token_cost": _money(cost.adjusted, cost.currency),
            "observed_cost": _money(cost.observed, cost.currency),
            "missing_reason": None if cost.raw is not None else "not_reported",
            "rate_revision": cost.rate_revision,
            "assumptions": [
                "estimated cost, not a guaranteed execution spending bound",
                "UTF-8 byte input upper bound",
            ]
            if cost.raw is not None
            else [],
        },
        "measurements": [],
        "reused_decision_id": None,
    }
    declared, runtime = request["capabilities"]["declared"], request["capabilities"]["runtime"]
    if set(declared) != set(runtime):
        details["capability_mismatches"] = [
            {
                "code": "capability_mismatch",
                "declared": declared,
                "runtime": runtime,
                "effective": sorted(set(declared) & set(runtime)),
                "affected_operations": ["route"],
                "evidence_refs": [],
                "resolution_advice": ["Refresh the host-supplied authorized inventory."],
            }
        ]
    return details


def select_plan(
    request: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    cost: AttemptCost | None = None,
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if policy is not None:
        request = dict(request) | {
            "versions": dict(request["versions"], policy_revision=policy["policy_revision"])
        }
    constraints = request["hard_constraints"]
    objective = request["optimization_objective"]
    exclusions: list[dict[str, Any]] = []
    feasible: list[Mapping[str, Any]] = []
    cap = constraints["spending_ceiling"]
    for row in candidates:
        reasons = list(row.get("exclusion_reasons", []))
        estimate = row.get("cost", cost) or AttemptCost(None, None, None, "USD", "unknown")
        execution_limits = row.get("execution_token_limits")
        requested_limits = constraints.get("execution_token_limits")
        if requested_limits is not None and (
            execution_limits is None
            or any(execution_limits[key] > requested_limits[key] for key in requested_limits)
        ):
            reasons.append("execution_token_limits")
        rates = row.get("rates")
        bound = (
            estimate_attempt_cost(
                execution_limits["input_tokens"],
                execution_limits["output_tokens"],
                rates["input_rate"],
                rates["output_rate"],
                rates["currency"],
                rates["revision"],
            )
            if execution_limits is not None and rates is not None
            else AttemptCost(None, None, None, "USD", "unknown")
        )
        if not row.get("available", False):
            reasons.append("unavailable")
        if constraints["local_only"] and not row["local"]:
            reasons.append("local_only")
        if (
            constraints["allowed_providers"]
            and row["provider"] not in constraints["allowed_providers"]
        ):
            reasons.append("provider_not_allowed")
        if row.get("quality_sufficient") is not True:
            reasons.append("quality_unknown_or_insufficient")
        requirements = {value["requirement_id"] for value in objective["acceptance_requirements"]}
        if not requirements <= set(row.get("satisfied_requirements", [])):
            reasons.append("acceptance_unproven")
        if row.get("completion_time_ms") is None:
            reasons.append("completion_time_unknown")
        if (
            row.get("completion_time_limit_ms") is not None
            and row["completion_time_ms"] is not None
            and row["completion_time_ms"] > row["completion_time_limit_ms"]
        ):
            reasons.append("completion_time_limit")
        if cap is not None and (
            bound.raw is None
            or bound.currency != cap["currency"]
            or bound.raw > Decimal(cap["amount"])
        ):
            reasons.append("cost_cap")
        if objective["routing_cost_basis"] == "adjusted" and estimate.adjusted is None:
            reasons.append("adjustment_unknown")
        if row.get("native_effort", {}).get("kind") == "unsupported":
            reasons.append("unsupported_effort")
        retry = request["retry_context"]
        if retry and (
            retry["remaining_attempts"] <= 0
            or retry["remaining_time_ms"] <= 0
            or retry["failure_class"] not in row.get("addresses_failures", [])
        ):
            reasons.append("retry_does_not_address_failure")
        if (
            retry
            and retry["remaining_spend"] is not None
            and (
                bound.raw is None
                or bound.currency != retry["remaining_spend"]["currency"]
                or bound.raw > Decimal(retry["remaining_spend"]["amount"])
            )
        ):
            reasons.append("retry_spend")
        if reasons:
            exclusions.append(
                {"candidate_id": row["candidate_id"], "reasons": sorted(set(reasons))}
            )
        else:
            feasible.append(dict(row) | {"cost": estimate})
    exclusions.sort(key=lambda row: row["candidate_id"])
    details = decision_details(request, exclusions)
    if (
        objective["metric_id"]
        not in {"raw_token_cost", "adjusted_token_cost", "token_cost", "completion_time_ms"}
        or objective["direction"] != "minimize"
    ):
        return {
            "status": "constraint_conflict",
            "details": details,
            "conflicting_requirements": ["unsupported objective"],
        }
    if not feasible:
        return {"status": "no_compatible_plan", "details": details}
    currencies = {row["cost"].currency for row in feasible if row["cost"].raw is not None}
    order = (
        {}
        if policy is None
        else {
            row["candidate_id"]: (index, row["candidate_fingerprint"])
            for index, row in enumerate(policy["candidate_order"])
        }
    )
    if any(
        row["candidate_id"] in order and candidate_fingerprint(row) != order[row["candidate_id"]][1]
        for row in feasible
    ):
        return {
            "status": "routing_failed",
            "details": details,
            "error_code": "policy_candidate_changed",
            "retryable": True,
        }

    def rank(row: Mapping[str, Any]) -> tuple[Any, ...]:
        estimate = (
            row["cost"].adjusted
            if objective["routing_cost_basis"] == "adjusted"
            else row["cost"].raw
        )
        comparable = estimate is not None and len(currencies) == 1
        metric = (
            row["completion_time_ms"]
            if objective["metric_id"] == "completion_time_ms"
            else estimate
            if comparable
            else Decimal(0)
        )
        return (
            order.get(row["candidate_id"], (len(order), ""))[0],
            0 if row["evidence_strength"] == "measured" else 1,
            0 if comparable else 1,
            metric,
            not row.get("default", False),
            row["model_id"],
            row["candidate_id"],
        )

    ranked = sorted(feasible, key=rank)
    selected = ranked[0]
    details = decision_details(request, exclusions, selected["cost"])
    details["alternatives"] = [row["candidate_id"] for row in ranked[1:]]
    details["evidence_refs"] = list(selected["evidence_refs"])
    if policy is not None:
        details["evidence_refs"].append(policy["evidence_digest"])
        details["diagnostics"].append(
            {
                "code": "learned_policy_ordering",
                "summary": "Applied a verified candidate ordering.",
                "evidence_refs": [policy["evidence_digest"]],
                "resolution_advice": [],
            }
        )
    if len(currencies) > 1 or any(row["cost"].raw is None for row in feasible):
        details["close_calls"] = [
            {
                "candidate_ids": [row["candidate_id"] for row in ranked],
                "differing_dimensions": ["cost"],
                "uncertainty_reason": "unknown or incomparable currency; no cheapest claim",
                "evidence_refs": [],
            }
        ]
    plan_id = str(
        uuid.uuid5(
            uuid.UUID(request["envelope"]["request_id"]),
            canonical_digest({key: value for key, value in selected.items() if key != "cost"}),
        )
    )
    optional = selected.get("optional_guidance", [])
    plan = {
        "execution_plan_id": plan_id,
        "predecessor_plan_id": selected.get("predecessor_plan_id"),
        "model_id": selected["model_id"],
        "resolved_model_revision": selected["resolved_model_revision"],
        "provider": selected["provider"],
        "access_route": selected["access_route"],
        "native_effort": selected["native_effort"],
        "optional_guidance": optional,
        "required_guidance": selected.get("required_guidance", []),
        "guidance_action": "inject" if optional else "none",
        "required_capabilities": selected["required_capabilities"],
        "harness_id": request["envelope"]["harness_id"],
        "execution_target_id": request["envelope"]["execution_target_id"],
    }
    return {
        "status": "ready",
        "details": details,
        "execution_plan": plan,
        "fallback_used": selected.get("fallback_used", False),
        "readiness": {
            "verified_at": selected["verified_at"],
            "valid_until": selected["expires_at"],
            "inventory_revision": request["capabilities"]["inventory_revision"],
            "checked_capabilities": selected["effective_capabilities"],
            "evidence_refs": selected["evidence_refs"],
        },
    }
