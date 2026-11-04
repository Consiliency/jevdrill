import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

import baml_sdk as sdk
from jevdrill.application import Application
from jevdrill.contracts import ContractError
from jevdrill.discovery import initial_state, next_question
from jevdrill.integrations.jev import DiscoveryJevAdapter
from jevdrill.storage import SQLiteStorage


@pytest.fixture
def discovery_provider(monkeypatch):
    observed = {"requests": [], "score": 0.9, "answers_invalid": False}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            observed["requests"].append(
                json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {
                        "model": "jev-latest",
                        "answers": {}
                        if observed["answers_invalid"]
                        else {"result": {"type": "noul", "noul": observed["score"]}},
                        "usage": {"input_tokens": 123},
                    }
                ).encode()
            )

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("JEVDRILL_TEST_URL", f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setattr(
        "jevdrill.integrations.jev.ObserveDiscoveryOption", sdk.MockObserveDiscoveryOption
    )
    yield observed
    server.shutdown()
    server.server_close()
    thread.join()


def test_generated_baml_discovery_application_loopback_and_partial_usage(
    tmp_path, discovery_inputs, discovery_provider
):
    discovery_inputs["limits"]["max_rounds"] = 1
    rates = {
        "revision": "synthetic-rates",
        "currency": "USD",
        "input_rate": "0.000001",
        "output_rate": "0",
        "verified_at": "2026-01-01T00:00:00Z",
        "expires_at": "2099-01-01T00:00:00Z",
        "subscription_multiplier": None,
    }
    discovery_inputs["judgment_policy"]["rates"] = rates
    discovery_inputs["limits"]["spending_ceiling"] = {"amount": "1", "currency": "USD"}
    storage = SQLiteStorage(tmp_path / "route.db")
    result = Application(storage).discover(discovery_inputs)
    assert result["status"] == "selected_guidance"
    assert len(discovery_provider["requests"]) == 1
    envelope = discovery_inputs["envelope"]
    scope = {
        "project_id": envelope["project_id"],
        "workspace_id": envelope["workspace_id"],
        "producer": envelope["harness_id"],
        "operation": "discover",
    }
    recorded = storage.load_discovery(scope, result["details"]["discovery_id"])
    measurements = recorded["calls"][0]["observation"]["measurements"]
    assert measurements[1]["measurement_value"]["value"] == 123
    assert measurements[2]["measurement_value"] == {"kind": "unknown", "reason": "not_reported"}
    request = json.dumps(discovery_provider["requests"][0])
    assert "Synthetic alpha instructions" not in request and "synthetic-owned" not in request
    assert "source_occurrences" not in request and "rights" not in request
    assert "question_digest" in request and "Human-authored guidance" in request


@pytest.mark.parametrize(
    "bad",
    ["output", "positive_output_rate", "unknown_input_rate", "expired_rates", "too_small_spend"],
)
def test_unsupported_requested_bounds_reject_before_http(
    tmp_path, discovery_inputs, discovery_provider, bad
):
    policy = discovery_inputs["judgment_policy"]
    policy["spending_ceiling"] = {"amount": "1", "currency": "USD"}
    policy["rates"] = {
        "revision": "synthetic",
        "currency": "USD",
        "input_rate": "0.000001",
        "output_rate": "0",
        "verified_at": "2026-01-01T00:00:00Z",
        "expires_at": "2099-01-01T00:00:00Z",
        "subscription_multiplier": None,
    }
    if bad == "output":
        policy["hard_output_token_limit"] = 1
    elif bad == "positive_output_rate":
        policy["rates"]["output_rate"] = "0.01"
    elif bad == "unknown_input_rate":
        policy["rates"]["input_rate"] = None
    elif bad == "expired_rates":
        policy["rates"]["expires_at"] = "2026-01-01T00:00:00Z"
    else:
        policy["spending_ceiling"]["amount"] = "0"
    question = next_question(initial_state(discovery_inputs, discovery_inputs["limits"]))
    adapter = DiscoveryJevAdapter(policy)
    if bad == "too_small_spend":
        result = Application(SQLiteStorage(tmp_path / "route.db")).discover(discovery_inputs)
        assert result["status"] == "discovery_failed" and not discovery_provider["requests"]
        return
    with pytest.raises(ContractError):
        adapter.prepare_option("objective", "context", question, question["options"][0])
    assert not discovery_provider["requests"]


def test_failed_answer_keeps_usage_and_reserved_attempt(discovery_inputs, discovery_provider):
    discovery_provider["answers_invalid"] = True
    policy = discovery_inputs["judgment_policy"]
    adapter = DiscoveryJevAdapter(policy)
    question = next_question(initial_state(discovery_inputs, discovery_inputs["limits"]))
    option = question["options"][0]
    task, offered, reservation = adapter.prepare_option("objective", "context", question, option)
    result = adapter.observe_option(
        task, offered, question["question_digest"], option["option_id"], time.monotonic() + 1
    )
    assert not result["judgments"]
    assert result["measurements"][1]["measurement_value"]["value"] == 123
    assert reservation["input_tokens"] > 0 and len(discovery_provider["requests"]) == 1


@pytest.mark.parametrize("restriction", ["enabled", "cloud_allowed", "expired_rates"])
def test_discovery_call_rechecks_authorization_before_http(
    discovery_inputs, discovery_provider, restriction
):
    policy = discovery_inputs["judgment_policy"]
    adapter = DiscoveryJevAdapter(policy)
    question = next_question(initial_state(discovery_inputs, discovery_inputs["limits"]))
    option = question["options"][0]
    task, offered, _ = adapter.prepare_option("objective", "context", question, option)
    if restriction == "expired_rates":
        adapter.policy["spending_ceiling"] = {"amount": "1", "currency": "USD"}
        adapter.policy["rates"] = {
            "revision": "synthetic",
            "currency": "USD",
            "input_rate": "0.000001",
            "output_rate": "0",
            "verified_at": "2025-01-01T00:00:00Z",
            "expires_at": "2026-01-01T00:00:00Z",
            "subscription_multiplier": None,
        }
    else:
        adapter.policy[restriction] = False
    with pytest.raises(ContractError):
        adapter.observe_option(
            task, offered, question["question_digest"], option["option_id"], time.monotonic() + 1
        )
    assert not discovery_provider["requests"]
