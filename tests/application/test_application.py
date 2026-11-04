import copy
import json
import sqlite3
import uuid
from pathlib import Path

import pytest

from jevdrill.application import Application
from jevdrill.contracts import ContractError, parse_contract
from jevdrill.storage import SQLiteStorage

ROOT = Path(__file__).resolve().parents[2]


def fixture(identifier):
    rows = json.loads((ROOT / "tests/contracts/fixtures/boundary.json").read_text())
    return copy.deepcopy(next(row["payload"] for row in rows if row["id"] == identifier))


def route_request():
    return json.loads((ROOT / "tests/contracts/fixtures/route-application.json").read_text())[0][
        "payload"
    ]


def scope(request):
    envelope = request["request"]["envelope"]
    return {
        "project_id": envelope["project_id"],
        "workspace_id": envelope["workspace_id"],
        "producer": envelope["harness_id"],
        "operation": "route",
    }


def test_route_commits_before_ready_and_replays(tmp_path):
    request = route_request()
    app = Application(SQLiteStorage(tmp_path / "route.sqlite3"))
    response = app.route(request)
    assert response["status"] == "ready"
    assert app.replay(scope(request), response["details"]["routing_decision_id"]) == response


def test_report_is_a_versioned_durable_acknowledgment(tmp_path):
    app = Application(SQLiteStorage(tmp_path / "route.sqlite3"))
    response = app.report(fixture("ReportRequest-0"))
    assert response["status"] == "accepted"
    parse_contract("ReportAcknowledgment", response)


def test_missing_inventory_never_invents_a_free_local_model(tmp_path):
    payload = route_request()
    payload["inventory"] = None
    response = Application(SQLiteStorage(tmp_path / "route.db")).route(payload)
    assert response["status"] == "routing_failed"
    assert response["details"]["cost_estimate"]["raw_token_cost"] is None


@pytest.mark.parametrize("mutation", ["stale", "unknown_cost", "unavailable", "oversize"])
def test_prepared_candidate_hard_constraints_fail_closed(tmp_path, mutation):
    payload = route_request()
    candidate = payload["inventory"]["candidates"][0]
    if mutation == "stale":
        candidate["expires_at"] = "2000-01-01T00:00:00Z"
    elif mutation == "unknown_cost":
        candidate["rates"] = None
        payload["request"]["hard_constraints"]["spending_ceiling"] = {
            "amount": "1",
            "currency": "USD",
        }
    elif mutation == "unavailable":
        candidate["runtime_capabilities"] = []
    else:
        payload["request"]["hard_constraints"]["context_token_limit"] = 1
    assert (
        Application(SQLiteStorage(tmp_path / "route.db")).route(payload)["status"]
        == "no_compatible_plan"
    )


def test_commit_failure_cannot_escape_as_ready(tmp_path, monkeypatch):
    store = SQLiteStorage(tmp_path / "route.db")
    entered = []

    def fail(*args):
        entered.append(True)
        raise sqlite3.OperationalError("synthetic failure")

    monkeypatch.setattr(store, "commit_decision", fail)
    with pytest.raises(sqlite3.OperationalError):
        Application(store).route(route_request())
    assert entered


def test_idempotency_replays_exact_result_and_changed_authority_conflicts(tmp_path):
    app = Application(SQLiteStorage(tmp_path / "route.db"))
    payload = route_request()
    response = app.route(payload)
    assert response == app.route(payload)
    payload["request"]["hard_constraints"]["local_only"] = True
    with pytest.raises(ContractError, match="idempotency conflict"):
        app.route(payload)


def test_application_deletion_spans_route_report_producers(tmp_path):
    app = Application(SQLiteStorage(tmp_path / "route.db"))
    payload = route_request()
    app.route(payload)
    app.delete_task(
        scope(payload) | {"producer": "other", "operation": "report"}, payload["request"]["task_id"]
    )
    assert app.report(fixture("ReportRequest-0"))["status"] == "rejected"
    payload["request"]["envelope"].update(request_id=str(uuid.uuid4()), idempotency_key="new")
    with pytest.raises(ContractError, match="deleted"):
        app.route(payload)


def test_cross_request_cache_preserves_validity_and_authority_invalidates(tmp_path):
    app = Application(SQLiteStorage(tmp_path / "route.db"))
    payload = route_request()
    original = app.route(payload)
    payload["request"]["envelope"].update(request_id=str(uuid.uuid4()), idempotency_key="second")
    reused = app.route(payload)
    assert reused["details"]["reused_decision_id"] == original["details"]["routing_decision_id"]
    assert reused["readiness"] == original["readiness"]
    payload["request"]["envelope"].update(request_id=str(uuid.uuid4()), idempotency_key="third")
    payload["request"]["hard_constraints"]["local_only"] = True
    changed = app.route(payload)
    assert changed["details"]["reused_decision_id"] is None


def test_completion_limit_is_enforced_through_application(tmp_path):
    payload = route_request()
    payload["completion_time_limit_ms"] = 1
    assert (
        Application(SQLiteStorage(tmp_path / "route.db")).route(payload)["status"]
        == "no_compatible_plan"
    )
