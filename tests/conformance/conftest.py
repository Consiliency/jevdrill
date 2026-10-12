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


@pytest.fixture(scope="session")
def host_conformance(tmp_path_factory):
    root = Path(__file__).parents[2]
    configured = os.environ.get("JEVDRILL_AGENT_HARNESS_ROOT")
    assert configured, "Explicit HOST companion checkout is required"
    companion = Path(configured) / "phase-loop-runtime"
    python = Path(
        os.environ.get(
            "JEVDRILL_AGENT_HARNESS_PYTHON",
            str(companion / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")),
        )
    )
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
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.endswith(("_API_KEY", "_TOKEN", "_SECRET")) and k != "PYTHONHOME"
    }
    env.update(
        JEVDRILL_TEST_CLI=str(cli),
        JEVDRILL_TEST_PYTHON=sys.executable,
        JEVDRILL_TEST_ARTIFACTS=str(artifacts),
        PYTHONPATH=os.pathsep.join([str(companion / "src"), str(companion / "tests")]),
    )
    report = tmp / "probes.xml"
    result = subprocess.run(
        [
            str(python),
            "-m",
            "pytest",
            "-q",
            "--override-ini=addopts=",
            "--rootdir=" + str(root),
            str(root / "research/evaluation/host/test_bridge_probe.py"),
            str(root / "research/evaluation/host/test_baseline_probe.py"),
            f"--junitxml={report}",
            f"--basetemp={tmp / 'child'}",
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    discovery_report = tmp / "discovery.xml"
    discovery = subprocess.run(
        [
            str(python),
            "-m",
            "pytest",
            "-q",
            "--override-ini=addopts=",
            "tests/test_jevdrill_discovery.py",
            f"--junitxml={discovery_report}",
            f"--basetemp={tmp / 'discovery-child'}",
        ],
        cwd=companion,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
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
