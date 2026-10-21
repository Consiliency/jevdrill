import copy
import hashlib
import importlib.util
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from tests.verification.test_learn_phase import (
    synthetic_reducer_input as synthetic_reducer_input,  # noqa: PLC0414 -- pytest fixture
)

ROOT = Path(__file__).parents[2]
SPEC = importlib.util.spec_from_file_location(
    "experiment_checks", ROOT / "scripts/verify_experiment_phase.py"
)
checks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checks)


@pytest.fixture
def synthetic_experiment(synthetic_reducer_input):
    inherited = copy.deepcopy(synthetic_reducer_input)
    assertions = inherited["inherited_host"]["route_regressions"]["assertions"]
    known = {row["node_id"] for row in assertions}
    for nodes in checks.CONTROLS.values():
        assertions.extend(
            {"node_id": node, "outcome": "passed"} for node in nodes if node not in known
        )
    route = inherited["inherited_host"]["route_regressions"]
    commands = checks.learn.host.route.commands_for(
        "python", Path("temporary"), "Linux", extra_test_paths=checks.TEST_PATHS
    )
    for check in route["checks"]:
        check["command"] = commands[check["name"]]
        check["command_sha256"] = checks.learn.host.route.command_digest(check["command"])
    route["tests"]["total"] = len(assertions)
    route["assertions_sha256"] = checks.learn.host.route.command_digest(assertions)
    return {
        "schema_version": 1,
        "phase": "EXPERIMENT",
        "os": "Linux",
        "python_minor": "3.13",
        "input_digest": checks.input_digest(ROOT),
        "source_stable": True,
        "inherited_learn": inherited,
        "module_provenance": {
            name: hashlib.sha256(
                (ROOT / "src/jevdrill" / (name.replace(".", "/") + ".py")).read_bytes()
            ).hexdigest()
            for name in checks.MODULES
        },
        "experiment_static": {"command": ["<python>", *checks.STATIC], "exit_code": 0},
        "native_internal_support": "configured_linux_only",
        "duration_seconds": 120,
    }


def reduce(receipts):
    return checks.reduce_manifests(
        receipts,
        checks.input_digest(ROOT),
        json.loads((ROOT / "evidence/HOST/verification.json").read_text())["companion_digest"],
        required_platforms={("Linux", "3.13")},
    )


def test_native_static_timeout_is_preserved_as_failed_receipt(monkeypatch):
    monkeypatch.setattr(checks.learn, "collect", lambda *_, **__: {"preserved": True})

    def timeout(*args, **kwargs):
        raise checks.subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(checks.subprocess, "run", timeout)
    receipt = checks.collect(ROOT, ROOT)
    assert receipt["inherited_learn"] == {"preserved": True}
    assert receipt["experiment_static"]["exit_code"] == 125
    assert (
        receipt["experiment_static"]["output_sha256"]
        == hashlib.sha256(b"TimeoutExpired").hexdigest()
    )


def test_reducer_accepts_executed_parameterized_control_and_rejects_omission(synthetic_experiment):
    route = synthetic_experiment["inherited_learn"]["inherited_host"]["route_regressions"]
    control = next(node for node in checks.CONTROLS["EC-EXPERIMENT-4"] if "guarded_driver" in node)
    row = next(row for row in route["assertions"] if row["node_id"] == control)
    row["node_id"] = control + "[0-None]"
    route["assertions_sha256"] = checks.learn.host.route.command_digest(route["assertions"])
    assert reduce([synthetic_experiment]) == []
    route["assertions"].remove(row)
    route["tests"]["total"] -= 1
    route["assertions_sha256"] = checks.learn.host.route.command_digest(route["assertions"])
    assert "missing EXPERIMENT assertion: " + control in reduce([synthetic_experiment])


