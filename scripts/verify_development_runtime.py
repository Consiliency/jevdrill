"""Explicit Linux runtime proof using local responses and an already installed image."""

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
from collections import Counter
from pathlib import Path
from uuid import uuid4

from jevdrill.contracts import ContractError
from jevdrill.integrations.archive import maintenance_lock
from jevdrill.integrations.development import DevelopmentRunner, IndependentDevelopmentGrader
from jevdrill.integrations.experiments import RestrictedContainerRunner

ROOT = Path(__file__).resolve().parents[1]
INSPECTED_IMAGE = "sha256:70af8b01bcbd3a008522f36ea07b679f14f9ad3fb721868cf0cc3f80b7e3f958"
EXPECTED_CHECKS = {
    "actual_baml_local_provider_and_restricted_evaluation",
    "recorded_comparisons_use_independent_restricted_grader",
    "unavailable_image_observed",
    "unavailable_image_rejected_by_runtime_probe",
    "independent_grader_uses_restricted_runtime_and_external_answers",
    "detached_child_observed",
    "restricted_container_limits",
    "container_client_retains_worker_custody",
    "container_and_detached_child_removed_after_worker_death",
    "custody_released_after_container_exit",
    "source_unchanged",
}
RUNTIME_TESTS = (
    "test_development_pair_uses_actual_baml_and_persistent_receipts",
    "test_development_cancel_before_start_survives_restart",
    "test_development_recovery_never_repeats_uncertain_call",
    "test_development_cancel_inflight_waits_and_prevents_second_call",
    "test_development_two_workers_cannot_dispatch_twice",
    "test_development_killed_worker_recovers_without_another_call",
    "test_actual_immediate_host_acceptance_is_bounded_and_not_redispatched",
    "test_actual_baml_artifact_worker_preserves_independent_checks[review]",
    "test_actual_baml_artifact_worker_preserves_independent_checks[documentation]",
    "test_resolved_pause_during_actual_call_prevents_later_call_and_retains_reservation",
    "test_five_arm_comparison_reserves_once_and_survives_restart_without_redispatch",
    "test_five_arm_cancellation_during_third_request_prevents_fourth_and_recovery_retry",
)
RECORDED_TESTS = {
    f"test_recorded_comparison_uses_restricted_grader[{mode}]": "tests.promotion.runtime_recorded_evidence"
    for mode in ("runtime_good", "runtime_bad")
}


