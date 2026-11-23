import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from jevdrill.evaluation import evaluate_host_artifact, validate_splits

# The one pytest child runs both bridge and baseline probes. This is an aggregate
# test-process watchdog, separate from each logical operation's five-second limit.
HOST_PROBES_WATCHDOG_SECONDS = 420
# The one marker deselected from the other repository's tests (HOST plan, R4 and J6).
DESELECTION = ("-m", "not dotfiles_integration")
# The only parent variables a child sees: what an interpreter needs to start on Linux, macOS
# and Windows. Everything else the children read is set below by name; nothing else passes,
# so no credential, proxy or behaviour switch reaches the other repository's code.
INHERITED_VARIABLES = (
    "PATH",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TMPDIR",
    "TEMP",
    "TMP",
    "SYSTEMROOT",
    "SystemRoot",
    "WINDIR",
    "COMSPEC",
    "PATHEXT",
)


def child_environment(home, **values):
    """A child's whole environment: the allowlist, an empty home, and the named values."""
    env = {name: os.environ[name] for name in INHERITED_VARIABLES if name in os.environ}
    env.update(HOME=str(home), USERPROFILE=str(home), NO_PROXY="127.0.0.1,localhost")
    env["no_proxy"] = env["NO_PROXY"]
    env.update(values)
    return env


def last_test_id(text):
    """The last pytest node id a verbose child printed, or None if it printed none."""
    ids = [line.split(" ", 1)[0] for line in text.splitlines() if "::" in line.split(" ", 1)[0]]
    return ids[-1] if ids else None


def run_child(command, *, cwd, env, timeout, name):
    """Run one pytest child; on watchdog expiry, fail with what it had printed.

    The child runs verbose and unbuffered, so the last test id it printed is the case in
    flight when the watchdog expires. There is no retry and no longer deadline.
    """
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as expired:
        stdout, stderr = (
            part.decode(errors="replace") if isinstance(part, bytes) else (part or "")
            for part in (expired.stdout, expired.stderr)
        )
        in_flight = last_test_id(stdout) or "none printed (collection or setup)"
        pytest.fail(
            f"{name} exceeded its {timeout} s watchdog; last test id: {in_flight}\n"
            + "stdout tail:\n"
            + "\n".join(stdout.splitlines()[-30:])
            + "\nstderr tail:\n"
            + "\n".join(stderr.splitlines()[-30:])
        )


