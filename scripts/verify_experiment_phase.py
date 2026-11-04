"""Collect current native software proof; full acceptance requires a new linked study."""

import argparse
import hashlib
import importlib
import importlib.util
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "experiment_inherited_learn", ROOT / "scripts/verify_learn_phase.py"
)
learn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(learn)
study_spec = importlib.util.spec_from_file_location(
    "experiment_discovery_study", ROOT / "scripts/verify_discovery_calibration.py"
)
study = importlib.util.module_from_spec(study_spec)
study_spec.loader.exec_module(study)
CONTROLS = {
    "EC-EXPERIMENT-1": [
        "tests/application/test_experiments.py::test_queue_survives_restart_deduplicates_and_counts_distinct_tasks",
        "tests/experiments/test_execution.py::test_admission_reserves_whole_run_without_dispatch_and_retries_reuse",
        "tests/experiments/test_execution.py::test_concurrent_reservations_and_dispatch_claims",
        "tests/experiments/test_execution.py::test_spend_reservations_survive_deletion_and_daily_rollover",
        "tests/storage/test_experiments.py::test_resolved_settings_disable_even_an_enabled_grant",
        "tests/storage/test_experiments.py::test_unregistered_task_cannot_populate_proposal_content_or_recurrence",
        "tests/storage/test_experiments.py::test_opted_out_equivalent_recurrence_cannot_increase_priority",
    ],
    "EC-EXPERIMENT-2": [
        "tests/experiments/test_execution.py::test_lost_ack_restart_polls_without_redispatch",
        "tests/experiments/test_execution.py::test_cancellation_waits_for_cleanup_even_after_restart",
        "tests/experiments/test_execution.py::test_deletion_during_start_cannot_restore_content_or_accept_late_result",
        "tests/experiments/test_development.py::test_actual_immediate_host_acceptance_is_bounded_and_not_redispatched",
        "tests/experiments/test_development.py::test_documented_provider_context_cannot_be_replaced_by_request_bytes",
        "tests/experiments/test_development.py::test_actual_baml_artifact_worker_preserves_independent_checks[review]",
        "tests/experiments/test_development.py::test_actual_baml_artifact_worker_preserves_independent_checks[documentation]",
        "tests/experiments/test_development.py::test_five_arm_comparison_reserves_once_and_survives_restart_without_redispatch",
        "tests/experiments/test_development.py::test_five_arm_cancellation_during_third_request_prevents_fourth_and_recovery_retry",
    ],
    "EC-EXPERIMENT-3": [
        "tests/promotion/test_lifecycle.py::test_grant_required_and_bounded_routes_survive_restart",
        "tests/promotion/test_lifecycle.py::test_deleted_supporting_data_invalidates_active_policy",
        "tests/promotion/test_lifecycle.py::test_regression_restores_only_current_verified_previous_policy",
        "tests/promotion/test_lifecycle.py::test_optout_only_invalidates_policies_using_the_affected_task",
        "tests/promotion/test_recorded_evidence.py::test_recorded_evaluator_binds_real_durable_comparisons_without_new_calls",
        "tests/promotion/test_recorded_evidence.py::test_incomplete_candidate_preserves_unknown_critical_checks",
        "tests/application/test_experiments.py::test_recovered_learned_route_cannot_bypass_missing_policy_verification",
    ],
    "EC-EXPERIMENT-4": [
        "tests/verification/test_discovery_calibration.py::test_actual_offline_navigation_and_task_configuration_reject_unsuitable_controls",
        "tests/verification/test_discovery_calibration.py::test_software_only_cannot_become_authorized_empirical_study",
        "tests/verification/test_calibration_benchmark.py::test_family_specific_calibration_is_pending_and_references_are_independent",
        "tests/verification/test_discovery_calibration.py::test_guarded_driver_records_five_distinct_arms_with_loopback_and_explicit_fixture_runtime",
        "tests/verification/test_discovery_calibration.py::test_critical_regression_is_observed_but_missing_outcome_remains_unknown",
        "tests/experiments/test_development_judge.py::test_actual_baml_pinned_judge_reserves_all_discovery_and_task_calls",
        "tests/experiments/test_development_judge.py::test_completed_identical_judgment_reuses_immutable_receipt_without_new_dispatch",
        "tests/experiments/test_development_judge.py::test_slow_credential_lookup_cannot_dispatch_after_caller_deadline",
    ],
}
TEST_PATHS = tuple(
    sorted(
        set(learn.TEST_PATHS)
        | {node.split("::")[0] for nodes in CONTROLS.values() for node in nodes}
    )
)
STATIC = [
    "-m",
    "ruff",
    "check",
    "tests/experiments",
    "tests/promotion",
    "scripts/verify_experiment_phase.py",
    "scripts/verify_development_runtime.py",
    "scripts/verify_calibration_benchmark.py",
    "scripts/verify_discovery_calibration.py",
]
MODULES = (
    "application",
    "cli",
    "contracts",
    "storage",
    "experiments",
    "analysis",
    "evaluation",
    "routing",
    "integrations.development",
    "integrations.experiments",
)


