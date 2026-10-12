import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
spec = importlib.util.spec_from_file_location(
    "host_verification", ROOT / "scripts/verify_host_phase.py"
)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def witness():
    runs = [
        {
            "task_id": f"task-{i}",
            "model": f"model-{i}",
            "effort": f"effort-{i}",
            "decision_id": f"decision-{i}",
            "discovery_ref": {"trace_digest": "a" * 64},
            "execution_run": {
                "task_id": f"task-{i}",
                "selected_plan_id": f"plan-{i}",
                "applied_plan_id": f"plan-{i}",
                "execution_run_id": f"run-{i}",
            },
        }
        for i in range(2)
    ]
    records = [
        {
            "flow": "discovery",
            "objective": name,
            "entered": ["main", "open_application", "discover", "next_question", "route"],
            "construction_events": ["planning.executor", "task.SL-0.route-v2"],
            "runs": copy.deepcopy(runs),
        }
        for name in ("alpha", "beta")
    ]
    records += [
        {
            "flow": "discovery-control",
            "fault": fault,
            "discovery_id": "discovery",
            "task_id": "task",
            "rejected_before_execution": True,
        }
        for fault in ("forged", "deleted", "stale_catalog", "relaxed", "decline")
    ]
    records += [
        {"task_family": family, "damaged": True, "objective_checks": {"independent": False}}
        for family in ("implementation", "review", "documentation")
    ]
    records += [
        {"task_family": family, "objective_checks": {"independent": True}}
        for family in ("implementation", "review", "documentation")
    ]
    return {
        "records": records,
        "assertions": [{"id": "entered", "outcome": "passed"}],
        "holdouts_opened": False,
        "promotion_eligible": False,
        "performance_claims": "insufficient_evidence",
    }


@pytest.mark.parametrize(
    "fault",
    [
        "old",
        "stale",
        "source_changed",
        "wrong_command",
        "missing_companion",
        "skipped",
        "fixture",
        "missing_decomposition",
        "one_task",
        "same_configuration",
        "flags_only",
        "holdout",
        "quality_claim",
        "duplicate",
        "failed_control",
        "fault_only_control",
        "missing_positive_checks",
        "installed_provenance",
        "integrated_command",
    ],
)
def test_reducer_rejects_invalid_receipts(monkeypatch, fault):
    monkeypatch.setattr(runner.route, "reduce_manifests", lambda *_a, **_k: [])
    command = runner.companion_command("python", Path("temporary"))
    assertions = [
        {"node_id": "tests/" + node, "outcome": "passed"} for node in runner.COMPANION_CONTROLS
    ]
    inherited = {
        "assertions": [
            {"node_id": node, "outcome": "passed"}
            for controls in runner.CONTROLS.values()
            for node in controls
        ]
    }
    manifest = {
        "schema_version": 2,
        "phase": "HOST",
        "os": "Linux",
        "python_minor": "3.13",
        "input_digest": "fixture",
        "source_stable": True,
        "route_regressions": inherited,
        "companion": {
            "installed_provenance": {
                "modules": json.loads((ROOT / "evidence/HOST/adapter-handoff.json").read_text())[
                    "companion_modules"
                ],
                "version": "0.7.20",
                "os": "Linux",
                "source_root_matches": True,
            },
            "command": command,
            "command_sha256": runner.digest_value(command),
            "input_digest": "companion",
            "source_stable": True,
            "exit_code": 0,
            "output_sha256": "a" * 64,
            "assertions": assertions,
            "assertions_sha256": runner.digest_value(assertions),
        },
        "witnesses": witness(),
        "fixture_digests": json.loads((ROOT / "evidence/HOST/adapter-handoff.json").read_text())[
            "schemas"
        ],
        "host_static": {
            "command": [
                "<python>",
                "-m",
                "ruff",
                "check",
                "tests/conformance",
                "research/evaluation/host",
            ],
            "exit_code": 0,
        },
        "duration_seconds": 1,
    }
    discovery_command = [
        "python",
        "-m",
        "pytest",
        "-q",
        "--override-ini=addopts=",
        "tests/test_jevdrill_discovery.py",
        "--junitxml=temporary/discovery.xml",
        "--basetemp=temporary/discovery-child",
    ]
    discovery = {
        "origin": "installed_companion_conformance_subprocess",
        "command": discovery_command,
        "command_sha256": runner.digest_value(discovery_command),
        "output_sha256": "a" * 64,
        "input_digest": "companion",
        "source_stable": True,
        "exit_code": 0,
        "assertions": assertions,
        "assertions_sha256": runner.digest_value(assertions),
    }
    manifest["witnesses"]["companion_discovery"] = discovery
    manifest["companion"]["integrated_discovery"] = discovery
    manifest["witness_sha256"] = runner.digest_value(manifest["witnesses"])
    assert (
        runner.reduce_manifests(
            [manifest], "fixture", "companion", required_platforms={("Linux", "3.13")}
        )
        == []
    )
    if fault == "old":
        manifest["schema_version"] = 1
    elif fault == "stale":
        manifest["input_digest"] = "stale"
    elif fault == "source_changed":
        manifest["source_stable"] = False
    elif fault == "wrong_command":
        manifest["companion"]["command"] = ["python", "--help"]
    elif fault == "missing_companion":
        manifest["companion"] = {}
    elif fault == "installed_provenance":
        manifest["companion"]["installed_provenance"]["source_root_matches"] = False
    elif fault == "integrated_command":
        discovery["command"] = ["python", "--help"]
        discovery["command_sha256"] = runner.digest_value(discovery["command"])
    elif fault == "skipped":
        manifest["companion"]["assertions"][0]["outcome"] = "skipped"
    elif fault == "fixture":
        manifest["fixture_digests"] = {}
    elif fault == "flags_only":
        manifest["witnesses"] = {"records": [], "entered": True, "decomposition": True}
    elif fault == "holdout":
        manifest["witnesses"]["holdouts_opened"] = True
    elif fault == "quality_claim":
        manifest["witnesses"]["performance_claims"] = "quality_gain"
    elif fault == "failed_control":
        inherited["assertions"][0]["outcome"] = "failed"
    elif fault == "fault_only_control":
        row = next(
            row
            for row in manifest["witnesses"]["records"]
            if row.get("flow") == "discovery-control"
        )
        row.pop("discovery_id")
    elif fault == "missing_positive_checks":
        manifest["witnesses"]["records"] = [
            row for row in manifest["witnesses"]["records"] if row.get("damaged") or row.get("flow")
        ]
    elif fault in ("missing_decomposition", "one_task", "same_configuration"):
        flow = manifest["witnesses"]["records"][0]
        if fault == "missing_decomposition":
            flow["construction_events"] = ["task.SL-0.route-v2"]
        elif fault == "one_task":
            flow["runs"] = flow["runs"][:1]
        else:
            flow["runs"][1]["model"] = flow["runs"][0]["model"]
    manifest["witness_sha256"] = runner.digest_value(manifest["witnesses"])
    receipts = [manifest, manifest] if fault == "duplicate" else [manifest]
    assert runner.reduce_manifests(
        receipts, "fixture", "companion", required_platforms={("Linux", "3.13")}
    )


def test_missing_companion_configuration_is_failure():
    assert "missing production witnesses" in runner.witness_errors(None)
