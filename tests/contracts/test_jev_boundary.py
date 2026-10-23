"""Exercise the pinned bridge against synthetic loopback responses only."""

import asyncio
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from baml_bridge.errors import BamlError

import baml_sdk as sdk
from baml_sdk.ai.events import LLMCall, Usage
from jevdrill.telemetry import retain_jev_call


@pytest.fixture
def provider():
    observations = {
        "delay": 0,
        "body": {"model": "jev-latest", "answers": {"result": {"type": "noul", "noul": 0.9}}},
        "requests": [],
        "started": threading.Event(),
    }

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            observations["requests"].append((self.path, body))
            observations["started"].set()
            time.sleep(observations["delay"])
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("X-Synthetic-Secret", "header-sentinel")
            self.end_headers()
            try:
                self.wfile.write(json.dumps(observations["body"]).encode())
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", observations
    server.shutdown()
    server.server_close()
    thread.join()


def test_request_alias_and_decoding(provider):
    url, observed = provider
    assert sdk.mock_judgment(url, 1000) is True
    path, body = observed["requests"][0]
    assert path == "/systemone"
    assert body["model"] == "jev-latest"
    assert body["questions"]["result"]["type"] == "noul"
    assert json.loads(sdk.request_shape())["questions"]["result"]["type"] == "noul"


def test_suitability_request_describes_a_prospective_execution_configuration():
    body = sdk.candidate_request_shape("task", "configuration")
    assert "prospective execution configuration" in body
    assert "correctness of a produced answer" in body
    assert "guidance instructions" in body


def test_event_surface(provider, monkeypatch):
    url, _observed = provider
    events = []
    monkeypatch.setenv("JEVDRILL_TEST_URL", url)
    result = sdk.MockIsSuitable("synthetic-task", "synthetic-candidate", on_event=events.append)
    assert result is True
    calls = [event for event in events if isinstance(event, LLMCall)]
    assert len(calls) == 1
    call = calls[0]
    assert call.http_request is None
    assert call.http_response.body is None
    assert call.http_response.headers["x-synthetic-secret"] == "header-sentinel"
    retained = [value for event in events if (value := retain_jev_call(event)) is not None]
    assert len(retained) == 1
    assert retained[0]["input_tokens"] is None
    assert retained[0]["duration_ms"] >= 0
    assert not any(
        word in json.dumps(retained)
        for word in (
            "synthetic-task",
            "synthetic-candidate",
            "header-sentinel",
            "synthetic-secret",
            "arguments",
            "headers",
            "body",
            "content",
            "value_json",
        )
    )
    # Usage counters belong to one call; a second event must not double count them.
    call.usage = Usage(input_tokens=10, output_tokens=2, cached_input_tokens=3)
    assert retain_jev_call(call)["input_tokens"] == 10
    assert retain_jev_call(call.usage) is None


def test_invalid_response_is_typed_failure(provider):
    url, observed = provider
    observed["body"] = {"invalid": True}
    with pytest.raises(BamlError):
        sdk.mock_judgment(url, 1000)


def test_timeout(provider):
    url, observed = provider
    observed["delay"] = 1
    start = time.monotonic()
    with pytest.raises(BamlError):
        sdk.mock_judgment(url, 50)
    assert time.monotonic() - start < 0.9


def test_async_cancellation(provider):
    url, observed = provider
    observed["delay"] = 1

    async def run():
        task = asyncio.create_task(sdk.mock_judgment_async(url, 3000))
        assert await asyncio.to_thread(observed["started"].wait, 2)
        start = time.monotonic()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert time.monotonic() - start < 0.9

    asyncio.run(run())


def test_route_adapter_uses_baml_timeout_and_sanitized_events(provider, monkeypatch):
    from jevdrill.integrations.jev import JevAdapter

    url, observations = provider
    monkeypatch.setenv("JEVDRILL_TEST_URL", url)
    monkeypatch.setattr("jevdrill.integrations.jev.JudgeCandidate", sdk.MockJudgeCandidate)
    retained = []
    policy = {
        "enabled": True,
        "cloud_allowed": True,
        "max_calls": 1,
        "max_candidates": 1,
        "max_input_tokens": 10000,
        "max_output_tokens": 10,
        "spending_ceiling": None,
        "rates": None,
        "model_revision": "jev-latest",
        "function_revision": "JudgeCandidate-v2",
        "token_counter_revision": "utf8-bytes-upper-bound-v1",
    }

    def observe(event):
        value = retain_jev_call(event)
        if value is not None:
            retained.append(value)

    response = JevAdapter(policy, observe).judge(
        "synthetic", ({"candidate_id": "a", "model_id": "model"},), time.monotonic() + 1
    )
    assert response["judgments"] == {"a": True}
    assert retained and "header-sentinel" not in json.dumps(retained)
    assert observations["requests"]


