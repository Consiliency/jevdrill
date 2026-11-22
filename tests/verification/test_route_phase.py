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
        "python_minor": "3.14",
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


@pytest.mark.parametrize("phase", ["route", "contracts"])
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
        if step.get("uses", "").startswith("actions/upload-artifact@")
    )
    reduction = jobs["reduce"]["steps"]
    summary = next(
        step["with"]["name"]
        for step in reduction
        if step.get("uses", "").startswith("actions/upload-artifact@")
    )
    pattern = next(
        step["with"]["pattern"]
        for step in reduction
        if step.get("uses", "").startswith("actions/download-artifact@")
    )
    artifacts = {
        produced.replace("${{ matrix.os }}", row["os"]).replace(
            "${{ matrix.platform }}", row["platform"]
        ): {"os": row["platform"], "python_minor": "3.14"}
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


def test_windows_command_leaves_out_only_the_listed_inapplicable_tests(tmp_path):
    controls = {control for controls in runner.REQUIRED_CONTROLS.values() for control in controls}
    assert runner.WINDOWS_DESELECTED
    for node in runner.WINDOWS_DESELECTED:
        # Exactly one whole test function: not a file, a directory, a class or one parameter.
        # So leaving it out cannot remove a case of any required control.
        path, separator, function = node.partition("::")
        assert separator and function and "::" not in function and "[" not in function
        assert (ROOT / path).is_file()
        assert node not in controls
    for name in ("Linux", "Darwin", "Windows"):
        command = runner.commands_for("python", tmp_path, name)["tests"]
        deselected = [arg.removeprefix("--deselect=") for arg in command if "--deselect" in arg]
        assert deselected == (list(runner.WINDOWS_DESELECTED) if name == "Windows" else [])


@pytest.mark.parametrize(
    ("phase", "native", "variable"),
    [("route", "native", "NATIVE_RESULT"), ("contracts", "platform", "PLATFORM_RESULT")],
)
def test_reduction_runs_only_after_every_native_job_succeeded(phase, native, variable):
    workflow = yaml.safe_load((ROOT / ".github/workflows" / f"{phase}.yml").read_text())
    job = workflow["jobs"]["reduce"]
    assert job["needs"] == native
    steps = job["steps"]
    guard = next(index for index, step in enumerate(steps) if "env" in step)
    reduce = next(
        index for index, step in enumerate(steps) if "--reduce-only" in step.get("run", "")
    )
    # A receipt already in the checkout must not stand in for a native job that failed.
    assert steps[guard]["env"] == {variable: "${{ needs." + native + ".result }}"}
    assert steps[guard]["run"] == f'test "${variable}" = success'
    assert guard < reduce and "if" not in steps[guard] and "if" not in steps[reduce]


def test_verifier_outputs_are_ignored_by_git():
    ignored = (ROOT / ".gitignore").read_text().splitlines()
    assert "evidence/ROUTE/platforms/" in ignored
    assert "evidence/ROUTE/verification.json" in ignored


def test_every_coverage_path_is_in_the_verifiers_selection(tmp_path):
    coverage = json.loads((ROOT / "evidence/ROUTE/coverage.json").read_text())
    command = runner.commands_for("python", tmp_path, "Linux")["tests"]
    selected = [arg for arg in command if arg.startswith("tests/")]
    for requirement, paths in coverage["coverage"].items():
        for path in paths:
            assert any(path == arg or path.startswith(arg + "/") for arg in selected), (
                requirement,
                path,
            )


def test_collected_identities_keep_test_class_names(tmp_path, monkeypatch):
    monkeypatch.delenv("RUNNER_TEMP", raising=False)
    module = tmp_path / "tests/sample/test_module.py"
    module.parent.mkdir(parents=True)
    module.write_text("def test_function(): assert True\n")
    command = ["fixture-python", "-m", "pytest"]
    locations = []

    def commands_for(python, temporary, **kwargs):
        locations.append(temporary)
        return {"tests": command}

    def run(args, **kwargs):
        if args == command:
            (locations[0] / "tests.xml").write_text(
                '<testsuites><testsuite tests="3" skipped="0" failures="0" errors="0">'
                '<testcase classname="tests.sample.test_module" name="test_function"/>'
                '<testcase classname="tests.sample.test_module.TestGroup" name="test_function"/>'
                '<testcase classname="tests.sample.test_module.TestGroup.TestInner"'
                ' name="test_deep[case]"/>'
                "</testsuite></testsuites>"
            )
            return runner.subprocess.CompletedProcess(args, 0, b"passed", b"")
        return runner.subprocess.CompletedProcess(args, 0, stdout="baml-cli 0.20.1\n")

    monkeypatch.setattr(runner, "commands_for", commands_for)
    monkeypatch.setattr(runner.subprocess, "run", run)
    receipt = runner.collect(tmp_path)
    assert [row["node_id"] for row in receipt["assertions"]] == [
        "tests/sample/test_module.py::TestGroup::TestInner::test_deep[case]",
        "tests/sample/test_module.py::TestGroup::test_function",
        "tests/sample/test_module.py::test_function",
    ]
    assert receipt["tests"]["total"] == 3


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        ("duplicate_platform", "unexpected or duplicate platform"),
        ("unknown_platform", "unexpected or duplicate platform"),
        ("no_runner_identity", "missing runner identity"),
        ("no_architecture", "missing runner identity"),
        ("malformed_command", "malformed command"),
        ("excessive_cost", "invalid or excessive single-node proof cost"),
        ("cold_not_ready", "missing or failed cold deadline measurement"),
        ("cold_zero_duration", "missing or failed cold deadline measurement"),
        ("cold_huge_integer", "missing or failed cold deadline measurement"),
    ],
)
def test_reducer_names_each_malformed_receipt(evidence_root, mutation, error):
    rows = [manifest(name) for name, _ in sorted(runner.MATRIX)]
    assert runner.reduce_manifests(rows, "fixture", evidence_root) == []
    row = rows[0]
    cold = next(check for check in row["checks"] if check["name"] == "cold_cli")
    if mutation == "duplicate_platform":
        rows.append(copy.deepcopy(row))
    elif mutation == "unknown_platform":
        rows.append(copy.deepcopy(row) | {"python_minor": "3.13"})
    elif mutation == "no_runner_identity":
        row["runner_identity"] = ""
    elif mutation == "no_architecture":
        row["architecture"] = ""
    elif mutation == "malformed_command":
        row["checks"][0]["command"] = []
    elif mutation == "excessive_cost":
        row["duration_seconds"] = 601
    elif mutation == "cold_not_ready":
        cold["response_status"] = "unavailable"
    elif mutation == "cold_zero_duration":
        cold["duration_seconds"] = 0
    else:
        cold["duration_seconds"] = 10**400
    assert error in runner.reduce_manifests(rows, "fixture", evidence_root)


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        ("controls_changed", "missing entered negative controls"),
        ("coverage_path_absent", "invalid test coverage: EC-ROUTE-3"),
        ("coverage_path_outside", "invalid test coverage: EC-ROUTE-3"),
        ("coverage_file_absent", "missing or malformed requirement coverage"),
        ("required_tests_absent", "missing required tests: tests/costing"),
        ("deferral_dropped", "missing or malformed CONTRACT deferral coverage"),
        ("deferral_duplicated", "missing or malformed CONTRACT deferral coverage"),
        ("contract_record_malformed", "malformed CONTRACT deferral coverage"),
    ],
)
def test_coverage_record_errors_are_each_reported(evidence_root, mutation, error):
    path = evidence_root / "evidence/ROUTE/coverage.json"
    coverage = json.loads(path.read_text())
    deferral = {"id": "JD-900", "criteria": ["EC-ROUTE-1"]}
    coverage["contract_deferrals"] = [deferral]
    prior = evidence_root / "evidence/CONTRACT/coverage.json"
    prior.parent.mkdir(parents=True)
    requirement = {"id": "JD-900", "phase": "ROUTE", "criteria": [{"id": "EC-ROUTE-1"}]}
    other = {"id": "JD-901", "phase": "HOST", "criteria": [{"id": "EC-HOST-1"}]}
    prior.write_text(json.dumps({"requirements": [requirement, other]}))
    path.write_text(json.dumps(coverage))
    assert runner.coverage_errors(evidence_root) == []
    if mutation == "controls_changed":
        coverage["required_controls"] = copy.deepcopy(runner.REQUIRED_CONTROLS)
        coverage["required_controls"]["EC-ROUTE-4"].pop()
    elif mutation == "coverage_path_absent":
        coverage["coverage"]["EC-ROUTE-3"] = ["tests/absent.py"]
    elif mutation == "coverage_path_outside":
        coverage["coverage"]["EC-ROUTE-3"] = ["tests/../tests/test_fixture.py"]
    elif mutation == "deferral_dropped":
        coverage["contract_deferrals"] = []
    elif mutation == "deferral_duplicated":
        coverage["contract_deferrals"] = [deferral, deferral]
    elif mutation == "contract_record_malformed":
        prior.write_text(json.dumps({"requirements": [{"phase": "ROUTE"}]}))
    path.write_text(json.dumps(coverage))
    if mutation == "coverage_file_absent":
        path.unlink()
    elif mutation == "required_tests_absent":
        (evidence_root / "tests/costing").rmdir()
    assert error in runner.coverage_errors(evidence_root)


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
        [row], "fixture", evidence_root, required_platforms={("Linux", "3.14")}
    )


