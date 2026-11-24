import contextlib
import copy
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path
from typing import ClassVar

import pytest

ROOT = Path(__file__).parents[2]
spec = importlib.util.spec_from_file_location(
    "host_verification", ROOT / "scripts/verify_host_phase.py"
)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

HANDOFF = json.loads((ROOT / "evidence/HOST/adapter-handoff.json").read_text())
RUN = {"run_id": "1001", "run_attempt": "1", "repository": "Consiliency/jevdrill"}
JEVDRILL_COMMIT = "c" * 40
GIT_CONFIG = "d" * 64
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
            "task_id": "judged-task",
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
    by_source = {
        source: rows_for(
            {
                node: count
                for node, count in runner.CONTROL_COUNTS.items()
                if runner.CONTROL_SOURCES[node] == source
            }
        )
        for source in (runner.INHERITED, runner.HOST)
    }
    host_command = runner.expected_host_command()
    inherited_command = runner.expected_inherited_command(os_name)
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
        "jevdrill": {
            "repository": RUN["repository"],
            "commit": JEVDRILL_COMMIT,
            "clean": True,
            "git_config_sha256": GIT_CONFIG,
        },
        "input_digest": "fixture",
        "source_stable": True,
        "inherited_call": {"exit_code": 0, "deadline_expired": False},
        "route_regressions": {
            "assertions": by_source[runner.INHERITED],
            "checks": [{"name": "tests", "command": inherited_command, "exit_code": 0}],
            "runner_identity": RUN["run_id"],
            "python_minor": "3.14",
            "python_version": "3.14.0",
            "duration_seconds": 100.0,
        },
        "host_controls": {
            "command": host_command,
            "command_sha256": runner.digest_value(host_command),
            "exit_code": 0,
            "deadline_expired": False,
            "output_sha256": "c" * 64,
            "assertions": by_source[runner.HOST],
            "assertions_sha256": runner.digest_value(by_source[runner.HOST]),
            "duration_seconds": 90.0,
        },
        "companion": {
            "repository": HANDOFF["repository"],
            "commit": HANDOFF["commit"],
            "clean": True,
            "git_config_sha256": GIT_CONFIG,
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
            "contract_substitution": list(runner.CONTRACT_SUBSTITUTION),
            "command_sha256": runner.companion_command_digest(command),
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
        "host_static": {
            "command": list(runner.HOST_STATIC_COMMAND),
            "exit_code": 0,
            "output_sha256": "b" * 64,
        },
        "checkouts_after": {
            "jevdrill": {
                "repository": RUN["repository"],
                "commit": JEVDRILL_COMMIT,
                "clean": True,
                "git_config_sha256": GIT_CONFIG,
            },
            "companion": {
                "repository": HANDOFF["repository"],
                "commit": HANDOFF["commit"],
                "clean": True,
                "git_config_sha256": GIT_CONFIG,
            },
        },
        "parts": {"inherited_seconds": 100.5, "host_seconds": 149.5, "companion_seconds": 40.0},
        "failed_ids": [],
        "failed_checks": [],
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
    """Recompute what a collector derives, so that only the broken fact is wrong."""
    manifest["failed_ids"], manifest["failed_checks"] = runner.failure_summary(manifest)
    manifest["witness_sha256"] = runner.digest_value(manifest["witnesses"])
    companion = manifest["companion"]
    if "assertions" in companion:
        companion["assertions_sha256"] = runner.digest_value(companion["assertions"])
    host = manifest.get("host_controls")
    if isinstance(host, dict) and "assertions" in host:
        host["assertions_sha256"] = runner.digest_value(host["assertions"])
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
    elif fault == "inherited_over_600_seconds":
        row["parts"].update(inherited_seconds=600.5, host_seconds=149.5)
        row.update(duration_seconds=750.0, proof_cost_target_exceeded=True)
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
    elif fault == "missing_companion":
        row["companion"] = {}
    elif fault == "flags_only":
        row["witnesses"] = {"records": [], "entered": True, "decomposition": True}
    elif fault == "failed_control":
        node = "tests/conformance/test_notices.py::test_every_report_connection_queries_notices"
        next(r for r in row["host_controls"]["assertions"] if r["node_id"] == node)["outcome"] = (
            "failed"
        )
    elif fault == "missing_model":
        flow(row)["runs"][1].pop("model")
    elif fault == "non_object_run":
        flow(row)["runs"].append("task-2")
    elif fault == "non_string_effort":
        flow(row)["runs"][1]["effort"] = 2
    elif fault == "non_string_task_id":
        flow(row)["runs"][1]["task_id"] = 1
    elif fault == "boolean_judgment":
        judged = next(r for r in records if r.get("flow") == "judged")
        judged.update(stored_judgments=True, loopback_judgment_requests=True)
    elif fault == "judged_without_task":
        next(r for r in records if r.get("flow") == "judged").pop("task_id")
    elif fault == "exit_code_false":
        companion["exit_code"] = False
    elif fault == "discovery_exit_code_false":
        row["witnesses"]["companion_discovery"]["exit_code"] = False
    elif fault == "static_exit_code_false":
        row["host_static"]["exit_code"] = False
    elif fault == "failed_ids_mismatch":
        refresh(row)
        row["failed_ids"] = ["tests/test_jevdrill_queue.py::test_unnamed_0"]
        return
    elif fault == "failed_checks_mismatch":
        refresh(row)
        row["failed_checks"] = ["tests"]
        return
    elif fault == "static_digest_missing":
        row["host_static"].pop("output_sha256")
    elif fault == "discovery_lists_disagree":
        rows = [r for r in row["witnesses"]["assertions"] if "test_jevdrill_discovery" in r["id"]]
        rows[0]["id"] = "tests.test_jevdrill_discovery::test_other"
    elif fault == "inherited_other_run":
        row["route_regressions"]["runner_identity"] = "999"
    elif fault == "missing_attempt":
        row["workflow_run"]["run_attempt"] = None
    elif fault == "companion_version_disagrees":
        companion["python"]["version"] = "3.13.1"
        companion["installed_provenance"]["python_version"] = "3.13.1"
    elif fault == "python_version_disagrees":
        row["python_version"] = "3.13.0"
        row["route_regressions"]["python_version"] = "3.13.0"
    elif fault == "inherited_python_disagrees":
        row["route_regressions"]["python_version"] = "3.14.9"
    elif fault == "inherited_longer":
        row["route_regressions"]["duration_seconds"] = 260.0
    elif fault == "substitution_missing":
        companion.pop("contract_substitution")
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
    # Property 9, as declared change 17 divides it: the inherited part's 600-second bound, and
    # the five-minute flag. HOST's part and the other time faults are in test_time_faults_*.
    ("inherited_over_600_seconds", "inherited part over 600 seconds"),
    ("misreported_flag", "misreported five-minute proof-cost flag"),
    # The receipt's own source, provenance and interpreter.
    ("stale_input", "stale HOST input digest"),
    ("source_changed", "HOST inputs changed during collection"),
    ("installed_provenance", "mismatched installed companion provenance"),
    ("companion_python", "companion Python is not the pinned version"),
    ("old_schema", "unsupported HOST receipt"),
    ("collection_error", "Linux: collection failed: the companion did not import"),
    # The tag's three cases that had dropped out, each asserting its own error.
    ("missing_companion", "missing companion receipt"),
    ("flags_only", "missing production witnesses"),
    (
        "failed_control",
        (
            "failed or skipped HOST control: "
            "tests/conformance/test_notices.py::test_every_report_connection_queries_notices"
        ),
    ),
    # Typed two-task and judged-task records.
    ("missing_model", "missing independent two-task configuration"),
    ("non_object_run", "malformed discovery run list"),
    ("non_string_effort", "discovery run with no string effort"),
    ("non_string_task_id", "discovery run with no string task_id"),
    ("boolean_judgment", "missing v2 judged task"),
    ("judged_without_task", "missing v2 judged task"),
    # A receipt that contradicts itself.
    ("exit_code_false", "companion tests failed"),
    ("discovery_exit_code_false", "missing or mismatched integrated companion discovery"),
    ("static_exit_code_false", "failed or wrong host static check"),
    ("failed_ids_mismatch", "failed_ids disagrees with the assertions"),
    ("failed_checks_mismatch", "failed_checks disagrees with the checks"),
    ("static_digest_missing", "failed or wrong host static check"),
    ("discovery_lists_disagree", "the two discovery assertion lists disagree"),
    ("inherited_other_run", "inherited ROUTE receipt is from another run"),
    ("missing_attempt", "receipt is not from this workflow run"),
    ("companion_version_disagrees", "companion Python is not the pinned version"),
    ("python_version_disagrees", "Python version disagrees with the receipt's minor"),
    ("inherited_python_disagrees", "inherited ROUTE receipt's Python disagrees with the receipt's"),
    ("inherited_longer", "inherited collection longer than its receipt's"),
    ("substitution_missing", "companion receipt does not name the contract substitution"),
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
    assert report["jevdrill"] == {"repository": RUN["repository"], "commit": JEVDRILL_COMMIT}
    # The same receipts produce the gate only once nothing stands uncovered.
    monkeypatch.setattr(runner, "not_covered", list)
    report = runner.verdict(manifests, reference)
    assert report["status"] == "passed" and report["produced_if_gates"] == ["IF-0-HOST-1"]
    # Over five minutes is flagged, not rejected.
    # The total is the sum of the two parts (declared change 17), so the HOST part moves with it.
    manifests[0].update(duration_seconds=301.0, proof_cost_target_exceeded=True)
    manifests[0]["parts"]["host_seconds"] = 200.5
    report = runner.verdict(manifests, reference)
    assert report["proof_cost_over_five_minutes"] == [manifests[0]["os"]]
    assert report["produced_if_gates"] == ["IF-0-HOST-1"]


def test_verdict_names_the_clauses_outside_the_plans_reading(evidence, monkeypatch):
    manifests, reference = evidence
    expected = sorted(
        name for name, (_c, status, _n) in runner.CLAUSES.items() if status == "outside_reading"
    )
    assert expected == ["EC-HOST-3/live-evaluation"]
    assert runner.verdict(manifests, reference)["outside_reading"] == expected
    # Shown beside a produced gate too: the gate rests on the plan's reading of EC-HOST-3.
    monkeypatch.setattr(runner, "not_covered", list)
    report = runner.verdict(manifests, reference)
    assert report["produced_if_gates"] == ["IF-0-HOST-1"]
    assert report["outside_reading"] == expected


def test_reducer_rejects_a_reduction_outside_the_run_or_on_a_foreign_checkout(evidence):
    manifests, reference = evidence
    outside = copy.deepcopy(reference)
    outside["run"]["run_id"] = None
    assert "reduction outside a workflow run" in runner.receipt_errors(manifests, outside)
    # A run id with no attempt: neither the reduction nor any receipt is accepted.
    no_attempt = copy.deepcopy(reference)
    no_attempt["run"]["run_attempt"] = None
    receipts = copy.deepcopy(manifests)
    for row in receipts:
        row["workflow_run"]["run_attempt"] = None
    errors = runner.receipt_errors(receipts, no_attempt)
    assert "reduction outside a workflow run" in errors, errors
    assert "Linux: receipt is not from this workflow run" in errors, errors
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
    ("value", "error"),
    [
        (None, "malformed HOST receipt"),
        ([], "malformed HOST receipt"),
        ("receipt", "malformed HOST receipt"),
        (7, "malformed HOST receipt"),
        ({"os": "Linux"}, "malformed platform identity"),
        ({"os": 1, "python_minor": "3.14"}, "malformed platform identity"),
    ],
)
def test_a_malformed_receipt_gives_a_verdict_not_a_traceback(evidence, value, error):
    manifests, reference = evidence
    assert runner.receipt_errors(manifests, reference) == []
    errors = runner.receipt_errors([*manifests[1:], value], reference)
    assert error in errors, errors