def input_digest(root):
    paths = {
        p
        for pattern in (
            "research/evaluation/discovery-calibration/**",
            ".github/workflows/experiment.yml",
            "plans/phase-plan-v1-EXPERIMENT.md",
            "evidence/EXPERIMENT/coverage.json",
            "evidence/EXPERIMENT/spec-delta.json",
            "evidence/EXPERIMENT/study-proposal.json",
        )
        for p in root.glob(pattern)
        if p.is_file()
    }
    return learn.host.digest_value(
        {
            "inherited": learn.input_digest(root),
            "experiment": {
                path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(paths)
            },
        }
    )


def collect(root, companion):
    started = time.monotonic()
    before = input_digest(root)
    inherited = learn.collect(root, companion, extra_test_paths=TEST_PATHS)
    try:
        result = subprocess.run(
            [sys.executable, *STATIC],
            cwd=root,
            capture_output=True,
            check=False,
            timeout=max(0.001, 600 - (time.monotonic() - started)),
        )
        static_code = result.returncode
        static_output = result.stdout + result.stderr
    except (OSError, subprocess.TimeoutExpired) as error:
        static_code = 125
        static_output = type(error).__name__.encode()
    provenance = {}
    for name in MODULES:
        path = Path(importlib.import_module("jevdrill." + name).__file__).resolve()
        if not path.is_relative_to(root / "src"):
            raise ValueError("wrong installed EXPERIMENT module origin")
        provenance[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "schema_version": 1,
        "phase": "EXPERIMENT",
        "os": platform.system(),
        "python_minor": f"{sys.version_info.major}.{sys.version_info.minor}",
        "input_digest": before,
        "source_stable": before == input_digest(root),
        "inherited_learn": inherited,
        "module_provenance": provenance,
        "experiment_static": {
            "command": ["<python>", *STATIC],
            "exit_code": static_code,
            "output_sha256": hashlib.sha256(static_output).hexdigest(),
        },
        "native_internal_support": "configured_linux_only"
        if sys.platform == "linux"
        else "unsupported_disabled",
        "duration_seconds": round(time.monotonic() - started, 3),
        "proof_cost_target_exceeded": time.monotonic() - started > 300,
    }


