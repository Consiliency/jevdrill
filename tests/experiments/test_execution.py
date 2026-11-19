import copy
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest

from jevdrill.contracts import canonical_digest
from jevdrill.experiments import Experiments
from jevdrill.settings import resolve_settings
from jevdrill.storage import SQLiteStorage


def enabled_settings(scope):
    return resolve_settings([("product", {"experiment_enabled": True})])


def seed_task(store, scope, task):
    rows = json.loads((Path(__file__).parents[1] / "contracts/fixtures/boundary.json").read_text())
    decision = copy.deepcopy(
        next(
            r["payload"]
            for r in rows
            if r["contract"] == "RoutingDecision"
            and r["accepted"]
            and r["payload"]["status"] == "ready"
        )
    )
    identity = str(uuid4())
    decision["details"].update(task_id=task, routing_decision_id=identity)
    bundle = {"task_id": task, "routing_decision_id": identity, "decision": decision}
    store.commit_decision(scope, str(uuid4()), canonical_digest(bundle), bundle)


class Host:
    def __init__(self):
        self.starts = 0
        self.cancels = 0
        self.receipt = None
        self.lost_ack = False
        self.cleaned = True
        self.readiness_change = {}
        self.on_start = lambda: None

    def prepare(self, experiment, deadline_ms):
        capabilities = [
            "bounded_execution",
            "durable_dispatch",
            "cancel_before_start",
            "verified_cleanup",
            "restricted_container",
            "network_disabled",
            "shadow_side_effects_disabled",
        ]
        return {
            "schema_version": "1",
            "harness_id": "fixture",
            "execution_target_id": "fixture",
            "context_hash": experiment["context_hash"],
            "context_available": True,
            "local_execution": True,
            "isolation_ref": "fixture",
            "declared_capabilities": capabilities,
            "runtime_capabilities": capabilities,
            "candidate_plan_digests": [canonical_digest(p) for p in experiment["candidate_plans"]],
            "spend_bound_verified": True,
            "upper_cost_microusd": 600_000,
            "available_cpu": 2,
            "available_memory_bytes": 2 * 1024**3,
            "max_concurrency": 1,
            "expires_at": "2099-01-01T00:00:00Z",
        } | self.readiness_change

    def start(self, experiment, record):
        self.on_start()
        self.starts += 1
        if self.receipt is None:
            self.receipt = {
                "schema_version": "1",
                "dispatch_token": record["dispatch_token"],
                "experiment_digest": record["experiment_digest"],
                "host_status": "running",
                "cleanup_verified": False,
                "candidates": [],
                "preferred_plan_id": None,
                "preference_reason": None,
            }
        if self.lost_ack:
            raise OSError("lost acknowledgment")
        return copy.deepcopy(self.receipt)

    def poll(self, record):
        if self.receipt is None:
            return {
                "schema_version": "1",
                "dispatch_token": record["dispatch_token"],
                "experiment_digest": record["experiment_digest"],
                "host_status": "absent",
                "cleanup_verified": False,
                "candidates": [],
                "preferred_plan_id": None,
                "preference_reason": None,
            }
        return copy.deepcopy(self.receipt)

    def cancel(self, record):
        self.cancels += 1
        self.receipt = {
            "schema_version": "1",
            "dispatch_token": record["dispatch_token"],
            "experiment_digest": record["experiment_digest"],
            "host_status": "canceled",
            "cleanup_verified": self.cleaned,
            "candidates": [],
            "preferred_plan_id": None,
            "preference_reason": None,
        }
        return copy.deepcopy(self.receipt)