def deep(depth=200):
    """Nested deeper than the verifier's bound, yet shallow enough for any Python to handle."""
    assert depth > runner.MAX_RECEIPT_DEPTH
    value = []
    for _ in range(depth):
        value = [value]
    return value


@pytest.mark.parametrize(
    ("case", "error"),
    [
        # A number too large for a float, where it is compared with the 600-second bound.
        ("huge_duration", "Linux: no valid collection duration"),
        # Nesting deeper than the verifier's explicit bound.
        ("deep_witness", "Linux: malformed receipt (nesting deeper than 64)"),
        ("architecture_number", "Linux: missing or malformed architecture"),
        ("architecture_list", "Linux: missing or malformed architecture"),
        ("python_version_text", "Linux: Python version disagrees with the receipt's minor"),
        ("collection_error_object", "Linux: collection failed: malformed collection error"),
    ],
)
def test_malformed_fields_are_reported_with_their_own_error(evidence, case, error):
    manifests, reference = evidence
    assert runner.receipt_errors(manifests, reference) == []
    row = next(m for m in manifests if m["os"] == "Linux")
    if case == "huge_duration":
        row["duration_seconds"] = 10**400
    elif case == "deep_witness":
        row["witnesses"]["records"][0]["nested"] = deep()
    elif case == "architecture_number":
        row["architecture"] = 7
    elif case == "architecture_list":
        row["architecture"] = ["X64"]
    elif case == "python_version_text":
        row["python_version"] = "text"
    else:
        manifests[manifests.index(row)] = {"os": "Linux", "python_minor": "3.14"} | {
            "collection_error": {"nested": [[[[]]]]}
        }
    errors = runner.receipt_errors(manifests, reference)
    assert error in errors, errors


def test_a_deeply_nested_platform_name_is_reported_not_raised(evidence):
    manifests, reference = evidence
    malformed = {"os": deep(), "python_minor": "3.14", "proof_cost_target_exceeded": True}
    report = runner.verdict([*manifests[1:], malformed], reference)
    assert "malformed platform identity" in report["errors"], report["errors"]
    # Only a string names a platform in the verdict's own lists.
    assert report["platforms"] == sorted(m["os"] for m in manifests[1:])
    assert report["proof_cost_over_five_minutes"] == []


@pytest.mark.parametrize(
    ("text", "error"),
    [
        ("{", "unreadable HOST receipt Linux-3.14.json: JSONDecodeError"),
        ("[" * 200 + "]" * 200, "unreadable HOST receipt Linux-3.14.json: nesting deeper than 64"),
        (
            '{"duration_seconds": ' + "9" * 101 + "}",
            "unreadable HOST receipt Linux-3.14.json: integer longer than 100 digits",
        ),
        (
            '{"duration_seconds": NaN}',
            "unreadable HOST receipt Linux-3.14.json: non-standard JSON constant NaN",
        ),
        (
            '{"os": "Linux", "os": "Darwin"}',
            "unreadable HOST receipt Linux-3.14.json: duplicate key",
        ),
    ],
    ids=["unparsable", "deep", "long_number", "nan", "duplicate_key"],
)
def test_unreadable_receipt_files_are_reported(tmp_path, evidence, text, error):
    manifests, reference = evidence
    for manifest in manifests:
        name = f"{manifest['os']}-{manifest['python_minor']}.json"
        (tmp_path / name).write_text(json.dumps(manifest))
    (tmp_path / "Linux-3.14.json").write_text(text)
    receipts = runner.read_receipts(tmp_path)
    report = runner.verdict(
        [value for _, value in receipts], reference, names=[name for name, _ in receipts]
    )
    assert error in report["errors"], report["errors"]
    assert "missing Linux/Python 3.14" in report["errors"]
    assert report["produced_if_gates"] == []


def test_a_receipt_file_must_name_its_platform(tmp_path, evidence):
    manifests, reference = evidence
    for manifest in manifests:
        (tmp_path / f"{manifest['os']}-{manifest['python_minor']}.json").write_text(
            json.dumps(manifest)
        )
    receipts = runner.read_receipts(tmp_path)
    names = [name for name, _ in receipts]
    values = [value for _, value in receipts]
    assert runner.receipt_errors(values, reference, names=names) == []
    swapped = [names[1], names[0], *names[2:]]
    errors = runner.receipt_errors(values, reference, names=swapped)
    assert any("names another platform" in item for item in errors), errors


def test_an_exception_in_the_inherited_reduction_is_reported(evidence, monkeypatch):
    manifests, reference = evidence
    assert runner.receipt_errors(manifests, reference) == []

    def raises(*_args, **_kwargs):
        raise TypeError("a malformed inherited receipt")

    monkeypatch.setattr(runner.route, "reduce_manifests", raises)
    errors = runner.receipt_errors(manifests, reference)
    assert "Linux: ROUTE regression: malformed inherited regressions" in errors, errors


def test_every_malformed_field_gives_a_verdict_not_a_traceback(evidence):
    manifests, reference = evidence
    assert runner.receipt_errors(manifests, reference) == []
    original = manifests[0]
    # Every field the reducer reads. The companion's `environment` is a description it does not
    # check, and the inherited checks are the (here stubbed) ROUTE reduction's to judge.
    paths = [(key,) for key in original]
    paths += [("companion", key) for key in original["companion"] if key != "environment"]
    paths += [("witnesses", key) for key in original["witnesses"]]
    paths += [("witnesses", "companion_discovery", key) for key in witness()["companion_discovery"]]
    paths += [
        ("route_regressions", key) for key in original["route_regressions"] if key != "checks"
    ]
    for path in paths:
        for value in (None, 7, "text", [1, "x", None], {"x": 1}, 10**400, True):
            if (path, value) in (
                (("architecture",), "text"),
                (("route_regressions", "duration_seconds"), 7),
            ):
                continue  # valid: any architecture string; an inherited collection of 7 seconds
            row = copy.deepcopy(original)
            target = row
            for key in path[:-1]:
                target = target[key]
            if type(target[path[-1]]) is type(value) and target[path[-1]] == value:
                continue  # the value the valid receipt already has
            target[path[-1]] = value
            errors = runner.receipt_errors([row, *manifests[1:]], reference)
            # The broken receipt has an error of its own, from a reducer that raised nothing.
            assert any(
                item.startswith(original["os"] + ":")
                or item in ("malformed platform identity", "unexpected or duplicate platform")
                for item in errors
            ), (path, value, errors)


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
            command = next(a for a in args[1:] if a in ("rev-parse", "status", "remote", "config"))
            output = {"rev-parse": "a" * 40, "status": "", "remote": "", "config": ""}[command]
            return subprocess.CompletedProcess(args, 0, stdout=output)
        if args[1:3] == ["-c", runner.INHERITED_CALL]:
            # The inherited call writes the ROUTE collector's receipt where it is told to.
            route_receipt = {"assertions": [], "checks": [], "runner_identity": "machine"}
            Path(args[4]).write_text(json.dumps(route_receipt))
            return subprocess.CompletedProcess(args, 0, b"", b"")
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
            if junit.name == "host.xml":
                junit.write_text(
                    '<testsuites><testsuite><testcase classname="tests.verification.test_host_phase"'
                    ' name="test_one"/></testsuite></testsuites>'
                )
                return subprocess.CompletedProcess(args, 0, b"", b"")
            junit.write_text(
                '<testsuites><testsuite><testcase classname="tests.test_jevdrill_queue"'
                ' name="test_one"><failure/></testcase></testsuite></testsuites>'
            )
            # A failing child's output is printed to the log: it tries to issue a command.
            output = b"::error::a forged annotation\n::add-mask::hidden\n"
            return subprocess.CompletedProcess(args, self.companion_code, output, b"")
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
    # HOST's command must pass whole, so nothing in this file may skip: HOST's command, like unit
    # CI, always runs with the package installed. A missing CLI is a broken environment.
    if not cli.is_file():
        pytest.fail(f"the installed jevdrill CLI is not beside this interpreter: {cli}", False)
    seen = []

    def run_child(command, *, cwd, env, timeout, capture=True, launched=None):
        """The collector's one way to start a child, through `subprocess.run` as stood in for."""
        if launched is not None:
            launched.append(list(command))
        if command[1:3] == ["-c", runner.INHERITED_CALL]:
            seen.append((dict(env), list(command), timeout))
        try:
            result = runner.subprocess.run(
                command, cwd=cwd, env=env, capture_output=True, timeout=timeout, check=False
            )
        except subprocess.TimeoutExpired:
            return 125, b"TimeoutExpired\n", True
        return result.returncode, result.stdout + result.stderr, False

    monkeypatch.setattr(runner, "_run", run_child)
    return companion_root, seen


def test_collector_children_get_only_the_allowlist_and_run_once(collection, tmp_path, monkeypatch):
    companion_root, seen = collection
    children = Children(tmp_path, companion_code=1)
    monkeypatch.setattr(runner.subprocess, "run", children)
    receipt_value = runner.collect(ROOT, companion_root)
    allowed = {*runner.INHERITED_VARIABLES, "HOME", "USERPROFILE", "NO_PROXY", "no_proxy"}
    companion_runs = [kw for args, kw in children.calls if reports(args, "companion.xml")]
    assert len(companion_runs) == 1  # No retry and no rerun on failure.
    # The inherited call and HOST's command get the ROUTE allowlist and the four HOST values.
    route_children = [
        (args, kw)
        for args, kw in children.calls
        if args[1:3] == ["-c", runner.INHERITED_CALL] or reports(args, "host.xml")
    ]
    assert len(route_children) == 2
    for args, kwargs in children.calls:
        env = kwargs["env"]
        if (args, kwargs) in route_children:
            assert set(env) <= {*runner.ROUTE_INHERITED_VARIABLES, *runner.HOST_VARIABLES}, args
            assert "PHASE_LOOP_TDD_EXPECT_SCHED" not in env
            continue
        named = (
            {"PYTHONPATH", "JEVDRILL_TEST_CLI", "JEVDRILL_TEST_PYTHON"}
            if "pytest" in args
            else set()
        )
        named |= set(runner.SCHEDULER_SWITCH) if "pytest" in args else set()
        # The cleanness check's git calls also name an empty global configuration and no system one.
        named |= {"GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM"} if args[0] == "git" else set()
        assert set(env) <= allowed | named, args
        assert ("PHASE_LOOP_TDD_EXPECT_SCHED" in env) is ("pytest" in args)
    assert companion_runs[0]["env"]["PHASE_LOOP_TDD_EXPECT_SCHED"] == "1"
    assert companion_runs[0]["timeout"] <= runner.HOST_BOUND_SECONDS
    # One call of the ROUTE collector: no path is added, its budget is ROUTE's own.
    ((route_env, command, timeout),) = seen
    assert command[:3] == [runner.sys.executable, "-c", runner.INHERITED_CALL]
    assert command[3] == str(ROOT) and len(command) == 5
    assert timeout == runner.INHERITED_BOUND_SECONDS + runner.INHERITED_WATCHDOG_GRACE_SECONDS
    assert set(route_env) <= {*runner.ROUTE_INHERITED_VARIABLES, *runner.HOST_VARIABLES}
    assert "GITHUB_TOKEN" not in route_env and "HTTPS_PROXY" not in route_env
    assert runner.os.environ["GITHUB_TOKEN"] == "planted-credential"  # never removed
    companion = receipt_value["companion"]
    assert companion["command"] == runner.expected_companion_command(runner.platform.system())
    assert companion["exit_code"] == 1 and companion["deadline_expired"] is False
    assert receipt_value["failed_ids"] == ["tests/test_jevdrill_queue.py::test_one"]
    # A local collection names no machine and no run; no reduction accepts it.
    assert receipt_value["runner_identity"] == "local"
    assert receipt_value["route_regressions"]["runner_identity"] == "local"
    assert str(tmp_path) not in json.dumps(receipt_value)


