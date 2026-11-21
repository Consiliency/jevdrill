import json
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import uuid4

import pytest

from jevdrill.contracts import ContractError
from jevdrill.integrations.development import DevelopmentJudge


@pytest.fixture
def judge(tmp_path):
    state = {"requests": 0, "body": None}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            state["requests"] += 1
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(state["body"]).encode())

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    service = DevelopmentJudge(
        tmp_path / "judgments.db",
        scope={
            "project_id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "producer": "fixture",
            "operation": "discover",
        },
        authorization_revision="synthetic-grant",
        max_calls=2,
        total_spend_microusd=5506,
        deadline_ms=int(time.time() * 1000) + 10_000,
        credential=lambda: "synthetic-secret",
        authorize=lambda scope: True,
        base_url=f"http://127.0.0.1:{server.server_port}/v1",
    )
    yield service, state
    server.shutdown()
    thread.join(timeout=2)
    server.server_close()


VALID = {"type": "noul", "noul": 0.9}


@pytest.mark.parametrize(
    "body",
    [
        {"model": "jev-1.13.0", "answers": None},
        {"model": "jev-1.13.0", "answers": ["result"]},
        {"model": "jev-1.13.0", "answers": {"result": [0.5]}},
        {"model": "jev-1.13.0", "answers": {"result": None}},
        {"model": "jev-1.13.0", "answers": {"result": VALID}, "usage": [1, 2]},
        ["jev-1.13.0"],
    ],
)
def test_malformed_success_body_is_a_contract_failure_and_is_not_retried(judge, body):
    service, state = judge
    state["body"] = body
    with pytest.raises(ContractError, match="development_judgment_incomplete"):
        service.observe_option("public task", "option", "0" * 64, "offered", time.monotonic() + 5)
    with sqlite3.connect(service.path) as db:
        payloads = [json.loads(row[0]) for row in db.execute("SELECT payload FROM judgment_calls")]
    assert [row["state"] for row in payloads] == ["uncertain"]
    assert payloads[0]["response"] is None
    with pytest.raises(ContractError, match="development_judgment_reservation_denied"):
        service.observe_option("public task", "option", "0" * 64, "offered", time.monotonic() + 5)
    assert state["requests"] == 1


def test_well_formed_success_body_is_still_accepted(judge):
    service, state = judge
    state["body"] = {
        "model": "jev-1.13.0",
        "answers": {"result": VALID},
        "usage": {"input_tokens": 100, "output_tokens": 1},
    }
    record = service.observe_option(
        "public task", "option", "0" * 64, "offered", time.monotonic() + 5
    )
    assert record["judgments"] == {"offered": True}
    assert state["requests"] == 1
