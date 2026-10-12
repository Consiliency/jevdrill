"""Collect current native LEARN and inherited controls, then reduce strict receipts."""

import argparse
import hashlib
import importlib
import importlib.util
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "learn_inherited_host", ROOT / "scripts/verify_host_phase.py"
)
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)
CONTROLS = {
    "EC-LEARN-1": [
        "tests/application/test_learning.py::test_analysis_batch_interval_objective_history_and_immutable_replay",
        "tests/analysis/test_observations.py::test_missing_failed_canceled_corrected_and_unknown_observations",
        "tests/analysis/test_observations.py::test_metric_revisions_units_methods_remain_separate",
        "tests/analysis/test_observations.py::test_source_digest_recheck_prevents_deleted_analysis_commit",
        "tests/analysis/test_observations.py::test_terminal_applied_ids_corrections_and_unrelated_runs_remain_authoritative",
    ],
    "EC-LEARN-2": [
        "tests/maintenance/test_maintenance.py::test_process_owned_nonoverlap_and_exit_release",
        "tests/maintenance/test_maintenance.py::test_bounded_resumable_cursor_pause_cancel_and_interactive_contention",
        "tests/maintenance/test_maintenance.py::test_pause_and_interactive_start_are_rechecked_between_production_items",
        "tests/cli/test_learning.py::test_native_scheduler_argv_enters_installed_maintenance_and_host_contention",
    ],
    "EC-LEARN-3": [
        "tests/retention/test_retention.py::test_active_grace_encrypted_archive_one_year_expiry_and_measurement_persistence",
        "tests/retention/test_retention.py::test_key_failures_keep_pending_active_content_and_notice[missing]",
        "tests/retention/test_retention.py::test_key_failures_keep_pending_active_content_and_notice[locked]",
        "tests/retention/test_retention.py::test_key_failures_keep_pending_active_content_and_notice[failed]",
        "tests/retention/test_retention.py::test_clock_rollback_and_corruption_enter_production_retention",
        "tests/retention/test_retention.py::test_archive_crash_retry_keeps_source_until_durable_verification",
        "tests/retention/test_retention.py::test_archive_tamper_cannot_restore",
        "tests/maintenance/test_recovery.py::test_portable_export_backup_import_preserves_lineage_and_deletion_precedes_sources",
        "tests/maintenance/test_recovery.py::test_native_archive_restore_and_portable_archive_export",
        "tests/maintenance/test_recovery.py::test_malformed_or_conflicting_import_rejects_transactionally[tamper]",
        "tests/maintenance/test_recovery.py::test_malformed_or_conflicting_import_rejects_transactionally[digest]",
        "tests/maintenance/test_recovery.py::test_malformed_or_conflicting_import_rejects_transactionally[decision_conflict]",
    ],
    "EC-LEARN-4": [
        "tests/privacy/test_learning.py::test_default_workspace_scope_and_explicit_redacted_user_wide_consent",
        "tests/application/test_learning.py::test_settings_optout_exclusions_and_disabled_model_analysis_enter_application",
        "tests/cli/test_learning.py::test_installed_cli_analyze_notices_recovery_and_reject_unknown_claims",
        "tests/storage/test_learning.py::test_deletion_preserves_unrelated_project_evidence_and_objective_history",
    ],
    "EC-LEARN-5": [
        "tests/application/test_learning.py::test_installed_discovery_host_tasks_reports_analysis_and_entered_denials",
        "tests/storage/test_learning_lineage.py::test_forged_learning_link_enters_storage_and_is_rejected[discovery_ref]",
        "tests/storage/test_learning_lineage.py::test_cross_producer_objective_tombstone_suppresses_analysis_but_keeps_task_reports",
        "tests/analysis/test_observations.py::test_substitution_preference_and_evaluation_are_distinct",
        "tests/analysis/test_observations.py::test_no_guidance_discoveries_keep_authoritative_boundaries_despite_forged_family_labels",
    ],
}
EXTRA_COMMAND = [
    "-m",
    "pytest",
    "-q",
    "tests/test_windows_locking.py",
    "tests/test_launcher_liveness.py",
]
LEARN_STATIC = ["-m", "ruff", "check", "tests/analysis", "tests/maintenance", "tests/retention"]


def extra_arguments(os_name):
    return [
        *EXTRA_COMMAND,
        *(
            ["tests/test_windows_processes.py", "tests/test_windows_storage.py"]
            if os_name == "Windows"
            else []
        ),
    ]


