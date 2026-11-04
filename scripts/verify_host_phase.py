"""Collect native HOST and companion receipts; reduce entered production controls."""

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_route_spec = importlib.util.spec_from_file_location(
    "host_route_regressions", ROOT / "scripts/verify_route_phase.py"
)
route = importlib.util.module_from_spec(_route_spec)
_route_spec.loader.exec_module(route)
REQUIREMENTS = {f"EC-HOST-{number}" for number in range(1, 5)} | {"IF-0-HOST-1", "IF-0-VC-2"}
CONTROLS = {
    "EC-HOST-1": [
        "tests/conformance/test_launch_paths.py::test_real_main_delegated_lane_constructors",
        "tests/conformance/test_launch_paths.py::test_entered_permission_expansion_denials",
    ],
    "EC-HOST-2": [
        "tests/conformance/test_transport_queue.py::test_entered_ack_loss_and_cross_producer_deletion",
        "tests/conformance/test_notices.py::test_every_report_connection_queries_notices",
        "tests/storage/test_host_notices.py::test_notice_scope_reads_and_cross_producer_deletion",
    ],
    "EC-HOST-3": [
        "tests/conformance/test_launch_paths.py::test_independent_checks_reject_entered_routed_artifacts",
        "tests/evaluation/test_host_acceptance.py::test_frozen_groups_are_disjoint_and_holdouts_unopened",
    ],
    "EC-HOST-4": [
        "tests/conformance/test_discovery_handoff.py::test_installed_discovery_harness_planning_two_independent_tasks",
        "tests/conformance/test_discovery_handoff.py::test_entered_reference_deletion_revision_and_policy_controls",
    ],
    "IF-0-HOST-1": [
        "tests/conformance/test_discovery_handoff.py::test_installed_discovery_harness_planning_two_independent_tasks"
    ],
    "IF-0-VC-2": ["tests/verification/test_host_phase.py::test_reducer_rejects_invalid_receipts"],
}
TEST_PATHS = tuple(sorted({node.split("::")[0] for nodes in CONTROLS.values() for node in nodes}))
COMPANION_TESTS = tuple(
    f"test_{name}.py"
    for name in (
        "jevdrill_adapter",
        "jevdrill_queue",
        "jevdrill_discovery",
        "phase_loop_launcher",
        "phase_loop_work_unit_observability",
        "jevdrill_input",
        "jevdrill_usage",
        "jevdrill_diagnostics",
    )
)
COMPANION_CONTROLS = (
    "test_jevdrill_discovery.py::test_installed_discovery_decomposition_two_task_launch[alpha]",
    "test_jevdrill_discovery.py::test_installed_discovery_decomposition_two_task_launch[beta]",
    "test_jevdrill_discovery.py::test_entered_discovery_requires_harness_decomposition",
    "test_jevdrill_discovery.py::test_objective_tombstone_survives_restart_and_preserves_reports",
    "test_jevdrill_adapter.py::test_guidance_is_verified_injected_once_and_deactivated",
    "test_jevdrill_discovery.py::test_native_unsupported_observer_records_unknown_capture",
    "test_jevdrill_queue.py::test_objective_guard_reuses_anchored_transaction_and_bounds_admission",
    "test_jevdrill_queue.py::test_objective_guard_bounds_other_thread_contention",
)


def digest_value(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def source_digest(root):
    paths = {
        p
        for pattern in (
            "src/**/*.py",
            "src/**/*.json",
            "tests/**/*.py",
            "tests/fixtures/jevdrill/*.json",
            "pyproject.toml",
            "uv.lock",
        )
        for p in root.glob(pattern)
        if p.is_file() and "__pycache__" not in p.parts
    }
    return digest_value(
        {
            p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths, key=lambda p: p.relative_to(root).as_posix())
        }
    )


def input_digest(root):
    extra = {}
    for pattern in (
        "research/evaluation/host/*.py",
        "research/evaluation/host/protocol.json",
        "tests/conformance/fixtures/*.json",
        "evidence/HOST/adapter-handoff.json",
        "evidence/HOST/coverage.json",
        "evidence/HOST/spec-delta.json",
        ".github/workflows/host.yml",
    ):
        extra.update(
            {
                p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in root.glob(pattern)
                if p.is_file()
            }
        )
    return digest_value({"route_source": route.input_digest(root), "host_sources": extra})