def reports(args, name):
    """Whether a child is the pytest command that writes the JUnit report `name`."""
    return any(part.startswith("--junitxml=") and part.endswith(name) for part in args)


def test_child_output_in_the_log_cannot_issue_workflow_commands(
    collection, tmp_path, monkeypatch, capsys
):
    companion_root, _ = collection
    monkeypatch.setattr(runner.subprocess, "run", Children(tmp_path, companion_code=1))
    runner.collect(ROOT, companion_root)
    lines = capsys.readouterr().out.splitlines()
    forged = lines.index("::error::a forged annotation")
    stops = [i for i, line in enumerate(lines) if line.startswith("::stop-commands::")]
    assert len(stops) == 1 and stops[0] < forged
    token = lines[stops[0]].removeprefix("::stop-commands::")
    assert len(token) == 32 and "::" + token + "::" in lines[forged:]
    assert lines.index("::" + token + "::") > lines.index("::add-mask::hidden")


def test_collector_records_a_deadline_as_a_deadline(collection, tmp_path, monkeypatch):
    companion_root, _ = collection
    children = Children(tmp_path, timeout=True)
    monkeypatch.setattr(runner.subprocess, "run", children)
    receipt_value = runner.collect(ROOT, companion_root)
    assert len([args for args, _ in children.calls if reports(args, "companion.xml")]) == 1
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


# Declared change 17 (HOST plan, SL-6): the inherited part and HOST's own part.


def linux(manifests):
    return next(m for m in manifests if m["os"] == "Linux")


def host_rows(manifest):
    return manifest["host_controls"]["assertions"]


_INHERITED_CONTROL = (
    "tests/privacy/test_sink_proof.py::"
    "test_a_report_with_a_refused_identifier_is_refused_before_it_is_stored"
)
_MOVED_CONTROL = (
    "tests/conformance/test_transport_queue.py::test_entered_ack_loss_and_cross_producer_deletion"
)


REQUIREMENT_1_CASES = [
    ("no_host_receipt", "missing HOST command receipt"),
    ("no_host_assertions", "missing or malformed HOST command assertions"),
    ("host_exit_code", "HOST command failed"),
    ("host_output_digest", "HOST command failed"),
    ("host_deadline", "HOST command stopped at HOST's 900-second bound"),
    ("host_time_missing", "missing or malformed part time"),
    ("failed_unnamed_host_test", "failed or skipped test in HOST's command: tests/x.py::t"),
    ("duplicate_host_test", "a test appears twice in HOST's command"),
]


@pytest.mark.parametrize(
    ("fault", "error"),
    REQUIREMENT_1_CASES,
    ids=[fault for fault, _ in REQUIREMENT_1_CASES],
)
def test_requirement_1_hosts_command_is_an_inventory_of_its_own(evidence, fault, error):
    """Requirement 1: HOST's command, exit code, each test's id and outcome, and its time."""
    manifests, reference = evidence
    row = linux(manifests)
    host = row["host_controls"]
    if fault == "no_host_receipt":
        del row["host_controls"]
    elif fault == "no_host_assertions":
        host["assertions"] = []
    elif fault == "host_exit_code":
        host["exit_code"] = 1
    elif fault == "host_output_digest":
        del host["output_sha256"]
    elif fault == "host_deadline":
        host["deadline_expired"] = True
    elif fault == "host_time_missing":
        del host["duration_seconds"]
    elif fault == "failed_unnamed_host_test":
        host["assertions"].append({"node_id": "tests/x.py::t", "outcome": "failed"})
    else:
        host["assertions"].append(dict(host["assertions"][0]))
    refresh(row)
    errors = runner.receipt_errors(manifests, reference)
    assert "Linux: " + error in errors, errors


def test_requirement_1_the_collector_records_hosts_command(collection, tmp_path, monkeypatch):
    companion_root, _ = collection
    monkeypatch.setattr(runner.subprocess, "run", Children(tmp_path))
    host = runner.collect(ROOT, companion_root)["host_controls"]
    assert host["command"] == runner.expected_host_command()
    assert host["command_sha256"] == runner.digest_value(runner.expected_host_command())
    assert host["exit_code"] == 0 and host["deadline_expired"] is False
    assert host["assertions"] == [
        {"node_id": "tests/verification/test_host_phase.py::test_one", "outcome": "passed"}
    ]
    assert host["assertions_sha256"] == runner.digest_value(host["assertions"])
    assert runner._seconds(host["duration_seconds"])


def test_requirement_2_every_control_has_one_stated_source(tmp_path):
    """The source table names every control once; "inherited" exactly when ROUTE selects it."""
    assert set(runner.CONTROL_SOURCES) == set(runner.CONTROL_COUNTS)
    assert set(runner.CONTROL_SOURCES.values()) == {runner.INHERITED, runner.HOST}
    for os_name in runner.PLATFORMS:
        command = runner.route.commands_for("python", tmp_path, os_name)["tests"]
        selected = [arg for arg in command if arg.startswith("tests/")]

        def routed(path, selected=selected):
            return any(path == arg or path.startswith(arg + "/") for arg in selected)

        for node, source in runner.CONTROL_SOURCES.items():
            assert routed(node.split("::")[0]) is (source == runner.INHERITED), node
        # HOST's command selects nothing ROUTE's command selects: no test runs in both.
        assert not any(routed(path) for path in runner.HOST_TEST_PATHS)
        deselected = [arg for arg in command if arg.startswith("--deselect=")]
        assert not any(
            arg.split("=", 1)[1].split("::")[0] in runner.HOST_TEST_PATHS for arg in deselected
        )
    assert runner.HOST_TEST_PATHS == tuple(
        sorted({n.split("::")[0] for n, s in runner.CONTROL_SOURCES.items() if s == runner.HOST})
    )


REQUIREMENT_2_CASES = [
    (
        "inherited_control_also_in_host",
        "control counted from two sources: " + _INHERITED_CONTROL,
    ),
    ("moved_control_also_inherited", "control counted from two sources: " + _MOVED_CONTROL),
    ("any_test_in_both", "a test ran in both commands: tests/x.py::t"),
    ("control_without_source", "control without a stated source: " + _MOVED_CONTROL),
]


@pytest.mark.parametrize(
    ("fault", "error"),
    REQUIREMENT_2_CASES,
    ids=[fault for fault, _ in REQUIREMENT_2_CASES],
)
def test_requirement_2_a_control_found_in_both_commands_is_rejected(
    evidence, monkeypatch, fault, error
):
    manifests, reference = evidence
    row = linux(manifests)
    inherited = row["route_regressions"]["assertions"]
    if fault == "inherited_control_also_in_host":
        host_rows(row).append({"node_id": _INHERITED_CONTROL, "outcome": "passed"})
    elif fault == "moved_control_also_inherited":
        inherited.append({"node_id": _MOVED_CONTROL, "outcome": "passed"})
    elif fault == "any_test_in_both":
        inherited.append({"node_id": "tests/x.py::t", "outcome": "passed"})
        host_rows(row).append({"node_id": "tests/x.py::t", "outcome": "passed"})
    else:
        sources = dict(runner.CONTROL_SOURCES)
        del sources[_MOVED_CONTROL]
        monkeypatch.setattr(runner, "CONTROL_SOURCES", sources)
    refresh(row)
    errors = runner.receipt_errors(manifests, reference)
    assert "Linux: " + error in errors, errors


@pytest.mark.parametrize("fault", ["moved_control_missing", "host_command_never_ran"])
def test_requirement_3_a_receipt_missing_a_moved_control_is_rejected(evidence, fault):
    manifests, reference = evidence
    row = linux(manifests)
    host = row["host_controls"]
    if fault == "moved_control_missing":
        host["assertions"] = [r for r in host["assertions"] if r["node_id"] != _MOVED_CONTROL]
        moved = [_MOVED_CONTROL]
    else:
        # A HOST command that never ran leaves every moved control missing.
        host.update(assertions=[], exit_code=125, deadline_expired=True)
        moved = [n for n, s in runner.CONTROL_SOURCES.items() if s == runner.HOST]
    refresh(row)
    errors = runner.receipt_errors(manifests, reference)
    for node in moved:
        assert "Linux: HOST control count not exact: " + node in errors, errors


def test_requirement_3_a_failure_summary_must_name_a_failed_moved_case(evidence):
    manifests, reference = evidence
    row = linux(manifests)
    case = next(r for r in host_rows(row) if r["node_id"].startswith(_MOVED_CONTROL))
    case["outcome"] = "failed"
    refresh(row)
    assert case["node_id"] in row["failed_ids"]
    assert "Linux: failed_ids disagrees with the assertions" not in (
        runner.receipt_errors(manifests, reference)
    )
    row["failed_ids"] = [i for i in row["failed_ids"] if i != case["node_id"]]
    errors = runner.receipt_errors(manifests, reference)
    assert "Linux: failed_ids disagrees with the assertions" in errors, errors


PLANTED = {
    "GITHUB_TOKEN": "planted-credential",
    "ACTIONS_RUNTIME_TOKEN": "planted-credential",
    "ACTIONS_ID_TOKEN_REQUEST_TOKEN": "planted-credential",
    "ACTIONS_ID_TOKEN_REQUEST_URL": "https://planted.invalid",
    "AWS_SECRET_ACCESS_KEY": "planted-credential",
    "NPM_TOKEN": "planted-credential",
    "SSH_AUTH_SOCK": "/planted/agent",
    "HTTP_PROXY": "http://planted-proxy",
    "HTTPS_PROXY": "http://planted-proxy",
    "http_proxy": "http://planted-proxy",
    "https_proxy": "http://planted-proxy",
    "ALL_PROXY": "http://planted-proxy",
    "NO_PROXY": "planted.invalid",
    "PHASE_LOOP_TDD_EXPECT_SCHED": "1",
}


