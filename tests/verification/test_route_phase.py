import copy
import importlib.util
import json
from fnmatch import fnmatchcase
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "route_verification", ROOT / "scripts/verify_route_phase.py"
)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def manifest(name):
    assertions = [
        {
            "node_id": control
            if runner.CONTROL_COUNTS.get(control, 1) == 1
            else control + f"[fixture-{number}]",
            "outcome": "passed",
        }
        for control in sorted(
            {control for controls in runner.REQUIRED_CONTROLS.values() for control in controls}
        )
        for number in range(runner.CONTROL_COUNTS.get(control, 1))
    ]
    return {
        "schema_version": 1,
        "execution_kind": "native",
        "os": name,
        "python_minor": "3.13",
        "input_digest": "fixture",
        "source_stable": True,
        "duration_seconds": 1,
        "runner_identity": "fixture",
        "architecture": "fixture",
        "bridge_version": "0.20.1",
        "compiler_version": "baml-cli 0.20.1",
        "tests": {"total": len(assertions), "skipped": 0, "failures": 0, "errors": 0},
        "assertions": assertions,
        "assertions_sha256": runner.command_digest(assertions),
        "checks": [
            {
                "name": check,
                "command": command,
                "exit_code": 0,
                "command_sha256": runner.command_digest(command),
                "output_sha256": "0" * 64,
                "duration_seconds": 0.1,
                "response_status": "ready" if check == "cold_cli" else None,
            }
            for check, command in runner.commands_for(
                "fixture-python", Path("fixture-tmp"), name
            ).items()
        ],
    }


@pytest.fixture
def evidence_root(tmp_path):
    route = tmp_path / "evidence/ROUTE"
    route.mkdir(parents=True)
    (route / "spec-delta.json").write_text(
        json.dumps(
            {
                "schema": "spec_delta_closeout.v1",
                "phase": "ROUTE",
                "decision": "canonical_spec_update",
                "redaction_posture": "metadata_only",
                "target_surfaces": [
                    "docs/contracts.md",
                    "docs/route-interfaces.md",
                    "docs/vocabulary.yaml",
                    "docs/vocabulary.md",
                ],
                "evidence_paths": [
                    "evidence/ROUTE/spec-delta.json",
                    "evidence/ROUTE/verification.json",
                    "evidence/ROUTE/coverage.json",
                ],
                "downstream_handling": "replan_HOST",
                "canonical_adoption": False,
                "publication_performed": False,
                "if_gates_produced": [],
                "closeout_status": "verification_pending",
            }
        )
    )
    test_file = tmp_path / "tests/test_fixture.py"
    test_file.parent.mkdir()
    test_file.write_text("def test_fixture(): assert True\n")
    (route / "coverage.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "phase": "ROUTE",
                "status": "complete",
                "coverage": {key: ["tests/test_fixture.py"] for key in runner.REQUIREMENTS},
                "required_controls": runner.REQUIRED_CONTROLS,
            }
        )
    )
    for relative in runner.REQUIRED_TEST_PATHS:
        path = tmp_path / relative
        if path.suffix:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("def test_fixture(): assert True\n")
        else:
            path.mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.mark.parametrize("phase", ["route", "contracts", "host", "learn"])
def test_native_download_excludes_prior_reduction_reports(phase):
    workflow = yaml.safe_load((ROOT / ".github/workflows" / f"{phase}.yml").read_text())
    jobs = workflow["jobs"]
    native = jobs.get("native", jobs.get("platform"))
    matrix = native["strategy"]["matrix"]
    rows = matrix.get("include") or [
        {"os": os_name, "platform": platform}
        for os_name, platform in zip(matrix["os"], ["Linux", "Darwin", "Windows"], strict=True)
    ]
    produced = next(
        step["with"]["name"]
        for step in native["steps"]
        if step.get("uses") == "actions/upload-artifact@v4"
    )
    reduction = jobs["reduce"]["steps"]
    summary = next(
        step["with"]["name"]
        for step in reduction
        if step.get("uses") == "actions/upload-artifact@v4"
    )
    pattern = next(
        step["with"]["pattern"]
        for step in reduction
        if step.get("uses") == "actions/download-artifact@v4"
    )
    artifacts = {
        produced.replace("${{ matrix.os }}", row["os"]).replace(
            "${{ matrix.platform }}", row["platform"]
        ): {"os": row["platform"], "python_minor": "3.13"}
        for row in rows
    }
    artifacts[summary] = {"phase": phase, "status": "blocked"}
    selected = [value for name, value in artifacts.items() if fnmatchcase(name, pattern)]
    assert len(selected) == 3
    assert {value.get("os") for value in selected} == {"Linux", "Darwin", "Windows"}


