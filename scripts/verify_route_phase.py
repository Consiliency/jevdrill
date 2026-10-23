"""Collect native ROUTE verification or reduce recorded native manifests."""

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = {("Linux", "3.13"), ("Darwin", "3.13"), ("Windows", "3.13")}
CHECKS = {
    "tests",
    "contracts",
    "generation",
    "vocabulary",
    "imports",
    "lint",
    "format",
    "types",
    "build",
    "cli",
    "vocabulary_lint",
    "installed_package",
    "cold_cli",
}
REQUIREMENTS = {f"EC-ROUTE-{number}" for number in range(1, 8)} | {"IF-0-VC-2"}
REQUIRED_CONTROLS = {
    "EC-ROUTE-1": [
        "tests/storage/test_discovery_recovery.py::test_reservation_crash_recovery_never_dispatches_or_replenishes",
        "tests/application/test_discovery_application.py::test_route_commit_rechecks_concurrent_objective_deletion",
    ],
    "EC-ROUTE-2": [
        "tests/application/test_discovery_application.py::test_bad_links_never_enter_prepare",
        "tests/application/test_discovery_application.py::test_required_guidance_rebinds_coalesces_and_rejects_conflicts",
    ],
    "EC-ROUTE-3": [
        "tests/privacy/test_discovery_privacy.py::test_discovery_forbidden_provider_traffic_never_dispatches",
        "tests/integrations/test_discovery_jev.py::test_unsupported_requested_bounds_reject_before_http",
        "tests/integrations/test_discovery_jev.py::test_discovery_call_rechecks_authorization_before_http",
    ],
    "EC-ROUTE-4": [
        "tests/privacy/test_discovery_privacy.py::test_metadata_replay_has_no_raw_objective_description_or_provider_payload",
        "tests/cli/test_discovery_cli.py::test_cold_discover_inspect_replay_delete_commands",
        "tests/privacy/test_round34_combined.py::test_suffix_assignments_never_reach_six_application_sinks",
        "tests/privacy/test_round34_combined.py::test_raw_multiline_owner_rejects_before_six_application_effects_and_bytes",
        "tests/privacy/test_round34_combined.py::test_multiline_named_expression_checks_raw_owner",
        "tests/privacy/test_round35_records.py::test_sensitive_records_never_reach_six_application_sinks",
        "tests/privacy/test_round35_records.py::test_hidden_suffix_records_after_prose_are_clean",
        "tests/privacy/test_round35_records.py::test_alternate_key_delimiters_are_clean",
        "tests/privacy/test_round36_records.py::test_sensitive_records_never_reach_six_application_sinks",
        "tests/privacy/test_round36_records.py::test_spacing_combining_suffix_records_are_clean",
        "tests/privacy/test_round36_records.py::test_perl_dereference_owner_remains_sensitive",
        "tests/privacy/test_round36_records.py::test_right_arrow_target_is_checked_before_its_value",
        "tests/privacy/test_round36_records.py::test_word_and_left_arrow_assignments_are_clean",
        "tests/privacy/test_round37_values.py::test_open_literal_values_never_escape_owner",
        "tests/privacy/test_round37_values.py::test_incomplete_assignment_values_never_escape_owner",
        "tests/privacy/test_round37_values.py::test_original_witness_line_boundaries_are_clean",
        "tests/privacy/test_round37_values.py::test_multiline_values_never_reach_six_application_sinks",
        "tests/privacy/test_round38_completeness.py::test_owned_expression_bodies_are_clean",
        "tests/privacy/test_round38_completeness.py::test_original_witnesses_keep_ownership_across_line_boundaries",
        "tests/privacy/test_round38_completeness.py::test_expression_bodies_never_reach_six_application_sinks",
        "tests/privacy/test_round38_completeness.py::test_public_expression_twins_preserve_classification",
    ],
    "EC-ROUTE-5": [
        "tests/contracts/test_discovery_contracts.py::test_discovery_contract_parity",
        "tests/discovery/test_navigation.py::test_binding_unknown_duplicate_and_stale_answers",
        "tests/storage/test_discovery_recovery.py::test_late_answer_cannot_replace_terminal_failure",
    ],
    "EC-ROUTE-6": [
        "tests/discovery/test_navigation.py::test_successive_questions_false_categories_recover_and_permutations",
        "tests/discovery/test_navigation.py::test_false_domain_children_follow_already_queued_alternate_domains",
        "tests/application/test_discovery_application.py::test_false_initial_category_recovers_useful_alternate_branch",
        "tests/integrations/test_discovery_jev.py::test_generated_baml_discovery_application_loopback_and_partial_usage",
    ],
    "EC-ROUTE-7": [
        "tests/application/test_discovery_application.py::test_public_discovery_two_independent_tasks_and_replay",
        "tests/application/test_discovery_application.py::test_changing_objective_changes_supported_guidance",
        "tests/application/test_discovery_application.py::test_all_discovery_statuses_gate_quality_sufficient_route",
    ],
    "IF-0-VC-2": [
        "tests/verification/test_route_phase.py::test_reducer_rejects_four_criterion_coverage",
        "tests/verification/test_route_phase.py::test_reducer_requires_executed_controls",
        "tests/verification/test_route_phase.py::test_reducer_rejects_inputs_changed_during_collection",
    ],
}
CONTROL_COUNTS = {
    "tests/privacy/test_round38_completeness.py::test_owned_expression_bodies_are_clean": 672,
    "tests/privacy/test_round38_completeness.py::test_original_witnesses_keep_ownership_across_line_boundaries": 168,
    "tests/privacy/test_round38_completeness.py::test_expression_bodies_never_reach_six_application_sinks": 672,
    "tests/privacy/test_round38_completeness.py::test_public_expression_twins_preserve_classification": 56,
    "tests/privacy/test_round37_values.py::test_open_literal_values_never_escape_owner": 192,
    "tests/privacy/test_round37_values.py::test_incomplete_assignment_values_never_escape_owner": 264,
    "tests/privacy/test_round37_values.py::test_original_witness_line_boundaries_are_clean": 42,
    "tests/privacy/test_round37_values.py::test_multiline_values_never_reach_six_application_sinks": 168,
    "tests/privacy/test_round36_records.py::test_sensitive_records_never_reach_six_application_sinks": 312,
    "tests/privacy/test_round36_records.py::test_spacing_combining_suffix_records_are_clean": 80,
    "tests/privacy/test_round36_records.py::test_perl_dereference_owner_remains_sensitive": 128,
    "tests/privacy/test_round36_records.py::test_right_arrow_target_is_checked_before_its_value": 32,
    "tests/privacy/test_round36_records.py::test_word_and_left_arrow_assignments_are_clean": 96,
    "tests/privacy/test_round35_records.py::test_sensitive_records_never_reach_six_application_sinks": 288,
    "tests/privacy/test_round35_records.py::test_hidden_suffix_records_after_prose_are_clean": 96,
    "tests/privacy/test_round35_records.py::test_alternate_key_delimiters_are_clean": 96,
    "tests/privacy/test_round34_combined.py::test_suffix_assignments_never_reach_six_application_sinks": 216,
    "tests/privacy/test_round34_combined.py::test_raw_multiline_owner_rejects_before_six_application_effects_and_bytes": 24,
    "tests/privacy/test_round34_combined.py::test_multiline_named_expression_checks_raw_owner": 48,
    "tests/integrations/test_discovery_jev.py::test_discovery_call_rechecks_authorization_before_http": 3,
    "tests/verification/test_route_phase.py::test_reducer_rejects_inputs_changed_during_collection": 2,
    "tests/application/test_discovery_application.py::test_bad_links_never_enter_prepare": 8,
    "tests/privacy/test_discovery_privacy.py::test_discovery_forbidden_provider_traffic_never_dispatches": 5,
    "tests/integrations/test_discovery_jev.py::test_unsupported_requested_bounds_reject_before_http": 5,
    "tests/contracts/test_discovery_contracts.py::test_discovery_contract_parity": 25,
    "tests/application/test_discovery_application.py::test_all_discovery_statuses_gate_quality_sufficient_route": 5,
}
REQUIRED_TEST_PATHS = (
    "tests/costing",
    "tests/discovery",
    "tests/contracts/test_discovery_contracts.py",
    "tests/storage/test_discovery_recovery.py",
    "tests/integrations/test_discovery_jev.py",
    "tests/privacy/test_discovery_privacy.py",
    "tests/application/test_discovery_application.py",
    "tests/cli/test_discovery_cli.py",
    "tests/guidance",
    "tests/privacy/test_storage_privacy.py",
    "tests/privacy/test_context_privacy.py",
    "tests/privacy/test_jev_privacy.py",
    "tests/privacy/test_application_privacy.py",
    "tests/privacy/test_round34_combined.py",
    "tests/privacy/test_round35_records.py",
    "tests/privacy/test_round36_records.py",
    "tests/privacy/test_round37_values.py",
    "tests/privacy/test_round38_completeness.py",
)


