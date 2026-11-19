import json
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import uuid4

import pytest

from jevdrill.application import Application
from jevdrill.contracts import ContractError
from jevdrill.integrations.development import DevelopmentJudge
from jevdrill.storage import SQLiteStorage


@pytest.fixture
def judge(tmp_path):
    state = {"requests": [], "status": 200, "model": "jev-1.13.0", "body_bytes": None, "delay": 0}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            state["requests"].append(
                json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            )
            time.sleep(state["delay"])
            self.send_response(state["status"])
            self.end_headers()
            body = (
                state["body_bytes"]
                or json.dumps(
                    {
                        "model": state["model"],
                        "answers": {"result": {"type": "noul", "noul": 0.9}},
                        "usage": {"input_tokens": 100, "output_tokens": 1},
                    }
                ).encode()
            )
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    operations = []
    service = DevelopmentJudge(
        tmp_path / "judgments.db",
        scope={
            "project_id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "producer": "public-study",
            "operation": "discover",
        },
        authorization_revision="synthetic-new-grant",
        max_calls=2,
        total_spend_microusd=5506,
        deadline_ms=int(time.time() * 1000) + 10000,
        credential=lambda: "synthetic-secret",
        authorize=lambda scope: operations.append(scope["operation"]) or True,
        base_url=f"http://127.0.0.1:{server.server_port}/v1",
    )
    yield service, state, operations
    server.shutdown()
    thread.join(timeout=2)
    server.server_close()


def test_actual_baml_pinned_judge_reserves_all_discovery_and_task_calls(judge):
    service, state, operations = judge
    assert service.observe_option(
        "public task", "option", "0" * 64, "offered", time.monotonic() + 2
    )["judgments"] == {"offered": True}
    task = service.judge("different task", ({"candidate_id": "one"},), time.monotonic() + 2)
    assert task["judgments"] == {"one": True}
    assert task["function_revision"] == "JudgeCandidate-v2"
    assert "discover" in operations and "route" in operations
    assert all(row["model"] == "jev-1.13.0" for row in state["requests"])
    with sqlite3.connect(service.path) as db:
        assert db.execute("SELECT COUNT(*),SUM(reservation) FROM judgment_calls").fetchone() == (
            2,
            5506,
        )
        payloads = [json.loads(row[0]) for row in db.execute("SELECT payload FROM judgment_calls")]
    assert all(
        row["state"] == "completed" and row["response"]["model"] == "jev-1.13.0" for row in payloads
    )
    for payload in payloads:
        measured = {row["metric_id"]: row["measurement_value"] for row in payload["measurements"]}
        assert measured["routing_input_tokens"] == {"kind": "known", "value": 100, "unit": "tokens"}
        assert measured["routing_output_tokens"] == {"kind": "known", "value": 1, "unit": "tokens"}
        assert measured["routing_duration_ms"]["kind"] == "known"
    assert "synthetic-secret" not in json.dumps(payloads)
    with pytest.raises(ContractError, match="reservation_denied"):
        service.judge("third task", ({"candidate_id": "two"},), time.monotonic() + 2)
    assert len(state["requests"]) == 2