def input_digest(root):
    return host.digest_value(
        {
            "inherited": host.input_digest(root),
            "learn": {
                name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                for name in (
                    "evidence/LEARN/coverage.json",
                    "evidence/LEARN/spec-delta.json",
                    ".github/workflows/learn.yml",
                    "plans/phase-plan-v1-LEARN.md",
                )
            },
        }
    )


def witness_errors(witness):
    if (
        not isinstance(witness, dict)
        or witness.get("origin") != "installed_discovery_host_tasks_reports_analysis"
    ):
        return ["missing installed LEARN lineage observation"]
    errors = []
    groups = witness.get("observed_groups")
    if not isinstance(groups, list) or len(groups) != 2:
        return ["missing independent task observations"]
    try:
        from jevdrill.contracts import parse_contract

        for group in groups:
            parse_contract("EvidenceGroup", group)
        sources = [g["sources"][0] for g in groups]
        if any(
            g["evidence_scope"] != "observed_task_group" or g["completed_count"] != 1
            for g in groups
        ):
            errors.append("invalid applied task observation")
        runs = witness["run_observations"]
        if len(runs) != len(groups):
            errors.append("missing authoritative run observations")
        for group in groups:
            source = group["sources"][0]
            records = [r for r in runs if r["source"] == source]
            if len(records) != 1:
                errors.append("missing or unrelated authoritative run")
                continue
            record = records[0]
            argv = record["inspection_command"]
            if (
                argv[1:4] != ["-m", "jevdrill.cli", "--storage"]
                or argv[5:8] != ["inspect", "--decision-id", source["routing_decision_id"]]
                or record["inspection_exit_code"] != 0
            ):
                errors.append("wrong authoritative inspection command")
            reported = record["report_command"]
            if (
                reported[1:3]
                != [
                    "-c",
                    "import json,sys;from pathlib import Path;from jevdrill.storage import SQLiteStorage;print(json.dumps(SQLiteStorage(Path(sys.argv[1])).project_run(json.loads(sys.argv[2]),sys.argv[3])))",
                ]
                or reported[3] != argv[4]
                or reported[5] != source["execution_run_id"]
                or reported[4] != argv[9]
                or record["report_exit_code"] != 0
            ):
                errors.append("wrong authoritative report command")
            lifecycle = record["lifecycle"]
            from jevdrill.contracts import parse_contract

            for event in lifecycle:
                if event["payload"]["kind"] != "lifecycle":
                    errors.append("wrong report payload kind")
            if (
                not lifecycle
                or len({e["event_id"] for e in lifecycle}) != len(lifecycle)
                or any(
                    e[k] != source[k]
                    for e in lifecycle
                    for k in ("task_id", "routing_decision_id", "execution_run_id")
                )
                or not any(e["payload"]["event_type"] == "completed" for e in lifecycle)
            ):
                errors.append("missing or unrelated lifecycle reports")
            applied = [
                e["payload"]["applied_plan_id"]
                for e in lifecycle
                if e["payload"]["applied_plan_id"] is not None
            ]
            verified = bool(applied) and all(p == record["selected_plan_id"] for p in applied)
            expected_configuration = (
                group["conditions"]["selected_configuration"] if verified else "unknown"
            )
            reason = (
                "reported_selected_plan"
                if verified
                else "different_plan"
                if applied
                else "not_reported"
            )
            if (
                group["conditions"]["applied_configuration"] != expected_configuration
                or group["conditions"]["applied_configuration_reason"] != reason
                or group["applied_unknown_count"] != int(not verified)
            ):
                errors.append("unsupported applied configuration alternative")
        if (
            sources[0]["discovery_ref"] is None
            or sources[0]["discovery_ref"] != sources[1]["discovery_ref"]
            or len({s["task_id"] for s in sources}) != 2
            or len({s["routing_decision_id"] for s in sources}) != 2
            or len({s["execution_run_id"] for s in sources}) != 2
        ):
            errors.append("unlinked or reused task identities")
        if len({g["conditions"]["selected_model"] for g in groups}) != 2:
            errors.append("missing independent task constraints")
        required = {
            "planning.build_launch_request",
            "planning.build_launch_spec",
            "planning.executor",
            "task.build_launch_request",
            "task.build_launch_spec",
            "task.executor",
        }
        if not required <= set(witness["construction_events"]):
            errors.append("missing production host construction")
        commands = witness["commands"]
        if [r["control"] for r in commands] != [
            "record_task",
            "record_task",
            "analyze_observations",
            "missing_discovery_ref",
            "forged_discovery_ref",
            "whole_skill_claim",
            "delete_objective",
            "deleted_objective_analysis",
        ]:
            errors.append("missing control-specific installed faults")
        for index in (0, 1):
            bound = [s for s in sources if s["task_id"] == commands[index]["lineage"]["task_id"]]
            if len(bound) != 1 or commands[index]["lineage"] != {
                k: bound[0][k] for k in ("task_id", "routing_decision_id", "discovery_ref")
            }:
                errors.append("installed record lineage mismatch")
        first_source = next(s for s in sources if s["task_id"] == commands[0]["lineage"]["task_id"])
        if (
            commands[3]["lineage"]["task_id"] != first_source["task_id"]
            or commands[3]["lineage"]["routing_decision_id"] != first_source["routing_decision_id"]
            or commands[3]["lineage"]["discovery_ref"] is not None
        ):
            errors.append("missing entered missing-link fault")
        forged = commands[4]["lineage"]
        if (
            forged["task_id"] != first_source["task_id"]
            or forged["routing_decision_id"] != first_source["routing_decision_id"]
            or forged["discovery_ref"] != dict(first_source["discovery_ref"], trace_digest="0" * 64)
        ):
            errors.append("missing entered forged-link fault")
        if commands[5]["claim_scope"] != "whole_skill":
            errors.append("missing entered whole-skill fault")
        deletion = commands[6]["command"]
        if (
            deletion[deletion.index("--work-objective-id") + 1]
            != sources[0]["discovery_ref"]["work_objective_id"]
        ):
            errors.append("wrong deleted objective")
        statuses = [r["response_status"] for r in commands]
        if statuses != [
            "recorded",
            "recorded",
            "updated",
            "invalid",
            "invalid",
            "invalid",
            "deleted",
            "not_due",
        ]:
            errors.append("missing entered installed denial commands")
        for index, record in enumerate(commands):
            argv = record["command"]
            if (
                argv[1:4] != ["-m", "jevdrill.cli", "--storage"]
                or argv[5] != ("delete-discovery" if index == 6 else "analyze")
                or record["exit_code"] != (2 if 3 <= index <= 5 else 0)
            ):
                errors.append("wrong installed command or outcome")
        if (
            witness["deleted_groups"] != []
            or witness["performance_claims"] != "insufficient_evidence"
        ):
            errors.append("unsupported learning claim or deletion")
    except (KeyError, TypeError, ValueError, IndexError, StopIteration):
        errors.append("malformed installed lineage observations")
    return errors


