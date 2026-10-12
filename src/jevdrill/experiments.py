"""Durable comparison proposals, deterministic priority and explicit cancellation."""

import copy
from collections.abc import Callable, Mapping
from datetime import datetime
from decimal import Decimal
from fractions import Fraction
from time import time
from typing import Any, Protocol
from uuid import uuid4

from .contracts import ContractError, canonical_digest, parse_contract
from .storage import SQLiteStorage


class ExperimentRunner(Protocol):
    """Trusted host adapter. Methods are bounded; start is never automatically retried.

    The host enforces the persisted deadline and limits, and cancellation creates
    a durable tombstone even if it arrives before start. Poll cannot start work.
    Readiness checks the actual context, plans, isolation and whole-run cost bound.
    """

    def prepare(self, experiment: Mapping[str, Any], deadline_ms: int) -> Mapping[str, Any]: ...
    def start(
        self, experiment: Mapping[str, Any], record: Mapping[str, Any]
    ) -> Mapping[str, Any]: ...
    def poll(self, record: Mapping[str, Any]) -> Mapping[str, Any]: ...
    def cancel(self, record: Mapping[str, Any]) -> Mapping[str, Any]: ...


ExperimentAuthority = Callable[[Mapping[str, str]], Mapping[str, Any] | None]
ExperimentSettings = Callable[[Mapping[str, str]], Mapping[str, Any]]
_TERMINAL = {"completed", "incomplete", "canceled"}
_HOST_CAPABILITIES = {
    "bounded_execution",
    "durable_dispatch",
    "cancel_before_start",
    "verified_cleanup",
    "shadow_side_effects_disabled",
}


def _expires(value: str) -> int:
    return int(datetime.fromisoformat(value).timestamp() * 1000)


def _money(value: Mapping[str, str] | None) -> int:
    if value is None or value["currency"] != "USD":
        raise ContractError("experiment_raw_usd_cap_required")
    # Rounding down a spending cap cannot grant an extra microdollar.
    return int(Decimal(value["amount"]) * 1_000_000)