def test_phase_test_command_covers_controls_without_downstream_companion(tmp_path):
    command = runner.commands_for("python", tmp_path)["tests"]
    selected = [arg for arg in command if arg.startswith("tests/")]
    assert selected
    assert "tests/conformance" not in selected
    assert "tests/application" not in selected
    for controls in runner.REQUIRED_CONTROLS.values():
        for control in controls:
            file = control.split("::")[0]
            assert any(file == path or file.startswith(path + "/") for path in selected)


@pytest.mark.parametrize("phase", ["host", "learn", "experiment"])
def test_downstream_commands_cover_phase_controls_and_bind_extra_paths(tmp_path, phase):
    spec = importlib.util.spec_from_file_location(
        "downstream_" + phase, ROOT / "scripts" / f"verify_{phase}_phase.py"
    )
    downstream = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(downstream)
    command = runner.commands_for("python", tmp_path, extra_test_paths=downstream.TEST_PATHS)[
        "tests"
    ]
    selected = [arg for arg in command if arg.startswith("tests/")]
    for controls in downstream.CONTROLS.values():
        for control in controls:
            file = control.split("::")[0]
            assert any(file == path or file.startswith(path + "/") for path in selected)
    assert len(selected) == len(set(selected))
    assert command != runner.commands_for("python", tmp_path)["tests"]


def test_reducer_requires_each_native_platform(evidence_root):
    assert runner.reduce_manifests([manifest("Linux")], "fixture", evidence_root)
    assert not runner.reduce_manifests(
        [manifest(name) for name, _ in runner.MATRIX], "fixture", evidence_root
    )


def test_reducer_rejects_failed_or_proxy_evidence(evidence_root):
    rows = [manifest(name) for name, _ in runner.MATRIX]
    rows[0]["execution_kind"] = "proxy"
    rows[1]["checks"][0]["exit_code"] = 1
    errors = runner.reduce_manifests(rows, "fixture", evidence_root)
    assert "unsupported evidence" in errors
    assert "failed check" in errors


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate",
        "malformed",
        "bad_name",
        "failed_assertion",
        "error_assertion",
        "no_assertions",
        "wrong_command",
        "command_digest",
        "output_digest",
        "stale_input",
        "tool_version",
        "skipped_assertion",
        "cold_deadline",
    ],
)
def test_reducer_rejects_forged_or_malformed_success(evidence_root, mutation):
    row = manifest("Linux")
    if mutation == "duplicate":
        row["checks"].append(copy.deepcopy(row["checks"][0]))
    elif mutation == "malformed":
        row["checks"][0] = None
    elif mutation == "bad_name":
        row["checks"][0]["name"] = []
    elif mutation in {"failed_assertion", "error_assertion", "no_assertions", "skipped_assertion"}:
        key = {
            "failed_assertion": "failures",
            "error_assertion": "errors",
            "no_assertions": "total",
            "skipped_assertion": "skipped",
        }[mutation]
        row["tests"][key] = 0 if key == "total" else 1
    elif mutation == "wrong_command":
        row["checks"][0]["command"] = ["python", "--version"]
        row["checks"][0]["command_sha256"] = runner.command_digest(row["checks"][0]["command"])
    elif mutation == "command_digest":
        row["checks"][0]["command_sha256"] = "f" * 64
    elif mutation == "output_digest":
        row["checks"][0]["output_sha256"] = "missing"
    elif mutation == "stale_input":
        row["input_digest"] = "old"
    elif mutation == "cold_deadline":
        next(check for check in row["checks"] if check["name"] == "cold_cli")[
            "duration_seconds"
        ] = 5.1
    else:
        row["compiler_version"] = "baml-cli 0.226.2"
    assert runner.reduce_manifests(
        [row], "fixture", evidence_root, required_platforms={("Linux", "3.13")}
    )


@pytest.mark.parametrize("row", [None, [], {"os": []}, {"os": "Linux", "python_minor": {}}])
def test_malformed_manifests_block_without_crashing(evidence_root, row):
    assert runner.reduce_manifests([row], "fixture", evidence_root)


@pytest.mark.parametrize("stable", [None, False])
def test_reducer_rejects_inputs_changed_during_collection(evidence_root, stable):
    row = manifest("Linux")
    row["source_stable"] = stable
    assert "inputs changed during collection" in runner.reduce_manifests(
        [row], "fixture", evidence_root, required_platforms={("Linux", "3.13")}
    )