@pytest.fixture(scope="session")
def host_conformance(tmp_path_factory):
    root = Path(__file__).parents[2]
    configured = os.environ.get("JEVDRILL_AGENT_HARNESS_ROOT")
    assert configured, "Explicit HOST companion checkout is required"
    companion = Path(configured) / "phase-loop-runtime"
    configured_python = os.environ.get("JEVDRILL_AGENT_HARNESS_PYTHON")
    assert configured_python, "Explicit HOST companion interpreter is required"
    python = Path(configured_python)
    assert python.is_file(), "Installed companion interpreter is required"
    specification = importlib.util.spec_from_file_location(
        "host_receipt_digest", root / "scripts/verify_host_phase.py"
    )
    verifier = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(verifier)
    companion_digest = verifier.source_digest(companion)
    tmp = tmp_path_factory.mktemp("host-conformance")
    artifacts = tmp / "artifacts"
    artifacts.mkdir()
    cli = Path(sys.executable).parent / ("jevdrill.exe" if os.name == "nt" else "jevdrill")
    assert cli.is_file()
    home = tmp / "home"
    home.mkdir()
    env = child_environment(
        home,
        JEVDRILL_TEST_CLI=str(cli),
        JEVDRILL_TEST_PYTHON=sys.executable,
        JEVDRILL_TEST_ARTIFACTS=str(artifacts),
        PYTHONPATH=os.pathsep.join([str(companion / "src"), str(companion / "tests")]),
        PYTHONUNBUFFERED="1",
    )
    report = tmp / "probes.xml"
    result = run_child(
        [
            str(python),
            "-m",
            "pytest",
            "-v",
            "--override-ini=addopts=",
            *DESELECTION,
            "--rootdir=" + str(root),
            str(root / "research/evaluation/host/test_bridge_probe.py"),
            str(root / "research/evaluation/host/test_baseline_probe.py"),
            f"--junitxml={report}",
            f"--basetemp={tmp / 'child'}",
        ],
        cwd=root,
        env=env,
        timeout=HOST_PROBES_WATCHDOG_SECONDS,
        name="probe child",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    discovery_report = tmp / "discovery.xml"
    discovery = run_child(
        [
            str(python),
            "-m",
            "pytest",
            "-v",
            "--override-ini=addopts=",
            *DESELECTION,
            "tests/test_jevdrill_discovery.py",
            f"--junitxml={discovery_report}",
            f"--basetemp={tmp / 'discovery-child'}",
        ],
        cwd=companion,
        env=env,
        timeout=120,
        name="companion discovery child",
    )
    assert discovery.returncode == 0, discovery.stdout + discovery.stderr
    discovery_assertions = verifier.assertions_from(discovery_report, companion)
    discovery_receipt = {
        "origin": "installed_companion_conformance_subprocess",
        "command": discovery.args,
        "command_sha256": verifier.digest_value(discovery.args),
        "output_sha256": hashlib.sha256((discovery.stdout + discovery.stderr).encode()).hexdigest(),
        "input_digest": companion_digest,
        "source_stable": verifier.source_digest(companion) == companion_digest,
        "exit_code": discovery.returncode,
        "assertions": discovery_assertions,
        "assertions_sha256": verifier.digest_value(discovery_assertions),
    }
    assertions = []
    cases = [
        case
        for path in (report, discovery_report)
        for case in ET.parse(path).getroot().iter("testcase")
    ]
    for case in cases:
        outcome = (
            "failed"
            if case.find("failure") is not None or case.find("error") is not None
            else ("skipped" if case.find("skipped") is not None else "passed")
        )
        assertions.append(
            {"id": case.get("classname") + "::" + case.get("name"), "outcome": outcome}
        )
    assert assertions and all(row["outcome"] == "passed" for row in assertions)
    records = [json.loads(path.read_text()) for path in sorted(artifacts.glob("*.json"))]
    assert records
    protocol = json.loads((root / "research/evaluation/host/protocol.json").read_text())
    cases = protocol["cases"]
    groups = {case["id"]: case["ancestry"] for case in cases}
    validate_splits(
        {
            split: [case["id"] for case in cases if case["split"] == split]
            for split in ("development", "validation")
        },
        groups,
        set(groups),
    )
    assert protocol["holdouts_opened"] is False and protocol["promotion_eligible"] is False
    for record in records:
        if "artifact" not in record:
            continue
        case = cases[record["case_index"]]
        checks = evaluate_host_artifact(case["family"], case["expected"], record.pop("artifact"))
        if record.get("control") in ("privacy_leak", "swapped_split"):
            checks["privacy"] = record["privacy_passed"]
            checks["split_provenance"] = record["declared_split"] == case["split"]
            assert not all(checks.values())
        elif "damaged" in record:
            assert all(checks.values()) is not record["damaged"]
        else:
            assert all(checks.values())
        record.update(
            objective_checks=checks,
            dataset_revision=protocol["revision"],
            rubric_revision=protocol["rubric_revision"],
            task_family=case["family"],
            ancestry=case["ancestry"],
            split=case["split"],
            model_judgment=None,
            host_preference=None,
        )
    witness = {
        "assertions": assertions,
        "records": records,
        "companion_discovery": discovery_receipt,
        "claim_scope": "synthetic_conformance_only",
        "probes_watchdog_seconds": HOST_PROBES_WATCHDOG_SECONDS,
        "performance_claims": "insufficient_evidence",
        "holdouts_opened": False,
        "promotion_eligible": False,
        "evaluator_sha256": hashlib.sha256(
            (root / "src/jevdrill/evaluation.py").read_bytes()
        ).hexdigest(),
        "command_sha256": hashlib.sha256(
            json.dumps([result.args, discovery.args]).encode()
        ).hexdigest(),
        "output_sha256": hashlib.sha256(
            (result.stdout + result.stderr + discovery.stdout + discovery.stderr).encode()
        ).hexdigest(),
        "source_sha256": hashlib.sha256(
            (root / "research/evaluation/host/test_bridge_probe.py").read_bytes()
        ).hexdigest(),
    }
    if output := os.environ.get("JEVDRILL_EVALUATION_OUTPUT"):
        Path(output).write_text(json.dumps(witness, sort_keys=True, indent=2) + "\n")
    return witness
