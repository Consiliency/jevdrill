"""Learning privacy at real application and SQLite boundaries."""

import copy
import json
from pathlib import Path
from uuid import uuid4

import pytest

from jevdrill.application import Application
from jevdrill.contracts import ContractError
from jevdrill.storage import SQLiteStorage
from tests.analysis.test_observations import case
from tests.application.test_learning import analysis_request

MARKER = "INERT_R41_LEARNING_VALUE"
FIXTURES = Path(__file__).parents[1] / "contracts/fixtures"


def test_analysis_objective_description_is_sanitized_before_retention(tmp_path):
    app, scope, _context, decision = case(tmp_path)
    request = analysis_request(scope)
    objective = copy.deepcopy(decision["details"]["optimization_objective"])
    objective["acceptance_requirements"] = [
        {
            "description": "password: " + MARKER,
            "evaluator_ref": "checks-v1",
            "requirement_id": "requirement-one",
            "source": "user",
        }
    ]
    request["objectives"] = [objective]
    response = app.analyze(request)
    assert response["status"] == "updated"
    assert MARKER not in json.dumps(response)
    assert MARKER not in json.dumps(app.storage.objective_versions(scope))
    assert MARKER not in json.dumps(app.storage.latest_evidence(scope))


def test_report_sensitive_map_key_rejects_before_persistence(tmp_path):
    app, _scope, context, _ = case(tmp_path)
    envelope = json.loads((FIXTURES / "route-application.json").read_text())[0]["payload"][
        "request"
    ]["envelope"]
    envelope.update(operation="report", request_id=str(uuid4()), idempotency_key=str(uuid4()))
    event = {
        "schema_version": "1",
        "event_id": str(uuid4()),
        "task_id": context["task_id"],
        "routing_decision_id": context["routing_decision_id"],
        "execution_run_id": str(uuid4()),
        "source_id": "synthetic-host",
        "source_sequence": 1,
        "occurred_at": "2026-10-09T00:00:00Z",
        "supersedes_event_id": None,
        "payload": {
            "kind": "evaluation",
            "evaluator_ref": "checks-v1",
            "rubric_revision": "v1",
            "check_results": {"password: " + MARKER: True},
            "measurements": [],
        },
    }
    with pytest.raises(ContractError):
        app.report({"envelope": envelope, "event": event})
    with app.storage._connect() as conn:
        assert conn.execute("SELECT count(*) FROM events_v1").fetchone()[0] == 0


def test_route_optout_survives_failure_immediately_after_commit(tmp_path, monkeypatch):
    app = Application(SQLiteStorage(tmp_path / "route.db"))
    payload = json.loads((FIXTURES / "route-application.json").read_text())[0]["payload"]
    payload["settings_layers"] = [
        {"source": "request", "values": {"local_analysis_enabled": False}}
    ]
    original = app.storage.commit_decision

    def committed_then_crashed(*args, **kwargs):
        original(*args, **kwargs)
        raise TimeoutError("injected after durable commit")

    monkeypatch.setattr(app.storage, "commit_decision", committed_then_crashed)
    with pytest.raises(TimeoutError, match="injected"):
        app.route(payload)
    monkeypatch.setattr(app.storage, "commit_decision", original)
    assert app.route(payload)["status"] == "ready"
    app.storage.deadline = None
    with app.storage._connect() as conn:
        row = conn.execute(
            "SELECT enabled FROM task_learning_policy WHERE task=?",
            (payload["request"]["task_id"],),
        ).fetchone()
        assert row == (0,)


@pytest.mark.parametrize("legacy", (False, True))
def test_second_objective_for_same_task_invalidates_learning(tmp_path, discovery_inputs, legacy):
    app, scope, context, _ = case(tmp_path, discovery_inputs)
    second = copy.deepcopy(discovery_inputs)
    second["catalog"]["resources"] = []
    second["descriptions"] = []
    second["work_objective_id"] = str(uuid4())
    second["envelope"].update(request_id=str(uuid4()), idempotency_key=str(uuid4()))
    found = app.discover(second)
    linkage = {
        key: found["details"][key] for key in ("discovery_id", "work_objective_id", "trace_digest")
    }
    payload = json.loads((FIXTURES / "route-application.json").read_text())[0]["payload"]
    payload["request"]["active_guidance"] = []
    payload["inventory"]["candidates"][0]["guidance_options"] = []
    payload["request"]["task_id"] = context["task_id"]
    payload["request"]["envelope"].update(
        project_id=scope["project_id"],
        workspace_id=scope["workspace_id"],
        harness_id=scope["producer"],
        request_id=str(uuid4()),
        idempotency_key=str(uuid4()),
    )
    payload["request"]["hard_constraints"] = second["hard_constraints"]
    payload["catalog"] = second["catalog"]
    payload["settings_layers"] = [{"source": "request", "values": {"local_analysis_enabled": True}}]
    decision = app.route({"schema_version": "2", "route_inputs": payload, "discovery_ref": linkage})
    assert decision["status"] == "ready"
    app.storage.deadline = None
    app.storage.record_learning_context(
        scope,
        dict(
            context,
            routing_decision_id=decision["details"]["routing_decision_id"],
            discovery_ref=linkage,
        ),
    )
    assert app.analyze(analysis_request(scope))["status"] == "updated"
    assert app.storage.latest_evidence(scope) is not None
    with app.storage._connect(True) as conn:
        assert conn.execute("SELECT count(*) FROM learning_dependencies").fetchone()[0] == 2
        if legacy:
            conn.execute("ALTER TABLE learning_dependencies RENAME TO modern_dependencies")
            conn.execute(
                "CREATE TABLE learning_dependencies (scope TEXT, revision TEXT, source_scope TEXT, task TEXT, objective TEXT, PRIMARY KEY(scope,revision,source_scope,task))"
            )
            conn.execute(
                "INSERT INTO learning_dependencies SELECT * FROM modern_dependencies WHERE objective=?",
                (context["discovery_ref"]["work_objective_id"],),
            )
            conn.execute("DROP TABLE modern_dependencies")
            conn.execute("PRAGMA user_version = 3")
    if legacy:
        app.storage = SQLiteStorage(app.storage.path)
        with app.storage._connect() as conn:
            assert conn.execute("PRAGMA user_version").fetchone()[0] == 4
            assert conn.execute("SELECT count(*) FROM learning_dependencies").fetchone()[0] == 1
    app.storage.delete_discovery(dict(scope, operation="discover"), linkage["work_objective_id"])
    assert app.storage.latest_evidence(scope) is None