@pytest.mark.parametrize("row", [None, [], {"os": []}, {"os": "Linux", "python_minor": {}}])
def test_malformed_manifests_block_without_crashing(evidence_root, row):
    assert runner.reduce_manifests([row], "fixture", evidence_root)


@pytest.mark.parametrize("stable", [None, False])
def test_reducer_rejects_inputs_changed_during_collection(evidence_root, stable):
    row = manifest("Linux")
    row["source_stable"] = stable
    assert "inputs changed during collection" in runner.reduce_manifests(
        [row], "fixture", evidence_root, required_platforms={("Linux", "3.14")}
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


@pytest.mark.parametrize("runner_temp", [False, True], ids=["local-temp", "runner-temp"])
def test_collection_timeout_retains_progress_and_stack_trace(
    tmp_path, monkeypatch, capsys, runner_temp
):
    if runner_temp:
        monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    else:
        monkeypatch.delenv("RUNNER_TEMP", raising=False)
    command = ["fixture-python", "-m", "pytest"]
    locations = []

    def commands_for(python, temporary, **kwargs):
        locations.append(temporary)
        return {"tests": command}

    monkeypatch.setattr(runner, "commands_for", commands_for)

    def run(args, **kwargs):
        if args == command:
            raise runner.subprocess.TimeoutExpired(
                args, 600, output=b"last-test-name\n", stderr=b"stalled-test-stack\n"
            )
        return runner.subprocess.CompletedProcess(args, 0, stdout="baml-cli 0.20.1\n")

    monkeypatch.setattr(runner.subprocess, "run", run)
    result = runner.collect(tmp_path)
    expected_parent = tmp_path if runner_temp else Path(runner.tempfile.gettempdir())
    assert len(locations) == 1 and locations[0].parent == expected_parent
    check = result["checks"][0]
    assert check["exit_code"] == 125
    expected = b"TimeoutExpired\nlast-test-name\nstalled-test-stack\n"
    assert check["output_sha256"] == runner.hashlib.sha256(expected).hexdigest()
    output = capsys.readouterr().out
    assert "last-test-name" in output and "stalled-test-stack" in output
    assert result["tests"]["total"] == 0


def test_reduce_only_reports_corrupt_json(evidence_root, monkeypatch):
    directory = evidence_root / "evidence/ROUTE/platforms"
    directory.mkdir()
    (directory / "Linux-3.14.json").write_text("{")
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
        [row], "fixture", evidence_root, required_platforms={("Linux", "3.14")}
    )


