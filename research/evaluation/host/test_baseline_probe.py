"""Paired synthetic baselines; provider quality and observed token usage stay unknown."""

import json
import os
import sys
import time
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
from phase_loop_runtime.jevdrill_adapter import JevDrillTransport
from phase_loop_runtime.launcher import build_launch_request, build_launch_spec, launch
from phase_loop_test_utils import make_repo
from test_jevdrill_adapter import FIXTURES, adapter_fixture

CASES = json.loads(Path(__file__).with_name("protocol.json").read_text())["cases"]
BASELINES = ("fixed_default", "cheapest_feasible", "no_optional_guidance")


@pytest.mark.parametrize("case_index", range(6))
@pytest.mark.parametrize("baseline", BASELINES)
def test_paired_baseline(tmp_path, case_index, baseline, control=None):
    adapter, inputs, _, kwargs, _, _ = adapter_fixture(tmp_path)
    adapter.transport = JevDrillTransport(
        (os.environ["JEVDRILL_TEST_PYTHON"], "-m", "jevdrill.cli"),
        tmp_path / "jev.sqlite",
        FIXTURES,
        json.loads((FIXTURES / "digests.json").read_text()),
    )
    if control == "privacy_leak":
        original_sanitize = adapter.queue.sanitize

        def faulty_sanitizer(report):
            clean = original_sanitize(report)
            clean["envelope"]["extensions"]["test.fault"] = "SYNTHETIC_PRIVATE_SENTINEL"
            return clean

        adapter.queue.sanitize = faulty_sanitizer
    default = inputs["inventory"]["candidates"][0]
    default["default"] = True
    cheap = deepcopy(default)
    cheap.update(
        candidate_id="candidate-b",
        model_id="model-b",
        resolved_model_revision="model-b-v1",
        default=False,
    )
    cheap["rates"].update(input_rate="0.0000001", output_rate="0.0000002")
    if baseline == "fixed_default":
        kwargs["model_selection"] = replace(
            kwargs["model_selection"], model="model-a", source="user_override"
        )
    else:
        inputs["inventory"]["candidates"].append(cheap)
    # This protocol has no optional resources: the no-guidance control is deliberately
    # equivalent to cheapest-feasible, and supports no guidance effectiveness claim.
    repo = make_repo(tmp_path)
    before = time.monotonic_ns()
    prepared = adapter.prepare(
        mode="main",
        dry_run=False,
        **kwargs,
        action="execute",
        repo=repo,
        roadmap=repo / "specs/phase-plans-v1.md",
        phase=None,
        plan=None,
        json_output=False,
        bypass_approvals=False,
    )
    routing_ms = (time.monotonic_ns() - before) / 1_000_000
    spec = build_launch_spec(build_launch_request(**prepared))
    assert spec.selected_model == ("model-a" if baseline == "fixed_default" else "model-b")
    assert spec.prompt_bundle.body == "required"
    execution_ms = []

    def execute(_spec, **_kwargs):
        started = time.monotonic_ns()
        result = launch([sys.executable, "-I", "-S", "-c", CASES[case_index]["program"]])
        execution_ms.append((time.monotonic_ns() - started) / 1_000_000)
        return result

    started = time.monotonic_ns()
    result = adapter.launch(execute, spec)
    storage_files = [path for path in tmp_path.rglob("*.sqlite*") if path.is_file()]
    assert adapter.queue.path in storage_files
    privacy_passed = all(
        b"SYNTHETIC_PRIVATE_SENTINEL" not in path.read_bytes() for path in storage_files
    )
    assert privacy_passed is (control != "privacy_leak")
    for _ in range(3):
        adapter.flush()
    elapsed_ms = (time.monotonic_ns() - started) / 1_000_000
    assert result.returncode == 0 and adapter.queue.status()["records"] == 0
    decision = adapter.last_decision
    record = {
        "baseline": baseline,
        "case_index": case_index,
        "artifact": json.loads(result.output),
        "selected_model": spec.selected_model,
        "model_revision": decision["execution_plan"]["resolved_model_revision"],
        "native_effort": decision["execution_plan"]["native_effort"],
        "versions": decision["details"]["versions"],
        "cost_estimate": decision["details"]["cost_estimate"],
        "routing_ms": routing_ms,
        "execution_ms": execution_ms[0],
        "reporting_and_bridge_ms": elapsed_ms - execution_ms[0],
        "token_usage": {"kind": "unknown", "reason": "not_reported"},
        "observed_cost": {"kind": "unknown", "reason": "not_reported"},
        "attempts": 1,
        "failures": 0,
        "provider_execution": False,
        "privacy_passed": privacy_passed,
        "declared_split": "validation"
        if control == "swapped_split"
        else CASES[case_index]["split"],
    }
    destination = Path(os.environ["JEVDRILL_TEST_ARTIFACTS"])
    if control:
        record["control"] = control
    name = f"control-{control}" if control else f"baseline-{baseline}-{case_index}"
    (destination / f"{name}.json").write_text(json.dumps(record))


@pytest.mark.parametrize("control", ["privacy_leak", "swapped_split"])
def test_routed_negative_control(tmp_path, control):
    test_paired_baseline(tmp_path, 0, "cheapest_feasible", control=control)
