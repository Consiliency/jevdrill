"""A cached decision is reused only when nothing outside its cache key could change it."""

import copy
import uuid
from datetime import UTC, datetime

import jevdrill.application
import jevdrill.inventory
from jevdrill.application import Application
from jevdrill.storage import SQLiteStorage
from tests.application.test_route_integration import inputs


def again(value):
    """The same request content under a new request id and idempotency key."""
    value = copy.deepcopy(value)
    value["request"]["envelope"].update(
        request_id=str(uuid.uuid4()), idempotency_key=str(uuid.uuid4())
    )
    return value


def report(app, value, decision, run_id, event_type):
    envelope = dict(
        value["request"]["envelope"], operation="report", idempotency_key=str(uuid.uuid4())
    )
    event = {
        "schema_version": "1",
        "event_id": str(uuid.uuid4()),
        "task_id": value["request"]["task_id"],
        "routing_decision_id": decision["details"]["routing_decision_id"],
        "execution_run_id": run_id,
        "source_id": "fixture",
        "source_sequence": 1,
        "occurred_at": "2026-09-28T00:00:00Z",
        "supersedes_event_id": None,
        "payload": {
            "kind": "lifecycle",
            "event_type": event_type,
            "applied_plan_id": None,
            "reason": "synthetic",
        },
    }
    assert app.report({"envelope": envelope, "event": event})["status"] == "accepted"


def test_a_retry_is_checked_against_recorded_attempts_and_never_served_from_the_cache(tmp_path):
    value = inputs()
    value["request"]["hard_constraints"]["max_attempts"] = 2
    app = Application(SQLiteStorage(tmp_path / "route.db"))
    decision = app.route(value)
    first_run = str(uuid.uuid4())
    report(app, value, decision, first_run, "failed")
    retry = again(value)
    retry["request"]["retry_context"] = {
        "prior_routing_decision_id": decision["details"]["routing_decision_id"],
        "prior_execution_run_id": first_run,
        "failure_class": "infrastructure",
        "failure_summary": "synthetic",
        "remaining_attempts": 1,
        "remaining_time_ms": 5000,
        "remaining_spend": None,
    }
    retry["inventory"]["candidates"][0]["addresses_failures"] = ["infrastructure"]
    allowed = app.route(retry)
    assert allowed["status"] == "ready"
    # A second attempt is recorded. The same retry now claims an attempt that is spent.
    report(app, value, allowed, str(uuid.uuid4()), "failed")
    refused = app.route(again(retry))
    assert refused["status"] == "no_compatible_plan"
    assert refused["details"]["reused_decision_id"] is None
    reasons = [reason for row in refused["details"]["exclusions"] for reason in row["reasons"]]
    assert "unverified retry run or attempt budget" in reasons


def test_an_expired_rate_card_is_evaluated_again_and_not_served_from_the_cache(
    tmp_path, monkeypatch
):
    value = inputs()
    value["request"]["hard_constraints"]["spending_ceiling"] = {"amount": "1", "currency": "USD"}
    candidate = value["inventory"]["candidates"][0]
    candidate["execution_token_limits"] = {"input_tokens": 32768, "output_tokens": 1024}
    candidate["rates"]["expires_at"] = "2050-01-01T00:00:00Z"
    app = Application(SQLiteStorage(tmp_path / "route.db"))
    first = app.route(value)
    assert first["status"] == "ready"
    # While the rates are current the cache answers, so the cache is what the rest tests.
    reused = app.route(again(value))
    assert reused["details"]["reused_decision_id"] == first["details"]["routing_decision_id"]

    current = jevdrill.inventory.fresh

    def after_the_rates_expire(verified_at, expires_at, now=None):
        return current(verified_at, expires_at, datetime(2060, 1, 1, tzinfo=UTC))

    monkeypatch.setattr(jevdrill.inventory, "fresh", after_the_rates_expire)
    monkeypatch.setattr(jevdrill.application, "fresh", after_the_rates_expire)
    late = app.route(again(value))
    assert late["status"] == "no_compatible_plan"
    assert late["details"]["reused_decision_id"] is None
    assert [row["reasons"] for row in late["details"]["exclusions"]] == [["cost_cap"]]
