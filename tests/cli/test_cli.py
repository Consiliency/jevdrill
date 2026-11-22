import copy
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_route_cli_emits_one_json_response(tmp_path):
    rows = json.loads((ROOT / "tests/contracts/fixtures/route-application.json").read_text())
    payload = copy.deepcopy(rows[0]["payload"])
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "jevdrill.cli",
            "--storage",
            str(tmp_path / "route.sqlite3"),
            "route",
        ],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        cwd=tmp_path,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["status"] == "ready"
    assert result.stderr == ""


def invoke(tmp_path, command, payload, *arguments):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "jevdrill.cli",
            "--storage",
            str(tmp_path / "route.db"),
            command,
            *arguments,
        ],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=tmp_path,
        timeout=6,
        check=False,
    )


@pytest.mark.parametrize(
    "outcome",
    ["ready", "needs_context", "constraint_conflict", "no_compatible_plan", "routing_failed"],
)
def test_five_route_outcomes_and_cold_deadline(tmp_path, outcome):
    payload = json.loads((ROOT / "tests/contracts/fixtures/route-application.json").read_text())[0][
        "payload"
    ]
    if outcome == "needs_context":
        payload["request"]["task_representation"] = ""
    elif outcome == "constraint_conflict":
        payload["request"]["optimization_objective"]["metric_id"] = "unknown"
    elif outcome == "no_compatible_plan":
        payload["inventory"]["candidates"] = []
    elif outcome == "routing_failed":
        payload["inventory"] = None
    started = time.monotonic()
    result = invoke(tmp_path, "route", payload)
    assert time.monotonic() - started < 5
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == outcome


def test_report_acknowledgments_inspect_and_delete(tmp_path):
    rows = json.loads((ROOT / "tests/contracts/fixtures/boundary.json").read_text())
    report = next(row["payload"] for row in rows if row["id"] == "ReportRequest-0")
    assert json.loads(invoke(tmp_path, "report", report).stdout)["status"] == "accepted"
    assert json.loads(invoke(tmp_path, "report", report).stdout)["status"] == "duplicate"
    changed = copy.deepcopy(report)
    changed["event"]["source_sequence"] += 1
    conflict = invoke(tmp_path, "report", changed)
    assert conflict.returncode == 3
    assert json.loads(conflict.stdout)["status"] == "conflict"
    envelope = report["envelope"]
    scope = {
        "project_id": envelope["project_id"],
        "workspace_id": envelope["workspace_id"],
        "producer": "different",
        "operation": "route",
    }
    deleted = invoke(
        tmp_path,
        "delete",
        {},
        "--task-id",
        report["event"]["task_id"],
        "--scope",
        json.dumps(scope),
    )
    assert deleted.returncode == 0
    assert json.loads(invoke(tmp_path, "report", report).stdout)["status"] == "rejected"