@pytest.mark.parametrize(
    "restriction",
    [
        "allowed",
        "local_only",
        "allowlist",
        "disabled",
        "cloud",
        "provider",
        "hard_output",
        "unsupported_model",
        "wrong_model",
        "unsupported_counter",
        "ceiling_zero",
        "ceiling_small",
        "ceiling_funded",
        "ceiling_unknown",
        "ceiling_positive_output",
        "ceiling_stale",
        "ceiling_currency",
    ],
)
def test_application_checks_discovery_authority_before_actual_adapter_calls(
    judge, discovery_inputs, tmp_path, restriction
):
    service, state, operations = judge
    inputs = discovery_inputs
    inputs["catalog"]["resources"] = inputs["catalog"]["resources"][:1]
    inputs["descriptions"] = inputs["descriptions"][:1]
    inputs["judgment_policy"].update(
        model_revision="jev-1.13.0", max_input_tokens=200_000, output_planning_reservation=0
    )
    inputs["limits"]["max_input_tokens"] = 200_000
    inputs["limits"]["output_planning_reservation"] = 0
    inputs["hard_constraints"]["context_token_limit"] = 200_000
    if restriction == "local_only":
        inputs["hard_constraints"]["local_only"] = True
    elif restriction == "allowlist":
        inputs["hard_constraints"]["allowed_providers"] = ["local"]
    elif restriction == "disabled":
        inputs["judgment_policy"]["enabled"] = False
    elif restriction == "cloud":
        inputs["judgment_policy"]["cloud_allowed"] = False
    elif restriction == "provider":
        inputs["judgment_policy"]["provider"] = "local"
        inputs["hard_constraints"]["allowed_providers"] = ["local"]
    elif restriction == "hard_output":
        inputs["judgment_policy"]["hard_output_token_limit"] = 1
    elif restriction == "unsupported_model":
        inputs["judgment_policy"]["model_revision"] = "unsupported-review-model"
    elif restriction == "wrong_model":
        inputs["judgment_policy"]["model_revision"] = "jev-latest"
    elif restriction == "unsupported_counter":
        inputs["judgment_policy"]["token_counter_revision"] = "unsupported-review-counter"
    elif restriction.startswith("ceiling_"):
        inputs["judgment_policy"]["spending_ceiling"] = {
            "amount": "0"
            if restriction == "ceiling_zero"
            else "0.001"
            if restriction == "ceiling_small"
            else "1",
            "currency": "EUR" if restriction == "ceiling_currency" else "USD",
        }
        inputs["judgment_policy"]["rates"] = {
            "input_rate": "0.000001",
            "output_rate": "0",
            "subscription_multiplier": None,
            "currency": "USD",
            "revision": "synthetic-fixture",
            "verified_at": "2020-01-01T00:00:00Z",
            "expires_at": "2100-01-01T00:00:00Z",
        }
        if restriction == "ceiling_unknown":
            inputs["judgment_policy"]["rates"] = None
        elif restriction == "ceiling_positive_output":
            inputs["judgment_policy"]["rates"]["output_rate"] = "0.01"
        elif restriction == "ceiling_stale":
            inputs["judgment_policy"]["rates"]["expires_at"] = "2021-01-01T00:00:00Z"
    app = Application(SQLiteStorage(tmp_path / "route.db"), discovery_judgments=service)
    result = app.discover(inputs)
    if restriction == "allowed":
        assert result["status"] == "selected_guidance"
        assert len(state["requests"]) == 1
        assert operations
    else:
        assert result["status"] != "selected_guidance"
        assert state["requests"] == [] and operations == []


@pytest.mark.parametrize(
    "restriction",
    [
        "allowed",
        "unsupported_model",
        "wrong_model",
        "unsupported_counter",
        "ceiling_zero",
        "ceiling_small",
        "ceiling_funded",
        "ceiling_unknown",
        "ceiling_positive_output",
        "ceiling_stale",
        "ceiling_currency",
    ],
)
def test_injected_task_profile_binding_and_unsupported_ceiling_never_dispatch(
    judge, tmp_path, restriction
):
    from tests.application.test_route_integration import inputs, policy

    service, state, operations = judge
    value = inputs()
    value["judgment_policy"] = policy() | {"model_revision": service.model_revision}
    value["inventory"]["candidates"][0]["quality_sufficient"] = None
    if restriction == "unsupported_model":
        value["judgment_policy"]["model_revision"] = "unsupported-review-model"
    elif restriction == "wrong_model":
        value["judgment_policy"]["model_revision"] = "jev-latest"
    elif restriction == "unsupported_counter":
        value["judgment_policy"]["token_counter_revision"] = "unsupported-review-counter"
    elif restriction.startswith("ceiling_"):
        value["judgment_policy"]["spending_ceiling"] = {
            "amount": "0"
            if restriction == "ceiling_zero"
            else "0.001"
            if restriction == "ceiling_small"
            else "1",
            "currency": "EUR" if restriction == "ceiling_currency" else "USD",
        }
        value["judgment_policy"]["rates"] = {
            "input_rate": "0.000001",
            "output_rate": "0",
            "subscription_multiplier": None,
            "currency": "USD",
            "revision": "synthetic-fixture",
            "verified_at": "2020-01-01T00:00:00Z",
            "expires_at": "2100-01-01T00:00:00Z",
        }
        if restriction == "ceiling_unknown":
            value["judgment_policy"]["rates"] = None
        elif restriction == "ceiling_positive_output":
            value["judgment_policy"]["rates"]["output_rate"] = "0.01"
        elif restriction == "ceiling_stale":
            value["judgment_policy"]["rates"]["expires_at"] = "2021-01-01T00:00:00Z"
    app = Application(SQLiteStorage(tmp_path / "route.db"), judgments=service)
    result = app.route(value)
    if restriction == "allowed":
        assert result["status"] == "ready"
        assert len(state["requests"]) == 1 and operations
    else:
        assert result["status"] == "routing_failed"
        assert state["requests"] == [] and operations == []
    with sqlite3.connect(service.path) as db:
        assert db.execute("SELECT COUNT(*) FROM judgment_calls").fetchone()[0] == int(
            restriction == "allowed"
        )