@pytest.mark.parametrize(
    "control",
    [
        control
        for control in runner.REQUIRED_CONTROLS["EC-ROUTE-4"]
        if runner.CONTROL_COUNTS.get(control, 1) > 1
    ],
)
def test_reducer_rejects_one_missing_privacy_parameter(evidence_root, control):
    row = manifest("Linux")
    missing = next(
        index
        for index, item in enumerate(row["assertions"])
        if item["node_id"].startswith(control + "[")
    )
    row["assertions"].pop(missing)
    row["tests"]["total"] -= 1
    row["assertions_sha256"] = runner.command_digest(row["assertions"])
    assert "missing executed control: " + control in runner.reduce_manifests(
        [row], "fixture", evidence_root, required_platforms={("Linux", "3.14")}
    )


def test_input_binding_includes_nested_pinned_patch(evidence_root):
    path = evidence_root / "baml_src/ns_typesafe_patch/ns_internal/jev.baml"
    path.parent.mkdir(parents=True)
    path.write_text("synthetic first source")
    original = runner.input_digest(evidence_root)
    path.write_text("synthetic changed source")
    assert runner.input_digest(evidence_root) != original


@pytest.mark.parametrize("test_timeout", (False, True))
def test_windows_collection_overlaps_checks_without_resetting_deadline(
    tmp_path, monkeypatch, test_timeout
):
    import threading

    tests_entered = threading.Event()
    static_entered = threading.Event()
    clock = [100.0]
    timeouts = {}
    fixture = tmp_path / "tests/contracts/fixtures/route-application.json"
    fixture.parent.mkdir(parents=True)
    fixture.write_text('[{"payload": {}}]')
    commands = {
        "tests": ["tests-command"],
        "lint": ["static-command"],
        "cold_cli": ["cold-command"],
    }
    monkeypatch.setattr(runner, "commands_for", lambda *a, **k: commands)
    monkeypatch.setattr(runner.platform, "system", lambda: "Windows")
    monkeypatch.setattr(runner.time, "monotonic", lambda: clock[0])

    def run(args, **kwargs):
        if args == commands["cold_cli"]:
            assert not tests_entered.is_set() and not static_entered.is_set()
            timeouts["cold_cli"] = kwargs["timeout"]
            clock[0] = 102.0
            return runner.subprocess.CompletedProcess(args, 0, b'{"status":"ready"}', b"")
        if args == commands["tests"]:
            timeouts["tests"] = kwargs["timeout"]
            tests_entered.set()
            assert static_entered.wait(2), "static checks were starved behind pytest"
            if test_timeout:
                raise runner.subprocess.TimeoutExpired(args, kwargs["timeout"], output=b"progress")
        elif args == commands["lint"]:
            timeouts["lint"] = kwargs["timeout"]
            static_entered.set()
            assert tests_entered.wait(2), "independent checks did not overlap"
        else:
            return runner.subprocess.CompletedProcess(args, 0, stdout="baml-cli 0.20.1\n")
        return runner.subprocess.CompletedProcess(args, 0, b"passed", b"")

    monkeypatch.setattr(runner.subprocess, "run", run)
    receipt = runner.collect(tmp_path)
    assert timeouts == {"cold_cli": 600, "tests": 598, "lint": 598}
    assert [row["name"] for row in receipt["checks"]] == list(commands)
    checks = {row["name"]: row for row in receipt["checks"]}
    assert checks["lint"]["exit_code"] == 0
    assert checks["cold_cli"]["response_status"] == "ready"
    assert checks["tests"]["exit_code"] == (125 if test_timeout else 0)