def runtime_tests_passed(path, returncode, expected=None):
    """Require every selected test exactly once, without skipped or failed evidence."""
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        return False
    cases = list(root.iter("testcase"))
    if expected is None:
        expected = dict.fromkeys(RUNTIME_TESTS, "tests.experiments.test_development")
    return (
        returncode == 0
        and Counter((case.get("name"), case.get("classname")) for case in cases)
        == Counter(expected.items())
        and not any(list(root.iter(tag)) for tag in ("skipped", "failure", "error"))
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image-id", required=True)
    args = parser.parse_args()
    if args.image_id != INSPECTED_IMAGE:
        raise SystemExit("This proof requires the inspected authorized immutable image.")
    if platform.system() != "Linux":
        raise SystemExit("This proof requires an explicit Linux worker.")
    container = RestrictedContainerRunner(args.image_id)
    inspected_image = json.loads(
        subprocess.run(
            ["docker", "image", "inspect", args.image_id],
            capture_output=True,
            check=True,
            timeout=2,
        ).stdout
    )[0]
    spec = importlib.util.spec_from_file_location(
        "experiment_checks", ROOT / "scripts/verify_experiment_phase.py"
    )
    checks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checks)
    digest = checks.input_digest(ROOT)
    run = ROOT / f".phase-loop/runs/EXPERIMENT-development-{time.strftime('%Y%m%d')}-{uuid4().hex}"
    run.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ, JEVDRILL_DEVELOPMENT_IMAGE=args.image_id)
    junit = run / "tests.xml"
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        f"--junitxml={junit}",
        *[f"tests/experiments/test_development.py::{name}" for name in RUNTIME_TESTS],
    ]
    test = subprocess.run(
        command, cwd=ROOT, env=environment, capture_output=True, timeout=120, check=False
    )
    (run / "restricted-comparison.log").write_bytes(test.stdout + test.stderr)
    outcomes = {
        "actual_baml_local_provider_and_restricted_evaluation": runtime_tests_passed(
            junit, test.returncode
        )
    }
    recorded_junit = run / "recorded-tests.xml"
    recorded_command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        f"--junitxml={recorded_junit}",
        "tests/promotion/runtime_recorded_evidence.py",
    ]
    recorded = subprocess.run(
        recorded_command, cwd=ROOT, env=environment, capture_output=True, timeout=120, check=False
    )
    (run / "recorded-comparison.log").write_bytes(recorded.stdout + recorded.stderr)
    outcomes["recorded_comparisons_use_independent_restricted_grader"] = runtime_tests_passed(
        recorded_junit, recorded.returncode, RECORDED_TESTS
    )
    with tempfile.TemporaryDirectory(prefix="jevdrill-missing-runtime-") as temporary:
        missing_image = "sha256:" + uuid4().hex + uuid4().hex
        probe = subprocess.run(
            ["docker", "image", "inspect", missing_image],
            capture_output=True,
            timeout=2,
            check=False,
        )
        outcomes["unavailable_image_observed"] = (
            probe.returncode != 0 and b"no such image" in probe.stderr.lower()
        )
        runner = DevelopmentRunner(
            Path(temporary) / "worker.db",
            models={},
            cases={},
            container=RestrictedContainerRunner(missing_image),
            credential=lambda: None,
            authorize=lambda _: False,
        )
        outcomes["unavailable_image_rejected_by_runtime_probe"] = False
        if outcomes["unavailable_image_observed"]:
            try:
                runner._runtime()
            except ContractError as error:
                outcomes["unavailable_image_rejected_by_runtime_probe"] = (
                    str(error) == "development_container_unavailable"
                )
    with tempfile.TemporaryDirectory(prefix="jevdrill-independent-grade-") as temporary:
        grader = IndependentDevelopmentGrader(
            {"opaque-grading-key": {"inputs": [[2, 3], [5, 7]], "expected_answers": [5, 12]}},
            container=container,
            lock_path=Path(temporary) / "worker.lock",
            duration_ms=10_000,
            authorize=lambda key: key == "opaque-grading-key",
        )
        grades = grader.grade(
            "opaque-grading-key",
            [
                "function solve(a, b) { return a + b; }",
                "function solve(a, b) { return a - b; }",
            ],
        )
        outcomes["independent_grader_uses_restricted_runtime_and_external_answers"] = grades == [
            {"quality": 1.0, "critical": {"answers_match": True}},
            {"quality": 0.0, "critical": {"answers_match": False}},
        ]
    identity = str(uuid4())
    name = container.container_name(identity)
    with tempfile.TemporaryDirectory(prefix="jevdrill-development-custody-") as temporary:
        lock = Path(temporary) / "worker.lock"
        # Kill only the verifier's Python worker after its generated-code fixture
        # runs. Its Docker client and detached container child must remain bounded.
        worker = subprocess.Popen(
            [
                sys.executable,
                "-c",
                """
from pathlib import Path
import sys, time
from jevdrill.integrations.archive import maintenance_lock
from jevdrill.integrations.experiments import RestrictedContainerRunner
fds = []
with maintenance_lock(Path(sys.argv[3]), acquired_fd=fds.append) as acquired:
    assert acquired
    RestrictedContainerRunner(sys.argv[1]).evaluate(
        'function solve() { require("node:child_process").spawn("node", ["-e", "setInterval(() => {}, 1000)"], {detached: true, stdio: "ignore"}).unref(); while (true) {} }',
        [[]], time.monotonic() + 6, run_id=sys.argv[2], custody_fd=fds[0])
""",
                args.image_id,
                identity,
                str(lock),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            end = time.monotonic() + 5
            inspected = None
            while time.monotonic() < end and worker.poll() is None:
                probe = subprocess.run(
                    ["docker", "inspect", name], capture_output=True, timeout=1, check=False
                )
                if probe.returncode == 0:
                    current = json.loads(probe.stdout)[0]
                    top = subprocess.run(
                        ["docker", "top", name, "-eo", "pid,ppid,args"],
                        capture_output=True,
                        check=False,
                        timeout=1,
                    )
                    processes = [line.split(None, 2) for line in top.stdout.splitlines()[1:]]
                    node_pids = {
                        p[0] for p in processes if len(p) == 3 and p[2].startswith(b"node ")
                    }
                    if (
                        current["State"]["Running"]
                        and len(node_pids) >= 2
                        and any(p[1] in node_pids for p in processes if len(p) == 3)
                    ):
                        inspected = current
                        break
                time.sleep(0.02)
            outcomes["detached_child_observed"] = inspected is not None
            if inspected:
                host = inspected["HostConfig"]
                outcomes["restricted_container_limits"] = (
                    host["NetworkMode"] == "none"
                    and host["ReadonlyRootfs"]
                    and host["Memory"] == 2 * 1024**3
                    and host["NanoCpus"] == 2_000_000_000
                    and host["PidsLimit"] == 64
                    and host["CapDrop"] == ["ALL"]
                    and "no-new-privileges" in host["SecurityOpt"]
                    and inspected["Config"]["User"] == "65534:65534"
                    and not inspected["Mounts"]
                )
            worker.kill()
            worker.wait(timeout=5)
            with maintenance_lock(lock) as acquired:
                outcomes["container_client_retains_worker_custody"] = not acquired
            end = time.monotonic() + 8
            while time.monotonic() < end:
                probe = subprocess.run(
                    ["docker", "inspect", name], capture_output=True, timeout=1, check=False
                )
                if probe.returncode != 0 and b"no such" in probe.stderr.lower():
                    break
                time.sleep(0.05)
            outcomes["container_and_detached_child_removed_after_worker_death"] = (
                probe.returncode != 0 and b"no such" in probe.stderr.lower()
            )
            with maintenance_lock(lock) as acquired:
                outcomes["custody_released_after_container_exit"] = acquired
        finally:
            if worker.poll() is None:
                worker.kill()
                worker.wait(timeout=5)
            container.cleanup(identity)
    outcomes["source_unchanged"] = digest == checks.input_digest(ROOT)
    report = {
        "schema_version": 1,
        "kind": "bounded_development_runtime",
        "os": platform.system(),
        "runner_identity": platform.node(),
        "input_digest": digest,
        "image_id": args.image_id,
        "image_provenance": {name: inspected_image[name] for name in ("Id", "Os", "Architecture")},
        "paid_calls": 0,
        "checks": outcomes,
        "criterion": "EC-EXPERIMENT-2",
        "additional_criterion": "EC-EXPERIMENT-3",
        "coverage": "partial_linux_development_runtime",
        "runtime_test_command": command,
        "runtime_tests": list(RUNTIME_TESTS),
        "runtime_test_exit_code": test.returncode,
        "recorded_test_command": recorded_command,
        "recorded_tests": list(RECORDED_TESTS),
        "recorded_test_exit_code": recorded.returncode,
        "run_directory": str(run.relative_to(ROOT)),
        "artifact_digests": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (
                junit,
                recorded_junit,
                run / "restricted-comparison.log",
                run / "recorded-comparison.log",
            )
        },
        "status": "passed" if all(outcomes.values()) else "failed",
        "limitations": [
            "Local synthetic provider responses do not establish model quality.",
            "This proof does not enable general host execution or policy promotion.",
        ],
    }
    report_path = ROOT / "evidence/EXPERIMENT/development-runtime.json"
    if report_path.exists():
        (run / "previous-development-runtime.json").write_bytes(report_path.read_bytes())
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    return report["status"] != "passed"


if __name__ == "__main__":
    raise SystemExit(main())