@pytest.mark.parametrize("fault", ["429", "wrong_model", "oversized", "timeout", "revoked"])
def test_uncertain_judgments_never_retry_refund_or_accept_wrong_model(judge, fault):
    service, state, _ = judge
    if fault == "429":
        state["status"] = 429
    elif fault == "wrong_model":
        state["model"] = "jev-latest"
    elif fault == "oversized":
        state["body_bytes"] = b"x" * 65537
    elif fault == "timeout":
        state["delay"] = 0.3
    else:
        service.authorize = lambda _: False
    with pytest.raises(ContractError):
        service.judge(
            "task",
            ({"candidate_id": "one"},),
            time.monotonic() + (0.1 if fault == "timeout" else 2),
        )
    with sqlite3.connect(service.path) as db:
        count, reserve = db.execute(
            "SELECT COUNT(*),COALESCE(SUM(reservation),0) FROM judgment_calls"
        ).fetchone()
    assert (count, reserve) == ((0, 0) if fault == "revoked" else (1, 2753))
    with pytest.raises(ContractError):
        service.judge("task", ({"candidate_id": "one"},), time.monotonic() + 2)
    assert len(state["requests"]) == (0 if fault == "revoked" else 1)


def test_completed_identical_judgment_reuses_immutable_receipt_without_new_dispatch(judge):
    service, state, _ = judge
    first = service.judge("same task", ({"candidate_id": "one"},), time.monotonic() + 2)
    assert service.judge("same task", ({"candidate_id": "one"},), time.monotonic() + 2) == first
    assert len(state["requests"]) == 1
    with sqlite3.connect(service.path) as database:
        assert database.execute("SELECT SUM(reservation) FROM judgment_calls").fetchone()[0] == 2753


def test_slow_credential_lookup_cannot_dispatch_after_caller_deadline(judge):
    service, state, _ = judge
    service.credential = lambda: time.sleep(0.15) or "synthetic-secret"
    with pytest.raises(ContractError, match="deadline"):
        service.judge("task", ({"candidate_id": "one"},), time.monotonic() + 0.1)
    assert not state["requests"]
    with sqlite3.connect(service.path) as database:
        assert database.execute("SELECT SUM(reservation) FROM judgment_calls").fetchone()[0] == 2753