def assertions_from(path, root):
    rows = []
    for case in ET.parse(path).getroot().iter("testcase"):
        parts = case.get("classname", "").split(".")
        while parts and not (root / ("/".join(parts) + ".py")).is_file():
            parts.pop()
        rows.append(
            {
                "node_id": "/".join(parts) + ".py::" + case.get("name", ""),
                "outcome": "skipped"
                if case.find("skipped") is not None
                else "failed"
                if case.find("failure") is not None or case.find("error") is not None
                else "passed",
            }
        )
    return sorted(rows, key=lambda row: row["node_id"])


def companion_command(python, temporary, os_name="Linux"):
    return [
        python,
        "-m",
        "pytest",
        "-q",
        *[
            "phase-loop-runtime/tests/" + p
            for p in COMPANION_TESTS
            if p != "test_jevdrill_discovery.py"
            and (
                os_name == "Linux"
                or p
                not in (
                    "test_jevdrill_input.py",
                    "test_jevdrill_usage.py",
                    "test_jevdrill_diagnostics.py",
                )
            )
        ],
        f"--junitxml={temporary / 'companion.xml'}",
        f"--basetemp={temporary / 'companion-tests'}",
    ]


def normalized_companion_command(command):
    return [
        "<python>"
        if index == 0
        else "--junitxml=<temporary>/companion.xml"
        if part.startswith("--junitxml=")
        else "--basetemp=<temporary>/companion-tests"
        if part.startswith("--basetemp=")
        else part
        for index, part in enumerate(command)
    ]


def witness_errors(witness):
    errors = []
    if not isinstance(witness, dict) or not isinstance(witness.get("records"), list):
        return ["missing production witnesses"]
    assertions = witness.get("assertions", [])
    if not assertions or any(row.get("outcome") != "passed" for row in assertions):
        errors.append("failed or skipped entered assertions")
    if (
        witness.get("holdouts_opened") is not False
        or witness.get("promotion_eligible") is not False
    ):
        errors.append("holdout or promotion authority violation")
    if witness.get("performance_claims") != "insufficient_evidence":
        errors.append("ineligible performance claim")
    flows = [r for r in witness["records"] if r.get("flow") == "discovery"]
    if {r.get("objective") for r in flows} != {"alpha", "beta"}:
        errors.append("missing objective-dependent discovery")
    for flow in flows:
        if not {"main", "open_application", "discover", "next_question", "route"} <= set(
            flow.get("entered", [])
        ):
            errors.append("missing installed entry")
        events = flow.get("construction_events", [])
        routed = [i for i, event in enumerate(events) if event.endswith("route-v2")]
        if (
            "planning.executor" not in events
            or not routed
            or events.index("planning.executor") >= min(routed)
        ):
            errors.append("missing entered harness decomposition")
        runs = flow.get("runs", [])
        if (
            len(runs) < 2
            or len({r.get("task_id") for r in runs}) != len(runs)
            or len({r.get("model") for r in runs}) < 2
            or len({r.get("effort") for r in runs}) < 2
        ):
            errors.append("missing independent two-task configuration")
        for run in runs:
            ref, execution = run.get("discovery_ref", {}), run.get("execution_run", {})
            if (
                not ref.get("trace_digest")
                or execution.get("task_id") != run.get("task_id")
                or not (
                    execution.get("selected_plan_id") == execution.get("applied_plan_id")
                    and execution.get("execution_run_id")
                    and run.get("decision_id")
                )
            ):
                errors.append("missing task decision run discovery linkage")
    faults = {r.get("fault") for r in witness["records"] if r.get("flow") == "discovery-control"}
    if faults != {"forged", "deleted", "stale_catalog", "relaxed", "decline"}:
        errors.append("missing entered linked controls")
    for row in witness["records"]:
        if row.get("flow") == "discovery-control" and (
            not row.get("discovery_id")
            or not row.get("task_id")
            or row.get("rejected_before_execution") is not True
        ):
            errors.append("missing linked control rejection evidence")
    for family in ("implementation", "review", "documentation"):
        rows = [
            r for r in witness["records"] if r.get("task_family") == family and r.get("damaged")
        ]
        if not rows or any(all(r.get("objective_checks", {}).values()) for r in rows):
            errors.append("missing independent artifact rejection")
        positive = [
            r
            for r in witness["records"]
            if r.get("task_family") == family and not r.get("damaged") and not r.get("control")
        ]
        if not positive or any(
            not r.get("objective_checks") or not all(r["objective_checks"].values())
            for r in positive
        ):
            errors.append("missing independent positive artifact checks")
    return errors