def command_digest(command: list[str]) -> str:
    return hashlib.sha256(json.dumps(command, separators=(",", ":")).encode()).hexdigest()


def commands_for(
    python: str,
    temporary: Path,
    os_name: str | None = None,
    *,
    extra_test_paths: tuple[str, ...] = (),
) -> dict[str, list[str]]:
    scoped_checks = [
        "src/jevdrill",
        "tests/contracts",
        "tests/evaluation",
        "tests/storage",
        "tests/catalog",
        "tests/discovery",
        "tests/conftest.py",
        "tests/inventory",
        "tests/context",
        "tests/settings",
        "tests/routing",
        "tests/costing",
        "tests/guidance",
        "tests/integrations",
        "tests/application",
        "tests/cli",
        "tests/privacy",
        "tests/verification",
    ]
    commands = {
        "tests": [
            python,
            "-m",
            "pytest",
            "-v",
            "-o",
            "faulthandler_timeout=30",
            *REQUIRED_TEST_PATHS,
            "tests/verification/test_route_phase.py",
            "tests/contracts/test_boundaries.py",
            "tests/contracts/test_generation.py",
            "tests/contracts/test_route_ports.py",
            "tests/contracts/test_jev_boundary.py",
            "tests/contracts/test_package.py",
            "tests/evaluation",
            "tests/storage/test_storage.py",
            "tests/storage/test_recovery.py",
            "tests/application/test_application.py",
            "tests/application/test_route_integration.py",
            "tests/cli/test_cli.py",
            "tests/routing",
            "tests/catalog",
            "tests/inventory",
            "tests/context",
            "tests/settings",
            f"--junitxml={temporary / 'tests.xml'}",
            f"--basetemp={temporary / 'pytest'}",
        ],
        "contracts": ["node", "scripts/contract_consumer.mjs", "tests/contracts/fixtures"],
        "generation": [python, "scripts/check_generated_contracts.py"],
        "vocabulary": [python, "scripts/render_vocabulary.py", "--check"],
        "imports": [python, "scripts/check_import_boundaries.py"],
        "lint": [python, "-m", "ruff", "check", *scoped_checks],
        "format": [python, "-m", "ruff", "format", "--check", *scoped_checks],
        "types": [python, "-m", "mypy", "src/jevdrill"],
        "build": ["uv", "build", "--out-dir", str(temporary / "dist")],
        "cli": [python, "-m", "jevdrill.cli", "--help"],
        "vocabulary_lint": [python, "scripts/lint_vocabulary.py"],
        "installed_package": [
            python,
            "-m",
            "pytest",
            "-q",
            "tests/contracts/test_package.py",
            "-k",
            "installed",
            f"--basetemp={temporary / 'installed-pytest'}",
        ],
        "cold_cli": [
            python,
            "-m",
            "jevdrill.cli",
            "--storage",
            str(temporary / "cold.sqlite3"),
            "route",
        ],
    }
    if (os_name or platform.system()) == "Linux":
        commands["catalog"] = [
            python,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_catalog_*.py",
        ]
    selected = [arg for arg in commands["tests"] if arg.startswith("tests/")]
    for path in sorted(set(extra_test_paths)):
        if not any(path == arg or path.startswith(arg + "/") for arg in selected):
            commands["tests"].insert(-2, path)
    return commands