@pytest.fixture
def setup(tmp_path):
    rows = json.loads((Path(__file__).parents[1] / "contracts/fixtures/boundary.json").read_text())
    experiment = copy.deepcopy(
        next(
            r["payload"] for r in rows if r["contract"] == "ComparisonExperiment" and r["accepted"]
        )
    )
    for plan in experiment["candidate_plans"]:
        plan["resolved_model_revision"] = "fixed-revision"
    experiment["limits"].update(
        max_duration_ms=120_000,
        cpu_limit=2,
        memory_limit_bytes=2 * 1024**3,
        per_experiment_spend={"amount": "1", "currency": "USD"},
        daily_spend={"amount": "5", "currency": "USD"},
    )
    scope = {
        "project_id": str(uuid4()),
        "workspace_id": str(uuid4()),
        "producer": "fixture",
        "operation": "route",
    }
    authority = {
        "schema_version": "1",
        "authorization_revision": "owner-v1",
        "scope": scope,
        "enabled": True,
        "task_ids": [experiment["task_id"]],
        "allowed_providers": ["fixture"],
        "allowed_harnesses": ["fixture"],
        "allowed_execution_paths": ["internal"],
        "allowed_isolation_refs": ["fixture"],
        "background_allowed": False,
        "local_only": True,
        "expires_at": "2099-01-01T00:00:00Z",
        "limits": copy.deepcopy(experiment["limits"]),
        "total_spend_microusd": 5_000_000,
    }
    store = SQLiteStorage(tmp_path / "db")
    seed_task(store, scope, experiment["task_id"])
    host, now = Host(), [1_000_000]
    service = Experiments(
        store, lambda _: authority, host, lambda: now[0], settings=enabled_settings
    )
    proposal = {
        "schema_version": "1",
        "scope": scope,
        "idempotency_key": str(uuid4()),
        "action": "propose",
        "comparison_experiment_id": None,
        "proposal": {
            "experiment": experiment,
            "task_group": "fixture",
            "uncertainty_rank": 2,
            "benefit_rank": 3,
            "estimated_cost_microusd": 1,
        },
    }
    service.handle(proposal)
    request = {
        "schema_version": "1",
        "scope": scope,
        "comparison_experiment_id": experiment["comparison_experiment_id"],
        "action": "admit",
        "background": False,
    }
    return service, request, authority, host, now, proposal


def advance(service, request):
    return service.execute(request | {"action": "advance"})


def test_portable_recovery_cannot_replenish_experiment_authority(setup, tmp_path):
    from jevdrill.application import Application

    service, request, authority, host, _, proposal = setup
    service.storage = SQLiteStorage(tmp_path / "original.db")
    value = json.loads(
        (Path(__file__).parents[1] / "contracts/fixtures/route-application.json").read_text()
    )[0]["payload"]
    value["request"]["task_id"] = proposal["proposal"]["experiment"]["task_id"]
    value["request"]["envelope"].update(
        project_id=request["scope"]["project_id"],
        workspace_id=request["scope"]["workspace_id"],
        harness_id=request["scope"]["producer"],
    )
    value["settings_layers"].append(
        {"source": "request", "values": {"local_analysis_enabled": True}}
    )
    assert Application(service.storage).route(value)["status"] == "ready"
    service.handle(proposal)
    authority["total_spend_microusd"] = 600_000
    service.execute(request)
    advance(service, request)
    assert host.starts == 1
    body = service.storage.export_recovery(request["scope"])
    restored = SQLiteStorage(tmp_path / "restored.db")
    restored.import_recovery(request["scope"], body, 100)
    recovered = Experiments(
        restored, lambda _: authority, host, lambda: 1_000_000, settings=enabled_settings
    )
    recovered.handle(proposal)
    denied = recovered.execute(request)
    assert denied["reasons"] == ["experiment_recovery_authority_unreconciled"]
    assert host.starts == 1
    assert SQLiteStorage(restored.path).experiment_recovery_blocked(request["scope"])
    assert not restored.experiment_recovery_blocked(request["scope"] | {"project_id": str(uuid4())})


