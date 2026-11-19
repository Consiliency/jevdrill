import copy
import json
from pathlib import Path
from uuid import uuid4

import pytest

from jevdrill.experiments import Experiments
from jevdrill.settings import resolve_settings
from tests.analysis.test_observations import case
from tests.experiments.test_execution import setup as setup  # noqa: PLC0414


@pytest.mark.parametrize("field", ["producer", "operation", "project_id", "workspace_id"])
def test_all_grant_scope_fields_bind_admission(setup, field):
    service, request, authority, host, _, _ = setup
    authority["scope"] = dict(
        authority["scope"], **{field: "report" if field == "operation" else str(uuid4())}
    )
    assert service.execute(request)["reasons"] == ["experiment_authority_scope_mismatch"]
    assert host.starts == 0


def test_resolved_settings_disable_even_an_enabled_grant(setup):
    service, request, _, host, _, _ = setup
    service.settings = lambda _: resolve_settings(
        [("user", {"experiment_enabled": False}), ("request", {"experiment_enabled": True})]
    )
    assert service.execute(request)["reasons"] == ["experiment_settings_disabled"]
    assert host.starts == 0


def test_settings_opt_out_after_admission_prevents_dispatch(setup):
    service, request, _, host, _, _ = setup
    reservation = service.execute(request)["record"]["reserved_microusd"]
    service.settings = lambda _: resolve_settings([])
    result = service.execute(request | {"action": "advance"})
    assert result["record"]["execution_status"] == "canceled"
    assert result["record"]["reserved_microusd"] == reservation
    assert host.starts == 0


def test_unregistered_task_cannot_populate_proposal_content_or_recurrence(setup):
    service, request, _authority, host, _, proposal = setup
    changed = copy.deepcopy(proposal)
    task, identity = str(uuid4()), str(uuid4())
    changed["proposal"]["experiment"].update(
        task_id=task, comparison_experiment_id=identity, context_hash="unregistered"
    )
    changed["idempotency_key"] = str(uuid4())
    from jevdrill.contracts import ContractError

    with pytest.raises(ContractError):
        service.handle(changed)
    assert service.storage.experiment_proposal(request["scope"], identity) is None
    assert host.starts == 0


def test_changed_authoritative_source_invalidates_context(setup):
    service, request, _, host, _, proposal = setup
    service.execute(request)
    from tests.experiments.test_execution import seed_task

    seed_task(service.storage, request["scope"], proposal["proposal"]["experiment"]["task_id"])
    assert service.execute(request | {"action": "advance"})["reasons"] == [
        "experiment_context_changed"
    ]
    assert host.starts == 0


def test_opted_out_equivalent_recurrence_cannot_increase_priority(setup):
    service, _, _, _, _, proposal = setup
    task = proposal["proposal"]["experiment"]["task_id"]
    service.storage.restrict_learning(proposal["scope"], task, False)
    changed = copy.deepcopy(proposal)
    changed["idempotency_key"] = str(uuid4())
    changed["proposal"]["experiment"]["comparison_experiment_id"] = str(uuid4())
    from jevdrill.contracts import ContractError

    with pytest.raises(ContractError):
        service.handle(changed)
    inspected = service.handle(
        proposal | {"action": "inspect", "proposal": None, "idempotency_key": str(uuid4())}
    )
    assert inspected["experiments"][0]["occurrence_count"] == 1


def test_cross_producer_objective_delete_denies_existing_proposal(tmp_path, discovery_inputs):
    app, scope, context, _ = case(tmp_path, discovery_inputs)
    from tests.experiments.test_execution import Host, enabled_settings

    rows = json.loads((Path(__file__).parents[1] / "contracts/fixtures/boundary.json").read_text())
    experiment = copy.deepcopy(
        next(
            row["payload"]
            for row in rows
            if row["contract"] == "ComparisonExperiment" and row["accepted"]
        )
    )
    experiment["task_id"] = context["task_id"]
    payload = {
        "schema_version": "1",
        "scope": scope,
        "idempotency_key": str(uuid4()),
        "action": "propose",
        "comparison_experiment_id": None,
        "proposal": {
            "experiment": experiment,
            "task_group": "fixture",
            "uncertainty_rank": 1,
            "benefit_rank": 1,
            "estimated_cost_microusd": None,
        },
    }
    service = Experiments(app.storage, settings=enabled_settings, runner=Host())
    service.handle(payload)
    identity = payload["proposal"]["experiment"]["comparison_experiment_id"]
    assert app.storage.experiment_context_current(scope, identity)
    app.storage.delete_discovery(
        dict(scope, operation="discover", producer="other"),
        context["discovery_ref"]["work_objective_id"],
    )
    assert not app.storage.experiment_context_current(scope, identity)
    assert app.storage.load_replay(scope, context["routing_decision_id"]) is not None
