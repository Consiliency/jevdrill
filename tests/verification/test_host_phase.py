import copy
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
spec = importlib.util.spec_from_file_location(
    "host_verification", ROOT / "scripts/verify_host_phase.py"
)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

ROUTE_REDUCE = runner.route.reduce_manifests
HANDOFF = json.loads((ROOT / "evidence/HOST/adapter-handoff.json").read_text())
RUN = {"run_id": "1001", "run_attempt": "1", "repository": "Consiliency/jevdrill"}
JEVDRILL_COMMIT = "c" * 40
PLATFORMS = sorted(runner.MATRIX)


def companion_tree(root):
    """A companion checkout holding only its contract copies, as the pin's are made."""
    runtime = root / "phase-loop-runtime"
    directory = runtime / runner.CONTRACT_DIRECTORY
    directory.mkdir(parents=True)
    for name in runner.CONTRACT_SCHEMAS:
        shutil.copyfile(ROOT / "schemas" / name, directory / name)
    for name in runner.CONTRACT_FIXTURES:
        own = (ROOT / "tests/contracts/fixtures" / name).read_bytes()
        directory.joinpath(name).write_bytes(
            own.replace(runner.TOKEN_COUNTER_REVISION, runner.TOKEN_COUNTER_PLACEHOLDER)
        )
    write_digests(directory)
    return runtime