def test_requirement_4_hosts_command_gets_the_allowlist_and_four_values_only(
    collection, tmp_path, monkeypatch
):
    companion_root, seen = collection
    for name, value in PLANTED.items():
        monkeypatch.setenv(name, value)
    children = Children(tmp_path)
    monkeypatch.setattr(runner.subprocess, "run", children)
    runner.collect(ROOT, companion_root)
    ((_host_args, host_kwargs),) = [
        (args, kw) for args, kw in children.calls if reports(args, "host.xml")
    ]
    env = host_kwargs["env"]
    allowlisted = {
        name
        for name in runner.ROUTE_INHERITED_VARIABLES
        if name in runner.os.environ and runner.os.environ.get(name) is not None
    }
    assert set(env) == allowlisted | set(runner.HOST_VARIABLES)
    assert not set(PLANTED) & set(env), set(PLANTED) & set(env)
    assert "PHASE_LOOP_TDD_EXPECT_SCHED" not in env
    for name in allowlisted:
        assert env[name] == runner.os.environ[name]
    assert env["JEVDRILL_AGENT_HARNESS_ROOT"] == str(companion_root)
    assert (
        env["JEVDRILL_AGENT_HARNESS_PYTHON"] == runner.os.environ["JEVDRILL_AGENT_HARNESS_PYTHON"]
    )
    assert Path(env["JEVDRILL_TEST_CLI"]).parent == Path(runner.sys.executable).parent
    assert Path(env["JEVDRILL_EVALUATION_OUTPUT"]).name == "witness.json"
    # The same environment as the inherited call's: the allowlist SL-3 gave it, and the values.
    ((route_env, _command, _timeout),) = seen
    assert env == route_env
    assert host_kwargs["cwd"] == ROOT


REQUIREMENT_5_CASES = [
    ("dropped_path", "HOST command is not the expected command"),
    ("added_selection", "HOST command is not the expected command"),
    ("changed_flag", "HOST command is not the expected command"),
    ("added_deselection", "HOST command is not the expected command"),
    ("wrong_digest", "HOST command digest mismatch"),
]


@pytest.mark.parametrize(
    ("fault", "error"),
    REQUIREMENT_5_CASES,
    ids=[fault for fault, _ in REQUIREMENT_5_CASES],
)
def test_requirement_5_hosts_command_is_rebuilt_from_the_verifiers_constants(
    evidence, fault, error
):
    manifests, reference = evidence
    row = linux(manifests)
    host = row["host_controls"]
    command = list(host["command"])
    if fault == "dropped_path":
        command.remove("tests/conformance/test_usage_reporting.py")
    elif fault == "added_selection":
        command[4:4] = ["-k", "not usage"]
    elif fault == "changed_flag":
        command[command.index("faulthandler_timeout=30")] = "faulthandler_timeout=3000"
    elif fault == "added_deselection":
        command.insert(-2, "--deselect=" + _MOVED_CONTROL)
    if fault == "wrong_digest":
        host["command_sha256"] = runner.digest_value(["<python>", "--help"])
    else:
        # A command and its own digest, consistent with each other, are still not the command.
        host.update(command=command, command_sha256=runner.digest_value(command))
    refresh(row)
    errors = runner.receipt_errors(manifests, reference)
    assert "Linux: " + error in errors, errors


def test_requirement_5_hosts_command_digest_ignores_paths_and_platforms():
    posix = runner.host_test_command("/opt/runner/python", "/tmp/jevdrill-host-1")
    windows = runner.host_test_command("D:\\a\\python.exe", "D:\\a\\_temp\\jevdrill-host-1")
    assert runner.normalized_command(posix, "host") == runner.normalized_command(windows, "host")
    assert runner.normalized_command(posix, "host") == runner.expected_host_command()
    assert [a for a in posix if a.startswith("tests/")] == list(runner.HOST_TEST_PATHS)


def kind(args):
    if args[0] == "git":
        return "git"
    if args[1:3] == ["-c", runner.INHERITED_CALL]:
        return "inherited"
    if args[1] == "-c":
        return "probe"
    if reports(args, "host.xml"):
        return "host"
    if reports(args, "companion.xml"):
        return "companion"
    return "static" if "ruff" in args else "other"


def test_requirement_6_the_order_is_fixed_and_checkouts_are_read_again_after_the_last(
    collection, tmp_path, monkeypatch
):
    companion_root, _ = collection
    children = Children(tmp_path)

    def dirtied_at_the_end(args, **kwargs):
        result = children(args, **kwargs)
        if (
            args[0] == "git"
            and "status" in args
            and any(kind(call) == "static" for call, _ in children.calls)
        ):
            return subprocess.CompletedProcess(args, 0, stdout=" M scripts/verify_host_phase.py")
        return result

    monkeypatch.setattr(runner.subprocess, "run", dirtied_at_the_end)
    receipt_value = runner.collect(ROOT, companion_root)
    order = [kind(args) for args, _ in children.calls]
    children_only = [name for name in order if name != "git"]
    assert children_only == ["probe", "inherited", "host", "companion", "static"]
    # Both checkouts are read before the first child and again after the last.
    assert order[:8] == ["git"] * 8 and order[-8:] == ["git"] * 8
    assert receipt_value["jevdrill"]["clean"] is True
    assert receipt_value["checkouts_after"]["jevdrill"]["clean"] is False
    assert receipt_value["checkouts_after"]["companion"]["clean"] is False


@pytest.mark.parametrize(
    "fault",
    [
        "jevdrill_unclean_after",
        "companion_unclean_after",
        "jevdrill_commit_changed",
        "companion_commit_changed",
        "no_second_reading",
    ],
)
def test_requirement_6_a_collection_that_left_a_checkout_changed_is_rejected(evidence, fault):
    manifests, reference = evidence
    row = linux(manifests)
    after = row["checkouts_after"]
    if fault == "jevdrill_unclean_after":
        after["jevdrill"]["clean"] = False
    elif fault == "companion_unclean_after":
        after["companion"]["clean"] = False
    elif fault == "jevdrill_commit_changed":
        after["jevdrill"]["commit"] = "e" * 40
    elif fault == "companion_commit_changed":
        after["companion"]["commit"] = "e" * 40
    else:
        del row["checkouts_after"]
    errors = runner.receipt_errors(manifests, reference)
    assert "Linux: a checkout changed or was left unclean by the collection" in errors, errors


GRANDCHILD = (
    "import os, socket, sys, time\n"
    "connection = socket.create_connection(('127.0.0.1', int(sys.argv[1])))\n"
    "connection.sendall(str(os.getpid()).encode() + b'\\n')\n"
    "time.sleep(300)\n"
)
PARENT = (
    "import os, subprocess, sys, time\n"
    "own_session = sys.argv[3] == 'own_session' and os.name != 'nt'\n"
    "subprocess.Popen([sys.executable, '-c', sys.argv[1], sys.argv[2]], start_new_session=own_session)\n"
    "if sys.argv[3] != 'returned':\n"
    "    time.sleep(120)\n"
)


@pytest.mark.parametrize("ending", ["deadline", "own_session", "returned"])
def test_requirement_7_a_child_and_every_process_it_started_are_stopped(monkeypatch, ending):
    """A real child starts a grandchild that would outlive it; neither outlives `_run`.

    "deadline": the child's bound is reached while both run. "own_session": the same, with the
    grandchild in a session of its own on Linux and macOS, as the companion's launcher starts
    its children. "returned": the child ends and leaves the grandchild running. The grandchild holds a loopback connection open, so its end
    is seen as the connection closing, on Linux, macOS and Windows alike. Nothing here waits on
    a deadline: the bound is reached when the grandchild is known to be running.
    """
    import signal
    import socket

    listener = socket.create_server(("127.0.0.1", 0))
    listener.settimeout(120)
    port = listener.getsockname()[1]
    held = {}

    def await_exit(child, timeout):
        connection, _ = listener.accept()
        # Each read is bounded by the socket's timeout; a peer that closes early, or sends more
        # than a process id, ends the loop with a failure instead of a spin.
        connection.settimeout(120)
        data = b""
        while not data.endswith(b"\n"):
            chunk = connection.recv(64)
            if not chunk or len(data) > 64:
                pytest.fail(f"the grandchild did not name itself before closing: {data!r}")
            data += chunk
        held.update(connection=connection, pid=int(data))
        if ending != "returned":
            raise subprocess.TimeoutExpired(child.args, timeout)
        return real_await_exit(child, 120)

    real_await_exit = runner._await_exit
    monkeypatch.setattr(runner, "_await_exit", await_exit)
    command = [runner.sys.executable, "-c", PARENT, GRANDCHILD, str(port), ending]
    try:
        code, output, expired = runner._run(
            command, cwd=ROOT, env=dict(runner.os.environ), timeout=600
        )
        assert expired is (ending != "returned")
        assert code == (0 if ending == "returned" else 125), output
        connection = held["connection"]
        connection.settimeout(60)
        try:
            ended = connection.recv(64) == b""
        except ConnectionResetError, ConnectionAbortedError:
            ended = True
        except TimeoutError:
            ended = False
        assert ended, "the grandchild outlived its child's stop"
    finally:
        listener.close()
        if "connection" in held:
            held["connection"].close()
        if "pid" in held:
            with contextlib.suppress(OSError):
                runner.os.kill(held["pid"], getattr(signal, "SIGKILL", signal.SIGTERM))


def test_requirement_7_a_child_whose_bound_is_spent_is_never_started(monkeypatch):
    def never(*_args, **_kwargs):
        raise AssertionError("no child is started once its bound is spent")

    monkeypatch.setattr(runner.subprocess, "Popen", never)
    assert runner._run(["python"], cwd=ROOT, env={}, timeout=0) == (
        125,
        b"TimeoutExpired\nthe bound was reached before this child started\n",
        True,
    )
    assert runner._run(["python"], cwd=ROOT, env={}, timeout=-1.0)[2] is True


def test_requirement_7_each_part_has_its_bound_and_outside_ci_the_limit_is_stated(
    collection, tmp_path, monkeypatch, capsys
):
    companion_root, seen = collection
    children = Children(tmp_path)
    monkeypatch.setattr(runner.subprocess, "run", children)
    runner.collect(ROOT, companion_root)
    out = capsys.readouterr().out
    assert f"at most {runner.TOTAL_LIMIT_SECONDS} seconds in total" in out
    assert runner.TOTAL_LIMIT_SECONDS == 1530
    ((_env, _command, timeout),) = seen
    assert timeout == runner.INHERITED_BOUND_SECONDS + runner.INHERITED_WATCHDOG_GRACE_SECONDS
    for args, kwargs in children.calls:
        if kind(args) in ("host", "companion", "static"):
            assert 0 < kwargs["timeout"] <= runner.HOST_BOUND_SECONDS, args
        if kind(args) == "probe":
            assert 0 < kwargs["timeout"] <= 30
    # In CI the run's own log says it; nothing is stated there.
    monkeypatch.setenv("GITHUB_RUN_ID", "1001")
    runner.collect(ROOT, companion_root)
    assert "seconds in total" not in capsys.readouterr().out


TIME_CASES = [
    ("host_over_900", "HOST part over 900 seconds"),
    ("inherited_over_600", "inherited part over 600 seconds"),
    ("parts_do_not_sum", "parts do not sum to the total"),
    ("parts_overshoot_total", "parts do not sum to the total"),
    ("parts_undershoot_total", "parts do not sum to the total"),
    ("inherited_615_after_its_bound", "inherited part over 600 seconds"),
    (
        "inherited_shorter_than_route",
        "inherited part shorter than the ROUTE receipt's own duration",
    ),
    ("commands_exceed_host_part", "HOST command and companion times exceed HOST's part"),
    ("no_parts", "missing or malformed part time"),
    ("missing_part", "missing or malformed part time"),
    ("text_part", "missing or malformed part time"),
    ("negative_part", "missing or malformed part time"),
    ("nan_part", "missing or malformed part time"),
    ("huge_part", "missing or malformed part time"),
    ("extra_part", "missing or malformed part time"),
]