def reduce_manifests(manifests, expected, companion_digest, root=ROOT, required_platforms=None):
    errors, seen = [], set()
    for receipt in manifests:
        if not isinstance(receipt, dict):
            errors.append("malformed EXPERIMENT native receipt")
            continue
        identity = (receipt.get("os"), receipt.get("python_minor"))
        if (
            not all(isinstance(part, str) for part in identity)
            or identity not in learn.host.route.MATRIX
            or identity in seen
        ):
            errors.append("duplicate or unexpected EXPERIMENT platform")
            continue
        seen.add(identity)
        if (
            receipt.get("schema_version") != 1
            or receipt.get("phase") != "EXPERIMENT"
            or receipt.get("input_digest") != expected
            or receipt.get("source_stable") is not True
        ):
            errors.append("stale or unsupported EXPERIMENT source")
        inherited = receipt.get("inherited_learn")
        if not isinstance(inherited, dict):
            errors.append("missing inherited current-source LEARN controls")
            continue
        errors.extend(
            learn.reduce_manifests(
                [inherited],
                learn.input_digest(root),
                companion_digest,
                root,
                required_platforms={identity},
                extra_test_paths=TEST_PATHS,
            )
        )
        assertions = (
            inherited.get("inherited_host", {}).get("route_regressions", {}).get("assertions", [])
        )
        actual = {row.get("node_id") for row in assertions if row.get("outcome") == "passed"}
        for controls in CONTROLS.values():
            errors.extend(
                "missing EXPERIMENT assertion: " + node
                for node in controls
                if not any(value == node or value.startswith(node + "[") for value in actual)
            )
        provenance = receipt.get("module_provenance", {})
        for name in MODULES:
            source = root / "src/jevdrill" / (name.replace(".", "/") + ".py")
            if provenance.get(name) != hashlib.sha256(source.read_bytes()).hexdigest():
                errors.append("wrong installed EXPERIMENT origin: " + name)
        static = receipt.get("experiment_static", {})
        if static.get("command") != ["<python>", *STATIC] or static.get("exit_code") != 0:
            errors.append("missing or failed EXPERIMENT static check")
        duration = receipt.get("duration_seconds")
        if type(duration) not in (float, int) or not 0 < duration <= 600:
            errors.append("invalid or excessive EXPERIMENT proof cost")
        if receipt.get("native_internal_support") != (
            "configured_linux_only" if identity[0] == "Linux" else "unsupported_disabled"
        ):
            errors.append("unsupported native execution capability claim")
    required = learn.host.route.MATRIX if required_platforms is None else required_platforms
    errors.extend(f"missing {name}/Python {minor}" for name, minor in sorted(required - seen))
    try:
        coverage = json.loads((root / "evidence/EXPERIMENT/coverage.json").read_text())
        delta = json.loads((root / "evidence/EXPERIMENT/spec-delta.json").read_text())
        if set(coverage["coverage"]) != set(CONTROLS) or coverage["required_controls"] != CONTROLS:
            errors.append("missing four-criterion EXPERIMENT coverage")
        if (
            delta["schema"] != "spec_delta_closeout.v1"
            or delta["decision"] != "no_spec_delta"
            or delta["redaction_posture"] != "metadata_only"
        ):
            errors.append("invalid EXPERIMENT spec closeout")
    except (OSError, ValueError, KeyError, TypeError):
        errors.append("missing EXPERIMENT control artifacts")
    return sorted(set(errors))


def operational_errors(root, expected):
    try:
        runtime = json.loads((root / "evidence/EXPERIMENT/development-runtime.json").read_text())
        if (
            type(runtime["schema_version"]) is not int
            or runtime["schema_version"] != 1
            or runtime["kind"] != "bounded_development_runtime"
            or runtime["os"] != "Linux"
            or runtime["input_digest"] != expected
            or runtime["status"] != "passed"
            or runtime["paid_calls"] != 0
            or not runtime["checks"]
            or any(value is not True for value in runtime["checks"].values())
            or runtime["runtime_test_exit_code"] != 0
            or runtime["recorded_test_exit_code"] != 0
        ):
            return ["missing current actual Linux execution/cleanup/grading proof"]
        import importlib.util

        runtime_spec = importlib.util.spec_from_file_location(
            "experiment_runtime_checks", root / "scripts/verify_development_runtime.py"
        )
        runtime_checks = importlib.util.module_from_spec(runtime_spec)
        runtime_spec.loader.exec_module(runtime_checks)
        if (
            set(runtime["checks"]) != runtime_checks.EXPECTED_CHECKS
            or runtime["image_id"] != runtime_checks.INSPECTED_IMAGE
            or runtime["image_provenance"]
            != {"Id": runtime_checks.INSPECTED_IMAGE, "Os": "linux", "Architecture": "amd64"}
        ):
            return ["missing named operational checks or immutable image provenance"]
        directory = root / runtime["run_directory"]
        expected_prefix = [sys.executable, "-m", "pytest", "-q"]
        if runtime["runtime_test_command"] != [
            *expected_prefix,
            f"--junitxml={directory / 'tests.xml'}",
            *[
                f"tests/experiments/test_development.py::{name}"
                for name in runtime_checks.RUNTIME_TESTS
            ],
        ] or runtime["recorded_test_command"] != [
            *expected_prefix,
            f"--junitxml={directory / 'recorded-tests.xml'}",
            "tests/promotion/runtime_recorded_evidence.py",
        ]:
            return ["wrong actual operational command"]
        if not directory.resolve().is_relative_to((root / ".phase-loop/runs").resolve()):
            return ["runtime artifacts outside authorized run"]
        if runtime["runtime_tests"] != list(runtime_checks.RUNTIME_TESTS) or runtime[
            "recorded_tests"
        ] != list(runtime_checks.RECORDED_TESTS):
            return ["wrong operational tests"]
        if set(runtime["artifact_digests"]) != {
            "tests.xml",
            "recorded-tests.xml",
            "restricted-comparison.log",
            "recorded-comparison.log",
        } or any(
            hashlib.sha256((directory / name).read_bytes()).hexdigest() != digest
            for name, digest in runtime["artifact_digests"].items()
        ):
            return ["operational artifact digest mismatch"]
        if not runtime_checks.runtime_tests_passed(
            directory / "tests.xml", 0
        ) or not runtime_checks.runtime_tests_passed(
            directory / "recorded-tests.xml", 0, runtime_checks.RECORDED_TESTS
        ):
            return ["actual runtime commands/assertions missing"]
        return []
    except (OSError, ValueError, KeyError, TypeError):
        return ["actual Linux operational proof missing"]


