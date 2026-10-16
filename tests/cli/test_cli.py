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


def test_deep_malformed_context_rejects_within_the_five_second_deadline(tmp_path):
    payload = json.loads((ROOT / "tests/contracts/fixtures/route-application.json").read_text())[0][
        "payload"
    ]
    payload["request"]["task_representation"] = "{" * 20_000
    payload["judgment_policy"] = None
    started = time.monotonic()
    result = invoke(tmp_path, "route", payload)
    assert time.monotonic() - started < 5
    assert result.returncode == 2, result.stderr
    assert json.loads(result.stdout)["status"] == "invalid"
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