@pytest.mark.parametrize(
    ("text", "expected_status"),
    [
        ("a" * 20_000, "ready"),
        (" " * 60_000 + "ordinary", "no_compatible_plan"),
        ("ordinary\\\n" * 2_000, "ready"),
        ("x\\\n" * 20_000 + "ordinary", "no_compatible_plan"),
    ],
    ids=["ordinary-word", "leading-whitespace", "parser-continuations", "long-continuations"],
)
def test_long_ordinary_context_keeps_the_five_second_deadline(tmp_path, text, expected_status):
    payload = json.loads((ROOT / "tests/contracts/fixtures/route-application.json").read_text())[0][
        "payload"
    ]
    payload["request"]["task_representation"] = text
    payload["judgment_policy"] = None
    started = time.monotonic()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "jevdrill.cli",
            "--storage",
            str(tmp_path / "route.db"),
            "--remaining-budget-ms",
            "5000",
            "route",
        ],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=tmp_path,
        timeout=6,
        check=False,
    )
    elapsed = time.monotonic() - started
    if elapsed >= 5:
        print(
            "Failed CLI deadline:",
            json.dumps(
                {
                    "elapsed_seconds": elapsed,
                    "returncode": result.returncode,
                    "response": result.stdout,
                    "stderr": result.stderr,
                    "database_created": (tmp_path / "route.db").exists(),
                }
            ),
        )
        profile_code = (
            "import cProfile,pstats,runpy,sys\n"
            "profile=cProfile.Profile()\n"
            "profile.enable()\n"
            "try:\n"
            " runpy.run_module('jevdrill.cli',run_name='__main__')\n"
            "finally:\n"
            " profile.disable()\n"
            " pstats.Stats(profile,stream=sys.stderr).sort_stats('cumulative').print_stats(30)\n"
        )
        try:
            diagnostic = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    profile_code,
                    "--storage",
                    str(tmp_path / "profile-route.db"),
                    "--remaining-budget-ms",
                    "5000",
                    "route",
                ],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                cwd=tmp_path,
                timeout=6,
                check=False,
            )
            print("Diagnostic rerun only:", diagnostic.returncode, diagnostic.stdout)
            print(diagnostic.stderr)
        except subprocess.TimeoutExpired as error:
            print("Diagnostic rerun timed out:", error.stdout, error.stderr)
    assert elapsed < 5
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == expected_status
    assert result.stderr == ""


def test_incomplete_private_keys_reject_within_the_five_second_deadline(tmp_path):
    payload = json.loads((ROOT / "tests/contracts/fixtures/route-application.json").read_text())[0][
        "payload"
    ]
    payload["request"]["task_representation"] = "-----BEGIN PRIVATE KEY-----\n" * 5000
    payload["judgment_policy"] = None
    started = time.monotonic()
    result = invoke(tmp_path, "route", payload)
    assert time.monotonic() - started < 5
    assert result.returncode == 2, result.stderr
    assert json.loads(result.stdout)["status"] == "invalid"
    assert result.stderr == ""


def test_large_text_that_passes_the_check_is_answered_within_the_five_second_deadline(tmp_path):
    payload = json.loads((ROOT / "tests/contracts/fixtures/route-application.json").read_text())[0][
        "payload"
    ]
    payload["request"]["task_representation"] = "[" + ",".join(["x"] * 400_000) + "]"
    payload["judgment_policy"] = None
    assert len(json.dumps(payload).encode()) < 1_000_000
    started = time.monotonic()
    result = invoke(tmp_path, "route", payload)
    assert time.monotonic() - started < 5
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "no_compatible_plan"
    assert result.stderr == ""


@pytest.mark.parametrize("budget_ms", [1000, 5000])
def test_text_that_cannot_be_checked_in_time_ends_in_the_deadline_outcome(tmp_path, budget_ms):
    # Unicode normalization writes this character as 18, and the tail keeps the text changing
    # through every decoding pass: the costliest request the input limit admits. `route`
    # checks the task text twice, which takes longer than the five-second deadline allows.
    ligature = "\N{ARABIC LIGATURE SALLALLAHOU ALAYHE WASALLAM}"
    tail = "a" + "\\" * 16 + "b"
    payload = json.loads((ROOT / "tests/contracts/fixtures/route-application.json").read_text())[0][
        "payload"
    ]
    payload["judgment_policy"] = None
    payload["request"]["task_representation"] = tail
    room = 1_000_000 - len(json.dumps(payload, ensure_ascii=False).encode())
    payload["request"]["task_representation"] = ligature * (room // 3) + tail
    request = json.dumps(payload, ensure_ascii=False).encode()
    assert 999_990 < len(request) <= 1_000_000
    started = time.monotonic()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "jevdrill.cli",
            "--storage",
            str(tmp_path / "route.db"),
            "--remaining-budget-ms",
            str(budget_ms),
            "route",
        ],
        input=request,
        capture_output=True,
        cwd=tmp_path,
        timeout=budget_ms / 1000 + 15,
        check=False,
    )
    elapsed = time.monotonic() - started
    deadline_outcome = result.returncode == 4 and json.loads(result.stdout) == {
        "schema_version": "1",
        "status": "storage_failure",
        "code": "infrastructure_failure",
    }
    # At one second the check cannot finish. At five a fast machine may answer in time. A machine
    # that finishes the check in the last 50 ms before the deadline gets the answer `route` gives
    # inside its own margin: a stored, retryable routing failure with one of two fixed codes.
    answer = json.loads(result.stdout) if result.returncode == 0 else {}
    answered_in_time = (
        budget_ms == 5000
        and result.returncode == 0
        and elapsed < 6
        and (
            answer["status"] == "no_compatible_plan"
            or (
                answer["status"] == "routing_failed"
                and answer["retryable"] is True
                and answer["error_code"]
                in (
                    "invalid inventory target or deadline",
                    "candidate preparation deadline expired",
                )
            )
        )
    )
    assert deadline_outcome or answered_in_time, (
        result.returncode,
        result.stdout[:200],
        result.stdout[-200:],
    )
    assert elapsed < budget_ms / 1000 + 6, f"{elapsed:.2f} seconds"
    assert result.stderr == b""


