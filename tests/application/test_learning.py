import copy
import json
import os
import subprocess
import sys
from pathlib import Path


def analysis_request(scope, context=None, action="analyze"):
    return {
        "schema_version": "1",
        "scope": scope,
        "action": action,
        "context": context,
        "objectives": [],
        "minimum_batch": 1,
        "interval_seconds": 60,
        "include_user_wide": False,
        "settings_layers": [{"source": "request", "values": {"local_analysis_enabled": True}}],
    }


def test_analysis_batch_interval_objective_history_and_immutable_replay(tmp_path, monkeypatch):
    from jevdrill.contracts import canonical_digest
    from tests.analysis.test_observations import case

    app, scope, context, decision = case(tmp_path)
    request = analysis_request(scope)
    request["objectives"] = [decision["details"]["optimization_objective"]]
    before = canonical_digest(app.replay(scope, context["routing_decision_id"]))
    monkeypatch.setattr("jevdrill.application.time", lambda: 100)
    assert app.analyze(dict(request, minimum_batch=5))["status"] == "not_due"
    monkeypatch.setattr("jevdrill.application.time", lambda: 161)
    first = app.analyze(dict(request, minimum_batch=5))
    assert first["status"] == "updated"
    assert app.analyze(request)["status"] == "not_due"
    request["objectives"] = [
        dict(request["objectives"][0], version="reclassified-v2", direction="maximize")
    ]
    second = app.analyze(request)
    assert second["status"] == "updated" and len(second["objective_history"]) == 2
    assert second["groups"] == first["groups"]
    assert all(a["classification"] == "insufficient_evidence" for a in second["assessments"])
    assert canonical_digest(app.replay(scope, context["routing_decision_id"])) == before


def test_settings_optout_exclusions_and_disabled_model_analysis_enter_application(
    tmp_path, monkeypatch
):
    import pytest

    from jevdrill.contracts import ContractError
    from tests.analysis.test_observations import case

    app, scope, context, _ = case(tmp_path)
    monkeypatch.setattr(app, "route", lambda *_: pytest.fail("analysis recursively routed"))
    request = analysis_request(scope)
    assert app.analyze(dict(request, settings_layers=[]))["status"] == "denied"
    excluded = copy.deepcopy(request)
    excluded["settings_layers"][0]["values"]["excluded_paths"] = ["private"]
    assert app.analyze(excluded)["groups"] == []
    model = copy.deepcopy(request)
    model["settings_layers"][0]["values"]["model_analysis_enabled"] = True
    assert app.analyze(model)["status"] == "updated"
    with pytest.raises(ContractError):
        app.analyze(dict(model, model_budget=10, analysis_mode="model_assisted"))
    context["local_analysis_enabled"] = False
    app.analyze(analysis_request(scope, context, "record"))
    assert app.analyze(request)["groups"] == []