class Experiments:
    def __init__(
        self,
        storage: SQLiteStorage,
        authority: ExperimentAuthority | None = None,
        runner: ExperimentRunner | None = None,
        clock: Callable[[], int] | None = None,
        settings: ExperimentSettings | None = None,
    ) -> None:
        self.storage = storage
        self.authority = authority
        self.runner = runner
        self.clock = clock or (lambda: int(time() * 1000))
        self.settings = settings

    def _authorization(
        self,
        scope: Mapping[str, str],
        experiment: Mapping[str, Any],
        background: bool,
        deadline: int,
    ) -> dict[str, Any]:
        source = self.authority(scope) if self.authority else None
        if source is None:
            raise ContractError("experiment_authority_unavailable")
        authority = parse_contract("ExperimentAuthorization", source).payload()
        if (
            self.settings is None
            or not parse_contract("Settings", self.settings(scope)).payload()["experiment_enabled"]
        ):
            raise ContractError("experiment_settings_disabled")
        if not authority["enabled"]:
            raise ContractError("experiment_disabled")
        if any(authority["scope"][key] != scope[key] for key in scope):
            raise ContractError("experiment_authority_scope_mismatch")
        if _expires(authority["expires_at"]) < deadline:
            raise ContractError("experiment_authority_expired")
        if experiment["task_id"] not in authority["task_ids"]:
            raise ContractError("experiment_task_not_authorized")
        if background and not authority["background_allowed"]:
            raise ContractError("experiment_background_not_authorized")
        if experiment["execution_path"] not in authority["allowed_execution_paths"]:
            raise ContractError("experiment_execution_path_not_authorized")
        if experiment["isolation_ref"] not in authority["allowed_isolation_refs"]:
            raise ContractError("experiment_isolation_not_authorized")
        for plan in experiment["candidate_plans"]:
            if (
                plan["provider"] not in authority["allowed_providers"]
                or plan["harness_id"] not in authority["allowed_harnesses"]
            ):
                raise ContractError("experiment_candidate_not_authorized")
            if not plan["resolved_model_revision"]:
                raise ContractError("experiment_model_revision_required")
        for key in (
            "max_candidates",
            "max_concurrency",
            "max_duration_ms",
            "cpu_limit",
            "memory_limit_bytes",
        ):
            if experiment["limits"][key] > authority["limits"][key]:
                raise ContractError("experiment_limit_exceeds_authority")
        return dict(authority)

    def _readiness(
        self,
        experiment: Mapping[str, Any],
        authority: Mapping[str, Any],
        deadline: int,
    ) -> dict[str, Any]:
        if self.runner is None:
            raise ContractError("experiment_runner_unavailable")
        ready = parse_contract(
            "ExperimentReadiness", self.runner.prepare(copy.deepcopy(experiment), deadline)
        ).payload()
        if _expires(ready["expires_at"]) < deadline:
            raise ContractError("experiment_readiness_expired")
        if not ready["context_available"] or ready["context_hash"] != experiment["context_hash"]:
            raise ContractError("experiment_context_unavailable")
        if authority["local_only"] and not ready["local_execution"]:
            raise ContractError("experiment_local_execution_required")
        if ready["isolation_ref"] != experiment["isolation_ref"]:
            raise ContractError("experiment_isolation_mismatch")
        plans = experiment["candidate_plans"]
        if ready["candidate_plan_digests"] != [canonical_digest(p) for p in plans] or any(
            p["harness_id"] != ready["harness_id"]
            or p["execution_target_id"] != ready["execution_target_id"]
            for p in plans
        ):
            raise ContractError("experiment_plan_binding_mismatch")
        required = set(_HOST_CAPABILITIES)
        if experiment["execution_path"] == "internal":
            required.update({"restricted_container", "network_disabled"})
        for plan in plans:
            required.update(plan["required_capabilities"])
        if not required <= set(ready["declared_capabilities"]) & set(ready["runtime_capabilities"]):
            raise ContractError("experiment_capability_mismatch")
        limits = experiment["limits"]
        if (
            ready["available_cpu"] < limits["cpu_limit"]
            or ready["available_memory_bytes"] < limits["memory_limit_bytes"]
            or ready["max_concurrency"] < 1
        ):
            raise ContractError("experiment_resources_unavailable")
        if not ready["spend_bound_verified"]:
            raise ContractError("experiment_spend_bound_unverified")
        if ready["upper_cost_microusd"] > min(
            _money(limits["per_experiment_spend"]),
            _money(authority["limits"]["per_experiment_spend"]),
        ):
            raise ContractError("experiment_cost_exceeds_limit")
        return dict(ready)

    @staticmethod
    def _result(job: Mapping[str, Any] | None, *reasons: str) -> dict[str, Any]:
        return dict(
            parse_contract(
                "ExperimentExecutionResult",
                {
                    "schema_version": "1",
                    "status": "denied" if reasons else "recorded" if job else "not_found",
                    "reasons": list(reasons),
                    "record": job["record"] if job else None,
                },
            ).payload()
        )

    def execute(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        request = parse_contract("ExperimentExecutionRequest", payload).payload()
        scope, identity = request["scope"], request["comparison_experiment_id"]
        job = self.storage.experiment_execution(scope, identity)
        if request["action"] == "inspect":
            return self._result(job)
        if request["action"] == "cancel":
            self.storage.cancel_experiment_execution(scope, identity)
            job = self.storage.experiment_execution(scope, identity)
        if job:
            if request["action"] == "admit" or job["record"]["execution_status"] in _TERMINAL:
                return self._result(job)
            return self._advance(scope, identity, job)
        if request["action"] != "admit":
            return self._result(None)
        experiment = self.storage.experiment_proposal(scope, identity)
        if experiment is None:
            return self._result(None)
        try:
            if experiment["experiment_state"] != "proposed":
                raise ContractError("experiment_not_proposed")
            if self.storage.experiment_recovery_blocked(scope):
                raise ContractError("experiment_recovery_authority_unreconciled")
            now = self.clock()
            deadline = now + experiment["limits"]["max_duration_ms"]
            authority = self._authorization(scope, experiment, request["background"], deadline)
            ready = self._readiness(experiment, authority, deadline)
            record = {
                "comparison_experiment_id": identity,
                "task_id": experiment["task_id"],
                "experiment_digest": canonical_digest(experiment),
                "authorization_revision": authority["authorization_revision"],
                "authorization_digest": canonical_digest(authority),
                "dispatch_token": str(uuid4()),
                "harness_id": ready["harness_id"],
                "reserved_microusd": ready["upper_cost_microusd"],
                "admitted_at_ms": now,
                "observed_at_ms": now,
                "deadline_ms": deadline,
                "execution_status": "accepted",
                "receipt": None,
            }
            job = {
                "record": record,
                "experiment": experiment,
                "background": request["background"],
                "receipts": [],
            }
            self._result(job)  # Check the persisted public record before reserving.
            job = self.storage.admit_experiment(
                scope,
                job,
                min(
                    _money(authority["limits"]["daily_spend"]),
                    _money(experiment["limits"]["daily_spend"]),
                ),
                authority["total_spend_microusd"],
                min(experiment["limits"]["max_concurrency"], ready["max_concurrency"]),
            )
            return self._result(job)
        except ContractError as error:
            return self._result(None, str(error))
        except OSError:
            return self._result(None, "experiment_host_unavailable")

    def authorize_dispatch(self, scope: Mapping[str, str], record: Mapping[str, Any]) -> bool:
        """Recheck persisted authority for a queued worker and each subsequent call."""
        job = self.storage.experiment_execution(scope, record["comparison_experiment_id"])
        if job is None or job["experiment"] is None:
            return False
        current = job["record"]
        if (
            current["execution_status"] != "running"
            or any(
                current[key] != record[key]
                for key in (
                    "dispatch_token",
                    "experiment_digest",
                    "authorization_digest",
                    "deadline_ms",
                    "reserved_microusd",
                    "task_id",
                    "harness_id",
                )
            )
            or not current["observed_at_ms"] <= self.clock() < current["deadline_ms"]
            or self.storage.is_deleted(scope, current["task_id"])
            or not self.storage.experiment_context_current(
                scope, current["comparison_experiment_id"]
            )
        ):
            return False
        try:
            authority = self._authorization(
                scope, job["experiment"], job["background"], current["deadline_ms"]
            )
            return bool(canonical_digest(authority) == current["authorization_digest"])
        except (ContractError, OSError):
            return False

    def _advance(
        self, scope: Mapping[str, str], identity: str, job: dict[str, Any]
    ) -> dict[str, Any]:
        record, experiment = job["record"], job["experiment"]
        reasons: list[str] = []
        following = copy.deepcopy(job)
        now = self.clock()
        if record["execution_status"] != "cancel_pending":
            try:
                if now < record["observed_at_ms"] or now >= record["deadline_ms"]:
                    raise ContractError("experiment_deadline_or_clock_invalid")
                if experiment is None or self.storage.is_deleted(scope, record["task_id"]):
                    raise ContractError("experiment_context_deleted")
                if not self.storage.experiment_context_current(scope, identity):
                    raise ContractError("experiment_context_changed")
                authority = self._authorization(
                    scope, experiment, job["background"], record["deadline_ms"]
                )
                if canonical_digest(authority) != record["authorization_digest"]:
                    raise ContractError("experiment_authority_changed")
                if record["execution_status"] == "accepted":
                    ready = self._readiness(experiment, authority, record["deadline_ms"])
                    if ready["upper_cost_microusd"] > record["reserved_microusd"]:
                        raise ContractError("experiment_cost_bound_increased")
                    following["record"]["execution_status"] = "running"
            except (ContractError, OSError) as error:
                reasons.append(
                    str(error)
                    if isinstance(error, ContractError)
                    else "experiment_host_unavailable"
                )
                following["record"]["execution_status"] = "cancel_pending"
        following["record"]["observed_at_ms"] = max(now, record["observed_at_ms"])
        if not self.storage.update_experiment_execution(scope, identity, job, following):
            return self._result(
                self.storage.experiment_execution(scope, identity), "experiment_concurrent_update"
            )
        if self.runner is None:
            return self._result(following, "experiment_runner_unavailable")
        try:
            if following["record"]["execution_status"] == "cancel_pending":
                receipt = self.runner.cancel(copy.deepcopy(record))
            elif record["execution_status"] == "accepted":
                assert experiment is not None
                receipt = self.runner.start(copy.deepcopy(experiment), copy.deepcopy(record))
            else:
                receipt = self.runner.poll(copy.deepcopy(record))
            return self._receipt(scope, identity, following, receipt, reasons)
        except ContractError:
            return self._result(
                self.storage.experiment_execution(scope, identity), "experiment_receipt_invalid"
            )
        except OSError:
            # Dispatch may already have happened. A restart must poll, never retry start.
            return self._result(
                self.storage.experiment_execution(scope, identity), "experiment_host_unavailable"
            )

    def _receipt(
        self,
        scope: Mapping[str, str],
        identity: str,
        job: dict[str, Any],
        payload: Mapping[str, Any],
        reasons: list[str],
    ) -> dict[str, Any]:
        receipt = parse_contract("ExperimentHostReceipt", payload).payload()
        record, experiment = job["record"], job["experiment"]
        if any(receipt[key] != record[key] for key in ("dispatch_token", "experiment_digest")):
            raise ContractError("receipt binding mismatch")
        if receipt["host_status"] in {"absent", "running"} and (
            receipt["cleanup_verified"]
            or receipt["candidates"]
            or receipt["preferred_plan_id"] is not None
        ):
            raise ContractError("nonterminal receipt contains final results")
        if (receipt["preferred_plan_id"] is None) != (receipt["preference_reason"] is None):
            raise ContractError("incomplete host preference")
        if experiment is not None:
            known = {p["execution_plan_id"] for p in experiment["candidate_plans"]}
            seen = [r["execution_plan_id"] for r in receipt["candidates"]]
            if (
                len(seen) != len(set(seen))
                or not set(seen) <= known
                or (
                    receipt["preferred_plan_id"] is not None
                    and receipt["preferred_plan_id"] not in known
                )
            ):
                raise ContractError("unknown or duplicate candidate")
            for result in receipt["candidates"]:
                if any(
                    result[key] != experiment[key] for key in ("evaluator_ref", "rubric_revision")
                ):
                    raise ContractError("evaluator binding mismatch")
            if receipt["host_status"] == "completed" and (
                set(seen) != known or any(r["status"] != "completed" for r in receipt["candidates"])
            ):
                raise ContractError("incomplete candidate coverage")
        following = copy.deepcopy(job)
        # Deleted tasks retain only cancellation/budget metadata, never late outcomes.
        following["record"]["receipt"] = receipt if experiment is not None else None
        if experiment is not None and receipt not in following["receipts"]:
            following["receipts"].append(receipt)
        if receipt["cleanup_verified"]:
            following["record"]["execution_status"] = (
                "canceled"
                if record["execution_status"] == "cancel_pending"
                else "completed"
                if receipt["host_status"] == "completed"
                else "incomplete"
            )
        elif receipt["host_status"] != "running":
            following["record"]["execution_status"] = "cancel_pending"
        if not self.storage.update_experiment_execution(scope, identity, job, following):
            return self._result(
                self.storage.experiment_execution(scope, identity), "experiment_concurrent_update"
            )
        return self._result(following, *reasons)

    def handle(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        request = parse_contract("ExperimentRequest", payload).payload()
        action, proposal = request["action"], request["proposal"]
        identity = request["comparison_experiment_id"]
        if action == "propose":
            if proposal is None or identity is not None:
                raise ContractError("proposal required without a selected experiment")
            experiment = proposal["experiment"]
            if experiment["experiment_state"] != "proposed":
                raise ContractError("new experiment must be proposed")
            if experiment["authorization_revision"] is not None or experiment["host_accepted"]:
                raise ContractError("a proposal cannot declare execution authority")
        elif proposal is not None or (action == "cancel") != (identity is not None):
            raise ContractError("invalid experiment action fields")
        result = self.storage.experiment_queue(request, canonical_digest(request))
        ranked = []
        for row in result["experiments"]:
            proposal = row["proposal"]
            cost = proposal["estimated_cost_microusd"]
            score = Fraction(
                row["occurrence_count"] * proposal["uncertainty_rank"] * proposal["benefit_rank"],
                1 + cost if cost is not None else 1,
            )
            row["priority_revision"] = "recurrence-benefit-cost-v1"
            row["priority_score"] = str(score)
            ranked.append(
                (cost is None, -score, proposal["experiment"]["comparison_experiment_id"], row)
            )
        result["experiments"] = [row for _, _, _, row in sorted(ranked)]
        result["schema_version"] = "1"
        result["execution_authorized"] = False
        return dict(parse_contract("ExperimentResult", result).payload())