def write_digests(directory):
    """digests.json as the companion commits it: digests of the LF blobs."""
    digests = {
        name: runner.hashlib.sha256(
            (directory / name).read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
        for name in runner.CONTRACT_SCHEMAS
    }
    (directory / "digests.json").write_bytes((json.dumps(digests, indent=2) + "\n").encode())


def rows_for(counts, key="node_id"):
    """Passing rows that meet each control's exact count; a named parameter is one of them."""
    nodes = {}
    for node, count in counts.items():
        if "[" in node:
            continue
        nodes[node] = [node] if count == 1 else [f"{node}[case{index}]" for index in range(count)]
    for node in counts:
        if "[" in node:
            parent = node.split("[")[0]
            if parent in nodes:
                nodes[parent][0] = node
            else:
                nodes[node] = [node]
    return [{key: value, "outcome": "passed"} for values in nodes.values() for value in values]


def filled(rows, total, prefix, key="node_id"):
    filler = [
        {key: f"{prefix}::test_unnamed_{index}", "outcome": "passed"}
        for index in range(total - len(rows))
    ]
    return sorted(rows + filler, key=lambda row: row[key])


def discovery_rows():
    return filled(
        rows_for(runner.DISCOVERY_CONTROL_COUNTS),
        runner.DISCOVERY_TOTAL,
        "tests/test_jevdrill_discovery.py",
    )


def witness():
    runs = [
        {
            "task_id": f"task-{index}",
            "model": f"model-{index}",
            "effort": f"effort-{index}",
            "discovery_ref": {"discovery_id": "discovery", "trace_digest": "a" * 64},
            "execution_run": {
                "task_id": f"task-{index}",
                "selected_plan_id": f"plan-{index}",
                "applied_plan_id": f"plan-{index}",
                "execution_run_id": f"run-{index}",
            },
        }
        for index in range(2)
    ]
    records = []
    for objective in ("alpha", "beta"):
        flow_runs = copy.deepcopy(runs)
        for run in flow_runs:
            run["decision_id"] = f"decision-{objective}-{run['task_id']}"
        records.append(
            {
                "flow": "discovery",
                "objective": objective,
                "entered": ["main", "open_application", "discover", "next_question", "route"],
                "construction_events": ["planning.executor", "task.SL-0.route-v2"],
                "runs": flow_runs,
            }
        )
    records.append(
        {
            "flow": "judged",
            "stored_function_revision": "JudgeCandidate-v2",
            "stored_judgments": 1,
            "loopback_judgment_requests": 1,
            "decision_status": "ready",
            "routing_decision_id": "judged-decision",
        }
    )
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
    for family in ("implementation", "review", "documentation"):
        records.append(
            {"task_family": family, "damaged": True, "objective_checks": {"independent": False}}
        )
        records.append({"task_family": family, "objective_checks": {"independent": True}})
    probes = rows_for({runner._dotted(node): n for node, n in runner.PROBE_COUNTS.items()}, "id")
    discovered = [
        {"id": runner._dotted(row["node_id"]), "outcome": "passed"} for row in discovery_rows()
    ]
    discovery_command = list(runner.DISCOVERY_COMMAND)
    return {
        "records": records,
        "assertions": probes + discovered,
        "claim_scope": "synthetic_conformance_only",
        "holdouts_opened": False,
        "promotion_eligible": False,
        "performance_claims": "insufficient_evidence",
        "companion_discovery": {
            "origin": "installed_companion_conformance_subprocess",
            "command": discovery_command,
            "command_sha256": runner.digest_value(discovery_command),
            "output_sha256": "a" * 64,
            "input_digest": "companion",
            "source_stable": True,
            "exit_code": 0,
            "assertions": discovery_rows(),
            "assertions_sha256": runner.digest_value(discovery_rows()),
        },
    }


def receipt(os_name, copies):
    command = runner.expected_companion_command(os_name)
    assertions = filled(
        rows_for(
            {
                node: counts[os_name]
                for node, counts in runner.COMPANION_CONTROL_COUNTS.items()
                if os_name in counts
            }
        ),
        runner.COMPANION_TOTALS[os_name],
        "tests/test_jevdrill_queue.py",
    )
    evidence = witness()
    return {
        "schema_version": runner.SCHEMA_VERSION,
        "phase": "HOST",
        "execution_kind": "native",
        "os": os_name,
        "architecture": "X64",
        "python_minor": "3.14",
        "python_version": "3.14.0",
        "runner_identity": RUN["run_id"],
        "workflow_run": dict(RUN),
        "jevdrill": {"repository": RUN["repository"], "commit": JEVDRILL_COMMIT, "clean": True},
        "input_digest": "fixture",
        "source_stable": True,
        "route_regressions": {"assertions": rows_for(runner.CONTROL_COUNTS)},
        "companion": {
            "repository": HANDOFF["repository"],
            "commit": HANDOFF["commit"],
            "clean": True,
            "python": {"version": "3.12.9", "minor": "3.12"},
            "installed_provenance": {
                "modules": HANDOFF["modules"],
                "version": HANDOFF["package_version"],
                "os": os_name,
                "python_version": "3.12.9",
                "source_root_matches": True,
            },
            "contract_copies": copy.deepcopy(copies),
            "command": command,
            "command_sha256": runner.digest_value(command),
            "input_digest": "companion",
            "source_stable": True,
            "exit_code": 0,
            "deadline_expired": False,
            "output_sha256": "a" * 64,
            "assertions": assertions,
            "assertions_sha256": runner.digest_value(assertions),
        },
        "witnesses": evidence,
        "witness_sha256": runner.digest_value(evidence),
        "host_static": {"command": list(runner.HOST_STATIC_COMMAND), "exit_code": 0},
        "duration_seconds": 250.0,
        "proof_cost_target_exceeded": False,
    }


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    """Three valid receipts of one run, and the reducer's own state for that run."""
    monkeypatch.setattr(runner.route, "reduce_manifests", lambda *_a, **_k: [])
    monkeypatch.setattr(runner.route, "input_digest", lambda _root: "route")
    copies = runner.contract_copies(ROOT, companion_tree(tmp_path / "companion"))
    reference = {
        "input_digest": "fixture",
        "jevdrill": {"repository": RUN["repository"], "commit": JEVDRILL_COMMIT, "clean": True},
        "companion": {
            "repository": HANDOFF["repository"],
            "commit": HANDOFF["commit"],
            "clean": True,
            "digest": "companion",
            "contract_copies": copies,
        },
        "run": dict(RUN),
    }
    return [receipt(name, copies) for name, _ in PLATFORMS], reference


def refresh(manifest):
    manifest["witness_sha256"] = runner.digest_value(manifest["witnesses"])
    companion = manifest["companion"]
    companion["assertions_sha256"] = runner.digest_value(companion["assertions"])
    discovery = manifest["witnesses"].get("companion_discovery")
    if isinstance(discovery, dict):
        discovery["assertions_sha256"] = runner.digest_value(discovery["assertions"])
        manifest["witness_sha256"] = runner.digest_value(manifest["witnesses"])


def flow(manifest):
    return next(r for r in manifest["witnesses"]["records"] if r.get("flow") == "discovery")


def mutate(manifests, fault, tmp_path):
    row = next(m for m in manifests if m["os"] == "Linux")
    companion = row["companion"]
    records = row["witnesses"]["records"]
    if fault == "foreign_companion_commit":
        companion["commit"] = "d" * 40
    elif fault == "foreign_companion_repository":
        companion["repository"] = "Someone/agent-harness"
    elif fault == "unclean_companion":
        companion["clean"] = False
    elif fault == "unclean_jevdrill":
        row["jevdrill"]["clean"] = False
    elif fault == "other_jevdrill_commit":
        row["jevdrill"]["commit"] = "e" * 40
    elif fault == "other_run":
        row["workflow_run"]["run_id"] = row["runner_identity"] = "999"
    elif fault == "rerun_attempt":
        row["workflow_run"]["run_attempt"] = "2"
    elif fault == "local_receipt":
        row["runner_identity"] = "local"
        row["workflow_run"] = {"run_id": None, "run_attempt": None, "repository": None}
    elif fault == "duplicate_platform":
        manifests.append(copy.deepcopy(row))
    elif fault == "missing_platform":
        manifests.remove(next(m for m in manifests if m["os"] == "Windows"))
    elif fault == "skipped_companion_test":
        companion["assertions"][0]["outcome"] = "skipped"
    elif fault == "failed_companion_test":
        companion["assertions"][0]["outcome"] = "failed"
    elif fault == "extra_companion_case":
        companion["assertions"].append(
            {"node_id": "tests/test_jevdrill_queue.py::test_added", "outcome": "passed"}
        )
    elif fault == "missing_control_case":
        companion["assertions"] = [
            r for r in companion["assertions"] if not r["node_id"].endswith("reports[case2]")
        ]
    elif fault == "inexact_host_control":
        row["route_regressions"]["assertions"].append(
            {
                "node_id": "tests/contracts/test_host_contracts.py::test_host_shared_contract[x]",
                "outcome": "passed",
            }
        )
    elif fault == "skipped_discovery_test":
        row["witnesses"]["companion_discovery"]["assertions"][0]["outcome"] = "skipped"
    elif fault == "inexact_probe_count":
        row["witnesses"]["assertions"].pop(0)
    elif fault == "deadline_expired":
        companion.update(deadline_expired=True, exit_code=125)
    elif fault in ("dropped_deselection", "added_selection"):
        command = runner.expected_companion_command("Linux")
        if fault == "dropped_deselection":
            index = command.index("not dotfiles_integration")
            del command[index - 1 : index + 1]
        else:
            command[4:4] = ["-k", "queue"]
        companion.update(command=command, command_sha256=runner.digest_value(command))
    elif fault == "wrong_command_digest":
        companion["command_sha256"] = runner.digest_value(["<python>", "--help"])
    elif fault == "discovery_without_deselection":
        discovery = row["witnesses"]["companion_discovery"]
        index = discovery["command"].index("not dotfiles_integration")
        del discovery["command"][index - 1 : index + 1]
        discovery["command_sha256"] = runner.digest_value(discovery["command"])
    elif fault == "contract_copy_differs":
        runtime = companion_tree(tmp_path / "changed")
        schema = runtime / runner.CONTRACT_DIRECTORY / "RouteInputs.json"
        schema.write_text(schema.read_text().replace("{", "{ ", 1))
        write_digests(schema.parent)
        companion["contract_copies"] = runner.contract_copies(ROOT, runtime)
    elif fault == "no_judged_task":
        records[:] = [r for r in records if r.get("flow") != "judged"]
    elif fault == "v1_judged_task":
        next(r for r in records if r.get("flow") == "judged")["stored_function_revision"] = (
            "JudgeCandidate-v1"
        )
    elif fault == "reused_decision":
        runs = flow(row)["runs"]
        runs[1]["decision_id"] = runs[0]["decision_id"]
    elif fault == "one_task":
        flow(row)["runs"] = flow(row)["runs"][:1]
    elif fault == "same_configuration":
        runs = flow(row)["runs"]
        runs[1]["model"] = runs[0]["model"]
    elif fault == "missing_decomposition":
        flow(row)["construction_events"] = ["task.SL-0.route-v2"]
    elif fault == "holdout":
        row["witnesses"]["holdouts_opened"] = True
    elif fault == "quality_claim":
        row["witnesses"]["performance_claims"] = "quality_gain"
    elif fault == "fault_only_control":
        next(r for r in records if r.get("flow") == "discovery-control").pop("discovery_id")
    elif fault == "missing_positive_checks":
        records[:] = [r for r in records if r.get("damaged") or r.get("flow")]
    elif fault == "over_600_seconds":
        row.update(duration_seconds=600.5, proof_cost_target_exceeded=True)
    elif fault == "misreported_flag":
        row.update(duration_seconds=400.0, proof_cost_target_exceeded=False)
    elif fault == "stale_input":
        row["input_digest"] = "stale"
    elif fault == "source_changed":
        row["source_stable"] = False
    elif fault == "installed_provenance":
        companion["installed_provenance"]["source_root_matches"] = False
    elif fault == "companion_python":
        companion["python"] = {"version": "3.14.0", "minor": "3.14"}
    elif fault == "old_schema":
        row["schema_version"] = 2
    elif fault == "collection_error":
        manifests[manifests.index(row)] = {
            "schema_version": runner.SCHEMA_VERSION,
            "phase": "HOST",
            "os": "Linux",
            "python_minor": "3.14",
            "collection_error": "the companion did not import",
        }
        return
    else:
        raise AssertionError(fault)
    refresh(row)


FAULTS = [
    # Property 1: the handoff's commit and clean checkouts.
    ("foreign_companion_commit", "companion receipt is not for the handoff's commit"),
    ("foreign_companion_repository", "companion receipt is not for the handoff's commit"),
    ("unclean_companion", "companion checkout was not clean"),
    ("unclean_jevdrill", "jevdrill checkout is not the reduced commit, or was not clean"),
    ("other_jevdrill_commit", "jevdrill checkout is not the reduced commit, or was not clean"),
    # Property 2: three receipts of this workflow run.
    ("other_run", "receipt is not from this workflow run"),
    ("rerun_attempt", "receipt is not from this workflow run"),
    ("local_receipt", "receipt is not from this workflow run"),
    ("duplicate_platform", "unexpected or duplicate platform"),
    ("missing_platform", "missing Windows/Python 3.14"),
    # Property 3: no failed or skipped selected test; exact counts.
    ("skipped_companion_test", "failed or skipped companion test: "),
    ("failed_companion_test", "failed or skipped companion test: "),
    ("extra_companion_case", "companion test count not exact"),
    (
        "missing_control_case",
        (
            "companion control count not exact: "
            "tests/test_jevdrill_queue.py::test_process_crash_windows_recover_durable_reports"
        ),
    ),
    (
        "inexact_host_control",
        (
            "HOST control count not exact: "
            "tests/contracts/test_host_contracts.py::test_host_shared_contract"
        ),
    ),
    ("skipped_discovery_test", "failed, skipped or inexact companion discovery tests"),
    ("inexact_probe_count", "probe count not exact: "),
    ("deadline_expired", "companion tests exceeded the collection deadline"),
    # Property 4: the deselection and the selection are bound in the command digest.
    ("dropped_deselection", "companion command is not the expected command"),
    ("added_selection", "companion command is not the expected command"),
    ("wrong_command_digest", "companion command digest mismatch"),
    ("discovery_without_deselection", "missing or mismatched integrated companion discovery"),
    # Property 5: the contract copies are jevdrill's.
    ("contract_copy_differs", "companion contract copies differ from jevdrill's"),
    # Property 6 and the witness: a v2 judged task and a distinct decision per task.
    ("no_judged_task", "missing v2 judged task"),
    ("v1_judged_task", "missing v2 judged task"),
    ("reused_decision", "missing or reused routing decision"),
    ("one_task", "missing independent two-task configuration"),
    ("same_configuration", "missing independent two-task configuration"),
    ("missing_decomposition", "missing entered harness decomposition"),
    ("holdout", "holdout or promotion authority violation"),
    ("quality_claim", "ineligible performance claim"),
    ("fault_only_control", "missing linked control rejection evidence"),
    ("missing_positive_checks", "missing independent positive artifact checks"),
    # Property 9: the 600-second bound and the five-minute flag.
    ("over_600_seconds", "collection over 600 seconds, or no valid duration"),
    ("misreported_flag", "misreported five-minute proof-cost flag"),
    # The receipt's own source, provenance and interpreter.
    ("stale_input", "stale HOST input digest"),
    ("source_changed", "HOST inputs changed during collection"),
    ("installed_provenance", "mismatched installed companion provenance"),
    ("companion_python", "companion Python is not the pinned version"),
    ("old_schema", "unsupported HOST receipt"),
    ("collection_error", "Linux: collection failed: the companion did not import"),
]


@pytest.mark.parametrize(("fault", "error"), FAULTS, ids=[fault for fault, _ in FAULTS])
def test_reducer_rejects_invalid_receipts(evidence, tmp_path, fault, error):
    manifests, reference = evidence
    assert runner.receipt_errors(manifests, reference) == []
    mutate(manifests, fault, tmp_path)
    errors = runner.receipt_errors(manifests, reference)
    assert any(error in item for item in errors), errors


def test_reducer_accepts_valid_receipts(evidence, monkeypatch):
    manifests, reference = evidence
    assert runner.receipt_errors(manifests, reference) == []
    # Property 7: every clause not covered is reported as such, and no gate is produced.
    gaps = runner.not_covered()
    assert gaps
    assert runner.reduce_manifests(manifests, reference) == ["not covered: " + g for g in gaps]
    report = runner.verdict(manifests, reference)
    assert report["controls_passed"] is True and report["errors"] == []
    assert report["status"] == "blocked" and report["produced_if_gates"] == []
    assert report["not_covered"] == gaps
    assert report["platforms"] == ["Darwin", "Linux", "Windows"]
    # The same receipts produce the gate only once nothing stands uncovered.
    monkeypatch.setattr(runner, "not_covered", list)
    report = runner.verdict(manifests, reference)
    assert report["status"] == "passed" and report["produced_if_gates"] == ["IF-0-HOST-1"]
    # Over five minutes is flagged, not rejected.
    manifests[0].update(duration_seconds=301.0, proof_cost_target_exceeded=True)
    report = runner.verdict(manifests, reference)
    assert report["proof_cost_over_five_minutes"] == [manifests[0]["os"]]
    assert report["produced_if_gates"] == ["IF-0-HOST-1"]


def test_reducer_rejects_a_reduction_outside_the_run_or_on_a_foreign_checkout(evidence):
    manifests, reference = evidence
    outside = copy.deepcopy(reference)
    outside["run"]["run_id"] = None
    assert "reduction outside a workflow run" in runner.receipt_errors(manifests, outside)
    foreign = copy.deepcopy(reference)
    foreign["companion"]["commit"] = "f" * 40
    assert "reducer's companion checkout is not the handoff's clean commit" in (
        runner.receipt_errors(manifests, foreign)
    )


def test_missing_companion_configuration_is_failure(tmp_path, monkeypatch):
    assert "missing production witnesses" in runner.witness_errors(None)

    def never(*_args, **_kwargs):
        raise AssertionError("nothing may run without the companion")

    monkeypatch.setattr(runner.route, "collect", never)
    monkeypatch.setattr(runner.subprocess, "run", never)
    monkeypatch.delenv("JEVDRILL_AGENT_HARNESS_PYTHON", raising=False)
    with pytest.raises(runner.CollectionError, match="JEVDRILL_AGENT_HARNESS_PYTHON"):
        runner.collect(ROOT, tmp_path)
    interpreter = tmp_path / "python"
    interpreter.write_text("")
    monkeypatch.setenv("JEVDRILL_AGENT_HARNESS_PYTHON", str(interpreter))
    with pytest.raises(runner.CollectionError, match="companion checkout is missing"):
        runner.collect(ROOT, tmp_path / "absent")
    monkeypatch.delenv("JEVDRILL_AGENT_HARNESS_ROOT", raising=False)
    with pytest.raises(SystemExit):
        runner.main(["--local-only"])


@pytest.mark.parametrize(
    "value",
    [None, [], "receipt", 7, {"os": "Linux"}, {"os": 1, "python_minor": "3.14"}],
)
def test_a_malformed_receipt_gives_a_verdict_not_a_traceback(evidence, value):
    manifests, reference = evidence
    errors = runner.receipt_errors([*manifests[1:], value], reference)
    assert errors


def test_every_malformed_field_gives_a_verdict_not_a_traceback(evidence, monkeypatch):
    manifests, reference = evidence
    monkeypatch.setattr(runner.route, "reduce_manifests", ROUTE_REDUCE)
    original = manifests[0]
    paths = [(key,) for key in original] + [("companion", key) for key in original["companion"]]
    paths += [("witnesses", key) for key in original["witnesses"]]
    paths += [("witnesses", "companion_discovery", key) for key in witness()["companion_discovery"]]
    for path in paths:
        for value in (None, 7, "text", [1, "x", None], {"x": 1}):
            row = copy.deepcopy(original)
            target = row
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            assert runner.receipt_errors([row, *manifests[1:]], reference), path


def test_unreadable_receipt_files_are_reported(tmp_path, evidence):
    _, reference = evidence
    (tmp_path / "Linux-3.14.json").write_text("{")
    (tmp_path / "Darwin-3.14.json").write_text("[]")
    receipts = runner.read_receipts(tmp_path)
    assert receipts[1] is None
    report = runner.verdict(receipts, reference)
    assert "malformed HOST receipt" in report["errors"]
    assert report["produced_if_gates"] == []


def test_command_digest_ignores_paths_and_binds_every_flag():
    posix = runner.companion_command("/opt/runner/python", Path("/tmp/x"), "Linux")
    windows = runner.companion_command(
        "D:\\a\\companion\\python.exe", "D:\\a\\_temp\\jevdrill-host-1", "Linux"
    )
    normalized = runner.normalized_command(posix, "companion")
    assert normalized == runner.normalized_command(windows, "companion")
    assert runner.digest_value(normalized) == runner.digest_value(
        runner.expected_companion_command("Linux")
    )
    assert "-m" in normalized and "not dotfiles_integration" in normalized
    for os_name in ("Darwin", "Windows"):
        command = runner.expected_companion_command(os_name)
        assert not any(
            name in part for part in command for name in runner.LINUX_ONLY_COMPANION_FILES
        )
        assert runner.digest_value(command) != runner.digest_value(normalized)
    for extra in (["-k", "queue"], ["-p", "no:cacheprovider"], ["--deselect=tests/x.py::y"]):
        changed = normalized[:4] + extra + normalized[4:]
        assert runner.digest_value(runner.normalized_command(changed, "companion")) != (
            runner.digest_value(normalized)
        )


def test_contract_copies_are_compared_with_jevdrills_files(tmp_path):
    runtime = companion_tree(tmp_path / "pin")
    directory = runtime / runner.CONTRACT_DIRECTORY
    same = runner.contract_copies(ROOT, runtime)
    assert same["mismatches"] == []
    # Line endings change no digest (Consiliency/jevdrill#90, item 11).
    for path in directory.glob("*.json"):
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert runner.contract_copies(ROOT, runtime) == same
    # Without the one substitution, a fixture copy differs.
    fixture = directory / "host.json"
    fixture.write_bytes(
        fixture.read_bytes().replace(runner.TOKEN_COUNTER_PLACEHOLDER, b"utf8-bytes-upper-bound-v2")
    )
    assert runner.contract_copies(ROOT, runtime)["mismatches"] == ["host.json"]
    # A differing schema copy, an extra file, a missing file and a wrong digest list.
    runtime = companion_tree(tmp_path / "other")
    directory = runtime / runner.CONTRACT_DIRECTORY
    (directory / "RouteInputs.json").write_bytes(b"{}\n")
    assert runner.contract_copies(ROOT, runtime)["mismatches"] == [
        "RouteInputs.json",
        "digests.json",
    ]
    write_digests(directory)
    assert runner.contract_copies(ROOT, runtime)["mismatches"] == ["RouteInputs.json"]
    (directory / "Extra.json").write_bytes(b"{}\n")
    assert (
        "unexpected or missing contract copies"
        in (runner.contract_copies(ROOT, runtime)["mismatches"])
    )
    (directory / "NoticeInbox.json").unlink()
    assert "NoticeInbox.json" in runner.contract_copies(ROOT, runtime)["mismatches"]


def test_source_digest_ignores_line_endings(tmp_path):
    (tmp_path / "src").mkdir()
    module = tmp_path / "src/module.py"
    module.write_bytes(b"one = 1\ntwo = 2\n")
    before = runner.source_digest(tmp_path)
    module.write_bytes(b"one = 1\r\ntwo = 2\r\n")
    assert runner.source_digest(tmp_path) == before
    module.write_bytes(b"one = 1\ntwo = 3\n")
    assert runner.source_digest(tmp_path) != before


def test_rebuilt_ids_keep_class_names_and_the_discovery_fixture_ids(tmp_path):
    """Declared change 2, and the ids the conformance fixture's discovery child rebuilds."""
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_jevdrill_discovery.py").write_text("")
    (tmp_path / "tests/test_observability.py").write_text("")
    report = tmp_path / "report.xml"
    report.write_text(
        "<testsuites><testsuite>"
        '<testcase classname="tests.test_jevdrill_discovery"'
        ' name="test_entered_linked_launch_rejections[decline]"/>'
        '<testcase classname="tests.test_observability.ObservabilityTest" name="test_one">'
        "<skipped/></testcase>"
        '<testcase classname="tests.test_observability" name="test_one"><failure/></testcase>'
        "</testsuite></testsuites>"
    )
    assert runner.assertions_from(report, tmp_path) == [
        {
            "node_id": "tests/test_jevdrill_discovery.py::test_entered_linked_launch_rejections"
            "[decline]",
            "outcome": "passed",
        },
        {
            "node_id": "tests/test_observability.py::ObservabilityTest::test_one",
            "outcome": "skipped",
        },
        {"node_id": "tests/test_observability.py::test_one", "outcome": "failed"},
    ]
    # The discovery child's ids, rebuilt this way, meet the reducer's discovery controls.
    rows = discovery_rows()
    receipt_value = witness()["companion_discovery"]
    receipt_value["assertions"] = rows
    receipt_value["assertions_sha256"] = runner.digest_value(rows)
    assert runner._discovery_errors(receipt_value, "companion") == []


def test_constants_name_every_control_once_and_records_agree():
    table = runner.expected_control_table()
    for name, (criterion, status, nodes) in runner.CLAUSES.items():
        assert (status == "covered") == bool(nodes), name
        assert all(node in table for node in nodes), name
        assert criterion in runner.REQUIREMENTS or criterion in {"JD-083", "JD-084", "scope"}
    covered = {criterion for criterion, status, _ in runner.CLAUSES.values() if status == "covered"}
    assert runner.REQUIREMENTS <= covered
    named = {node for _, _, nodes in runner.CLAUSES.values() for node in nodes}
    assert named == set(table)
    for nodes in runner.LAUNCH_PATHS.values():
        for node in nodes:
            assert node in table or node.split("[")[0] in table
            assert not node.startswith(runner.DESELECTED_LAUNCHER_CLASS)
    assert all((ROOT / path).is_file() for path in runner.TEST_PATHS)
    for os_name in runner.PLATFORMS:
        selected = sum(c.get(os_name, 0) for c in runner.COMPANION_CONTROL_COUNTS.values())
        assert selected <= runner.COMPANION_TOTALS[os_name]
    assert sum(runner.PROBE_COUNTS.values()) == runner.PROBE_TOTAL
    # This file's own controls of IF-0-VC-2 are held at their collected counts.
    assert runner.CONTROL_COUNTS[
        "tests/verification/test_host_phase.py::test_reducer_rejects_invalid_receipts"
    ] == len(FAULTS)
    assert runner.coverage_errors(ROOT) == []


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        ("count_changed", "control counts in the coverage record disagree with the verifier"),
        ("clause_covered", "clause coverage disagrees with the verifier"),
        ("clause_dropped", "clause coverage disagrees with the verifier"),
        ("launch_path_changed", "launch-path mapping disagrees with the verifier"),
        ("coverage_absent", "missing or malformed HOST coverage record"),
        ("spec_delta_decision", "malformed HOST spec-delta"),
        ("spec_delta_downstream", "malformed HOST spec-delta"),
        ("spec_delta_absent", "malformed HOST spec-delta"),
    ],
)
def test_records_must_agree_with_the_verifier(tmp_path, mutation, error):
    records = tmp_path / "evidence/HOST"
    records.mkdir(parents=True)
    for name in ("adapter-handoff.json", "coverage.json", "spec-delta.json"):
        shutil.copyfile(ROOT / "evidence/HOST" / name, records / name)
    assert runner.coverage_errors(tmp_path) == []
    coverage = json.loads((records / "coverage.json").read_text())
    delta = json.loads((records / "spec-delta.json").read_text())
    if mutation == "count_changed":
        coverage["controls"][next(iter(coverage["controls"]))]["counts"]["Linux"] += 1
    elif mutation == "clause_covered":
        coverage["clauses"]["EC-HOST-2/disconnect-advice"]["status"] = "covered"
    elif mutation == "clause_dropped":
        del coverage["clauses"]["scope/no-silent-forwarding"]
    elif mutation == "launch_path_changed":
        coverage["launch_paths"]["lane"] = coverage["launch_paths"]["lane"][:1]
    elif mutation == "spec_delta_decision":
        # The spec-delta check keeps roadmap_amendment (HOST plan, "The verifier").
        delta["decision"] = "canonical_spec_update"
    elif mutation == "spec_delta_downstream":
        delta["downstream_handling"] = "none"
    (records / "coverage.json").write_text(json.dumps(coverage))
    (records / "spec-delta.json").write_text(json.dumps(delta))
    if mutation == "coverage_absent":
        (records / "coverage.json").unlink()
    elif mutation == "spec_delta_absent":
        (records / "spec-delta.json").unlink()
    assert error in runner.coverage_errors(tmp_path)


