"""Controlled executors through real host entrypoints and the installed JEV CLI.

Run with the companion interpreter, through tests/conformance/conftest.py or an equally
stripped environment; the two BAML runtimes stay in separate processes.
Provider authentication and output are synthetic. Routing, reporting, launch construction,
the final subprocess and durable storage use production implementations.
"""

import hashlib
import json
import os
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
import uuid
from copy import deepcopy
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from phase_loop_runtime import runner
from phase_loop_runtime.jevdrill_adapter import JevDrillTransport, JevDrillUnavailable
from phase_loop_runtime.jevdrill_queue import ReportQueue
from phase_loop_runtime.launcher import launch
from phase_loop_runtime.models import (
    DelegationBudget,
    DelegationRequest,
    HarnessLaneAssignment,
    PromptBundle,
)
from phase_loop_test_utils import make_repo, write_phase_plan
from test_jevdrill_adapter import FIXTURES, adapter_fixture

# installed_discovery is the companion's pytest fixture (a name the handoff keeps);
# importing it registers it for the judged-task test below.
from test_jevdrill_discovery import installed_discovery, linked_task  # noqa: F401
from test_jevdrill_usage import synthetic_spec

CASES = json.loads(Path(__file__).with_name("protocol.json").read_text())["cases"]
# grant: which side permits the fixture's capability. "both" launches; "neither" and the two
# one-sided grants must be refused before launch. Both the host and JEV Drill intersect
# declared and runtime, so these cases do not isolate the host's own intersection.
GRANTS = {
    "both": (["text"], ["text"]),
    "neither": ([], []),
    "declared": (["text"], []),
    "runtime": ([], ["text"]),
}
RUNS = [
    (mode, "both", index, False)
    for index, mode in enumerate(["main", "delegated", "lane", "main", "delegated", "lane"])
]
RUNS += [
    (mode, "both", index, True) for mode, index in [("main", 0), ("delegated", 2), ("lane", 4)]
]
RUNS += [(mode, "neither", 0, False) for mode in ("main", "delegated", "lane")]
RUNS += [("main", "declared", 0, False), ("main", "runtime", 0, False)]

# Seeds one pending notice through JEV Drill's own archive path (no archive key), in a
# JEV Drill process so that the two BAML runtimes stay apart. Reads it back through the
# public notice query, requires exactly one, and prints its id.
SEED_NOTICE = """
import json, sys
from pathlib import Path
from jevdrill.storage import SQLiteStorage
store = SQLiteStorage(Path(sys.argv[1]))
scope = dict(json.loads(sys.argv[2]), operation="route")
store.archive(scope, "pending-notice-task", b"synthetic", lambda: None, lambda c, k: c)
(notice,) = store.load_notices(scope)
print(notice["notice_id"])
"""


