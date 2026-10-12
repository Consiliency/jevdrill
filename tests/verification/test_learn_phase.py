import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from jevdrill.analysis import aggregate_observations
from tests.analysis.test_observations import case

ROOT = Path(__file__).parents[2]
spec = importlib.util.spec_from_file_location(
    "learn_verifier", ROOT / "scripts/verify_learn_phase.py"
)
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


@pytest.fixture
def synthetic_reducer_input(tmp_path, discovery_inputs):
    # A unit-test input, never a collection receipt or phase acceptance artifact.
    inherited = json.loads((ROOT / "evidence/HOST/platforms/Linux-3.13.json").read_text())
    inherited["input_digest"] = verifier.host.input_digest(ROOT)
    inherited["route_regressions"]["input_digest"] = verifier.host.route.input_digest(ROOT)
    commands = verifier.host.route.commands_for(
        "python", tmp_path, "Linux", extra_test_paths=verifier.TEST_PATHS
    )
    for check in inherited["route_regressions"]["checks"]:
        check["command"] = commands[check["name"]]
        check["command_sha256"] = verifier.host.route.command_digest(check["command"])
    assertions = inherited["route_regressions"]["assertions"]
    known = {row["node_id"] for row in assertions}
    for nodes in verifier.CONTROLS.values():
        for node in nodes:
            if node not in known:
                assertions.append({"node_id": node, "outcome": "passed"})
    inherited["route_regressions"]["tests"]["total"] = len(assertions)
    inherited["route_regressions"]["assertions_sha256"] = verifier.host.route.command_digest(
        assertions
    )
    app, scope, context, _ = case(tmp_path, discovery_inputs)
    groups = aggregate_observations(app.storage.learning_observations(scope))
    first = groups[0]
    first.update(completed_count=1, incomplete_count=0)
    first["conditions"]["applied_configuration"] = first["conditions"]["selected_configuration"]
    first["conditions"]["applied_configuration_reason"] = "reported_selected_plan"
    first["applied_unknown_count"] = 0
    first["sources"][0]["execution_run_id"] = "00000000-0000-4000-8000-000000000009"
    second = copy.deepcopy(first)
    second["conditions"]["selected_model"] = "other"
    second["sources"][0].update(
        task_id="00000000-0000-4000-8000-000000000011",
        routing_decision_id="00000000-0000-4000-8000-000000000012",
        execution_run_id="00000000-0000-4000-8000-000000000013",
    )
    statuses = [
        "recorded",
        "recorded",
        "updated",
        "invalid",
        "invalid",
        "invalid",
        "deleted",
        "not_due",
    ]
    witness = {
        "origin": "installed_discovery_host_tasks_reports_analysis",
        "commands": [
            {
                "command": [
                    "python",
                    "-m",
                    "jevdrill.cli",
                    "--storage",
                    "synthetic.db",
                    "delete-discovery" if i == 6 else "analyze",
                ],
                "exit_code": 2 if 3 <= i <= 5 else 0,
                "response_status": status,
            }
            for i, status in enumerate(statuses)
        ],
        "construction_events": [
            "planning.build_launch_request",
            "planning.build_launch_spec",
            "planning.executor",
            "task.build_launch_request",
            "task.build_launch_spec",
            "task.executor",
        ],
        "observed_groups": [first, second],
        "deleted_groups": [],
        "performance_claims": "insufficient_evidence",
    }
    control_names = [
        "record_task",
        "record_task",
        "analyze_observations",
        "missing_discovery_ref",
        "forged_discovery_ref",
        "whole_skill_claim",
        "delete_objective",
        "deleted_objective_analysis",
    ]
    for index, record in enumerate(witness["commands"]):
        record.update(control=control_names[index], lineage=None, claim_scope=None)
    for index, group in enumerate((first, second)):
        witness["commands"][index]["lineage"] = {
            k: group["sources"][0][k] for k in ("task_id", "routing_decision_id", "discovery_ref")
        }
    witness["commands"][3]["lineage"] = dict(witness["commands"][0]["lineage"], discovery_ref=None)
    witness["commands"][4]["lineage"] = dict(
        witness["commands"][0]["lineage"],
        discovery_ref=dict(context["discovery_ref"], trace_digest="0" * 64),
    )
    witness["commands"][5]["claim_scope"] = "whole_skill"
    witness["commands"][6]["command"].extend(
        ["--work-objective-id", context["discovery_ref"]["work_objective_id"]]
    )
    witness["run_observations"] = []
    for group in (first, second):
        source = group["sources"][0]
        plan_id = "00000000-0000-4000-8000-000000000015"
        witness["run_observations"].append(
            {
                "source": copy.deepcopy(source),
                "selected_plan_id": plan_id,
                "lifecycle": [
                    {
                        "event_id": "00000000-0000-4000-8000-000000000016",
                        **{
                            k: source[k]
                            for k in ("task_id", "routing_decision_id", "execution_run_id")
                        },
                        "payload": {
                            "kind": "lifecycle",
                            "event_type": "completed",
                            "applied_plan_id": plan_id,
                            "reason": None,
                        },
                    }
                ],
                "inspection_command": [
                    "python",
                    "-m",
                    "jevdrill.cli",
                    "--storage",
                    "synthetic.db",
                    "inspect",
                    "--decision-id",
                    source["routing_decision_id"],
                    "--scope",
                    "{}",
                    "--replay",
                ],
                "inspection_exit_code": 0,
                "report_command": [
                    "python",
                    "-c",
                    "import json,sys;from pathlib import Path;from jevdrill.storage import SQLiteStorage;print(json.dumps(SQLiteStorage(Path(sys.argv[1])).project_run(json.loads(sys.argv[2]),sys.argv[3])))",
                    "synthetic.db",
                    "{}",
                    source["execution_run_id"],
                ],
                "report_exit_code": 0,
            }
        )
    extra = json.loads((ROOT / "evidence/HOST/companion/extra-Linux.json").read_text())
    return {
        "schema_version": 1,
        "phase": "LEARN",
        "os": "Linux",
        "python_minor": "3.13",
        "input_digest": verifier.input_digest(ROOT),
        "source_stable": True,
        "inherited_host": inherited,
        "companion_extras": extra,
        "module_provenance": {
            name: hashlib.sha256((ROOT / "src/jevdrill" / (name + ".py")).read_bytes()).hexdigest()
            for name in ("application", "storage", "analysis", "maintenance", "contracts")
        },
        "witness": witness,
        "witness_sha256": verifier.host.digest_value(witness),
        "learn_static": {"command": ["<python>", *verifier.LEARN_STATIC], "exit_code": 0},
        "duration_seconds": 100,
    }