def test_verifier_outputs_are_ignored_by_git():
    ignored = (ROOT / ".gitignore").read_text().splitlines()
    for path in (
        "evidence/HOST/platforms/",
        "evidence/HOST/evaluation.json",
        "evidence/HOST/verification.json",
        ".host/",
    ):
        assert path in ignored


class Children:
    """Stands in for every child process of one collection, and records each one."""

    def __init__(self, tmp_path, companion_code=0, timeout=False):
        self.calls = []
        self.tmp_path = tmp_path
        self.companion_code = companion_code
        self.timeout = timeout

    def __call__(self, args, **kwargs):
        self.calls.append((list(args), kwargs))
        if args[0] == "git":
            output = {"rev-parse": "a" * 40, "status": "", "remote": ""}[args[3]]
            return subprocess.CompletedProcess(args, 0, stdout=output)
        if args[1] == "-c":
            provenance = {
                "modules": HANDOFF["modules"],
                "version": HANDOFF["package_version"],
                "os": runner.platform.system(),
                "python_version": "3.12.9",
                "source_root_matches": True,
            }
            return subprocess.CompletedProcess(args, 0, json.dumps(provenance).encode(), b"")
        if "pytest" in args:
            if self.timeout:
                raise subprocess.TimeoutExpired(args, kwargs["timeout"])
            junit = Path(next(a for a in args if a.startswith("--junitxml=")).split("=", 1)[1])
            junit.write_text(
                '<testsuites><testsuite><testcase classname="tests.test_jevdrill_queue"'
                ' name="test_one"><failure/></testcase></testsuite></testsuites>'
            )
            return subprocess.CompletedProcess(args, self.companion_code, b"x", b"")
        return subprocess.CompletedProcess(args, 0, b"", b"")