@pytest.mark.parametrize(
    ("fault", "error"),
    TIME_CASES,
    ids=[fault for fault, _ in TIME_CASES],
)
def test_time_faults_are_each_their_own_error(evidence, fault, error):
    manifests, reference = evidence
    row = linux(manifests)
    parts = row["parts"]
    if fault == "host_over_900":
        parts["host_seconds"] = 900.5
        row.update(duration_seconds=1001.0, proof_cost_target_exceeded=True)
    elif fault == "inherited_over_600":
        parts["inherited_seconds"] = 600.001
        row.update(duration_seconds=749.501, proof_cost_target_exceeded=True)
    elif fault == "parts_do_not_sum":
        parts["host_seconds"] = 150.5
    elif fault == "parts_overshoot_total":
        # The inherited part raised alone: the parts no longer sum to the total.
        parts["inherited_seconds"] += 10
    elif fault == "parts_undershoot_total":
        parts.update(inherited_seconds=100.5, host_seconds=140.0)
        row.update(duration_seconds=1100.0, proof_cost_target_exceeded=True)
    elif fault == "inherited_615_after_its_bound":
        # An inherited call that ended inside the collector's watchdog grace, after ROUTE's 600 s.
        parts.update(inherited_seconds=615.0, host_seconds=149.5)
        row.update(duration_seconds=764.5, proof_cost_target_exceeded=True)
    elif fault == "inherited_shorter_than_route":
        parts.update(inherited_seconds=99.0, host_seconds=151.0)
    elif fault == "commands_exceed_host_part":
        parts["companion_seconds"] = 60.0
    elif fault == "no_parts":
        del row["parts"]
    elif fault == "missing_part":
        del parts["companion_seconds"]
    elif fault == "text_part":
        parts["host_seconds"] = "149.5"
    elif fault == "negative_part":
        parts.update(inherited_seconds=-1.0, host_seconds=251.0)
    elif fault == "nan_part":
        parts["host_seconds"] = float("nan")
    elif fault == "huge_part":
        parts["host_seconds"] = 10**400
    else:
        parts["setup_seconds"] = 1.0
    errors = runner.receipt_errors(manifests, reference)
    assert "Linux: " + error in errors, errors


def test_each_part_at_its_bound_is_accepted(evidence):
    manifests, reference = evidence
    row = linux(manifests)
    row["parts"].update(inherited_seconds=600.0, host_seconds=900.0, companion_seconds=40.0)
    row.update(duration_seconds=1500.0, proof_cost_target_exceeded=True)
    assert runner.receipt_errors(manifests, reference) == []
    # The ROUTE receipt rounds its duration to the millisecond; that rounding is allowed.
    row["route_regressions"]["duration_seconds"] = 600.0004
    assert runner.receipt_errors(manifests, reference) == []


def test_the_inherited_budget_is_routes_own(tmp_path, monkeypatch):
    """ROUTE's collector gives its children 600 seconds and its reducer allows 600; so does HOST."""
    import types

    calls = []

    def run(command, **kwargs):
        calls.append((list(command), kwargs.get("timeout")))
        return subprocess.CompletedProcess(command, 0, b"", b"")

    monkeypatch.setattr(runner.route.subprocess, "run", run)
    monkeypatch.setattr(runner.route, "time", types.SimpleNamespace(monotonic=lambda: 0.0))
    monkeypatch.setattr(runner.route, "input_digest", lambda _root: "route")
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    runner.route.collect(ROOT)
    budgets = {timeout for command, timeout in calls if command[-1] != "--version"}
    assert budgets == {runner.INHERITED_BOUND_SECONDS}

    def proof_cost_rejected(seconds):
        manifest = {"os": "Linux", "python_minor": "3.14", "duration_seconds": seconds}
        errors = runner.route.reduce_manifests([manifest], "route", ROOT)
        return "invalid or excessive single-node proof cost" in errors

    assert not proof_cost_rejected(runner.INHERITED_BOUND_SECONDS)
    assert proof_cost_rejected(runner.INHERITED_BOUND_SECONDS + 0.001)


@pytest.mark.parametrize("fault", ["host_paths_added", "no_tests_check", "other_os_command"])
def test_the_inherited_command_is_routes_own(evidence, monkeypatch, fault):
    manifests, reference = evidence
    row = linux(manifests)
    check = row["route_regressions"]["checks"][0]
    if fault == "host_paths_added":
        # The old inherited command: ROUTE's with HOST's paths added.
        old = runner.route.commands_for(
            "<python>", Path("<temporary>"), "Linux", extra_test_paths=runner.TEST_PATHS
        )["tests"]
        check["command"] = runner.route.normalized_command(old, "tests")
    elif fault == "no_tests_check":
        row["route_regressions"]["checks"] = []
    else:
        check["command"] = runner.expected_inherited_command("Windows")
    errors = runner.receipt_errors(manifests, reference)
    assert "Linux: inherited command differs from ROUTE's own" in errors, errors


def test_the_inherited_receipt_is_reduced_as_routes_own(evidence, monkeypatch):
    manifests, reference = evidence
    seen = []
    monkeypatch.setattr(runner.route, "reduce_manifests", lambda *a, **k: seen.append(k) or [])
    assert runner.receipt_errors(manifests, reference) == []
    assert len(seen) == 3 and all(set(k) == {"required_platforms"} for k in seen), seen


@pytest.mark.parametrize("fault", ["call_failed", "call_stopped", "call_missing"])
def test_an_inherited_call_that_failed_or_hit_its_bound_is_rejected(evidence, fault):
    manifests, reference = evidence
    row = linux(manifests)
    if fault == "call_failed":
        row["inherited_call"]["exit_code"] = 1
    elif fault == "call_stopped":
        row["inherited_call"].update(exit_code=125, deadline_expired=True)
    else:
        del row["inherited_call"]
    errors = runner.receipt_errors(manifests, reference)
    assert (
        "Linux: inherited ROUTE call failed or was stopped by the collector's watchdog" in errors
    ), errors


def test_a_receipt_of_the_old_shape_is_rejected_as_old(evidence):
    manifests, reference = evidence
    row = linux(manifests)
    # As SL-3's collector wrote it: HOST's controls inside the inherited command, one bound.
    row["schema_version"] = 3
    row["route_regressions"]["assertions"] += row.pop("host_controls")["assertions"]
    for key in ("parts", "inherited_call", "checkouts_after"):
        del row[key]
    refresh(row)
    errors = runner.receipt_errors(manifests, reference)
    assert "Linux: HOST receipt of an old shape (schema 3)" in errors, errors
    assert [e for e in errors if e.startswith("Linux")] == [
        "Linux: HOST receipt of an old shape (schema 3)",
        "Linux: unsupported HOST receipt",
    ]


class FakeClock:
    """A monotonic clock that moves only when a stood-in child runs."""

    def __init__(self):
        self.now = 1000.0

    def monotonic(self):
        return self.now


# Seconds each stood-in child takes on the fake clock.
CHILD_SECONDS = {"probe": 5.0, "inherited": 100.0, "host": 200.0, "companion": 50.0, "static": 10.0}


def clocked(monkeypatch, tmp_path, seconds=CHILD_SECONDS):
    clock = FakeClock()
    monkeypatch.setattr(runner, "time", clock)
    children = Children(tmp_path)

    def run(args, **kwargs):
        result = children(args, **kwargs)
        clock.now += seconds.get(kind(args), 0.0)
        return result

    monkeypatch.setattr(runner.subprocess, "run", run)
    return children


def test_the_collectors_clock_gives_each_child_hosts_remaining_time(
    collection, tmp_path, monkeypatch
):
    """Blocker 2: the remaining time each child is given, and the parts recorded, on one clock."""
    companion_root, _ = collection
    children = clocked(monkeypatch, tmp_path)
    receipt_value = runner.collect(ROOT, companion_root)
    timeouts = {
        kind(args): kwargs["timeout"] for args, kwargs in children.calls if kind(args) != "git"
    }
    # The probe comes first in HOST's part; the inherited call (5 s in) is not HOST's part.
    assert timeouts == {
        "probe": 30,
        "inherited": runner.INHERITED_BOUND_SECONDS + runner.INHERITED_WATCHDOG_GRACE_SECONDS,
        "host": 900 - 5.0,
        "companion": 900 - (5.0 + 200.0),
        "static": 900 - (5.0 + 200.0 + 50.0),
    }
    assert receipt_value["parts"] == {
        "inherited_seconds": 100.0,
        "host_seconds": 265.0,
        "companion_seconds": 50.0,
    }
    assert receipt_value["host_controls"]["duration_seconds"] == 200.0
    assert receipt_value["duration_seconds"] == 365.0


def test_the_watchdog_lets_routes_own_deadline_fire_and_hosts_part_is_unaffected(
    collection, tmp_path, monkeypatch
):
    """The president's ruling: a 30 s watchdog after the inherited bound, not a budget."""
    companion_root, seen = collection
    children = clocked(monkeypatch, tmp_path, {**CHILD_SECONDS, "inherited": 615.0})
    receipt_value = runner.collect(ROOT, companion_root)
    ((_env, _command, timeout),) = seen
    # Not stopped before ROUTE's own 600-second deadline has had time to fire.
    assert timeout > runner.INHERITED_BOUND_SECONDS
    assert timeout == runner.INHERITED_BOUND_SECONDS + runner.INHERITED_WATCHDOG_GRACE_SECONDS
    assert receipt_value["inherited_call"] == {"exit_code": 0, "deadline_expired": False}
    # HOST's part is unaffected: a late inherited call neither eats into its 900 s nor is
    # charged to it.
    timeouts = {
        kind(args): kwargs["timeout"] for args, kwargs in children.calls if kind(args) != "git"
    }
    assert timeouts["host"] == 900 - 5.0
    assert receipt_value["parts"]["inherited_seconds"] == 615.0
    assert receipt_value["parts"]["host_seconds"] == 265.0
    # The reducer is unchanged: an inherited part of 615 s is rejected
    # (test_time_faults_are_each_their_own_error[inherited_615_after_its_bound]).


@pytest.mark.parametrize("changed", ["jevdrill_inputs", "companion_sources"])
def test_requirement_6_the_collector_reads_its_inputs_again_after_the_last_child(
    collection, tmp_path, monkeypatch, changed
):
    """Blocker 3: the collector's own second reading of input stability, after the last child."""
    companion_root, _ = collection
    children = Children(tmp_path)
    monkeypatch.setattr(runner.subprocess, "run", children)
    name = "input_digest" if changed == "jevdrill_inputs" else "source_digest"
    real = getattr(runner, name)
    readings = []

    def digest(root):
        # The first reading is before any child; any later one sees changed inputs.
        readings.append([kind(args) for args, _ in children.calls])
        return real(root) if len(readings) == 1 else "changed during the collection"

    monkeypatch.setattr(runner, name, digest)
    receipt_value = runner.collect(ROOT, companion_root)
    assert readings[0] == [] and "static" in readings[-1]
    if changed == "jevdrill_inputs":
        assert receipt_value["source_stable"] is False
        assert receipt_value["companion"]["source_stable"] is True
    else:
        assert receipt_value["companion"]["source_stable"] is False
        assert receipt_value["source_stable"] is True