@pytest.mark.parametrize("control", sorted(checks.learn.host.route.CONTROL_COUNTS))
def test_reducer_rejects_missing_inherited_route_parameter(synthetic_experiment, control):
    assert reduce([synthetic_experiment]) == []
    route = synthetic_experiment["inherited_learn"]["inherited_host"]["route_regressions"]
    row = next(
        row
        for row in route["assertions"]
        if row["node_id"] == control or row["node_id"].startswith(control + "[")
    )
    route["assertions"].remove(row)
    route["tests"]["total"] -= 1
    route["assertions_sha256"] = checks.learn.host.route.command_digest(route["assertions"])
    assert "missing executed control: " + control in reduce([synthetic_experiment])


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "missing",
        "duplicate",
        "stale",
        "changed",
        "module",
        "static",
        "controls",
        "inherited",
        "cost",
        "malformed",
        "native_capabilities",
    ],
)
def test_original_reducer_requires_current_native_controls(synthetic_experiment, fault):
    receipt = synthetic_experiment
    if fault == "missing":
        assert reduce([])
        return
    if fault == "duplicate":
        assert reduce([receipt, receipt])
        return
    if fault == "stale":
        receipt["input_digest"] = "wrong"
    elif fault == "changed":
        receipt["source_stable"] = False
    elif fault == "module":
        receipt["module_provenance"]["experiments"] = "wrong"
    elif fault == "static":
        receipt["experiment_static"]["command"] = ["fixture"]
    elif fault == "controls":
        receipt["inherited_learn"]["inherited_host"]["route_regressions"]["assertions"].pop()
    elif fault == "inherited":
        receipt["inherited_learn"] = None
    elif fault == "cost":
        receipt["duration_seconds"] = 601
    elif fault == "malformed":
        receipt["os"] = {"fake": "Linux"}
    elif fault == "native_capabilities":
        receipt["native_internal_support"] = "all_hosts_supported"
    assert bool(reduce([receipt])) is (fault is not None)


def test_software_success_cannot_close_missing_empirical_gates(synthetic_experiment):
    assert not reduce([synthetic_experiment])
    assert checks.empirical_errors(ROOT) == [
        "Q12/Q13 family-specific empirical calibration unresolved",
        "authorized preregistered linked discovery/routing development study missing",
    ]


@pytest.mark.parametrize(
    "fault",
    [None, "fake_checks", "missing_check", "wrong_command", "wrong_image", "mutated_artifact"],
)
def test_operational_reducer_requires_exact_named_checks_commands_image_and_artifacts(
    tmp_path, fault
):
    script = tmp_path / "scripts/verify_development_runtime.py"
    script.parent.mkdir()
    shutil.copyfile(ROOT / "scripts/verify_development_runtime.py", script)
    spec = importlib.util.spec_from_file_location("synthetic_operational_reducer_controls", script)
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    directory = tmp_path / ".phase-loop/runs/synthetic-mutation-control"
    directory.mkdir(parents=True)
    for filename, expected in (
        ("tests.xml", dict.fromkeys(runtime.RUNTIME_TESTS, "tests.experiments.test_development")),
        ("recorded-tests.xml", runtime.RECORDED_TESTS),
    ):
        suite = ET.Element("testsuite")
        for name, classname in expected.items():
            ET.SubElement(suite, "testcase", name=name, classname=classname)
        ET.ElementTree(suite).write(directory / filename)
    for name in ("restricted-comparison.log", "recorded-comparison.log"):
        (directory / name).write_text("synthetic mutation control; not operational evidence\n")
    report = {
        "schema_version": 1,
        "kind": "bounded_development_runtime",
        "os": "Linux",
        "input_digest": "synthetic",
        "status": "passed",
        "paid_calls": 0,
        "checks": dict.fromkeys(runtime.EXPECTED_CHECKS, True),
        "runtime_test_exit_code": 0,
        "recorded_test_exit_code": 0,
        "image_id": runtime.INSPECTED_IMAGE,
        "image_provenance": {"Id": runtime.INSPECTED_IMAGE, "Os": "linux", "Architecture": "amd64"},
        "run_directory": str(directory.relative_to(tmp_path)),
        "runtime_test_command": [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            f"--junitxml={directory / 'tests.xml'}",
            *[f"tests/experiments/test_development.py::{name}" for name in runtime.RUNTIME_TESTS],
        ],
        "recorded_test_command": [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            f"--junitxml={directory / 'recorded-tests.xml'}",
            "tests/promotion/runtime_recorded_evidence.py",
        ],
        "runtime_tests": list(runtime.RUNTIME_TESTS),
        "recorded_tests": list(runtime.RECORDED_TESTS),
        "artifact_digests": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir()
        },
    }
    if fault == "fake_checks":
        report["checks"] = {"fake": True}
    elif fault == "missing_check":
        report["checks"].pop(next(iter(report["checks"])))
    elif fault == "wrong_command":
        report["runtime_test_command"][0] = "fixture-python"
    elif fault == "wrong_image":
        report["image_id"] = "sha256:" + "0" * 64
    elif fault == "mutated_artifact":
        (directory / "restricted-comparison.log").write_text("changed")
    output = tmp_path / "evidence/EXPERIMENT/development-runtime.json"
    output.parent.mkdir(parents=True)
    output.write_text(json.dumps(report))
    assert bool(checks.operational_errors(tmp_path, "synthetic")) is (fault is not None)