@pytest.fixture
def collection(tmp_path, monkeypatch):
    companion_root = tmp_path / "companion"
    companion_tree(companion_root).joinpath("tests/test_jevdrill_queue.py").write_text("")
    interpreter = tmp_path / "python"
    interpreter.write_text("")
    for name in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_REPOSITORY", "RUNNER_TEMP"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("JEVDRILL_AGENT_HARNESS_PYTHON", str(interpreter))
    # Neither a credential, a proxy nor another behaviour switch may reach a child.
    monkeypatch.setenv("GITHUB_TOKEN", "planted-credential")
    monkeypatch.setenv("HTTPS_PROXY", "http://planted-proxy")
    monkeypatch.setenv("PHASE_LOOP_DESELECT_QUARANTINE", "1")
    cli = Path(runner.sys.executable).parent / (
        "jevdrill.exe" if runner.os.name == "nt" else "jevdrill"
    )
    if not cli.is_file():
        pytest.skip("the installed jevdrill CLI is not beside this interpreter")
    seen = []

    def route_collect(root, *, extra_test_paths):
        seen.append((dict(runner.os.environ), extra_test_paths))
        return {"assertions": [], "checks": [], "runner_identity": "machine"}

    monkeypatch.setattr(runner.route, "collect", route_collect)
    return companion_root, seen