def reduce(receipts):
    companion = json.loads((ROOT / "evidence/HOST/verification.json").read_text())[
        "companion_digest"
    ]
    return verifier.reduce_manifests(
        receipts, verifier.input_digest(ROOT), companion, required_platforms={("Linux", "3.13")}
    )


def test_reducer_accepts_complete_synthetic_input(synthetic_reducer_input):
    assert reduce([synthetic_reducer_input]) == []


@pytest.mark.parametrize(
    "alternative", ["not_reported", "different_plan", "reported_selected_plan"]
)
def test_reducer_binds_sorted_groups_and_applied_alternatives_to_authoritative_runs(
    synthetic_reducer_input, alternative
):
    receipt = copy.deepcopy(synthetic_reducer_input)
    group = receipt["witness"]["observed_groups"][0]
    if alternative != "reported_selected_plan":
        group["conditions"].update(
            applied_configuration="unknown", applied_configuration_reason=alternative
        )
        group["applied_unknown_count"] = 1
        receipt["witness"]["run_observations"][0]["lifecycle"][0]["payload"]["applied_plan_id"] = (
            None if alternative == "not_reported" else "00000000-0000-4000-8000-000000000098"
        )
    receipt["witness"]["observed_groups"].reverse()
    receipt["witness_sha256"] = verifier.host.digest_value(receipt["witness"])
    assert reduce([receipt]) == []


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "duplicate",
        "stale",
        "changed",
        "command",
        "assertion_origin",
        "skipped",
        "module_origin",
        "unlinked",
        "boolean",
        "wrong_witness_origin",
        "metric_only",
        "missing_extras",
        "cost",
        "digest",
        "malformed",
        "omitted_fault",
        "wrong_fault",
        "missing_run_records",
        "unrelated_run_unknown",
        "unsupported_unknown",
    ],
)
def test_reducer_rejects_missing_stale_wrong_origin_and_boolean_substitutes(
    synthetic_reducer_input, fault
):
    receipt = copy.deepcopy(synthetic_reducer_input)
    if fault == "missing":
        assert reduce([])
        return
    if fault == "duplicate":
        assert reduce([receipt, receipt])
        return
    if fault == "stale":
        receipt["input_digest"] = "0" * 64
    elif fault == "changed":
        receipt["source_stable"] = False
    elif fault == "command":
        receipt["witness"]["commands"][0]["command"][5] = "route"
    elif fault in {"assertion_origin", "skipped"}:
        node = verifier.CONTROLS["EC-LEARN-5"][0]
        row = next(
            r
            for r in receipt["inherited_host"]["route_regressions"]["assertions"]
            if r["node_id"] == node
        )
        row["node_id"] = "tests/other.py::forged" if fault == "assertion_origin" else node
        if fault == "skipped":
            row["outcome"] = "skipped"
        receipt["inherited_host"]["route_regressions"]["assertions_sha256"] = (
            verifier.host.route.command_digest(
                receipt["inherited_host"]["route_regressions"]["assertions"]
            )
        )
    elif fault == "module_origin":
        receipt["module_provenance"]["analysis"] = "0" * 64
    elif fault == "unlinked":
        receipt["witness"]["observed_groups"][0]["sources"][0]["discovery_ref"] = None
    elif fault == "boolean":
        receipt["witness"] = {"passed": True, "tasks": 2}
    elif fault == "wrong_witness_origin":
        receipt["witness"]["origin"] = "route_v1_only"
    elif fault == "metric_only":
        receipt["witness"]["observed_groups"][0].pop("sources")
    elif fault == "missing_extras":
        receipt["companion_extras"] = {}
    elif fault == "cost":
        receipt["duration_seconds"] = 601
    elif fault == "digest":
        receipt["witness_sha256"] = "0" * 64
    elif fault == "malformed":
        receipt["os"] = {"simulated": "Linux"}
    elif fault == "omitted_fault":
        receipt["witness"]["commands"][3].pop("control")
    elif fault == "wrong_fault":
        receipt["witness"]["commands"][4]["lineage"]["discovery_ref"] = receipt["witness"][
            "observed_groups"
        ][0]["sources"][0]["discovery_ref"]
    elif fault == "missing_run_records":
        receipt["witness"].pop("run_observations")
    elif fault in {"unrelated_run_unknown", "unsupported_unknown"}:
        group = receipt["witness"]["observed_groups"][0]
        group["conditions"].update(
            applied_configuration="unknown", applied_configuration_reason="not_reported"
        )
        group["applied_unknown_count"] = 1
        if fault == "unrelated_run_unknown":
            receipt["witness"]["run_observations"][0]["lifecycle"][0]["execution_run_id"] = (
                "00000000-0000-4000-8000-000000000099"
            )
    if fault != "digest":
        receipt["witness_sha256"] = verifier.host.digest_value(receipt["witness"])
    assert reduce([receipt])


def test_windows_extra_command_requires_process_and_storage_controls():
    expected = verifier.extra_arguments("Windows")
    assert expected[-2:] == ["tests/test_windows_processes.py", "tests/test_windows_storage.py"]
    assert verifier.extra_arguments("Darwin") == verifier.EXTRA_COMMAND