@pytest.mark.parametrize(
    "shape", ["a bare array", "an unknown member of a route request", "a member of an experiment"]
)
def test_deeply_nested_input_is_one_invalid_input_response(tmp_path, shape):
    # Each of these is far below the input limit. The first is too deep for the JSON decoder,
    # the second for contract validation and the third for the credential check.
    command = "route"
    if shape == "a bare array":
        raw = "[" * 100_000 + "]" * 100_000
    else:
        nested = "[" * 5_000 + "]" * 5_000
        if shape == "a member of an experiment":
            command, raw = "experiment", '{"note": ' + nested + "}"
        else:
            payload = json.loads(
                (ROOT / "tests/contracts/fixtures/route-application.json").read_text()
            )[0]["payload"]
            raw = json.dumps(payload)[:-1] + ', "note": ' + nested + "}"
    result = subprocess.run(
        [sys.executable, "-m", "jevdrill.cli", "--storage", str(tmp_path / "route.db"), command],
        input=raw,
        check=False,
        text=True,
        capture_output=True,
        cwd=tmp_path,
        timeout=20,
    )
    assert result.returncode == 2
    assert json.loads(result.stdout) == {
        "schema_version": "1",
        "status": "invalid",
        "code": "invalid_input",
    }
    assert result.stderr == ""


@pytest.mark.parametrize(
    "raw",
    ["{", "[]", '{"x":1,"x":2}', "x" * 1_000_001],
    ids=["malformed", "array", "duplicate-key", "oversized"],
)
def test_invalid_input_is_one_redacted_json_response(tmp_path, raw):
    result = subprocess.run(
        [sys.executable, "-m", "jevdrill.cli", "--storage", str(tmp_path / "route.db"), "route"],
        input=raw,
        check=False,
        text=True,
        capture_output=True,
        cwd=tmp_path,
    )
    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "invalid"
    assert result.stderr == ""


def test_storage_creation_failure_and_stalled_input_are_bounded(tmp_path):
    blocked = tmp_path / "file"
    blocked.write_text("synthetic")
    result = subprocess.run(
        [sys.executable, "-m", "jevdrill.cli", "--storage", str(blocked / "route.db"), "route"],
        input="{}",
        check=False,
        text=True,
        capture_output=True,
        cwd=tmp_path,
    )
    assert result.returncode == 4
    assert json.loads(result.stdout)["status"] == "storage_failure"
    process = subprocess.Popen(
        [sys.executable, "-m", "jevdrill.cli", "--remaining-budget-ms", "100", "route"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=tmp_path,
    )
    process.wait(timeout=3)
    stdout, stderr = process.communicate()
    assert process.returncode == 4
    assert json.loads(stdout)["status"] == "storage_failure"
    assert stderr == ""
