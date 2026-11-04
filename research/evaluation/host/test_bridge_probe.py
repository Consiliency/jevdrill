"""Controlled executors through real host entrypoints and the installed JEV CLI.

Run with the companion interpreter; the two BAML runtimes stay in separate processes.
Provider authentication and output are synthetic. Routing, reporting, launch construction,
the final subprocess and durable storage use production implementations.
"""

import json
import os
import sqlite3
import sys
import time
from copy import deepcopy
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

CASES = json.loads(Path(__file__).with_name("protocol.json").read_text())["cases"]
RUNS = [
    (mode, True, index, False)
    for index, mode in enumerate(["main", "delegated", "lane", "main", "delegated", "lane"])
]
RUNS += [(mode, True, index, True) for mode, index in [("main", 0), ("delegated", 2), ("lane", 4)]]
RUNS += [(mode, False, 0, False) for mode in ("main", "delegated", "lane")]


@pytest.mark.parametrize("entrypoint,permitted,case_index,damaged", RUNS)
def test_real_bridge(tmp_path, monkeypatch, entrypoint, permitted, case_index, damaged):
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
    if not permitted:
        adapter.capabilities_for = lambda _: ([], [])
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
        (Path(os.environ["JEVDRILL_TEST_ARTIFACTS"]) / f"permission-{entrypoint}.json").write_text(
            json.dumps(
                {
                    "control": "permission_denial",
                    "entrypoint": entrypoint,
                    "entered": entered,
                    "launched": len(completed),
                }
            )
        )
    for path in tmp_path.glob("*.sqlite*"):
        assert b"PRIVATE_OUTPUT_SENTINEL" not in path.read_bytes()