def reduce_manifests(
    manifests,
    expected,
    companion_digest,
    root=ROOT,
    required_platforms=None,
    *,
    extra_test_paths=(),
):
    errors = []
    seen = set()
    for manifest in manifests:
        if not isinstance(manifest, dict):
            errors.append("malformed HOST receipt")
            continue
        identity = (manifest.get("os"), manifest.get("python_minor"))
        if identity in seen or identity not in route.MATRIX:
            errors.append("duplicate or unexpected native input")
        seen.add(identity)
        if (
            manifest.get("phase") != "HOST"
            or manifest.get("schema_version") != 2
            or manifest.get("input_digest") != expected
            or manifest.get("source_stable") is not True
        ):
            errors.append("stale or unsupported HOST source")
        inherited = manifest.get("route_regressions", {})
        if not isinstance(inherited, dict):
            errors.append("missing inherited regressions")
        else:
            errors.extend(
                route.reduce_manifests(
                    [inherited],
                    route.input_digest(root),
                    root,
                    required_platforms={identity},
                    extra_test_paths=(*TEST_PATHS, *extra_test_paths),
                )
            )
            actual = {
                row["node_id"]
                for row in inherited.get("assertions", [])
                if row.get("outcome") == "passed"
            }
            for nodes in CONTROLS.values():
                for node in nodes:
                    if not any(value == node or value.startswith(node + "[") for value in actual):
                        errors.append("missing HOST control: " + node)
        companion = manifest.get("companion", {})
        command = companion.get("command", [])
        if (
            companion.get("input_digest") != companion_digest
            or companion.get("source_stable") is not True
            or companion.get("exit_code") != 0
            or not companion.get("output_sha256")
            or normalized_companion_command(command)
            != normalized_companion_command(
                companion_command("<python>", Path("<temporary>"), identity[0])
            )
            or companion.get("command_sha256") != digest_value(command)
        ):
            errors.append("missing or mismatched companion receipt")
        assertions = companion.get("assertions", [])
        if not assertions or any(row.get("outcome") != "passed" for row in assertions):
            errors.append("failed or skipped companion assertions")
        if companion.get("assertions_sha256") != digest_value(assertions):
            errors.append("companion assertion digest mismatch")
        actual = {row.get("node_id") for row in assertions}
        discovery_receipt = companion.get("integrated_discovery", {})
        integrated = discovery_receipt.get("assertions", [])
        discovery_command = discovery_receipt.get("command", [])
        normalized_discovery = ["<python>", *discovery_command[1:6]] if discovery_command else []
        if (
            not integrated
            or any(row.get("outcome") != "passed" for row in integrated)
            or discovery_receipt.get("assertions_sha256") != digest_value(integrated)
            or discovery_receipt.get("input_digest") != companion_digest
            or discovery_receipt.get("source_stable") is not True
            or discovery_receipt.get("exit_code") != 0
            or discovery_receipt.get("origin") != "installed_companion_conformance_subprocess"
            or not discovery_receipt.get("output_sha256")
            or discovery_receipt.get("command_sha256") != digest_value(discovery_command)
            or normalized_discovery
            != [
                "<python>",
                "-m",
                "pytest",
                "-q",
                "--override-ini=addopts=",
                "tests/test_jevdrill_discovery.py",
            ]
            or len(discovery_command) != 8
            or not discovery_command[6].startswith("--junitxml=")
            or not discovery_command[7].startswith("--basetemp=")
            or discovery_receipt != (manifest.get("witnesses") or {}).get("companion_discovery")
        ):
            errors.append("missing integrated companion discovery assertions")
        actual.update(row.get("node_id") for row in integrated)
        for node in COMPANION_CONTROLS:
            if "tests/" + node not in actual:
                errors.append("missing companion control: " + node)
        expected_provenance = json.loads((root / "evidence/HOST/adapter-handoff.json").read_text())
        provenance = companion.get("installed_provenance", {})
        if (
            provenance.get("modules") != expected_provenance["companion_modules"]
            or provenance.get("version") != expected_provenance["companion_runtime_version"]
            or provenance.get("os") != identity[0]
            or provenance.get("source_root_matches") is not True
        ):
            errors.append("mismatched installed companion provenance")
        if manifest.get("witness_sha256") != digest_value(manifest.get("witnesses")):
            errors.append("witness digest mismatch")
        errors.extend(witness_errors(manifest.get("witnesses")))
        if (
            manifest.get("fixture_digests")
            != json.loads((root / "evidence/HOST/adapter-handoff.json").read_text())["schemas"]
        ):
            errors.append("mismatched packaged companion schemas")
        static = manifest.get("host_static", {})
        if static.get("exit_code") != 0 or static.get("command") != [
            "<python>",
            "-m",
            "ruff",
            "check",
            "tests/conformance",
            "research/evaluation/host",
        ]:
            errors.append("failed or wrong host static check")
        duration = manifest.get("duration_seconds")
        if type(duration) not in (int, float) or not 0 < duration <= 600:
            errors.append("excessive or invalid proof cost")
    required = route.MATRIX if required_platforms is None else required_platforms
    errors.extend(f"missing {os_name}/Python {minor}" for os_name, minor in sorted(required - seen))
    try:
        coverage = json.loads((root / "evidence/HOST/coverage.json").read_text())
        delta = json.loads((root / "evidence/HOST/spec-delta.json").read_text())
        if set(coverage["coverage"]) != REQUIREMENTS or coverage["required_controls"] != CONTROLS:
            errors.append("missing four-criterion coverage")
        if (
            delta["schema"] != "spec_delta_closeout.v1"
            or delta["decision"] != "roadmap_amendment"
            or delta["redaction_posture"] != "metadata_only"
            or delta["downstream_handling"] != "replan_LEARN"
        ):
            errors.append("malformed HOST spec-delta")
    except (OSError, ValueError, KeyError, TypeError):
        errors.append("malformed HOST control artifacts")
    return sorted(set(errors))