def normalized_command(command: list[str], name: str) -> list[str]:
    normalized = list(command)
    if name not in {"contracts", "build"} and normalized:
        normalized[0] = "<python>"
    if name in {"tests", "installed_package"}:
        normalized = [
            "--junitxml=<temporary>/tests.xml"
            if part.startswith("--junitxml=")
            else f"--basetemp=<temporary>/{'pytest' if name == 'tests' else 'installed-pytest'}"
            if part.startswith("--basetemp=")
            else part
            for part in normalized
        ]
    if name == "build" and len(normalized) == 4:
        normalized[3] = "<temporary>/dist"
    if name == "cold_cli" and len(normalized) == 6:
        normalized[4] = "<temporary>/cold.sqlite3"
    return normalized


def input_digest(root: Path) -> str:
    paths: set[Path] = set()
    for pattern in (
        "src/**/*.py",
        "src/**/*.pyi",
        "src/**/*.json",
        "baml_src/**/*",
        "schemas/*.json",
        "tests/**/*.py",
        "tests/contracts/fixtures/*.json",
        "scripts/*.py",
        "scripts/*.mjs",
        "docs/*.md",
        "docs/*.yaml",
        "pyproject.toml",
        "uv.lock",
        "package*.json",
        "baml.toml",
        "README.md",
        ".python-version",
        ".github/workflows/route.yml",
        "specs/phase-plans-v1.md",
        "specs/jevdrill-design-input.md",
        "specs/jevdrill-implementation-proposal.md",
        "plans/phase-plan-v1-ROUTE.md",
        "evidence/ROUTE/spec-delta.json",
        "evidence/ROUTE/coverage.json",
        "evidence/CONTRACT/coverage.json",
        "research/evaluation/cases.json",
    ):
        paths.update(path for path in root.glob(pattern) if path.is_file())
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(root).as_posix()):
        digest.update(path.relative_to(root).as_posix().encode() + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def _valid_spec_delta(root: Path) -> bool:
    try:
        document = json.loads((root / "evidence/ROUTE/spec-delta.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        isinstance(document, dict)
        and document.get("schema") == "spec_delta_closeout.v1"
        and document.get("phase") == "ROUTE"
        and document.get("decision") == "canonical_spec_update"
        and document.get("redaction_posture") == "metadata_only"
        and document.get("target_surfaces")
        == [
            "docs/contracts.md",
            "docs/route-interfaces.md",
            "docs/vocabulary.yaml",
            "docs/vocabulary.md",
        ]
        and document.get("evidence_paths")
        == [
            "evidence/ROUTE/spec-delta.json",
            "evidence/ROUTE/verification.json",
            "evidence/ROUTE/coverage.json",
        ]
        and document.get("downstream_handling") == "replan_HOST"
        and document.get("canonical_adoption") is False
        and document.get("publication_performed") is False
        and isinstance(document.get("if_gates_produced"), list)
        and all(
            isinstance(gate, str) and gate in {"IF-0-ROUTE-1", "IF-0-VC-2"}
            for gate in document["if_gates_produced"]
        )
        and len(set(document["if_gates_produced"])) == len(document["if_gates_produced"])
        and document.get("closeout_status") in {"verification_pending", "blocked", "complete"}
    )


def coverage_errors(root: Path) -> list[str]:
    errors = []
    try:
        coverage = json.loads((root / "evidence/ROUTE/coverage.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ["missing or malformed requirement coverage"]
    if (
        not isinstance(coverage, dict)
        or coverage.get("schema_version") != 1
        or coverage.get("phase") != "ROUTE"
    ):
        return ["malformed requirement coverage"]
    rows = coverage.get("coverage")
    if not isinstance(rows, dict) or set(rows) != REQUIREMENTS:
        return ["missing requirement coverage"]
    if coverage.get("required_controls") != REQUIRED_CONTROLS:
        errors.append("missing entered negative controls")
    for requirement, paths in rows.items():
        if (
            not isinstance(paths, list)
            or not paths
            or any(
                not isinstance(path, str)
                or not path.startswith(("tests/", "scripts/"))
                or ".." in Path(path).parts
                or not (root / path).is_file()
                for path in paths
            )
        ):
            errors.append(f"invalid test coverage: {requirement}")
    if coverage.get("status") != "complete":
        errors.append("incomplete requirement coverage: active recovery plan remains unimplemented")
    prior_path = root / "evidence/CONTRACT/coverage.json"
    if prior_path.exists():
        try:
            prior = json.loads(prior_path.read_text(encoding="utf-8"))
            expected = {
                row["id"]: [item["id"] for item in row["criteria"]]
                for row in prior["requirements"]
                if row.get("phase") == "ROUTE"
            }
            deferrals = coverage.get("contract_deferrals", [])
            actual = {row["id"]: row["criteria"] for row in deferrals}
            if actual != expected or len(actual) != len(deferrals):
                errors.append("missing or malformed CONTRACT deferral coverage")
        except (ValueError, KeyError, TypeError):
            errors.append("malformed CONTRACT deferral coverage")
    for path in REQUIRED_TEST_PATHS:
        if not (root / path).exists():
            errors.append(f"missing required tests: {path}")
    return errors


def reduce_manifests(
    manifests: list[dict[str, object]],
    expected_digest: str,
    root: Path = ROOT,
    *,
    required_platforms: set[tuple[str, str]] | None = None,
    extra_test_paths: tuple[str, ...] = (),
) -> list[str]:
    errors: list[str] = []
    seen: set[tuple[object, object]] = set()
    for manifest in manifests:
        if not isinstance(manifest, dict):
            errors.append("malformed manifest")
            continue
        identity = (manifest.get("os"), manifest.get("python_minor"))
        if not all(isinstance(part, str) for part in identity):
            errors.append("malformed platform identity")
            continue
        if identity not in MATRIX or identity in seen:
            errors.append("unexpected or duplicate platform")
        seen.add(identity)
        if manifest.get("schema_version") != 1 or manifest.get("execution_kind") != "native":
            errors.append("unsupported evidence")
        if manifest.get("input_digest") != expected_digest:
            errors.append("stale input digest")
        if manifest.get("source_stable") is not True:
            errors.append("inputs changed during collection")
        if (
            manifest.get("bridge_version") != "0.20.1"
            or manifest.get("compiler_version") != "baml-cli 0.20.1"
        ):
            errors.append("tool pin mismatch")
        if not manifest.get("runner_identity") or not manifest.get("architecture"):
            errors.append("missing runner identity")
        checks = manifest.get("checks", [])
        expected = commands_for(
            "<python>", Path("<temporary>"), str(identity[0]), extra_test_paths=extra_test_paths
        )
        if (
            not isinstance(checks, list)
            or len(checks) != len(expected)
            or not all(isinstance(item, dict) for item in checks)
            or not all(isinstance(item.get("name"), str) for item in checks)
            or {item.get("name") for item in checks if isinstance(item, dict)} != set(expected)
        ):
            errors.append("missing or duplicate checks")
        if isinstance(checks, list):
            for item in checks:
                if not isinstance(item, dict):
                    errors.append("malformed check")
                    continue
                command = item.get("command")
                name = item.get("name")
                if (
                    not isinstance(command, list)
                    or not command
                    or not all(isinstance(part, str) and part for part in command)
                ):
                    errors.append("malformed command")
                elif (
                    not isinstance(name, str)
                    or name not in expected
                    or normalized_command(command, name) != normalized_command(expected[name], name)
                ):
                    errors.append("stale command coverage")
                elif item.get("command_sha256") != command_digest(command):
                    errors.append("command digest mismatch")
                if type(item.get("exit_code")) is not int or item["exit_code"] != 0:
                    errors.append("failed check")
                if name == "cold_cli" and (
                    type(item.get("duration_seconds")) not in (int, float)
                    or not math.isfinite(item["duration_seconds"])
                    or not 0 < item["duration_seconds"] < 5
                    or item.get("response_status") != "ready"
                ):
                    errors.append("missing or failed cold deadline measurement")
                output_digest = item.get("output_sha256")
                if (
                    not isinstance(output_digest, str)
                    or len(output_digest) != 64
                    or any(char not in "0123456789abcdef" for char in output_digest)
                ):
                    errors.append("missing output digest")
        tests = manifest.get("tests", {})
        if (
            not isinstance(tests, dict)
            or any(
                type(tests.get(key)) is not int
                for key in ("total", "skipped", "failures", "errors")
            )
            or tests.get("total", 0) <= 0
            or any(tests.get(key) != 0 for key in ("skipped", "failures", "errors"))
        ):
            errors.append("missing assertions or skipped tests")
        assertions = manifest.get("assertions")
        if (
            not isinstance(assertions, list)
            or not assertions
            or any(
                not isinstance(row, dict)
                or not isinstance(row.get("node_id"), str)
                or row.get("outcome") != "passed"
                for row in assertions
            )
        ):
            errors.append("missing executed control assertions")
        else:
            if manifest.get("assertions_sha256") != command_digest(assertions):
                errors.append("assertion digest mismatch")
            if (
                not isinstance(tests, dict)
                or len(assertions) != tests.get("total")
                or len({row["node_id"] for row in assertions}) != len(assertions)
            ):
                errors.append("incomplete or duplicate assertion inventory")
            for controls in REQUIRED_CONTROLS.values():
                for control in controls:
                    matched = [
                        row
                        for row in assertions
                        if row["node_id"] == control or row["node_id"].startswith(control + "[")
                    ]
                    if len(matched) < CONTROL_COUNTS.get(control, 1):
                        errors.append("missing executed control: " + control)
        if (
            type(manifest.get("duration_seconds")) not in (int, float)
            or not 0 < manifest["duration_seconds"] <= 600
        ):
            errors.append("invalid or excessive single-node proof cost")
    required = MATRIX if required_platforms is None else required_platforms
    errors.extend(f"missing {name}/Python {minor}" for name, minor in sorted(required - seen))
    if not _valid_spec_delta(root):
        errors.append("malformed spec-delta evidence")
    errors.extend(coverage_errors(root))
    return errors


def collect(root: Path, *, extra_test_paths: tuple[str, ...] = ()) -> dict[str, object]:
    collection_started = time.monotonic()
    initial_digest = input_digest(root)
    with tempfile.TemporaryDirectory(
        prefix="jevdrill-route-", dir=os.environ.get("RUNNER_TEMP"), delete=False
    ) as temporary:
        temporary_path = Path(temporary)
        junit = temporary_path / "tests.xml"
        commands = commands_for(sys.executable, temporary_path, extra_test_paths=extra_test_paths)
        checks: list[dict[str, object]] = []
        for name, command in commands.items():
            started = time.monotonic()
            result = None
            try:
                fixture = None
                if name == "cold_cli":
                    fixture = json.dumps(
                        json.loads(
                            (root / "tests/contracts/fixtures/route-application.json").read_text(
                                encoding="utf-8"
                            )
                        )[0]["payload"]
                    ).encode()
                result = subprocess.run(
                    command,
                    cwd=temporary_path if name == "cold_cli" else root,
                    input=fixture,
                    capture_output=True,
                    timeout=max(0.001, 600 - (time.monotonic() - collection_started)),
                    check=False,
                )
                output = result.stdout + result.stderr
                code = result.returncode
            except subprocess.TimeoutExpired as error:
                output = b"TimeoutExpired\n" + (error.stdout or b"") + (error.stderr or b"")
                code = 125
            except OSError as error:
                output = type(error).__name__.encode()
                code = 125
            checks.append(
                {
                    "name": name,
                    "command": command,
                    "command_sha256": command_digest(command),
                    "exit_code": code,
                    "output_sha256": hashlib.sha256(output).hexdigest(),
                    "duration_seconds": round(time.monotonic() - started, 3),
                }
            )
            if name == "cold_cli":
                try:
                    checks[-1]["response_status"] = (
                        json.loads(result.stdout).get("status")
                        if result is not None
                        else "unavailable"
                    )
                except ValueError:
                    checks[-1]["response_status"] = "unavailable"
            print(f"{name}: {'passed' if code == 0 else 'FAILED'}", flush=True)
            if code:
                print(output.decode(errors="replace")[-20000:], flush=True)
        tests: dict[str, int] = {"total": 0, "skipped": 0, "failures": 0, "errors": 0}
        assertions = []
        if junit.exists():
            suites = ET.parse(junit).getroot().findall("testsuite")
            tests = {
                "total": sum(int(suite.get("tests", 0)) for suite in suites),
                "skipped": sum(int(suite.get("skipped", 0)) for suite in suites),
                "failures": sum(int(suite.get("failures", 0)) for suite in suites),
                "errors": sum(int(suite.get("errors", 0)) for suite in suites),
            }
            for suite in suites:
                for case in suite.findall("testcase"):
                    parts = case.get("classname", "").split(".")
                    while parts and not (root / ("/".join(parts) + ".py")).is_file():
                        parts.pop()
                    node_id = "/".join(parts) + ".py::" + case.get("name", "")
                    outcome = (
                        "skipped"
                        if case.find("skipped") is not None
                        else "failed"
                        if case.find("failure") is not None or case.find("error") is not None
                        else "passed"
                    )
                    assertions.append({"node_id": node_id, "outcome": outcome})
            assertions.sort(key=lambda row: row["node_id"])
    try:
        compiler = subprocess.run(
            [os.environ.get("BAML_CLI", "baml-cli"), "--version"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        compiler = "unavailable"
    return {
        "schema_version": 1,
        "phase": "ROUTE",
        "execution_kind": "native",
        "os": platform.system(),
        "architecture": platform.machine(),
        "python_minor": f"{sys.version_info.major}.{sys.version_info.minor}",
        "python_version": platform.python_version(),
        "bridge_version": importlib.metadata.version("baml-bridge"),
        "compiler_version": compiler,
        "runner_identity": os.environ.get("GITHUB_RUN_ID", platform.node()),
        "timestamp": datetime.now(UTC).isoformat(),
        "input_digest": initial_digest,
        "source_stable": input_digest(root) == initial_digest,
        "checks": checks,
        "tests": tests,
        "assertions": assertions,
        "assertions_sha256": command_digest(assertions),
        "duration_seconds": round(time.monotonic() - collection_started, 3),
        "proof_cost_target_exceeded": time.monotonic() - collection_started > 300,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-only", action="store_true")
    parser.add_argument("--reduce-only", action="store_true")
    args = parser.parse_args()
    platform_dir = ROOT / "evidence/ROUTE/platforms"
    platform_dir.mkdir(parents=True, exist_ok=True)
    current: dict[str, object] | None = None
    if not args.reduce_only:
        current = collect(ROOT)
        path = platform_dir / f"{current['os']}-{current['python_minor']}.json"
        path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    manifests = []
    for path in sorted(platform_dir.glob("*.json")):
        try:
            manifests.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            manifests.append(None)
    errors = reduce_manifests(manifests, input_digest(ROOT), ROOT)
    report = {
        "schema_version": 1,
        "phase": "ROUTE",
        "status": "passed" if not errors else "blocked",
        "errors": errors,
        "input_digest": input_digest(ROOT),
        "platforms": [item.get("os") for item in manifests if isinstance(item, dict)],
    }
    (ROOT / "evidence/ROUTE/verification.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report))
    if args.local_only and current is not None:
        local_errors = reduce_manifests(
            [current], input_digest(ROOT), ROOT, required_platforms={(platform.system(), "3.13")}
        )
        return int(bool(local_errors))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