def reduce_manifests(manifests, expected, companion_digest, root=ROOT, required_platforms=None):
    errors = []
    seen = set()
    for receipt in manifests:
        if not isinstance(receipt, dict):
            errors.append("malformed LEARN receipt")
            continue
        identity = (receipt.get("os"), receipt.get("python_minor"))
        if not all(isinstance(part, str) for part in identity) or identity not in host.route.MATRIX:
            errors.append("duplicate or unexpected native platform")
            continue
        if identity in seen:
            errors.append("duplicate or unexpected native platform")
        seen.add(identity)
        if (
            receipt.get("phase") != "LEARN"
            or receipt.get("schema_version") != 1
            or receipt.get("input_digest") != expected
            or receipt.get("source_stable") is not True
        ):
            errors.append("stale or unsupported LEARN source")
        inherited = receipt.get("inherited_host")
        if not isinstance(inherited, dict):
            errors.append("missing inherited current-source controls")
            continue
        errors.extend(
            host.reduce_manifests(
                [inherited],
                host.input_digest(root),
                companion_digest,
                root,
                required_platforms={identity},
            )
        )
        assertions = inherited.get("route_regressions", {}).get("assertions", [])
        actual = {row.get("node_id") for row in assertions if row.get("outcome") == "passed"}
        for nodes in CONTROLS.values():
            for node in nodes:
                if node not in actual:
                    errors.append("missing LEARN assertion: " + node)
        provenance = receipt.get("module_provenance", {})
        if not isinstance(provenance, dict):
            provenance = {}
        for name in ("application", "storage", "analysis", "maintenance", "contracts"):
            if (
                provenance.get(name)
                != hashlib.sha256((root / "src/jevdrill" / (name + ".py")).read_bytes()).hexdigest()
            ):
                errors.append("wrong installed module origin: " + name)
        if receipt.get("witness_sha256") != host.digest_value(receipt.get("witness")):
            errors.append("learning observation digest mismatch")
        errors.extend(witness_errors(receipt.get("witness")))
        extra = receipt.get("companion_extras", {})
        if not isinstance(extra, dict):
            extra = {}
        command = extra.get("command", [])
        required_command = extra_arguments(identity[0])
        if (
            len(command) != len(required_command) + 2
            or command[1:-1] != required_command
            or not command[-1].startswith("--junitxml=")
            or extra.get("command_sha256") != host.digest_value(command)
            or extra.get("exit_code") != 0
            or extra.get("input_digest") != companion_digest
            or extra.get("source_stable") is not True
        ):
            errors.append("missing required native locking/liveness command")
        assertions = extra.get("assertions", [])
        expected_assertions = {
            row["node_id"]
            for row in json.loads(
                (
                    root / "evidence/HOST/companion" / ("extra-" + str(identity[0]) + ".json")
                ).read_text()
            )["assertions"]
        }
        if (
            not assertions
            or any(row.get("outcome") != "passed" for row in assertions)
            or {row.get("node_id") for row in assertions} != expected_assertions
            or extra.get("assertions_sha256") != host.digest_value(assertions)
        ):
            errors.append("missing required native locking/liveness assertions")
        static = receipt.get("learn_static", {})
        if not isinstance(static, dict):
            static = {}
        if static.get("command") != ["<python>", *LEARN_STATIC] or static.get("exit_code") != 0:
            errors.append("failed or wrong LEARN static check")
        duration = receipt.get("duration_seconds")
        if type(duration) not in (int, float) or not 0 < duration <= 600:
            errors.append("invalid or excessive proof cost")
    required = host.route.MATRIX if required_platforms is None else required_platforms
    errors.extend(f"missing {name}/Python {minor}" for name, minor in sorted(required - seen))
    try:
        coverage = json.loads((root / "evidence/LEARN/coverage.json").read_text())
        delta = json.loads((root / "evidence/LEARN/spec-delta.json").read_text())
        if (
            coverage.get("required_controls") != CONTROLS
            or set(coverage.get("coverage", {})) != set(CONTROLS)
            or coverage.get("status") != "complete"
        ):
            errors.append("missing five-criterion LEARN coverage")
        if (
            delta.get("schema") != "spec_delta_closeout.v1"
            or delta.get("decision") != "no_spec_delta"
            or delta.get("redaction_posture") != "metadata_only"
        ):
            errors.append("malformed LEARN spec delta")
    except (OSError, ValueError):
        errors.append("malformed LEARN control declarations")
    return sorted(set(errors))