def _installed_worker(root, tmp, jevpython):
    import pytest
    import test_jevdrill_discovery as flow

    artifacts = tmp / "artifacts"
    artifacts.mkdir()
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("JEVDRILL_TEST_PYTHON", jevpython)
        patch.setenv(
            "JEVDRILL_TEST_CLI",
            str(Path(jevpython).parent / ("jevdrill.exe" if os.name == "nt" else "jevdrill")),
        )
        patch.setenv("JEVDRILL_TEST_ARTIFACTS", str(artifacts))
        original = flow.linked_task

        def consenting(*args):
            value = original(*args)
            value["route_inputs"]["settings_layers"] = [
                {"source": "request", "values": {"local_analysis_enabled": True}}
            ]
            return value

        patch.setattr(flow, "linked_task", consenting)
        generator = flow.installed_discovery.__wrapped__(tmp, patch)
        fixture = next(generator)
        try:
            flow.test_installed_discovery_decomposition_two_task_launch(fixture, tmp, "alpha")
            _adapter, inputs, _base, *_ = fixture
            envelope = inputs["envelope"]
            scope = {
                "project_id": envelope["project_id"],
                "workspace_id": envelope["workspace_id"],
                "producer": envelope["harness_id"],
                "operation": "route",
            }
            record = json.loads((artifacts / "discovery-alpha.json").read_text())
            command = [jevpython, "-m", "jevdrill.cli", "--storage", str(tmp / "jev.sqlite")]
            commands = []

            def call(name, payload, *flags, expected=0, control="record_task"):
                argv = command + [name, *flags]
                result = subprocess.run(
                    argv,
                    input=json.dumps(payload) if payload is not None else None,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                assert result.returncode == expected, result.stdout + result.stderr
                context = payload.get("context") if payload else None
                commands.append(
                    {
                        "command": argv,
                        "exit_code": result.returncode,
                        "response_status": json.loads(result.stdout)["status"],
                        "control": control,
                        "lineage": {
                            key: context[key]
                            for key in ("task_id", "routing_decision_id", "discovery_ref")
                        }
                        if context
                        else None,
                        "claim_scope": payload.get("evidence_scope") if payload else None,
                    }
                )
                return json.loads(result.stdout)

            contexts = []
            for run in record["runs"]:
                context = {
                    "task_id": run["task_id"],
                    "routing_decision_id": run["decision_id"],
                    "discovery_ref": run["discovery_ref"],
                    "task_family": "implementation",
                    "task_group": "native-host",
                    "environment_revision": "synthetic-host-v1",
                    "isolation_revision": "isolated-v1",
                    "evaluator_ref": "checks-v1",
                    "rubric_revision": "v1",
                    "local_analysis_enabled": True,
                    "share_user_wide": False,
                }
                contexts.append(context)
                assert (
                    call("analyze", analysis_request(scope, context, "record"))["status"]
                    == "recorded"
                )
            observed = call("analyze", analysis_request(scope), control="analyze_observations")
            assert observed["status"] == "updated"
            assert (
                len(observed["groups"]) == 2
                and sum(g["completed_count"] for g in observed["groups"]) == 2
            )
            assert len({g["conditions"]["selected_model"] for g in observed["groups"]}) == 2
            assert all(
                g["sources"][0]["discovery_ref"] == contexts[0]["discovery_ref"]
                for g in observed["groups"]
            )
            run_observations = []
            for group in observed["groups"]:
                source = group["sources"][0]
                inspected = subprocess.run(
                    command
                    + [
                        "inspect",
                        "--decision-id",
                        source["routing_decision_id"],
                        "--scope",
                        json.dumps(scope),
                        "--replay",
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=10,
                )
                replay = json.loads(inspected.stdout)
                report_command = [
                    jevpython,
                    "-c",
                    "import json,sys;from pathlib import Path;from jevdrill.storage import SQLiteStorage;print(json.dumps(SQLiteStorage(Path(sys.argv[1])).project_run(json.loads(sys.argv[2]),sys.argv[3])))",
                    str(tmp / "jev.sqlite"),
                    json.dumps(scope),
                    source["execution_run_id"],
                ]
                reported = subprocess.run(
                    report_command, capture_output=True, text=True, check=True, timeout=10
                )
                lifecycle = [
                    e
                    for e in json.loads(reported.stdout)["events"]
                    if e["execution_run_id"] == source["execution_run_id"]
                    and e["task_id"] == source["task_id"]
                    and e["routing_decision_id"] == source["routing_decision_id"]
                    and e["payload"]["kind"] == "lifecycle"
                ]
                run_observations.append(
                    {
                        "source": source,
                        "selected_plan_id": replay["execution_plan"]["execution_plan_id"],
                        "lifecycle": [
                            {
                                k: e[k]
                                for k in (
                                    "event_id",
                                    "task_id",
                                    "routing_decision_id",
                                    "execution_run_id",
                                    "payload",
                                )
                            }
                            for e in lifecycle
                        ],
                        "inspection_command": command
                        + [
                            "inspect",
                            "--decision-id",
                            source["routing_decision_id"],
                            "--scope",
                            json.dumps(scope),
                            "--replay",
                        ],
                        "inspection_exit_code": inspected.returncode,
                        "report_command": report_command,
                        "report_exit_code": reported.returncode,
                    }
                )
            for control, context in (
                ("missing_discovery_ref", dict(contexts[0], discovery_ref=None)),
                (
                    "forged_discovery_ref",
                    dict(
                        contexts[0],
                        discovery_ref=dict(contexts[0]["discovery_ref"], trace_digest="0" * 64),
                    ),
                ),
            ):
                assert (
                    call(
                        "analyze",
                        analysis_request(scope, context, "record"),
                        expected=2,
                        control=control,
                    )["status"]
                    == "invalid"
                )
            assert (
                call(
                    "analyze",
                    dict(analysis_request(scope), evidence_scope="whole_skill"),
                    expected=2,
                    control="whole_skill_claim",
                )["status"]
                == "invalid"
            )
            call(
                "delete-discovery",
                None,
                "--work-objective-id",
                contexts[0]["discovery_ref"]["work_objective_id"],
                "--scope",
                json.dumps(dict(scope, producer="other", operation="discover")),
                control="delete_objective",
            )
            assert (
                call("analyze", analysis_request(scope), control="deleted_objective_analysis")[
                    "groups"
                ]
                == []
            )
            return {
                "origin": "installed_discovery_host_tasks_reports_analysis",
                "commands": commands,
                "construction_events": record["construction_events"],
                "observed_groups": observed["groups"],
                "run_observations": run_observations,
                "deleted_groups": [],
                "performance_claims": "insufficient_evidence",
            }
        finally:
            generator.close()


def test_installed_discovery_host_tasks_reports_analysis_and_entered_denials(tmp_path):
    configured = os.environ.get("JEVDRILL_AGENT_HARNESS_ROOT")
    assert configured, "Explicit installed companion is required"
    runtime = Path(configured) / "phase-loop-runtime"
    python = os.environ.get(
        "JEVDRILL_AGENT_HARNESS_PYTHON",
        str(runtime / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")),
    )
    assert Path(python).is_file()
    env = dict(
        os.environ, PYTHONPATH=os.pathsep.join([str(runtime / "src"), str(runtime / "tests")])
    )
    result = subprocess.run(
        [
            python,
            str(Path(__file__).resolve()),
            "--worker",
            str(Path(__file__).parents[2]),
            str(tmp_path),
            sys.executable,
        ],
        cwd=runtime,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    witness = json.loads(result.stdout)
    assert len(witness["observed_groups"]) == 2 and witness["deleted_groups"] == []
    if output := os.environ.get("JEVDRILL_LEARN_WITNESS"):
        Path(output).write_text(json.dumps(witness, sort_keys=True, indent=2) + "\n")


if __name__ == "__main__":
    print(json.dumps(_installed_worker(Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4])))
