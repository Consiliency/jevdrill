import copy
import json
from pathlib import Path
from uuid import uuid4

import pytest

from jevdrill.application import Application
from jevdrill.contracts import ContractError, canonical_digest
from jevdrill.storage import SQLiteStorage
from tests.experiments.test_execution import seed_task


def test_recovered_learned_route_cannot_bypass_missing_policy_verification(tmp_path):
    payload = json.loads(
        (Path(__file__).parents[1] / "contracts/fixtures/route-application.json").read_text()
    )[0]["payload"]
    original = SQLiteStorage(tmp_path / "original")
    assert Application(original).route(payload)["status"] == "ready"
    envelope = payload["request"]["envelope"]
    scope = {
        "project_id": envelope["project_id"],
        "workspace_id": envelope["workspace_id"],
        "producer": envelope["harness_id"],
        "operation": "route",
    }
    digest = canonical_digest(payload)
    bundle = original.lookup_retry(scope, envelope["idempotency_key"], digest)["bundle"]
    bundle["decision"]["details"]["versions"]["policy_revision"] = "archived-policy"
    bundle["decision"]["details"]["diagnostics"].append(
        {
            "code": "learned_policy_ordering",
            "summary": "fixture",
            "evidence_refs": [],
            "resolution_advice": [],
        }
    )
    recovered = SQLiteStorage(tmp_path / "recovered")
    recovered.commit_decision(scope, envelope["idempotency_key"], digest, bundle)
    result = Application(recovered).route(payload)
    assert result["status"] == "routing_failed"
    assert result["error_code"] == "policy_verification_required"


def proposal():
    fixtures = json.loads(
        (Path(__file__).parents[1] / "contracts/fixtures/boundary.json").read_text()
    )
    experiment = copy.deepcopy(
        next(
            r["payload"]
            for r in fixtures
            if r["contract"] == "ComparisonExperiment" and r["accepted"]
        )
    )
    return {
        "schema_version": "1",
        "scope": {
            "project_id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "producer": "fixture",
            "operation": "route",
        },
        "idempotency_key": str(uuid4()),
        "action": "propose",
        "comparison_experiment_id": None,
        "proposal": {
            "experiment": experiment,
            "task_group": "fixture",
            "uncertainty_rank": 2,
            "benefit_rank": 3,
            "estimated_cost_microusd": 100,
        },
    }


def test_queue_survives_restart_deduplicates_and_counts_distinct_tasks(tmp_path):
    path = tmp_path / "db"
    app = Application(SQLiteStorage(path))
    request = proposal()
    seed_task(app.storage, request["scope"], request["proposal"]["experiment"]["task_id"])
    assert app.experiment(request)["status"] == "recorded"
    assert app.experiment(request)["status"] == "duplicate"
    request["idempotency_key"] = str(uuid4())
    assert app.experiment(request)["experiments"][0]["occurrence_count"] == 1
    request["idempotency_key"] = str(uuid4())
    request["proposal"]["experiment"]["task_id"] = str(uuid4())
    seed_task(app.storage, request["scope"], request["proposal"]["experiment"]["task_id"])
    request["proposal"]["experiment"]["comparison_experiment_id"] = str(uuid4())
    experiment = request["proposal"]["experiment"]
    probabilities = experiment["assignment_probabilities"]
    for plan in experiment["candidate_plans"]:
        old = plan["execution_plan_id"]
        plan["execution_plan_id"] = str(uuid4())
        if old in probabilities:
            probabilities[plan["execution_plan_id"]] = probabilities.pop(old)
        for guidance in plan["required_guidance"] + plan["optional_guidance"]:
            guidance["task_id"] = experiment["task_id"]
    result = Application(SQLiteStorage(path)).experiment(request)
    assert len(result["experiments"]) == 1
    assert result["experiments"][0]["occurrence_count"] == 2
    assert result["execution_authorized"] is False


def test_queue_idempotency_and_immutable_input_conflicts(tmp_path):
    app = Application(SQLiteStorage(tmp_path / "db"))
    request = proposal()
    seed_task(app.storage, request["scope"], request["proposal"]["experiment"]["task_id"])
    app.experiment(request)
    changed = copy.deepcopy(request)
    changed["proposal"]["experiment"]["rubric_revision"] = "changed"
    with pytest.raises(ContractError, match="idempotency conflict"):
        app.experiment(changed)
    changed["idempotency_key"] = str(uuid4())
    with pytest.raises(ContractError, match="identity conflict"):
        app.experiment(changed)


def test_queue_priority_and_scope_isolation(tmp_path):
    app = Application(SQLiteStorage(tmp_path / "db"))
    low = proposal()
    seed_task(app.storage, low["scope"], low["proposal"]["experiment"]["task_id"])
    app.experiment(low)
    high = copy.deepcopy(low)
    high["idempotency_key"] = str(uuid4())
    high["proposal"]["experiment"]["comparison_experiment_id"] = str(uuid4())
    high["proposal"]["estimated_cost_microusd"] = 1
    result = app.experiment(high)
    assert result["experiments"][0]["proposal"]["estimated_cost_microusd"] == 1
    high.update(action="inspect", proposal=None, idempotency_key=str(uuid4()))
    high["scope"]["workspace_id"] = str(uuid4())
    assert app.experiment(high)["experiments"] == []


def test_canceled_or_deleted_proposals_never_resurrect(tmp_path):
    app = Application(SQLiteStorage(tmp_path / "db"))
    request = proposal()
    seed_task(app.storage, request["scope"], request["proposal"]["experiment"]["task_id"])
    app.experiment(request)
    cancel = copy.deepcopy(request)
    cancel.update(
        action="cancel",
        proposal=None,
        idempotency_key=str(uuid4()),
        comparison_experiment_id=request["proposal"]["experiment"]["comparison_experiment_id"],
    )
    assert app.experiment(cancel)["status"] == "canceled"
    request["idempotency_key"] = str(uuid4())
    with pytest.raises(ContractError, match="terminal"):
        app.experiment(request)
    task = request["proposal"]["experiment"]["task_id"]
    app.delete_task(request["scope"], task)
    with pytest.raises(ContractError, match="deleted"):
        app.experiment(request)
    cancel.update(action="inspect", comparison_experiment_id=None, idempotency_key=str(uuid4()))
    assert app.experiment(cancel)["experiments"] == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("authorization_revision", "not-authority"),
        ("host_accepted", True),
        ("experiment_state", "running"),
    ],
)
def test_proposal_cannot_self_authorize(tmp_path, field, value):
    request = proposal()
    request["proposal"]["experiment"][field] = value
    with pytest.raises(ContractError):
        Application(SQLiteStorage(tmp_path / "db")).experiment(request)