def test_requirement_7_a_failed_tree_stop_cannot_leave_an_unbounded_wait(monkeypatch):
    """If the tree's stop fails (TerminateJobObject or taskkill on Windows), the child itself is
    killed before it is waited for, and the wait is bounded."""
    events = []

    class LiveChild:
        pid, args, returncode = 4242, ["child"], None

        def __init__(self, *_args, **_kwargs):
            pass

        def kill(self):
            events.append("kill")
            self.returncode = -9

        def wait(self, timeout=None):
            if self.returncode is None:
                raise AssertionError("waited for a live child")
            assert timeout is not None, "an unbounded wait"
            events.append("wait")
            return self.returncode

    class FailingTree:
        POPEN_OPTIONS: ClassVar[dict] = {}

        def __init__(self, child):
            pass

        def stop(self):
            events.append("stop")
            return False

    def deadline(child, timeout):
        raise subprocess.TimeoutExpired(child.args, timeout)

    monkeypatch.setattr(runner.subprocess, "Popen", LiveChild)
    monkeypatch.setattr(runner, "ProcessTree", FailingTree)
    monkeypatch.setattr(runner, "_await_exit", deadline)
    code, _output, expired = runner._run(["child"], cwd=ROOT, env={}, timeout=10)
    assert (code, expired) == (125, True)
    assert events == ["stop", "kill", "wait"]


# Round 1 (Consiliency/jevdrill#140).


def test_a_receipt_of_schema_4_is_rejected_as_old(evidence):
    """Schema 5 adds the checkouts' git configuration digests; schema 4 receipts are old."""
    manifests, reference = evidence
    row = linux(manifests)
    row["schema_version"] = 4
    errors = runner.receipt_errors(manifests, reference)
    assert [e for e in errors if e.startswith("Linux")] == [
        "Linux: HOST receipt of an old shape (schema 4)",
        "Linux: unsupported HOST receipt",
    ]


def test_round1_a_failed_moved_case_stays_in_the_inventory_and_the_failure_summary(
    collection, tmp_path, monkeypatch
):
    """Vendor blocker 1: a failed moved case is recorded with its outcome, and in failed_ids."""
    companion_root, _ = collection
    children = Children(tmp_path)
    moved = "tests/conformance/test_transport_queue.py::test_entered_ack_loss_and_cross_producer_deletion"

    def host_report_with_a_failure(args, **kwargs):
        result = children(args, **kwargs)
        if reports(args, "host.xml"):
            junit = Path(next(a for a in args if a.startswith("--junitxml=")).split("=", 1)[1])
            junit.write_text(
                "<testsuites><testsuite>"
                '<testcase classname="tests.verification.test_host_phase" name="test_one"/>'
                '<testcase classname="tests.conformance.test_transport_queue"'
                ' name="test_entered_ack_loss_and_cross_producer_deletion"><failure/></testcase>'
                "</testsuite></testsuites>"
            )
            return subprocess.CompletedProcess(args, 1, b"", b"")
        return result

    monkeypatch.setattr(runner.subprocess, "run", host_report_with_a_failure)
    receipt_value = runner.collect(ROOT, companion_root)
    assert {"node_id": moved, "outcome": "failed"} in receipt_value["host_controls"]["assertions"]
    assert moved in receipt_value["failed_ids"]
    assert receipt_value["host_controls"]["exit_code"] == 1


def test_round1_27_of_the_28_contract_cases_is_rejected(evidence):
    """Vendor blocker 2: a presence check would accept this; the exact count does not."""
    manifests, reference = evidence
    row = linux(manifests)
    node = "tests/contracts/test_host_contracts.py::test_host_shared_contract"
    cases = [r for r in host_rows(row) if r["node_id"].startswith(node + "[")]
    assert len(cases) == 28
    host_rows(row).remove(cases[-1])
    refresh(row)
    errors = runner.receipt_errors(manifests, reference)
    assert "Linux: HOST control count not exact: " + node in errors, errors


def test_round1_a_malformed_id_in_hosts_command_is_rejected(evidence):
    """Vendor blocker 2: the singleton control's id with a bare "[" is not a test id."""
    manifests, reference = evidence
    row = linux(manifests)
    case = next(r for r in host_rows(row) if r["node_id"] == _MOVED_CONTROL)
    case["node_id"] = _MOVED_CONTROL + "["
    refresh(row)
    errors = runner.receipt_errors(manifests, reference)
    assert f"Linux: malformed test id in HOST's command: {_MOVED_CONTROL + '['!r}" in errors, errors


def test_round1_an_id_that_appears_twice_in_hosts_command_is_rejected(evidence):
    manifests, reference = evidence
    row = linux(manifests)
    host_rows(row).append({"node_id": _MOVED_CONTROL, "outcome": "passed"})
    refresh(row)
    errors = runner.receipt_errors(manifests, reference)
    assert "Linux: a test appears twice in HOST's command" in errors, errors


def test_round1_well_formed_ids_are_accepted_by_shape():
    for node in (
        "tests/x.py::test_a",
        "tests/a/b.py::Class::test_a[case-1: with spaces]",
        "tests/conformance/test_usage_reporting.py::test_installed_usage_persistence[x[1]]",
    ):
        assert runner._TEST_ID.fullmatch(node), node
    for node in (
        "tests/x.py::test_a[",
        "tests/x.py::test_a[]",
        "tests/x.py",
        "x.py::t",
        "tests/x.py::",
    ):
        assert not runner._TEST_ID.fullmatch(node), node


# HOST's command as the plan's SL-6 fixes it, written out here and not rebuilt from the verifier,
# so that a change to the verifier's builder fails this test.
EXPECTED_HOST_COMMAND = [
    "<python>",
    "-m",
    "pytest",
    "-q",
    "-o",
    "faulthandler_timeout=30",
    "tests/analysis/test_observations.py",
    "tests/application/test_host_notices.py",
    "tests/application/test_host_routing.py",
    "tests/conformance/test_discovery_handoff.py",
    "tests/conformance/test_launch_paths.py",
    "tests/conformance/test_notices.py",
    "tests/conformance/test_transport_queue.py",
    "tests/conformance/test_usage_reporting.py",
    "tests/contracts/test_host_contracts.py",
    "tests/storage/test_dry_run_evidence.py",
    "tests/storage/test_host_notices.py",
    "tests/verification/test_host_phase.py",
    "--junitxml=<temporary>/host.xml",
    "--basetemp=<temporary>/host-tests",
]


def test_round1_the_receipt_records_the_command_as_launched(collection, tmp_path, monkeypatch):
    """Vendor blocker 3: what the receipt records is what was launched, and it is the plan's
    command. A deselection added in the builder, or only at launch, fails here."""
    companion_root, _ = collection
    children = Children(tmp_path)
    monkeypatch.setattr(runner.subprocess, "run", children)
    receipt_value = runner.collect(ROOT, companion_root)
    ((launched, _),) = [(args, kw) for args, kw in children.calls if reports(args, "host.xml")]
    # `_run` is stood in for here, so the check is the comparison with the literal command below;
    # that the real `_run` launches what it records is test_round1_run_records_exactly_what_it_hands_to_popen.
    assert receipt_value["host_controls"]["command"] == EXPECTED_HOST_COMMAND
    assert runner.expected_host_command() == EXPECTED_HOST_COMMAND
    # Its selection covers every control counted from it, and nothing filters a control out.
    for node, source in runner.CONTROL_SOURCES.items():
        if source == runner.HOST:
            assert node.split("::")[0] in launched, node
    assert not any(a.startswith(("--deselect", "-k", "--lf", "--sw")) for a in launched)
    ((companion_launched, _),) = [
        (args, kw) for args, kw in children.calls if reports(args, "companion.xml")
    ]
    assert receipt_value["companion"]["command"] == runner.normalized_command(
        companion_launched, "companion"
    )


def launched_commands(tmp_path):
    """Every command the collector hands to `_run`, as its builders make them."""
    python = runner.sys.executable
    return {
        "host": runner.host_test_command(python, tmp_path),
        **{
            f"companion-{os_name}": runner.companion_command(python, tmp_path, os_name)
            for os_name in runner.PLATFORMS
        },
        "inherited": [python, "-c", runner.INHERITED_CALL, str(ROOT), str(tmp_path / "route.json")],
        "probe": [python, "-c", runner.PROVENANCE_PROBE, str(tmp_path), "[]"],
        "static": [python, *runner.HOST_STATIC_COMMAND[1:]],
    }


@pytest.mark.parametrize(
    "name",
    [
        "host",
        "companion-Linux",
        "companion-Darwin",
        "companion-Windows",
        "inherited",
        "probe",
        "static",
    ],
)
def test_round1_run_records_exactly_what_it_hands_to_popen(monkeypatch, tmp_path, name):
    """The real `_run`, given each real command the collector launches: what it records is what
    `Popen` received."""
    command = launched_commands(tmp_path)[name]
    seen = []

    class Recorded:
        pid, returncode = 4242, None

        def __init__(self, args, **_kwargs):
            seen.append(list(args))
            self.args = args

        def kill(self):
            self.returncode = -9

        def wait(self, timeout=None):
            self.returncode = 0 if self.returncode is None else self.returncode
            return self.returncode

    class Tree:
        POPEN_OPTIONS: ClassVar[dict] = {}

        def __init__(self, child):
            pass

        def stop(self):
            return True

    monkeypatch.setattr(runner.subprocess, "Popen", Recorded)
    monkeypatch.setattr(runner, "ProcessTree", Tree)
    monkeypatch.setattr(runner, "_await_exit", lambda child, timeout: None)
    launched = []
    runner._run(command, cwd=ROOT, env={}, timeout=5, launched=launched)
    assert launched == seen == [command]


def test_round1_a_launched_command_with_an_added_deselection_is_rejected(evidence):
    manifests, reference = evidence
    row = linux(manifests)
    command = [*row["host_controls"]["command"]]
    command.insert(-2, "--deselect=" + _MOVED_CONTROL)
    row["host_controls"].update(command=command, command_sha256=runner.digest_value(command))
    errors = runner.receipt_errors(manifests, reference)
    assert "Linux: HOST command is not the expected command" in errors, errors


# Each git call in these tests takes well under a second, a few seconds at most on a slow hosted
# runner. 120 seconds is far above that, so only a hung call reaches it.
GIT_TIMEOUT_SECONDS = 120


def setup_environment(tmp_path):
    """For setting a test repository up: no user or system configuration of this machine's."""
    empty = tmp_path / "setup-gitconfig"
    empty.write_bytes(b"")
    return {**runner.os.environ, "GIT_CONFIG_GLOBAL": str(empty), "GIT_CONFIG_NOSYSTEM": "1"}