def collect(root, companion_root):
    started = time.monotonic()
    before = input_digest(root)
    runtime = companion_root / "phase-loop-runtime"
    companion_before = host.source_digest(runtime)
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
            raise ValueError("Companion handoff content mismatch")
    probe = subprocess.run(
        [
            str(python),
            "-c",
            "import hashlib,importlib,importlib.metadata,json,platform,sys;from pathlib import Path;root=Path(sys.argv[1]).resolve();names=json.loads(sys.argv[2]);paths={n:Path(importlib.import_module('phase_loop_runtime.'+n).__file__).resolve() for n in names};print(json.dumps({'modules':{n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in paths.items()},'version':importlib.metadata.version('phase-loop-runtime'),'os':platform.system(),'python_minor':f'{sys.version_info.major}.{sys.version_info.minor}','python_version':platform.python_version(),'source_root_matches':all(p.is_relative_to(root/'src') for p in paths.values())}))",
            str(runtime),
            json.dumps(list(handoff["companion_modules"])),
        ],
        cwd=companion_root,
        capture_output=True,
        check=True,
        timeout=30,
    )
    provenance = json.loads(probe.stdout)
    os.environ.update(
        JEVDRILL_AGENT_HARNESS_ROOT=str(companion_root),
        JEVDRILL_TEST_PYTHON=sys.executable,
        JEVDRILL_TEST_CLI=str(
            Path(sys.executable).parent / ("jevdrill.exe" if os.name == "nt" else "jevdrill")
        ),
        PHASE_LOOP_TDD_EXPECT_SCHED="1",
    )
    with tempfile.TemporaryDirectory(prefix="jevdrill-learn-") as temporary:
        tmp = Path(temporary)
        host_witness = tmp / "host.json"
        learn_witness = tmp / "learn.json"
        os.environ.update(
            JEVDRILL_EVALUATION_OUTPUT=str(host_witness), JEVDRILL_LEARN_WITNESS=str(learn_witness)
        )
        inherited = host.route.collect(root)

        def run(command, cwd, junit=None):
            try:
                result = subprocess.run(
                    command,
                    cwd=cwd,
                    capture_output=True,
                    check=False,
                    env=dict(
                        os.environ,
                        PYTHONPATH=os.pathsep.join([str(runtime / "src"), str(runtime / "tests")]),
                    ),
                    timeout=max(0.001, 600 - (time.monotonic() - started)),
                )
            except subprocess.TimeoutExpired:
                result = subprocess.CompletedProcess(command, 125, b"TimeoutExpired", b"")
            assertions = host.assertions_from(junit, runtime) if junit and junit.exists() else []
            return {
                "command": command,
                "command_sha256": host.digest_value(command),
                "output_sha256": hashlib.sha256(result.stdout + result.stderr).hexdigest(),
                "exit_code": result.returncode,
                "input_digest": companion_before,
                "source_stable": host.source_digest(runtime) == companion_before,
                "assertions": assertions,
                "assertions_sha256": host.digest_value(assertions),
            }

        companion = run(
            host.companion_command(str(python), tmp, platform.system()),
            companion_root,
            tmp / "companion.xml",
        )
        companion["installed_provenance"] = provenance
        witness = json.loads(host_witness.read_text()) if host_witness.exists() else None
        companion["integrated_discovery"] = (witness or {}).get("companion_discovery", {})
        host_static = run(
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                "tests/conformance",
                "research/evaluation/host",
            ],
            root,
        )
        host_static["command"] = ["<python>", *host_static["command"][1:]]
        inherited_host = {
            "schema_version": 2,
            "phase": "HOST",
            "os": platform.system(),
            "python_minor": f"{sys.version_info.major}.{sys.version_info.minor}",
            "input_digest": host.input_digest(root),
            "source_stable": input_digest(root) == before,
            "route_regressions": inherited,
            "companion": companion,
            "witnesses": witness,
            "witness_sha256": host.digest_value(witness),
            "fixture_digests": handoff["schemas"],
            "host_static": host_static,
            "duration_seconds": round(time.monotonic() - started, 3),
        }
        extras = run(
            [str(python), *extra_arguments(platform.system()), f"--junitxml={tmp / 'extras.xml'}"],
            runtime,
            tmp / "extras.xml",
        )
        static = run([sys.executable, *LEARN_STATIC], root)
        static["command"] = ["<python>", *LEARN_STATIC]
        observed = json.loads(learn_witness.read_text()) if learn_witness.exists() else None
    modules = {
        name: Path(importlib.import_module("jevdrill." + name).__file__).resolve()
        for name in ("application", "storage", "analysis", "maintenance", "contracts")
    }
    if not all(path.is_relative_to(root / "src") for path in modules.values()):
        raise ValueError("JEV installed module origin mismatch")
    return {
        "schema_version": 1,
        "phase": "LEARN",
        "os": platform.system(),
        "python_minor": f"{sys.version_info.major}.{sys.version_info.minor}",
        "input_digest": before,
        "source_stable": input_digest(root) == before,
        "inherited_host": inherited_host,
        "companion_extras": extras,
        "module_provenance": {
            name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in modules.items()
        },
        "witness": observed,
        "witness_sha256": host.digest_value(observed),
        "learn_static": static,
        "duration_seconds": round(time.monotonic() - started, 3),
        "proof_cost_target_exceeded": time.monotonic() - started > 300,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-harness", type=Path)
    parser.add_argument("--local-only", action="store_true")
    parser.add_argument("--reduce-only", action="store_true")
    args = parser.parse_args()
    if args.agent_harness is None:
        parser.error("Explicit --agent-harness PATH is required")
    output = ROOT / "evidence/LEARN"
    platforms = output / "platforms"
    platforms.mkdir(parents=True, exist_ok=True)
    current = None if args.reduce_only else collect(ROOT, args.agent_harness.resolve())
    if current is not None:
        (platforms / (platform.system() + "-3.13.json")).write_text(
            json.dumps(current, indent=2) + "\n", encoding="utf-8"
        )
    manifests = []
    for path in sorted(platforms.glob("*.json")):
        try:
            manifests.append(json.loads(path.read_text()))
        except (OSError, ValueError):
            manifests.append(None)
    expected = input_digest(ROOT)
    companion = host.source_digest(args.agent_harness.resolve() / "phase-loop-runtime")
    errors = reduce_manifests(manifests, expected, companion)
    report = {
        "schema_version": 1,
        "phase": "LEARN",
        "status": "passed" if not errors else "blocked",
        "errors": errors,
        "input_digest": expected,
        "companion_digest": companion,
        "platforms": [r.get("os") for r in manifests if isinstance(r, dict)],
        "produced_if_gates": ["IF-0-LEARN-1"] if not errors else [],
    }
    (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))
    if args.local_only and current is not None:
        errors = reduce_manifests(
            [current], expected, companion, required_platforms={(platform.system(), "3.13")}
        )
        print(json.dumps({"local_errors": errors}))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
