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
