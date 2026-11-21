from uuid import uuid4

import pytest

from tests.experiments import test_execution as execution

setup = execution.setup
advance = execution.advance


def finish(service, request, host, proposal, host_status):
    service.execute(request)
    advance(service, request)
    experiment = proposal["proposal"]["experiment"]
    host.receipt.update(
        host_status=host_status,
        cleanup_verified=True,
        candidates=[
            {
                "execution_plan_id": plan["execution_plan_id"],
                "status": "completed",
                "measurements": [],
                "acceptance_checks": {"correct": True},
                "evaluator_ref": experiment["evaluator_ref"],
                "rubric_revision": experiment["rubric_revision"],
            }
            for plan in experiment["candidate_plans"]
        ]
        if host_status == "completed"
        else [],
    )
    return advance(service, request)


def stored(service, request):
    return service.storage.experiment_execution(
        request["scope"], request["comparison_experiment_id"]
    )


@pytest.mark.parametrize(
    "host_status,terminal", [("completed", "completed"), ("failed", "incomplete")]
)
@pytest.mark.parametrize("entry", ["execute", "handle"])
def test_cancel_leaves_a_finished_execution_and_its_receipt(setup, host_status, terminal, entry):
    service, request, _, host, _, proposal = setup
    finished = finish(service, request, host, proposal, host_status)
    assert finished["record"]["execution_status"] == terminal
    before = stored(service, request)
    if entry == "execute":
        assert service.execute(request | {"action": "cancel"})["record"] == finished["record"]
    else:
        service.handle(
            {
                "schema_version": "1",
                "scope": request["scope"],
                "idempotency_key": str(uuid4()),
                "action": "cancel",
                "comparison_experiment_id": request["comparison_experiment_id"],
                "proposal": None,
            }
        )
    assert stored(service, request) == before
    assert advance(service, request)["record"] == finished["record"]
    assert host.cancels == 0


def test_deletion_still_reopens_a_finished_execution_for_cleanup(setup):
    service, request, _, host, _, proposal = setup
    assert (
        finish(service, request, host, proposal, "completed")["record"]["execution_status"]
        == "completed"
    )
    service.storage.delete_task(request["scope"], proposal["proposal"]["experiment"]["task_id"])
    job = stored(service, request)
    assert job["record"]["execution_status"] == "cancel_pending"
    assert job["experiment"] is None and job["record"]["receipt"] is None and job["receipts"] == []
    assert advance(service, request)["record"]["execution_status"] == "canceled"
    assert host.cancels == 1