@pytest.mark.parametrize("entrypoint,grant,case_index,damaged", RUNS)
def test_real_bridge(tmp_path, monkeypatch, entrypoint, grant, case_index, damaged):
    permitted = grant == "both"
    adapter, inputs, _, _, _, _ = adapter_fixture(tmp_path)
    adapter.transport = JevDrillTransport(
        (os.environ["JEVDRILL_TEST_PYTHON"], "-m", "jevdrill.cli"),
        tmp_path / "jev.sqlite",
        FIXTURES,
        json.loads((FIXTURES / "digests.json").read_text()),
    )
    actual_call = adapter.transport.call
    acknowledgments, submitted, connections, construction_events = [], [], [], []
    original_request = runner.build_launch_request
    original_spec = runner.build_launch_spec

    def construct_request(**kwargs):
        construction_events.append("build_launch_request")
        return original_request(**kwargs)

    def construct_spec(request):
        construction_events.append("build_launch_spec")
        return original_spec(request)

    monkeypatch.setattr(runner, "build_launch_request", construct_request)
    monkeypatch.setattr(runner, "build_launch_spec", construct_spec)

    def lose_first_ack(command, payload, **kwargs):
        connections.append(command)
        response = actual_call(command, payload, **kwargs)
        if command == "report":
            submitted.append(deepcopy(payload))
            acknowledgments.append(deepcopy(response))
            if len(submitted) == 1:
                raise OSError("synthetic acknowledgment loss after durable commit")
        return response

    adapter.transport.call = lose_first_ack
    envelope = inputs["request"]["envelope"]
    seeded = subprocess.run(
        [
            os.environ["JEVDRILL_TEST_PYTHON"],
            "-I",
            "-c",
            SEED_NOTICE,
            str(tmp_path / "jev.sqlite"),
            json.dumps(
                {
                    "project_id": envelope["project_id"],
                    "workspace_id": envelope["workspace_id"],
                    "producer": envelope["harness_id"],
                }
            ),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    ).stdout.split()
    delivered = []
    adapter.notice_sink = lambda notice: delivered.append(notice["notice_id"])
    adapter.capabilities_for = lambda _: GRANTS[grant]
    repo = make_repo(tmp_path)
    roadmap = repo / "specs/phase-plans-v1.md"
    plan = write_phase_plan(repo, "RUNNER", roadmap, owned_files=("notes.md",))
    monkeypatch.setattr(
        runner,
        "build_prompt",
        lambda *a, **k: PromptBundle("synthetic-workflow", "required", "inline"),
    )
    monkeypatch.setattr(runner, "run_auth_preflight", lambda _: None)
    entered, completed = [], []

    def inputs_for(context):
        entered.append(context["mode"])
        inputs["request"]["execution_mode"] = "main" if entrypoint == "main" else "delegated"
        selection = context["model_selection"]
        inputs["inventory"]["candidates"][0].update(
            model_id=selection.model,
            native_effort={"kind": "explicit", "native_value": selection.effort},
            supported_efforts=[selection.effort],
        )
        return deepcopy(inputs)

    adapter.inputs_for = inputs_for

    def execute(spec, **kwargs):
        assert spec.prompt_bundle.body == "required"
        program = "print('{}')" if damaged else CASES[case_index]["program"]
        program += "; import sys; print('PRIVATE_OUTPUT_SENTINEL', file=sys.stderr)"
        result = launch(
            [sys.executable, "-I", "-S", "-c", program],
            dry_run=False,
            log_path=None,
        )
        completed.append(result)
        return result

    monkeypatch.setattr(runner, "launch_with_spec", execute)
    original_bridge = runner.launch_jevdrill

    class Finished(Exception):
        pass

    def stop_after_reporting(*args, **kwargs):
        result = original_bridge(*args, **kwargs)
        assert result.returncode == 0
        assert result.jevdrill_execution_run is not None
        assert "PRIVATE_OUTPUT_SENTINEL" in result.output
        assert adapter.queue.status()["records"] > 0
        storage_files = [path for path in tmp_path.rglob("*.sqlite*") if path.is_file()]
        assert adapter.queue.path in storage_files
        for path in storage_files:
            assert b"PRIVATE_OUTPUT_SENTINEL" not in path.read_bytes()
        artifact_lines = [
            line for line in result.output.splitlines() if line != "PRIVATE_OUTPUT_SENTINEL"
        ]
        assert len(artifact_lines) == 1
        artifact = json.loads(artifact_lines[0])
        output = Path(os.environ["JEVDRILL_TEST_ARTIFACTS"])
        (output / f"{case_index}-{damaged}.json").write_text(
            json.dumps(
                {
                    "case_index": case_index,
                    "damaged": damaged,
                    "artifact": artifact,
                    "entrypoint": entrypoint,
                }
            )
        )
        for _ in range(3):
            adapter.queue.clock = lambda: time.time() + 10
            adapter.flush()
        assert adapter.queue.status()["records"] == 0
        assert sum(row["status"] == "accepted" for row in acknowledgments) == 3
        assert sum(row["status"] == "duplicate" for row in acknowledgments) == 1
        assert connections.count("notices") == connections.count("report") + 1
        with sqlite3.connect(tmp_path / "jev.sqlite") as db:
            durable_events = db.execute("SELECT COUNT(*) FROM events_v1").fetchone()[0]
            assert durable_events == len({row["event_id"] for row in acknowledgments})
        envelope = inputs["request"]["envelope"]
        scope = {key: envelope[key] for key in ("project_id", "workspace_id")}
        scope.update(producer="synthetic-delete", operation=envelope["operation"])
        adapter.delete_task(scope, inputs["request"]["task_id"])
        recovered = ReportQueue(adapter.queue.path, sanitize=adapter.queue.sanitize)
        replay = deepcopy(submitted[0])
        replay["envelope"]["harness_id"] = "00000000-0000-4000-8000-000000000099"
        restart_status = recovered.enqueue(replay)
        assert restart_status == "deleted"
        with sqlite3.connect(tmp_path / "jev.sqlite") as db:
            assert db.execute("SELECT COUNT(*) FROM events_v1").fetchone()[0] == 0
        (output / f"{case_index}-{damaged}.json").write_text(
            json.dumps(
                {
                    "case_index": case_index,
                    "damaged": damaged,
                    "artifact": artifact,
                    "entrypoint": entrypoint,
                    "construction_events": construction_events,
                    "execution_run": result.jevdrill_execution_run,
                    "delivery_events": acknowledgments,
                    "durable_events": durable_events,
                    "restart_enqueue_status": restart_status,
                    "connections": connections,
                    "pending_notices": seeded,
                    "notices_delivered": delivered,
                }
            )
        )
        raise Finished()

    monkeypatch.setattr(runner, "launch_jevdrill", stop_after_reporting)
    with pytest.raises(Finished if permitted else JevDrillUnavailable):
        if entrypoint == "main":
            runner.run_loop(
                repo,
                roadmap,
                phase="RUNNER",
                executor="codex",
                model="gpt-5.4",
                effort="high",
                jevdrill_adapter=adapter,
            )
        elif entrypoint == "delegated":
            runner.launch_delegated_child(
                repo=repo,
                roadmap=roadmap,
                parent_phase="RUNNER",
                parent_action="execute",
                plan=plan,
                request=DelegationRequest(
                    request_id="synthetic",
                    product_action="review",
                    target_executor="codex",
                    reason="synthetic conformance",
                    owned_files=("notes.md",),
                    expected_output="findings",
                    budget=DelegationBudget(max_seconds=60),
                ),
                jevdrill_adapter=adapter,
            )
        else:
            runner.launch_harness_lane_work_unit(
                repo=repo,
                roadmap=roadmap,
                plan=plan,
                assignment=HarnessLaneAssignment(
                    phase="RUNNER",
                    lane_id="SL-0",
                    work_unit_kind="lane_execute",
                    owned_files=("notes.md",),
                ),
                dry_run=False,
                jevdrill_adapter=adapter,
            )
    assert entered == [entrypoint]
    assert len(completed) == int(permitted)
    if not permitted:
        artifacts = Path(os.environ["JEVDRILL_TEST_ARTIFACTS"])
        (artifacts / f"permission-{entrypoint}-{grant}.json").write_text(
            json.dumps(
                {
                    "control": "permission_denial",
                    "entrypoint": entrypoint,
                    "grant": grant,
                    "entered": entered,
                    "launched": len(completed),
                }
            )
        )
    for path in tmp_path.glob("*.sqlite*"):
        assert b"PRIVATE_OUTPUT_SENTINEL" not in path.read_bytes()


JUDGMENT_POLICY = {
    "enabled": True,
    "cloud_allowed": True,
    "max_calls": 1,
    "max_candidates": 1,
    "max_input_tokens": 30000,
    "max_output_tokens": 10,
    "spending_ceiling": None,
    "rates": None,
    "model_revision": "jev-latest",
    "function_revision": "JudgeCandidate-v2",
    "token_counter_revision": "utf8-bytes-upper-bound-v1",
}
# JEV Drill's judge call reads `jevdrill.integrations.jev.JudgeCandidate`; this wrapper binds
# it, and discovery, to the SDK's loopback mocks, which refuse a blank JEVDRILL_TEST_URL. It
# fails if either name is not the SDK function it expects to replace, so a rename cannot leave
# the provider function in place.
JUDGED_WRAPPER = """
import baml_sdk
import jevdrill.integrations.jev as bridge
from jevdrill import cli
assert bridge.ObserveDiscoveryOption is baml_sdk.ObserveDiscoveryOption
assert bridge.JudgeCandidate is baml_sdk.ObserveCandidate
bridge.ObserveDiscoveryOption = baml_sdk.MockObserveDiscoveryOption
bridge.JudgeCandidate = baml_sdk.MockObserveCandidate
raise SystemExit(cli.main())
"""
# The instruction that opens every IsSuitable request (baml_src/jev.baml); a judgment request
# carries it, and a discovery-option request carries an option row with a level.
JUDGMENT_MARKER = "Judge whether this prospective execution configuration is suitable"
PROXY_VARIABLES = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)