def test_collector_children_get_only_the_allowlist_and_run_once(collection, tmp_path, monkeypatch):
    companion_root, seen = collection
    children = Children(tmp_path, companion_code=1)
    monkeypatch.setattr(runner.subprocess, "run", children)
    receipt_value = runner.collect(ROOT, companion_root)
    allowed = {*runner.INHERITED_VARIABLES, "HOME", "USERPROFILE", "NO_PROXY", "no_proxy"}
    companion_runs = [kw for args, kw in children.calls if "pytest" in args]
    assert len(companion_runs) == 1  # No retry and no rerun on failure.
    for args, kwargs in children.calls:
        env = kwargs["env"]
        named = (
            {"PYTHONPATH", "JEVDRILL_TEST_CLI", "JEVDRILL_TEST_PYTHON"}
            if "pytest" in args
            else set()
        )
        named |= set(runner.SCHEDULER_SWITCH) if "pytest" in args else set()
        assert set(env) <= allowed | named, args
        assert ("PHASE_LOOP_TDD_EXPECT_SCHED" in env) is ("pytest" in args)
    assert companion_runs[0]["env"]["PHASE_LOOP_TDD_EXPECT_SCHED"] == "1"
    assert companion_runs[0]["timeout"] <= runner.COLLECTION_BOUND_SECONDS
    ((route_env, paths),) = seen
    assert paths == runner.TEST_PATHS
    assert set(route_env) <= {
        *runner.ROUTE_INHERITED_VARIABLES,
        "JEVDRILL_AGENT_HARNESS_ROOT",
        "JEVDRILL_AGENT_HARNESS_PYTHON",
        "JEVDRILL_TEST_CLI",
        "JEVDRILL_EVALUATION_OUTPUT",
    }
    assert "GITHUB_TOKEN" not in route_env and "HTTPS_PROXY" not in route_env
    assert runner.os.environ["GITHUB_TOKEN"] == "planted-credential"  # restored afterwards
    companion = receipt_value["companion"]
    assert companion["command"] == runner.expected_companion_command(runner.platform.system())
    assert companion["exit_code"] == 1 and companion["deadline_expired"] is False
    assert receipt_value["failed_ids"] == ["tests/test_jevdrill_queue.py::test_one"]
    # A local collection names no machine and no run; no reduction accepts it.
    assert receipt_value["runner_identity"] == "local"
    assert receipt_value["route_regressions"]["runner_identity"] == "local"
    assert str(tmp_path) not in json.dumps(receipt_value)