def test_admission_reserves_whole_run_without_dispatch_and_retries_reuse(setup):
    service, request, _, host, _, _ = setup
    admitted = service.execute(request)
    assert admitted["record"]["reserved_microusd"] == 600_000
    assert host.starts == 0
    assert service.execute(request) == admitted
    assert advance(service, request)["record"]["execution_status"] == "running"
    assert advance(service, request)["record"]["execution_status"] == "running"
    assert host.starts == 1


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"enabled": False}, "disabled"),
        ({"expires_at": "1970-01-01T00:00:00Z"}, "expired"),
        ({"task_ids": []}, "task_not_authorized"),
        ({"allowed_providers": []}, "candidate_not_authorized"),
        ({"allowed_harnesses": []}, "candidate_not_authorized"),
        ({"allowed_execution_paths": []}, "execution_path_not_authorized"),
        ({"allowed_isolation_refs": []}, "isolation_not_authorized"),
        ({"total_spend_microusd": 1}, "budget_exhausted"),
    ],
)
def test_authority_denials_never_dispatch_or_reserve(setup, change, reason):
    service, request, authority, host, _, _ = setup
    authority.update(change)
    result = service.execute(request)
    assert result["status"] == "denied" and reason in result["reasons"][0]
    assert (
        service.storage.experiment_execution(request["scope"], request["comparison_experiment_id"])
        is None
    )
    assert host.starts == 0


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"context_available": False}, "context_unavailable"),
        ({"context_hash": "changed"}, "context_unavailable"),
        ({"local_execution": False}, "local_execution_required"),
        ({"runtime_capabilities": []}, "capability_mismatch"),
        ({"declared_capabilities": []}, "capability_mismatch"),
        ({"upper_cost_microusd": 1_000_001}, "cost_exceeds_limit"),
        ({"spend_bound_verified": False}, "spend_bound_unverified"),
        ({"available_cpu": 1}, "resources_unavailable"),
        ({"max_concurrency": 0}, "resources_unavailable"),
        ({"isolation_ref": "other"}, "isolation_mismatch"),
        ({"candidate_plan_digests": ["a" * 64, "b" * 64]}, "plan_binding_mismatch"),
    ],
)
def test_current_host_readiness_required(setup, change, reason):
    service, request, _, host, _, _ = setup
    host.readiness_change = change
    result = service.execute(request)
    assert result["status"] == "denied" and reason in result["reasons"][0]
    assert host.starts == 0


def test_default_has_no_authority_or_runner(setup):
    service, request, authority, _, _, _ = setup
    assert Experiments(service.storage).execute(request)["reasons"] == [
        "experiment_authority_unavailable"
    ]
    assert Experiments(service.storage, lambda _: authority, settings=enabled_settings).execute(
        request
    )["reasons"] == ["experiment_runner_unavailable"]


def test_lost_ack_restart_polls_without_redispatch(setup):
    service, request, authority, host, now, _ = setup
    service.execute(request)
    host.lost_ack = True
    assert advance(service, request)["reasons"] == ["experiment_host_unavailable"]
    resumed = Experiments(
        SQLiteStorage(service.storage.path),
        lambda _: authority,
        host,
        lambda: now[0],
        settings=enabled_settings,
    )
    assert advance(resumed, request)["record"]["execution_status"] == "running"
    assert host.starts == 1


@pytest.mark.parametrize("trigger", ["deadline", "clock", "authority", "context", "cost"])
def test_recheck_before_dispatch_cancels_safely(setup, trigger):
    service, request, authority, host, now, _ = setup
    service.execute(request)
    if trigger == "deadline":
        now[0] += 120_000
    if trigger == "clock":
        now[0] -= 1
    if trigger == "authority":
        authority["enabled"] = False
    if trigger == "context":
        host.readiness_change["context_available"] = False
    if trigger == "cost":
        host.readiness_change["upper_cost_microusd"] = 700_000
    result = advance(service, request)
    assert result["status"] == "denied"
    assert result["record"]["execution_status"] == "canceled"
    assert host.starts == 0 and host.cancels == 1


def test_cancellation_waits_for_cleanup_even_after_restart(setup):
    service, request, _, host, _, _ = setup
    service.execute(request)
    advance(service, request)
    host.cleaned = False
    result = service.execute(request | {"action": "cancel"})
    assert result["record"]["execution_status"] == "cancel_pending"
    host.cleaned = True
    assert advance(service, request)["record"]["execution_status"] == "canceled"
    assert host.starts == 1


def test_deletion_during_start_cannot_restore_content_or_accept_late_result(setup):
    service, request, _, host, _, proposal = setup
    service.execute(request)
    host.on_start = lambda: service.storage.delete_task(
        request["scope"], proposal["proposal"]["experiment"]["task_id"]
    )
    result = advance(service, request)
    assert result["record"]["execution_status"] == "cancel_pending"
    job = service.storage.experiment_execution(
        request["scope"], request["comparison_experiment_id"]
    )
    assert job["experiment"] is None and job["record"]["receipt"] is None
    assert advance(service, request)["record"]["execution_status"] == "canceled"