def git_repository(path):
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    path.mkdir()
    env = setup_environment(path.parent)
    for args in (["init", "-q"], ["add", "."], ["commit", "-q", "-m", "x"]):
        if args[0] == "add":
            (path / "file.txt").write_text("x\n")
        subprocess.run(
            [*git, "-C", str(path), *args],
            check=True,
            capture_output=True,
            env=env,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    return path


def marker_command(marker, passthrough=False):
    """A shell command that writes `marker`, portable to the `sh` Git for Windows runs commands
    under: this interpreter, quoted, with forward slashes. With `passthrough` it also copies its
    standard input to its output, as a clean filter must."""
    code = f"import pathlib,sys;pathlib.Path('{marker.as_posix()}').write_text('ran')"
    if passthrough:
        code += ";sys.stdout.buffer.write(sys.stdin.buffer.read())"
    return f'"{Path(runner.sys.executable).as_posix()}" -c "{code}"'


def set_config(tmp_path, key, value, *, repository=None, file=None):
    """Set a configuration value with git itself, which quotes it for the file."""
    command = (
        ["git", "config", "--file", str(file), key, value]
        if file is not None
        else ["git", "-C", str(repository), "config", key, value]
    )
    subprocess.run(
        command,
        check=True,
        capture_output=True,
        env=setup_environment(tmp_path),
        timeout=GIT_TIMEOUT_SECONDS,
    )


def plain_status(repository, env):
    """`git status` as an unisolated caller would run it: `env` as given, no option added."""
    return subprocess.run(
        ["git", "-C", str(repository), "status", "--porcelain", "--untracked-files=all"],
        capture_output=True,
        text=True,
        env=env,
        check=True,
        timeout=GIT_TIMEOUT_SECONDS,
    ).stdout


def test_round1_n1_the_cleanness_check_runs_no_file_system_monitor(tmp_path):
    """Security N1: a checkout's configuration cannot make the cleanness check run a command.
    Witness first: without the cleanness check's options, the configured monitor does run."""
    repository = git_repository(tmp_path / "repository")
    marker = tmp_path / "fsmonitor-ran"
    set_config(tmp_path, "core.fsmonitor", marker_command(marker), repository=repository)
    env = runner.child_environment(tmp_path)
    plain_status(repository, env)
    assert marker.exists(), "witness: git did not run the configured monitor"
    marker.unlink()
    state = runner.checkout_state(repository, env)
    assert state["clean"] is True and state["commit"]
    assert not marker.exists()


def test_round1_n1_every_cleanness_git_call_disables_the_monitor(collection, tmp_path, monkeypatch):
    companion_root, _ = collection
    children = Children(tmp_path)
    monkeypatch.setattr(runner.subprocess, "run", children)
    runner.collect(ROOT, companion_root)
    git_calls = [args for args, _ in children.calls if args[0] == "git"]
    assert len(git_calls) == 16
    assert all(args[1:3] == ["-c", "core.fsmonitor=false"] for args in git_calls)


@pytest.mark.parametrize("changed", ["config", "info/exclude", "info/attributes"])
def test_round1_n1_a_changed_git_configuration_changes_its_digest(tmp_path, changed):
    repository = git_repository(tmp_path / "repository")
    before = runner.git_config_digest(repository)
    assert runner._is_digest(before) and runner.git_config_digest(repository) == before
    target = repository / ".git" / changed
    target.parent.mkdir(exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write("\n# changed during a collection\n")
    assert runner.git_config_digest(repository) != before


@pytest.mark.parametrize("checkout", ["jevdrill", "companion", "not_recorded"])
def test_round1_n1_a_changed_git_configuration_is_rejected(evidence, checkout):
    manifests, reference = evidence
    row = linux(manifests)
    if checkout == "not_recorded":
        row["jevdrill"]["git_config_sha256"] = None
        row["checkouts_after"]["jevdrill"]["git_config_sha256"] = None
    else:
        row["checkouts_after"][checkout]["git_config_sha256"] = "e" * 64
    errors = runner.receipt_errors(manifests, reference)
    assert "Linux: a checkout's git configuration changed during the collection" in errors, errors


def test_round1_n4a_the_tree_is_stopped_before_the_child_is_reaped(monkeypatch):
    """Security N4a, on the platform this runs on: when the tree is stopped after a normal return,
    the child is still unreaped. On Linux and macOS its process group is signalled while its
    process id still names it; on Windows its job object is terminated before `Popen` takes its
    exit code. A real child; the stop must have happened, so the test cannot pass vacuously."""
    children = []
    real_popen = runner.subprocess.Popen
    stopped = []

    def popen(*args, **kwargs):
        child = real_popen(*args, **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(runner.subprocess, "Popen", popen)
    if runner.os.name == "nt":
        real_kernel32 = runner._kernel32

        class Recording:
            """The real kernel32, recording when the job is terminated."""

            def __init__(self):
                self.real = real_kernel32()

            def __getattr__(self, name):
                return getattr(self.real, name)

            def TerminateJobObject(self, job, code):
                stopped.append(("job", children[0].returncode))
                return self.real.TerminateJobObject(job, code)

        monkeypatch.setattr(runner, "_kernel32", Recording)
    else:
        real_killpg = runner.os.killpg

        def killpg(pgid, sig):
            stopped.append((sig, children[0].returncode))
            return real_killpg(pgid, sig)

        monkeypatch.setattr(runner.os, "killpg", killpg)
    code, _output, expired = runner._run(
        [runner.sys.executable, "-c", "pass"], cwd=ROOT, env=dict(runner.os.environ), timeout=120
    )
    assert (code, expired) == (0, False)
    assert stopped and all(returncode is None for _how, returncode in stopped), stopped
    assert children[0].returncode == 0


class AsWindows:
    """The `os` module as the verifier sees it, but naming Windows: its Windows paths run."""

    name = "nt"

    def __getattr__(self, attribute):
        return getattr(runner.os, attribute)


def test_n4a_on_windows_the_job_is_terminated_before_the_child_is_reaped(monkeypatch):
    """The Windows stop path, exercised on every platform with stand-ins for the child and
    kernel32: the child's end is awaited without reaping it, the job is terminated, and only then
    is the child reaped. Reversing that order fails here."""
    events = []

    class Child:
        pid, args = 4242, ["child"]

        def __init__(self, *_args, **_kwargs):
            self.returncode = None

        def wait(self, timeout=None):
            events.append("reaped")
            self.returncode = 0
            return 0

        def kill(self):
            events.append("killed")

    children = []

    class Kernel32:
        def CreateJobObjectW(self, *_args):
            return 101

        def OpenProcess(self, *_args):
            return 202

        def AssignProcessToJobObject(self, *_args):
            return 1

        def WaitForSingleObject(self, handle, milliseconds):
            events.append("ended, unreaped")
            return 0  # WAIT_OBJECT_0

        def TerminateJobObject(self, job, code):
            events.append(("job terminated", children[0].returncode))
            return 1

        def CloseHandle(self, handle):
            return 1

    def popen(*args, **kwargs):
        children.append(Child())
        return children[-1]

    monkeypatch.setattr(runner, "os", AsWindows())
    monkeypatch.setattr(runner, "_kernel32", Kernel32)
    monkeypatch.setattr(runner.subprocess, "Popen", popen)
    code, _output, expired = runner._run(["child"], cwd=ROOT, env={}, timeout=120)
    assert (code, expired) == (0, False)
    assert events == ["ended, unreaped", ("job terminated", None), "reaped"], events


def test_round1_n5_a_tree_that_cannot_be_made_still_ends_the_child(monkeypatch):
    """Security N5: the tree is made inside the guarded block, so its failure cannot leave the
    child running or unwaited."""
    events = []

    class LiveChild:
        pid, args, returncode = 4242, ["child"], None

        def __init__(self, *_args, **_kwargs):
            pass

        def kill(self):
            events.append("kill")
            self.returncode = -9

        def wait(self, timeout=None):
            assert self.returncode is not None and timeout is not None
            events.append("wait")
            return self.returncode

    class BrokenTree:
        POPEN_OPTIONS: ClassVar[dict] = {}

        def __init__(self, child):
            raise OSError("no job object")

    monkeypatch.setattr(runner.subprocess, "Popen", LiveChild)
    monkeypatch.setattr(runner, "ProcessTree", BrokenTree)
    with pytest.raises(OSError, match="no job object"):
        runner._run(["child"], cwd=ROOT, env={}, timeout=10)
    assert events == ["kill", "wait"]


# Final-ruling patch (president, #140).


def force_rehash(path):
    """Move a tracked file's modification time, so that `git status` must read it again."""
    stat = path.stat()
    runner.os.utime(path, (stat.st_atime + 100, stat.st_mtime + 100))


@pytest.mark.parametrize(
    "where",
    ["home_gitconfig", "home_default_ignore", "xdg_variable", "global_variable", "system_variable"],
)
def test_final_a_user_or_system_ignore_file_cannot_hide_an_untracked_file(tmp_path, where):
    """(a) The cleanness check sees an untracked file whatever ignore file the user's or the
    system's configuration names; it runs with its own home and no such configuration."""
    repository = git_repository(tmp_path / "repository")
    (repository / "planted.py").write_text("x = 1\n")
    home = tmp_path / "home"
    home.mkdir()
    ignore = tmp_path / "ignore-everything"
    ignore.write_text("*\n")
    config = tmp_path / "config"
    config.write_text(f"[core]\n\texcludesFile = {ignore.as_posix()}\n")
    env = runner.child_environment(home)
    if where == "home_gitconfig":
        (home / ".gitconfig").write_text(config.read_text())
    elif where == "home_default_ignore":
        (home / ".config" / "git").mkdir(parents=True)
        (home / ".config" / "git" / "ignore").write_text("*\n")
    elif where == "xdg_variable":
        (tmp_path / "xdg" / "git").mkdir(parents=True)
        (tmp_path / "xdg" / "git" / "ignore").write_text("*\n")
        env["XDG_CONFIG_HOME"] = str(tmp_path / "xdg")
    elif where == "global_variable":
        env["GIT_CONFIG_GLOBAL"] = str(config)
    else:
        env["GIT_CONFIG_SYSTEM"] = str(config)
    # Witness first: under the same environment a plain `git status` does not see the file.
    assert "planted.py" not in plain_status(repository, env), "witness: the ignore did not apply"
    bare_home = tmp_path / "bare-home"
    bare_home.mkdir()
    assert "planted.py" in plain_status(repository, runner.child_environment(bare_home))
    assert runner.checkout_state(repository, env)["clean"] is False


def test_final_a_a_user_attributes_file_and_clean_filter_do_not_run(tmp_path):
    """(a) A filter named by the user's configuration is not run by `git status`. Witness first:
    a plain `git status` under the same environment does run it."""
    repository = git_repository(tmp_path / "repository")
    marker = tmp_path / "filter-ran"
    attributes = tmp_path / "attributes"
    attributes.write_text("* filter=x\n")
    home = tmp_path / "home"
    home.mkdir()
    set_config(tmp_path, "core.attributesFile", attributes.as_posix(), file=home / ".gitconfig")
    set_config(tmp_path, "filter.x.clean", marker_command(marker, True), file=home / ".gitconfig")
    env = runner.child_environment(home)
    force_rehash(repository / "file.txt")
    plain_status(repository, env)
    assert marker.exists(), "witness: git did not run the user's filter"
    marker.unlink()
    force_rehash(repository / "file.txt")
    state = runner.checkout_state(repository, env)
    assert not marker.exists()
    assert state["clean"] is True


def test_final_a_a_change_to_an_included_configuration_file_is_seen(tmp_path):
    """(a) The digest covers the repository's effective configuration, included files among
    them; and a changed configuration stops the second reading before `git status`."""
    repository = git_repository(tmp_path / "repository")
    included = tmp_path / "included.gitconfig"
    included.write_text("[user]\n\tname = before\n")
    with (repository / ".git" / "config").open("a", encoding="utf-8") as handle:
        handle.write(f"[include]\n\tpath = {included.as_posix()}\n")
    env = runner.child_environment(tmp_path)
    before = runner.checkout_state(repository, env)
    assert runner._is_digest(before["git_config_sha256"]) and before["clean"] is True
    assert (
        runner.checkout_state(repository, env)["git_config_sha256"] == before["git_config_sha256"]
    )
    included.write_text("[user]\n\tname = after\n")
    after = runner.checkout_state(repository, env, expected_config=before["git_config_sha256"])
    assert after["git_config_sha256"] != before["git_config_sha256"]
    assert after["clean"] is False


def test_final_a_a_filter_added_during_the_collection_is_not_run_at_the_second_reading(tmp_path):
    """(a) A filter the collection adds to the repository's own configuration does not run when
    the checkout is read again: the changed configuration is seen first."""
    repository = git_repository(tmp_path / "repository")
    env = runner.child_environment(tmp_path)
    before = runner.checkout_state(repository, env)["git_config_sha256"]
    marker = tmp_path / "filter-ran"
    set_config(tmp_path, "filter.x.clean", marker_command(marker, True), repository=repository)
    (repository / ".git" / "info").mkdir(exist_ok=True)
    (repository / ".git" / "info" / "attributes").write_text("* filter=x\n")
    # Witness first: a plain `git status` runs the filter the configuration now names.
    force_rehash(repository / "file.txt")
    plain_status(repository, env)
    assert marker.exists(), "witness: git did not run the repository's filter"
    marker.unlink()
    force_rehash(repository / "file.txt")
    after = runner.checkout_state(repository, env, expected_config=before)
    assert not marker.exists()
    assert after["clean"] is False and after["git_config_sha256"] != before


def test_final_b_a_path_with_dot_segments_is_not_a_test_id(evidence):
    """(b) `tests/../example.py::test_sample`, added with its digest refreshed, is rejected."""
    manifests, reference = evidence
    row = linux(manifests)
    host_rows(row).append({"node_id": "tests/../example.py::test_sample", "outcome": "passed"})
    refresh(row)
    errors = runner.receipt_errors(manifests, reference)
    assert (
        "Linux: malformed test id in HOST's command: 'tests/../example.py::test_sample'" in errors
    )
    for node in (
        "tests/../example.py::test_sample",
        "tests/./example.py::test_sample",
        "tests//example.py::test_sample",
        "/tests/example.py::test_sample",
        "tests/a/../../example.py::test_sample",
        "tests/...py::test_sample",
    ):
        assert not runner._TEST_ID.fullmatch(node), node
    assert runner._TEST_ID.fullmatch("tests/a.b/c-d/test_e.py::test_f")


@pytest.mark.parametrize(
    ("root", "value"),
    [
        ("/tmp/jevdrill-host-1", "/tmp/jevdrill-host-1/x/y"),
        ("D:\\a\\_temp\\jevdrill-host-1", "D:\\a\\_temp\\jevdrill-host-1\\x\\y"),
    ],
    ids=["posix", "windows"],
)
def test_final_c_normalization_keeps_what_follows_the_temporary_root(root, value):
    os_name = "Windows" if "\\" in root else "Linux"
    command = ["python", "-m", "pytest", f"--basetemp={value}", f"--junitxml={root}/host.xml"]
    assert runner.normalized_command(command, "host", temporary=root, os_name=os_name)[3:] == [
        "--basetemp=<temporary>/x/y",
        "--junitxml=<temporary>/host.xml",
    ]
    # A value outside the root is kept whole, so that it cannot match an expected command.
    assert (
        runner.normalized_command(
            ["python", "--basetemp=/elsewhere/x"], "host", temporary=root, os_name=os_name
        )[1]
        == "--basetemp=/elsewhere/x"
    )


@pytest.mark.parametrize("command_of", ["host_controls", "companion"])
def test_final_c_a_command_with_another_temporary_directory_is_rejected(evidence, command_of):
    """(c) `<temporary>/x/y` in place of the expected directory is rejected, for HOST's command
    and for the companion's."""
    manifests, reference = evidence
    row = linux(manifests)
    receipt_part = row[command_of]
    command = [
        "--basetemp=<temporary>/x/y" if part.startswith("--basetemp=") else part
        for part in receipt_part["command"]
    ]
    receipt_part["command"] = command
    if command_of == "host_controls":
        receipt_part["command_sha256"] = runner.digest_value(command)
        error = "Linux: HOST command is not the expected command"
    else:
        receipt_part["command_sha256"] = runner.companion_command_digest(command)
        error = "Linux: companion command is not the expected command"
    errors = runner.receipt_errors(manifests, reference)
    assert error in errors, errors


def test_final_c_the_expected_temporary_directories_are_the_plans():
    """(c) Written out here, not rebuilt: the directories each command's receipt must name."""
    assert runner.expected_host_command()[-2:] == [
        "--junitxml=<temporary>/host.xml",
        "--basetemp=<temporary>/host-tests",
    ]
    for os_name in runner.PLATFORMS:
        assert runner.expected_companion_command(os_name)[-2:] == [
            "--junitxml=<temporary>/companion.xml",
            "--basetemp=<temporary>/companion-tests",
        ]


@pytest.mark.parametrize(
    ("os_name", "root", "accepted"),
    [
        ("Linux", "/tmp/jevdrill-host-1", False),
        ("Darwin", "/private/var/folders/jevdrill-host-1", False),
        ("Windows", "D:\\a\\_temp\\jevdrill-host-1", True),
    ],
    ids=["Linux", "Darwin", "Windows"],
)
def test_final_c_a_backslash_is_a_separator_only_on_a_windows_receipt(
    evidence, os_name, root, accepted
):
    """(c), the vendor's finding: on a POSIX receipt `<root>\\host-tests` is a sibling of the
    temporary root, not under it, and is rejected; on a Windows receipt it is the root's
    `host-tests` and is accepted. Which separators count is the receipt's platform's, whatever
    platform this test (or the reducer) runs on."""
    manifests, reference = evidence
    launched = [
        f"--junitxml={root}\\host.xml"
        if part.startswith("--junitxml=")
        else f"--basetemp={root}\\host-tests"
        if part.startswith("--basetemp=")
        else part
        for part in runner.host_test_command("/opt/python", "<unused>")
    ]
    command = runner.normalized_command(launched, "host", temporary=root, os_name=os_name)
    row = linux(manifests)
    row["host_controls"].update(command=command, command_sha256=runner.digest_value(command))
    errors = runner.receipt_errors(manifests, reference)
    assert ("Linux: HOST command is not the expected command" in errors) is not accepted, errors
    assert (command == runner.expected_host_command()) is accepted


def test_final_c_the_collector_normalizes_with_its_own_platform(collection, tmp_path, monkeypatch):
    """(c): the collector names its own platform when it normalizes. On a Linux collector a
    launched `<root>\\host-tests` is a sibling of the root: it is recorded whole, and rejected."""
    companion_root, _ = collection
    monkeypatch.setattr(runner.subprocess, "run", Children(tmp_path))
    monkeypatch.setattr(runner.platform, "system", lambda: "Linux")
    built = {"host": runner.host_test_command, "companion": runner.companion_command}

    def sibling(command, name):
        """The command with `--basetemp=<root>\\<name>`: a backslash after the root."""
        return [
            f"--basetemp={Path(part.split('=', 1)[1]).parent}\\{name}"
            if part.startswith("--basetemp=")
            else part
            for part in command
        ]

    monkeypatch.setattr(
        runner, "host_test_command", lambda *a: sibling(built["host"](*a), "host-tests")
    )
    monkeypatch.setattr(
        runner,
        "companion_command",
        lambda *a: sibling(built["companion"](*a), "companion-tests"),
    )
    receipt_value = runner.collect(ROOT, companion_root)
    for part_of, name in (("host_controls", "host-tests"), ("companion", "companion-tests")):
        (basetemp,) = [p for p in receipt_value[part_of]["command"] if p.startswith("--basetemp=")]
        assert basetemp.endswith("\\" + name) and not basetemp.startswith("--basetemp=<temporary>")
    assert "HOST command is not the expected command" in runner._host_command_errors(
        receipt_value["host_controls"]
    )
    companion_errors = runner._companion_errors(receipt_value["companion"], "Linux", HANDOFF, {})
    assert "companion command is not the expected command" in companion_errors


# What would skip a test. Held as strings, and matched only as names and attributes in the
# code, so this list does not count as a skip itself.
SKIP_NAMES = frozenset(
    {"skip", "skipif", "importorskip", "xfail", "skipTest", "SkipTest", "skipIf", "skipUnless"}
)


def skips_in(path):
    """Every use of a skip in a Python file's code: a name or an attribute in SKIP_NAMES."""
    import ast

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    label = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.name
    found = []
    for node in ast.walk(tree):
        name = (
            node.attr
            if isinstance(node, ast.Attribute)
            else node.id
            if isinstance(node, ast.Name)
            else None
        )
        if name in SKIP_NAMES:
            found.append(f"{label}:{node.lineno}: {name}")
        if isinstance(node, ast.ImportFrom | ast.Import):
            found.extend(
                f"{label}:{node.lineno}: import {alias.name}"
                for alias in node.names
                if alias.name.rsplit(".", 1)[-1] in SKIP_NAMES
            )
    return found


def host_command_files():
    """The files HOST's command selects, and every conftest.py that applies to them."""
    files = {ROOT / path for path in runner.HOST_TEST_PATHS}
    for path in runner.HOST_TEST_PATHS:
        for parent in (ROOT / path).parents:
            if parent == ROOT:
                break
            if (parent / "conftest.py").is_file():
                files.add(parent / "conftest.py")
    return sorted(files)


def test_no_file_hosts_command_selects_can_skip_a_test():
    """HOST's command must pass whole, with no skipped case, on every platform (run 45279806415
    was rejected for one). So no file it selects, nor any conftest.py over them, holds a skip of
    any kind: `pytest.skip`, `skipif`, `mark.skip`, `importorskip`, `xfail`, or unittest's."""
    files = host_command_files()
    assert {ROOT / path for path in runner.HOST_TEST_PATHS} <= set(files)
    assert ROOT / "tests/conformance/conftest.py" in files and ROOT / "tests/conftest.py" in files
    found = [use for path in files for use in skips_in(path)]
    assert found == [], found


def test_the_skip_guard_finds_every_kind_of_skip(tmp_path):
    """The guard is not vacuous: each kind of skip, written into a test file, is found."""
    for line in (
        "pytest.skip('x')",
        "@pytest.mark.skipif(True, reason='x')\ndef test_x(): pass",
        "@pytest.mark.skip\ndef test_x(): pass",
        "pytest.importorskip('json')",
        "@pytest.mark.xfail\ndef test_x(): pass",
        "pytest.xfail('x')",
        "import unittest\n@unittest.skipIf(True, 'x')\ndef test_x(): pass",
        "raise unittest.SkipTest('x')",
        "from pytest import skip",
    ):
        path = tmp_path / "test_probe.py"
        path.write_text("import pytest\n" + line + "\n", encoding="utf-8")
        assert skips_in(path), line
    # A file with none is clean, and a string that names a skip is not one.
    path = tmp_path / "test_clean.py"
    path.write_text("NAMES = ['skip', 'xfail']\ndef test_x():\n    assert True\n", encoding="utf-8")
    assert skips_in(path) == []