def collect(root, companion_root):
    started = time.monotonic()
    before = input_digest(root)
    runtime = companion_root / "phase-loop-runtime"
    companion_before = source_digest(runtime)
    python = Path(
        os.environ.get(
            "JEVDRILL_AGENT_HARNESS_PYTHON",
            str(runtime / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")),
        )
    )
    if not python.is_file():
        raise ValueError("Installed companion interpreter is required")
    handoff = json.loads((root / "evidence/HOST/adapter-handoff.json").read_text())
    fixture_dir = runtime / "tests/fixtures/jevdrill"
    for name, digest in {**handoff["schemas"], **handoff["fixtures"]}.items():
        if hashlib.sha256((fixture_dir / name).read_bytes()).hexdigest() != digest:
            raise ValueError("Companion fixture/schema differs from handoff")
    probe = subprocess.run(
        [
            str(python),
            "-c",
            (
                "import hashlib,importlib,importlib.metadata,json,platform,sys; from pathlib import Path; "
                "root=Path(sys.argv[1]).resolve(); names=json.loads(sys.argv[2]); "
                "paths={name:Path(importlib.import_module('phase_loop_runtime.'+name).__file__).resolve() for name in names}; "
                "print(json.dumps({'modules':{name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in paths.items()},"
                "'version':importlib.metadata.version('phase-loop-runtime'),'os':platform.system(),"
                "'source_root_matches':all(path.is_relative_to(root/'src') for path in paths.values())}))"
            ),
            str(runtime),
            json.dumps(list(handoff["companion_modules"])),
        ],
        cwd=companion_root,
        capture_output=True,
        check=True,
        timeout=30,
    )
    provenance = json.loads(probe.stdout)
    os.environ["JEVDRILL_AGENT_HARNESS_ROOT"] = str(companion_root)
    os.environ["JEVDRILL_TEST_CLI"] = str(
        Path(sys.executable).parent / ("jevdrill.exe" if os.name == "nt" else "jevdrill")
    )
    os.environ["JEVDRILL_TEST_PYTHON"] = sys.executable
    os.environ["PHASE_LOOP_TDD_EXPECT_SCHED"] = "1"
    with tempfile.TemporaryDirectory(prefix="jevdrill-host-verify-") as temporary:
        tmp = Path(temporary)
        witness_path = tmp / "witness.json"
        os.environ["JEVDRILL_EVALUATION_OUTPUT"] = str(witness_path)
        inherited = route.collect(root, extra_test_paths=TEST_PATHS)
        history = root / "evidence/HOST/history"
        history.mkdir(parents=True, exist_ok=True)
        (history / f"latest-inherited-{platform.system()}.json").write_text(
            json.dumps(inherited, indent=2) + "\n"
        )
        command = companion_command(str(python), tmp, platform.system())
        try:
            result = subprocess.run(
                command,
                cwd=companion_root,
                capture_output=True,
                timeout=max(0.001, 600 - (time.monotonic() - started)),
                check=False,
            )
        except subprocess.TimeoutExpired:
            result = subprocess.CompletedProcess(command, 125, b"TimeoutExpired", b"")
        assertions = (
            assertions_from(tmp / "companion.xml", runtime)
            if (tmp / "companion.xml").exists()
            else []
        )
        companion = {
            "installed_provenance": provenance,
            "command": command,
            "command_sha256": digest_value(command),
            "input_digest": companion_before,
            "source_stable": source_digest(runtime) == companion_before,
            "output_sha256": hashlib.sha256(result.stdout + result.stderr).hexdigest(),
            "exit_code": result.returncode,
            "assertions": assertions,
            "assertions_sha256": digest_value(assertions),
        }
        static_command = [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "tests/conformance",
            "research/evaluation/host",
        ]
        static = subprocess.run(static_command, cwd=root, capture_output=True, check=False)
        witness = json.loads(witness_path.read_text()) if witness_path.exists() else None
        companion["integrated_discovery"] = (witness or {}).get("companion_discovery", {})
    return {
        "schema_version": 2,
        "phase": "HOST",
        "os": platform.system(),
        "python_minor": f"{sys.version_info.major}.{sys.version_info.minor}",
        "input_digest": before,
        "source_stable": input_digest(root) == before,
        "route_regressions": inherited,
        "companion": companion,
        "witnesses": witness,
        "witness_sha256": digest_value(witness),
        "fixture_digests": handoff["schemas"],
        "host_static": {
            "command": ["<python>", *static_command[1:]],
            "exit_code": static.returncode,
            "output_sha256": hashlib.sha256(static.stdout + static.stderr).hexdigest(),
        },
        "duration_seconds": round(time.monotonic() - started, 3),
        "proof_cost_target_exceeded": time.monotonic() - started > 300,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agent-harness", type=Path, default=os.environ.get("JEVDRILL_AGENT_HARNESS_ROOT")
    )
    parser.add_argument("--local-only", action="store_true")
    parser.add_argument("--reduce-only", action="store_true")
    args = parser.parse_args()
    if args.agent_harness is None:
        parser.error("Explicit --agent-harness PATH or JEVDRILL_AGENT_HARNESS_ROOT is required")
    output = ROOT / "evidence/HOST"
    platforms = output / "platforms"
    platforms.mkdir(parents=True, exist_ok=True)
    current = None if args.reduce_only else collect(ROOT, args.agent_harness.resolve())
    if current is not None:
        (platforms / f"{platform.system()}-3.13.json").write_text(
            json.dumps(current, indent=2) + "\n"
        )
        (output / "evaluation.json").write_text(json.dumps(current["witnesses"], indent=2) + "\n")
    manifests = [json.loads(p.read_text()) for p in sorted(platforms.glob("*.json"))]
    expected = input_digest(ROOT)
    companion_digest = source_digest(args.agent_harness.resolve() / "phase-loop-runtime")
    errors = reduce_manifests(manifests, expected, companion_digest)
    report = {
        "schema_version": 2,
        "phase": "HOST",
        "status": "passed" if not errors else "blocked",
        "errors": errors,
        "input_digest": expected,
        "companion_digest": companion_digest,
        "platforms": [m["os"] for m in manifests],
        "produced_if_gates": ["IF-0-HOST-1"] if not errors else [],
    }
    (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    if args.local_only and current is not None:
        errors = reduce_manifests(
            [current], expected, companion_digest, required_platforms={(platform.system(), "3.13")}
        )
        print(json.dumps({"local_errors": errors}))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