def objects(value):
    """Every JSON object in a request body, including objects embedded in its strings."""
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from objects(child)
    elif isinstance(value, str):
        for index, char in enumerate(value):
            if char == "{":
                try:
                    child, _ = json.JSONDecoder().raw_decode(value[index:])
                except ValueError:
                    continue
                if isinstance(child, dict):
                    yield child


def request_kind(body):
    try:
        parsed = json.loads(body)
    except ValueError:
        return None
    if any("option_id" in row and "level" in row for row in objects(parsed)):
        return "discovery"
    if JUDGMENT_MARKER in json.dumps(parsed):
        return "judgment"
    return None


def test_installed_flow_carries_a_judged_task(installed_discovery, tmp_path, monkeypatch):  # noqa: F811
    """One task of the installed two-task flow carries a JudgeCandidate-v2 policy.

    No judgment request leaves the runner. The wrapper binds the judge to the loopback mock
    and fails if the binding does not take; the only URL it is given is this loopback server's;
    this test removes the provider key and every proxy variable itself, and forwards without a
    proxy. Discovery-option requests are forwarded to the companion fixture's own loopback
    handler, which answers them as in its own test; judgment requests are answered here and
    recorded; a request of neither kind fails the test.
    """
    adapter, inputs, base, kwargs, _, _ = installed_discovery
    upstream = os.environ["JEVDRILL_TEST_URL"]
    assert urllib.parse.urlsplit(upstream).hostname == "127.0.0.1"
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    for name in PROXY_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    monkeypatch.setenv("no_proxy", "127.0.0.1,localhost")
    direct = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    judgments, unexpected = [], []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            kind = request_kind(body)
            if kind is None:
                unexpected.append({"path": self.path, "bytes": len(body)})
                self.send_response(500)
                self.end_headers()
                return
            if kind == "discovery":
                forwarded = urllib.request.Request(
                    upstream + self.path,
                    data=body,
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
                with direct.open(forwarded, timeout=5) as response:
                    answer = response.read()
            else:
                judgments.append({"path": self.path, "bytes": len(body)})
                answer = json.dumps(
                    {
                        "model": "jev-latest",
                        "answers": {"result": {"type": "noul", "noul": 1}},
                        "usage": {"input_tokens": 1, "output_tokens": 1},
                    }
                ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(answer)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}"
        assert url.strip() and upstream.strip()
        monkeypatch.setenv("JEVDRILL_TEST_URL", url)
        wrapper = tmp_path / "judged_observer.py"
        wrapper.write_text(JUDGED_WRAPPER)
        adapter.transport = JevDrillTransport(
            (os.environ["JEVDRILL_TEST_PYTHON"], str(wrapper)),
            tmp_path / "jev.sqlite",
            FIXTURES,
            json.loads((FIXTURES / "digests.json").read_text()),
        )
        repo = make_repo(tmp_path)
        roadmap = repo / "specs/phase-plans-v1.md"
        body = "# RUNNER\n\n## Lanes\n\n" + "".join(
            f"### SL-{index} - Task {index}\n- **Owned files**: `task-{index}.py`\n"
            for index in range(2)
        )
        result, tasks = runner.discover_jevdrill_work_units(
            adapter,
            inputs,
            plan_objective=lambda _value: write_phase_plan(repo, "RUNNER", roadmap, body=body),
        )
        assert result["status"] == "selected_guidance" and len(tasks) == 2
        value = linked_task(base, inputs, tasks[0], 0)
        value["route_inputs"]["judgment_policy"] = dict(JUDGMENT_POLICY)
        value["route_inputs"]["inventory"]["candidates"][0]["quality_sufficient"] = None
        adapter.inputs_for = lambda _context: deepcopy(value)
        adapter.prepare(mode="main", dry_run=False, **kwargs)
        decision = adapter.last_decision
        assert unexpected == []
        assert decision["status"] == "ready" and len(judgments) == 1
        # What JEV Drill itself recorded for the decision: the replay bundle's judgment record.
        with sqlite3.connect(tmp_path / "jev.sqlite") as db:
            (stored,) = db.execute(
                "SELECT bundle FROM decisions_v1 WHERE decision_id=?",
                (decision["details"]["routing_decision_id"],),
            ).fetchone()
        recorded = json.loads(stored)["judgments"] or {}
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    (Path(os.environ["JEVDRILL_TEST_ARTIFACTS"]) / "judged-task.json").write_text(
        json.dumps(
            {
                "flow": "judged",
                "task_id": tasks[0]["task_id"],
                "stored_function_revision": recorded.get("function_revision"),
                "stored_judgments": len(recorded.get("judgments") or {}),
                "loopback_judgment_requests": len(judgments),
                "decision_status": decision["status"],
                "routing_decision_id": decision["details"]["routing_decision_id"],
            }
        )
    )


def installed_transport(tmp_path):
    """The installed JEV Drill CLI, as test_real_bridge reaches it."""
    return JevDrillTransport(
        (os.environ["JEVDRILL_TEST_PYTHON"], "-m", "jevdrill.cli"),
        tmp_path / "jev.sqlite",
        FIXTURES,
        json.loads((FIXTURES / "digests.json").read_text()),
    )


# HOST SL-7, item 3. A separate process, standard library only and started with -I so that
# nothing of the host integration is on its path, opens the queue's file read-only and prints
# what each stored report holds. No public call lists stored reports, so this depends on the
# queue's private layout, table `reports`, column `payload` (jevdrill_queue.py:57-61 at the pin);
# each pin step re-checks it.
QUEUE_READER = """
import importlib.util, json, sqlite3, sys
from pathlib import Path
db = sqlite3.connect(Path(sys.argv[1]).as_uri() + "?mode=ro", uri=True, timeout=5)
rows = []
for (stored,) in db.execute("SELECT payload FROM reports"):
    event = json.loads(stored)["event"]
    body = event["payload"]
    names = ("execution_run_id", "task_id", "routing_decision_id", "source_id", "source_sequence")
    row = {name: event[name] for name in names}
    row.update(kind=body["kind"], event_type=body.get("event_type"))
    row.update(content=body.get("selected_run_id"))
    rows.append(row)
db.close()
host = importlib.util.find_spec("phase_loop_runtime") is not None
print(json.dumps({"rows": rows, "host_importable": host}))
"""


def read_queue(path):
    read = subprocess.run(
        [os.environ["JEVDRILL_TEST_PYTHON"], "-I", "-c", QUEUE_READER, str(path)],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return json.loads(read.stdout)


def test_explicit_reports_share_the_run_queue(tmp_path, monkeypatch):
    """Item 3: four explicit reports under two runs of one adapter, read by another process.

    Delivery is held: every report send fails as a disconnect before it reaches JEV Drill, so
    the queue keeps each row and nothing is delivered before the last read. Every hook call is
    serial, on this thread, and none is retried. The record holds observations only.
    """
    from phase_loop_runtime import launcher

    adapter, inputs, _, kwargs, _, _ = adapter_fixture(tmp_path)
    adapter.transport = installed_transport(tmp_path)
    actual_call = adapter.transport.call
    held = []

    def hold_reports(command, payload, **options):
        if command == "report":
            held.append(payload["event"]["event_id"])
            raise OSError("synthetic disconnect: delivery is held until the last read")
        return actual_call(command, payload, **options)

    adapter.transport.call = hold_reports
    spec = synthetic_spec(tmp_path, monkeypatch)
    runs, active, launched, sent = {}, {}, {}, []

    def explicit(label, run_id):
        others = [other for other in runs.values() if other != run_id]

        def sequences():
            return [adapter.run_event_identity(other)["next_source_sequence"] for other in others]

        before, counts, other_before = (
            adapter.run_event_identity(run_id),
            adapter.run_report_counts(run_id),
            sequences(),
        )
        content = str(uuid.uuid4())
        report = {"kind": "host_choice", "reason": label, "selected_run_id": content}
        try:
            answer = adapter.enqueue_run_event(run_id, report)
        except (KeyError, ValueError, RuntimeError, OSError, sqlite3.Error) as error:
            answer = "raised " + type(error).__name__
        sent.append(
            {
                "label": label,
                "run": run_id,
                "content": content,
                "answer": answer,
                "sequence_before": before["next_source_sequence"],
                "counts_before": counts,
                "counts_after": adapter.run_report_counts(run_id),
                "other_sequences": [other_before, sequences()],
            }
        )

    def launch_run(name, during):
        value = deepcopy(inputs)
        task_id = value["request"]["task_id"] = str(uuid.uuid4())
        value["request"]["envelope"].update(request_id=str(uuid.uuid4()), idempotency_key=name)
        adapter.inputs_for = lambda _context: deepcopy(value)
        prepared = adapter.prepare(mode="main", dry_run=False, **kwargs)

        def execute(launch_spec, **options):
            active[name] = list(adapter.active_execution_run_ids(task_id))
            runs[name] = active[name][0]
            during()
            return launcher.launch_with_spec(launch_spec, **options)

        result = adapter.launch(execute, replace(spec, prompt_bundle=prepared["prompt_bundle"]))
        launched[name] = result.jevdrill_execution_run["execution_run_id"]

    launch_run("A", lambda: explicit("E1", runs["A"]))
    explicit("E2", launched["A"])
    launch_run("B", lambda: explicit("E3", launched["A"]))
    explicit("E4", launched["B"])
    first = read_queue(adapter.queue.path)
    status_first = adapter.queue.status()
    identities = {name: adapter.run_event_identity(run) for name, run in launched.items()}
    envelope = inputs["request"]["envelope"]
    scope = {key: envelope[key] for key in ("project_id", "workspace_id")}
    scope.update(producer="synthetic-delete", operation=envelope["operation"])
    adapter.delete_task(scope, identities["A"]["task_id"])
    second = read_queue(adapter.queue.path)
    record = {
        "runs": launched,
        "active": active,
        "sent": sent,
        "identities": identities,
        "held_report_sends": len(held),
        "first_read": first,
        "status_first": status_first,
        "deleted_task": identities["A"]["task_id"],
        "second_read": second,
        "status_second": adapter.queue.status(),
    }
    (Path(os.environ["JEVDRILL_TEST_ARTIFACTS"]) / "explicit-reports.json").write_text(
        json.dumps({"explicit_reports": record})
    )


if sys.platform == "darwin":
    # HOST SL-7, item 8, macOS only. The machine identity is the boot session UUID, read from the
    # operating system by absolute path; it differs between machines and between boots. The
    # record holds only digests of it salted with a one-time value.
    MACHINE_IDENTITY = ("/usr/sbin/sysctl", "-n", "kern.bootsessionuuid")
    RENDEZVOUS_SECONDS = 20
    # Appended to the synthetic executor by synthetic_spec: after its protocol lines, the child
    # connects to the rendezvous, sends its pid, platform and digest, and waits to be released.
    LOCAL_CHILD = """
import hashlib, socket, subprocess
identity = subprocess.run({command!r}, capture_output=True, text=True, timeout=10, check=True)
identity = identity.stdout.strip()
assert identity
client = socket.socket(socket.AF_UNIX)
client.settimeout({bound})
client.connect({path!r})
digest = hashlib.sha256(({nonce!r} + identity).encode()).hexdigest()
message = {{"pid": os.getpid(), "platform": sys.platform, "digest": digest}}
client.sendall(json.dumps(message).encode() + b"\\n")
client.recv(1)
client.close()
"""

    def machine_digest(nonce):
        read = subprocess.run(
            MACHINE_IDENTITY, capture_output=True, text=True, timeout=10, check=False
        )
        identity = read.stdout.strip() if read.returncode == 0 else ""
        return hashlib.sha256((nonce + identity).encode()).hexdigest() if identity else None

    def process_row(pid):
        """[pid, parent pid] from the machine's process table, or None if it is absent."""
        found = subprocess.run(
            ("/bin/ps", "-o", "pid=,ppid=", "-p", str(pid)),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        ).stdout.split()
        return [int(value) for value in found] if len(found) == 2 else None

    def serve(listener, nonce, observed):
        try:
            connection, _ = listener.accept()
        except OSError:
            return
        with connection:
            connection.settimeout(RENDEZVOUS_SECONDS)
            message = json.loads(connection.makefile("rb").readline())
            observed.update(
                connected=True,
                pid_sent=message["pid"],
                child_platform=message["platform"],
                child_digest=message["digest"],
            )
            row = process_row(message["pid"])
            ancestry = [message["pid"]]
            observed["pid_found"] = row[0] if row else None
            while row and row[1] > 1 and ancestry[-1] != os.getpid() and len(ancestry) < 32:
                ancestry.append(row[1])
                row = process_row(row[1])
            observed.update(ancestry=ancestry, parent_digest=machine_digest(nonce))
            connection.sendall(b"\n")

    def test_ordinary_macos_launch_stays_local(tmp_path, monkeypatch):
        """Item 8: a routed, live launch with no lease authority, through the unpatched launcher.

        The rendezvous is a Unix-domain socket in a private directory, reachable only on this
        machine; it is closed and removed when the case ends. Every wait is bounded.
        """
        from phase_loop_runtime import launcher

        adapter, _, _, kwargs, _, _ = adapter_fixture(tmp_path)
        adapter.transport = installed_transport(tmp_path)
        nonce = secrets.token_hex(16)
        directory = tempfile.mkdtemp(prefix="jd8-", dir="/tmp")
        path = os.path.join(directory, "s")
        assert len(path.encode()) < 104
        listener = socket.socket(socket.AF_UNIX)
        observed = {"connected": False}
        result, refusal = None, None
        try:
            listener.bind(path)
            listener.listen(1)
            listener.settimeout(RENDEZVOUS_SECONDS)
            thread = threading.Thread(target=serve, args=(listener, nonce, observed), daemon=True)
            thread.start()
            tail = LOCAL_CHILD.format(
                command=MACHINE_IDENTITY, bound=RENDEZVOUS_SECONDS, path=path, nonce=nonce
            )
            spec = synthetic_spec(tmp_path, monkeypatch, tail=tail)
            prepared = adapter.prepare(mode="main", dry_run=False, **kwargs)
            spec = replace(spec, prompt_bundle=prepared["prompt_bundle"])
            try:
                result = adapter.launch(launcher.launch_with_spec, spec)
            except JevDrillUnavailable as error:
                refusal = str(error)
            thread.join(RENDEZVOUS_SECONDS + 10)
        finally:
            listener.close()
            shutil.rmtree(directory)
        observed.update(
            parent_pid=os.getpid(),
            parent_platform=sys.platform,
            returncode=result.returncode if result else None,
            available=result.available if result else None,
            unavailable_reason=result.unavailable_reason if result else None,
            refusal=refusal,
        )
        (Path(os.environ["JEVDRILL_TEST_ARTIFACTS"]) / "local-execution.json").write_text(
            json.dumps({"local_execution": observed})
        )
