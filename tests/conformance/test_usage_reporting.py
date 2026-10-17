"""Installed transport checks with a separate companion interpreter and synthetic tokens."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

CASES = (
    "known",
    "missing",
    "lagged",
    "unsupported",
    "nonzero",
    "timeout",
    "stall",
    "abrupt",
    "startup_warning",
    "startup_loss",
    "recorded_usage",
)
SENTINELS = (
    "SYNTHETIC_PRIVATE_TASK",
    "PRIVATE_OUTPUT_SENTINEL",
    "PRIVATE_REASONING_SENTINEL",
    "PRIVATE_CREDENTIAL_SENTINEL",
)


def _probe(directory, case):
    import sqlite3
    import time
    from copy import deepcopy
    from dataclasses import replace

    import pytest
    from phase_loop_runtime import launcher
    from phase_loop_runtime.jevdrill_adapter import JevDrillTransport
    from phase_loop_runtime.jevdrill_queue import ReportQueue
    from test_jevdrill_adapter import FIXTURES, adapter_fixture
    from test_jevdrill_usage import records, synthetic_spec, values

    supported_capture = sys.platform.startswith("linux")
    executable = os.environ["JEVDRILL_TEST_CLI"]
    installed_python = str(
        Path(executable).parent / ("python.exe" if os.name == "nt" else "python")
    )
    cli_argv = (installed_python, "-m", "jevdrill.cli") if os.name == "nt" else (executable,)

    adapter, inputs, _, kwargs, _, _ = adapter_fixture(directory)
    storage = directory / "jev.sqlite"
    adapter.transport = JevDrillTransport(
        cli_argv,
        storage,
        FIXTURES,
        json.loads((FIXTURES / "digests.json").read_text()),
    )
    actual = adapter.transport.call
    submitted, acknowledgments = [], []
    lost = False

    def deliver(command, payload, **options):
        nonlocal lost
        response = actual(command, payload, **options)
        if command == "report":
            submitted.append(deepcopy(payload))
            acknowledgments.append(response)
            if payload["event"]["payload"]["kind"] == "usage" and not lost:
                lost = True
                raise OSError("synthetic acknowledgment loss after durable commit")
        return response

    adapter.transport.call = deliver
    prepared = adapter.prepare(mode="main", dry_run=False, **kwargs)
    assert prepared["json_output"] is True
    lines = records()
    recorded = None
    fixture_path = Path(__file__).parent / "fixtures/codex-0.159.2-v2-usage.json"
    if case == "recorded_usage":
        recorded = json.loads(fixture_path.read_text())
        captured_values = values(recorded["usage"])
        lines = records(
            {
                ("reasoning_output_tokens" if key == "reasoning_tokens" else key): value["value"]
                for key, value in captured_values.items()
            }
        )
    if case in ("missing", "abrupt"):
        lines = lines[:-1]
    if case == "lagged":
        lines = records(
            middle=[
                (
                    '{"type":"item.completed","item":{"type":"error",'
                    '"message":"in-process app-server event stream lagged; dropped 1 event"}}'
                )
            ]
        )
    if case in ("startup_warning", "startup_loss", "recorded_usage"):
        message = (
            "synthetic configuration warning PRIVATE_OUTPUT_SENTINEL"
            if case in ("startup_warning", "recorded_usage")
            else "in-process app-server event stream lagged; dropped 1 event"
        )
        lines.insert(
            1,
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {"id": "synthetic-warning", "type": "error", "message": message},
                }
            ),
        )
    lines.insert(
        3 if case in ("startup_warning", "startup_loss", "recorded_usage") else 2,
        '{"type":"item.completed","item":{"type":"reasoning","text":"PRIVATE_REASONING_SENTINEL"}}',
    )
    tail = "print('PRIVATE_OUTPUT_SENTINEL PRIVATE_CREDENTIAL_SENTINEL',file=sys.stderr,flush=True)"
    if case in ("nonzero", "abrupt"):
        tail += "\nsys.exit(7)"
    elif case in ("timeout", "stall"):
        tail += "\nsignal.signal(signal.SIGTERM,lambda *_: sys.exit(0)); time.sleep(10)"
    with pytest.MonkeyPatch.context() as patch:
        spec = synthetic_spec(
            directory,
            patch,
            lines=lines,
            tail=tail,
            version="codex-cli 0.159.1" if case == "unsupported" else "codex-cli 0.159.2",
        )
        spec = replace(
            spec,
            prompt_bundle=prepared["prompt_bundle"],
            launch_timeout_seconds=0.25 if case == "timeout" else None,
        )
        if recorded:
            spec = replace(
                spec,
                codex_output_schema=recorded["output_schema"],
                command=[
                    *spec.command[:-1],
                    "--output-schema",
                    launcher.CODEX_OUTPUT_SCHEMA_PLACEHOLDER,
                    spec.delivery_payload(),
                ],
            )
        options = {}
        if case == "stall":
            original = launcher.run_heartbeat_summary

            def heartbeat(**kw):
                summary = original(**kw)
                summary["stalled_suspect"] = summary.get("elapsed_seconds", 0) >= 1
                return summary

            patch.setattr(launcher, "run_heartbeat_summary", heartbeat)
            options["heartbeat_interval_seconds"] = 0
        result = adapter.launch(launcher.launch_with_spec, spec, **options)
    input_ok = None
    if recorded and supported_capture:

        def component(data):
            return {"byte_count": len(data), "sha256": hashlib.sha256(data).hexdigest()}

        input_ok = result.executor_input_manifest == {
            "method": "codex_executor_input_v1",
            "scope": "prepared_submission",
            "encoding": "utf-8",
            "prompt": component(spec.delivery_payload().encode()),
            "output_schema": component(
                (json.dumps(recorded["output_schema"], sort_keys=True) + "\n").encode()
            ),
            "output_schema_status": "observed",
            "provider_context": "unknown",
            "provider_receipt": "unknown",
        }
        assert input_ok
        assert result.jevdrill_usage == recorded["usage"]
    if not supported_capture:
        assert result.jevdrill_usage is None
        assert result.executor_input_manifest is None
    assert "PRIVATE_OUTPUT_SENTINEL" in result.output
    identity = result.jevdrill_execution_run
    assert identity["selected_plan_id"] == identity["applied_plan_id"]
    # Resume sending from a newly opened persistent queue after acknowledgment loss.
    adapter.flush()
    adapter.flush()
    adapter.queue = ReportQueue(
        adapter.queue.path, sanitize=adapter.sanitize_report, clock=lambda: time.time() + 10
    )
    adapter.flush()
    assert adapter.queue.status()["records"] == 0
    assert acknowledgments[-1]["status"] == "duplicate" and acknowledgments[-1]["durable"] is True
    with sqlite3.connect(storage) as db:
        events = [
            json.loads(row[0])
            for row in db.execute(
                "SELECT payload FROM events_v1 ORDER BY json_extract(payload,'$.source_sequence')"
            )
        ]
    assert len(events) == 3
    usage = [event["payload"] for event in events if event["payload"]["kind"] == "usage"]
    assert len(usage) == 1
    token_values = {key: value for key, value in values(usage[0]).items() if key.endswith("tokens")}
    known = supported_capture and case in (
        "known",
        "nonzero",
        "timeout",
        "stall",
        "startup_warning",
        "recorded_usage",
    )
    if known:
        assert {row["method"] for row in usage[0]["measurements"][1:5]} == {
            "codex_exec_jsonl_0_159_2_v2"
        }
        expected_values = {
            "input_tokens": {"kind": "known", "unit": "tokens", "value": 100},
            "output_tokens": {"kind": "known", "unit": "tokens", "value": 20},
            "cached_input_tokens": {"kind": "known", "unit": "tokens", "value": 0},
            "reasoning_tokens": {"kind": "known", "unit": "tokens", "value": 5},
        }
        assert token_values == (captured_values if recorded else expected_values)
        if recorded:
            reported = {row["metric_id"]: row for row in usage[0]["measurements"]}
            assert all(
                reported[row["metric_id"]] == row for row in recorded["usage"]["measurements"]
            )
    else:
        assert all(
            value == {"kind": "unknown", "reason": "not_reported"}
            for value in token_values.values()
        )
    if supported_capture and case == "startup_loss":
        assert result.jevdrill_protocol_diagnostics["reason"] == "announced_event_loss"
    if supported_capture and case == "startup_warning":
        assert result.jevdrill_protocol_diagnostics["item_counts"]["error"] == 1
    terminal = "failed" if case in ("nonzero", "timeout", "stall", "abrupt") else "completed"
    assert events[1]["payload"]["event_type"] == terminal
    assert events[1]["payload"]["applied_plan_id"] == identity["selected_plan_id"]
    assert usage[0]["measurements"][-1]["measurement_value"]["kind"] == "unknown"
    # Remove the controlled executor: SQLite replay must work without launching it.
    child = directory / "codex"
    child.unlink()
    scope = {key: inputs["request"]["envelope"][key] for key in ("project_id", "workspace_id")}
    scope.update(producer=inputs["request"]["envelope"]["harness_id"], operation="route")
    replayed = subprocess.run(
        [
            *cli_argv,
            "--storage",
            str(storage),
            "inspect",
            "--replay",
            "--decision-id",
            adapter.last_decision["details"]["routing_decision_id"],
            "--scope",
            json.dumps(scope),
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=5,
    )
    assert replayed.returncode == 0, replayed.stderr
    replay = json.loads(replayed.stdout)
    assert replay == adapter.last_decision
    projected = subprocess.run(
        [
            installed_python,
            "-c",
            (
                "import json,sys; from pathlib import Path; from jevdrill.storage import SQLiteStorage; "
                "print(json.dumps(SQLiteStorage(Path(sys.argv[1])).project_run(json.loads(sys.argv[2]),sys.argv[3])))"
            ),
            str(storage),
            json.dumps(scope),
            identity["execution_run_id"],
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=5,
    )
    assert projected.returncode == 0, projected.stderr
    projection = json.loads(projected.stdout)
    assert projection["events"] == events and projection["status"] == terminal
    for path in directory.rglob("*.sqlite*"):
        if path.is_file():
            raw = path.read_bytes()
            assert not any(sentinel.encode() in raw for sentinel in SENTINELS)
    result_record = {
        "case": case,
        "provenance": "synthetic_local_codex",
        "provider_execution": False,
        "known": known,
        "capture_supported": supported_capture,
        "token_values": token_values,
        "usage_events": 1,
        "durable_replay": True,
        "queue_restart": True,
        "duplicate_ack": True,
        "privacy_passed": True,
        "executor_invocations_on_replay": 0,
        "terminal": terminal,
        "applied_identity_preserved": True,
    }
    if recorded and supported_capture:
        result_record.update(
            provenance="recorded_receipt_with_synthetic_execution",
            fixture_sha256=hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
            original_result_sha256=recorded["original_result_sha256"],
            input_manifest_verified=input_ok,
            recorded_receipt_preserved=True,
        )
    return result_record


@pytest.mark.parametrize("case", CASES)
def test_installed_usage_persistence(tmp_path, case):
    companion_root = os.environ.get("JEVDRILL_AGENT_HARNESS_ROOT")
    cli = os.environ.get("JEVDRILL_TEST_CLI")
    assert companion_root and cli, "Explicit companion checkout and installed CLI are required"
    companion = Path(companion_root) / "phase-loop-runtime"
    python = companion / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    assert python.is_file() and Path(cli).is_file()
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.endswith(("_API_KEY", "_TOKEN", "_SECRET")) and key != "PYTHONHOME"
    }
    env["PYTHONPATH"] = os.pathsep.join((str(companion / "src"), str(companion / "tests")))
    result = subprocess.run(
        [str(python), str(Path(__file__).resolve()), "--probe", str(tmp_path), case],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    record = json.loads(result.stdout)
    assert record["case"] == case and record["privacy_passed"] is True
    if output := os.environ.get("JEVDRILL_USAGE_ARTIFACTS"):
        Path(output, case + ".json").write_text(json.dumps(record) + "\n")


if __name__ == "__main__":
    assert sys.argv[1] == "--probe"
    print(json.dumps(_probe(Path(sys.argv[2]), sys.argv[3])))