def empirical_errors(root):
    errors = []
    protocol = study.read_protocol(root)
    errors.extend(study.calibration_errors(protocol))
    path, authority = (
        root / "evidence/EXPERIMENT/development-study.json",
        root / "evidence/EXPERIMENT/study-authorization.json",
    )
    if not path.is_file():
        errors.append("authorized preregistered linked discovery/routing development study missing")
    else:
        errors.extend(
            study.validate_study(
                json.loads(path.read_text()),
                protocol,
                json.loads(authority.read_text()) if authority.is_file() else None,
                root,
            )
        )
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-harness", required=True, type=Path)
    parser.add_argument("--local-only", action="store_true")
    parser.add_argument("--reduce-only", action="store_true")
    parser.add_argument("--software-only", action="store_true")
    args = parser.parse_args()
    output = ROOT / "evidence/EXPERIMENT"
    platforms = output / "platforms"
    platforms.mkdir(parents=True, exist_ok=True)
    current = None if args.reduce_only else collect(ROOT, args.agent_harness.resolve())
    if current is not None:
        destination = platforms / (platform.system() + "-3.13.json")
        if destination.exists():
            history = output / "history"
            history.mkdir(exist_ok=True)
            (history / (str(time.time_ns()) + "-" + destination.name)).write_bytes(
                destination.read_bytes()
            )
        destination.write_text(json.dumps(current, indent=2) + "\n")
    manifests = [json.loads(path.read_text()) for path in sorted(platforms.glob("*.json"))]
    expected = input_digest(ROOT)
    companion = learn.host.source_digest(args.agent_harness.resolve() / "phase-loop-runtime")
    native = reduce_manifests(
        [current] if args.local_only and current else manifests,
        expected,
        companion,
        required_platforms={(platform.system(), "3.13")} if args.local_only else None,
    )
    operational = [] if args.local_only else operational_errors(ROOT, expected)
    empirical = [] if args.software_only else empirical_errors(ROOT)
    errors = native + operational + empirical
    report = {
        "schema_version": 1,
        "phase": "EXPERIMENT",
        "status": "passed" if not errors else "blocked",
        "scope": "software_only_diagnostic" if args.software_only else "whole_phase",
        "input_digest": expected,
        "companion_digest": companion,
        "errors": sorted(set(errors)),
        "native_errors": native,
        "operational_errors": operational,
        "empirical_errors": empirical,
        "produced_if_gates": []
        if errors or args.software_only or args.local_only
        else ["IF-0-EXPERIMENT-1"],
    }
    target = output / ("software-verification.json" if args.software_only else "verification.json")
    target.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