@pytest.mark.parametrize(
    "mutation", ["template", "development_template", "discovery_template", "projection", "fields"]
)
def test_profile_binding_rejects_changed_templates_without_mutating_receipts(
    judge, monkeypatch, mutation
):
    from jevdrill.integrations import jev

    service, state, _ = judge
    first = service.judge("task", ({"candidate_id": "one"},), time.monotonic() + 2)
    with sqlite3.connect(service.path) as database:
        before = database.execute("SELECT * FROM judgment_calls").fetchall()
    if mutation in {"template", "development_template", "discovery_template"}:
        name = {
            "template": "candidate_request_shape",
            "development_template": "development_task_request_shape",
            "discovery_template": "development_discovery_request_shape",
        }[mutation]
        original = getattr(jev, name)
        monkeypatch.setattr(
            jev, name, lambda task, offered, *args: original(task + " amended", offered, *args)
        )
    elif mutation == "projection":
        monkeypatch.setattr(jev, "JUDGMENT_PROJECTION_VERSION", "synthetic-new-projection")
    else:
        monkeypatch.setattr(
            jev, "JUDGMENT_CANDIDATE_FIELDS", jev.JUDGMENT_CANDIDATE_FIELDS - {"verified_at"}
        )
    with pytest.raises(ContractError, match="profile_changed"):
        DevelopmentJudge(
            service.path,
            scope=service.scope,
            authorization_revision="synthetic-new-grant",
            max_calls=service.max_calls,
            total_spend_microusd=service.total_spend_microusd,
            deadline_ms=service.deadline_ms,
            credential=service.credential,
            authorize=service.authorize,
            base_url=service.url.geturl(),
            clock=service.clock,
        )
    assert service.judge("task", ({"candidate_id": "one"},), time.monotonic() + 2) == first
    assert len(state["requests"]) == 1
    with sqlite3.connect(service.path) as database:
        assert database.execute("SELECT * FROM judgment_calls").fetchall() == before
        assert (
            database.execute("SELECT revision FROM judgment_profile").fetchone()[0]
            == service.revision
        )


def test_replay_rejects_changed_rendered_body_without_dispatch(judge, monkeypatch):
    from jevdrill.integrations import development

    service, state, _ = judge
    service.judge("task", ({"candidate_id": "one"},), time.monotonic() + 2)
    original = development.development_task_request_shape
    monkeypatch.setattr(
        development,
        "development_task_request_shape",
        lambda task, offered, model: original(task + " amended", offered, model),
    )
    with pytest.raises(ContractError, match="reservation_denied"):
        service.judge("task", ({"candidate_id": "one"},), time.monotonic() + 2)
    assert len(state["requests"]) == 1


@pytest.mark.parametrize(
    "usage",
    [
        "absent",
        None,
        {},
        {"input_tokens": None, "output_tokens": 7},
        {"input_tokens": None, "output_tokens": 0},
        {"input_tokens": None, "output_tokens": None},
    ],
)
def test_missing_usage_preserves_task_and_discovery_judgments_and_replays(judge, usage):
    service, state, _ = judge
    body = {"model": "jev-1.13.0", "answers": {"result": {"type": "noul", "noul": 0.9}}}
    if usage != "absent":
        body["usage"] = usage
    state["body_bytes"] = json.dumps(body).encode()
    candidate = ({"candidate_id": "one"},)
    task = service.judge("task", candidate, time.monotonic() + 2)
    discovery = service.observe_option("task", "option", "0" * 64, "one", time.monotonic() + 2)
    for record in (task, discovery):
        assert record["judgments"] == {"one": True}
        measurements = {
            row["metric_id"]: row["measurement_value"] for row in record["measurements"]
        }
        assert measurements["routing_input_tokens"] == {"kind": "unknown", "reason": "not_reported"}
        assert measurements["raw_token_cost"] == {"kind": "unknown", "reason": "not_reported"}
        output = usage.get("output_tokens") if isinstance(usage, dict) else None
        assert measurements["routing_output_tokens"] == (
            {"kind": "unknown", "reason": "not_reported"}
            if output is None
            else {"kind": "known", "value": output, "unit": "tokens"}
        )
    assert service.judge("task", candidate, time.monotonic() + 2) == task
    assert (
        service.observe_option("task", "option", "0" * 64, "one", time.monotonic() + 2) == discovery
    )
    assert len(state["requests"]) == 2
    with sqlite3.connect(service.path) as database:
        assert database.execute(
            "SELECT COUNT(*),SUM(reservation) FROM judgment_calls"
        ).fetchone() == (2, 5506)