@pytest.mark.parametrize("artifact", ["spec-delta.json", "coverage.json"])
def test_reducer_requires_full_metadata_records(evidence_root, artifact):
    (evidence_root / "evidence/ROUTE" / artifact).write_text("{}")
    assert runner.reduce_manifests(
        [manifest(name) for name, _ in runner.MATRIX], "fixture", evidence_root
    )


def test_partial_coverage_remains_blocked_with_all_platforms(evidence_root):
    path = evidence_root / "evidence/ROUTE/coverage.json"
    value = json.loads(path.read_text())
    value["status"] = "partial"
    path.write_text(json.dumps(value))
    errors = runner.reduce_manifests(
        [manifest(name) for name, _ in runner.MATRIX], "fixture", evidence_root
    )
    assert any(error.startswith("incomplete requirement coverage") for error in errors)


def test_local_only_does_not_suppress_missing_assertions(evidence_root, monkeypatch):
    row = manifest("Linux")
    row["tests"]["total"] = 0
    monkeypatch.setattr(runner, "ROOT", evidence_root)
    monkeypatch.setattr(runner, "collect", lambda _: row)
    monkeypatch.setattr(runner, "input_digest", lambda _: "fixture")
    monkeypatch.setattr(runner.platform, "system", lambda: "Linux")
    monkeypatch.setattr("sys.argv", ["verify_route_phase.py", "--local-only"])
    assert runner.main() == 1


def test_local_only_ignores_only_absent_other_platforms(evidence_root, monkeypatch):
    monkeypatch.setattr(runner, "ROOT", evidence_root)
    monkeypatch.setattr(runner, "collect", lambda _: manifest("Linux"))
    monkeypatch.setattr(runner, "input_digest", lambda _: "fixture")
    monkeypatch.setattr(runner.platform, "system", lambda: "Linux")
    monkeypatch.setattr("sys.argv", ["verify_route_phase.py", "--local-only"])
    assert runner.main() == 0


def test_reduce_only_reports_corrupt_json(evidence_root, monkeypatch):
    directory = evidence_root / "evidence/ROUTE/platforms"
    directory.mkdir()
    (directory / "Linux-3.13.json").write_text("{")
    monkeypatch.setattr(runner, "ROOT", evidence_root)
    monkeypatch.setattr("sys.argv", ["verify_route_phase.py", "--reduce-only"])
    assert runner.main() == 1
    report = json.loads((evidence_root / "evidence/ROUTE/verification.json").read_text())
    assert "malformed manifest" in report["errors"]


def test_reducer_rejects_four_criterion_coverage(evidence_root):
    path = evidence_root / "evidence/ROUTE/coverage.json"
    coverage = json.loads(path.read_text())
    coverage["coverage"] = {
        key: value
        for key, value in coverage["coverage"].items()
        if key not in {"EC-ROUTE-5", "EC-ROUTE-6", "EC-ROUTE-7"}
    }
    path.write_text(json.dumps(coverage))
    assert "missing requirement coverage" in runner.reduce_manifests(
        [manifest(name) for name, _ in runner.MATRIX], "fixture", evidence_root
    )


@pytest.mark.parametrize("mutation", ["missing", "skipped", "digest", "parameter", "duplicates"])
def test_reducer_requires_executed_controls(evidence_root, mutation):
    row = manifest("Linux")
    if mutation == "missing":
        row.pop("assertions")
    elif mutation == "skipped":
        row["assertions"][0]["outcome"] = "skipped"
    elif mutation == "digest":
        row["assertions_sha256"] = "f" * 64
    elif mutation == "parameter":
        row["assertions"].pop()
        row["tests"]["total"] -= 1
        row["assertions_sha256"] = runner.command_digest(row["assertions"])
    else:
        row["assertions"][0] = copy.deepcopy(row["assertions"][1])
        row["assertions_sha256"] = runner.command_digest(row["assertions"])
    assert runner.reduce_manifests(
        [row], "fixture", evidence_root, required_platforms={("Linux", "3.13")}
    )


def test_input_binding_includes_nested_pinned_patch(evidence_root):
    path = evidence_root / "baml_src/ns_typesafe_patch/ns_internal/jev.baml"
    path.parent.mkdir(parents=True)
    path.write_text("synthetic first source")
    original = runner.input_digest(evidence_root)
    path.write_text("synthetic changed source")
    assert runner.input_digest(evidence_root) != original