def test_concurrent_reservations_and_dispatch_claims(setup):
    service, request, _, host, _, proposal = setup
    another = copy.deepcopy(proposal)
    another["idempotency_key"] = str(uuid4())
    another["proposal"]["experiment"]["comparison_experiment_id"] = str(uuid4())
    another["proposal"]["experiment"]["context_hash"] = "other-context"
    service.handle(another)
    other_request = request | {
        "comparison_experiment_id": another["proposal"]["experiment"]["comparison_experiment_id"]
    }
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(service.execute, [request, other_request]))
    assert sorted(r["status"] for r in results) == ["denied", "recorded"]
    selected = request if results[0]["status"] == "recorded" else other_request
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: advance(service, selected), range(2)))
    assert host.starts == 1


def test_completed_receipt_keeps_preference_separate_and_checks_binding(setup):
    service, request, _, host, _, proposal = setup
    service.execute(request)
    advance(service, request)
    experiment = proposal["proposal"]["experiment"]
    host.receipt.update(
        host_status="completed",
        cleanup_verified=True,
        candidates=[
            {
                "execution_plan_id": p["execution_plan_id"],
                "status": "completed",
                "measurements": [],
                "acceptance_checks": {"correct": False},
                "evaluator_ref": experiment["evaluator_ref"],
                "rubric_revision": experiment["rubric_revision"],
            }
            for p in experiment["candidate_plans"]
        ],
        preferred_plan_id=experiment["candidate_plans"][0]["execution_plan_id"],
        preference_reason="host selected",
    )
    host.receipt["experiment_digest"] = "a" * 64
    assert advance(service, request)["reasons"] == ["experiment_receipt_invalid"]
    host.receipt["experiment_digest"] = canonical_digest(experiment)
    result = advance(service, request)
    assert result["record"]["execution_status"] == "completed"
    assert not result["record"]["receipt"]["candidates"][0]["acceptance_checks"]["correct"]
    assert result["record"]["reserved_microusd"] == 600_000


def test_spend_reservations_survive_deletion_and_daily_rollover(setup):
    service, request, authority, host, now, proposal = setup
    authority["total_spend_microusd"] = 600_000
    service.execute(request)
    service.execute(request | {"action": "cancel"})
    service.storage.delete_task(request["scope"], proposal["proposal"]["experiment"]["task_id"])
    another = copy.deepcopy(proposal)
    another["idempotency_key"] = str(uuid4())
    experiment = another["proposal"]["experiment"]
    experiment["comparison_experiment_id"] = str(uuid4())
    experiment["task_id"] = str(uuid4())
    seed_task(service.storage, request["scope"], experiment["task_id"])
    authority["task_ids"] = [experiment["task_id"]]
    authority["authorization_revision"] = "revised-owner-grant"
    now[0] += 86_400_000
    service.handle(another)
    result = service.execute(
        request | {"comparison_experiment_id": experiment["comparison_experiment_id"]}
    )
    assert result["reasons"] == ["experiment_budget_exhausted"]
    assert host.starts == 0


def test_absent_host_after_dispatch_checkpoint_is_canceled_without_retry(setup):
    service, request, _, host, _, _ = setup
    service.execute(request)
    job = service.storage.experiment_execution(
        request["scope"], request["comparison_experiment_id"]
    )
    dispatched = copy.deepcopy(job)
    dispatched["record"]["execution_status"] = "running"
    assert service.storage.update_experiment_execution(
        request["scope"], request["comparison_experiment_id"], job, dispatched
    )
    assert advance(service, request)["record"]["execution_status"] == "cancel_pending"
    assert advance(service, request)["record"]["execution_status"] == "canceled"
    assert host.starts == 0


def test_queue_cancel_reaches_running_execution(setup):
    service, request, _, host, _, proposal = setup
    service.execute(request)
    advance(service, request)
    service.handle(
        proposal
        | {
            "idempotency_key": str(uuid4()),
            "action": "cancel",
            "proposal": None,
            "comparison_experiment_id": request["comparison_experiment_id"],
        }
    )
    assert advance(service, request)["record"]["execution_status"] == "canceled"
    assert host.cancels == 1