def test_collector_records_a_deadline_as_a_deadline(collection, tmp_path, monkeypatch):
    companion_root, _ = collection
    children = Children(tmp_path, timeout=True)
    monkeypatch.setattr(runner.subprocess, "run", children)
    receipt_value = runner.collect(ROOT, companion_root)
    assert len([args for args, _ in children.calls if "pytest" in args]) == 1
    companion = receipt_value["companion"]
    assert companion["deadline_expired"] is True and companion["exit_code"] == 125
    assert companion["assertions"] == [] and receipt_value["failed_ids"] == []
    errors = runner._companion_errors(companion, receipt_value["os"], HANDOFF, {})
    assert "companion tests exceeded the collection deadline" in errors


def test_collector_stops_when_the_companion_does_not_import(collection, tmp_path, monkeypatch):
    companion_root, seen = collection
    calls = []

    def children(args, **kwargs):
        calls.append(args)
        if args[0] == "git":
            return subprocess.CompletedProcess(args, 0, stdout="")
        return subprocess.CompletedProcess(args, 1, b"", b"ModuleNotFoundError: fcntl")

    monkeypatch.setattr(runner.subprocess, "run", children)
    with pytest.raises(runner.CollectionError, match="companion did not import"):
        runner.collect(ROOT, companion_root)
    assert seen == [] and not any("pytest" in args for args in calls)