@pytest.mark.parametrize(
    "usage, expected, reason",
    [
        ({"input_tokens": 123, "output_tokens": 1}, 1, None),
        ({"input_tokens": 123, "output_tokens": 0}, 0, None),
        ({"input_tokens": 123, "output_tokens": None}, None, "not_reported"),
        ({"input_tokens": 123}, None, "not_reported"),
        ({}, None, "not_reported"),
        (None, None, "not_reported"),
        ({"input_tokens": 123, "output_tokens": -1}, None, "incomplete"),
        ({"input_tokens": 123, "output_tokens": "7"}, None, "incomplete"),
        ({"input_tokens": 123, "output_tokens": True}, None, "incomplete"),
        ({"input_tokens": 123, "output_tokens": 0.5}, None, "incomplete"),
    ],
)
def test_observed_partial_usage(provider, monkeypatch, usage, expected, reason):
    from jevdrill.contracts import jev_usage_measurements

    url, observed = provider
    monkeypatch.setenv("JEVDRILL_TEST_URL", url)
    if usage is not None:
        observed["body"]["usage"] = usage
    events = []
    assert sdk.MockObserveCandidate("task-canary", "candidate-canary", 1000, events.append)
    assert len(events) == len(observed["requests"]) == 1
    rows = jev_usage_measurements(events[0])
    output = rows[2]["measurement_value"]
    assert output == (
        {"kind": "known", "value": expected, "unit": "tokens"}
        if reason is None
        else {"kind": "unknown", "reason": reason}
    )
    if usage and usage.get("input_tokens") == 123:
        assert rows[1]["measurement_value"]["value"] == 123
    serialized = json.dumps(events[0].model_dump())
    assert all(
        sentinel not in serialized
        for sentinel in ("task-canary", "candidate-canary", "header-sentinel", "synthetic-secret")
    )


@pytest.mark.parametrize("score", [0, 0.49, 0.5, 0.51, 1])
def test_observed_request_and_boolean_parity(provider, monkeypatch, score):
    url, observed = provider
    monkeypatch.setenv("JEVDRILL_TEST_URL", url)
    observed["body"]["answers"]["result"]["noul"] = score
    observed["body"]["usage"] = {"input_tokens": 123, "output_tokens": 1}
    old = sdk.MockJudgeCandidate("task", "candidate", 1000, None)
    new = sdk.MockObserveCandidate("task", "candidate", 1000, None)
    assert old is new is (score >= 0.5)
    assert len(observed["requests"]) == 2
    assert observed["requests"][0] == observed["requests"][1]


@pytest.mark.parametrize("answers", [{}, None, {"result": {"type": "noul", "noul": "bad"}}])
def test_usage_survives_answer_decode_failure(provider, monkeypatch, answers):
    from jevdrill.contracts import jev_usage_measurements

    url, observed = provider
    monkeypatch.setenv("JEVDRILL_TEST_URL", url)
    observed["body"] = {"usage": {"input_tokens": 123, "output_tokens": 1}, "answers": answers}
    events = []
    with pytest.raises(BamlError):
        sdk.MockObserveCandidate("task", "candidate", 1000, events.append)
    assert len(events) == len(observed["requests"]) == 1
    assert jev_usage_measurements(events[0])[1]["measurement_value"]["value"] == 123


def test_observed_timeout_and_cancellation(provider, monkeypatch):
    url, observed = provider
    monkeypatch.setenv("JEVDRILL_TEST_URL", url)
    observed["delay"] = 1
    events = []
    start = time.monotonic()
    with pytest.raises(BamlError):
        sdk.MockObserveCandidate("task", "candidate", 50, events.append)
    assert time.monotonic() - start < 0.9
    assert not events
    observed["started"].clear()

    async def run():
        task = asyncio.create_task(
            sdk.MockObserveCandidate_async("task", "candidate", 3000, events.append)
        )
        assert await asyncio.to_thread(observed["started"].wait, 2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run())
    assert len(observed["requests"]) == 2
    assert not events
